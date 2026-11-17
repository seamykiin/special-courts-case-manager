#!/usr/bin/env python3
"""
Special Courts Case Management System — Local Server
Serves index.html with native CoreGraphics + Tesseract OCR + Ollama Vision integration.
"""

import os
import sys
import threading
import json
import base64
import io
import re
import shutil
import sqlite3
import tempfile
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Import core extraction from case.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from case import (
    extract_image_frames,
    run_tesseract_ocr,
    clean_and_normalize_case_data,
    process_frame,
    group_extracted_pages,
    check_ollama_available,
    check_tesseract_available,
    extract_case_number_only,
    render_document_page_png,
    get_pdf_page_count,
    NOTICE_TO_RESPONDENT_REGEX,
    extract_court_hall_from_filename,
    extract_bundle_month_year_from_filename,
    summarize_call_description_from_window,
    infer_stage_group_from_description,
    log_ocr,
    get_recent_logs
)

# Safe streams for windowed (no-console) execution
class _SafeStream:
    def __init__(self, target=None):
        self._target = target
    def write(self, s):
        if self._target:
            try:
                self._target.write(s)
                self._target.flush()
            except Exception:
                pass
    def flush(self):
        if self._target:
            try:
                self._target.flush()
            except Exception:
                pass
    def isatty(self):
        return False

def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

try:
    _log_fp = open(get_app_dir() / "server.log", "a", encoding="utf-8")
except Exception:
    _log_fp = None

if sys.stdout is None:
    sys.stdout = _SafeStream(_log_fp)
if sys.stderr is None:
    sys.stderr = _SafeStream(_log_fp)

ACTIVE_PORT = None
SERVER_READY_EVENT = threading.Event()

PORT = int(os.environ.get("PORT", 8000))

DB_PATH = get_app_dir() / "pending_cases.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS custom_options (
        field_key TEXT PRIMARY KEY,
        field_value TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        display_name TEXT,
        role TEXT,
        role_title TEXT,
        hall TEXT,
        mode TEXT,
        password TEXT,
        status TEXT
    )""")
    c.execute("""
    CREATE TABLE IF NOT EXISTS cases (
        id TEXT PRIMARY KEY,
        case_no TEXT,
        type TEXT,
        filing_year INTEGER,
        operator_id TEXT,
        entered_by TEXT,
        court_hall TEXT,
        status TEXT,
        data_json TEXT,
        created_at TEXT,
        updated_at TEXT
    )""")
    conn.commit()

    user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if user_count == 0:
        default_users = [
            ("admin", "System Administrator", "admin", "Registrar & System Administrator", "1", "Pending", "admin", "active"),
            ("operator1", "Data Entry Person 1", "operator", "Data Entry Operator (Desk 1)", "1", "Pending", "operator", "active"),
            ("operator2", "Data Entry Person 2", "operator", "Data Entry Operator (Desk 2)", "2", "Pending", "operator", "active"),
        ]
        c.executemany("INSERT INTO users VALUES (?,?,?,?,?,?,?,?)", default_users)
        conn.commit()

    case_count = c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    if case_count == 0 and os.path.exists("sample_cause_list.csv"):
        import csv
        with open("sample_cause_list.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for idx, r in enumerate(reader):
                cno = r.get("Case No.", "")
                if not cno: continue
                if idx % 3 == 0:
                    op_id = "operator1"
                    ent_by = "Data Entry Person 1"
                elif idx % 3 == 1:
                    op_id = "operator2"
                    ent_by = "Data Entry Person 2"
                else:
                    op_id = "admin"
                    ent_by = "System Administrator"
                
                ch = "2" if r.get("Court Hall") == "II" else "1"
                fyr = int(r.get("Filed Year")) if r.get("Filed Year", "").isdigit() else 2024
                ctype = r.get("Type", "G")
                st_grp = r.get("Stage Group", "Evidence")
                cur_st = r.get("Current Stage", "Appearance of Accused")
                next_h = r.get("Next Hearing", "2026-11-02")
                c_date = (r.get("Created At") or "2026-10-23T06:00:00.000Z")
                cid = f"case_{idx+1}"

                cs_obj = {
                    "id": cid,
                    "caseNo": cno,
                    "fullCaseNo": cno,
                    "existing_case_no": cno,
                    "type": ctype,
                    "case_type": f"LGC({ctype})" if ctype in ("G","P","T","S") else ctype,
                    "court": f"Court Hall No.{ch}",
                    "courtHall": ch,
                    "filedYear": fyr,
                    "filing_year": fyr,
                    "stageGroup": st_grp,
                    "stage_group": st_grp,
                    "currentStage": cur_st,
                    "stage": cur_st,
                    "sub_stage": cur_st,
                    "nextHearing": next_h,
                    "hearing_date": next_h,
                    "operatorId": op_id,
                    "enteredBy": ent_by,
                    "entered_by": ent_by,
                    "status": "Pending",
                    "caseMode": "Pending",
                    "entryDate": c_date[:10],
                    "createdAt": c_date,
                    "updatedAt": c_date,
                    "applicants": "Special Tahsildar, Bengaluru",
                    "applicant_name": "Special Tahsildar",
                    "applicant_address": "Bengaluru Urban District",
                    "respondents": "Sri Anand Kumar & Others",
                    "respondent_name": "Sri Anand Kumar",
                    "respondent_address": "Hebbal, Bengaluru North",
                    "district": "Bengaluru Urban",
                    "taluk": "Bengaluru North",
                    "hobli": "Kasaba",
                    "village": "Hebbal",
                    "surveyNo": f"{idx+10}/A",
                    "survey_no": f"{idx+10}/A",
                    "extent": "1.20",
                    "unit": "Acre + Guntas",
                    "extentUnit": "Acre + Guntas",
                    "restoration": "No"
                }

                c.execute("""
                INSERT OR REPLACE INTO cases (id, case_no, type, filing_year, operator_id, entered_by, court_hall, status, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (cid, cno, ctype, fyr, op_id, ent_by, ch, "Pending", json.dumps(cs_obj), c_date, c_date))
        conn.commit()

    conn.close()

