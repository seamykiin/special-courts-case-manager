#!/usr/bin/env python3
"""
Special Courts Case Management System — Local Server
Serves index.html with native CoreGraphics + Tesseract OCR + Ollama Vision integration.
"""

import os
import sys
import json
import base64
import io
import re
import shutil
import sqlite3
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
    NOTICE_TO_RESPONDENT_REGEX,
    extract_court_hall_from_filename,
    summarize_call_description_from_window,
    infer_stage_group_from_description
)

PORT = int(os.environ.get("PORT", 8000))

def get_pdf_folder_path() -> str:
    db_file = Path("pending_cases.db")
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
                
    db_file = Path("pending_cases.db")
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
                        score += 80
                    elif clean_no in fn:
                        score += 30
                    if year and str(year) in fn:
                        score += 20
                    if folder and (root == folder or str(root).startswith(str(folder))):
                        score += 100
                    if " (" in fn or "copy" in fn:
                        score -= 5
                    if score > 0:
                        candidates.append((score, os.path.join(root, f)))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_match = candidates[0][1]
        
        total_pages = 1
        res = render_document_page_png(best_match, 1, 1000)
        if res:
            total_pages = res[1]
        return best_match, total_pages

    return None, 0

class CaseRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
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

        if path == "/" or path == "":
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
        self.send_error(404, "Endpoint not found")

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
            res = {
                "found": True,
                "path": matched_file,
                "filename": os.path.basename(matched_file),
                "totalPages": total_pages,
                "folder": folder
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

    def handle_models(self):
        _, models = check_ollama_available()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps({"models": models or []}).encode("utf-8"))

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
                            temp_path = os.path.join("/tmp", fn)
                            with open(temp_path, "wb") as tf:
                                tf.write(content_part)
                            saved_files.append((fn, temp_path))

            elif "application/json" in content_type:
                data = json.loads(body.decode("utf-8"))
                engine = data.get("engine", "ocr")
                model_name = data.get("model", "qwen2.5vl:7b")
                files_data = data.get("files", [])
                for item in files_data:
                    fn = item.get("filename", "upload.jpg")
                    b64 = item.get("data", "")
                    if b64:
                        if "," in b64:
                            b64 = b64.split(",", 1)[1]
                        raw_bytes = base64.b64decode(b64)
                        temp_path = os.path.join("/tmp", fn)
                        with open(temp_path, "wb") as tf:
                            tf.write(raw_bytes)
                        saved_files.append((fn, temp_path))

            if not saved_files:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No files received"}).encode("utf-8"))
                return

            all_page_results = []
            for orig_name, file_path in saved_files:
                frames = extract_image_frames(file_path)
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

                # Sub-stage and stage group extraction
                p_stage = ext.get("stage") or ""
                p_stgroup = ext.get("stage_group") or ""
                if NOTICE_TO_RESPONDENT_REGEX.search(p_stage) or NOTICE_TO_RESPONDENT_REGEX.search(p.get("raw_text", "")):
                    p_stage = "Notice to Respondent"
                    p_stgroup = "Notice / Summons / Service"
                elif not p_stage or p_stage in ("Appearance of Accused", "Appearance of Respondent/Accused", "Hearing"):
                    p_desc, p_grp = summarize_call_description_from_window(p.get("raw_text", ""))
                    if p_desc:
                        p_stage = p_desc
                        p_stgroup = p_grp
                    else:
                        p_stage = p_stage or "Appearance of Respondent/Accused"
                        p_stgroup = p_stgroup or "Appearance"
                elif not p_stgroup:
                    p_stgroup = infer_stage_group_from_description(p_stage)

                output_cases.append({
                    "name": p["name"],
                    "caseNo": str(cno_num),
                    "fullCaseNo": full_case_no,
                    "existing_case_no": str(cno_num),
                    "type": type_code,
                    "case_type": f"LGC({type_code})" if type_code in ("G", "P", "T", "S") else type_code,
                    "court": court_val,
                    "filedYear": int(fyear) if str(fyear).isdigit() else 2024,
                    "filing_year": int(fyear) if str(fyear).isdigit() else 2024,
                    "applicants": ext.get("applicants") or "",
                    "respondents": ext.get("respondents") or "",
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

                stage_val = ext.get("stage") or ""
                stgroup_val = ext.get("stage_group") or ""

                # Priority Rule: If there is notice to respondent, take Notice to Respondent only!
                if NOTICE_TO_RESPONDENT_REGEX.search(stage_val) or NOTICE_TO_RESPONDENT_REGEX.search(raw_full):
                    stage_val = "Notice to Respondent"
                    stgroup_val = "Notice / Summons / Service"
                elif not stage_val or stage_val in ("Appearance of Accused", "Appearance of Respondent/Accused", "Hearing"):
                    # Check if a description can be created based on available sentences above next hearing date
                    desc, grp = summarize_call_description_from_window(raw_full)
                    if desc:
                        stage_val = desc
                        stgroup_val = grp
                    elif re.search(r'(?i)\b(?:for\s+)?hbc(?:\s+finally)?\b|\bhearing\s+before\s+charge\b', raw_full):
                        stage_val = "HBC"
                        stgroup_val = "HBC"
                    elif "witness summons" in raw_full.lower():
                        stage_val = "Summons to Witness"
                        stgroup_val = "Evidence"
                    else:
                        stage_val = stage_val or "Appearance of Respondent/Accused"
                        stgroup_val = stgroup_val or "Appearance"
                elif not stgroup_val:
                    stgroup_val = infer_stage_group_from_description(stage_val)

                # Take court hall number from file name per user rule
                ch_fn = extract_court_hall_from_filename(g.get("name", "")) or (extract_court_hall_from_filename(g["paths"][0]) if g.get("paths") else None)
                court_val = ch_fn or ext.get("court") or "Court Hall No.1"

                combined_cases.append({
                    "name": g.get("name") or "Combined Case",
                    "caseNo": str(cno_num),
                    "fullCaseNo": full_case_no,
                    "existing_case_no": str(cno_num),
                    "type": type_code,
                    "case_type": f"LGC({type_code})" if type_code in ("G", "P", "T", "S") else type_code,
                    "court": court_val,
                    "filedYear": int(fyear) if str(fyear).isdigit() else 2024,
                    "filing_year": int(fyear) if str(fyear).isdigit() else 2024,
                    "applicants": ext.get("applicants") or "",
                    "respondents": ext.get("respondents") or "",
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
                    "notes": f"Combined from {len(g.get('merged_pages', [1]))} pages."
                })

            # If multi-page document was combined, primary response is the unified cases!
            res = {
                "success": True,
                "cases": combined_cases if len(combined_cases) < len(output_cases) else output_cases,
                "all_pages": output_cases,
                "combined": combined_cases
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))

        except Exception as err:
            import traceback
            traceback.print_exc()
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(err)}).encode("utf-8"))

def main():
    ThreadingHTTPServer.allow_reuse_address = True
    preferred_port = PORT
    ports_to_try = [preferred_port]
    for p in (8000, 8001, 8080):
        if p not in ports_to_try:
            ports_to_try.append(p)

    server = None
    active_port = preferred_port
    for p in ports_to_try:
        try:
            server = ThreadingHTTPServer(("0.0.0.0", p), CaseRequestHandler)
            active_port = p
            break
        except OSError:
            continue

    if server is None:
        server = ThreadingHTTPServer(("0.0.0.0", 0), CaseRequestHandler)
        active_port = server.server_address[1]

    print(f"Special Courts Server running at http://localhost:{active_port}")
    print(f"Open http://localhost:{active_port} in your browser.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()