def get_pdf_folder_path() -> str:
    db_file = DB_PATH
    if db_file.exists():
        try:
            conn = sqlite3.connect(db_file)
            row = conn.execute("SELECT field_value FROM custom_options WHERE field_key = 'pdf_folder_path'").fetchone()
            conn.close()
            if row and row[0] and os.path.exists(row[0]):
                return row[0]
        except Exception:
            pass
    cand = Path.home() / "Documents" / "Case Names"
    if cand.exists():
        return str(cand)
    return str(Path.cwd())

def set_pdf_folder_path(new_path: str) -> tuple[bool, str, int]:
    p = os.path.expanduser(str(new_path).strip())
    if not os.path.exists(p):
        return False, f"Folder does not exist: {p}", 0
    if not os.path.isdir(p):
        return False, f"Path is not a directory: {p}", 0
    
    pdf_count = 0
    for root, _, files in os.walk(p):
        for f in files:
            if f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
                pdf_count += 1
                
    db_file = DB_PATH
    try:
        conn = sqlite3.connect(db_file)
        conn.execute("CREATE TABLE IF NOT EXISTS custom_options (field_key TEXT PRIMARY KEY, field_value TEXT)")
        conn.execute("INSERT OR REPLACE INTO custom_options (field_key, field_value) VALUES ('pdf_folder_path', ?)", (p,))
        conn.commit()
        conn.close()
    except Exception as e:
        return False, str(e), 0
        
    return True, p, pdf_count

def find_case_pdf(case_no: str, year: str = "") -> tuple[str | None, int]:
    if not case_no:
        return None, 0

    clean_no = extract_case_number_only(str(case_no)).lower()
    if not clean_no:
        return None, 0

    folder = get_pdf_folder_path()
    search_dirs = []
    if folder and os.path.exists(folder):
        search_dirs.append(folder)
    cwd_str = str(Path.cwd())
    if cwd_str not in search_dirs:
        search_dirs.append(cwd_str)
    
    # Also search application directory and system temp folder
    app_dir_str = str(get_app_dir())
    if app_dir_str not in search_dirs:
        search_dirs.append(app_dir_str)
    sys_tmp = tempfile.gettempdir()
    if sys_tmp not in search_dirs:
        search_dirs.append(sys_tmp)
    if os.path.exists("/tmp") and "/tmp" not in search_dirs:
        search_dirs.append("/tmp")

    exact_pat = re.compile(rf"(?:^|\D){re.escape(clean_no)}(?:\D|$)", re.IGNORECASE)
    candidates = []

    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in (".pdf", ".jpg", ".jpeg", ".png"):
                    score = 0
                    fn = f.lower()
                    if exact_pat.search(f):
                        score += 500
                    elif clean_no in fn:
                        score += 200
                    else:
                        continue  # Must match the case number!

                    if year and str(year) in fn:
                        score += 50
                    if folder and (root == folder or str(root).startswith(str(folder))):
                        score += 40
                    # Prioritize files containing bundle and month/year details
                    if re.search(r'(?:Bundle[-_ ]*|[Bb])[0-9A-Za-z]+[-_ ]+(?:0?[1-9]|1[0-2])[-_ /.]+(?:19|20)[0-9]{2}', fn):
                        score += 20
                    elif re.search(r'(?:Bundle[-_ ]*|[Bb])[0-9A-Za-z]+', fn):
                        score += 10
                    if " (" in fn or "copy" in fn:
                        score -= 50
                    if score > 0:
                        candidates.append((score, os.path.join(root, f)))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_match = candidates[0][1]
        
        total_pages = get_pdf_page_count(best_match)
        res = render_document_page_png(best_match, 1, 1000)
        if res and res[1] > 0:
            total_pages = res[1]
        return best_match, total_pages

    return None, 0

class CaseRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        static_dir = getattr(sys, "_MEIPASS", None)
        app_dir = get_app_dir()
        if static_dir and os.path.exists(os.path.join(static_dir, "index.html")):
            kwargs["directory"] = str(static_dir)
        elif os.path.exists(os.path.join(app_dir, "index.html")):
            kwargs["directory"] = str(app_dir)
        super().__init__(*args, **kwargs)

    def handle(self):
        try:
            super().handle()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            if "10053" in str(e) or "10054" in str(e):
                pass
            else:
                raise

    def finish(self):
        try:
            super().finish()
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            if "10053" in str(e) or "10054" in str(e):
                pass
            else:
                raise

    def log_message(self, format, *args):
        try:
            if sys.stderr is not None:
                sys.stderr.write("%s - - [%s] %s\n" %
                                 (self.address_string(),
                                  self.log_date_time_string(),
                                  format % args))
        except Exception:
            pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, PUT, DELETE")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With, Access-Control-Request-Private-Network")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_HEAD(self):
        return self.do_GET()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path in ("/", "", "/index.html"):
            # Resolve index.html location with absolute priority
            html_candidates = [
                getattr(sys, "_MEIPASS", None) and os.path.join(getattr(sys, "_MEIPASS"), "index.html"),
                os.path.join(get_app_dir(), "index.html"),
                "index.html",
            ]
            html_file = None
            for cand in html_candidates:
                if cand and os.path.exists(cand):
                    html_file = cand
                    break

            if html_file:
                try:
                    with open(html_file, "rb") as f:
                        data = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                except Exception as err:
                    self.send_response(500)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(f"Error reading index.html: {err}".encode("utf-8"))
                    return

            self.path = "/index.html"
            return super().do_GET()
        elif path == "/api/status":
            self.handle_status()
            return
        elif path == "/api/models":
            self.handle_models()
            return
        elif path == "/api/pdf-folder":
            self.handle_get_pdf_folder()
            return
        elif path == "/api/find-pdf":
            self.handle_find_pdf(query)
            return
        elif path == "/api/render-page":
            self.handle_render_page(query)
            return
        elif path == "/api/pdf-raw":
            self.handle_pdf_raw(query)
            return
        elif path == "/api/users":
            self.handle_get_users()
            return
        elif path == "/api/cases":
            self.handle_get_cases()
            return
        elif path == "/api/logs":
            self.handle_logs()
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path.startswith("/api/scan"):
            self.handle_scan()
            return
        elif path.startswith("/api/pdf-folder"):
            self.handle_set_pdf_folder()
            return
        elif path == "/api/users":
            self.handle_save_users()
            return
        elif path == "/api/cases":
            self.handle_save_cases()
            return
        elif path == "/api/login":
            self.handle_login()
            return
        elif path == "/api/change-password":
            self.handle_change_password()
            return
        elif path == "/api/upload-pdf":
            self.handle_upload_pdf()
            return
        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)
        if path == "/api/users":
            self.handle_delete_user(query)
            return
        elif path == "/api/cases":
            self.handle_delete_case(query)
            return
        self.send_error(404, "Endpoint not found")

    def handle_get_users(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            rows = c.execute("SELECT username, display_name, role, role_title, hall, mode, password, status FROM users").fetchall()
            conn.close()
            res = {}
            for r in rows:
                res[r[0]] = {
                    "username": r[0],
                    "displayName": r[1],
                    "role": r[2],
                    "roleTitle": r[3],
                    "hall": r[4],
                    "mode": r[5],
                    "password": r[6],
                    "status": r[7]
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_save_users(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # Can be a dict { username: { ... } } or single user dict
            items = []
            if isinstance(data, dict):
                if "username" in data:
                    items.append(data)
                else:
                    for k, v in data.items():
                        if isinstance(v, dict):
                            items.append(v)
            elif isinstance(data, list):
                items = data

            for u in items:
                un = str(u.get("username", "")).strip().lower()
                if not un:
                    continue
                dn = u.get("displayName") or u.get("display_name") or un
                role = u.get("role") or "operator"
                rt = u.get("roleTitle") or u.get("role_title") or ("System Administrator" if role == "admin" else "Data Entry Operator")
                hall = str(u.get("hall") or "1")
                mode = u.get("mode") or "Pending"
                pwd = u.get("password") or "operator"
                st = u.get("status") or "active"

                c.execute("""
                INSERT OR REPLACE INTO users (username, display_name, role, role_title, hall, mode, password, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (un, dn, role, rt, hall, mode, pwd, st))

            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_login(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            username = str(data.get("username", "")).strip().lower()
            password = str(data.get("password", "")).strip()

            if not username:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Username is required."}).encode("utf-8"))
                return

            if not password:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Password is required for authentication."}).encode("utf-8"))
                return

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            row = c.execute("SELECT username, display_name, role, role_title, hall, mode, password, status FROM users WHERE LOWER(username) = ?", (username,)).fetchone()
            conn.close()

            if not row:
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": f"Account '{username}' does not exist."}).encode("utf-8"))
                return

            db_user, display_name, role, role_title, hall, mode, db_password, status = row
            if status == "disabled":
                self.send_response(403)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": f"Account '{display_name}' is disabled. Please contact the System Administrator."}).encode("utf-8"))
                return

            if db_password and password != db_password:
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Incorrect password. Please verify credentials."}).encode("utf-8"))
                return

            user_obj = {
                "username": db_user,
                "displayName": display_name,
                "role": role,
                "roleTitle": role_title,
                "hall": hall,
                "mode": mode,
                "status": status
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "user": user_obj}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

    def handle_change_password(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            username = str(data.get("username", "")).strip().lower()
            current_password = str(data.get("current_password", "")).strip()
            new_password = str(data.get("new_password", "")).strip()

            if not username or not current_password or not new_password:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Username, current password, and new password are all required."}).encode("utf-8"))
                return

            if len(new_password) < 4:
                self.send_response(400)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "New password must be at least 4 characters long."}).encode("utf-8"))
                return

            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            row = c.execute("SELECT password FROM users WHERE LOWER(username) = ?", (username,)).fetchone()
            if not row:
                conn.close()
                self.send_response(404)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": f"Account '{username}' does not exist."}).encode("utf-8"))
                return

            db_password = row[0]
            if db_password and current_password != db_password:
                conn.close()
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": "Current password is incorrect. Verification failed."}).encode("utf-8"))
                return

            c.execute("UPDATE users SET password = ? WHERE LOWER(username) = ?", (new_password, username))
            conn.commit()
            conn.close()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "message": "Password updated successfully."}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode("utf-8"))

    def handle_delete_user(self, query):
        try:
            username = query.get("username", [""])[0].strip().lower()
            if not username:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Username required"}).encode("utf-8"))
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"deleted": True, "username": username}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_get_cases(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            rows = c.execute("SELECT id, case_no, type, filing_year, operator_id, entered_by, court_hall, status, data_json, created_at, updated_at FROM cases").fetchall()
            conn.close()
            cases = []
            for r in rows:
                try:
                    obj = json.loads(r[8]) if r[8] else {}
                except Exception:
                    obj = {}
                obj["id"] = r[0]
                obj["caseNo"] = r[1]
                obj["type"] = r[2]
                obj["filing_year"] = r[3]
                obj["filedYear"] = r[3]
                obj["operatorId"] = r[4]
                obj["enteredBy"] = r[5]
                obj["entered_by"] = r[5]
                obj["courtHall"] = r[6]
                obj["status"] = r[7]
                obj["createdAt"] = r[9]
                obj["updatedAt"] = r[10]
                cases.append(obj)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(cases).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_save_cases(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            items = data if isinstance(data, list) else [data]
            for cs in items:
                if not isinstance(cs, dict):
                    continue
                cid = cs.get("id") or ("case_" + str(int(os.times().elapsed * 1000)))
                cno = cs.get("caseNo") or cs.get("existing_case_no") or ""
                ctype = cs.get("type") or cs.get("case_type") or "G"
                fyr = int(cs.get("filedYear") or cs.get("filing_year") or 2024)
                op_id = cs.get("operatorId") or "admin"
                ent_by = cs.get("enteredBy") or cs.get("entered_by") or "System Administrator"
                ch = str(cs.get("courtHall") or "1")
                st = cs.get("status") or cs.get("caseMode") or "Pending"
                cat = cs.get("createdAt") or ""
                uat = cs.get("updatedAt") or ""
                data_json = json.dumps(cs)

                c.execute("""
                INSERT OR REPLACE INTO cases (id, case_no, type, filing_year, operator_id, entered_by, court_hall, status, data_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (cid, cno, ctype, fyr, op_id, ent_by, ch, st, data_json, cat, uat))

            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"success": True, "count": len(items)}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_delete_case(self, query):
        try:
            cid = query.get("id", [""])[0]
            if not cid:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "ID required"}).encode("utf-8"))
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM cases WHERE id = ?", (cid,))
            conn.commit()
            conn.close()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"deleted": True, "id": cid}).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_get_pdf_folder(self):
        folder = get_pdf_folder_path()
        exists = os.path.exists(folder) and os.path.isdir(folder)
        file_count = 0
        if exists:
            for root, _, files in os.walk(folder):
                for f in files:
                    if f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
                        file_count += 1
        res = {
            "folder": folder,
            "exists": exists,
            "file_count": file_count
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(res).encode("utf-8"))

    def handle_set_pdf_folder(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))
            new_folder = data.get("folder", "").strip()
            ok, msg_or_path, count = set_pdf_folder_path(new_folder)
            if not ok:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": msg_or_path}).encode("utf-8"))
                return
            res = {
                "success": True,
                "folder": msg_or_path,
                "file_count": count
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_find_pdf(self, query):
        case_no = query.get("caseNo", [""])[0] or query.get("cno", [""])[0]
        year = query.get("year", [""])[0]
        folder = get_pdf_folder_path()
        matched_file, total_pages = find_case_pdf(case_no, year)
        if matched_file and os.path.exists(matched_file):
            fn = os.path.basename(matched_file)
            fn_details = extract_bundle_month_year_from_filename(fn) or {}
            res = {
                "found": True,
                "path": matched_file,
                "filename": fn,
                "totalPages": total_pages,
                "folder": folder,
                "bundleNo": fn_details.get("bundleNo", ""),
                "bundle_number": fn_details.get("bundleNo", ""),
                "month": fn_details.get("month", ""),
                "year": fn_details.get("year", ""),
                "monthYear": fn_details.get("monthYear", ""),
                "month_year": fn_details.get("monthYear", ""),
                "courtHall": fn_details.get("courtHall", ""),
                "caseNo": fn_details.get("caseNo", ""),
                "caseType": fn_details.get("caseType", ""),
                "filingYear": fn_details.get("filingYear", "")
            }
        else:
            res = {
                "found": False,
                "message": f"No matching PDF found for case '{case_no}' in '{folder}'",
                "folder": folder
            }
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(res).encode("utf-8"))

    def handle_upload_pdf(self):
        try:
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            saved_files = []
            if "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[-1].strip()
                if boundary.startswith('"') and boundary.endswith('"'):
                    boundary = boundary[1:-1]
                parts = body.split(f"--{boundary}".encode())
                for p in parts:
                    if not p or p == b"--\r\n" or p == b"--":
                        continue
                    if b"\r\n\r\n" in p:
                        header_part, content_part = p.split(b"\r\n\r\n", 1)
                        content_part = content_part.rstrip(b"\r\n")
                        header_text = header_part.decode("utf-8", errors="ignore")
                        if 'filename="' in header_text:
                            fn_match = re.search(r'filename="([^"]+)"', header_text)
                            fn = fn_match.group(1) if fn_match else "uploaded.pdf"
                            fn = os.path.basename(fn)
                            sys_tmp = tempfile.gettempdir()
                            dest_dirs = [get_pdf_folder_path(), sys_tmp]
                            chosen_path = None
                            for d in dest_dirs:
                                if d and os.path.exists(d):
                                    fp = os.path.join(d, fn)
                                    with open(fp, "wb") as f_out:
                                        f_out.write(content_part)
                                    if not chosen_path:
                                        chosen_path = fp
                            saved_files.append((fn, chosen_path or os.path.join(sys_tmp, fn)))

            elif "application/json" in content_type:
                data = json.loads(body.decode("utf-8"))
                fn = data.get("filename", "uploaded.pdf")
                fn = os.path.basename(fn)
                b64 = data.get("data", "")
                if "," in b64:
                    b64 = b64.split(",", 1)[1]
                raw_bytes = base64.b64decode(b64)
                sys_tmp = tempfile.gettempdir()
                dest_dirs = [get_pdf_folder_path(), sys_tmp]
                chosen_path = None
                for d in dest_dirs:
                    if d and os.path.exists(d):
                        fp = os.path.join(d, fn)
                        with open(fp, "wb") as f_out:
                            f_out.write(raw_bytes)
                        if not chosen_path:
                            chosen_path = fp
                saved_files.append((fn, chosen_path or os.path.join(sys_tmp, fn)))

            if not saved_files:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No file uploaded"}).encode("utf-8"))
                return

            fn, file_path = saved_files[0]
            fn_details = extract_bundle_month_year_from_filename(fn) or {}
            total_pages = get_pdf_page_count(file_path)
            res = render_document_page_png(file_path, 1, 1000)
            if res and res[1] > 0:
                total_pages = res[1]

            result = {
                "success": True,
                "path": file_path,
                "filename": fn,
                "totalPages": total_pages,
                "bundleNo": fn_details.get("bundleNo", ""),
                "bundle_number": fn_details.get("bundleNo", ""),
                "month": fn_details.get("month", ""),
                "year": fn_details.get("year", ""),
                "monthYear": fn_details.get("monthYear", ""),
                "month_year": fn_details.get("monthYear", ""),
                "courtHall": fn_details.get("courtHall", ""),
                "caseNo": fn_details.get("caseNo", ""),
                "caseType": fn_details.get("caseType", ""),
                "filingYear": fn_details.get("filingYear", "")
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def handle_render_page(self, query):
        file_path = query.get("path", [""])[0]
        page_str = query.get("page", ["1"])[0]
        dim_str = query.get("max_dim", ["1400"])[0]
        try:
            page_num = max(1, int(page_str))
            max_dim = max(400, min(3000, int(dim_str)))
        except Exception:
            page_num = 1
            max_dim = 1400

        if not file_path or not os.path.exists(file_path):
            self.send_error(404, "File not found")
            return

        res = render_document_page_png(file_path, page_num, max_dim=max_dim)
        if not res:
            self.send_error(500, "Failed to render document page")
            return

        png_bytes, total_pages = res
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(png_bytes)))
        self.send_header("X-Total-Pages", str(total_pages))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(png_bytes)

    def handle_pdf_raw(self, query):
        file_path = query.get("path", [""])[0]
        if not file_path or not os.path.exists(file_path):
            self.send_error(404, "File not found")
            return

        fn = os.path.basename(file_path)
        mime = "application/pdf" if fn.lower().endswith(".pdf") else "image/jpeg"
        size = os.path.getsize(file_path)

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(size))
        self.send_header("Content-Disposition", f'inline; filename="{fn}"')
        self.end_headers()
        with open(file_path, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def handle_status(self):
        try:
            is_tess, tess_path = check_tesseract_available()
            is_ollama, models = check_ollama_available()
            res = {
                "status": "ready",
                "tesseract": {
                    "available": is_tess,
                    "path": tess_path or ""
                },
                "ollama": {
                    "available": is_ollama,
                    "models": models or []
                }
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass

    def handle_models(self):
        _, models = check_ollama_available()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"models": models or []}).encode("utf-8"))

    def handle_logs(self):
        try:
            logs = get_recent_logs(200)
            is_tess, tess_path = check_tesseract_available()
            is_ol, ol_models = check_ollama_available()
            res = {
                "status": "ready",
                "tesseract": {
                    "available": is_tess,
                    "path": tess_path or ""
                },
                "ollama": {
                    "available": is_ol,
                    "models": ol_models or []
                },
                "logs": logs
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))
        except (ConnectionAbortedError, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as err:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))

    def handle_scan(self):
        try:
            content_type = self.headers.get("Content-Type", "")
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            saved_files = []
            engine = "ocr"
            model_name = "qwen2.5vl:7b"

            if "multipart/form-data" in content_type:
                boundary = content_type.split("boundary=")[-1].strip()
                if boundary.startswith('"') and boundary.endswith('"'):
                    boundary = boundary[1:-1]
                
                parts = body.split(f"--{boundary}".encode())
                for p in parts:
                    if not p or p == b"--\r\n" or p == b"--":
                        continue
                    if b"\r\n\r\n" in p:
                        header_part, content_part = p.split(b"\r\n\r\n", 1)
                        content_part = content_part.rstrip(b"\r\n")
                        header_text = header_part.decode("utf-8", errors="ignore")
                        
                        if 'name="engine"' in header_text:
                            engine = content_part.decode("utf-8", errors="ignore").strip()
                        elif 'name="model"' in header_text:
                            model_name = content_part.decode("utf-8", errors="ignore").strip()
                        elif 'filename="' in header_text:
                            fn_match = re.search(r'filename="([^"]+)"', header_text)
                            fn = fn_match.group(1) if fn_match else "uploaded_file"
                            fn = os.path.basename(fn)
                            temp_dir = tempfile.gettempdir()
                            temp_path = os.path.join(temp_dir, fn)
                            with open(temp_path, "wb") as tf:
                                tf.write(content_part)
                            saved_files.append((fn, temp_path))

            elif "application/json" in content_type:
                data = json.loads(body.decode("utf-8"))
                engine = data.get("engine", "ocr")
                model_name = data.get("model", "qwen2.5vl:7b")
                files_data = data.get("files", [])
                temp_dir = tempfile.gettempdir()
                for item in files_data:
                    fn = item.get("filename", "upload.jpg")
                    fn = os.path.basename(fn)
                    b64 = item.get("data", "")
                    if b64:
                        if "," in b64:
                            b64 = b64.split(",", 1)[1]
                        raw_bytes = base64.b64decode(b64)
                        temp_path = os.path.join(temp_dir, fn)
                        with open(temp_path, "wb") as tf:
                            tf.write(raw_bytes)
                        saved_files.append((fn, temp_path))

            log_ocr(f"[/api/scan] Incoming request: {len(saved_files)} file(s), engine='{engine}', model='{model_name}'")

            if not saved_files:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No files received"}).encode("utf-8"))
                return

            all_page_results = []
            for orig_name, file_path in saved_files:
                frames = extract_image_frames(file_path)
                log_ocr(f"[/api/scan] '{orig_name}' split into {len(frames)} page frame(s).")
                for label, fp, b64 in frames:
                    raw_text, extracted = process_frame(
                        label, fp, b64, engine=engine, model_name=model_name
                    )
                    all_page_results.append({
                        "name": f"{orig_name} ({label})" if orig_name not in label else label,
                        "path": file_path,
                        "file_path": file_path,
                        "extracted": extracted,
                        "raw_text": raw_text
                    })

            def format_case_type_and_prefix(ctype_in: str) -> tuple[str, str]:
                c_upper = str(ctype_in or "LGC(G)").upper()
                if "(P)" in c_upper or " P " in f" {c_upper} " or c_upper.endswith("P") or "ಪಿ" in c_upper:
                    return "P", "L.G.C.(P)"
                elif "(T" in c_upper or "T-CRIM" in c_upper or "T-CIV" in c_upper or c_upper.endswith("T") or "ಟಿ" in c_upper:
                    return "T", "L.G.C.(T)"
                elif "(S)" in c_upper or c_upper.endswith("S") or "ಎಸ್" in c_upper:
                    return "S", "L.G.C.(S)"
                elif "RP" in c_upper:
                    return "RP", "RP"
                elif "MISC" in c_upper:
                    return "Misc", "Misc"
                else:
                    return "G", "L.G.C.(G)"

            # Format individual page results
            output_cases = []
            for p in all_page_results:
                ext = p["extracted"]
                cno_num = extract_case_number_only(ext.get("existing_case_no") or ext.get("case_no") or "")
                ctype = ext.get("case_type") or "LGC(G)"
                fyear = ext.get("filing_year") or 2024
                
                type_code, prefix = format_case_type_and_prefix(ctype)
                full_case_no = f"{prefix}.No.{cno_num}/{fyear}" if cno_num else f"{prefix}.No.New/{fyear}"

                # Take court hall number from file name per user rule
                ch_fn = extract_court_hall_from_filename(p.get("name", "")) or extract_court_hall_from_filename(p.get("file_path", ""))
                court_val = ch_fn or ext.get("court") or "Court Hall No.1"

                fn_details = extract_bundle_month_year_from_filename(p.get("name", "")) or extract_bundle_month_year_from_filename(p.get("file_path", ""))
                if fn_details:
                    if fn_details.get("courtHall"):
                        court_val = fn_details["courtHall"]
                    if fn_details.get("caseNo") and not cno_num:
                        cno_num = fn_details["caseNo"]
                    if fn_details.get("caseType") and not ext.get("case_type"):
                        type_code, prefix = format_case_type_and_prefix(fn_details["caseType"])
                    if fn_details.get("filingYear") and not ext.get("filing_year"):
                        fyear = fn_details["filingYear"]
                    full_case_no = f"{prefix}.No.{cno_num}/{fyear}" if cno_num else f"{prefix}.No.New/{fyear}"

                # Sub-stage and stage group extraction
                p_stage = ext.get("stage") or "Appearance of Respondent/Accused"
                p_stgroup = ext.get("stage_group") or STAGE_TO_GROUP.get(p_stage) or infer_stage_group_from_description(p_stage)

                # Fallback month and year from hearing date if not in filename
                month_val = fn_details.get("month", "")
                year_val = fn_details.get("year", "")
                my_val = fn_details.get("monthYear", "")
                if not my_val and ext.get("hearing_date"):
                    m_hd = re.search(r'((?:19|20)[0-9]{2})[-_ /.](0?[1-9]|1[0-2])', str(ext["hearing_date"]))
                    if m_hd:
                        year_val, month_val = m_hd.group(1), m_hd.group(2).zfill(2)
                        my_val = f"{month_val}-{year_val}"

                output_cases.append({
                    "name": p["name"],
                    "path": p.get("file_path", ""),
                    "file_path": p.get("file_path", ""),
                    "filename": Path(p.get("file_path", "")).name if p.get("file_path") else "",
                    "caseNo": str(cno_num),
                    "fullCaseNo": full_case_no,
                    "existing_case_no": str(cno_num),
                    "type": type_code,
                    "case_type": f"LGC({type_code})" if type_code in ("G", "P", "T", "S") else type_code,
                    "court": court_val,
                    "possession": ext.get("possession") or "N/A",
                    "bundleNo": fn_details.get("bundleNo", ""),
                    "bundle_number": fn_details.get("bundleNo", ""),
                    "month": month_val,
                    "year": year_val,
                    "monthYear": my_val,
                    "month_year": my_val,
                    "filedYear": int(fyear) if str(fyear).isdigit() else 2024,
                    "filing_year": int(fyear) if str(fyear).isdigit() else 2024,
                    "applicants": ext.get("applicants") or "",
                    "applicant_name": ext.get("applicant_name") or "",
                    "applicant_address": ext.get("applicant_address") or "",
                    "respondents": ext.get("respondents") or "",
                    "respondent_name": ext.get("respondent_name") or "",
                    "respondent_address": ext.get("respondent_address") or "",
                    "applicants_data": ext.get("applicants_data") or [],
                    "respondents_data": ext.get("respondents_data") or [],
                    "petitioners": ext.get("applicants_data") or [],
                    "currentStage": p_stage,
                    "stage": p_stage,
                    "sub_stage": p_stage,
                    "stageGroup": p_stgroup,
                    "stage_group": p_stgroup,
                    "restoration": ext.get("restoration") or "No",
                    "restorationOfLand": ext.get("restoration") or "No",
                    "nextHearing": ext.get("hearing_date") or "",
                    "hearing_date": ext.get("hearing_date") or "",
                    "landExtent": str(ext.get("extent") or ""),
                    "extent": str(ext.get("extent") or ""),
                    "extentUnit": ext.get("unit") or "Acre + Guntas",
                    "unit": ext.get("unit") or "Acre + Guntas",
                    "surveyNo": ext.get("survey_no") or "",
                    "survey_no": ext.get("survey_no") or "",
                    "district": ext.get("district") or "",
                    "taluk": ext.get("taluk") or "",
                    "hobli": ext.get("hobli") or "",
                    "village": ext.get("village") or "",
                    "totalPages": get_pdf_page_count(p.get("file_path", "")),
                    "raw_text": p["raw_text"]
                })

            # Group pages from the same document together into unified cases!
            grouped = group_extracted_pages(all_page_results)
            combined_cases = []
            for g in grouped:
                ext = g["extracted"]
                raw_full = " ".join(g.get("raw_texts", []))
                
                cno_num = extract_case_number_only(ext.get("existing_case_no") or ext.get("case_no") or "")
                ctype = ext.get("case_type") or "LGC(G)"
                fyear = ext.get("filing_year") or 2024
                type_code, prefix = format_case_type_and_prefix(ctype)
                full_case_no = f"{prefix}.No.{cno_num}/{fyear}" if cno_num else f"{prefix}.No.New/{fyear}"

                stage_val = ext.get("stage") or "Appearance of Respondent/Accused"
                stgroup_val = ext.get("stage_group") or STAGE_TO_GROUP.get(stage_val) or infer_stage_group_from_description(stage_val)

                # Take court hall number from file name per user rule
                ch_fn = extract_court_hall_from_filename(g.get("name", "")) or (extract_court_hall_from_filename(g["paths"][0]) if g.get("paths") else None)
                court_val = ch_fn or ext.get("court") or "Court Hall No.1"

                fn_details = extract_bundle_month_year_from_filename(g.get("name", "")) or (extract_bundle_month_year_from_filename(g["paths"][0]) if g.get("paths") else {})
                if fn_details:
                    if fn_details.get("courtHall"):
                        court_val = fn_details["courtHall"]
                    if fn_details.get("caseNo") and not cno_num:
                        cno_num = fn_details["caseNo"]
                    if fn_details.get("caseType") and not ext.get("case_type"):
                        type_code, prefix = format_case_type_and_prefix(fn_details["caseType"])
                    if fn_details.get("filingYear") and not ext.get("filing_year"):
                        fyear = fn_details["filingYear"]
                    full_case_no = f"{prefix}.No.{cno_num}/{fyear}" if cno_num else f"{prefix}.No.New/{fyear}"

                # Fallback month and year from hearing date if not in filename
                c_month_val = fn_details.get("month", "")
                c_year_val = fn_details.get("year", "")
                c_my_val = fn_details.get("monthYear", "")
                if not c_my_val and ext.get("hearing_date"):
                    m_hd = re.search(r'((?:19|20)[0-9]{2})[-_ /.](0?[1-9]|1[0-2])', str(ext["hearing_date"]))
                    if m_hd:
                        c_year_val, c_month_val = m_hd.group(1), m_hd.group(2).zfill(2)
                        c_my_val = f"{c_month_val}-{c_year_val}"

                c_path = g["paths"][0] if g.get("paths") else ""
                combined_cases.append({
                    "name": g.get("name") or "Combined Case",
                    "path": c_path,
                    "file_path": c_path,
                    "filename": Path(c_path).name if c_path else "",
                    "caseNo": str(cno_num),
                    "fullCaseNo": full_case_no,
                    "existing_case_no": str(cno_num),
                    "type": type_code,
                    "case_type": f"LGC({type_code})" if type_code in ("G", "P", "T", "S") else type_code,
                    "court": court_val,
                    "possession": ext.get("possession") or "N/A",
                    "bundleNo": fn_details.get("bundleNo", ""),
                    "bundle_number": fn_details.get("bundleNo", ""),
                    "month": c_month_val,
                    "year": c_year_val,
                    "monthYear": c_my_val,
                    "month_year": c_my_val,
                    "filedYear": int(fyear) if str(fyear).isdigit() else 2024,
                    "filing_year": int(fyear) if str(fyear).isdigit() else 2024,
                    "applicants": ext.get("applicants") or "",
                    "applicant_name": ext.get("applicant_name") or "",
                    "applicant_address": ext.get("applicant_address") or "",
                    "respondents": ext.get("respondents") or "",
                    "respondent_name": ext.get("respondent_name") or "",
                    "respondent_address": ext.get("respondent_address") or "",
                    "applicants_data": ext.get("applicants_data") or [],
                    "respondents_data": ext.get("respondents_data") or [],
                    "petitioners": ext.get("applicants_data") or [],
                    "currentStage": stage_val,
                    "stage": stage_val,
                    "sub_stage": stage_val,
                    "stageGroup": stgroup_val,
                    "stage_group": stgroup_val,
                    "restoration": ext.get("restoration") or "No",
                    "restorationOfLand": ext.get("restoration") or "No",
                    "nextHearing": ext.get("hearing_date") or "",
                    "hearing_date": ext.get("hearing_date") or "",
                    "landExtent": str(ext.get("extent") or ""),
                    "extent": str(ext.get("extent") or ""),
                    "extentUnit": ext.get("unit") or "Acre + Guntas",
                    "unit": ext.get("unit") or "Acre + Guntas",
                    "surveyNo": ext.get("survey_no") or "",
                    "survey_no": ext.get("survey_no") or "",
                    "district": ext.get("district") or "",
                    "taluk": ext.get("taluk") or "",
                    "hobli": ext.get("hobli") or "",
                    "village": ext.get("village") or "",
                    "totalPages": get_pdf_page_count(c_path),
                    "notes": f"Combined from {len(g.get('merged_pages', [1]))} pages."
                })

            # If multi-page document was combined, primary response is the unified cases!
            final_cases = combined_cases if len(combined_cases) < len(output_cases) else output_cases
            log_ocr(f"[/api/scan] Scan request completed successfully. Produced {len(final_cases)} case(s).")
            res = {
                "success": True,
                "cases": final_cases,
                "all_pages": output_cases,
                "combined": combined_cases,
                "logs": get_recent_logs(50)
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))

        except Exception as err:
            import traceback
            traceback.print_exc()
            log_ocr(f"[/api/scan] Fatal error in handle_scan: {err}", level="ERROR")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(err), "logs": get_recent_logs(20)}).encode("utf-8"))

class QuietThreadingServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        ex_type, ex_val, _ = sys.exc_info()
        if ex_type and (issubclass(ex_type, (ConnectionAbortedError, ConnectionResetError, BrokenPipeError)) or "10053" in str(ex_val) or "10054" in str(ex_val)):
            return
        super().handle_error(request, client_address)

def main():
    global ACTIVE_PORT
    init_db()
    QuietThreadingServer.allow_reuse_address = True
    preferred_port = PORT
    ports_to_try = [preferred_port]
    for p in (8000, 8001, 8080):
        if p not in ports_to_try:
            ports_to_try.append(p)

    server = None
    active_port = preferred_port
    for p in ports_to_try:
        try:
            # Bind all interfaces so Docker port publishing and LAN clients can reach the server.
            server = QuietThreadingServer(("0.0.0.0", p), CaseRequestHandler)
            active_port = p
            break
        except OSError:
            try:
                server = QuietThreadingServer(("0.0.0.0", p), CaseRequestHandler)
                active_port = p
                break
            except OSError:
                continue

    if server is None:
        try:
            server = QuietThreadingServer(("127.0.0.1", 0), CaseRequestHandler)
        except OSError:
            server = QuietThreadingServer(("0.0.0.0", 0), CaseRequestHandler)
        active_port = server.server_address[1]

    ACTIVE_PORT = active_port
    SERVER_READY_EVENT.set()

    print(f"Special Courts Server running at http://127.0.0.1:{active_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
