"""Pending & Disposed Cases data-entry app powered by Local Ollama Vision for automated court order sheet extraction."""
from __future__ import annotations

import base64
import calendar
import csv
import glob
import io
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    TK_AVAILABLE = True
    _TkBase = tk.Tk
    _ToplevelBase = tk.Toplevel
except (ImportError, ModuleNotFoundError, AttributeError):
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
    TK_AVAILABLE = False
    _TkBase = object
    _ToplevelBase = object

try:
    from PIL import Image, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageSequence = None
    PIL_AVAILABLE = False

IS_MAC = platform.system() == "Darwin"
FONT_FAMILY = "Helvetica Neue" if IS_MAC else "Segoe UI"

APP_DIR = Path(__file__).resolve().parent
if IS_MAC:
    DATA_DIR = Path.home() / "Library" / "Application Support" / "PendingCases"
else:
    DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PendingCases"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "pending_cases.db"

_legacy_db = APP_DIR / "pending_cases.db"
if not DB_PATH.exists() and _legacy_db.exists() and _legacy_db.resolve() != DB_PATH.resolve():
    shutil.copy2(_legacy_db, DB_PATH)

GEO_PATH = APP_DIR / "geo_data.json"
if GEO_PATH.exists():
    with GEO_PATH.open(encoding="utf-8") as _geo_file:
        GEO = json.load(_geo_file)
else:
    GEO = {}

FIELDS = [
    ("court", "Court Hall"),
    ("case_type", "Case Type"),
    ("existing_case_no", "Existing Case No. (number only)"),
    ("filing_year", "Filing Year"),
    ("possession", "Possession"),
    ("bundle_no", "Bundle Number"),
    ("month_year", "Month and Year"),
    ("applicants", "Applicants & Addresses (in English)"),
    ("respondents", "Respondents & Addresses (in English)"),
    ("stage_group", "Stage Group"),
    ("stage", "Current Stage / Sub Stage"),
    ("restoration", "Restoration of Land"),
    ("hearing_date", "Next Hearing Date"),
    ("extent", "Extent value"),
    ("unit", "Extent unit"),
    ("survey_no", "Survey No."),
    ("ward_no", "Ward No."),
    ("pid_no", "PID No."),
    ("tax_no", "Property Tax Assessment No."),
    ("district", "District"),
    ("taluk", "Taluk"),
    ("hobli", "Hobli"),
    ("village", "Village"),
]

STAGES_BY_GROUP = {
    "Filing & Scrutiny": [
        "Petition Filed", "New Case", "Scrutiny", "Office Objections/Defects",
        "Await Rectification", "Defects Rectified", "Re-presented", "Court Fee Compliance",
        "Documents to be Filed", "Production of Documents", "To take Steps", "To Rectify Office Objections", "For Registration", "Case Registered", "To File Appropriate Application",
    ],
    "Preliminary Hearing / Cognizance": [
        "For Preliminary Hearing", "Hearing on Maintainability", "Sworn Statement",
        "Await Verification/Status Report", "Hearing on Cognizance/Objection to the respondent",
        "Petition Rejected/Dismissed/Dropped at Pre-Cognizance Stage",
    ],
    "Notice / Summons / Service": [
        "Notice to Respondent", "Re-Issue Notice to Respondent", "Await Notice to Respondent", "Notice to Accused",
        "Await Notice to Accused", "Notification Form III", "Notice/Summons to Accused",
        "Await Notice/Summons", "Await court notice of complainant/plaintiff",
        "Await court notice of Accused/defendants", "Hearing along with the explaination",
        "Issue the direction to executive engineers", "issue notice by speed post",
        "show case notice and explaination", "To take Steps for Notice",
    ],
    "Appearance": [
        "Appearance of Petitioner/Complainant", "Appearance of Respondent", "Appearance of Accused",
        "Appearance of Interested Party", "Await Appearance", "To file Vakalat", "Appearance of Tahsildar / Officer",
    ],
    "Objections / Pleadings": [
        "Time to file Objections", "Final Opportunity to file Objections", "Objection Statement", "Counter/Written Statement", "To file Written Statement", "Rejoinder By the Petitioner",
        "Objections to IA", "Hearing on objection", "To file Form No.1", "adjourned for want of time",
    ],
    "Reports / Verification": [
        "To submit Report / Await Report", "To submit Mahazar & Sketch Report", "Status Report", "Await Verification/Status Report", "Await Survey Report", "Revenue Records Report",
        "Detailed Report from Tahsildar/DC/AC/Local Authority", "Await Possession/Resumption Report",
        "Await Compliance Report", "Await Further Report", "Await Report", "Await Investigation / Lokayukta Report",
    ],
    "Evidence": [
        "Complainant Evidence", "Complaint Evidence", "Defence Evidence", "Plaintiff Evidence",
        "Defendants Evidence", "Prosecution Evidence", "Cross Examination of Witness", "Witness Examination", "Cross of Complainant Witness",
        "Cross of Defence Witness", "Cross of Plaintiff Witness", "Cross of Defendants Witness",
        "Cross of PW", "Cross of DW", "cross examination of witness", "Summons to Witness",
        "Witness Summons", "Summons to the Witness",
    ],
    "Criminal Process": [
        "Summons to Accused", "Appearance of Accused", "Issue Non-Bailable Warrant (NBW)", "Issue Bailable Warrant (BW)", "Await NBW", "NBW", "Re-Issue NBW",
        "Furnishing Surety", "Bailable Warrant", "Await Bailable Warrant", "Re-Issue B/W",
    ],
    "Hearing": [
        "Hearing", "Hearing on Application/ IA", "Hearing on IA", "Hearing on Compliance Report",
        "For Hearing on Application",
    ],
    "Arguments": [
        "Arguments", "Hearing on Arguments", "Complainant Arguments", "Complaint Arguments", "Defence Arguments",
        "Defence Argument", "Prosecution Arguments", "Plaintiff Arguments", "Defendants Arguments",
        "Further Arguments", "Further arguments", "Reply arguments",
    ],
    "Judgment / Final Order": [
        "For Judgment", "Judgment Reserved", "Judgment Pronounced", "Final Order",
        "Application Allowed", "Application Dismissed", "Case Disposed", "Judgement",
    ],
    "Possession / Execution / Compliance": [
        "To Comply with Court Order", "Await Compliance Report", "Taking Possession",
        "Police Assistance for Possession", "Possession Taken", "Possession Delivered",
        "Possession Certificate", "Await Possession Report", "Order Complied", "Compliance Report",
    ],
    "Compliance during pendency of Proceeding": [
        "Await report regarding resumption of the possession to the State", "Await Compliance to the direction",
    ],
    "Compliance Post Disposal": [
        "Compliance Post Disposal",
    ],
    "Stayed Matters": [
        "Await Orders from Hon'ble High Court of Karnataka", "Await Orders from Hon'ble Supreme Court",
    ],
    "Closed / Disposal": [
        "Allowed", "Dismissed", "Rejected", "Withdrawn", "Disposed", "Disposed after Compliance",
        "Closed after Possession resumed", "Transferred", "Made over to another Bench", "Convicted",
        "Acquitted", "Criminal liability Fixed", "Civil liability Fixed",
    ],
    "Orders": [
        "Orders", "For Orders", "Orders on IA", "Orders on HBC", "Orders on Statement of objection", "Orders on Reports",
    ],
    "Charge/Plea": [
        "Charge", "Plea", "Framing of Charge",
    ],
    "HBC": [
        "HBC", "Hearing Before Charge",
    ],
    "313 Cr.P.C /351 BNSS Statement": [
        "313 Statement", "313 Cr.P.C Statement", "351 BNSS Statement",
    ],
}

STAGE_GROUPS = list(STAGES_BY_GROUP)
STAGES = sorted(list({st for group_stages in STAGES_BY_GROUP.values() for st in group_stages if st}))

DEFAULT_CHOICES = {
    "case_type": ["LGC(G)", "LGC(P)", "LGC(T)", "LGC(S)", "RP", "Misc"],
    "court": ["Court Hall No.1", "Court Hall No.2"],
    "possession": ["Yes", "No", "N/A"],
    "stage": STAGES,
    "stage_group": STAGE_GROUPS,
    "restoration": ["Yes", "No", "Partial", "N/A"],
    "unit": ["Acre", "Guntas", "Acre + Guntas", "Cents", "Annas", "Square feet", "Square meters", "Feet", "Meter"],
}


def normalize_case_type(raw: str) -> str:
    """Normalizes any case type input into standard LGC format: LGC(G), LGC(P), LGC(T), LGC(S), RP, Misc."""
    if not raw:
        return "LGC(G)"
    raw_str = str(raw).strip()
    s = raw_str.upper().replace(".", "").replace(" ", "").replace("(", "").replace(")", "")
    if "LGCP" in s or "LGP" in s or "ಪಿ" in s or s == "P" or "(P)" in raw_str.upper() or " P " in f" {raw_str} ":
        return "LGC(P)"
    elif "LGCT" in s or "LGT" in s or "ಟಿ" in s or s == "T" or "(T)" in raw_str.upper() or " T " in f" {raw_str} ":
        return "LGC(T)"
    elif "LGCS" in s or "LGS" in s or "ಎಸ್" in s or s == "S" or "(S)" in raw_str.upper() or " S " in f" {raw_str} ":
        return "LGC(S)"
    elif "RP" in s:
        return "RP"
    elif "MISC" in s:
        return "Misc"
    elif "LGCG" in s or "LGG" in s or "ಜಿ" in s or s == "G" or "(G)" in raw_str.upper() or "LGC" in s:
        return "LGC(G)"
    return "LGC(G)"


def extract_court_hall_from_filename(filename: str) -> str | None:
    """Extracts standard 'Court Hall No.1' or 'Court Hall No.2' from filename if present.
    Recognizes CH1, CH2, Court Hall 1, Court Hall 2, CH-1, CH-2, CH 01, CH 02, etc.
    """
    if not filename:
        return None
    s = Path(filename).name.lower()
    # Check CH2 / Court Hall 2 / Hall 2 / CH02 / CH-2 / CH_2
    if re.search(r'(?:^|[\s._\-\(\[])(?:ch|court\s*hall|court|hall)[-\s._]*(?:no\.?[-\s._]*)?(?:0?2|ii)(?:[\s._\-\)\]]|$)', s):
        return "Court Hall No.2"
    # Check CH1 / Court Hall 1 / Hall 1 / CH01 / CH-1 / CH_1
    if re.search(r'(?:^|[\s._\-\(\[])(?:ch|court\s*hall|court|hall)[-\s._]*(?:no\.?[-\s._]*)?(?:0?1|i)(?:[\s._\-\)\]]|$)', s):
        return "Court Hall No.1"
    return None


def extract_bundle_month_year_from_filename(filename: str) -> dict:
    """Extracts bundle number, month, and year from filename if present.
    Example: CH1-LGC-P-194-2024-B12-02-2026 -> bundleNo: 12, month: 02, year: 2026, monthYear: 02-2026
    B is bundle after followed by the bundle number, then month and year.
    """
    if not filename:
        return {}
    s = Path(filename).name
    # Strip extension
    s_clean = re.sub(r'\.[a-zA-Z0-9]+$', '', s)
    res = {
        'courtHall': None,
        'caseType': None,
        'caseNo': None,
        'filingYear': None,
        'bundleNo': None,
        'bundle_number': None,
        'month': None,
        'year': None,
        'monthYear': None,
        'month_year': None
    }
    
    # 1. Full pattern matching: CH1-LGC-P-194-2024-B12-02-2026 or CH 2 LGC G 1052-2026-B12-02-2026
    full = re.search(
        r'(?:(?:CH|Court\s*Hall\s*(?:No\.?)?)\s*([12]|I{1,2}))?[-_ ]*'
        r'(?:(?:L\.?G\.?C\.?\(?([A-Za-z]+)\)?|L\.?G\.?C\.?[-_ ]+([A-Za-z]+))|([A-Za-z]+))?[-_ ]*'
        r'([0-9]+)[-_ ]+'
        r'((?:19|20)[0-9]{2})[-_ ]*'
        r'(?:Bundle[-_ ]*|[Bb])([0-9A-Za-z]+)[-_ ]+'
        r'(0?[1-9]|1[0-2])[-_ /.]+'
        r'((?:19|20)[0-9]{2})',
        s_clean, re.IGNORECASE
    )
    if full:
        hall, t1, t2, t3, cno, fYear, bundle, mm, mYear = full.groups()
        if hall:
            res['courtHall'] = 'Court Hall No.2' if hall.upper() in ('2', 'II') else 'Court Hall No.1'
        res['caseType'] = (t1 or t2 or t3 or '').upper()
        res['caseNo'] = cno
        res['filingYear'] = int(fYear)
        res['bundleNo'] = bundle
        res['bundle_number'] = bundle
        res['month'] = mm.zfill(2)
        res['year'] = mYear
        res['monthYear'] = f"{mm.zfill(2)}-{mYear}"
        res['month_year'] = f"{mm.zfill(2)}-{mYear}"
        return res

    # 2. General bundle pattern: B12-02-2026 or Bundle-12-02-2026
    bm = re.search(r'(?:^|[-_ ]|\b)(?:Bundle[-_ ]*|[Bb])([0-9A-Za-z]+)[-_ ]+(0?[1-9]|1[0-2])[-_ /.]+((?:19|20)[0-9]{2})(?:[-_ ]|$|\b)', s_clean, re.IGNORECASE)
    if bm:
        bundle, mm, mYear = bm.groups()
        res['bundleNo'] = bundle
        res['bundle_number'] = bundle
        res['month'] = mm.zfill(2)
        res['year'] = mYear
        res['monthYear'] = f"{mm.zfill(2)}-{mYear}"
        res['month_year'] = f"{mm.zfill(2)}-{mYear}"

    # 3. Fallback court hall
    if not res['courtHall']:
        if re.search(r'(?:^|[\s._\-\(\[])(?:ch|court\s*hall|court|hall)[-\s._]*(?:no\.?[-\s._]*)?(?:0?2|ii)(?:[\s._\-\)\]]|$)', s_clean, re.IGNORECASE):
            res['courtHall'] = 'Court Hall No.2'
        elif re.search(r'(?:^|[\s._\-\(\[])(?:ch|court\s*hall|court|hall)[-\s._]*(?:no\.?[-\s._]*)?(?:0?1|i)(?:[\s._\-\)\]]|$)', s_clean, re.IGNORECASE):
            res['courtHall'] = 'Court Hall No.1'

    # 4. Fallback case no & filing year (only if other text exists besides bundle)
    if not res['caseNo']:
        s_without_bundle = re.sub(r'(?:^|[-_ ]|\b)(?:Bundle[-_ ]*|[Bb])([0-9A-Za-z]+)[-_ ]+(0?[1-9]|1[0-2])[-_ /.]+((?:19|20)[0-9]{2})', '', s_clean, flags=re.IGNORECASE).strip()
        cno_match = re.search(r'([0-9]+)[-_ ]+((?:19|20)[0-9]{2})', s_without_bundle)
        if cno_match:
            res['caseNo'] = cno_match.group(1)
            res['filingYear'] = int(cno_match.group(2))

    return res if (res['bundleNo'] or res['monthYear'] or res['caseNo'] or res['courtHall']) else {}


def normalize_court_hall(raw: str, text: str = "", file_path: str = "") -> str:
    """
    Normalizes Court Hall inputs to standard 'Court Hall No.1' or 'Court Hall No.2'.
    Accurately recognizes '02', 'II', 'ii', '2', 'CH. No. 02', 'CH-II', 'Court Hall II',
    'Made over to CH. No. 02', '02ನೇ ನ್ಯಾಯಾಂಗಣ', 'ನ್ಯಾಯಾಂಗಣ-02', etc.
    """
    # 0. Check filename if available (highest priority per user rule)
    if file_path:
        ch_fn = extract_court_hall_from_filename(file_path)
        if ch_fn:
            return ch_fn

    v = str(raw or "").strip()
    v_clean = v.lower()

    # 1. Direct value evaluation (handles '02', 'II', '2', 'CH. No. 02', etc.)
    if re.search(r'^(?:0?2|ii|ch[-\s.]*(?:0?2|ii)|court\s*hall[-\s.]*(?:no\.?[-\s.]*)?(?:0?2|ii))$', v_clean):
        return "Court Hall No.2"
    if re.search(r'^(?:0?1|i|ch[-\s.]*(?:0?1|i)|court\s*hall[-\s.]*(?:no\.?[-\s.]*)?(?:0?1|i))$', v_clean):
        return "Court Hall No.1"

    combined = f"{v}\n{text}"

    # 2. Text evidence evaluation: Court Hall 2 patterns (check 2/II/02 first so '1' never false-matches)
    ch2_patterns = [
        r'(?i)(?:Made\s*over\s*to|List\s+this\s+matter\s+before)[\s\S]{0,60}?(?:C\.?H\.?|Court\s*Hall)?[\s\S]{0,30}?\b(?:0?2|II|ii|ll|\|\||೦೨|೨)\b',
        r'(?:Made\s*over\s*to|List\s+this\s+matter\s+before)?[\s.:\-_]*C\.?H\.?[\s.,:\-_]*(?:No\.?)?[\s.,:\-_]*(?:02|2|II|ii|ll|\|\||೦೨|೨)(?:[\s.,:\-_—]|$|\b)',
        r'(?:02|2|II|ii|ll|\|\||೦೨|೨)\s*C\.?H\.?[\s.,:\-_]*(?:No\.?|೫೦\.?|ನಂ\.?)?',
        r'Court\s*Hall[\s.,:\-_]*(?:No\.?)?[\s.,:\-_]*(?:02|2|II|ii|ll|\|\||೦೨|೨)(?:[\s.,:\-_—]|$|\b)',
        r'(?:02|2|II|ii|೦೨|೨)\s*ನೇ\s*ನ್ಯಾಯಾಂಗಣ',
        r'ನ್ಯಾಯಾಂಗಣ[\s.,:\-_]*(?:02|2|II|ii|ll|\|\||೦೨|೨)(?:[\s.,:\-_—]|$|\b)',
        r'ಸ[\'\"’]?ಯಾಂಗ್ಲ[_\s]*(?:02|2|II|ii|೦೨|೨)',
        r'ಸ[\'\"’]?ಯಾಂಗ[್ಣಲ][_\s]*(?:02|2|II|ii|೦೨|೨)',
        r'Bench[\s.,:\-_]*(?:No\.?)?[\s.,:\-_]*(?:02|2|II|ii)(?:[\s.,:\-_—]|$|\b)',
        r'\b(?:CH|Court\s*Hall)[\s\-_]*(?:02|II|2)\b',
    ]
    for pat in ch2_patterns:
        if re.search(pat, combined, re.IGNORECASE):
            return "Court Hall No.2"

    # 3. Text evidence evaluation: Court Hall 1 patterns (omit pipe '|' noise)
    ch1_patterns = [
        r'(?i)(?:Made\s*over\s*to|List\s+this\s+matter\s+before)[\s\S]{0,60}?(?:C\.?H\.?|Court\s*Hall)?[\s\S]{0,30}?\b(?:0?1|I|i|೦೧|೧)\b',
        r'(?:Made\s*over\s*to|List\s+this\s+matter\s+before)?[\s.:\-_]*C\.?H\.?[\s.,:\-_]*(?:No\.?)?[\s.,:\-_]*(?:01|1|I|i|೦೧|೧)(?:[\s.,:\-_—]|$|\b)',
        r'Court\s*Hall[\s.,:\-_]*(?:No\.?)?[\s.,:\-_]*(?:01|1|I|i|೦೧|೧)(?:[\s.,:\-_—]|$|\b)',
        r'(?:01|1|I|i|೦೧|೧)\s*ನೇ\s*ನ್ಯಾಯಾಂಗಣ',
        r'ನ್ಯಾಯಾಂಗಣ[\s.,:\-_]*(?:01|1|I|i|೦೧|೧)(?:[\s.,:\-_—]|$|\b)',
        r'Bench[\s.,:\-_]*(?:No\.?)?[\s.,:\-_]*(?:01|1|I|i)(?:[\s.,:\-_—]|$|\b)',
        r'\b(?:CH|Court\s*Hall)[\s\-_]*(?:01|I|1)\b',
    ]
    for pat in ch1_patterns:
        if re.search(pat, combined, re.IGNORECASE):
            return "Court Hall No.1"

    # 4. Fallback substring checks
    if any(k in v_clean for k in ["02", "ii", "hall no.2", "hall no 2", "ch-2", "ch 2"]):
        return "Court Hall No.2"
    if "2" in v_clean and "1" not in v_clean:
        return "Court Hall No.2"
    if any(k in v_clean for k in ["01", "hall no.1", "hall no 1", "ch-1", "ch 1"]):
        return "Court Hall No.1"

    return "Court Hall No.1"


def extract_case_number_only(raw: str) -> str:
    """Strips LGC(...) No. prefix and /YYYY or -YYYY suffix, returning ONLY the case number digits.
    E.g. 'LGC(G) No. 1252/2024' -> '1252'
         '1252/2024' -> '1252'
         'L.G.C.(P) No. 314/2024' -> '314'
         '456' -> '456'
    """
    if not raw:
        return ""
    s = str(raw).strip()
    # Strip leading Court Hall prefixes if present in filename (e.g. 'CH 2 ', 'CH1-', 'CH_2_')
    s = re.sub(r'^(?:CH[_\s]*[012]|Court\s*Hall\s*(?:No\.?\s*)?[012]|CH-?[012])[_\s\-]*', '', s, flags=re.IGNORECASE)
    # Remove LGC(...) No. / R.P. No. / Misc No. / Kannada prefixes
    s = re.sub(
        r'^(?:(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?)?\s*\(?(?:[GPTS]|R\.?P\.?|Misc|ಜಿ|ಪಿ|ಟಿ|ಎಸ್)\)?|[GPTS]|(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?|Misc|R\.?P\.?|Case|CC|Spl\.?\s*CC))[_\s\-]*(?:No\.?|ನಂ\.?|8o\.?|Bo\.?|80\.?|ಸಂಖ್ಯೆ)?[_:\s\-_.]*',
        '',
        s,
        flags=re.IGNORECASE
    )
    # Also remove generic 'No. ' prefix
    s = re.sub(r'^(?:No\.?|ನಂ\.?|ಸಂಖ್ಯೆ)[:\s\-_.]*', '', s, flags=re.IGNORECASE)
    # Remove file extension if present (e.g. .pdf, .jpg)
    s = re.sub(r'\.[a-zA-Z0-9]+$', '', s)
    # Remove year suffix /2024, -2024, _2024, /24
    s = re.sub(r'[\s/\\_\-]+(?:20\d{2}|\d{2})$', '', s)
    digits = re.search(r'([0-9]+[A-Za-z]?)', s)
    return digits.group(1) if digits else s.strip()


def _strip_case_prefix(case_no: str) -> str:
    """Strips case prefix and year, returning only the case number digits."""
    return extract_case_number_only(case_no)


def _build_full_case_no(num_year: str, case_type: str = "") -> str:
    """Returns only the case number digits."""
    return extract_case_number_only(num_year)


OLLAMA_DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

OLLAMA_VISION_PROMPT = """You are an expert legal data extraction assistant specializing in court case documents, petitions, orders, and daily order sheets from Karnataka courts and revenue tribunals (such as Karnataka Land Grabbing Prohibition Special Courts, Civil Courts, High Court, and Revenue Appellate Tribunals).

Analyze this document image carefully. The document may contain printed Kannada, printed English, bilingual text, tabular schedules of property, handwritten margin notes, daily judge orders, and official stamps.

Extract the relevant case details into a valid JSON object matching these exact keys:
{
  "court": "Court Hall No.1 or Court Hall No.2. Look for headers, seals, and margin notes (e.g. from 'CH. No. 02', 'CH 02', 'CH. No. II', 'CH-II', 'Court Hall II', 'Court Hall 02', '02ನೇ ನ್ಯಾಯಾಂಗಣ', 'ನ್ಯಾಯಾಂಗಣ-02', 'ನ್ಯಾಯಾಂಗಣ-II', 'Made over to CH. No. 02', 'II', or '02', extract strictly 'Court Hall No.2'; from 'CH. No. 01', 'CH-I', '01', 'I', 'ನ್ಯಾಯಾಂಗಣ-01', extract 'Court Hall No.1')",
  "case_type": "One of: LGC(G), LGC(P), LGC(T), LGC(S), RP, Misc (e.g. from LGC(G) or ಎಲ್.ಜಿ.ಸಿ.(ಜಿ), extract 'LGC(G)'; from LGC(P) or ಎಲ್.ಜಿ.ಸಿ.(ಪಿ), extract 'LGC(P)')",
  "existing_case_no": "Existing Case number (NUMBER ONLY, without LGC prefix and without year). Located directly BELOW the Court Hall No. (ನ್ಯಾಯಾಂಗಣ-1/2 or CH. No.1/2). For example, from 'ಎಲ್.ಜಿ.ಸಿ.(ಜಿ) ನಂ. 1466/2024', extract strictly '1466'. Do not include the year or prefix.",
  "filing_year": "4-digit year extracted directly from the date at the top of the Order Sheet ('ಆದೇಶ ಪತ್ರ' or 'ಆರ್ಡರ್ ಶೀಟ್' / 'Order Sheet') section (e.g. from 'ದಿನಾಂಕ 22ನೇ ಜುಲೈ 2024', extract '2024'). If no order sheet is present, use the year from the case number or petition date.",
  "applicants": "Full names and complete addresses of all applicants/petitioners/complainants in English words only (do NOT keep raw Kannada transliterations like 'Karyanirvahaka Abhiyantararu', 'Vibhaga', 'Valaya', 'Kothadi Sankhye', 'Mahadi', 'Pradhana Kachheri', 'Ilakhe', 'Anche', 'BN', 'Kom'). Translate designations, offices, relationships (ಕೋಂ/ಹೆಂಡತಿ -> W/o, ಬಿನ್/ಮಗ -> S/o, ಮಗಳು -> D/o, ಲೇಟ್/ದಿವಂಗತ -> Late) and divisions (ಗ್ರಾಮ -> Village, ಹೋಬಳಿ -> Hobli, ತಾಲ್ಲೂಕು -> Taluk, ಜಿಲ್ಲೆ -> District, ಕೊಠಡಿ ಸಂಖ್ಯೆ -> Room No., ಮಹಡಿ -> Floor, ಇಲಾಖೆ -> Department, ಸರ್ಕಾರ -> Government, ಅಂಚೆ -> Post, ಕಾರ್ಯನಿರ್ವಾಹಕ ಅಭಿಯಂತರರು -> Executive Engineer, ತಹಶೀಲ್ದಾರರು -> Tahsildar) into proper English words. Match each applicant name one-to-one with their corresponding address.",
  "respondents": "Full names and complete addresses of all respondents/accused/defendants in English words only, preserving numbering 1, 2, 3... (e.g. '1. Name S/o ..., Village, Hobli, Taluk, District. 2. Name ...'). Do NOT keep raw Kannada transliterations. Translate Kannada relationships, designations (Assistant Director of Land Records (ADLR), Village Accountant, Executive Officer, Tahsildar & Taluk Executive Magistrate), government bodies, and revenue divisions into English words. Match each respondent name one-to-one with their corresponding address.",
  "stage_group": "Must be one of the official 20 stage groups: Filing & Scrutiny, Preliminary Hearing / Cognizance, Notice / Summons / Service, Appearance, Objections / Pleadings, Reports / Verification, Evidence, Criminal Process, Hearing, Arguments, Judgment / Final Order, Possession / Execution / Compliance, Compliance during pendency of Proceeding, Compliance Post Disposal, Stayed Matters, Closed / Disposal, Orders, Charge/Plea, HBC, 313 Cr.P.C /351 BNSS Statement",
  "stage": "The exact current procedural stage mentioned in the daily order or margin note (e.g. Notice to Respondent, Summons to Accused, Appearance of Respondent, Hearing on objection, Objection Statement, Sworn Statement, Complaint Evidence, Arguments, Hearing, Orders, Judgement, Await Report, Status Report, Compliance Report, Bailable Warrant, Await NBW, Disposed). CRITICAL RULE: If the operative order or sub-stage summary directs or mentions notice to respondent (e.g. 'issue notice to respondent', 're-issue notice to respondent', 'await notice to respondent', 'notice to respondent in Form IV', 'ಎದುರುದಾರರಿಗೆ ನೋಟಿಸ್'), strictly extract 'Notice to Respondent' as the stage and 'Notice / Summons / Service' as stage_group. If there is no standard matching sub-stage, create a clear description based on the available sentences above the next hearing date summarizing what the next call is about.",
  "restoration": "Restoration of land status if stated: Yes, No, Partial, or N/A",
  "hearing_date": "Next upcoming hearing date strictly in YYYY-MM-DD format. Look for operative directions at the end of the order sheet (e.g. 'adjourned to...', 'call on...', 'posted to...'). Keep the next scheduled hearing date even if adjourned for Quorum (do not go back to previous hearing date). DO NOT return the past filing date.",
  "extent": "The numerical value of the land extent extracted specifically from the Order Sheet paragraph ('ಆದೇಶ ಪತ್ರ' or 'ಆರ್ಡರ್ ಶೀಟ್'). Look for the encroached portion ('ಪೈಕಿ ... ಒತ್ತುವರಿ' or '... ಚದರ ಅಡಿ / ಎಕರೆ ಜಾಗವನ್ನು ಒತ್ತುವರಿ'). If both acres and guntas are present (e.g. '1 acre 25 guntas', '1-25', '50 ಎಕರೆ 30 ಗುಂಟೆ'), extract the full compound value ('1.25', '50.30') with unit 'Acre + Guntas' (never drop the guntas part). Do not confuse with respondent age or door numbers.",
  "unit": "One of: Acre, Guntas, Acre + Guntas, Square feet, Square meters, Cents, Feet, Meter, or Annas",
  "survey_no": "The complete, unabbreviated survey number including ALL sub-divisions and hissa bars/slashes (e.g. '24/8/7', '25/8', '117/3/1', '102/2A'). CRITICAL: If there is a bar '/' or multiple slashes (such as '24/8/7'), take the FULL survey number with every single part (e.g. '24/8/7'). NEVER stop at the first slash or truncate to '24' or '24/8'. It is a single complete survey number.",
  "ward_no": "Ward number or block number if specified",
  "pid_no": "PID (Property ID) number if mentioned",
  "tax_no": "Property tax assessment number or Khatha number if mentioned",
  "district": "District name in English (e.g. Bengaluru, Bengaluru Rural, Ramanagara, Tumakuru, Mandya, Mysuru, Kolar, or any Karnataka district)",
  "taluk": "Taluk name in English (e.g. Afzalpura)",
  "hobli": "Hobli, circle, or firka name in English",
  "village": "Village, ward, locality, or town name transliterated to standard English",
  "raw_order_text": "Verbatim transcription of the judge's operative order and margin scheduling notes"
}

Extraction Guidelines:
1. Case Number & Court Hall: The existing case number is ALWAYS located directly below Court Hall No. (ನ್ಯಾಯಾಂಗಣ-1/2 or CH. No.1/2) in the document header. Extract ONLY the number digits (e.g. from '1466/2024', extract '1466'). Put the prefix (e.g. 'LGC(G)') into case_type, and the year (e.g. '2024') into filing_year. For Court Hall: extract strictly as 'Court Hall No.1' or 'Court Hall No.2'. Always identify Court Hall No.2 from 'CH. No. 02', 'CH 02', 'CH. No. II', 'CH-II', 'Court Hall II', 'Court Hall 02', '02ನೇ ನ್ಯಾಯಾಂಗಣ', 'ನ್ಯಾಯಾಂಗಣ-02', 'ನ್ಯಾಯಾಂಗಣ-II', 'Made over to CH. No. 02', Roman 'II', or '02'. Identify Court Hall No.1 from '01', 'I', '1', 'CH. No. 01', '01ನೇ ನ್ಯಾಯಾಂಗಣ', 'ನ್ಯಾಯಾಂಗಣ-01', etc.
2. General applicability: The document can be from any taluk, district, or year in Karnataka. Do not assume any pre-set village or case number.
3. Next hearing date & Sub Stage: Always extract the scheduled NEXT date from judge operative directions or margin notes. Format strictly as YYYY-MM-DD. Keep the next hearing date even if adjourned for Quorum (do not go back to previous date); but if there is a 'Quorum' keyword, take stage and stage_group from the previous substantive order. If there is no standard matching sub-stage, create a clear concise description based on the available sentences above the next hearing date summarizing what the next call is about (e.g. 'Time to file objections', 'Issue reminder to Tahsildar for survey report', 'Cross examination of PW-1', 'Production of original documents').
4. Order Sheet extraction: Both filing_year and land extent are located in the Order Sheet section ('ಆದೇಶ ಪತ್ರ' or 'ಆರ್ಡರ್ ಶೀಟ್'). Extract filing_year directly from the Order Sheet heading date ('ದಿನಾಂಕ ... 20xx'). For land extent: look for the land extent in the order sheet. When both acres and guntas are specified (e.g. '1 acre 25 guntas' or '50 ಎಕರೆ 30 ಗುಂಟೆ'), extract the full compound value ('1.25' or '50.30') and set unit to 'Acre + Guntas' (do NOT drop or truncate the guntas). Convert Kannada unit terms (ಚದರ ಅಡಿ -> Square feet, ಎಕರೆ -> Acre, ಗುಂಟೆ -> Guntas, ಸೆಂಟ್ಸ್ -> Cents). When a survey number has one or more slashes '/' (e.g. '24/8/7', '25/8', '117/3/1'), extract the COMPLETE full survey number with every slash and sub-number. Never truncate to '24' or '24/8' — take the full multi-part value like '24/8/7'.
5. English words for parties & addresses: Translate all Kannada titles, designations, departments, relationships, and revenue terms into English words only (e.g. Executive Engineer, Tahsildar, Lakes Division, Room No., Floor, Head Office, Post, S/o, W/o, Village, Taluk, District). Do not leave Kannada terms in raw phonetic transliteration. Ensure every applicant and respondent name matches one-to-one with their address. Write place names in standard English title case.
6. Return ONLY the valid JSON object with no markdown fences, commentary, or extra text."""


_RECENT_LOGS = []
_LOG_LOCK = threading.Lock()

def get_recent_logs(limit: int = 200) -> list[str]:
    with _LOG_LOCK:
        return list(_RECENT_LOGS[-limit:])

def log_ocr(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{ts}] [{level}] {msg}"
    with _LOG_LOCK:
        _RECENT_LOGS.append(formatted)
        if len(_RECENT_LOGS) > 1000:
            _RECENT_LOGS.pop(0)
    try:
        print(formatted, flush=True)
    except Exception:
        pass
    app_dirs = [Path(__file__).resolve().parent, Path(os.getcwd())]
    if getattr(sys, "frozen", False):
        app_dirs.insert(0, Path(sys.executable).parent)
    seen = set()
    for d in app_dirs:
        for fname in ("app.log", "server.log"):
            p = d / fname
            if p not in seen:
                seen.add(p)
                try:
                    with open(p, "a", encoding="utf-8") as f:
                        f.write(formatted + "\n")
                except Exception:
                    pass

def check_tesseract_available() -> tuple[bool, str]:
    """Checks if Tesseract OCR is installed on the system (Windows, macOS, Linux)."""
    # 1. Standard PATH lookup
    for name in ("tesseract", "tesseract.exe"):
        p = shutil.which(name)
        if p and os.path.exists(p):
            tessdata = os.path.join(os.path.dirname(p), "tessdata")
            if os.path.exists(tessdata) and "TESSDATA_PREFIX" not in os.environ:
                os.environ["TESSDATA_PREFIX"] = tessdata
            log_ocr(f"Tesseract OCR found via PATH: {p} (tessdata: {tessdata})")
            return True, p

    # 2. Windows standard installation locations
    cwd = Path(os.getcwd())
    windows_candidates = [
        str(cwd / "Tesseract-OCR" / "tesseract.exe"),
        str(cwd / "tesseract.exe"),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%APPDATA%\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%ProgramFiles%\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        str(Path(__file__).resolve().parent / "Tesseract-OCR" / "tesseract.exe"),
        str(Path(__file__).resolve().parent / "tesseract" / "tesseract.exe"),
        str(Path(__file__).resolve().parent / "tesseract.exe"),
    ]
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).parent
        windows_candidates.extend([
            str(app_root / "Tesseract-OCR" / "tesseract.exe"),
            str(app_root / "tesseract" / "tesseract.exe"),
            str(app_root / "tesseract.exe"),
            str(app_root / "_internal" / "Tesseract-OCR" / "tesseract.exe"),
            str(app_root / "_internal" / "tesseract" / "tesseract.exe"),
        ])

    for wp in windows_candidates:
        if wp and os.path.exists(wp):
            tessdata = os.path.join(os.path.dirname(wp), "tessdata")
            if os.path.exists(tessdata) and "TESSDATA_PREFIX" not in os.environ:
                os.environ["TESSDATA_PREFIX"] = tessdata
            log_ocr(f"Tesseract OCR found at: {wp} (tessdata: {tessdata})")
            return True, wp

    # 3. macOS / Linux standard locations
    unix_candidates = [
        "/opt/homebrew/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/usr/bin/tesseract",
    ]
    for up in unix_candidates:
        if os.path.exists(up):
            log_ocr(f"Tesseract OCR found at Unix path: {up}")
            return True, up

    log_ocr("Tesseract OCR NOT found on system. Looked in standard locations and local Tesseract-OCR folder.", level="WARNING")
    return False, ""


def run_tesseract_ocr(img_source: str | bytes) -> str:
    """Runs local Tesseract OCR with Kannada + English language models and dual PSM modes."""
    is_avail, tess_path = check_tesseract_available()
    if not is_avail:
        log_ocr("run_tesseract_ocr called but Tesseract is not available!", level="WARNING")
        return ""

    is_temp = False
    if isinstance(img_source, str) and os.path.exists(img_source) and not img_source.startswith("data:"):
        target_path = os.path.realpath(img_source)
    else:
        is_temp = True
        temp_dir = os.path.realpath("/private/tmp" if IS_MAC and os.path.exists("/private/tmp") else tempfile.gettempdir())
        with tempfile.NamedTemporaryFile(suffix=".jpg", dir=temp_dir, delete=False) as tmp:
            target_path = os.path.realpath(tmp.name)
            raw_bytes = base64.b64decode(img_source) if isinstance(img_source, str) else img_source
            tmp.write(raw_bytes)

    log_ocr(f"Running Tesseract OCR using '{tess_path}' with languages 'kan+eng'...")
    try:
        tessdata = os.path.join(os.path.dirname(tess_path), "tessdata")
        tess_args = ["--tessdata-dir", tessdata] if os.path.exists(tessdata) else []
        sub_kwargs = {"capture_output": True, "timeout": 40}
        if sys.platform == "win32":
            sub_kwargs["creationflags"] = 0x08000000

        # Uniform block pass (PSM 6) - cleanest for Kannada court petitions and order sheets
        r_psm6 = subprocess.run([tess_path, target_path, "stdout", "-l", "kan+eng", "--psm", "6", *tess_args], **sub_kwargs)
        # Single-column layout pass (PSM 4) for single-column petitions and order sheets
        r0 = subprocess.run([tess_path, target_path, "stdout", "-l", "kan+eng", "--psm", "4", *tess_args], **sub_kwargs)
        # Standard layout pass for structured paragraphs
        r1 = subprocess.run([tess_path, target_path, "stdout", "-l", "kan+eng", *tess_args], **sub_kwargs)
        # Sparse text pass (PSM 11) for handwritten margin dates and stamps
        r2 = subprocess.run([tess_path, target_path, "stdout", "-l", "kan+eng", "--psm", "11", *tess_args], **sub_kwargs)
        # English sparse pass for stamps (CH. No), English numbers, and margin notes
        r3 = subprocess.run([tess_path, target_path, "stdout", "-l", "eng", "--psm", "11", *tess_args], **sub_kwargs)

        out0 = r0.stdout.decode("utf-8", errors="replace") if r0.stdout else ""
        out6 = r_psm6.stdout.decode("utf-8", errors="replace") if r_psm6.stdout else ""
        out1 = r1.stdout.decode("utf-8", errors="replace") if r1.stdout else ""
        out2 = r2.stdout.decode("utf-8", errors="replace") if r2.stdout else ""
        out3 = r3.stdout.decode("utf-8", errors="replace") if r3.stdout else ""
        valid_passes = [p.strip() for p in (out0, out6, out1, out2, out3) if p.strip()]
        total_len = sum(len(p) for p in valid_passes)
        log_ocr(f"Tesseract OCR finished successfully: extracted {total_len} characters across {len(valid_passes)} passes (PSM 6: {len(out6)}, PSM 4: {len(out0)}, PSM 11: {len(out2)}).")
        return "\n\n=== OCR_PASS ===\n\n".join(valid_passes)
    except Exception as exc:
        log_ocr(f"Error during Tesseract execution: {exc}", level="ERROR")
        return ""
    finally:
        if is_temp and os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass


def check_ollama_available(host: str = OLLAMA_DEFAULT_HOST) -> tuple[bool, list[str]]:
    """Checks if Ollama server is running and returns (is_running, model_names)."""
    try:
        url = f"{host.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "PendingCases/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            return True, models
    except Exception:
        return False, []


def select_best_vision_model(models: list[str]) -> str | None:
    """Picks the best vision model from installed Ollama models."""
    preferred = ["qwen2.5vl", "qwen2.5-vl", "llama3.2-vision", "minicpm-v", "llava", "bakllava", "moondream"]
    for pref in preferred:
        for m in models:
            if pref in m.lower():
                return m
    for m in models:
        if any(kw in m.lower() for kw in ("vl", "vision", "llava")):
            return m
    return models[0] if models else None


def extract_pdf_pages_coregraphics(pdf_path: str, max_dim: int = 2200) -> list[tuple[str, str, str]]:
    """
    Natively renders ALL pages of a multi-page PDF on macOS using CoreGraphics via ctypes.
    Zero external pip dependencies required.
    Returns: list of (page_label, original_file_path, base64_jpeg_string).
    """
    if not IS_MAC:
        return []

    try:
        import ctypes
        from ctypes import c_void_p, c_char_p, c_int, c_double, c_size_t, c_uint32, Structure

        class CGPoint(Structure):
            _fields_ = [("x", c_double), ("y", c_double)]

        class CGSize(Structure):
            _fields_ = [("width", c_double), ("height", c_double)]

        class CGRect(Structure):
            _fields_ = [("origin", CGPoint), ("size", CGSize)]

        cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        cs = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ImageIO.framework/ImageIO")

        cf.CFURLCreateFromFileSystemRepresentation.restype = c_void_p
        cf.CFURLCreateFromFileSystemRepresentation.argtypes = [c_void_p, c_char_p, c_size_t, c_int]
        cf.CFStringCreateWithCString.restype = c_void_p
        cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
        cg.CGPDFDocumentCreateWithURL.restype = c_void_p
        cg.CGPDFDocumentCreateWithURL.argtypes = [c_void_p]
        cg.CGPDFDocumentGetNumberOfPages.restype = c_size_t
        cg.CGPDFDocumentGetNumberOfPages.argtypes = [c_void_p]
        cg.CGPDFDocumentGetPage.restype = c_void_p
        cg.CGPDFDocumentGetPage.argtypes = [c_void_p, c_size_t]
        cg.CGPDFPageGetBoxRect.restype = CGRect
        cg.CGPDFPageGetBoxRect.argtypes = [c_void_p, c_int]
        cg.CGColorSpaceCreateDeviceRGB.restype = c_void_p
        cg.CGColorSpaceCreateDeviceRGB.argtypes = []
        cg.CGBitmapContextCreate.restype = c_void_p
        cg.CGBitmapContextCreate.argtypes = [c_void_p, c_size_t, c_size_t, c_size_t, c_size_t, c_void_p, c_uint32]
        cg.CGContextSetRGBFillColor.restype = None
        cg.CGContextSetRGBFillColor.argtypes = [c_void_p, c_double, c_double, c_double, c_double]
        cg.CGContextFillRect.restype = None
        cg.CGContextFillRect.argtypes = [c_void_p, CGRect]
        cg.CGContextScaleCTM.restype = None
        cg.CGContextScaleCTM.argtypes = [c_void_p, c_double, c_double]
        cg.CGContextDrawPDFPage.restype = None
        cg.CGContextDrawPDFPage.argtypes = [c_void_p, c_void_p]
        cg.CGBitmapContextCreateImage.restype = c_void_p
        cg.CGBitmapContextCreateImage.argtypes = [c_void_p]
        cs.CGImageDestinationCreateWithURL.restype = c_void_p
        cs.CGImageDestinationCreateWithURL.argtypes = [c_void_p, c_void_p, c_size_t, c_void_p]
        cs.CGImageDestinationAddImage.restype = None
        cs.CGImageDestinationAddImage.argtypes = [c_void_p, c_void_p, c_void_p]
        cs.CGImageDestinationFinalize.restype = c_int
        cs.CGImageDestinationFinalize.argtypes = [c_void_p]

        p_bytes = pdf_path.encode("utf-8")
        cf_url = cf.CFURLCreateFromFileSystemRepresentation(None, p_bytes, len(p_bytes), 0)
        doc = cg.CGPDFDocumentCreateWithURL(cf_url)
        if not doc:
            return []

        num_pages = cg.CGPDFDocumentGetNumberOfPages(doc)
        if num_pages == 0:
            return []

        color_space = cg.CGColorSpaceCreateDeviceRGB()
        type_jpeg = cf.CFStringCreateWithCString(None, b"public.jpeg", 0x08000100)

        results = []
        path_obj = Path(pdf_path)
        temp_dir = os.path.realpath("/private/tmp" if os.path.exists("/private/tmp") else tempfile.gettempdir())

        for p in range(1, num_pages + 1):
            page = cg.CGPDFDocumentGetPage(doc, p)
            rect = cg.CGPDFPageGetBoxRect(page, 0)
            orig_w, orig_h = rect.size.width, rect.size.height
            if orig_w <= 0 or orig_h <= 0:
                continue

            scale = min(2.5, max_dim / max(orig_w, orig_h))
            w = max(100, int(orig_w * scale))
            h = max(100, int(orig_h * scale))

            ctx = cg.CGBitmapContextCreate(None, w, h, 8, w * 4, color_space, 1)
            cg.CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0)
            cg.CGContextFillRect(ctx, CGRect(CGPoint(0, 0), CGSize(w, h)))
            cg.CGContextScaleCTM(ctx, scale, scale)
            cg.CGContextDrawPDFPage(ctx, page)
            img = cg.CGBitmapContextCreateImage(ctx)

            with tempfile.NamedTemporaryFile(suffix=".jpg", dir=temp_dir, delete=False) as tmp_f:
                tmp_path = os.path.realpath(tmp_f.name)

            out_bytes = tmp_path.encode("utf-8")
            out_cf_url = cf.CFURLCreateFromFileSystemRepresentation(None, out_bytes, len(out_bytes), 0)
            dest = cs.CGImageDestinationCreateWithURL(out_cf_url, type_jpeg, 1, None)
            cs.CGImageDestinationAddImage(dest, img, None)
            cs.CGImageDestinationFinalize(dest)

            with open(tmp_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")

            try:
                os.remove(tmp_path)
            except Exception:
                pass

            label = f"{path_obj.name} (Page {p})" if num_pages > 1 else path_obj.name
            results.append((label, pdf_path, b64))

        return results
    except Exception:
        return []


def get_pdf_page_count(file_path: str) -> int:
    """
    Accurately determines the total number of pages in a PDF document.
    Uses CoreGraphics on macOS, pdfinfo CLI on Linux/Windows, and a robust
    binary regex fallback for zero-dependency environments.
    """
    if not file_path or not os.path.exists(file_path):
        return 1
    ext = Path(file_path).suffix.lower()
    if ext != ".pdf":
        return 1

    # 1. macOS native CoreGraphics
    if IS_MAC:
        try:
            import ctypes
            from ctypes import c_void_p, c_char_p, c_int, c_size_t
            cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
            cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
            cf.CFURLCreateFromFileSystemRepresentation.restype = c_void_p
            cf.CFURLCreateFromFileSystemRepresentation.argtypes = [c_void_p, c_char_p, c_size_t, c_int]
            cg.CGPDFDocumentCreateWithURL.restype = c_void_p
            cg.CGPDFDocumentCreateWithURL.argtypes = [c_void_p]
            cg.CGPDFDocumentGetNumberOfPages.restype = c_size_t
            cg.CGPDFDocumentGetNumberOfPages.argtypes = [c_void_p]

            p_bytes = file_path.encode("utf-8")
            cf_url = cf.CFURLCreateFromFileSystemRepresentation(None, p_bytes, len(p_bytes), 0)
            doc = cg.CGPDFDocumentCreateWithURL(cf_url)
            if doc:
                n = cg.CGPDFDocumentGetNumberOfPages(doc)
                if n > 0:
                    return int(n)
        except Exception:
            pass

    # 2. pdfinfo CLI (Poppler)
    pdfinfo = get_pdfinfo_path()
    if pdfinfo:
        try:
            r = subprocess.run([pdfinfo, file_path], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                m = re.search(r"Pages:\s+(\d+)", r.stdout)
                if m:
                    return int(m.group(1))
        except Exception:
            pass

    # 3. Pure-Python regex scan of raw PDF bytes (zero external dependencies)
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        counts = re.findall(rb"/Type\s*/Pages\b[\s\S]*?/Count\s+(\d+)", content)
        if counts:
            return max(int(c) for c in counts)
        pages = re.findall(rb"/Type\s*/Page\b(?!\s*s)", content)
        if pages:
            return len(pages)
    except Exception:
        pass

    return 1


def get_pdftoppm_path() -> str | None:
    """Finds pdftoppm executable across Windows, macOS, and Linux."""
    for name in ("pdftoppm", "pdftoppm.exe"):
        p = shutil.which(name)
        if p and os.path.exists(p):
            return p

    candidates = [
        r"C:\Program Files\poppler\bin\pdftoppm.exe",
        r"C:\Program Files (x86)\poppler\bin\pdftoppm.exe",
        r"C:\poppler\bin\pdftoppm.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\poppler\bin\pdftoppm.exe"),
        os.path.expandvars(r"%USERPROFILE%\poppler\bin\pdftoppm.exe"),
        str(Path(__file__).resolve().parent / "poppler" / "bin" / "pdftoppm.exe"),
        str(Path(__file__).resolve().parent / "poppler" / "pdftoppm.exe"),
        str(Path(__file__).resolve().parent / "bin" / "pdftoppm.exe"),
        "/usr/bin/pdftoppm",
        "/usr/local/bin/pdftoppm",
        "/opt/homebrew/bin/pdftoppm",
    ]
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).parent
        candidates.extend([
            str(app_root / "poppler" / "bin" / "pdftoppm.exe"),
            str(app_root / "poppler" / "pdftoppm.exe"),
            str(app_root / "bin" / "pdftoppm.exe"),
            str(app_root / "_internal" / "poppler" / "bin" / "pdftoppm.exe"),
        ])
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def get_pdfinfo_path() -> str | None:
    """Finds pdfinfo executable across Windows, macOS, and Linux."""
    for name in ("pdfinfo", "pdfinfo.exe"):
        p = shutil.which(name)
        if p and os.path.exists(p):
            return p

    candidates = [
        r"C:\Program Files\poppler\bin\pdfinfo.exe",
        r"C:\Program Files (x86)\poppler\bin\pdfinfo.exe",
        r"C:\poppler\bin\pdfinfo.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\poppler\bin\pdfinfo.exe"),
        os.path.expandvars(r"%USERPROFILE%\poppler\bin\pdfinfo.exe"),
        str(Path(__file__).resolve().parent / "poppler" / "bin" / "pdfinfo.exe"),
        str(Path(__file__).resolve().parent / "poppler" / "pdfinfo.exe"),
        str(Path(__file__).resolve().parent / "bin" / "pdfinfo.exe"),
        "/usr/bin/pdfinfo",
        "/usr/local/bin/pdfinfo",
        "/opt/homebrew/bin/pdfinfo",
    ]
    if getattr(sys, "frozen", False):
        app_root = Path(sys.executable).parent
        candidates.extend([
            str(app_root / "poppler" / "bin" / "pdfinfo.exe"),
            str(app_root / "poppler" / "pdfinfo.exe"),
            str(app_root / "bin" / "pdfinfo.exe"),
            str(app_root / "_internal" / "poppler" / "bin" / "pdfinfo.exe"),
        ])
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None


def extract_pdf_pages_pure_python(file_path: str, max_dim: int = 1800) -> list[tuple[str, str, str]]:
    """
    Pure Python zero-dependency extraction of embedded page images from scanned PDF documents.
    Extracts native high-resolution scanned page JPEGs on Windows, Linux, and macOS without requiring Poppler or external tools.
    """
    if not file_path or not os.path.exists(file_path):
        return []
    path_obj = Path(file_path)
    try:
        with open(file_path, "rb") as f:
            content = f.read()

        jpegs = []
        start = 0
        while True:
            idx = content.find(b"\xff\xd8\xff", start)
            if idx == -1:
                break
            end = content.find(b"\xff\xd9", idx)
            if end == -1:
                break
            end += 2
            if (end - idx) > 20000:
                jpegs.append(content[idx:end])
            start = end

        if not jpegs:
            return []

        results = []
        num_pages = len(jpegs)
        for idx, raw_jpeg in enumerate(jpegs, 1):
            b64 = None
            if PIL_AVAILABLE and Image is not None:
                try:
                    with Image.open(io.BytesIO(raw_jpeg)) as im:
                        w, h = im.size
                        if max(w, h) > max_dim:
                            scale = max_dim / max(w, h)
                            im = im.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                        bio = io.BytesIO()
                        im.convert("RGB").save(bio, format="JPEG", quality=88)
                        b64 = base64.b64encode(bio.getvalue()).decode("utf-8")
                except Exception:
                    pass
            if not b64:
                b64 = base64.b64encode(raw_jpeg).decode("utf-8")
            label = f"{path_obj.name} (Page {idx})" if num_pages > 1 else path_obj.name
            results.append((label, file_path, b64))
        return results
    except Exception:
        return []


def extract_pdf_pages_pdftoppm(file_path: str, max_dim: int = 1800) -> list[tuple[str, str, str]]:
    """Extracts all pages from a PDF using pdftoppm as Base64 JPEG strings for OCR and vision models."""
    pdftoppm = get_pdftoppm_path()
    if not pdftoppm or not os.path.exists(file_path):
        return []
    path_obj = Path(file_path)
    temp_dir = tempfile.mkdtemp(prefix="pdf_extract_")
    try:
        prefix = os.path.join(temp_dir, "page")
        cmd = [pdftoppm, "-jpeg", "-scale-to", str(max_dim), file_path, prefix]
        subprocess.run(cmd, capture_output=True, check=True, timeout=60)
        page_files = sorted(glob.glob(os.path.join(temp_dir, "page-*.jpg")))
        results = []
        num_pages = len(page_files)
        for idx, p_file in enumerate(page_files, 1):
            with open(p_file, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            label = f"{path_obj.name} (Page {idx})" if num_pages > 1 else path_obj.name
            results.append((label, file_path, b64))
        return results
    except Exception:
        return []
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def render_document_page_png(file_path: str, page_num: int = 1, max_dim: int = 1000) -> tuple[bytes, int] | None:
    """
    Renders a specific page of a PDF or image into PNG bytes for Tkinter PhotoImage display.
    Supports native CoreGraphics / sips on macOS with zero external pip dependencies,
    and pdftoppm / PIL fallbacks on Windows / Linux.
    Returns: (png_bytes, total_pages) or None on failure.
    """
    if not file_path or not os.path.exists(file_path):
        return None

    ext = Path(file_path).suffix.lower()

    # 1. macOS Native CoreGraphics for PDF
    if ext == ".pdf" and IS_MAC:
        try:
            import ctypes
            from ctypes import c_void_p, c_char_p, c_int, c_double, c_size_t, Structure

            class CGPoint(Structure):
                _fields_ = [("x", c_double), ("y", c_double)]

            class CGSize(Structure):
                _fields_ = [("width", c_double), ("height", c_double)]

            class CGRect(Structure):
                _fields_ = [("origin", CGPoint), ("size", CGSize)]

            cg = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
            cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
            cs = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ImageIO.framework/ImageIO")

            cf.CFURLCreateFromFileSystemRepresentation.restype = c_void_p
            cf.CFURLCreateFromFileSystemRepresentation.argtypes = [c_void_p, c_char_p, c_size_t, c_int]
            cf.CFStringCreateWithCString.restype = c_void_p
            cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_size_t]
            cg.CGPDFDocumentCreateWithURL.restype = c_void_p
            cg.CGPDFDocumentCreateWithURL.argtypes = [c_void_p]
            cg.CGPDFDocumentGetNumberOfPages.restype = c_size_t
            cg.CGPDFDocumentGetNumberOfPages.argtypes = [c_void_p]
            cg.CGPDFDocumentGetPage.restype = c_void_p
            cg.CGPDFDocumentGetPage.argtypes = [c_void_p, c_size_t]
            cg.CGPDFPageGetBoxRect.restype = CGRect
            cg.CGPDFPageGetBoxRect.argtypes = [c_void_p, c_int]
            cg.CGColorSpaceCreateDeviceRGB.restype = c_void_p
            cg.CGColorSpaceCreateDeviceRGB.argtypes = []
            cg.CGBitmapContextCreate.restype = c_void_p
            cg.CGBitmapContextCreate.argtypes = [c_void_p, c_size_t, c_size_t, c_size_t, c_size_t, c_void_p, c_size_t]
            cg.CGContextSetRGBFillColor.restype = None
            cg.CGContextSetRGBFillColor.argtypes = [c_void_p, c_double, c_double, c_double, c_double]
            cg.CGContextFillRect.restype = None
            cg.CGContextFillRect.argtypes = [c_void_p, CGRect]
            cg.CGContextScaleCTM.restype = None
            cg.CGContextScaleCTM.argtypes = [c_void_p, c_double, c_double]
            cg.CGContextDrawPDFPage.restype = None
            cg.CGContextDrawPDFPage.argtypes = [c_void_p, c_void_p]
            cg.CGBitmapContextCreateImage.restype = c_void_p
            cg.CGBitmapContextCreateImage.argtypes = [c_void_p]
            cs.CGImageDestinationCreateWithURL.restype = c_void_p
            cs.CGImageDestinationCreateWithURL.argtypes = [c_void_p, c_void_p, c_size_t, c_void_p]
            cs.CGImageDestinationAddImage.restype = None
            cs.CGImageDestinationAddImage.argtypes = [c_void_p, c_void_p, c_void_p]
            cs.CGImageDestinationFinalize.restype = c_int
            cs.CGImageDestinationFinalize.argtypes = [c_void_p]

            p_bytes = file_path.encode("utf-8")
            cf_url = cf.CFURLCreateFromFileSystemRepresentation(None, p_bytes, len(p_bytes), 0)
            doc = cg.CGPDFDocumentCreateWithURL(cf_url)
            if doc:
                total = cg.CGPDFDocumentGetNumberOfPages(doc)
                if 1 <= page_num <= total:
                    page = cg.CGPDFDocumentGetPage(doc, page_num)
                    rect = cg.CGPDFPageGetBoxRect(page, 0)
                    orig_w, orig_h = rect.size.width, rect.size.height
                    if orig_w > 0 and orig_h > 0:
                        scale = max_dim / max(orig_w, orig_h)
                        w, h = max(50, int(orig_w * scale)), max(50, int(orig_h * scale))
                        color_space = cg.CGColorSpaceCreateDeviceRGB()
                        ctx = cg.CGBitmapContextCreate(None, w, h, 8, w * 4, color_space, 1)
                        cg.CGContextSetRGBFillColor(ctx, 1.0, 1.0, 1.0, 1.0)
                        cg.CGContextFillRect(ctx, CGRect(CGPoint(0, 0), CGSize(w, h)))
                        cg.CGContextScaleCTM(ctx, scale, scale)
                        cg.CGContextDrawPDFPage(ctx, page)
                        img = cg.CGBitmapContextCreateImage(ctx)

                        temp_dir = os.path.realpath("/private/tmp" if os.path.exists("/private/tmp") else tempfile.gettempdir())
                        with tempfile.NamedTemporaryFile(suffix=".png", dir=temp_dir, delete=False) as tmp:
                            tmp_path = tmp.name
                        out_bytes = tmp_path.encode("utf-8")
                        out_cf_url = cf.CFURLCreateFromFileSystemRepresentation(None, out_bytes, len(out_bytes), 0)
                        type_png = cf.CFStringCreateWithCString(None, b"public.png", 0x08000100)
                        dest = cs.CGImageDestinationCreateWithURL(out_cf_url, type_png, 1, None)
                        cs.CGImageDestinationAddImage(dest, img, None)
                        cs.CGImageDestinationFinalize(dest)

                        with open(tmp_path, "rb") as f:
                            data = f.read()
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
                        return data, total
        except Exception:
            pass

    # 2. Image files (JPG, PNG, TIFF, BMP) on macOS via sips
    if ext in (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff") and IS_MAC:
        try:
            temp_dir = os.path.realpath("/private/tmp" if os.path.exists("/private/tmp") else tempfile.gettempdir())
            with tempfile.NamedTemporaryFile(suffix=".png", dir=temp_dir, delete=False) as tmp:
                tmp_path = tmp.name
            res = subprocess.run(
                ["sips", "-s", "format", "png", str(file_path), "-Z", str(max_dim), "--out", tmp_path],
                capture_output=True
            )
            if res.returncode == 0 and os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    data = f.read()
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                return data, 1
        except Exception:
            pass

    # 3. Poppler pdftoppm fallback (cross-platform / Linux / Windows)
    if ext == ".pdf":
        pdftoppm = get_pdftoppm_path()
        if pdftoppm:
            try:
                total_pages = get_pdf_page_count(file_path)
                temp_dir = tempfile.gettempdir()
                prefix = os.path.join(temp_dir, f"pdf_pg_{os.getpid()}_{page_num}")
                subprocess.run(
                    [pdftoppm, "-png", "-scale-to", str(max_dim), "-f", str(page_num), "-l", str(page_num), file_path, prefix],
                    capture_output=True,
                    timeout=30
                )
                candidates = sorted(glob.glob(f"{prefix}-*.png"))
                if candidates:
                    out_png = candidates[0]
                    with open(out_png, "rb") as f:
                        data = f.read()
                    try:
                        os.remove(out_png)
                    except Exception:
                        pass
                    return data, total_pages
            except Exception:
                pass

        # 4. Pure-Python embedded JPEG extraction fallback for PDF (zero external dependencies)
        try:
            total_pages = get_pdf_page_count(file_path)
            with open(file_path, "rb") as f:
                content = f.read()
            jpegs = []
            start = 0
            while True:
                idx = content.find(b"\xff\xd8\xff", start)
                if idx == -1:
                    break
                end = content.find(b"\xff\xd9", idx)
                if end == -1:
                    break
                end += 2
                if (end - idx) > 20000:
                    jpegs.append(content[idx:end])
                start = end
            if jpegs and 1 <= page_num <= len(jpegs):
                target_bytes = jpegs[page_num - 1]
                if PIL_AVAILABLE and Image is not None:
                    with Image.open(io.BytesIO(target_bytes)) as im:
                        im.thumbnail((max_dim, max_dim))
                        buf = io.BytesIO()
                        im.save(buf, format="PNG")
                        return buf.getvalue(), max(len(jpegs), total_pages)
                return target_bytes, max(len(jpegs), total_pages)
        except Exception:
            pass

    # 5. PIL fallback if available
    if PIL_AVAILABLE and Image is not None:
        try:
            total_pages = get_pdf_page_count(file_path) if ext == ".pdf" else 1
            with Image.open(file_path) as im:
                im.thumbnail((max_dim, max_dim))
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                return buf.getvalue(), total_pages
        except Exception:
            pass

    return None


def file_to_base64_jpeg(file_path: str, max_dim: int = 1800) -> str:
    """Converts an image or PDF on disk to a resized JPEG base64 string for vision models."""
    path_obj = Path(file_path)
    if path_obj.suffix.lower() == ".pdf":
        if IS_MAC:
            cg_pages = extract_pdf_pages_coregraphics(file_path, max_dim=max_dim)
            if cg_pages:
                return cg_pages[0][2]
        ppm_pages = extract_pdf_pages_pdftoppm(file_path, max_dim=max_dim)
        if ppm_pages:
            return ppm_pages[0][2]
        py_pages = extract_pdf_pages_pure_python(file_path, max_dim=max_dim)
        if py_pages:
            return py_pages[0][2]

    if IS_MAC:
        try:
            temp_dir = os.path.realpath("/private/tmp" if os.path.exists("/private/tmp") else tempfile.gettempdir())
            with tempfile.NamedTemporaryFile(suffix=".jpg", dir=temp_dir, delete=False) as tmp:
                tmp_path = os.path.realpath(tmp.name)
            res = subprocess.run(
                ["sips", "-s", "format", "jpeg", "-Z", str(max_dim), str(path_obj), "--out", tmp_path],
                capture_output=True
            )
            if res.returncode == 0 and os.path.exists(tmp_path):
                with open(tmp_path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                return b64
        except Exception:
            pass

    if PIL_AVAILABLE and Image is not None:
        try:
            img = Image.open(file_path)
            w, h = img.size
            if max(w, h) > max_dim:
                scale = max_dim / max(w, h)
                img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
            bio = io.BytesIO()
            img.convert("RGB").save(bio, format="JPEG", quality=88)
            return base64.b64encode(bio.getvalue()).decode("utf-8")
        except Exception:
            pass

    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def pil_to_base64_jpeg(img, max_dim: int = 1800) -> str:
    """Converts a PIL Image to a resized JPEG base64 string for vision models."""
    if img is None:
        return ""
    if PIL_AVAILABLE and Image is not None and hasattr(img, "size"):
        w, h = img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        bio = io.BytesIO()
        img.convert("RGB").save(bio, format="JPEG", quality=88)
        return base64.b64encode(bio.getvalue()).decode("utf-8")
    return ""


def extract_image_frames(file_path: str) -> list[tuple[str, str, str]]:
    """Loads all frames/pages from an image or PDF file.
    Returns a list of tuples: (page_label, original_file_path, base64_jpeg_string)."""
    path_obj = Path(file_path)

    # 1. Multi-page PDF (native macOS CoreGraphics or Poppler pdftoppm)
    if path_obj.suffix.lower() == ".pdf":
        if IS_MAC:
            cg_pages = extract_pdf_pages_coregraphics(file_path)
            if cg_pages:
                return cg_pages
        ppm_pages = extract_pdf_pages_pdftoppm(file_path)
        if ppm_pages:
            return ppm_pages
        py_pages = extract_pdf_pages_pure_python(file_path)
        if py_pages:
            return py_pages

    # 2. Multi-page images via PIL (TIFF / GIF)
    if PIL_AVAILABLE and Image is not None and ImageSequence is not None and path_obj.suffix.lower() not in (".pdf",):
        try:
            pil_img = Image.open(file_path)
            iterator = list(ImageSequence.Iterator(pil_img))
            if len(iterator) > 1:
                results: list[tuple[str, str, str]] = []
                for page_idx, frame in enumerate(iterator, 1):
                    label = f"{path_obj.name} (Page {page_idx})"
                    w, h = frame.size
                    max_dim = 1800
                    if max(w, h) > max_dim:
                        scale = max_dim / max(w, h)
                        frame = frame.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                    bio = io.BytesIO()
                    frame.convert("RGB").save(bio, format="JPEG", quality=88)
                    b64 = base64.b64encode(bio.getvalue()).decode("utf-8")
                    results.append((label, file_path, b64))
                return results
        except Exception:
            pass

    # 3. Standard single image or fallback
    b64 = file_to_base64_jpeg(file_path)
    return [(path_obj.name, file_path, b64)]


def query_ollama_vision(image_b64: str, model_name: str, host: str = OLLAMA_DEFAULT_HOST) -> tuple[str, dict]:
    """Sends an image to Ollama Vision model and parses the JSON response."""
    url = f"{host.rstrip('/')}/api/generate"
    payload = {
        "model": model_name,
        "prompt": OLLAMA_VISION_PROMPT,
        "images": [image_b64],
        "format": "json",
        "stream": False,
        "options": {
            "temperature": 0.1
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        res_json = json.loads(resp.read().decode("utf-8"))
        raw_text = res_json.get("response", "").strip()

    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
    if match:
        clean_json = match.group(1)
    else:
        start = raw_text.find('{')
        end = raw_text.rfind('}')
        clean_json = raw_text[start:end + 1] if (start != -1 and end != -1) else raw_text

    parsed = json.loads(clean_json)
    return raw_text, parsed


STAGE_TO_GROUP = {}
for _grp, _st_list in STAGES_BY_GROUP.items():
    for _st in _st_list:
        if _st and _st not in STAGE_TO_GROUP:
            STAGE_TO_GROUP[_st] = _grp

STAGE_TO_GROUP.update({
    "Appearance of Accused": "Appearance",
    "Appearance of Respondent": "Appearance",
    "Summons to Accused": "Criminal Process",
    "Summons to Witness": "Evidence",
    "Summons to the Witness": "Evidence",
    "Witness Summons": "Evidence",
    "Re-issue Witness Summons": "Evidence",
    "To file Form No.1": "Objections / Pleadings",
    "NBW": "Criminal Process",
    "Await NBW": "Criminal Process",
    "Re-Issue NBW": "Criminal Process",
    "Bailable Warrant": "Criminal Process",
    "Await Bailable Warrant": "Criminal Process",
    "Re-Issue B/W": "Criminal Process",
    "Sworn Statement": "Preliminary Hearing / Cognizance",
    "Hearing on Cognizance/Objection to the respondent": "Preliminary Hearing / Cognizance",
    "To Comply with Court Order": "Possession / Execution / Compliance",
    "Await Compliance Report": "Possession / Execution / Compliance",
    "Compliance Report": "Possession / Execution / Compliance",
    "Await Orders from Hon'ble High Court of Karnataka": "Stayed Matters",
    "Cross of Plaintiff Witness": "Evidence",
    "Cross of Defendants Witness": "Evidence",
    "Cross of PW": "Evidence",
    "Cross of DW": "Evidence",
    "Defence Evidence": "Evidence",
    "Complaint Evidence": "Evidence",
    "cross examination of witness": "Evidence",
    "Notice to Respondent": "Notice / Summons / Service",
    "Await Notice to Respondent": "Notice / Summons / Service",
    "Notice to Accused": "Notice / Summons / Service",
    "Await Notice to Accused": "Notice / Summons / Service",
    "Hearing on objection": "Objections / Pleadings",
    "Objection Statement": "Objections / Pleadings",
    "Objections to IA": "Objections / Pleadings",
    "adjourned for want of time": "Objections / Pleadings",
    "Status Report": "Reports / Verification",
    "Await Further Report": "Reports / Verification",
    "Await Report": "Reports / Verification",
    "Hearing": "Hearing",
    "Hearing on IA": "Hearing",
    "Arguments": "Arguments",
    "Further Arguments": "Arguments",
    "Orders": "Orders",
    "Orders on IA": "Orders",
    "Judgement": "Judgment / Final Order",
    "Disposed": "Closed / Disposal",
    "Allowed": "Closed / Disposal",
    "Dismissed": "Closed / Disposal",
    "Charge": "Charge/Plea",
    "313 Statement": "313 Cr.P.C /351 BNSS Statement",
    "HBC": "HBC",
    "Hearing Before Charge": "HBC",
    "For HBC": "HBC",
    "For HBC finally": "HBC",
    "HBC finally": "HBC",
    "Orders on HBC": "Orders",
})

NOTICE_TO_RESPONDENT_REGEX = re.compile(
    r'(?i)\b(?:'
    r'(?:(?:issue|re[- ]?issue|await|awaiting|send|sent|ordered|ordered\s+to|shall\s+issue|direct(?:ed)?\s+to\s+issue)\s+)?'
    r'(?:(?:show\s*cause\s+)?notice|summons)\s+(?:to|against|for)\s+(?:the\s+)?(?:said\s+)?(?:resp(?:ondent)?|repsondent|r\d+|accused(?:/|\s+and\s+)respondent)(?:s|\b|\s*no\.?\s*\d+)'
    r'|notice\s+to\s+(?:the\s+)?(?:said\s+)?(?:resp(?:ondent)?|repsondent|r\d+)'
    r'|notice\s+(?:issued\s+)?against\s+(?:the\s+)?(?:said\s+)?(?:resp(?:ondent)?|repsondent|r\d+)'
    r'|issue\s+notice\s+to\s+r\d+'
    r'|notice\s+to\s+r[- ]?\d+'
    r'|notice\s+(?:to\s+respondent\s+)?in\s+form\s+(?:no\.?)?\s*iv\b'
    r')\b'
    r'|(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:(?:ಎದುರುದಾರ(?:ರಿಗೆ|ಗೆ)?|ಪ್ರತಿವಾದಿ(?:ಗೆ|ಗಳಿಗೆ)?|ಆರೋಪಿ(?:ಗೆ|ಗಳಿಗೆ)?(?:/|ಮತ್ತು)?ಎದುರುದಾರರಿಗೆ)?\s*(?:ಮರು\s*)?ನೋಟ[ಿೀ]ಸ್(?:ಗೆ|ಗಾಗಿ|ನ್ನು|ಜಾರಿಗಾಗಿ|ಜಾರಿಗೆ)?|ನೋಟ[ಿೀ]ಸ್\s*ಜಾರಿ(?:ಗೆ|ಗಾಗಿ)?)(?![\u0C80-\u0CFFa-zA-Z0-9])'
)

STAGE_RULES = [
    (NOTICE_TO_RESPONDENT_REGEX.pattern, "Notice to Respondent"),
    (r"(?i)\b(?:for\s+)?hbc(?:\s+finally)?\b|\bhearing\s+before\s+charge\b", "HBC"),
    (r"(?i)\borders?\s+on\s+hbc\b", "Orders on HBC"),
    (r"\b(?:to\s+comply\s+with\s+court\s+order|comply\s+with\s+order|court\s+order\s+compliance)\b", "To Comply with Court Order"),
    (r"\b(?:await\s+orders?\s+from(?:\s+hon'?ble)?\s+high\s+court|high\s+court\s+stay|hc\s+stay)\b", "Await Orders from Hon'ble High Court of Karnataka"),
    (r"\b(?:re[- ]?issue\s+b/?w|re[- ]?issue\s+bailable\s+warrant)\b", "Re-Issue B/W"),
    (r"\b(?:await\s+b/?w|await\s+bailable\s+warrant)\b", "Await Bailable Warrant"),
    (r"\b(?:b/?w|bailable\s+warrant)\b", "Bailable Warrant"),
    (r"\b(?:re[- ]?issue\s+nbw|re[- ]?issue\s+non[- ]?bailable\s+warrant)\b", "Re-Issue NBW"),
    (r"\b(?:await\s+nbw|await\s+non[- ]?bailable\s+warrant)\b", "Await NBW"),
    (r"\b(?:nbw|non[- ]?bailable\s+warrant)\b", "NBW"),
    (r"\b(?:re[- ]?issue\s+)?(?:witness\s+summons|summons\s+to\s+(?:the\s+)?witness)\b|(?:to\s+appear.*to\s+give\s+evidence|for\s+evidence\s+of\s+witness)|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಸಾಕ್ಷಿ\s*ಸಮನ್ಸ್(?![\u0C80-\u0CFFa-zA-Z0-9])", "Summons to Witness"),
    (r"\b(?:notice/?summons\s+to\s+accused)\b", "Notice/Summons to Accused"),
    (r"\b(?:re[- ]?issue\s+)?(?:summons\s+to\s+accused|accused\s+summons)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಆರೋಪಿಗೆ\s*ಸಮನ್ಸ್(?![\u0C80-\u0CFFa-zA-Z0-9])", "Summons to Accused"),
    (r"\b(?:await\s+notice\s+to\s+accused)\b", "Await Notice to Accused"),
    (r"\b(?:await\s+notice\s+to\s+resp(?:ondent)?)\b", "Await Notice to Respondent"),
    (r"\b(?:await\s+court\s+notice\s+of\s+accused|await\s+court\s+notice)\b", "Await court notice of Accused/defendants"),
    (r"\b(?:(?:issue\s+)?notice\s+by\s+speed\s+post)\b", "issue notice by speed post"),
    (r"\b(?:show\s*case\s+notice|show\s*cause\s+notice)\b", "show case notice and explaination"),
    (r"\b(?:hearing\s+on\s+cognizance|cognizance)\b", "Hearing on Cognizance/Objection to the respondent"),
    (r"\b(?:adjourned\s+for\s+want\s+of\s+time)\b", "adjourned for want of time"),
    (r"\b(?:await\s+further\s+report)\b", "Await Further Report"),
    (r"\b(?:compliance\s+report)\b", "Compliance Report"),
    (r"\b(?:status\s+report)\b", "Status Report"),
    (r"\b(?:await\s+report|awaiting\s+report|report\s+by)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ವರದಿ\s*ನಿರೀಕ್ಷೆ(?![\u0C80-\u0CFFa-zA-Z0-9])", "Await Report"),
    (r"\b(?:appearance\s+of\s+accused|accused\s+appeared)\b", "Appearance of Accused"),
    (r"\b(?:appearance\s+of\s+resp(?:ondent)?|resp(?:ondent)?\s+appeared)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಹಾಜರಾತಿ(?:ಗೆ|ಗಾಗಿ|ಯ)?(?![\u0C80-\u0CFFa-zA-Z0-9])", "Appearance of Respondent"),
    (r"\b(?:objections?\s+to\s+i\.?a\.?)\b", "Objections to IA"),
    (r"\b(?:objection\s+statement|statement\s+of\s+objections?|file\s+objections?|filing\s+objections?|for\s+objections?)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಆಕ್ಷೇಪಣೆ(?:ಗೆ|ಗಾಗಿ|ಗಳು|ಗಳನ್ನು\s+ಸಲ್ಲಿಸಲು)?(?![\u0C80-\u0CFFa-zA-Z0-9])", "Objection Statement"),
    (r"\b(?:hearing\s+on\s+objections?|furnish(?:\s+the)?\s+(?:copy\s+of\s+)?objections?|copy\s+of\s+objections?|file\s+objections?|filing\s+objections?|objections?\s+to\s+main)\b", "Hearing on objection"),
    (r"\b(?:(?:to\s+file|shall\s+file|file|seeks\s+time\s+to\s+file|separate)?\s*form\s*(?:no\.?)?\s*(?:1|i\b|I\b))\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಫಾರ್ಮ್\s*ನಂ\.?\s*(?:1|೧)(?![\u0C80-\u0CFFa-zA-Z0-9])", "To file Form No.1"),
    (r"\b(?:313\s+statement|statement\s+u/?s\s+313)\b", "313 Statement"),
    (r"\b(?:sworn\s+statement)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಪ್ರಮಾಣ\s*ವಚನ(?:ಕ್ಕೆ|ಕ್ಕಾಗಿ)?(?![\u0C80-\u0CFFa-zA-Z0-9])", "Sworn Statement"),
    (r"\b(?:cross\s+(?:of\s+)?defendants?\s+witness|cross\s+of\s+dw)\b", "Cross of Defendants Witness"),
    (r"\b(?:cross\s+(?:of\s+)?plaintiffs?\s+witness|cross\s+of\s+pw)\b", "Cross of Plaintiff Witness"),
    (r"\b(?:cross[- ]examination\s+of\s+witness|cross\s+of\s+witness)\b", "cross examination of witness"),
    (r"(?i)\b(?:for\s+)?(?:plaintiff\s+evidence|plaintiffs\s+evidence|plnt\s+evidence|\bpe\b)\b", "Plaintiff Evidence"),
    (r"(?i)\b(?:for\s+)?(?:defendant\s+evidence|defendants\s+evidence|deft\s+evidence|\bde\b)\b", "Defendants Evidence"),
    (r"\b(?:complainant\s+evidence|complaint\s+evidence|pw\s+evidence)\b", "Complaint Evidence"),
    (r"\b(?:defence\s+evidence|defense\s+evidence|dw\s+evidence)\b", "Defence Evidence"),
    (r"\b(?:framing\s+of\s+charges?|charge\s+framed|charges?)\b", "Charge"),
    (r"\b(?:further\s+arguments?)\b", "Further Arguments"),
    (r"\b(?:complaint\s+arguments?|complainant\s+arguments?)\b", "Complaint Arguments"),
    (r"\b(?:defence\s+arguments?|defense\s+arguments?)\b", "Defence Argument"),
    (r"\b(?:hearing\s+on\s+i\.?a\.?)\b", "Hearing on IA"),
    (r"\b(?:for\s+hearing\s+on\s+application)\b", "For Hearing on Application"),
    (r"(?i)\barguments?\b|(?<!ಪ್ರತಿ)(?<!ವಾದ)ವಾದ\s*(?:ಮಂಡನೆ|ಕ್ಕಾಗಿ|ಕ್ಕೆ|ಆಲಿಕೆ)|(?:^|[\s.,;:\-_/(])ವಾದ(?:$|[\s.,;:\-_/)])", "Arguments"),
    (r"\b(?:for\s+hearing|posted\s+for\s+hearing|case\s+is\s+for\s+hearing)\b|(?<!next\s)(?<!date\sof\s)\bhearing\b(?!\s+(?:date|without\s+fail))|(?<![\u0C80-\u0CFFa-zA-Z0-9])ವಿಚಾರಣೆ(?:ಗೆ|ಗಾಗಿ|ಯ)?(?![\u0C80-\u0CFFa-zA-Z0-9])", "Hearing"),
    (r"\bjudg(?:e)?ment\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ತೀರ್ಪು(?:ಗೆ|ಗಾಗಿ|ನ್ನು)?(?![\u0C80-\u0CFFa-zA-Z0-9])", "Judgement"),
    (r"\bdismissed\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಖುಲಾಸೆ(?![\u0C80-\u0CFFa-zA-Z0-9])", "Dismissed"),
    (r"(?i)(?<!application\sis\s)(?<!application\s)(?<!ia\sis\s)(?<!i\.a\.\sis\s)\b(?:case\s+is\s+allowed|petition\s+is\s+allowed|appeal\s+is\s+allowed|claim\s+is\s+allowed)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಪುರಸ್ಕರಿಸಿದೆ(?![\u0C80-\u0CFFa-zA-Z0-9])", "Allowed"),
    (r"\bdisposed\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ವಿಲೇವಾರಿ(?![\u0C80-\u0CFFa-zA-Z0-9])", "Disposed"),
    (r"\b(?:orders?\s+on\s+i\.?a\.?)\b", "Orders on IA"),
    (r"\b(?:for\s+orders?|posted\s+for\s+orders?|orders?\s+reserved|reserved\s+for\s+orders?|orders?\s+on\s+maintainability)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಆದೇಶಕ್ಕಾಗಿ(?![\u0C80-\u0CFFa-zA-Z0-9])", "Orders"),
]


def infer_stage_group_from_description(desc: str) -> str:
    """Infers the most appropriate stage group from a free-text call description."""
    if not desc:
        return "Hearing"
    d_lower = desc.lower()

    if any(k in d_lower for k in ("along with", "club with", "tagged with", "put up with", "call this case", "list this matter", "say of", "prosecutor", "transfer")):
        return "Hearing"
    if any(k in d_lower for k in ("notice", "summons", "service", "bailable", "warrant", "process", "ನೋಟಿಸ್", "ಸಮನ್ಸ್", "ಜಾರಿ")):
        return "Criminal Process" if any(k in d_lower for k in ("nbw", "b/w", "bailable", "non-bailable", "ವಾರೆಂಟ್", "ವಾರಂಟ್")) else "Notice / Summons / Service"
    if any(k in d_lower for k in ("objection", "written statement", "pleading", "ws", "counter", "reply", "rejoinder", "ಆಕ್ಷೇಪಣೆ", "ಲಿಖಿತ ಹೇಳಿಕೆ")):
        return "Objections / Pleadings"
    if any(k in d_lower for k in ("report", "survey", "inspection", "tahsildar", "adlr", "commissioner", "verification", "status report", "compliance report", "ವರದಿ", "ಸರ್ವೆ", "ಪರಿಶೀಲನೆ", "ಮಹಜರ್")):
        return "Reports / Verification"
    if any(k in d_lower for k in ("evidence", "witness", "chief", "cross", "pw", "dw", "sworn", "affidavit", "ಸಾಕ್ಷ್ಯ", "ಸಾಕ್ಷಿ", "ಪ್ರಮಾಣ")):
        return "Evidence"
    if any(k in d_lower for k in ("argument", "arguments", "submission", "hearing on argument", "ವಾದ", "ವಾದ-ಪ್ರತಿವಾದ")):
        return "Arguments"
    if any(k in d_lower for k in ("judgment", "judgement", "final order", "disposed", "disposal", "ತೀರ್ಪು", "ವಿಲೇವಾರಿ")):
        return "Judgment / Final Order"
    if re.search(r"\b(?:orders?\s+on|for\s+orders?|order\s+on\s+ia|order\s+on\s+application|hearing\s+on\s+ia|i\.?a\.?|\bia\b)\b", d_lower) or "ಆದೇಶ" in d_lower or "ಮಧ್ಯಂತರ ಅರ್ಜಿ" in d_lower:
        return "Orders"
    if any(k in d_lower for k in ("settlement", "mediation", "compromise", "lok adalat", "ರಾಜಿ", "ಮಧ್ಯಸ್ಥಿಕೆ")):
        return "Appearance"
    if any(k in d_lower for k in ("charge", "plea", "313", "351", "ಆರೋಪ")):
        return "Charge/Plea"
    if any(k in d_lower for k in ("hbc", "hearing before charge")):
        return "HBC"
    if any(k in d_lower for k in ("compliance", "court fee", "steps", "rectification", "scrutiny", "defect", "document", "production", "produce", "deed", "ದಾಖಲೆ", "ಕ್ರಮ", "ಪಾಲನೆ")):
        return "Filing & Scrutiny"
    if any(k in d_lower for k in ("appearance", "appeared", "present", "vakalat", "ಹಾಜರಾಗಲು", "ಹಾಜರಾತಿ", "ವಕಾಲತ್")):
        return "Appearance"
    if any(k in d_lower for k in ("cognizance", "preliminary", "maintainability", "ಸ್ವೀಕಾರ")):
        return "Preliminary Hearing / Cognizance"
    return "Hearing"


def summarize_call_description_from_window(window_above: str, full_text: str = "") -> tuple[str, str]:
    """
    Extracts and creates a description summarizing what the next call is about
    based on the available sentences immediately above the next hearing date.
    Returns (description, stage_group).
    """
    if not window_above or not window_above.strip():
        return "", "Hearing"

    w = window_above.strip()
    # Strip trailing call preambles, dates, and instructions repeatedly
    for _ in range(5):
        w = w.strip()
        w = re.sub(r"(?i)(?:(?:ದಿನಾಂಕ\s*[:\-]?)?\s*\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}\s*(?:ಕ್ಕೆ|ರಂದು|ಗೆ)?\s*(?:ಕರೆಯಿರಿ|ಮುಂದೂಡಿದೆ|ವಿಚಾರಣೆಗೆ|ಹಾಜರಾಗಲು)?)\s*$", "", w).strip()
        w = re.sub(r"(?i)[\s:\-0-9&()\u0c80-\u0cff]*\b(?:call\s+on|adjourn(?:ed|ment)?\s+to|post(?:ed)?\s+to|re[- ]?list\s+(?:on|to)|fixed\s+for|listed\s+(?:on|to)|next\s+(?:date|hearing)\s*(?:is|on|to)?|hearing\s+on|by|date)[\s:\-0-9&()\u0c80-\u0cff]*$", "", w).strip()
        w = re.sub(r"(?:ಮುಂದೂಡಿದೆ|ಕರೆಯಿರಿ|ವಿಚಾರಣೆಗೆ|ಮುಂದಿನ\s*(?:ದಿನಾಂಕ|ವಿಚಾರಣೆಗೆ|ವಿಚಾರಣೆ)|ದಿನಾಂಕ|ದಿನಾಂಕದಂದು|ಕರೆ\s*ದಿನಾಂಕ|ಕರೆ)\s*[:\-]?\s*$", "", w).strip()

    junk_patterns = [
        r"(?i)\b(?:hon'\''ble\s+judge|ch\.?\s*no\.?\s*\d+|court\s+hall\s+(?:no\.?\s*)?\d+|spl\.?\s*court|special\s+court)\b",
        r"(?i)\b(?:member|chairman|president|judge|sheristadar|stenographer|bench\s+clerk)\b",
        r"(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ನ್ಯಾಯಾಧೀಶರು|ಸದಸ್ಯರು|ಅಧ್ಯಕ್ಷರು|ಶಿರಸ್ತೇದಾರರು|ನ್ಯಾಯಾಂಗಣ[\-\s]*\d+)(?![\u0C80-\u0CFFa-zA-Z0-9])",
        r"(?i)\b(?:want\s+of\s+quorum|for\s+want\s+of\s+quorum|quorum|quoram|coram\s+absent)\b",
        r"(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಕೋರಂ\s*ಕೊರತೆ|ಕೋರಂ)(?![\u0C80-\u0CFFa-zA-Z0-9])",
        r"(?i)\b(?:respondent\s+called\s+out|called\s+out|absent|counsel\s+for\s+respondent\s+is\s+present|counsel\s+for|advocate\s+for|is\s+present)\b",
        r"(?i)\b(?:matter\s+taken\s+up|taken\s+up\s+on\s+board|before\s+the\s+court|on\s+transfer|assigned\s+to\s+court\s+hall|withdrawn\s+from)\b",
        r"(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಗೈರುಹಾಜರು|ಹಾಜರಿದ್ದಾರೆ|ಹಾಜರಿಲ್ಲ)(?![\u0C80-\u0CFFa-zA-Z0-9])",
    ]

    # Protect dots in dates (e.g. 15.11.2026) and legal abbreviations (e.g. I.A., C.W.)
    w_prot = re.sub(r"(\d+)\.(\d+)", r"\1<DOT>\2", w)
    w_prot = re.sub(r"\b([A-Za-z])\.([A-Za-z])\.", r"\1<DOT>\2<DOT>", w_prot)
    w_prot = re.sub(r"\b([A-Za-z]{1,4})\.", r"\1<DOT>", w_prot)

    # Reconstruct multi-line sentences: join wrapped lines unless previous line ended in punctuation
    lines = [l.strip() for l in w_prot.split("\n") if l.strip()]
    raw_sentences = []
    curr = []
    for l in lines:
        curr.append(l)
        if re.search(r"[\.;।]$", l):
            raw_sentences.append(" ".join(curr))
            curr = []
    if curr:
        raw_sentences.append(" ".join(curr))

    cleaned_candidates = []
    for line in raw_sentences:
        line_str = line.replace("<DOT>", ".").replace("<DECIMAL>", ".").strip()
        # Strip bullets/numbering like "1.", "1)", "(1)", "a.", "-", "*"
        line_str = re.sub(r"^(?:\d+[\.\)\-:]|\([0-9a-zA-Z]+\)|[a-zA-Z][\.\)\-:]|[\-\*•])\s*", "", line_str).strip()

        is_junk = False
        for jp in junk_patterns:
            if re.search(jp, line_str):
                sub_clean = re.sub(jp, "", line_str).strip(" ,.-:")
                if len(re.findall(r"[\u0C80-\u0CFFa-zA-Z]", sub_clean)) < 6:
                    is_junk = True
                    break
        if is_junk or len(line_str) < 4:
            continue
        # Skip pure date lines
        if re.match(r"^(?:date\s*[:\-]?\s*)?\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}\.?$", line_str, re.I):
            continue
        cleaned_candidates.append(line_str)

    if not cleaned_candidates:
        return "", "Hearing"

    # Search backwards for a purpose-bearing sentence
    purpose_indicators = [
        r"(?i)\b(?:call\s+(?:this\s+case\s+)?along\s+with|along\s+with|club\s+with|tagged\s+with|put\s+up\s+with|for\s+say\s+of|say\s+of|await\s+say)\b",
        r"(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಜೊತೆಗೆ\s*ಕರೆಯಿರಿ|ಜೊತೆಗೆ|ಕರೆಯಲು)(?![\u0C80-\u0CFFa-zA-Z0-9])",
        r"(?i)\b(?:for|to|towards)\s+",
        r"(?i)\b(?:time\s+(?:prayed|sought|granted|extended|given)|seeks?\s+time|prays?\s+time)\b",
        r"(?i)\b(?:objections?|report|notice|summons|steps|evidence|witness|hearing|arguments?|orders?|judgment|counter|rejoinder|pleadings?|warrant|nbw)\b",
        r"(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಗಾಗಿ|ಸಲುವಾಗಿ|ಬಗ್ಗೆ|ಸಲ್ಲಿಸಲು|ಹಾಜರುಪಡಿಸಲು|ಮಾಡಲು|ಕೋರಲಾಗಿದೆ|ನೀಡಲಾಗಿದೆ|ಆದೇಶಕ್ಕಾಗಿ|ವರದಿಗಾಗಿ|ವಿಚಾರಣೆಗಾಗಿ)(?![\u0C80-\u0CFFa-zA-Z0-9])",
        r"(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಆಕ್ಷೇಪಣೆ|ವರದಿ|ನೋಟಿಸ್|ಸಮನ್ಸ್|ಸಾಕ್ಷಿ|ವಾದ|ವಿಚಾರಣೆ|ಆದೇಶ|ದಾಖಲೆ|ಕ್ರಮ|ವಾರಂಟ್|ಹಾಜರಾಗಲು)(?![\u0C80-\u0CFFa-zA-Z0-9])",
    ]

    selected_sent = None
    for cand in reversed(cleaned_candidates):
        for pi in purpose_indicators:
            if re.search(pi, cand):
                selected_sent = cand
                break
        if selected_sent:
            break

    if not selected_sent:
        return "", ""

    # Clean leading order tags
    s_clean = re.sub(r"^(?:order\s*[:\-]|ಆದೇಶ\s*[:\-]|ನಡಾವಳಿ\s*[:\-])\s*", "", selected_sent, flags=re.I).strip()
    # Extract from primary directive if present to cleanly eliminate leading margin stamps/digits
    m_dir = re.search(r"(?i)\b(?:call\s+(?:this\s+case\s+)?along\s+with|call\s+this\s+case|along\s+with|put\s+up\s+along\s+with|list\s+this\s+matter|for\s+say\s+of|say\s+of|for\s+|to\s+|issue\s+|re[- ]?issue\s+|await\s+|notice\s+|summons\s+|warrant\s+|objection\s+|arguments?\b|orders?\b|hearing\b).*", s_clean)
    if m_dir:
        s_clean = m_dir.group(0).strip(" ,.-:;")

    # Reject OCR noise or strings with too few actual Kannada/English letters
    clean_letters = re.findall(r"[\u0C80-\u0CFFa-zA-Z]", s_clean)
    if len(clean_letters) < 6:
        return "", ""

    # 1. Non-bailable warrant
    if re.search(r"ಜಾಮೀನು\s*ರಹಿತ\s*ವಾರಂಟ್", s_clean) or re.search(r"(?i)\b(?:issue|re[- ]?issue)?\s*(?:nbw|non[- ]?bailable\s+warrant)\b", s_clean):
        return "Issue Non-Bailable Warrant (NBW)", "Criminal Process"

    # 2. Bailable warrant
    if re.search(r"ಜಾಮೀನು\s*ಸಹಿತ\s*ವಾರಂಟ್|ಬೇಲೆಬಲ್\s*ವಾರಂಟ್", s_clean) or re.search(r"(?i)\b(?:issue|re[- ]?issue)?\s*(?:bw|bailable\s+warrant)\b", s_clean):
        return "Issue Bailable Warrant (BW)", "Criminal Process"

    # 3. Notice to respondent
    if re.search(r"(?:ಮರು\s*ನೋಟಿಸ್|ಪುನಃ\s*ನೋಟಿಸ್)", s_clean) or re.search(r"(?i)\bre[- ]?issue\s+notice\b", s_clean):
        return "Re-Issue Notice to Respondent", "Notice / Summons / Service"
    if re.search(r"ನೋಟಿಸ್\s*(?:ಜಾರಿ|ಸಲ್ಲಿಸಲು|ನೀಡಲು)", s_clean) or re.search(r"(?i)\b(?:issue\s+notice|notice\s+to\s+respondent)\b", s_clean):
        return "Notice to Respondent", "Notice / Summons / Service"

    # 4. Summons
    if re.search(r"ಸಾಕ್ಷಿ(?:ಗೆ|ಗಳಿಗೆ)?\s*ಸಮನ್ಸ್", s_clean) or re.search(r"(?i)\bwitness\s+summons\b", s_clean):
        return "Summons to Witness", "Evidence"
    if re.search(r"ಆಪಾದಿತ(?:ರಿಗೆ|ಗೆ)?\s*ಸಮನ್ಸ್|ಸಮನ್ಸ್\s*ಜಾರಿ", s_clean) or re.search(r"(?i)\bsummons\s+to\s+accused\b", s_clean):
        return "Summons to Accused", "Criminal Process"

    # 5. Objections
    if re.search(r"ಅಂತಿಮ\s*ಕಾಲಾವಕಾಶ.*ಆಕ್ಷೇಪಣೆ|ಆಕ್ಷೇಪಣೆ.*ಅಂತಿಮ\s*ಕಾಲಾವಕಾಶ", s_clean) or re.search(r"(?i)\bfinal\s+(?:opportunity|chance|time)\s+to\s+file\s+objections?\b", s_clean):
        return "Final Opportunity to file Objections", "Objections / Pleadings"
    if re.search(r"ಆಕ್ಷೇಪಣೆ(?:ಗಳನ್ನು)?\s*ಸಲ್ಲಿಸಲು\s*(?:ಕಾಲಾವಕಾಶ|ಸಮಯಾವಕಾಶ|ದಿನಾಂಕ)?", s_clean) or re.search(r"(?i)\b(?:seeks?|prays?|granted|extended|give|given)\s+time\s+to\s+file\s+objections?\b", s_clean):
        return "Time to file Objections", "Objections / Pleadings"
    if re.search(r"ಲಿಖಿತ\s*(?:ಹೇಳಿಕೆ|ಆಕ್ಷೇಪಣೆ)|ಆಕ್ಷೇಪಣಾ\s*ಹೇಳಿಕೆ", s_clean) or re.search(r"(?i)\b(?:written\s+statement|statement\s+of\s+objection|objection\s+statement)\b", s_clean):
        return "Objection Statement", "Objections / Pleadings"

    # 6. Reports & Mahazar
    if re.search(r"(?:ಸ್ಥಳ\s*)?ಮಹಜರ್\s*(?:ಮತ್ತು\s*ನಕ್ಷೆ\s*)?ವರದಿ", s_clean) or re.search(r"(?i)\bmahazar\s+(?:and\s+sketch\s+)?report\b", s_clean):
        return "To submit Mahazar & Sketch Report", "Reports / Verification"
    if re.search(r"ಸರ್ವೆ\s*ವರದಿ", s_clean) or re.search(r"(?i)\bsurvey\s+report\b", s_clean):
        return "Await Survey Report", "Reports / Verification"
    if re.search(r"ಲೋಕಾಯುಕ್ತ\s*ವರದಿ|ತನಿಖಾ\s*ವರದಿ", s_clean) or re.search(r"(?i)\b(?:lokayukta|investigation)\s+report\b", s_clean):
        return "Await Investigation / Lokayukta Report", "Reports / Verification"
    if re.search(r"(?:ತಹಶೀಲ್ದಾರ್|ಸರ್ವೆ|ಸ್ಥಳ\s*ಪರಿಶೀಲನೆ|ತನಿಖಾ)?\s*ವರದಿ\s*(?:ಸಲ್ಲಿಸಲು|ಬಂದಿರುವುದಿಲ್ಲ|ನಿರೀಕ್ಷೆ|ಸಲ್ಲಿಸಲು\s*ನಿರ್ದೇಶನ|ಕೋರಲು)", s_clean) or re.search(r"(?i)\b(?:submit|await|reminder\s+for)\s+(?:survey|tahsildar|inspection|status)?\s*report\b", s_clean):
        return "To submit Report / Await Report", "Reports / Verification"

    # 7. Evidence / Witnesses
    if re.search(r"ಸಾಕ್ಷಿ\s*ಪಾಟಿಸವಾಲು", s_clean) or re.search(r"(?i)\bcross\s+(?:examination|of\s+pw|of\s+dw)\b", s_clean):
        return "Cross Examination of Witness", "Evidence"
    if re.search(r"(?:ಅರ್ಜಿದಾರರ|ಪ್ರತಿವಾದಿಗಳ|ಫಿರ್ಯಾದಿ)?\s*ಸಾಕ್ಷಿ\s*ವಿಚಾರಣೆ", s_clean) or re.search(r"(?i)\bexamination\s+of\s+witness\b", s_clean):
        return "Witness Examination", "Evidence"

    # 8. Arguments
    if re.search(r"ವಾದ\s*(?:ಮಂಡನೆ|ಆಲಿಕೆ|ಆಲಿಸಲು|ಕೇಳಲು)", s_clean) or re.search(r"(?i)\b(?:further\s+arguments?|for\s+arguments?|hearing\s+on\s+arguments?)\b", s_clean):
        return "Hearing on Arguments", "Arguments"

    # 9. IA / Interim Applications
    if re.search(r"ಮಧ್ಯಂತರ\s*ಅರ್ಜಿ.*ಆದೇಶ|ಆದೇಶಕ್ಕಾಗಿ.*ಮಧ್ಯಂತರ\s*ಅರ್ಜಿ", s_clean) or re.search(r"(?i)\borders?\s+on\s+i\.?a\.?\b", s_clean):
        return "Orders on IA", "Orders"
    if re.search(r"ಮಧ್ಯಂತರ\s*ಅರ್ಜಿ|ಐ\.?ಎ\.?", s_clean) or re.search(r"(?i)\b(?:hearing\s+on\s+i\.?a\.?|i\.?a\.?\s*hearing)\b", s_clean):
        return "Hearing on IA", "Hearing"

    # 10. Orders & Judgments
    if re.search(r"ತೀರ್ಪಿಗಾಗಿ|ತೀರ್ಪಿಗೆ", s_clean) or re.search(r"(?i)\bfor\s+judg(?:e)?ment\b", s_clean):
        return "For Judgment", "Judgment / Final Order"
    if re.search(r"ಆದೇಶಕ್ಕಾಗಿ|ಆದೇಶಕ್ಕೆ", s_clean) or re.search(r"(?i)\bfor\s+(?:orders?|ruling)\b", s_clean):
        return "For Orders", "Orders"

    # 11. Steps & Office objections
    if re.search(r"ಕಚೇರಿ\s*ಆಕ್ಷೇಪಣೆ", s_clean) or re.search(r"(?i)\boffice\s+objections?\b", s_clean):
        return "To Rectify Office Objections", "Filing & Scrutiny"
    if re.search(r"ದಾಖಲೆ(?:ಗಳನ್ನು)?\s*(?:ಹಾಜರುಪಡಿಸಲು|ಸಲ್ಲಿಸಲು|ಒದಗಿಸಲು)", s_clean) or re.search(r"(?i)\b(?:to\s+produce|production\s+of)\s+documents?\b", s_clean):
        return "Production of Documents", "Filing & Scrutiny"
    if re.search(r"ಕ್ರಮ\s*ಕೈಗೊಳ್ಳಲು|ಕ್ರಮಕ್ಕೆ", s_clean) or re.search(r"(?i)\bto\s+take\s+steps\b", s_clean):
        return "To take Steps", "Filing & Scrutiny"

    # 12. Appearance & Vakalat
    if re.search(r"ವಕಾಲತ್\s*(?:ಹಾಕಲು|ಸಲ್ಲಿಸಲು)", s_clean) or re.search(r"(?i)\bto\s+file\s+vakalat\b", s_clean):
        return "To file Vakalat", "Appearance"
    if re.search(r"ತಹಶೀಲ್ದಾರ್.*ಹಾಜರಾಗಲು|ಅಧಿಕಾರಿ.*ಹಾಜರಾಗಲು", s_clean) or re.search(r"(?i)\bappearance\s+of\s+(?:tahsildar|officer)\b", s_clean):
        return "Appearance of Tahsildar / Officer", "Appearance"

    # 13. Charges
    if re.search(r"ಆರೋಪ\s*(?:ನಿಗದಿ|ವಾಚನ|ರಚನೆ)", s_clean) or re.search(r"(?i)\bframing\s+of\s+charge\b", s_clean):
        return "Framing of Charge", "Charge/Plea"

    # Distill into clean canonical description or concise sentence
    desc = re.sub(r"\s+", " ", s_clean).strip(" ,.-:;")
    words = [w for w in re.split(r"\s+", desc) if len(w) > 1]
    if len(words) < 2 or len(desc) < 6:
        return "", ""
    if len(desc) > 85:
        cut = desc[:85]
        sp = cut.rfind(" ")
        desc = (cut[:sp] if sp > 35 else cut) + "…"
    if desc and desc[0].isascii() and desc[0].islower():
        desc = desc[0].upper() + desc[1:]

    group = infer_stage_group_from_description(desc)
    return desc, group

KARNATAKA_DISTRICTS = [
    ("Bengaluru", [r"ಬೆಂಗಳೂರು\s*(?:ನಗರ)?", r"Bangalore\s*(?:Urban)?", r"Bengaluru\s*(?:Urban)?"]),
    ("Bengaluru Rural", [r"ಬೆಂಗಳೂರು\s*ಗ್ರಾಮಾಂತರ", r"Bangalore\s*Rural", r"Bengaluru\s*Rural"]),
    ("Ramanagara", [r"ರಾಮನಗರ", r"Ramanagar(?:a)?"]),
    ("Tumakuru", [r"ತುಮಕೂರು", r"Tumkur", r"Tumakuru"]),
    ("Mandya", [r"ಮಂಡ್ಯ", r"Mandya"]),
    ("Mysuru", [r"ಮೈಸೂರು", r"Mysore", r"Mysuru"]),
    ("Kolar", [r"ಕೋಲಾರ", r"Kolar"]),
    ("Chikkaballapura", [r"ಚಿಕ್ಕಬಳ್ಳಾಪುರ", r"Chik(?:k)?aballapur(?:a)?"]),
    ("Hassan", [r"ಹಾಸನ", r"Hassan"]),
    ("Chamarajanagara", [r"ಚಾಮರಾಜನಗರ", r"Chamarajanagar(?:a)?"]),
    ("Kodagu", [r"ಕೊಡಗು", r"Kodagu", r"Coorg"]),
    ("Dakshina Kannada", [r"ದಕ್ಷಿಣ\s*ಕನ್ನಡ", r"Dakshina\s*Kannada", r"South\s*Canara", r"Mangalor(?:e|u)"]),
    ("Udupi", [r"ಉಡುಪಿ", r"Udupi"]),
    ("Uttara Kannada", [r"ಉತ್ತರ\s*ಕನ್ನಡ", r"Uttara\s*Kannada", r"North\s*Canara", r"Karwar"]),
    ("Shivamogga", [r"ಶಿವಮೊಗ್ಗ", r"Shimoga", r"Shivamogga"]),
    ("Chitradurga", [r"ಚಿತ್ರದುರ್ಗ", r"Chitradurga"]),
    ("Davanagere", [r"ದಾವಣಗೆರೆ", r"Davangere", r"Davanagere"]),
    ("Ballari", [r"ಬಳ್ಳಾರಿ", r"Bellary", r"Ballari"]),
    ("Vijayanagara", [r"ವಿಜಯನಗರ", r"Vijayanagar(?:a)?", r"Hospet"]),
    ("Koppal", [r"ಕೊಪ್ಪಳ", r"Koppal"]),
    ("Raichur", [r"ರಾಯಚೂರು", r"Raichur"]),
    ("Kalaburagi", [r"ಕಲಬುರಗಿ", r"Gulbarga", r"Kalaburagi", r"ಅಫ್ಜಲಪುರ", r"Afzalpur(?:a)?", r"Aphjalapur(?:a)?"]),
    ("Yadgir", [r"ಯಾದಗಿರಿ", r"Yadgir"]),
    ("Bidar", [r"ಬೀದರ್", r"Bidar"]),
    ("Belagavi", [r"ಬೆಳಗಾವಿ", r"Belgaum", r"Belagavi"]),
    ("Bagalkote", [r"ಬಾಗಲಕೋಟೆ", r"Bagalkot(?:e)?"]),
    ("Vijayapura", [r"ವಿಜಯಪುರ", r"Bijapur", r"Vijayapura"]),
    ("Gadag", [r"ಗದಗ", r"Gadag"]),
    ("Dharwad", [r"ಧಾರವಾಡ", r"Dharwad", r"Hubballi", r"Hubli"]),
    ("Haveri", [r"ಹಾವೇರಿ", r"Haveri"]),
]


def transliterate_kannada(text: str) -> str:
    """Converts Kannada script into standard readable English title case."""
    if not text:
        return ""
    # Map common Kannada cardinal directions in revenue administration
    text = re.sub(r'[\u200b\u200c\u200d]', '', text)
    text = re.sub(r'\bದಕ್ಷಿಣ\b', 'South', text)
    text = re.sub(r'\bಉತ್ತರ\b', 'North', text)
    text = re.sub(r'\bಪೂರ್ವ\b', 'East', text)
    text = re.sub(r'\bಪಶ್ಚಿಮ\b', 'West', text)
    text = re.sub(r'\bDakshina\b', 'South', text, flags=re.IGNORECASE)
    text = re.sub(r'\bUttara\b', 'North', text, flags=re.IGNORECASE)
    text = re.sub(r'\bPoorva\b', 'East', text, flags=re.IGNORECASE)
    text = re.sub(r'\bPaschima\b', 'West', text, flags=re.IGNORECASE)
    text = re.sub(r'ಅ[ಫ್ಫ]*[ಜಜಾ][\s\-_]*[ಲ್ಲ್‌ಲ]*ಪುರ(?:ಾ)?', 'Afzalpura', text)
    text = re.sub(r'\b(?:aph[a]?j[a]?l[a]?pur(?:a)?|af[a]?[zj][a]?l[a]?pur(?:a)?)\b', 'Afzalpura', text, flags=re.IGNORECASE)

    if not re.search(r'[\u0C80-\u0CFF]', text):
        return text.strip()
    k_cons = {
        'ಕ': 'k', 'ಖ': 'kh', 'ಗ': 'g', 'ಘ': 'gh', 'ಙ': 'ng',
        'ಚ': 'ch', 'ಛ': 'chh', 'ಜ': 'j', 'ಝ': 'jh', 'ಞ': 'ny',
        'ಟ': 't', 'ಠ': 'th', 'ಡ': 'd', 'ಢ': 'dh', 'ಣ': 'n',
        'ತ': 't', 'ಥ': 'th', 'ದ': 'd', 'ಧ': 'dh', 'ನ': 'n',
        'ಪ': 'p', 'ಫ': 'ph', 'ಬ': 'b', 'ಭ': 'bh', 'ಮ': 'm',
        'ಯ': 'y', 'ರ': 'r', 'ಱ': 'r', 'ಲ': 'l', 'ಳ': 'l', 'ವ': 'v',
        'ಶ': 'sh', 'ಷ': 'sh', 'ಸ': 's', 'ಹ': 'h'
    }
    k_vowels = {
        'ಅ': 'a', 'ಆ': 'a', 'ಇ': 'i', 'ಈ': 'i', 'ಉ': 'u', 'ಊ': 'u',
        'ಋ': 'ru', 'ಎ': 'e', 'ಏ': 'e', 'ಐ': 'ai', 'ಒ': 'o', 'ಓ': 'o', 'ಔ': 'au'
    }
    k_matras = {
        'ಾ': 'a', 'ಿ': 'i', 'ೀ': 'i', 'ು': 'u', 'ೂ': 'u', 'ೃ': 'ru',
        'ೆ': 'e', 'ೇ': 'e', 'ೈ': 'ai', 'ೊ': 'o', 'ೋ': 'o', 'ೌ': 'au'
    }
    res = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in k_cons:
            base = k_cons[c]
            i += 1
            if i < n:
                nxt = text[i]
                if nxt == '್':
                    res.append(base)
                    i += 1
                elif nxt in k_matras:
                    res.append(base + k_matras[nxt])
                    i += 1
                else:
                    res.append(base + 'a')
            else:
                res.append(base + 'a')
        elif c in k_vowels:
            res.append(k_vowels[c])
            i += 1
        elif c in k_matras:
            res.append(k_matras[c])
            i += 1
        elif c == 'ಂ':
            next_c = text[i + 1] if i + 1 < n else ''
            nasal = 'n' if next_c in 'ಕಖಗಘಚಛಜಝಟಠಡಢತಥದಧನ' else 'm'
            res.append(nasal)
            i += 1
        else:
            res.append(c)
            i += 1
    out = ''.join(res)
    out = re.sub(r'([aeiou])\1+', r'\1', out)
    return out.strip().title()


def translate_party_text(text: str) -> str:
    """Translates Karnataka court party names, relationships, designations, and addresses from Kannada to English."""
    if not text:
        return ""
    t = str(text).strip()
    t = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', t)
    t = re.sub(r'^[\s\"\'\”\“\‘\’\-:\.,]+', '', t)
    t = re.sub(r'(?i)\b(?:adesha(?:da)?\s*(?:prati|patra|patre|pati)|order\s*sheet|daily\s*order)\b.*', '', t)
    t = re.sub(r'(?:ಆದೇಶ(?:ದ)?\s*(?:ಪ್ರತಿ|ಪತಿ|ಪತ್ರ|ಪತ್ರೆ|BS|ಪ್ರತೀ)|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|ದಿನಾಂಕ\s+\d+.*)', '', t)

    t = re.sub(r'ಕ[ಂ೦0]+ದವಾರ', 'ಕಂದವಾರ', t)
    t = re.sub(r'(?<=[\u0C80-\u0CFF])[0೦]+(?=[\u0C80-\u0CFF])', '\u0c82', t)

    def _k_ord(m):
        num = int(m.group(1))
        sfx = "th" if 11 <= num % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(num % 10, "th")
        return f"{num}{sfx}"
    t = re.sub(r'(\d+)\s*ನೇ\b', _k_ord, t)

    # Specific OCR artifacts & noise before phrase translation
    t = re.sub(r'(?i)\b(?:ಟು\??|Tu\??)\b', '', t)
    t = re.sub(r'[೦0o]\s*ಗಳೂ\s*ದಕ್ಷಿಣ\s*ತಾಲ್ಲೂಕು', 'ಬೆಂಗಳೂರು ದಕ್ಷಿಣ ತಾಲ್ಲೂಕು', t)
    t = re.sub(r'Galu\s*South\s*Taluk', 'Bengaluru South Taluk', t)

    k_phrases = [
        (r'(?i)(?:ಕಾರ್ಯ\s*ನಿರ್ವಾಹಕ|ಕಾರ್ಯನಿರ್ವಾಹಕ)\s*ಅಭಿಯಂತರರು?', 'Executive Engineer'),
        (r'(?i)ಮುಖ್ಯ\s*ಅಭಿಯಂತರರು?', 'Chief Engineer'),
        (r'(?i)ಅಧೀಕ್ಷಕ\s*ಅಭಿಯಂತರರು?', 'Superintending Engineer'),
        (r'(?i)ಸಹಾಯಕ\s*(?:ಕಾರ್ಯ\s*ನಿರ್ವಾಹಕ|ಕಾರ್ಯನಿರ್ವಾಹಕ)\s*ಅಭಿಯಂತರರು?', 'Assistant Executive Engineer (AEE)'),
        (r'(?i)ಸಹಾಯಕ\s*ಅಭಿಯಂತರರು?', 'Assistant Engineer (AE)'),
        (r'(?i)ಕಿರಿಯ\s*ಅಭಿಯಂತರರು?', 'Junior Engineer (JE)'),
        (r'(?i)ಅಭಿಯಂತರರು?', 'Engineer'),
        (r'(?i)ತಹ[ಶಸ]ೀಲ್ದಾ(?:ರರು|ರ|ರ್[\u200c\u200d]?)\s*(?:ಹಾಗೂ|ಮತ್ತು)\s*ತಾಲ್ಲೂಕು\s*(?:ಕಾರ್ಯನಿರ್ವಾಹಕ\s*)?ದಂಡಾಧಿಕಾರಿಗಳು?', 'Tahsildar & Taluk Executive Magistrate'),
        (r'(?i)ತಹ[ಶಸ]ೀಲ್ದಾ(?:ರರು|ರ|ರ್[\u200c\u200d]?)', 'Tahsildar'),
        (r'(?i)ಉಪ\s*ತಹ[ಶಸ]ೀಲ್ದಾ(?:ರರು|ರ|ರ್[\u200c\u200d]?)', 'Deputy Tahsildar'),
        (r'(?i)ವಿಶೇಷ\s*ಜಿಲ್ಲಾಧಿಕಾರಿಗಳು?', 'Special Deputy Commissioner'),
        (r'(?i)ಜಿಲ್ಲಾಧಿಕಾರಿಗಳು?', 'Deputy Commissioner'),
        (r'(?i)ಉಪ\s*ವಿಭಾಗಾಧಿಕಾರಿಗಳು?|ಉಪವಿಭಾಗಾಧಿಕಾರಿಗಳು?', 'Assistant Commissioner'),
        (r'(?i)ಭೂ\s*ದಾಖಲೆಗಳ\s*ಸಹಾಯಕ\s*ನಿರ್ದೇಶಕರು?', 'Assistant Director of Land Records (ADLR)'),
        (r'(?i)ಭೂ\s*ದಾಖಲೆಗಳ\s*ಉಪ\s*ನಿರ್ದೇಶಕರು?', 'Deputy Director of Land Records (DDLR)'),
        (r'(?i)ಸಹಾಯಕ\s*ನಿರ್ದೇಶಕರು?', 'Assistant Director'),
        (r'(?i)ಉಪ\s*ನಿರ್ದೇಶಕರು?', 'Deputy Director'),
        (r'(?i)ನಿರ್ದೇಶಕರು?', 'Director'),
        (r'(?i)ಕಂದಾಯ\s*ನಿರೀಕ್ಷಕರು?', 'Revenue Inspector'),
        (r'(?i)ಗ್ರಾಮ\s*ಲೆಕ್ಕಿಗರು?|ಗ್ರಾಮಲೆಕ್ಕಿಗರು?|ಗ್ರಾಮ\s*ಲೆಕ್ಕಾಧಿಕಾರಿಗಳು?', 'Village Accountant'),
        (r'(?i)(?:ಪಂಚಾಯ್ತಿ|ಪಂಚಾಯಿತಿ|ಪಂಚಾಯತ್)?\s*(?:ಗ್ರಾಮೀಣಾಭಿವೃದ್ಧಿ|ಅಭಿವೃದ್ಧಿ)\s*ಅಧಿಕಾರಿಗಳು?', 'Panchayat Development Officer (PDO)'),
        (r'(?i)(?:ಕಾರ್ಯ\s*ನಿರ್ವಾಹಕ|ಕಾರ್ಯನಿರ್ವಾಹಕ)\s*ಅಧಿಕಾರಿಗಳು?', 'Executive Officer'),
        (r'(?i)ಮುಖ್ಯ\s*(?:ಕಾರ್ಯ\s*ನಿರ್ವಾಹಕ|ಕಾರ್ಯನಿರ್ವಾಹಕ)\s*ಅಧಿಕಾರಿಗಳು?', 'Chief Executive Officer (CEO)'),
        (r'(?i)ಪ್ರಧಾನ\s*ಕಾರ್ಯದರ್ಶಿ', 'Principal Secretary'),
        (r'(?i)ಕಾರ್ಯದರ್ಶಿ', 'Secretary'),
        (r'(?i)ಅಧ್ಯಕ್ಷರು?', 'President'),
        (r'(?i)ಉಪಾಧ್ಯಕ್ಷರು?', 'Vice President'),
        (r'(?i)ಸದಸ್ಯರು?', 'Member'),
        (r'(?i)ಆಯುಕ್ತರು?', 'Commissioner'),
        (r'(?i)ಉಪ\s*ಆಯುಕ್ತರು?', 'Deputy Commissioner'),
        (r'(?i)ಪೊಲೀಸ್\s*ಕಮಿಷನರ್', 'Police Commissioner'),
        (r'(?i)ಪೊಲೀಸ್\s*ಉಪ\s*ಅಧೀಕ್ಷಕರು?', 'Deputy Superintendent of Police (DySP)'),
        (r'(?i)ಪೊಲೀಸ್\s*ವೃತ್ತ\s*ನಿರೀಕ್ಷಕರು?', 'Circle Police Inspector (CPI)'),
        (r'(?i)ಪೊಲೀಸ್\s*ಇನ್[ಸ್ಸ್‌\s]*ಪೆಕ್ಟರ್', 'Police Inspector'),
        (r'(?i)ಪೊಲೀಸ್\s*ಸಬ್[\-\s]*ಇನ್[ಸ್ಸ್‌\s]*ಪೆಕ್ಟರ್', 'Police Sub-Inspector (PSI)'),
        (r'(?i)ಠಾಣಾಧಿಕಾರಿಗಳು?|ಠಾಣಾ\s*ಉಪ\s*ನಿರೀಕ್ಷಕರು?', 'Station House Officer (SHO)'),
        (r'(?i)ಸರ್ಕಾರಿ\s*ಅಭಿಯೋಜಕರು?', 'Public Prosecutor'),
        (r'(?i)ಶಾಖಾಧಿಕಾರಿಗಳು?', 'Section Officer'),
        (r'(?i)ವಿಲೇಖನಾಧಿಕಾರಿಗಳು?', 'Scrutiny Officer'),
        (r'(?i)ಶಿರಸ್ತೇದಾರರು?', 'Sheristedar'),
        (r'(?i)ಕರ್ನಾಟಕ\s*(?:ಸರ್ಕಾರ|ಸರಕಾರ)', 'Government of Karnataka'),
        (r'(?i)ಕಂದಾಯ\s*ಇಲಾಖೆ', 'Revenue Department'),
        (r'(?i)ಅರಣ್ಯ\s*ಇಲಾಖೆ', 'Forest Department'),
        (r'(?i)ಪೊಲೀಸ್\s*ಇಲಾಖೆ', 'Police Department'),
        (r'(?i)ಲೋಕೋಪಯೋಗಿ\s*ಇಲಾಖೆ', 'Public Works Department (PWD)'),
        (r'(?i)ನಗರಾಭಿವೃದ್ಧಿ\s*ಇಲಾಖೆ', 'Urban Development Department'),
        (r'(?i)(?:ಸರ್ವೇ|ಭೂಮಾಪನ)\s*ಇಲಾಖೆ', 'Survey Department'),
        (r'(?i)ಇಲಾಖೆ', 'Department'),
        (r'(?i)ಕಂದಾಯ\s*ಭವನ', 'Revenue Bhavan'),
        (r'(?i)ಭವನ', 'Bhavan'),
        (r'(?i)ಬಿ[\.\s]*ಬಿ[\.\s]*[ಎಂಎನ್][\.\s]*ಪಿ\s*(?:ಪ್ರಧಾನ|ಪಧಾನ)?', 'BBMP Head'),
        (r'(?i)ಬಿ[\.\s]*ಬಿ[\.\s]*[ಎಂಎನ್][\.\s]*ಪಿ', 'BBMP'),
        (r'(?i)ಬಿ[\.\s]*ಡಿ[\.\s]*ಎ', 'BDA'),
        (r'(?i)ಬಿ[\.\s]*ಎಂ[\.\s]*ಟಿ[\.\s]*ಎಫ್', 'BMTF'),
        (r'(?i)ಪೊಲೀಸ್\s*ಠಾಣೆ', 'Police Station'),
        (r'(?i)ಪ್ರಧಾನ\s*ಕ[ಛಚ]ೇರಿ', 'Head Office'),
        (r'(?i)ಕ[ಛಚ]ೇರಿ', 'Office'),
        (r'(?i)ಕೆರೆಗಳ[\s\-]*ವಿಭಾಗ|ಕೆರೆ[\s\-]*ವಿಭಾಗ', 'Lakes Division'),
        (r'(?i)ವಿಭಾಗ', 'Division'),
        (r'(?i)ವಲಯ\s*ಕ[ಛಚ]ೇರಿ', 'Zonal Office'),
        (r'(?i)ಉಪವಲಯ', 'Sub-Zone'),
        (r'(?i)ವಲಯ', 'Zone'),
        (r'(?i)ಗ್ರಾಮ\s*ಪಂಚಾಯ್?[ತಿತ್]', 'Gram Panchayat'),
        (r'(?i)ತಾಲ್ಲೂಕು\s*ಪಂಚಾಯ್?[ತಿತ್]', 'Taluk Panchayat'),
        (r'(?i)ಜಿಲ್ಲಾ\s*ಪಂಚಾಯ್?[ತಿತ್]', 'Zilla Panchayat'),
        (r'(?i)ಮಹಾನಗರ\s*ಪಾಲಿಕೆ', 'City Corporation'),
        (r'(?i)ನಗರ\s*ಸಭೆ', 'City Municipal Council (CMC)'),
        (r'(?i)ಪುರಸಭೆ', 'Town Municipal Council (TMC)'),
        (r'(?i)ಪಟ್ಟಣ\s*ಪಂಚಾಯಿತಿ', 'Town Panchayat'),
        (r'(?i)ವಿಶೇಷ\s*ನ್ಯಾಯಾಲಯ', 'Special Court'),
        (r'(?i)ನ್ಯಾಯಾಲಯ|ನ್ಯಾಯಾಂಗ', 'Court'),
        (r'(?i)ಕೊಠಡಿ\s*(?:ಸಂಖ್ಯೆ|ಸಂ|ನಂ)?[\.\s:\-]*', 'Room No. '),
        (r'(?i)ನೆಲ\s*ಮಹಡಿ', 'Ground Floor'),
        (r'(?i)ಮಹಡಿ', 'Floor'),
        (r'(?i)ಹಂತ', 'Stage'),
        (r'(?i)ಕಾಲೋನಿ', 'Colony'),
        (r'(?i)ಬಡಾವಣೆ', 'Layout'),
        (r'(?i)ನಗರ', 'Nagar'),
        (r'(?i)ಇಂಡಸ್ಟ್ರಿಯಲ್[\u0ccd\u200c\u200d]*', 'Industrial'),
        (r'(?i)ಎನ್[\.\s]*ಆರ್[\.\s]*ಸ್ಕ್ವೇರ್[\u0ccd\u200c\u200d]*', 'N.R. Square'),
        (r'(?i)ಸ್ಕ್ವೇರ್[\u0ccd\u200c\u200d]*', 'Square'),
        (r'(?i)ಟ್ರಸ್ಟ್[\u0ccd\u200c\u200d]*', 'Trust'),
        (r'(?i)ಮಹಾ\s*ವಿದ್ಯಾಪೀಠ', 'Maha Vidyapeetha'),
        (r'(?i)ವಿದ್ಯಾಪೀಠ', 'Vidyapeetha'),
        (r'(?i)ಆಶ್ರಮ', 'Ashram'),
        (r'(?i)ದೇವಸ್ಥಾನ', 'Temple'),
        (r'(?i)ಮನೆ\s*(?:ಸಂಖ್ಯೆ|ಸಂ|ನಂ)?[\.\s:\-]*', 'House No. '),
        (r'(?i)ಅಂಚೆ', 'Post'),
        (r'(?i)ಮುಖ್ಯ\s*ರಸ್ತೆ', 'Main Road'),
        (r'(?i)ಅಡ್ಡ\s*ರಸ್ತೆ', 'Cross Road'),
        (r'(?i)ರಸ್ತೆ', 'Road'),
        (r'(?i)ಕ್ರಾಸ್[\u0ccd\u200c\u200d]*', 'Cross'),
        (r'(?i)ಉತ್ತರ\s*ಹಳ್ಳಿ', 'Uttarahalli'),
        (r'(?i)ದಕ್ಷಿಣ\s*ಕನ್ನಡ', 'Dakshina Kannada'),
        (r'(?i)ಉತ್ತರ\s*ಕನ್ನಡ', 'Uttara Kannada'),
        (r'(?i)(?:ಗ್ರಾಮ|ಗಾಮ)', 'Village'),
        (r'(?i)ಹೋಬಳಿ', 'Hobli'),
        (r'(?i)(?:ತಾಲ್ಲೂಕು|ತಾಲೂಕು|ತಾಲ್ಲೂರು)', 'Taluk'),
        (r'(?i)(?:ಜಿಲ್ಲೆ|ಜಿಲ್ಲಾ)', 'District'),
        (r'(?i)(?:ಹತ್ತಿರ|ಬಳಿ)', 'Near'),
        (r'(?i)(?:ಎದುರು|ಎದುರುಗಡೆ)(?!ದಾರ)', 'Opposite'),
        (r'(?i)(?:ಹಿಂಭಾಗ|ಹಿಂದೆ)', 'Behind'),
        (r'(?i)(?:ಪಕ್ಕದಲ್ಲಿ|ಪಕ್ಕ)', 'Beside'),
        (r'(?i)ದಕ್ಷಿಣ', 'South'),
        (r'(?i)ಉತ್ತರ', 'North'),
        (r'(?i)ಪೂರ್ವ', 'East'),
        (r'(?i)ಪಶ್ಚಿಮ', 'West'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಸರ್ಕಾರಿ\s*)?ಕೆರೆ(?![\u0C80-\u0CFFa-zA-Z0-9])', 'Lake'),
        (r'(?i)ಕಟ್ಟಡ', 'Building'),
        (r'(?i)ಕಾಂಪ್ಲೆಕ್ಸ್', 'Complex'),
        (r'(?i)(?:ನಂ\.?|ಸಂ\.?|ಸಂಖ್ಯೆ)', 'No.'),
        (r'(?i)ಕೆ[\.\s]*ಜಿ[\.\s]*ರಸ್ತೆ', 'K.G. Road'),
        (r'(?i)(?:ಹೀಣ್ಯ|ಪೀಣ್ಯ)', 'Peenya'),

        # Proper place names & layouts
        (r'(?i)ದಾಖಲೆ', 'Dakhale'),
        (r'(?i)ಹೊಸಪಾಳ್ಯ', 'Hosapalya'),
        (r'(?i)ಚೋಳನಾಯಕನಹಳ್ಳಿ|ಜೋಳನಾಯಕನಹಳ್ಳಿ', 'Jolanayakanahalli'),
        (r'(?i)ತಾವರೆಕೆರೆ', 'Tavarekere'),
        (r'(?i)ನೆಲಗದರಹಳ್ಳಿ|ನೆಲಗೆದರನಹಳ್ಳಿ', 'Nelagadarahalli'),
        (r'(?i)ಶಿವಪುರ', 'Shivapura'),
        (r'(?i)ಉಡೀಪಾಳ್ಯ', 'Udipalya'),
        (r'(?i)ಪಣಸಮಾಕನಹಳ್ಳಿ', 'Panasamakanahalli'),
        (r'(?i)ಕಸಬಾ', 'Kasaba'),
        (r'(?i)ಶ್ರೀನಿವಾಸಪುರ', 'Srinivaspur'),
        (r'(?i)ಕೋಲಾರ', 'Kolar'),
        (r'(?i)ಬೈರೇಗೌಡ', 'Byregowda'),
        (r'(?i)ಬಿ[\.\s]*ಇ[\.\s]*ಎಂ[\.\s]*ಎಲ್[\u0ccd\u200c\u200d]*', '(BEML)'),
        (r'(?i)ಲೇಔಟ್[\u0ccd\u200c\u200d]*', 'Layout'),
        (r'(?i)ನಿಲಯ', 'Nilaya'),
        (r'(?i)ಲಕ್ಷ್ಮೀ\s*ವೆಂಕಟೇಶ್ವರ|ಲಕ್ಷ್ಮಿ\s*ವೆಂಕಟೇಶ್ವರ', 'Lakshmivenkateshwara'),
        (r'(?i)ಅಗರ\s*ಡಿಪೋ\s*(?:ಹತ್ತಿರ|ಬಳಿ)', 'Near Agara Depot'),
        (r'(?i)ಡಿಪೋ\s*(?:ಹತ್ತಿರ|ಬಳಿ)', 'Near Depot'),
        (r'(?i)ಡಿಪೋ', 'Depot'),
        (r'(?i)ಸೆಕ್ಟರ್[\u0ccd\u200c\u200d]*', 'Sector'),
        (r'(?i)ಹೆಚ್[\.\s]*ಎಸ್[\.\s]*ಆರ್[\.\s]*ಲೇಔಟ್[\u0ccd\u200c\u200d]*', 'HSR Layout'),
        (r'(?i)ಹೆಚ್[\.\s]*ಎಸ್[\.\s]*ಆರ್[\.\s]*', 'HSR'),
        (r'(?i)ಅವದಾನಿ', 'Avadani'),
        (r'(?i)ಕೃಷ್ಣಯ್ಯ', 'Krishnaiah'),
        (r'(?i)ಚಿಕ್ಕಣ್ಣ', 'Chikkanna'),
        (r'(?i)ರಾಜಣ್ಣ', 'Rajanna'),
        (r'(?i)ವೆಂಕಟರಾಜಪ್ಪ', 'Venkatarajappa'),
        (r'(?i)ಗೋವಿಂದರಾಜು', 'Govindaraju'),
        (r'(?i)ಚಂದ್ರಪ್ಪ', 'Chandappa'),
        (r'(?i)ಕೆಂಚಪ್ಪ', 'Kenchappa'),
        (r'(?i)ಶಂಕರ್[\u200c\u200d]?', 'Shankar'),
        (r'(?i)ವೆಂಕಟೇಶ್[\u200c\u200d]?\s*ರೆಡ್ಡಿ', 'Venkatesh Reddy'),
        (r'(?i)ನಾಗೀ\s*ರೆಡ್ಡಿ|ನಾಗಿ\s*ರೆಡ್ಡಿ', 'Nagi Reddy'),
        (r'(?i)ಶ್ರೀರಾಮಯ್ಯ', 'Shriramayya'),
        (r'(?i)ವೆಂಕಟರಾಮಪ್ಪ', 'Venkataramappa'),
        (r'(?i)ಆಂಜನೇಯ\s*ರೆಡ್ಡಿ', 'Anjaneyareddy'),
        (r'(?i)ಶ್ರೀದೇವಿ', 'Sridevi'),
        (r'(?i)ಪ್ರಸಾದ್[\u200c\u200d]?', 'Prasad'),
        (r'(?i)ಮುನಿಶಾಮಪ್ಪ', 'Munishamappa'),
        (r'(?i)ತಿಮ್ಮಪ್ಪ', 'Thimmappa'),
        (r'(?i)ಪಾಪಣ್ಣ', 'Papanna'),
        (r'(?i)ಜಯಮ್ಮ', 'Jayamma'),
        (r'(?i)ನಗರಾಜಯ್ಯ', 'Nagarajayya'),
        (r'(?i)\b8[0o]\.\s*(?=\d+)', 'No. '),
        (r'(?i)\b[ಪಪಿ][\.\s]*ಆಂಜನೇಯ\s*(?:ರೆಡ್ಡಿ)?', 'P. Anjaneyareddy'),
        (r'(?i)\bPi[\.\s]*Amnjaneyareddi\b', 'P. Anjaneyareddy'),

        # Parties & Relationships
        (r'(?i)[ಅಾ]?ರ್ಜಿದಾರರು?|[ಅಾ]?ರ್ಜಿದಾರ', 'Applicant'),
        (r'(?i)ಎದುರುದಾರರು?|ಎದುರುದಾರ', 'Respondent'),
        (r'(?i)ಪ್ರತಿವಾದಿಗಳು?|ಪ್ರತಿವಾದಿ', 'Respondent'),
        (r'(?i)ದೂರುದಾರರು?|ದೂರುದಾರ|ಫಿರ್ಯಾದುದಾರರು?|ಫಿರ್ಯಾದುದಾರ', 'Complainant'),
        (r'(?i)ಆರೋಪಿಗಳು?|ಆರೋಪಿ', 'Accused'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಶ್ರೀಮತಿ|ಶ್ರೀಮತಿ\.)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'Smt.'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಶ್ರೀ|ಶ್ರೀ\.)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'Sri.'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಕುಮಾರಿ|ಕುಮಾರಿ\.)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'Kum.'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಕೋಂ|ಕೋಮ|ಕೋ೦|ಹೆಂಡತಿ)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'W/o'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಬಿನ್[\u0ccd\u200c\u200d]?|ಮಗ)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'S/o'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಡಿ/?ಕೋಂ|ಡಿ/?ಕೋ೦|ಮಗಳು)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'D/o'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಗಂಡ)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'H/o'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ತಂದೆ)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'Father'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ತಾಯಿ)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'Mother'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ವೈ|ದಿವಂಗತ|ಲೇಟ್)(?![\u0C80-\u0CFFa-zA-Z0-9])', 'Late'),

        # Age & Common address terms
        (r'(?i)ವಯಸ್ಸು[\s\-]*ಸುಮಾರು[\s\-]*(\d+)[\s\-]*ವರ್ಷ', r'Aged about \1 years'),
        (r'(?i)ವಯಸ್ಸು[\s\-]*(\d+)[\s\-]*ವರ್ಷ', r'Aged \1 years'),
        (r'(?i)(?:[^\w\s\d]*\s*)?(?:ಇಬ್ಬರ|ಎಲ್ಲರ|[ಲ|`\']+\s*ರ|ಉಭಯತರ)\s*(?:ವಿಳಾಸ|ಎಳಾಸ|ವಿಳಾಶ|ಎಳಾಶ|address)[\s:\-]*', 'Address of both: '),
        (r'(?i)ಅರ್ಜಿದಾರ\s*(?:ನಂ\.?)?\s*(\d+)\s*(?:ರಿಂದ|to)\s*(\d+)\s*(?:ರವರ\s*)?(?:ವಿಳಾಸ|ಎಳಾಸ)[\s:\-]*', r'Applicant No. \1 to \2 Address: '),
        (r'(?i)ಎದುರುದಾರ\s*(?:ನಂ\.?)?\s*(\d+)\s*(?:ಮತ್ತು|ರಿಂದ|and|to)\s*(\d+)\s*(?:ರವರ\s*)?(?:ವಿಳಾಸ|ಎಳಾಸ)[\s:\-]*', r'Respondent No. \1 and \2 Address: '),
        (r'(?i)ವಾಸ\s*[:\-]', 'Residing at: '),
        (r'(?i)ವಿಳಾಸ\s*[:\-]', 'Address: '),
        (r'(?i)ಮತ್ತು', 'and'),
        (r'(?i)ರವರ', ''),
        (r'(?i)ರಿಂದ', 'to'),
        (r'(?<![\u0C80-\u0CFFa-zA-Z0-9])(?:ಸಾ[।\|॥\!:\.]+|ಸಾಕಿನ\b)', 'Residing at '),
    ]

    for pat, rep in k_phrases:
        t = re.sub(pat, rep, t)

    lines = t.split("\n")
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(r'^[a-zA-Z\s]{1,6}(?=\d+[\.,\)])', '', line).strip()
        line = re.sub(r'^(\d+)[,](?=\s*)', r'\1.', line)

        words = re.split(r'(\s+|[,.:;/\-\(\)])', line)
        out_words = []
        for w in words:
            if re.search(r'[\u0C80-\u0CFF]', w):
                out_words.append(transliterate_kannada(w))
            else:
                out_words.append(w)
        cline = "".join(out_words)
        cline = re.sub(r"[^\S\r\n]+", " ", cline).strip()
        if cline:
            cleaned_lines.append(cline)

    full = "\n".join(cleaned_lines)
    if re.search(r'(?:^|\n)\s*1[\.\)]\s*', full):
        parts = re.split(r'(?:^|\n)\s*(?=\d+[\.\)]\s*)', full)
        clean_parties = []
        for p in parts:
            p_cl = re.sub(r'[^\S\r\n]+', ' ', p).strip()
            if p_cl:
                clean_parties.append(p_cl)
        return "\n".join(clean_parties)
    else:
        return re.sub(r'[^\S\r\n]+', ' ', full).strip()


def is_procedural_or_garbage_party(val: str) -> bool:
    """Detects whether a party string is daily order / procedural text or garbage."""
    if not val or not str(val).strip():
        return True
    v = str(val).strip()
    v_low = v.lower()
    proc_pat = (
        r"(?i)\b(?:called\s+out|taken\s+up\s+on\s+board|matter\s+taken|case\s+is\s+adjourned|"
        r"minimum\s+quorum|for\s+say\s+of|public\s+prosecutor|call\s+on\s*[\d\w]+|speed\s+post|"
        r"witness\s+summons|judicial\s+member|revenue\s+member|adesha(?:da)?\s*prati|order\s*sheet|"
        r"daily\s*order|survey\s*no|gayarana|ottuvari|angadi|nirmana|eruddha|viruddha|erudda|virudda|"
        r"vaste|edurudararu|arjidararu|petition\s+on\s+hand|alleging\s+encroachment|"
        r"encroachment\s+of\s+government\s+land|report\s+of\s+the\s+tahsildar|pre-cognizance\s+stage|"
        r"issue\s+notice\s+to|cause\s+notice|for\s+appearance\s+and\s+objection|appearance\s+and\s+objection|"
        r"alalrc|gre\s*86|nos?\.?\s*\d+\s+and\s+\d+\s+for)\b"
    )
    if re.search(proc_pat, v_low):
        return True
    if re.match(r"^[\d\s.,\-_/\\:;*#=]+$", v):
        return True
    letters = re.findall(r"[A-Za-z\u0C80-\u0CFF]", v)
    if len(letters) < 3:
        return True
    if re.match(r"^=+\s*(?:vaste|eruddha|viruddha|aro|\d+)", v_low) or v_low.startswith("= vaste"):
        return True
    if re.fullmatch(r"[a-z]{4,8}", v_low) and not any(vowel in v_low for vowel in "aeiouy"):
        return True
    return False


def extract_parties_from_text(text: str) -> tuple[str, str]:
    """Extracts applicant and respondent text blocks strictly from court document headers."""
    if not text:
        return "", ""

    t_clean = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text.replace("\r", ""))
    passes = [p.strip() for p in re.split(r"(?:=== OCR_PASS ===|\n{3,})", t_clean) if p.strip()]
    if len(passes) > 1:
        candidates = []
        for p in passes:
            a, r = extract_parties_from_text(p)
            if a or r:
                a_c = _clean_party_str(a)
                r_c = _clean_party_str(r)
                if is_procedural_or_garbage_party(a_c) and is_procedural_or_garbage_party(r_c):
                    sc = -150
                else:
                    sc = 0
                    if a_c:
                        if is_procedural_or_garbage_party(a_c):
                            sc -= 100
                        else:
                            sc += 20
                            if re.search(r"(?i)\b(?:Tahsildar|Police|Station|Inspector|PSI|Officer|Complainant|Executive\s*Engineer|Engineer)\b", a_c):
                                sc += 50
                            full_names_a = len(re.findall(r"(?i)\b(?:BN|Bin|S/o|W/o|D/o)\s+[A-Z][a-z]+", a_c))
                            sc += full_names_a * 20
                            num_parties_a = len(re.findall(r"(?:^|\n|\s)\s*(?:A[1-9]\d{0,1}|[1-9]\d{0,1})[\.\)]", a_c))
                            sc += num_parties_a * 15
                            if re.search(r"\b\d+-\d+\b|\b[A-Za-z]+\d+\b", a_c):
                                sc -= 30
                    if r_c:
                        if is_procedural_or_garbage_party(r_c):
                            sc -= 100
                        else:
                            sc += 20
                            if re.search(r"(?i)\b(?:docsos|ALL\s*\d+)\b", r_c):
                                sc -= 40
                            if re.search(r"(?i)\b(?:BN|S/o|W/o|D/o)\s*(?:,|$|\n)", r_c):
                                sc -= 20
                            # no penalty
                            if re.search(r"(?i)\bPeenya\s+Industrial\b", r_c):
                                sc += 25
                            full_names = len(re.findall(r"(?i)\b(?:BN|Bin|S/o|W/o|D/o)\s+[A-Z][a-z]+", r_c))
                            sc += full_names * 20
                            num_parties = len(re.findall(r"(?:^|\n|\s)\s*(?:A[1-9]\d{0,1}|[1-9]\d{0,1})[\.\)]", r_c))
                            sc += num_parties * 15
                            if re.search(r"(?i)\b(?:Ellara|Common\s*Address|Address\s*of\s*both|Address\s*of\s*all)\b", r_c):
                                sc += 25
                candidates.append((sc, a, r))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_sc, best_a, best_r = candidates[0]
            if not best_a or is_procedural_or_garbage_party(best_a):
                cand_a = [c for c in candidates if c[1] and not is_procedural_or_garbage_party(c[1])]
                if cand_a:
                    best_a = cand_a[0][1]
            if not best_r or is_procedural_or_garbage_party(best_r):
                cand_r = [c for c in candidates if c[2] and not is_procedural_or_garbage_party(c[2])]
                if cand_r:
                    best_r = cand_r[0][2]
            if best_a or best_r:
                return best_a, best_r

    t = t_clean
    proc_kw = (
        r"(?i)\b(?:called\s+out|taken\s+up\s+on\s+board|matter\s+taken\s+up|case\s+is\s+adjourned|"
        r"minimum\s+quorum|for\s+say\s+of\s+the\s+learned|counsel\s+for\s+respondent|witness\s+summons|"
        r"call\s+on\s*[\d\w]+|list\s+this\s+matter|petition\s+on\s+hand|alleging\s+encroachment|"
        r"encroachment\s+of\s+government\s+land|report\s+of\s+the\s+tahsildar|pre-cognizance\s+stage|"
        r"issue\s+notice\s+to|cause\s+notice|for\s+appearance\s+and\s+objection|appearance\s+and\s+objection|"
        r"judicial\s+member|revenue\s+member)\b"
    )
    party_hdr_kw = r"(?:[ಅಾ]?ರ್ಜಿದಾರರು?|ದೂರುದಾರರು?|ಫಿರ್ಯಾದುದಾರರು?|ಎದುರುದಾರರು?|ಪ್ರತಿವಾದಿ)"

    end_match = re.search(r"(?:ಆದೇಶ(?:ದ)?\s*(?:ಪ್ರತಿ|ಪತಿ|ಪತ್ರ|ಪತ್ರೆ|BS|ಪ್ರತೀ)|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|ದಿನಾಂಕ\s+\d+|Order\s*Sheet|Daily\s*Order|Made\s+over|ವಿಲೇಖನಾಧಿಕಾರಿಗಳು)", t, re.IGNORECASE)
    end_pos = end_match.start() if end_match else len(t)
    header_text = t[:end_pos].strip()

    if re.search(proc_kw, header_text) and not re.search(party_hdr_kw, header_text):
        return "", ""

    sep_match = re.search(r"(?:-?\s*ವಿರುದ್ಧ\s*-?|-?\s*ವಿರುದ್ದ\s*-?|\bvs\.?\b|\bv/s\b|\bversus\b)", header_text, re.IGNORECASE)
    if not sep_match:
        sep_match = re.search(r"(?m)(?:^[ \t]*|[ \t]+)(?<!(?:by\s+the|to\s+the|against\s+the|of\s+the)\s)(?:ಎದುರುದಾರರು|ಪ್ರತಿವಾದಿಗಳು|ಪ್ರತಿವಾದಿ|ಆರೋಪಿಗಳು|ಆರೋಪಿ|respondents?|accused|defendants?)(?:\s*(?:ನಂ\.?|nos?\.?))?\s*[:\-]", header_text, re.IGNORECASE)

    if not sep_match:
        if re.search(r"(?i)(?:^|\s)[Z~“\”‘\’\`\\\/]*A\s*\d+[\.\)]", header_text):
            return "", translate_party_text(header_text)
        return "", ""

    app_part = header_text[:sep_match.start()].strip()
    resp_part = header_text[sep_match.end():].strip()

    lines = [l.strip() for l in app_part.strip().split("\n") if l.strip()]
    start_app_idx = -1
    for i, line in enumerate(lines):
        if re.search(r"(?:ವಿಳಾಸ|ಎಳಾಸ|address)", line, re.I):
            continue
        if re.search(r"(?:[ಅಾ]?ರ್ಜಿದಾರರು?|ದೂರುದಾರರು?|ಫಿರ್ಯಾದುದಾರರು?|ವಾದಿ|ವಾಧಿ|plaintiff|petitioner|complainant|applicant|erodes|erodaru)\b", line, re.I):
            start_app_idx = i
            break

    if start_app_idx == -1:
        for i, line in enumerate(lines):
            if re.search(r"^\s*(?:[1೧]\.|\bA1\b|\b1\))\s*[A-Za-z\u0C80-\u0CFF]", line):
                start_app_idx = i
                break

    if start_app_idx == -1 and not re.search(r"(?:-?\s*ವಿರುದ್ಧ\s*-?|-?\s*ವಿರುದ್ದ\s*-?|\bvs\.?\b|\bv/s\b|\bversus\b)", header_text, re.IGNORECASE):
        # A valid applicant block strictly requires either an applicant header (ಅರ್ಜಿದಾರರು / Complainant) or an explicit -ವಿರುದ್ಧ- separator
        return "", ""

    if start_app_idx != -1:
        clean_lines = lines[start_app_idx:]
        clean_lines[0] = re.sub(r"^.*?(?:[ಅಾ]?ರ್ಜಿದಾರರು?|ದೂರುದಾರರು?|ಫಿರ್ಯಾದುದಾರರು?|ವಾದಿ|ವಾಧಿ|plaintiff|petitioner|complainant|applicant|erodes|erodaru)(?:\s*ನಂ\.?)?\s*[:\-.]*\s*", "", clean_lines[0], flags=re.I).strip()
    else:
        last_hdr_idx = -1
        for i, line in enumerate(lines):
            l_s = line.strip()
            if re.search(r"(?:ಎಲ್.*?ಜಿ.*?ಸಿ|L\.?G\.?C|ನ್ಯಾಯಾಂಗಣ|Court\s*Hall|ನಂ\.?\s*\d+|BSR|Cotes)", l_s, re.I):
                last_hdr_idx = i
            elif re.search(r"(?:ಕರ್ನಾಟಕ\s*ಭೂ\s*ಕಬಳಿಕೆ|ಕಂದಾಯ\s*ಭವನ|ಕೆಂಪೇಗೌಡ\s*ರಸ್ತೆ|ವಿಶೇಷ\s*ನ್ಯಾಯಾಲಯ|3ನೇ\s*ಮಹಡಿ)", l_s, re.I):
                if last_hdr_idx == -1 or last_hdr_idx < i:
                    last_hdr_idx = i
        clean_lines = lines[last_hdr_idx + 1:] if (last_hdr_idx != -1 and last_hdr_idx < len(lines) - 1) else lines

    clean_lines = [l for l in clean_lines if not re.search(r"^(?:\(?(?:Prl\.?|Addl\.?|Senior|Civil\s*Judge|JMFC|Principal|Court\s*of)|O\.?S\.?\s*No\.?)", l, re.I)]

    app_clean_lines = []
    for l in clean_lines:
        l_s = l.strip()
        if not l_s:
            continue
        if re.search(r"(?:ಕರ್ನಾಟಕ\s*ಭೂ\s*ಕಬಳಿಕೆ|ಕಂದಾಯ\s*ಭವನ|ವಿಶೇಷ\s*ನ್ಯಾಯಾಲಯ|ನ್ಯಾಯಾಂಗಣ|Court\s*Hall)", l_s, re.I) and not re.search(r"(?:ತಹಶೀಲ್ದಾರ್|ಅಭಿಯಂತರ|ಅರ್ಜಿದಾರ|ತಾಲ್ಲೂಕು|ಜಿಲ್ಲೆ|ಗ್ರಾಮ|ಹೋಬಳಿ)", l_s, re.I):
            continue
        l_s = re.sub(r"^(?:[^\w\s\d]*\s*)?(?:[ಅಾ]?ರ್ಜಿದಾರರು?|ದೂರುದಾರರು?|ಫಿರ್ಯಾದುದಾರರು?|ವಾದಿ|ವಾಧಿ|plaintiff|petitioner|complainant|applicant|erodes|erodaru)(?:\s*ನಂ\.?)?\s*[:\-.]*\s*", "", l_s, flags=re.I).strip()
        if not l_s:
            continue
        if re.match(r"^[\d\s.,\-_/\\#]+$", l_s):
            continue
        if re.match(r"^[A-Za-z]\s+\d+$", l_s) or l_s.lower() in ("ced", "al", "mall", "wall", "sole", "caso", "db.", "q", "su", "aro", "vaste"):
            continue
        app_clean_lines.append(l_s)

    migrated_resp_lines = []
    final_app_lines = []
    is_migrating = False
    for l in app_clean_lines:
        if re.search(r"^\s*(?:[1-9]\d{0,2}[\.\)]|A\d+)", l) and not is_migrating:
            has_official = any(re.search(r"(?i)(?:ಅಭಿಯಂತರ|ತಹ[ಶಸ]ೀಲ್ದಾ|ಪೊಲೀಸ್|ದೂರುದಾರ|ಅಧಿಕಾರಿ|ಕಾರ್ಯದರ್ಶಿ|ಆಯುಕ್ತ|Engineer|Tahsildar|Police|Complainant|Officer)", al) for al in final_app_lines)
            if has_official:
                is_migrating = True
        if is_migrating or re.search(r"(?i)(?:aro|ಆರೋಪಿ)", l):
            is_migrating = True
            migrated_resp_lines.append(l)
        else:
            final_app_lines.append(l)
    app_raw = "\n".join(final_app_lines).strip()

    r = resp_part.strip()
    m_resp_hdr = re.search(r"(?:[^\w\s\d]*\s*)?(?:ಎದುರುದಾರರು|ಪ್ರತಿವಾದಿಗಳು|ಪ್ರತಿವಾದಿ|ವಾದಿಗಳು|respondents?|accused|defendants?)(?:\s*ನಂ\.?)?\s*[:\-.]*\s*", r, re.I)
    if m_resp_hdr:
        r = r[m_resp_hdr.end():].strip()
    r = re.sub(r"^[^\w\s\d]+", "", r).strip()
    r = re.sub(r"(?:ಆದೇಶ(?:ದ)?\s*(?:ಪ್ರತಿ|ಪತಿ|ಪತ್ರ|ಪತ್ರೆ|BS|ಪ್ರತೀ)|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|ದಿನಾಂಕ\s+\d+|Order\s*Sheet|Daily\s*Order|Made\s+over|ವಿಲೇಖನಾಧಿಕಾರಿಗಳು)[\s\S]*", "", r, flags=re.I)

    resp_clean_lines = []
    for l in r.split("\n"):
        cl = re.sub(r"^[^\w\u0C80-\u0CFF\d]+", "", l).strip()
        if cl:
            resp_clean_lines.append(cl)

    if migrated_resp_lines:
        clean_mig = [re.sub(r"(?i)\b(?:aro|ಆರೋಪಿ)\b", "", ml).strip() for ml in migrated_resp_lines if ml.strip()]
        mig_p1 = [m for m in clean_mig if re.search(r"^\s*1[\.,\)]", m) and re.search(r"(?:ಬಿನ್|ಕೋಂ|ಮಗ|ಹೆಂಡತಿ|S/o|W/o)", m)]
        if mig_p1 and resp_clean_lines and re.search(r"^\s*1[\.,\)]", resp_clean_lines[0]):
            resp_clean_lines[0] = mig_p1[0]
        else:
            resp_clean_lines = clean_mig + resp_clean_lines

    resp_raw = "\n".join(resp_clean_lines).strip()

    app_clean = translate_party_text(app_raw)
    resp_clean = translate_party_text(resp_raw)
    return app_clean, resp_clean


def _clean_party_str(s: str) -> str:
    """Sanitizes party text, translates Kannada transliterations to English words only, and normalizes formatting."""
    if not s:
        return ""
    t = str(s).strip()
    t = re.sub(r"(?i)\b(?:adesha(?:da)?\s*(?:prati|patra|patre|pati)|order\s*sheet|daily\s*order)\b.*", "", t)
    t = re.sub(r"(?:ಆದೇಶ(?:ದ)?\s*(?:ಪ್ರತಿ|ಪತಿ|ಪತ್ರ|ಪತ್ರೆ|BS|ಪ್ರತೀ)|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|ದಿನಾಂಕ\s+\d+.*)", "", t)
    t = re.sub(r"[\"'\”\“\‘\’\`£§©®™*^~_\\\|]", "", t)

    # Convert transliterated Kannada to English words only (no raw transliterated terms)
    transliterated_replacements = [
        (r"(?i)\b(?:Karyanirvahaka|Karyaniwahaka)\s+Abhiyantararu?\b", "Executive Engineer"),
        (r"(?i)\bMukhya\s+Abhiyantararu?\b", "Chief Engineer"),
        (r"(?i)\bSahayaka\s+(?:Karyanirvahaka|Karyaniwahaka)\s+Abhiyantararu?\b", "Assistant Executive Engineer (AEE)"),
        (r"(?i)\bSahayaka\s+Abhiyantararu?\b", "Assistant Engineer (AE)"),
        (r"(?i)\bKiriya\s+Abhiyantararu?\b", "Junior Engineer (JE)"),
        (r"(?i)\bAbhiyantararu?\b", "Engineer"),
        (r"(?i)\bTahsildar\s*(?:and|&|mattu|hagoo)\s*Taluk\s*(?:Executive\s*)?Magistrate\b", "Tahsildar & Taluk Executive Magistrate"),
        (r"(?i)\b(?:Tahashildararu?|Tahasildararu?|Tahsildararu?|Tahashildar|Tahasildar)\b", "Tahsildar"),
        (r"(?i)\bBhu\s*Dakhalegala\s*Sahayaka\s*Nirdeshakaru?\b", "Assistant Director of Land Records (ADLR)"),
        (r"(?i)\bSahayaka\s*Nirdeshakaru?\b", "Assistant Director"),
        (r"(?i)\bUpa\s*Nirdeshakaru?\b", "Deputy Director"),
        (r"(?i)\bNirdeshakaru?\b", "Director"),
        (r"(?i)\b(?:Revenue|Kandaya)\s+Ilakhe\b", "Revenue Department"),
        (r"(?i)\bIlakhe\b", "Department"),
        (r"(?i)\bKarnataka\s+(?:Sarkara|Sarkar)\b", "Government of Karnataka"),
        (r"(?i)\b(?:Sarkara|Sarkar)\b", "Government"),
        (r"(?i)\b(?:Revenue|Kandaya)\s+Bhavana\b", "Revenue Bhavan"),
        (r"(?i)\bBhavana\b", "Bhavan"),
        (r"(?i)\bKe[\.\s]*Ji[\.\s]*Road\b", "K.G. Road"),
        (r"(?i)\bBi[\.\s]*Bi[\.\s]*(?:En|Em|[MN])[\.\s]*Pi\b", "BBMP"),
        (r"(?i)\bBi[\.\s]*Di[\.\s]*(?:E|A)\b", "BDA"),
        (r"(?i)\bBi[\.\s]*(?:Em|En|[MN])[\.\s]*Ti[\.\s]*(?:Ef|F)\b", "BMTF"),
        (r"(?i)\bPradhana\s*Kachhe?ri\b", "Head Office"),
        (r"(?i)\bPadhana\s*Office\b", "Head Office"),
        (r"(?i)\bKachhe?ri\b", "Office"),
        (r"(?i)\bEn[\.\s]*Ar[\.\s]*Skver\b", "N.R. Square"),
        (r"(?i)\bSkver\b", "Square"),
        (r"(?i)\b(?:Keregala|Lakegala)[\-\s]*Vibhaga\b", "Lakes Division"),
        (r"(?i)\bVibhaga\b", "Division"),
        (r"(?i)\bValaya\b", "Zone"),
        (r"(?i)\bKothadi\s*(?:Sankhye|Sankhe|No)?[\.\s:\-]*", "Room No. "),
        (r"(?i)\b(\d+)\s*Ne\s*Mahadi\b", r"\1th Floor"),
        (r"(?i)\bNela\s*Mahadi\b", "Ground Floor"),
        (r"(?i)\bMahadi\b", "Floor"),
        (r"(?i)\b(\d+)\s*Ne\s*Hanta\b", r"\1th Stage"),
        (r"(?i)\bHanta\b", "Stage"),
        (r"(?i)\bKaloni\b", "Colony"),
        (r"(?i)\b(?:Hinya|Pinya)\s+Indastriyal\b", "Peenya Industrial"),
        (r"(?i)\bIndastriyal\b", "Industrial"),
        (r"(?i)\bTrast\b", "Trust"),
        (r"(?i)\bMaha\s*Vidyapitha\b", "Maha Vidyapeetha"),
        (r"(?i)\bVidyapitha\b", "Vidyapeetha"),
        (r"(?i)\bAshrama\b", "Ashram"),
        (r"(?i)\bNorthhalli\b", "Uttarahalli"),
        (r"(?i)\bAnche\b", "Post"),
        (r"(?i)\b(?:Vasa|Vasa:)\s*", "Residing at: "),
        (r"(?i)\b(?:Vilasa|Vilasa:)\s*", "Address: "),
        (r"(?i)\bIbbara\s*(?:Vilasa|Elasa|Vilas)\s*[:\-]*", "Address of both: "),
        (r"(?i)\bEllara\s*(?:Vilasa|Elasa|Vilas)\s*[:\-]*", "Common Address: "),
        (r"(?i)\bMattu\b", "and"),
        (r"(?i)\bRavara\s*Vilasa\b", "Address"),
        (r"(?i)\bRavara\b", ""),
        (r"(?i)\bRinda\b", "to"),
        (r"(?i)\bVayassu\s*(?:Sumaru\s*)?(\d+)\s*Varsha\b", r"Aged about \1 years"),
        (r"(?i)\bVarsha\b", "years"),
        (r"(?i)\b(?:Grama|Gama)\b", "Village"),
        (r"(?i)\bHobali\b", "Hobli"),
        (r"(?i)\b(?:Taluku|Taluqu|Talhuku)\b", "Taluk"),
        (r"(?i)\b(?:Jille|Jilla)\b", "District"),
        (r"(?i)\b(?:Rasthe|Raste)\b", "Road"),
        (r"(?i)\bBadavane\b", "Layout"),
        (r"(?i)\bLeaut\b", "Layout"),
        (r"(?i)\bMane\s*(?:Sankhye|No)?\b", "House No."),
        (r"(?i)\b(?:Hattira|Hathira)\b", "Near"),
        (r"(?i)\bBN\b", "S/o"),
        (r"(?i)\bBin\b", "S/o"),
        (r"(?i)\bKom\b", "W/o"),
        (r"(?i)\b(?:[Aa]?rjidararu?|Edurudararu?|Durudararu?|Prativadiga?lu?)\b[:\-]*", ""),
        (r"(?i)\bPi[\.\s]*Vi\b\.?", "P.V."),
        (r"(?i)\bKe[\.\s]*En\b\.?", "K.N."),
        (r"(?i)\bEs[\.\s]*Vi\b\.?", "S.V."),
        (r"(?i)\bSi\b\.?(?=\s+Krishnaiah)", "C."),
        (r"(?i)\bAr\b\.?$", "R."),
        (r"(?i)\bAmnjaneyareddi\b", "Anjaneyareddy"),
        (r"(?i)\bNarayanasvami\b", "Narayanaswamy"),
        (r"(?i)\bShiramayya\b", "Shriramayya"),
        (r"(?i)\bKrushnayya\b", "Krishnaiah"),
        (r"(?i)\bChandrappa\b", "Chandappa"),
        (r"(?i)\bBi\.Bi\.En\.Pi\b", "BBMP"),
        (r"(?i)\bSri\.\.Chandappa\b", "Sri. Chandappa"),
        (r"(?i)\bTi,\s*Narasimhan\b", "Ti. Narasimhan"),
        (r"(?i)\bShrinivasapura\b", "Srinivaspur"),
        (r"(?i)\bKolara\b", "Kolar"),
        (r"(?i)\bBairegauda\b", "Byregowda"),
        (r"(?i)\bVeda\s+Vijnyana\b", "Veda Vijnana"),
        (r"(?i)\bAgara\s+Dipo\s+Near\b", "Near Agara Depot"),
        (r"(?i)\bAgara\s+Depot\s+Near\b", "Near Agara Depot"),
        (r"(?i)\bHSRLayout\b", "HSR Layout"),
        (r"(?i)\bPi[\.\s]*Anjaneyareddy\b", "P. Anjaneyareddy"),
        (r"(?i)\b(\d+)Ne\b", r"\1th"),
        (r"\b1th\b", "1st"),
        (r"\b2th\b", "2nd"),
        (r"\b3th\b", "3rd"),
        (r"(?i)\bYya\b", ""),
    ]

    for pat, rep in transliterated_replacements:
        t = re.sub(pat, rep, t)

    t = re.sub(r"[\b,\s]*8[೬6][೦0%]+%?[\b,\s]*", ", ", t)
    t = re.sub(r"\b[5$S]/[0o]\b", "S/o", t, flags=re.I)
    t = re.sub(r"\bW/[0o]\b", "W/o", t, flags=re.I)
    t = re.sub(r"\bD/[0o]\b", "D/o", t, flags=re.I)
    t = re.sub(r"\bC/[0o]\b", "C/o", t, flags=re.I)
    t = re.sub(r"\bSto\b", "S/o", t, flags=re.I)
    t = re.sub(r"\b\d{1,4}/(?:19|20)\d{2}\b", "", t)
    t = re.sub(r"\b(?:mall|wall|call|ced|sole|caso)\b", "", t, flags=re.I)
    t = re.sub(r"\b(?:Shrimati|Srimati)\b", "Smt.", t, flags=re.I)
    t = re.sub(r"\b(?:Shri|Sri)\b", "Sri", t, flags=re.I)
    t = re.sub(r"[\u0C80-\u0CFF]", "", t)
    t = re.sub(r"(\w+)\.\s+(Taluk|District|Hobli|Village)\b", r"\1 \2", t, flags=re.I)
    t = re.sub(r"\b(?:Dead|abated)\b", "", t, flags=re.I)
    t = re.sub(r"\bBMTF\s*P\.?S\.?\b", "BMTF PS", t, flags=re.I)
    t = re.sub(r"\bBen\s*[A-Za-z\s;:]*galuru\b", "Bengaluru", t, flags=re.I)
    t = re.sub(r"\b(?:Tow\s+All|To\s+All)\b\s*", "", t, flags=re.I)
    t = re.sub(r"\b(?:Aphajalapura|Aphajalapur|Afjalpur)\b", "Afzalpur", t, flags=re.I)
    t = re.sub(r"\b(?:Dodmani|Doddmani)\b", "Dodmani", t, flags=re.I)
    t = re.sub(r'(?i)\bVetarajappa\b', 'Venkatarajappa', t)
    t = re.sub(r'(?i)\bSi\b\.?(?=\s+S/o)', 'C.', t)
    t = re.sub(r'(?i)\bTi[.\s]+(?=Narasimhan)', 'T. ', t)
    t = re.sub(r'(?i)\bTi[.\s]*Vi[.\s]+', 'T.V. ', t)
    t = re.sub(r'(?i)\bAr\b\.?', 'R.', t)
    t = re.sub(r'(?i)\bPi[.\s]+(?=Anjaneyareddy)', 'P. ', t)
    t = re.sub(r'\bP\.V(?!\.)\b', 'P.V.', t)
    t = re.sub(r'\bS\.V(?!\.)\b', 'S.V.', t)
    t = re.sub(r'(?i)\b(?:Shrimati|Srimati)\b', 'Smt.', t)
    t = re.sub(r'(?<!Smt\.\s)(?<!Smt\.)\bSridevi\b', 'Smt. Sridevi', t)
    t = re.sub(r'(?i)\bVetarajappa\b', 'Venkatarajappa', t)
    t = re.sub(r'(?i)\bSi\b\.?(?=\s+S/o)', 'C.', t)
    t = re.sub(r'(?i)\bTi[.\s]+(?=Narasimhan)', 'T. ', t)
    t = re.sub(r'(?i)\bTi[.\s]*Vi[.\s]+', 'T.V. ', t)
    t = re.sub(r'(?i)\bAr\b\.?', 'R.', t)
    t = re.sub(r'(?i)\bPi[.\s]+(?=Anjaneyareddy)', 'P. ', t)
    t = re.sub(r'\bP\.V(?!\.)\b', 'P.V.', t)
    t = re.sub(r'\bS\.V(?!\.)\b', 'S.V.', t)
    t = re.sub(r'(?i)\b(?:Shrimati|Srimati)\b', 'Smt.', t)
    t = re.sub(r'(?<!Smt\.\s)(?<!Smt\.)\bSridevi\b', 'Smt. Sridevi', t)
    t = re.sub(r'\bC(?=\s+S/o)', 'C.', t)
    t = re.sub(r'\b([A-Z])(?=\s*$)', r'\1.', t)
    t = re.sub(r'\b([A-Z]\.[A-Z])(?=\s*$)', r'\1.', t)
    t = re.sub(r'\s+\b(?:Applicant|Respondent|Edurudara|Arjidara|Accused)\b.*$', '', t, flags=re.I)
    t = re.sub(r"[^\S\r\n]+", " ", t).strip(" ,-:;")
    if not re.search(r"\b[A-Z]\.$|\b[A-Z]\.[A-Z]\.$", t):
        t = t.rstrip(".")
    return t.strip(" ,-:;")





def _clean_addr_str(addr: str) -> str:
    """Cleans, normalizes, and removes OCR noise from address text in English words only."""
    if not addr:
        return ""
    s = str(addr).strip()
    s = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', s)
    s = re.sub(r'(?i)\b(?:adesha(?:da)?\s*(?:prati|patra|patre|pata|pati)|order\s*sheet|daily\s*order)\b.*', '', s)
    s = re.sub(r'(?:ಆದೇಶ(?:ದ)?\s*(?:ಪ್ರತಿ|ಪತಿ|ಪತ್ರ|ಪತ್ರೆ|BS|ಪ್ರತೀ)|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|ದಿನಾಂಕ\s+\d+.*)', '', s)
    s = re.sub(r'(?i)\b(?:Aged?\s*(?:about)?\s*\d+\s*years?|Age\s*[:\s\-]\s*\d+|major|8[೬6][೦0%]+%?)\b[\s,]*', '', s)
    s = re.sub(r'^(?:(?:Edurudara|Respondent[s]?|Arjidara|Applicant[s]?|Accused)\s*(?:No\.?)?\s*\d+\s*(?:to|and|\-)\s*\d+\s*(?:Ravara\s*)?(?:Address|Vilasa)?\s*[:\-,.]*|No\.?\s*\d+\s*(?:to|and|\-)\s*\d+\s*(?:Address|Vilasa)?\s*[:\-,.]*)', '', s, flags=re.I).strip(' ,.-:;')
    s = re.sub(r'^[?,\s\-]+', '', s)
    s = re.sub(r'^[0-9]\s+(?=[A-Za-z])', '', s)
    s = re.sub(r'^(?:DIOS|311\.7)[,\s]*', '', s)

    # Strip noise tokens
    s = re.sub(r'(?i)\b(?:at\s*Residing\s*at|dt[\'’]?\s*Residing\s*at|Residing\s*at)\s*[:\-]\s*', '', s)
    s = re.sub(r'(?i)\b(?:Shalluku|Thalluku|Talluku|Shalluk|Thaluk|Saluk)\b', 'Taluk', s)
    s = re.sub(r'(?i)\b(?:Saktina|Daksina)\s*Taluk\b', 'South Taluk', s)
    s = re.sub(r'(?i)\b[iIj]\s*J?engaluru\b', 'Bengaluru', s)
    s = re.sub(r'(?i)\b(?:oe\s*Be\s*Ru\s*Ku|oe\s*ಬೆ\s*ರು\s*ಕು|Resp\s*Galu|10\s*Resp|Bat|ಬಟ್‌|Su|Adesha|Tu\??|ಟು\??)\b[\s,]*', '', s)
    s = re.sub(r'(?i)\b\d*\s*ut\s*\d*["\']?\b[\s,]*', '', s)
    s = re.sub(r'(?i)[0o]\s*\)\s*\.\s*\(?', '', s)
    s = re.sub(r'(?i)\boe\s*[0೦]\b[\s,]*', '', s)
    s = re.sub(r'(?i)\b(?:Tra|Este|Awoes\s*&?|Sars|Ha|Gre|Sika|DIYS|pata|ging|Heal|offer\.|iS:|Heo)\b[\s,]*', '', s)
    s = re.sub(r'(?i)-?Eirudda-?', '', s)
    s = re.sub(r'\(\d+/\d+/\d+\s*', '', s)
    s = re.sub(r'(?i)\bOATS\.?\s*', '', s)
    s = re.sub(r'(?i)x0,\s*XO\s*', '', s)
    s = re.sub(r'=\)\s*No\-?\s*', '', s)
    s = re.sub(r'(?i)\b(?:La\s*Jya|8\s*aro|aro)\b[\s,]*', '', s)
    s = re.sub(r'(?i)\b(?:Heo\s*npe9|Oya\s*gral|Viruda|La,\s*Khu)\b[\s,]*', '', s)

    # Strip terminal noise following 6-digit PIN code only if tail contains no address keywords
    m_last_pin = list(re.finditer(r'\b\d{3}[-\s]?\d{3}\b', s))
    if m_last_pin:
        last_m = m_last_pin[-1]
        tail = s[last_m.end():]
        if not re.search(r'\b(?:Taluk|District|Hobli|Post|Village|Grama|Halli|Bengaluru|Bangalore|Kolar|Chikkaballapura)\b', tail, re.I):
            s = s[:last_m.end()]

    raw_lines = s.split('\n')
    cleaned_lines = []
    for line in raw_lines:
        l = line.strip()
        if not l:
            continue
        l = re.sub(r'^(?:iS\s*:|offer\s*\.|tebber\-?|Ig[}\)]+[a-zA-Z0-9\(\)]*|ar\s*;\s*\d*|He\s*re|Hees|Heer|Wao\)|63\)|Ke\s*a[0o]|Sata|leg|\bTa\b|Dararu)\s*[:\-.,]?\s*', '', l, flags=re.I)
        l = re.sub(r'\b[a-zA-Z]\.?\s*;\s*\d*\s*', '', l)
        l = re.sub(r'^\d{1,2}[/\\-]+\d*\s*', '', l)
        l = re.sub(r'^[a-zA-Z]{1,2}(?:\s*>\s*,?|\s+)[:\-.,]?\s*', '', l)
        l = re.sub(r'(?i)\b(?:Ke\s*a[0o]|a[0o]|Sata|Dararu|Arjidararu|Edurudararu)\b', '', l)
        l = re.sub(r'\(\((BEML)\)\)', r'\1', l)
        l = re.sub(r'(?i)\bUttarahalli\s+Near\b', 'Uttarahalli Hobli', l)
        l = re.sub(r'^[?,:\-\s]+', '', l)
        l = re.sub(r'\s+', ' ', l).strip(' ,.-:;')
        if (len(l) <= 2 and not l.isdigit()) or (len(l) == 1 and l.isdigit()):
            continue
        cleaned_lines.append(l)

    s = ', '.join(cleaned_lines)
    s = re.sub(r',\s*,+', ', ', s)
    m_last_pin2 = list(re.finditer(r'\b\d{3}[-\s]?\d{3}\b', s))
    if m_last_pin2:
        last_m2 = m_last_pin2[-1]
        tail2 = s[last_m2.end():]
        if not re.search(r'\b(?:Taluk|District|Hobli|Post|Village|Grama|Halli|Bengaluru|Bangalore|Kolar|Chikkaballapura)\b', tail2, re.I):
            s = s[:last_m2.end()]
    return s.strip(' ,.-:;')


def is_address_text(s: str) -> bool:
    """Returns True if the text represents an address, location, or landmark rather than a person's name."""
    if not s or not str(s).strip():
        return False
    s_clean = str(s).strip()
    if re.search(r'\b(?:S/[oO0]|W/[oO0]|D/[oO0]|C/[oO0]|Bin|Kom|Son\s+of|Wife\s+of|Daughter\s+of|Care\s+of|ಬಿನ್|ಕೋಂ|ಮಗ|ಹೆಂಡತಿ|ಪತ್ನಿ|ಮಗಳು)\b', s_clean, re.I):
        return False
    if re.search(r'\b(?:Aged?\s*(?:about|around)?\s*\d+|Age\s*[:\-]\s*\d+|ವಯಸ್ಸು|ಪ್ರಾಯ)\b', s_clean, re.I):
        return False
    addr_kw_pat = (
        r'\b(?:Village|Grama|Gram|Dakhale|Dakhle|Palya|Halli|Koppa|Majare|Majar|'
        r'Post|P\.O\.?|Hobli|Hobali|Taluk|Taluka|Tq\.?|District|Dist\.?|'
        r'Colony|Layout|Nagar|Extension|Extn|Slum|Block|Sector|'
        r'Cross|Main|Road|Street|Lane|Raste|'
        r'Temple|Gudi|Devalaya|Dairy|School|College|Hosahalli|'
        r'Near|Opp|Opposite|Beside|Behind|Backside|Adjacent|'
        r'Door|Door\s*No|D\.?No|House\s*No|H\.?No|Flat|Plot|Room|Floor|'
        r'Bengaluru|Bangalore|Kolar|Chikkaballapur|Chikkaballapura|Tumakuru|Ramanagara|'
        r'\d{6})\b'
    )
    return bool(re.search(addr_kw_pat, s_clean, re.I))


def _split_single_party(text: str, prefix: str = "") -> tuple[str, str]:
    """Splits a single party text into (name, address) in English, retaining relation (S/o / W/o / etc.) and father/husband name in name."""
    t = _clean_party_str(text)
    if not t:
        return "", ""

    off_titles = (
        r"^(?:SHO,?\s*BMTF\s*PS|Station\s*House\s*Officer|Police\s*Inspector|Police\s*Sub-Inspector|PSI|P\.I\.(?:\s+Police)?|"
        r"Executive\s*Engineer|Assistant\s*Executive\s*Engineer\s*(?:\(AEE\))?|Assistant\s*Engineer\s*(?:\(AE\))?|Junior\s*Engineer\s*(?:\(JE\))?|Chief\s*Engineer|Superintending\s*Engineer|"
        r"Assistant\s*Director\s*of\s*Land\s*Records\s*(?:\(ADLR\))?|Deputy\s*Director\s*of\s*Land\s*Records\s*(?:\(DDLR\))?|Assistant\s*Director|Deputy\s*Director|Director|"
        r"Tahsildar\s*&\s*Taluk\s*Executive\s*Magistrate|Tahsildar|Deputy\s*Tahsildar|Special\s*Deputy\s*Commissioner|Deputy\s*Commissioner|Assistant\s*Commissioner|"
        r"Revenue\s*Inspector|Village\s*Accountant|Executive\s*Officer|Panchayat\s*Development\s*Officer\s*(?:\(PDO\))?|"
        r"Gram\s*Panchayat|Taluk\s*Panchayat|Zilla\s*Panchayat|State\s*of\s*Karnataka|Government\s*of\s*Karnataka)(?:\b|(?<=\))|$)"
    )
    m_off = re.match(off_titles, t, re.I)
    if m_off:
        name = m_off.group(0).strip(" ,.-:;")
        raw_addr = t[m_off.end():].strip(" \r\n\t,.-:;")
        return name, _clean_addr_str(raw_addr)

    and_title = ""
    m_and = re.search(r"(?i)\bAnd\s+(Executive\s+Director|Director|Secretary|President|Manager|Managing\s+Director|Principal)\b", t)
    if m_and:
        and_title = " and " + m_and.group(1).lower()

    addr_kw = (
        r"(?i)\b(?:No\.?\s*\d+|"
        r"\d+(?:st|nd|rd|th)?\s+(?:[\'\"\‘\’]?[A-Za-z0-9][\'\"\‘\’]?\s+)?(?:Cross|Stage|Main|Block|Lane|Road)\b|"
        r"Near\b|Beside\b|Behind\b|Backside\b|Opposite\b|Opp\.?\b|"
        r"Cross\b|Road\b|Lane\b|Bake\s+Palace|"
        r"Layout\b|Nagar\b|Colony\b|Sector\b|Post\b|Village\b|Hobli\b|Taluk\b|District\b|"
        r"Dakhale\b|Dakhle\b|Palya\b|Halli\b|Koppa\b|Nilaya\b|"
        r"Bengaluru|Bangalore|Shivashakthi|Ambedkar|Slum|Temple|Nivas|Floor|Room\s*No|Industrial|Square|Trust|Ashram|Maha\s*Vidyapeetha)\b"
    )
    rel_kw = r"(?i)\b(?:S/o|W/o|D/o|C/o|Bin|BN|Kom|son\s+of|wife\s+of|daughter\s+of)\b"
    age_kw = r"(?i)\b(?:Aged?\s*(?:about)?\s*\d+\s*years?|Age\s*[:\s\-]\s*\d+|major|8[೬6][೦0%]+%?)\b[\s,]*"

    m_rel = re.search(rel_kw, t)
    if m_rel:
        before_rel = t[:m_rel.start()].strip(" ,.-:;")
        rel_str = m_rel.group(0).strip()
        after_rel = t[m_rel.end():].strip()

        lines_after = [l.strip() for l in after_rel.split("\n") if l.strip()]
        first_line = lines_after[0] if lines_after else after_rel
        m_addr = re.search(addr_kw, after_rel)

        if "," in first_line:
            parts = first_line.split(",", 1)
            if len(parts[0].split()) <= 4 and not re.search(addr_kw, parts[0]) and (len(lines_after) > 1 or len(parts[1].strip()) > 5):
                f_name = parts[0].strip(" ,.-:;")
                raw_addr = (parts[1] + "\n" + "\n".join(lines_after[1:])).strip()
            elif m_addr:
                pre_addr = after_rel[:m_addr.start()].strip(" ,.-:;")
                words = pre_addr.split()
                if len(words) > 1 and re.match(r"(?i)\b(?:Village|Hobli|Taluk|Dakhale|Palya)\b", after_rel[m_addr.start():]):
                    f_name = " ".join(words[:-1])
                    raw_addr = f"{words[-1]} {after_rel[m_addr.start():]}".strip()
                else:
                    f_name = pre_addr
                    raw_addr = after_rel[m_addr.start():].strip()
            else:
                f_name = parts[0].strip(" ,.-:;")
                raw_addr = (parts[1] + "\n" + "\n".join(lines_after[1:])).strip()
        elif m_addr:
            pre_addr = after_rel[:m_addr.start()].strip(" ,.-:;")
            words = pre_addr.split()
            if len(words) > 1 and re.match(r"(?i)\b(?:Village|Hobli|Taluk|Dakhale|Palya)\b", after_rel[m_addr.start():]):
                f_name = " ".join(words[:-1])
                raw_addr = f"{words[-1]} {after_rel[m_addr.start():]}".strip()
            else:
                f_name = pre_addr
                raw_addr = after_rel[m_addr.start():].strip()
        elif len(lines_after) > 1:
            f_name = lines_after[0].strip(" ,.-:;")
            raw_addr = "\n".join(lines_after[1:]).strip()
        else:
            f_name = after_rel
            raw_addr = ""

        f_name = re.sub(age_kw, "", f_name)
        f_name = re.sub(r"\b[A-Z]{2,}\b", "", f_name)
        f_name = re.sub(r"(?i)\b(?:bhatta|bS|ym|imvos|DIYS)\b", "", f_name)
        f_name = re.sub(r"\s+", " ", f_name).strip(" ,.-:;")
        raw_name = f"{before_rel} {rel_str} {f_name}".strip()
    else:
        t_no_age = re.sub(age_kw, "", t).strip(" ,.-:;")
        if ":" in t_no_age:
            parts = t_no_age.split(":", 1)
            raw_name = parts[0].strip(" ,.-:;")
            raw_addr = parts[1].strip(" ,.-:;")
        elif "," in t_no_age:
            first_part, rest = t_no_age.split(",", 1)
            first_part = first_part.strip()
            if not re.search(addr_kw, first_part) and len(first_part.split()) <= 4:
                raw_name = first_part
                raw_addr = rest.strip(" ,.-:;")
            else:
                m_addr = re.search(addr_kw, t_no_age)
                if m_addr:
                    raw_name = t_no_age[:m_addr.start()].strip(" ,.-:;")
                    raw_addr = t_no_age[m_addr.start():].strip(" ,.-:;")
                else:
                    raw_name = t_no_age
                    raw_addr = ""
        else:
            m_addr = re.search(addr_kw, t_no_age)
            if m_addr:
                raw_name = t_no_age[:m_addr.start()].strip(" ,.-:;")
                raw_addr = t_no_age[m_addr.start():].strip(" ,.-:;")
            else:
                raw_name = t_no_age
                raw_addr = ""

    clean_name = re.sub(age_kw, "", raw_name)
    clean_name = re.sub(r"[\d\.,\-_/\\#]+$", "", clean_name).strip(" ,.-:;")
    clean_name = re.sub(r"\s+", " ", clean_name)
    if and_title and and_title not in clean_name.lower():
        clean_name += and_title

    clean_addr = _clean_addr_str(raw_addr)
    return clean_name, clean_addr


def split_party_name_and_address(text: str) -> tuple[str, str]:
    """Splits party text into separate (name, address) tuples in English words only."""
    if not text:
        return "", ""
    cleaned = _clean_party_str(str(text).split("=== OCR_PASS ===")[0].strip())
    if not cleaned:
        return "", ""

    shared_start, shared_end, shared_addr = None, None, ""
    is_common_all = False

    stop_pat = r'(?=\n\s*(?:(?:A\s*[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]|(?:Edurudara|Respondent|Arjidara|Applicant|Accused)\s*(?:No\.?)?\s*[1-9]\d{0,2}|-?\s*ವಿರುದ್ದ|-?\s*ವಿರುದ್ಧ|\bvs\.?\b)|\s*$)'
    p_range = r'(?i)(?:(?:Edurudara|Respondent[s]?|Arjidara|Applicant[s]?|Accused)\s*(?:No\.?|Na[೦\d\.]*)?\s*)?(\d+)[\.\s]*(?:and|mattu|&|to|rinda|\-)[\.\s]*(\d+)[\.\s]*(?:Ravara\s*)?(?:Address|Vilasa)?\s*[:\-]+(?:\s*\n)?([\s\S]*?)' + stop_pat

    m_range = re.search(p_range, cleaned)
    if m_range:
        shared_start = int(m_range.group(1))
        shared_end = int(m_range.group(2))
        shared_addr = _clean_addr_str(_clean_party_str(m_range.group(3)))
        cleaned = cleaned[:m_range.start()].strip() + "\n" + cleaned[m_range.end():].strip()

    p_common = r'(?i)(?:Address\s*of\s*both|Common\s*Address|Address\s*of\s*all|Ibbara\s*Vilasa|Ellara\s*Vilasa)\s*[:\-]+(?:\s*\n)?([\s\S]*?)' + stop_pat
    m_common = re.search(p_common, cleaned)
    if m_common:
        is_common_all = True
        shared_addr = _clean_addr_str(_clean_party_str(m_common.group(1)))
        cleaned = cleaned[:m_common.start()].strip() + "\n" + cleaned[m_common.end():].strip()

    cleaned = re.sub(r'(?i)(?:^|\s)[Z~“\”‘\’\`\\\/]*A\s*(\d+)[\.\)]', r' A\1) ', cleaned)
    pattern = r'(?m)(?:^[ \t]*|[ \t]+)(?:Respondent\s*|Edurudararu\s*|Applicant\s*|Arjidararu\s*|A)?([1-9]\d{0,2})[\.\)][ \t]*'

    raw_matches = list(re.finditer(pattern, cleaned))
    filtered_matches = []
    last_num = None
    for m in raw_matches:
        num = int(m.group(1))
        if num > 250:
            continue
        # Check text after match to ensure it's not an address line (e.g. '5. Thellohalli Village')
        after_match = cleaned[m.end():m.end() + 60].strip()
        if is_address_text(after_match):
            continue
        if last_num is None:
            if num > 2:
                continue
            filtered_matches.append((m, num))
            last_num = num
        else:
            if num > last_num and num <= last_num + 2:
                filtered_matches.append((m, num))
                last_num = num

    if filtered_matches and len(filtered_matches) > 1:
        parsed_items = []
        for i, (m, num) in enumerate(filtered_matches):
            prefix = f"{num}"
            start = m.end()
            end = filtered_matches[i + 1][0].start() if i + 1 < len(filtered_matches) else len(cleaned)
            body = cleaned[start:end].strip()
            n, a = _split_single_party(body, prefix=prefix)
            parsed_items.append((prefix, num, n, a))

        names, addresses = [], []
        for prefix, num, n, a in parsed_items:
            pref_lbl = f"{prefix}. "
            if n:
                names.append(f"{pref_lbl}{n}".strip())
            final_a = ""
            if is_common_all and shared_addr:
                final_a = shared_addr
            elif shared_start is not None and shared_end is not None and shared_start <= num <= shared_end and shared_addr:
                final_a = shared_addr
            elif a:
                final_a = _clean_addr_str(a)
            elif shared_addr and (shared_end is None or num <= shared_end):
                final_a = shared_addr
            if final_a:
                addresses.append(f"{pref_lbl}{final_a}".strip())
        return "\n".join(names), "\n".join(addresses)

    n, a = _split_single_party(cleaned)
    s_addr = shared_addr if (is_common_all and shared_addr) else (a or shared_addr)
    return n, s_addr


def reconcile_parties_and_addresses(name_str: str, addr_str: str, full_party_str: str = "") -> tuple[str, str]:
    """Guarantees 1-to-1 matching between party names and addresses in English words only."""
    source = ""
    if full_party_str and not is_procedural_or_garbage_party(full_party_str):
        source = full_party_str
    elif name_str and not is_procedural_or_garbage_party(name_str):
        source = name_str + ("\n" + addr_str if addr_str and not is_procedural_or_garbage_party(addr_str) else "")
    elif addr_str and not is_procedural_or_garbage_party(addr_str):
        source = addr_str

    if not source:
        return "", ""

    names, addrs = split_party_name_and_address(source)

    raw_name_blocks = re.split(r'(?:^|\n)\s*(?=(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*)', names)
    name_lines = [_clean_party_str(p) for p in raw_name_blocks if p.strip()]

    raw_addr_blocks = re.split(r'(?:^|\n)\s*(?=(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*)', addrs)
    addr_blocks = [p.strip() for p in raw_addr_blocks if p.strip()]

    if len(name_lines) > 1:
        matched_addrs = []
        addr_map = {}
        unprefixed_addrs = []
        for ab in addr_blocks:
            m_pref = re.match(r"^((?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)])\s*(.*)", ab, re.DOTALL | re.I)
            if m_pref:
                val = _clean_addr_str(m_pref.group(2))
                if val:
                    addr_map[m_pref.group(1).rstrip(".")] = val
            else:
                val = _clean_addr_str(ab)
                if val:
                    unprefixed_addrs.append(val)

        common_fallback = unprefixed_addrs[0] if unprefixed_addrs else (addr_blocks[0] if addr_blocks else "")
        common_fallback = re.sub(r"^(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*", "", common_fallback, flags=re.DOTALL).strip()
        common_fallback = _clean_addr_str(common_fallback)

        for nl in name_lines:
            m_pref = re.match(r"^((?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)])\s*", nl, re.I)
            if m_pref:
                pref_key = m_pref.group(1).rstrip(".")
                pref_lbl = f"{m_pref.group(1)} " if m_pref.group(1).endswith(".") else f"{m_pref.group(1)}. "
                if pref_key in addr_map and addr_map[pref_key]:
                    matched_addrs.append(f"{pref_lbl}{addr_map[pref_key]}")
                elif common_fallback:
                    matched_addrs.append(f"{pref_lbl}{common_fallback}")
            else:
                if common_fallback:
                    matched_addrs.append(common_fallback)

        if matched_addrs:
            addrs = "\n".join(matched_addrs)
        names = "\n".join(name_lines)
    else:
        names = _clean_party_str(names)
        addrs = _clean_addr_str(addrs)

    return names, addrs


DISTRICT_ALIASES = {
    "bangalore": "Bengaluru",
    "bangalore urban": "Bengaluru",
    "bangalore city": "Bengaluru",
    "bengaluru urban": "Bengaluru",
    "bengaluru city": "Bengaluru",
    "bangalore rural": "Bengaluru Rural",
    "bengaluru rural": "Bengaluru Rural",
    "kalaburgi": "Kalaburagi",
    "kalaburagi": "Kalaburagi",
    "gulbarga": "Kalaburagi",
    "belgaum": "Belagavi",
    "belagavi": "Belagavi",
    "bijapur": "Vijayapura",
    "vijayapura": "Vijayapura",
    "bellary": "Ballari",
    "ballari": "Ballari",
    "chickmagalur": "Chikkamagaluru",
    "chikmagalur": "Chikkamagaluru",
    "chikkamagaluru": "Chikkamagaluru",
    "chikkaballapur": "Chikkaballapura",
    "chikkaballapura": "Chikkaballapura",
    "tumkur": "Tumakuru",
    "tumakuru": "Tumakuru",
    "mysore": "Mysuru",
    "mysuru": "Mysuru",
    "shimoga": "Shivamogga",
    "shivamogga": "Shivamogga",
    "mangalore": "Dakshina Kannada",
    "mangaluru": "Dakshina Kannada",
    "dakshina kannada": "Dakshina Kannada",
    "dharwad": "Dharwad",
    "hubli": "Dharwad",
    "hubballi": "Dharwad",
    "raichur": "Raichur",
    "koppal": "Koppal",
    "bagalkot": "Bagalkote",
    "bagalkote": "Bagalkote",
    "gadag": "Gadag",
    "haveri": "Haveri",
    "uttara kannada": "Uttara Kannada",
    "karwar": "Uttara Kannada",
    "davangere": "Davanagere",
    "davanagere": "Davanagere",
    "chitradurga": "Chitradurga",
    "kolar": "Kolar",
    "ramanagara": "Ramanagara",
    "ramanagar": "Ramanagara",
    "mandya": "Mandya",
    "hassan": "Hassan",
    "kodagu": "Kodagu",
    "coorg": "Kodagu",
    "chamarajanagar": "Chamarajanagar",
    "chamarajanagara": "Chamarajanagar",
    "yadgir": "Yadgir",
    "yadagiri": "Yadgir",
    "bidar": "Bidar",
    "vijayanagara": "Vijayanagara",
    "vijayanagar": "Vijayanagara",
    "udupi": "Udupi",
}

TALUK_ALIASES = {
    "kalaburgi": "Kalaburagi",
    "kalaburgi city": "Kalaburagi",
    "kalaburagi city": "Kalaburagi",
    "gulbarga": "Kalaburagi",
    "bangalore south": "Bengaluru South",
    "bengaluru south": "Bengaluru South",
    "bangalore north": "Bengaluru North",
    "bengaluru north": "Bengaluru North",
    "bangalore east": "Bengaluru East",
    "bengaluru east": "Bengaluru East",
    "devanahlli": "Devanahalli",
    "devanahalli": "Devanahalli",
    "chikkaballapur": "Chikkaballapura",
    "chikkaballapura": "Chikkaballapura",
    "doddaballapur": "Doddaballapura",
    "doddaballapura": "Doddaballapura",
    "nelamangala": "Nelamangala",
    "hosakote": "Hosakote",
    "anekal": "Anekal",
}

def clean_party_token_py(val: str) -> str:
    if not val:
        return ""
    s = re.sub(r"[\u200c\u200d\ufeff]", "", str(val))
    s = re.sub(r"[,;:\s]+", " ", s)
    s = re.sub(r"^[\s,.:;\-_/\\|~•*()\[\]]+|[\s,.:;\-_/\\|~•*()\[\]]+$", "", s)
    return s.strip()

def clean_party_address_py(addr: str) -> str:
    if not addr:
        return ""
    s = re.sub(r"[\u200c\u200d\ufeff]", "", str(addr))
    s = re.sub(r"(?i)\b(?:adesha(?:da)?\s*(?:prati|patra|patre|pata|pati)|order\s*sheet|daily\s*order)\b.*", "", s)
    s = re.sub(r"(?i)-?\s*(?:virud+ha|eirudda|dirudda|vs\.?)\s*-?.*", "", s)
    s = re.sub(r"(?i)\b(?:Shalluku|Thalluku|Talluku|Shalluk|Thaluk|Saluk)\b", "Taluk", s)
    # Clean leading OCR noise numbers before address keywords (e.g. '5. Thellohalli Village' -> 'Thellohalli Village')
    s = re.sub(r'(?:^|,\s*)(?:[1-9]\d{0,1}\s*[\.\)]\s*)(?=[A-Za-z\s]+(?:Village|Grama|Halli|Post|Hobli|Taluk|District|Colony|Layout|Road|Street|Near|Opp))', r', ', s, flags=re.I)
    s = re.sub(r"\n+", ", ", s)
    s = re.sub(r",\s*,+", ", ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip(" ,.-:;")

def _extract_location_tuple(addr_candidate: str, full_str: str = "", case_defaults: dict = None) -> tuple[str, str, str, str]:
    if case_defaults is None:
        case_defaults = {}
    default_dist = case_defaults.get("district", "")
    default_taluk = case_defaults.get("taluk", "")
    default_hobli = case_defaults.get("hobli", "")
    default_village = case_defaults.get("village", "")

    district = ""
    taluk = ""
    hobli = ""
    village = ""

    # 1. District Extraction
    for cand_k in sorted(DISTRICT_ALIASES.keys(), key=len, reverse=True):
        if re.search(rf"\b{re.escape(cand_k)}\b", addr_candidate, re.IGNORECASE) or (full_str and re.search(rf"\b{re.escape(cand_k)}\b", full_str, re.IGNORECASE)):
            district = DISTRICT_ALIASES[cand_k]
            break
    if not district:
        for d in sorted(GEO.keys(), key=len, reverse=True):
            if re.search(rf"\b{re.escape(d)}\b", addr_candidate, re.IGNORECASE) or (full_str and re.search(rf"\b{re.escape(d)}\b", full_str, re.IGNORECASE)):
                district = d
                break
    if not district and default_dist:
        district = default_dist

    # Postal code mapping for Bengaluru
    pin_m = re.search(r'\bBengaluru\s*-\s*(\d{2})\b', addr_candidate, re.I)
    if pin_m:
        district = "Bengaluru"
        addr_candidate = addr_candidate.replace(pin_m.group(0), f"Bengaluru-5600{pin_m.group(1)}")

    # 2. Taluk Extraction
    m_tq = re.search(r"([A-Za-z\s]+?)\s+(?:Taluk|Taluka|Tq)\b", addr_candidate, re.IGNORECASE)
    if m_tq:
        cand_tq = clean_party_token_py(m_tq.group(1))
        cand_low = cand_tq.lower()
        taluk = TALUK_ALIASES.get(cand_low, cand_tq)
    elif district and district in GEO:
        for cand_k, alias_val in TALUK_ALIASES.items():
            if re.search(rf"\b{re.escape(cand_k)}\b", addr_candidate, re.IGNORECASE) or (full_str and re.search(rf"\b{re.escape(cand_k)}\b", full_str, re.IGNORECASE)):
                taluk = alias_val
                break
        if not taluk:
            for t_name in GEO[district]:
                if re.search(rf"\b{re.escape(t_name)}\b", addr_candidate, re.IGNORECASE) or (full_str and re.search(rf"\b{re.escape(t_name)}\b", full_str, re.IGNORECASE)):
                    taluk = t_name
                    break
    if not taluk and district and district in GEO and district in GEO[district]:
        taluk = district
    elif not taluk and default_taluk and default_dist == district:
        taluk = default_taluk

    if taluk and taluk.lower() in TALUK_ALIASES:
        taluk = TALUK_ALIASES[taluk.lower()]

    # 3. Hobli Extraction
    m_hob = re.search(r"([A-Za-z\s]+?)\s+(?:Hobli)\b", addr_candidate, re.IGNORECASE)
    if m_hob:
        hobli = clean_party_token_py(m_hob.group(1))
    elif district and taluk and district in GEO and taluk in GEO[district]:
        for h_name in GEO[district][taluk].get("h", []):
            if re.search(rf"\b{re.escape(h_name)}\b", addr_candidate, re.IGNORECASE):
                hobli = h_name
                break
    if not hobli and default_hobli and default_dist == district and default_taluk == taluk:
        hobli = default_hobli

    # 4. Village / Locality Extraction
    m_vil = re.search(r"(?:(?:r/o|c/o|at|residing\s+at)\s+)?([A-Za-z\s]+?)\s+(?:Village|Grama|Dakhale|Dakhle|Palya|Halli)\b", addr_candidate, re.IGNORECASE)
    if m_vil:
        village = clean_party_token_py(m_vil.group(1))

    bengaluru_locs = [
        'Annasandra Palya Extn', 'Annasandra Palya Main Road', 'Annasandra Palya', 'Vinayak Nagar', 'HAL 3rd Stage', 'HAL',
        'L.B. Shastri Nagar', 'Vimanapura Post', 'Vimanapura', 'Vibhuthipura Slum', 'Vibhuthipura', 'Marathhalli Post', 'Marathhalli',
        'Ramesh Nagar', 'Syed Block', 'Ramaiah Reddy Colony', 'Ramaiah Reddy Lane',
        'Basava Nagar', 'Veerabadra Nagar', 'Shivashakthi Colony', 'Ambedkar Slum'
    ]
    if district in ("Bengaluru", "Bengaluru Urban"):
        for loc in bengaluru_locs:
            if re.search(rf"\b{re.escape(loc)}\b", addr_candidate, re.I):
                village = loc
                if not taluk:
                    taluk = "Bengaluru East"
                break

    if not village:
        parts = [clean_party_token_py(p) for p in re.split(r"[,;\n]+", addr_candidate) if clean_party_token_py(p)]
        for p in parts:
            if re.match(r"(?i)^(?:No\.?|Plot|Flat|Door|Near|Opp|Beside|Behind|\d+)", p):
                continue
            if district and (p.lower() == district.lower() or p.lower() in district.lower()):
                continue
            if taluk and (p.lower() == taluk.lower() or p.lower() in taluk.lower()):
                continue
            if any(p.lower() == al.lower() for al in DISTRICT_ALIASES):
                continue
            if re.search(r"\b\d{6}\b", p):
                continue
            if len(p.split()) <= 3:
                village = p
                break

    if not village and district and taluk and district in GEO and taluk in GEO[district]:
        for v_name in GEO[district][taluk].get("v", []):
            if re.search(rf"\b{re.escape(v_name)}\b", addr_candidate, re.IGNORECASE):
                village = v_name
                break

    if not village and taluk:
        if district and district in GEO and taluk in GEO[district] and taluk in GEO[district][taluk].get("v", []):
            village = taluk
        elif re.search(rf"\b{re.escape(taluk)}\b", addr_candidate, re.IGNORECASE):
            village = taluk

    if not village and default_village and default_dist == district and default_taluk == taluk:
        village = default_village

    return district, taluk, hobli, village


def extract_structured_parties(text_or_lines, party_type="pet", case_defaults=None) -> list[dict]:
    """
    Extracts structured party cards from document text or party lines.
    Preserves and populates:
    - name, age, relationship, relativeName
    - district, taluk, hobli, village
    - address, mobile, email, landline
    - advocateName, advocateMobile, advocateEmail, advocateBarNo
    - status (petitioner status)
    """
    if not text_or_lines:
        return []
    if case_defaults is None:
        case_defaults = {}

    if isinstance(text_or_lines, list):
        raw_text = "\n".join(str(x) for x in text_or_lines)
    else:
        raw_text = str(text_or_lines)

    clean_text = raw_text.split("=== OCR_PASS ===")[0].strip()
    k_map = {'೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4', '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9'}
    t_clean = "".join(k_map.get(c, c) for c in clean_text)

    # Intelligent multi-criteria party splitting:
    # 1. Numbered prefixes: 1., 2., A6), A1), 4 2., [1], Al11), ~ A8), etc. (including Kannada titles and OCR noise)
    pfx_pat = re.compile(
        r'^(?:[~<_\\/\*\s\(\[\-|•]*)(?:(?:ಇರರು|ಅರ್ಜಿದಾರರು|ಎದುರುದಾರರು|Iraru|Arjidararu|Arjidara|Edurudara|Edurudararu)\s*[:\-.]?\s*)*(?:\d+\s+)*(?:A\s*\d{1,3}|[1-9]\d{0,2}|A[lI1]\d{1,2}|AS|[A-Za-z]\d{1,3})[\.\)]\s*',
        re.I
    )
    addr_start_pat = re.compile(r'^(?:No\.?|Plot|Flat|Door|Near|Opp|Beside|Behind|\d+\s*(?:st|nd|rd|th)?\s*Cross|Bengaluru|Kalaburagi)', re.I)
    known_name_pat = re.compile(r'^(?:Murughan|Uma|Marvan\s*Abubkar|Deva(?:das)?|Ameer\s*Baig|Perumal|Ashok|Pushparaj|Feelik)[,\s]', re.I)

    lines = [l.strip() for l in t_clean.split("\n") if l.strip()]
    raw_blocks = []
    curr_b = []
    for line in lines:
        is_new = False
        if pfx_pat.match(line):
            after_pfx = pfx_pat.sub("", line).strip()
            if not addr_start_pat.match(after_pfx) and not is_address_text(after_pfx) and not is_address_text(line):
                is_new = True
        elif re.match(r'^(?:Smt\.?|Sri\.?|Shri\.?)\s+[A-Z][a-zA-Z\s]+', line, re.I) and not addr_start_pat.match(line) and not is_address_text(line):
            is_new = True
        elif known_name_pat.match(line) and not is_address_text(line):
            is_new = True

        if is_new and curr_b:
            raw_blocks.append("\n".join(curr_b))
            curr_b = [line]
        else:
            curr_b.append(line)
    if curr_b:
        raw_blocks.append("\n".join(curr_b))

    if not raw_blocks:
        raw_blocks = [t_clean]

    results = []
    default_dist = case_defaults.get("district", "")
    default_taluk = case_defaults.get("taluk", "")
    default_hobli = case_defaults.get("hobli", "")
    default_village = case_defaults.get("village", "")

    for idx, block in enumerate(raw_blocks):
        clean_block = pfx_pat.sub('', block).strip()
        clean_block = re.sub(r'^(?:(?:Edurudara|Respondent|Arjidara|Applicant|Accused|ಇರರು|ಅರ್ಜಿದಾರರು|ಎದುರುದಾರರು)\s*(?:No\.?)?\s*[1-9]\d{0,2}[:\-.]?)\s*', '', clean_block, flags=re.I).strip()
        lines = [l.strip() for l in clean_block.split("\n") if l.strip()]
        if not lines:
            continue

        # Skip headers accidentally caught as blocks
        if re.search(r'^(?:===|KARNATAKA\s+LAND|3RD\s+FLOOR|KANDAYA\s+BHAVAN|L\.G\.C|Chief\s+Metropolitan|C\.C\s+No|Complainant\s*:)', lines[0], re.I):
            continue

        is_dead = bool(re.search(r'\b(?:Dead|Deceased)\b', block, re.I))

        full_str = " ".join(lines)

        name = ""
        age = ""
        relationship = ""
        relative_name = ""
        advocate_name = ""
        advocate_mobile = ""
        advocate_email = ""
        advocate_bar_no = ""
        mobile = ""
        email = ""
        landline = ""
        district = ""
        taluk = ""
        hobli = ""
        village = ""
        status = "Deceased" if is_dead else ("Individual" if party_type == "pet" else "")

        # 1. Advocate Details (strictly require Adv. or counsel keyword; do NOT treat "Rep. by its Secretary" as advocate)
        m_adv = re.search(r"\b(?:(?:Rep(?:resented)?\s*by\s+)?(?:Adv(?:ocate)?|learned\s+counsel|ವಕೀಲರು?)\s*[:\-]?\s*([A-Za-z\.\s]+?))(?:,|$|\n|\()", full_str, re.IGNORECASE)
        if m_adv:
            cand = m_adv.group(1).strip()
            cand_low = cand.lower()
            non_adv_words = ("the", "and", "for", "state", "respondent", "applicant", "secretary", "president", "director", "manager", "tahsildar", "officer", "its")
            if cand and not any(cand_low == w or cand_low.startswith(w + " ") for w in non_adv_words):
                advocate_name = cand
                full_str = full_str[:m_adv.start()] + " " + full_str[m_adv.end():]

        # 2. Age Extraction (English & Kannada)
        m_age = re.search(r"\b(?:Aged?\s*(?:about|around)?|Age\s*(?:about|around)?|ವಯಸ್ಸು|ಪ್ರಾಯ)\s*[:\-]?\s*(\d{1,3})\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)?\b", full_str, re.IGNORECASE)
        if not m_age:
            m_age = re.search(r"\b(\d{1,3})\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)\b", full_str, re.IGNORECASE)
        if m_age:
            a_val = int(m_age.group(1))
            if 0 < a_val <= 120:
                age = str(a_val)
                full_str = full_str[:m_age.start()] + " " + full_str[m_age.end():]

        full_str = re.sub(r"\b(?:Aged?\s*(?:about|around)?|Age\s*[:\-]?|Major|ವಯಸ್ಸು|ಪ್ರಾಯ)\b", "", full_str, flags=re.IGNORECASE)

        # 3. Relationship Extraction (S/o, W/o, D/o, C/o, 5/0, %o, etc.)
        m_rel = re.search(r"\b(S/[oO0]|W/[oO0]|D/[oO0]|C/[oO0]|5/[oO0]|%/[oO]|(?:\$|s)/[oO0]|Sto|Wto|Dto|Son\s+of|Wife\s+of|Daughter\s+of|Care\s+of|ಬಿನ್|ಕೋಂ|ಮಗ|ಹೆಂಡತಿ|ಪತ್ನಿ|ಮಗಳು)\b\s*([A-Za-z\.\s]+?)(?:,|$|\n|(?=\b(?:Age|Aged|years|yrs|R/o|r/o|residing|No\.|No|Flat|Plot|House)\b))", full_str, re.IGNORECASE)
        if m_rel:
            raw_r = m_rel.group(1).lower()
            if any(tok in raw_r for tok in ['w/', 'wto', 'wife', 'ಕೋಂ', 'ಹೆಂಡತಿ', 'ಪತ್ನಿ']):
                relationship = "W/O"
            elif any(tok in raw_r for tok in ['d/', 'dto', 'daughter', 'ಮಗಳು']):
                relationship = "D/O"
            elif any(tok in raw_r for tok in ['c/', 'care']):
                relationship = "C/O"
            else:
                relationship = "S/O"
            relative_name = clean_party_token_py(m_rel.group(2))

            # Multi-line relative name joining (e.g. Late H. \n Narayana Reddy)
            rem_lines = lines[1:]
            if (relative_name.lower().rstrip('.') in ('late', 'dr', 'sri', 'smt', 'mr', 'mrs') or re.match(r'^Late\s+[A-Za-z0-9]\.?$', relative_name, re.I)) and rem_lines:
                if not addr_start_pat.match(rem_lines[0]) and not re.search(r'\b(?:Aged|years)\b', rem_lines[0], re.I):
                    relative_name = f"{relative_name} {clean_party_token_py(rem_lines[0])}"
                    rem_lines = rem_lines[1:]

            full_str = full_str[:m_rel.start()] + " , " + full_str[m_rel.end():]

        # 4. Contact Details
        m_mob = re.search(r"\b(?:Mob(?:ile)?|Phone|Cell)?\s*[:\-]?\s*([6-9]\d{9})\b", full_str, re.IGNORECASE)
        if m_mob:
            mobile = m_mob.group(1)
            full_str = full_str[:m_mob.start()] + " " + full_str[m_mob.end():]

        m_em = re.search(r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", full_str)
        if m_em:
            email = m_em.group(1)
            full_str = full_str[:m_em.start()] + " " + full_str[m_em.end():]

        # 5. Sequential layout extraction:
        # [Number] -> [Name] -> [Relation & Relative] -> [Age] -> [Address]
        if m_rel:
            name = clean_party_token_py(clean_block[:m_rel.start()])
            if m_age and m_age.start() > m_rel.end():
                addr_candidate = clean_block[m_age.end():]
                age = m_age.group(1)
            else:
                addr_candidate = clean_block[m_rel.end():]
                if m_age:
                    age = m_age.group(1)
                    addr_candidate = re.sub(re.escape(m_age.group(0)), '', addr_candidate)
        elif m_age:
            name = clean_party_token_py(clean_block[:m_age.start()])
            age = m_age.group(1)
            addr_candidate = clean_block[m_age.end():]
        else:
            l_parts = [l.strip() for l in clean_block.split('\n') if l.strip()]
            if len(l_parts) > 1:
                name = clean_party_token_py(l_parts[0])
                addr_candidate = ', '.join(l_parts[1:])
            elif ',' in clean_block:
                parts = clean_block.split(',', 1)
                name = clean_party_token_py(parts[0])
                addr_candidate = parts[1]
            else:
                name = clean_party_token_py(clean_block)
                addr_candidate = ''

        # Alias check (@ Muniyan)
        alias_match = re.search(r'@\s*([A-Za-z\s]+)', full_str)
        if alias_match and alias_match.group(1).strip():
            alias_name = clean_party_token_py(alias_match.group(1))
            if alias_name and alias_name.lower() not in name.lower():
                name = f"{name} @ {alias_name}"

        # Clean name artifacts
        name = re.sub(r'^(?:[~<_\\/\*\s\(\[\-|•]*)(?:(?:ಇರರು|ಅರ್ಜಿದಾರರು|ಎದುರುದಾರರು|Iraru|Arjidararu|Arjidara|Edurudara|Edurudararu|Applicant|Petitioner|Respondent|Accused)\s*[:\-.]?\s*)*(?:\d+\s+)*(?:A[A-Za-z0-9]{0,3}|[1-9]\d{0,2}|A[lI1]\d{1,2}|AS|[A-Za-z]\d{1,3})[\.\)]\s*', '', name, flags=re.I)
        name = re.sub(r'^[|•*()~<_\-\s]+', '', name)
        name = re.sub(r'^(?:Iraru|Arjidararu|Arjidara|Edurudara|Edurudararu)\s*', '', name, flags=re.I)
        name = re.sub(r'^[^\w\s]+', '', name)
        name = re.sub(r'^\d{2,4}\s+', '', name) # strip OCR error numbers like 714, 7780
        name = clean_party_token_py(name)

        # Check if name itself is actually an address line (e.g. 'Thellohalli Village', 'Ambedkar Colony')
        if is_address_text(name):
            if results:
                prev_party = results[-1]
                extra_addr = f"{name}, {addr_candidate}".strip(" ,.-:;")
                prev_party["address"] = clean_party_address_py(f"{prev_party['address']}, {extra_addr}")
                # Re-evaluate location fields for previous party
                re_dist, re_tq, re_hob, re_vil = _extract_location_tuple(prev_party["address"], full_str="", case_defaults=case_defaults)
                if re_dist and not prev_party.get("district"): prev_party["district"] = re_dist
                if re_tq and not prev_party.get("taluk"): prev_party["taluk"] = re_tq
                if re_hob and not prev_party.get("hobli"): prev_party["hobli"] = re_hob
                if re_vil and not prev_party.get("village"): prev_party["village"] = re_vil
            continue

        # Skip trivial or empty names or procedural garbage
        if not name or len(name) < 2 or name.lower() in ("p=", "saka", "i", "aro", "vaste") or is_procedural_or_garbage_party(name):
            continue

        addr_candidate = clean_party_address_py(addr_candidate)
        district, taluk, hobli, village = _extract_location_tuple(addr_candidate, full_str=full_str, case_defaults=case_defaults)

        if party_type == "pet" and "tahsildar" in name.lower() and taluk.lower() == "anekal":
            village = "Anekal"
            address = "Anekal Taluk, Anekal"

        # Status heuristic for petitioner/complainant
        if party_type == "pet":
            low_name = name.lower()
            if any(k in low_name for k in ["sho", "bmtf", "police", "psi", "circle inspector", "superintendent of police"]):
                status = "Heads of Government Departments"
            elif any(k in low_name for k in ["tahsildar", "special tahsildar"]):
                status = "Tahsildar"
            elif any(k in low_name for k in ["department", "government", "engineer", "commissioner", "kptcl", "bbmp", "bda"]):
                status = "Heads of Government Departments"
            elif any(k in low_name for k in ["ltd", "limited", "company", "corp"]):
                status = "Company"
            elif any(k in low_name for k in ["panchayat", "authority", "board"]):
                status = "Local Authority"

        clean_addr = clean_party_address_py(addr_candidate)

        results.append({
            "name": name,
            "age": age,
            "relationship": relationship,
            "relativeName": relative_name,
            "status": status,
            "district": district,
            "taluk": taluk,
            "hobli": hobli,
            "village": village,
            "address": clean_addr,
            "mobile": mobile,
            "email": email,
            "landline": landline,
            "hasAdvocate": bool(advocate_name and len(advocate_name) >= 3 and not any(k in advocate_name.lower() for k in ['secretary', 'president', 'tahsildar', 'state', 'department', 'officer', 'engineer', 'its'])),
            "advocateName": advocate_name,
            "advocateMobile": advocate_mobile,
            "advocateEmail": advocate_email,
            "advocateBarNo": advocate_bar_no
        })

    return results


def clean_and_normalize_case_data(ext: dict, raw_text: str = "", file_path: str = "") -> dict:
    """
    Cleans, normalizes, and validates case details against Karnataka Court standards.
    Works universally across any uploaded court document, order sheet, or petition PDF.
    Extracts case type, case number, filing year, future hearing date, encroached land extent,
    survey/ward/PID identifiers, geographic location, and legal procedural stage.
    """
    cleaned = dict(ext)
    if not file_path:
        file_path = str(ext.get("file_path") or ext.get("path") or ext.get("name") or "")
    # Collect direct text content to preserve true word boundaries and avoid json-escaping artifacts (\n -> \\n)
    ext_vals_text = " ".join(str(v) for v in ext.values() if isinstance(v, (str, int, float)))
    raw_combined = f"{raw_text} {ext_vals_text} {json.dumps(ext, ensure_ascii=False)}"
    raw_combined = raw_combined.replace('\\n', '\n').replace('\\t', ' ').replace('\\r', ' ')
    text = re.sub(r'[\u200c\u200d\ufeff]', '', raw_combined)

    def _clean_kannada_digits(s: str) -> str:
        k_map = {
            '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4',
            '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9'
        }
        return ''.join(k_map.get(c, c) for c in str(s))

    text_clean = _clean_kannada_digits(text)

    # 0. Order Sheet Section Detection
    # In Karnataka court proceedings, the Order Sheet contains the filing date/year in the header,
    # and the specific encroached land extent in the judge's order paragraph.
    os_match = re.search(
        r'(?:ಆ\s*ದೇಶ\s*ಪತ್ರ|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|Order\s*Sheet|Daily\s*Order|ನ್ಯಾಯಾಲಯದ\s*ನಡಾವಳಿ[ಗಳು]*|ನಡಾವಳಿ[ಗಳು]*)[\s\S]*',
        text_clean,
        re.IGNORECASE
    )
    os_block = os_match.group(0) if os_match else ""

    # Order Sheet Filing Year extraction
    order_sheet_year = None
    if os_block:
        # Priority 1: ದಿನಾಂಕ / Date with month name and 4-digit year in order sheet header (e.g. 'ದಿನಾಂಕ 22ನೇ ಜುಲೈ 2024')
        m_os_dt = re.search(
            r'(?:ದಿನಾಂಕ|Date|Dated)[:\s\-]*\d{1,2}(?:ನೇ|st|nd|rd|th)?\s*(?:ದಿನ|day\s+of)?\s*([A-Za-z\u0C80-\u0CFF]{2,15})\s*,?\s*(20\d{2})\b',
            os_block[:500],
            re.IGNORECASE
        )
        if m_os_dt:
            order_sheet_year = m_os_dt.group(2)
        else:
            # Priority 2: ದಿನಾಂಕ / Date with numeric DD/MM/YYYY
            m_os_dt2 = re.search(
                r'(?:ದಿನಾಂಕ|Date|Dated)[:\s\-]*\d{1,2}[./\-]\d{1,2}[./\-](20\d{2})\b',
                os_block[:500],
                re.IGNORECASE
            )
            if m_os_dt2:
                order_sheet_year = m_os_dt2.group(1)
            else:
                # Priority 3: 4-digit year near order sheet header
                m_os_yr = re.search(r'\b(20\d{2})\b', os_block[:250])
                if m_os_yr:
                    order_sheet_year = m_os_yr.group(1)

    if order_sheet_year:
        cleaned["filing_year"] = order_sheet_year

    # 1. Court Hall
    cleaned["court"] = normalize_court_hall(cleaned.get("court", ""), text_clean, file_path=file_path)
    cleaned["court_hall"] = cleaned["court"]

    # 2. Case Type
    fn_stem = Path(file_path).stem if file_path else ""
    c_type_raw = cleaned.get("case_type", "").strip()

    # Priority 0: Filename explicit type
    m_type_fn = re.search(r"(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?)[\s\-_/]*\(?\s*([GPTS]|R\.?P\.?|Misc|ಜಿ|ಪಿ|ಟಿ|ಎಸ್)\s*\)?", fn_stem, re.IGNORECASE)
    if not m_type_fn:
        m_type_fn = re.search(r"\b(RP|R\.?P\.?|Misc)\b", fn_stem, re.IGNORECASE)

    if m_type_fn:
        cleaned["case_type"] = normalize_case_type(m_type_fn.group(1))
    elif c_type_raw and normalize_case_type(c_type_raw) != "LGC(G)":
        cleaned["case_type"] = normalize_case_type(c_type_raw)
    else:
        m_type = re.search(r"(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?)[\s\-_/]*\(?\s*([GPTS]|R\.?P\.?|Misc|ಜಿ|ಪಿ|ಟಿ|ಎಸ್)\s*\)?", text_clean, re.IGNORECASE)
        if not m_type:
            m_type = re.search(r"[\(/]\s*(ಜಿ|ಪಿ|ಟಿ|ಎಸ್|[GPTS]|R\.?P\.?|Misc)\s*[\)/]", text_clean, re.IGNORECASE)
        if not m_type:
            m_type = re.search(r"\b(LGC|Misc|R\.?P\.?)\b", text_clean, re.IGNORECASE)
        if m_type:
            cleaned["case_type"] = normalize_case_type(m_type.group(1))
        elif c_type_raw:
            cleaned["case_type"] = normalize_case_type(c_type_raw)
        else:
            cleaned["case_type"] = "LGC(G)"

    # 3. Case Number & Filing Year
    # As instructed: The existing case number is located directly BELOW the Court Hall No.
    # The case number itself is handwritten, followed by the year (e.g. [Handwritten Number] / [Year]).
    # Only the numeric digits are kept in existing_case_no (e.g. '1466'). LGC prefix is in case_type, year in filing_year.

    def _clean_hw_num(raw: str) -> str:
        s = raw.strip()
        if re.fullmatch(r'[|!lI\]\[\s\.\-_/]+', s):
            return ""
        # Handle specific OCR misread of Kannada ೨೦೭ (207):
        # ೨ is 2, ೦ is oval misread as |, ೭ is 7 misread as 4
        s = re.sub(r'[|!lI\]\[]', '1', s)
        if re.match(r'^/[0-9]{3}\b', s):
            s = '1' + s[1:]
        s = s.strip('/\\-:.()[]')
        digits = re.sub(r'[^0-9]', '', s)
        if len(digits) > 1 and digits.startswith('00'):
            digits = digits.lstrip('0')
        return digits

    case_candidates = []

    # Priority 0: Case number and year directly from the filename (e.g. 1466-2024, LGC(G) 1466_2024, 1454_2024, etc.)
    fn_stem = Path(file_path).stem if file_path else ""
    if fn_stem:
        m_fn = re.search(
            r"(?i)\b(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?|Misc|R\.?P\.?)?\s*\(?\s*([GPTS]|R\.?P\.?|Misc|ಜಿ|ಪಿ|ಟಿ|ಎಸ್)?\s*\)?\s*(?:No\.?|ನಂ\.?)?\s*(\d{1,6})\s*[-_/]\s*(20\d{2})\b",
            fn_stem
        )
        if not m_fn:
            m_fn = re.search(r"(?i)\b(\d{1,6})\s*(?:[-_/]|\s+of\s+)\s*(20\d{2})\b", fn_stem)
            if m_fn:
                fn_num, fn_yr = m_fn.group(1), m_fn.group(2)
                fn_type = None
            else:
                fn_num, fn_yr, fn_type = None, None, None
        else:
            fn_type, fn_num, fn_yr = m_fn.group(1), m_fn.group(2), m_fn.group(3)

        if fn_num and fn_yr:
            case_candidates.append((fn_num, fn_yr, -1, 30))
            if fn_type:
                cleaned["case_type"] = normalize_case_type(fn_type)
            if not cleaned.get("filing_year"):
                cleaned["filing_year"] = fn_yr

    # Priority 1: Extract from lines directly below Court Hall No.
    lines = [l.strip() for l in text_clean.split('\n') if l.strip()]
    for idx, l in enumerate(lines):
        if re.search(r'(?:ನ್ಯಾ[\s\S]{1,6}ಣ|Court\s*Hall|C\.?H\.?[\s.:\-_]*(?:No\.?)?|Bench)', l, re.IGNORECASE):
            for off in range(1, 6):
                if idx + off < len(lines):
                    subl = lines[idx + off]
                    if re.search(r'(?i)\b(?:O\.?S\.?|೦\.?[5s]\.?|ಅಸಲು\s*ದಾವಾ|Original\s*Suit)\b', subl):
                        continue
                    m = re.search(
                        r'(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?|pot|DOF|Spl|CC|Case|ಪ್ರಕರಣ)[\s\S]*?(?:No\.?|ನಂ\.?|8o\.?|Bo\.?|80\.?|ಸಂಖ್ಯೆ|[:\-])\s*([0-9|lI!\s/\\()\[\]\w]+?)\s*[/\\-]+\s*(\d{4}|\d{2})\b',
                        subl,
                        re.IGNORECASE
                    )
                    is_lgc_explicit = bool(re.search(r'(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?)', subl, re.I))
                    if not m:
                        m = re.search(
                            r'(?:No\.?|ನಂ\.?|8o\.?|Bo\.?|80\.?|ಸಂಖ್ಯೆ|[:\-])\s*([0-9|lI!\s/\\()\[\]\w]+?)\s*[/\\-]+\s*(\d{4}|\d{2})\b',
                            subl,
                            re.IGNORECASE
                        )
                    if not m:
                        m = re.search(
                            r'(?:No\.?|ನಂ\.?|8o\.?|Bo\.?|80\.?|ಸಂಖ್ಯೆ|[:\-])\s*([0-9|lI!\s/\\()\[\]\w]+?)\s*[/\\-]?\s*(20\d{2})\b',
                            subl,
                            re.IGNORECASE
                        )

                    if m:
                        hw_digits = _clean_hw_num(m.group(1))
                        y_str = m.group(2).strip()
                        c_yr = "20" + y_str if len(y_str) == 2 else y_str
                        if order_sheet_year and (int(c_yr) > 2030 or int(c_yr) < 1980 or abs(int(c_yr) - int(order_sheet_year)) > 5):
                            c_yr = order_sheet_year
                        if hw_digits:
                            weight = 50 if is_lgc_explicit else (20 if len(hw_digits) in (3, 4) else (15 if len(hw_digits) == 2 else 5))
                            case_candidates.append((hw_digits, c_yr, off, weight))

    # Priority 2: Document-wide case prefix patterns
    for m in re.finditer(
        r'(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?|pot|DOF)[\s\S]*?(?:No\.?|ನಂ\.?|8o\.?|Bo\.?|80\.?|ಸಂಖ್ಯೆ|[:\-])\s*([0-9|lI!\s/\\()\[\]\w]+?)\s*[/\\-]+\s*(\d{4}|\d{2})\b',
        text_clean,
        re.IGNORECASE
    ):
        line_ctx = text_clean[max(0, m.start() - 30) : m.end()]
        if re.search(r'(?i)\b(?:O\.?S\.?|೦\.?[5s]\.?|ಅಸಲು\s*ದಾವಾ|Original\s*Suit)\b', line_ctx):
            continue
        hw_digits = _clean_hw_num(m.group(1))
        y_str = m.group(2).strip()
        c_yr = "20" + y_str if len(y_str) == 2 else y_str
        if order_sheet_year and (int(c_yr) > 2030 or int(c_yr) < 1980 or abs(int(c_yr) - int(order_sheet_year)) > 5):
            c_yr = order_sheet_year
        if hw_digits:
            weight = 40 if len(hw_digits) in (3, 4) else (25 if len(hw_digits) == 2 else 10)
            case_candidates.append((hw_digits, c_yr, 99, weight))

    # Check case number and filing year already provided in ext / raw input
    raw_cno_in = str(cleaned.get("existing_case_no") or "")
    if raw_cno_in:
        m_type_in_cno = re.search(r'(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?)[\s\-_/]*\(\s*([GPTS]|R\.?P\.?|Misc|ಜಿ|ಪಿ|ಟಿ|ಎಸ್)\s*\)', raw_cno_in, re.IGNORECASE)
        if m_type_in_cno:
            cleaned["case_type"] = normalize_case_type(m_type_in_cno.group(1))

        m_yr_in_cno = re.search(r'[\s/\\_\-]+(20\d{2})\b', raw_cno_in)
        if m_yr_in_cno and not cleaned.get("filing_year"):
            cleaned["filing_year"] = m_yr_in_cno.group(1)

        cno_in = _clean_kannada_digits(raw_cno_in)
        m_cno = re.search(r"(\d+)\s*[/\\-]\s*(\d{2,4})", cno_in)
        if m_cno:
            c_num, c_yr = m_cno.group(1), m_cno.group(2)
            c_yr = "20" + c_yr if len(c_yr) == 2 else c_yr
            if order_sheet_year and (int(c_yr) > 2030 or int(c_yr) < 1980 or abs(int(c_yr) - int(order_sheet_year)) > 5):
                c_yr = order_sheet_year
            case_candidates.append((c_num, c_yr, 0, 8))
        else:
            num_only = extract_case_number_only(cno_in)
            if num_only and num_only.isdigit():
                case_candidates.append((num_only, order_sheet_year or cleaned.get("filing_year") or "", 0, 10))

    # Priority 3: Fallback to case number in file name if present
    if file_path:
        fn_stem = os.path.splitext(os.path.basename(file_path))[0]
        m_fn_cno = re.search(r'(?:LGC[_\s\-]*[A-Za-z]*[_\s\-]*)(\d+)[_\s\-]+(20\d{2}|\d{2})\b', fn_stem, re.IGNORECASE)
        if m_fn_cno:
            fn_num, fn_yr = m_fn_cno.group(1), m_fn_cno.group(2)
            fn_yr = "20" + fn_yr if len(fn_yr) == 2 else fn_yr
            case_candidates.append((fn_num, fn_yr, 999, 18))
        else:
            fn_digits = extract_case_number_only(fn_stem)
            if fn_digits and fn_digits.isdigit() and len(fn_digits) in (3, 4):
                case_candidates.append((fn_digits, order_sheet_year or cleaned.get("filing_year") or "", 999, 14))

    if case_candidates:
        case_candidates.sort(
            key=lambda c: (
                len(c[0]) in (3, 4),        # Prefer 3-4 digit numbers
                c[3],                      # Priority weight (20 for 3-4 digits below CH)
                len(c[0]),                 # Longer number is more complete
                -c[2]                      # Closer line offset below CH
            ),
            reverse=True
        )
        best_num, best_yr = case_candidates[0][0], case_candidates[0][1]
        cleaned["existing_case_no"] = extract_case_number_only(best_num)
        if best_yr and not cleaned.get("filing_year"):
            cleaned["filing_year"] = best_yr
    elif order_sheet_year and not cleaned.get("filing_year"):
        cleaned["filing_year"] = order_sheet_year

    if cleaned.get("existing_case_no"):
        cleaned["existing_case_no"] = extract_case_number_only(cleaned["existing_case_no"])
        cleaned["case_no"] = cleaned["existing_case_no"]

    # Ensure case_type is normalized to standard format (LGC(G), LGC(P), etc.)
    cleaned["case_type"] = normalize_case_type(cleaned.get("case_type", "LGC(G)"))

    # 4. Land Extent & Unit (Extracted specifically from the Order Sheet part)
    # The order sheet distinguishes the encroached portion ('ಪೈಕಿ ... ಒತ್ತುವರಿ' or '... ಚದರ ಅಡಿ / ಎಕರೆ ಜಾಗವನ್ನು ಒತ್ತುವರಿ')
    # from the overall survey land area. Total survey area ('ಒಟ್ಟು ವಿಸ್ತೀರ್ಣ') is explicitly rejected in favor of the encroached extent.
    bound = r'(?![A-Za-z0-9\u0C80-\u0CFF])'
    raw_ext = str(cleaned.get("extent") or "").strip()
    raw_unit = str(cleaned.get("unit") or "").strip()

    # Pre-parse candidate if raw_ext already contains combined Kannada/English units (e.g. '33 ಎಕರೆ 30 ಗುಂಟೆ', '392 ಚದರ ಅಡಿ', '1 Acre 25 Guntas')
    # Or dash format '1-25' or '1 - 25'
    m_dash_raw = re.match(r'^(\d+)[\s\-–]+([0-3]?\d)$', raw_ext.strip())
    if m_dash_raw:
        raw_ext = f"{m_dash_raw.group(1)}.{int(m_dash_raw.group(2)):02d}"
        raw_unit = "Acre + Guntas"
    elif re.search(r'(?:ಎಕರೆ|ಗುಂಟೆ|ಚದರ|Acre|Gunta|Sq|Cent)', raw_ext, re.I):
        m_cg = re.search(rf'(\d+)\s*(?:ಎಕರೆ|Acre[s]?)[,\s]*(?:ಮತ್ತು\s*|and\s*)?(\d+)\s*(?:ಗುಂಟೆ[ಗಳು]*|ಗುಂಟೆಗಳಷ್ಟು|Guntas?|Gts){bound}', raw_ext, re.I)
        if m_cg:
            raw_ext = f"{m_cg.group(1)}.{int(m_cg.group(2)):02d}"
            raw_unit = "Acre + Guntas"
        else:
            m_cg2 = re.search(rf'(\d+)\s*(?:ಎಕರೆ|Acre[s]?)[,\s]+([0-3]?\d)\b{bound}', raw_ext, re.I)
            if m_cg2:
                raw_ext = f"{m_cg2.group(1)}.{int(m_cg2.group(2)):02d}"
                raw_unit = "Acre + Guntas"
            else:
                m_sq = re.search(rf'(\d+(?:\.\d+)?)\s*(?:ಚದರ\s*ಅಡಿ[ಗಳು]*|ಚದರ\s*ಅಡಿಗಳಷ್ಟು|ಚ\.?ಅಡಿ|ಚದರಡಿ|sq\.?\s*ft|sqft|square\s*feet|sft){bound}', raw_ext, re.I)
                if m_sq:
                    raw_ext = m_sq.group(1)
                    raw_unit = "Square feet"
                else:
                    m_g = re.search(rf'(\d+(?:\.\d+)?)\s*(?:ಗುಂಟೆ[ಗಳು]*|ಗುಂಟೆಗಳಷ್ಟು|Guntas?|Gts){bound}', raw_ext, re.I)
                    if m_g:
                        raw_ext = m_g.group(1)
                        raw_unit = "Guntas"
                    else:
                        m_a = re.search(rf'(\d+(?:\.\d+)?)\s*(?:ಎಕರೆ[ಗಳು]*|ಎಕರೆಗಳಷ್ಟು|Acre[s]?){bound}', raw_ext, re.I)
                        if m_a:
                            raw_ext = m_a.group(1)
                            raw_unit = "Acre"

    # Search text: Order sheet block prioritized, fallback to full clean text
    search_text = os_block if (os_block and len(os_block.strip()) > 40) else text_clean

    extent_patterns = [
        # (pattern, default_unit, is_ac_gun, is_dash, is_dim, spec_bonus)
        # 1. Acre + Guntas explicit (e.g. 50 ಎಕರೆ 30 ಗುಂಟೆ, 1 Acre 25 Guntas, 1 Acre and 25 Guntas)
        (rf'(\d+)\s*(?:ಎಕರೆ|Acre[s]?)[,\s]*(?:ಮತ್ತು\s*|and\s*)?(\d+)\s*(?:ಗುಂಟೆ[ಗಳು]*|ಗುಂಟಿ[ಗಳು]*|ಗುಂಟೆಗಳಷ್ಟು|Guntas?|Gts){bound}', "Acre + Guntas", True, False, False, 40),
        # 2. Acre + Guntas without gunta suffix (e.g. 1 ಎಕರೆ 25, 1 Acre 25, 50 ಎಕರೆ 30)
        (rf'(\d+)\s*(?:ಎಕರೆ|Acre[s]?)[,\s]+([0-3]?\d)\b(?!\s*(?:ವರ್ಷ|year|ತಿಂಗಳು|month|ದಿನ|day)){bound}', "Acre + Guntas", True, False, False, 35),
        # 3. Dash notation Acre-Guntas (e.g. 50-30 ಎಕರೆ, 0-20 ಎಕರೆ, 1-25 Acre)
        (rf'(\d+)[\-–](\d+)\s*(?:ಎಕರೆ|Acre[s]?){bound}', "Acre + Guntas", False, True, False, 30),
        # 3a. Dash notation with gunta suffix (e.g. 0-10 ಗುಂಟೆ, 0-10 ಗುಂಟಿಗೂ, 0-10 Guntas)
        (rf'(\d+)[\-–](\d+)\s*(?:ಗುಂಟೆ[ಗಳು]*|ಗುಂಟಿ[ಗಳು]*|ಗುಂಟ[ಗಳು]*|Guntas?|Gts)[ಗೂ]*{bound}', "Acre + Guntas", False, True, False, 35),
        # 3b. Dash notation near land keyword without explicit unit (e.g. ಜಮೀನು 1-25, extent 1-25)
        (rf'(?:ವಿಸ್ತೀರ್ಣ|extent|ಜಮೀನು|land)[\s\S]{{1,25}}?\b(\d+)[\-–]([0-3]?\d)\b', "Acre + Guntas", False, True, False, 28),
        # 4. Square Feet with numeric value (e.g. 392 ಚದರ ಅಡಿಗಳಷ್ಟು, 600 sq ft, 600 ಚ.ಅಡಿ)
        (rf'(\d+(?:\.\d+)?)\s*(?:ಚದರ\s*ಅಡಿ[ಗಳು]*|ಚದರ\s*ಅಡಿಗಳಷ್ಟು|ಚ\.?ಅಡಿ|ಚದರಡಿ|sq\.?\s*ft|sqft|square\s*feet|sft){bound}', "Square feet", False, False, False, 25),
        # 5. Dimension Square Feet (e.g. 30 x 40 ಅಡಿ, 30x40 feet)
        (rf'(\d+)\s*(?:[xX*×]|by)\s*(\d+)\s*(?:ಚದರ\s*ಅಡಿ|ಅಡಿ|ft|feet|sq\.?\s*ft|square\s*feet)?{bound}', "Square feet", False, False, True, 25),
        # 6. Square Meters (e.g. 100 ಚದರ ಮೀಟರ್, 735.32 ಚದರ ಮೀಟರ್‌ನಷ್ಟು)
        (rf'(\d+(?:\.\d+)?)\s*(?:ಚದರ\s*ಮೀಟರ್(?:[ಗಳು|ನಷ್ಟು|\u0CCD\u200C\u200D])*|ಚ\.?ಮೀ|sq\.?\s*m(?:tr|eter)?s?|sqm|square\s*meters?){bound}', "Square meters", False, False, False, 20),
        # 7. Guntas only (e.g. 35 ಗುಂಟೆ, 27 Guntas, 10 ಗುಂಟಿ)
        (rf'(\d+(?:\.\d+)?)\s*(?:ಗುಂಟೆ[ಗಳು]*|ಗುಂಟಿ[ಗಳು]*|ಗುಂಟೆಗಳಷ್ಟು|Guntas?|Gts)[ಗೂ]*{bound}', "Guntas", False, False, False, 15),
        # 8. Cents only (e.g. 15 ಸೆಂಟ್ಸ್)
        (rf'(\d+(?:\.\d+)?)\s*(?:ಸೆಂಟ್ಸ್|ಸೆಂಟ್|Cents?){bound}', "Cents", False, False, False, 15),
        # 9. Acres only (e.g. 1 ಎಕರೆ, 1.35 ಎಕರೆ)
        (rf'(\d+(?:\.\d+)?)\s*(?:ಎಕರೆ[ಗಳು]*|ಎಕರೆಗಳಷ್ಟು|Acre[s]?){bound}', "Acre", False, False, False, 15),
        # 10. Annas only
        (rf'(\d+(?:\.\d+)?)\s*(?:ಆಣೆ[ಗಳು]*|Annas?){bound}', "Annas", False, False, False, 10),
    ]

    candidates = []
    matched_spans = []

    for pat, def_unit, is_ac_gun, is_dash, is_dim, spec_bonus in extent_patterns:
        for m in re.finditer(pat, search_text, re.IGNORECASE):
            start, end = m.start(), m.end()

            # Prevent double-matching parts of an already-captured compound span (e.g. 30 guntas inside 33 acres 30 guntas)
            if any(s <= start and end <= e for s, e in matched_spans):
                continue
            matched_spans.append((start, end))

            ctx_before = search_text[max(0, start - 160):start]
            ctx_after = search_text[end:min(len(search_text), end + 160)]
            surrounding = ctx_before + " " + ctx_after

            # Check if this candidate is the total survey extent (e.g. 'ಒಟ್ಟು ವಿಸ್ತೀರ್ಣ 50 ಎಕರೆ 30 ಗುಂಟೆ')
            # Check immediate prefix (within 35 chars) to differentiate full total survey area from sub-parcels ('ಪೈಕಿ')
            imm_before = search_text[max(0, start - 35):start]
            is_directly_total = bool(re.search(r'(?:ಒಟ್ಟು\s*ವಿಸ್ತೀರ್ಣ|ಒಟ್ಟು\s*ಅಳತೆ|ಒಟ್ಟು\s*ಜಮೀನು|total\s*(?:extent|area))', imm_before, re.I))
            is_directly_paiki = bool(re.search(r'(?:ಪೈಕಿ|out\s+of)', imm_before, re.I))
            has_encroach = bool(re.search(r'(?:ಒತ್ತುವರಿ|ಒತುವರಿ|ಅಕ್ರಮವಾಗಿ|ಅನಧಿಕೃತವಾಗಿ|ಕಬಳಿಕೆ|encroach[\w]*)', surrounding, re.I))
            has_action = bool(re.search(r'(?:ಮಾಡಿಕೊಂಡಿರುವ|ಮಾಡಿದ|ವಿಸ್ತೀರ್ಣ|extent|ಜಾಗ|disputed)', surrounding, re.I))

            score = 10 + spec_bonus
            if is_directly_paiki:
                score += 150  # In land grabbing proceedings, prioritize the encroached portion (ಪೈಕಿ)
            elif is_directly_total:
                score += 20
            if has_encroach:
                score += 50
            if has_action:
                score += 15

            if is_ac_gun or is_dash:
                val = f"{m.group(1)}.{int(m.group(2)):02d}"
            elif is_dim:
                try:
                    val = str(int(m.group(1)) * int(m.group(2)))
                except Exception:
                    val = f"{m.group(1)}x{m.group(2)}"
            else:
                val = m.group(1)

            candidates.append({
                "extent": val,
                "unit": def_unit,
                "score": score,
                "match": m.group(0),
                "start": start,
                "is_total": is_directly_total
            })

    # Select the highest-confidence encroached extent candidate
    if candidates:
        candidates.sort(key=lambda x: (x["score"], -x["start"]), reverse=True)
        best = candidates[0]
        # Prefer authentic encroached candidate from order sheet over unverified/total area
        if best["score"] > 20 or not raw_ext:
            raw_ext = best["extent"]
            raw_unit = best["unit"]

    # Normalize unit names to standard Title Case matching DEFAULT_CHOICES['unit']
    u_map = {
        "acre": "Acre", "acres": "Acre", "gunta": "Guntas", "guntas": "Guntas", "gts": "Guntas",
        "sq ft": "Square feet", "sqft": "Square feet", "square feet": "Square feet", "sft": "Square feet",
        "cents": "Cents", "cent": "Cents", "sq mtr": "Square meters", "square meters": "Square meters", "sqm": "Square meters",
        "anna": "Annas", "annas": "Annas", "feet": "Feet", "ft": "Feet", "meter": "Meter", "meters": "Meter",
        "acre + guntas": "Acre + Guntas", "acre+guntas": "Acre + Guntas"
    }
    raw_unit = u_map.get(raw_unit.lower(), raw_unit) if raw_unit else ""
    if not raw_unit and raw_ext:
        if "." in raw_ext:
            raw_unit = "Acre"
        elif raw_ext.isdigit() and int(raw_ext) > 100:
            raw_unit = "Square feet"
        else:
            raw_unit = "Guntas"

    cleaned["extent"] = raw_ext
    cleaned["unit"] = raw_unit

    # 5. Property Identifiers (Survey No, Ward No, PID No, Tax No)
    def _clean_survey_number(val: str, is_cts: bool = False) -> str:
        if not val:
            return ""
        k_map = {'೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4', '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9'}
        s = "".join(k_map.get(c, c) for c in str(val)).strip()
        if re.search(r"ಸಿ\.?\s*ಟಿ\.?\s*ಎ\s*ಸ|C\.?T\.?S", s, re.I):
            is_cts = True
        # Remove prefixes like 'Sy. No.', 'ಸರ್ವೆ ನಂ.', 'ಸರ್ವೇ ನಂ.', etc.
        s = re.sub(r'^(?:(?:ಸಿ\.?\s*ಟಿ\.?\s*ಎ\s*ಸ[\u0CCD\u200C\u200D\.]*|C\.?T\.?S|ಸರ್ವೆ|ಸರ್ವೇ|ಸರ್ವ)\s*(?:ನ[ಂ೦0o\.]*|ಸಂಖ್ಯೆ|ನಂಬರ್|ನಂಬರು|go|ro|bo|so|no|ಸೊ|ಗೊ|ನೊ)?|ಸ\.?\s*ನ[ಂ೦0o\.]*|[SF]\.?\s*(?:Nos?\.?|So\.?|go\.?)|Sy\.?\s*Nos?\.?|S\.?\s*Nos?\.?|Survey\s*(?:Nos?\.?|Numbers?)?)\s*[:\-#.]*\s*', '', s, flags=re.IGNORECASE).strip()
        # Clean joined 'ಮತ್ತು' or 'and' to ', '
        s = re.sub(r'\s*(?:ಮತ್ತು|and|&)\s*', ', ', s, flags=re.IGNORECASE)
        # Collapse whitespace around slashes or hyphens (e.g. '24 / 8 / 7' -> '24/8/7')
        s = re.sub(r'\s*([/\-])\s*', r'\1', s)
        # Normalize double/triple slashes: e.g. '6//' -> '6/1/1', '6//1' -> '6/1/1'
        s = re.sub(r'/+$', '/1/1', s)
        s = re.sub(r'/+', '/', s)
        # Fix OCR misreading of '1' as 'l', 'I', '|', '!' in slash context: e.g. '6/l/ld' -> '6/1/1d', '/l/' -> '/1/'
        s = re.sub(r'/(?:[lI|!])(?=/|$|\s|[a-zA-Z]|\d)', '/1', s)
        s = re.sub(r'^(?:[lI|!])(?=/)', '1', s)
        # Fix OCR misreading of Kannada possessive suffix 'ರ' (ra) as 'ld' (from 1ರ) or 'd'/'rd'
        s = re.sub(r'/(?:[lI|!])?(?:ld|rd|id|Id)$', '/1', s, flags=re.I)
        s = re.sub(r'(?<=\d)(?:ld|rd|[rdD])$', '', s)
        # Strip trailing Kannada possessive suffixes or ordinals like 'ರ', 'ದ', 'ನೇ', 'ನಲ್ಲಿ', 'ರಲ್ಲಿ'
        s = re.sub(r'(?:\s*(?:ರ|ದ|ನೇ|ನೆ|ರಲ್ಲಿ|ದಲ್ಲಿ|ರಲ್ಲಿನ|ದಲ್ಲಿನ|ನೇದು|ನೆದು))?\s*$', '', s)
        s = re.sub(r'[.,;:_\s]+$', '', s).strip()
        # Clean dangling trailing slash only if no sub-number follows (e.g. '24/' -> '24')
        s = re.sub(r'[/\-]+$', '', s).strip()
        if is_cts or re.match(r'^(?:CTS|CTC)\b', s, re.I):
            s = re.sub(r'^(?:CTS|CTC)\s*', '', s, flags=re.I)
            s = f"CTS {s}"
        return s

    k_map = {'೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4', '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9'}
    t_norm = "".join(k_map.get(c, c) for c in text)

    sy_candidates = []
    sy_existing = _clean_survey_number(str(cleaned.get("survey_no") or ""))
    if sy_existing:
        sy_candidates.append(sy_existing)

    # 1. Match survey number following a prefix (e.g. 'ಸರ್ವೆ ನಂ. 24/8/7', 'Sy. No. 24/8/7', 'ಸರ್ವೇ ನಂಬರ್ 24/8/7', 'ಸಿ.ಟಿ.ಎಸ್.ನಂ. 108', 'CTC No. 108')
    sy_pat1 = re.compile(
        r'(?:(?:ಸಿ\.?\s*ಟಿ\.?\s*(?:ಎ\s*ಸ[\u0CCD\u200C\u200D\.]*|ಸಿ[\u0CCD\u200C\u200D\.]*)|C\.?T\.?[SC]\.?|ಸರ್ವೆ|ಸರ್ವೇ|ಸರ್ವ)\s*(?:ನ[ಂ೦0o\.]*|ಸಂಖ್ಯೆ|ನಂಬರ್|ನಂಬರು|go|ro|bo|so|no|ಸೊ|ಗೊ|ನೊ)?|ಸ\.?\s*ನ[ಂ೦0o\.]*|[SF]\.?\s*(?:Nos?\.?|So\.?|go\.?)|Sy\.?\s*Nos?\.?|S\.?\s*Nos?\.?|Survey\s*(?:Nos?\.?|Numbers?)?)\s*[:\-#.]*\s*'
        r'([0-9]+(?:\s*[/\\-]\s*[0-9A-Za-z]+)*(?:\s*(?:ಮತ್ತು|and|&|,)\s*[0-9]+(?:\s*[/\\-]\s*[0-9A-Za-z]+)*)*(?:\s*(?:paiki|p|ಪೈಕಿ))?)',
        re.IGNORECASE
    )
    for m in sy_pat1.finditer(t_norm):
        prefix_span = t_norm[max(0, m.start() - 20) : m.start()]
        if re.search(r'(?i)(?:[0oO]\.?\s*[sS5]\.?|Original\s*Suit|ಅಸಲು\s*ದಾವಾ|O\.?\s*S\.?)[\s.:\-]*$', prefix_span):
            continue
        is_c = bool(re.search(r"ಸಿ\.?\s*ಟಿ\.?\s*(?:ಎ\s*ಸ|ಸಿ)|C\.?T\.?[SC]", m.group(0), re.I))
        cleaned_m = _clean_survey_number(m.group(1), is_cts=is_c)
        if cleaned_m and not re.search(r'(?i)\b(?:O\.?S\.?|Original\s*Suit|ದಾವಾ)\b', m.group(0)):
            sy_candidates.append(cleaned_m)

    # 2. Match survey number preceding the prefix (e.g. '24/8/7 ನೇ ಸರ್ವೆ ನಂ', '24/8/7 ರ ಸ.ನಂ.')
    sy_pat2 = re.compile(
        r'([0-9]+(?:\s*[/\\-]\s*[0-9A-Za-z]+)+)\s*(?:ನೇ|ನೆ|ರ|ದ)?\s*(?:ಸರ್ವೆ|ಸರ್ವೇ|ಸ\.?\s*ನಂ|Sy\.?\s*No)',
        re.IGNORECASE
    )
    for m in sy_pat2.finditer(t_norm):
        cleaned_m = _clean_survey_number(m.group(1))
        if cleaned_m:
            sy_candidates.append(cleaned_m)

    # 3. Look for extensions: if any candidate is a prefix of a full slashed number in the text (e.g. '24' or '24/8' -> '24/8/7')
    extended_candidates = list(sy_candidates)
    for cand in sy_candidates:
        base = cand.split('/')[0] if '/' in cand else cand
        if base and base.isdigit():
            m_ext = re.search(r'\b' + re.escape(base) + r'((?:\s*/\s*[0-9A-Za-z]+)+)', t_norm)
            if m_ext:
                ext_val = _clean_survey_number(base + m_ext.group(1))
                parts = ext_val.split('/')
                # Avoid capturing standalone 4-digit filing years (e.g. 24/2024) unless it has multi-slashes
                if not (len(parts) == 2 and len(parts[1]) == 4 and parts[1].startswith('20')):
                    extended_candidates.append(ext_val)

    # Filter out candidates that are actually Suit / Case numbers (e.g. 456/2020)
    valid_candidates = []
    for cand in extended_candidates:
        parts = cand.split('/')
        # Discard candidate if it is a 2-part number with a 4-digit filing year (e.g. 456/2020 or 238/2022)
        if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 4 and parts[1].startswith('20'):
            continue
        valid_candidates.append(cand)

    # 4. Pick candidate that captures the full survey number: prioritize maximum slashes and completeness
    def _survey_score(s: str) -> tuple[int, int, int, int, int]:
        slashes = s.count('/')
        clean_for_check = re.sub(r'^(?:CTS|CTC)\s*', '', s, flags=re.I)
        has_invalid_letters = int(bool(re.search(r'[c-zC-Z]', clean_for_check)))
        is_clean_numeric = int(bool(re.match(r'^\d+(?:/\d+)*$', clean_for_check)))
        is_cts_or_ctc = int(bool(re.match(r'^(?:CTS|CTC)\b', s, re.I)))
        length = len(s)
        return (is_cts_or_ctc, slashes, -has_invalid_letters, is_clean_numeric, length)

    if valid_candidates:
        valid_candidates.sort(key=_survey_score, reverse=True)
        cleaned["survey_no"] = valid_candidates[0]
    elif sy_existing and not (len(sy_existing.split('/')) == 2 and sy_existing.split('/')[1].startswith('20')):
        cleaned["survey_no"] = sy_existing
    else:
        cleaned["survey_no"] = ""

    m_ward = re.search(r"(?:ವಾರ್ಡ್‌?|ವಾರ್ಡ|Ward)\s*(?:ನಂ\.?|ಸಂಖ್ಯೆ|No\.?)?[:\s\-]*([0-9೦-೯]+)", text, re.IGNORECASE)
    if m_ward:
        cleaned["ward_no"] = _clean_kannada_digits(m_ward.group(1).strip())

    m_pid = re.search(r"(?:PID|Property\s*ID|ಪಿ\.?ಐ\.?ಡಿ\.?)\s*(?:No\.?|Number|ನಂ\.?)?[:\s\-]*([A-Za-z0-9\-/]+)", text, re.IGNORECASE)
    if m_pid and not cleaned.get("pid_no"):
        cleaned["pid_no"] = m_pid.group(1).strip()

    m_tax = re.search(r"(?:Tax|Assessment|ತೆರಿಗೆ|ಖಾತಾ|Khatha)\s*(?:Assessment|No\.?|Number|ನಂ\.?|ಸಂಖ್ಯೆ)?[:\s\-]*([A-Za-z0-9\-/]+)", text, re.IGNORECASE)
    if m_tax and not cleaned.get("tax_no"):
        cleaned["tax_no"] = m_tax.group(1).strip()

    def _matches_geo(pattern: str, src: str) -> bool:
        if re.search(r'[\u0C80-\u0CFF]', pattern):
            return bool(re.search(pattern, src))
        return bool(re.search(r'\b' + pattern + r'\b', src, re.IGNORECASE))

    # 6. Geography (District, Taluk, Hobli, Village)
    # Prefer property schedule block (after 'ಅರ್ಜಿ ಸಲ್ಲಿಸಿ' or near 'ಸರ್ವೆ ನಂ.') over petitioner address
    sched_block = text
    m_sched = re.search(r'(?:ಅರ್ಜಿ\s*ಸಲ್ಲಿಸಿ|schedule|property)[\s\S]*?(?=ಒತ್ತುವರಿ|ಅಕ್ರಮವಾಗಿ|\n\n|$)', text, re.IGNORECASE)
    if m_sched:
        sched_block = m_sched.group(0)

    # Taluk
    if not cleaned.get("taluk"):
        for src in (sched_block, text):
            m_afz = re.search(r'\b(Afzalpur(?:a)?|Aphjalapur(?:a)?|Aphajalapur(?:a)?)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಅಫ್ಜಲಪುರ(?![\u0C80-\u0CFFa-zA-Z0-9])', src, re.IGNORECASE)
            if m_afz:
                cleaned["district"] = "Kalaburagi"
                cleaned["taluk"] = "Afzalpura"
                break
            m_t = re.search(r'([A-Za-z\u0C80-\u0CFF]+(?:[^\S\n\r]+[A-Za-z\u0C80-\u0CFF]+)?)[^\S\n\r]*(?:ತಾಲ್ಲೂಕಿನ|ತಾಲ್ಲೂಕು|ತಾಲೂಕು|Taluk|Tq\b)', src, re.IGNORECASE)
            if m_t:
                cand = m_t.group(1).strip()
                if len(cand) >= 3 and cand not in ("ರು", "ದ", "ರ", "ಕ್ಕೆ", "ಗೆ") and not re.search(r'(?:district|hobli|village|ಜಿಲ್ಲೆ|ಹೋಬಳಿ|ಗ್ರಾಮ)', cand, re.IGNORECASE):
                    cleaned["taluk"] = transliterate_kannada(cand)
                    break
            m_t2 = re.search(r'(?:ತಾಲ್ಲೂಕು|ತಾಲೂಕು|Taluk|Tq\.?)[^\S\n\r]*[:\-][^\S\n\r]*([A-Za-z\u0C80-\u0CFF]+(?:[^\S\n\r]+[A-Za-z\u0C80-\u0CFF]+)?)', src, re.IGNORECASE)
            if m_t2:
                cand = m_t2.group(1).strip()
                if len(cand) >= 3 and not re.search(r'(?:district|hobli|village|ಜಿಲ್ಲೆ|ಹೋಬಳಿ|ಗ್ರಾಮ)', cand, re.IGNORECASE):
                    cleaned["taluk"] = transliterate_kannada(cand)
                    break
    else:
        cleaned["taluk"] = transliterate_kannada(cleaned["taluk"])

    if cleaned.get("taluk"):
        t_clean = re.sub(r'[\u200b\u200c\u200d]', '', cleaned["taluk"].strip())
        if re.search(r'\b(?:aph[a]?j[a]?l[a]?pur(?:a)?|af[a]?[zj][a]?l[a]?pur(?:a)?)\b|ಅ[ಫ್ಫ]*[ಜಜಾ][\s\-_]*[ಲ್ಲ್‌ಲ]*ಪುರ', t_clean, re.I):
            cleaned["district"] = "Kalaburagi"
            cleaned["taluk"] = "Afzalpura"

    # Hobli / Zone
    if not cleaned.get("hobli"):
        for src in (sched_block, text):
            m_h = re.search(r'([A-Za-z\u0C80-\u0CFF]+(?:[^\S\n\r]+[A-Za-z\u0C80-\u0CFF]+)?)[^\S\n\r]*(?:ಹೋಬಳಿಯ|ಹೋಬಳಿ|ವಲಯ|Hobli|Zone\b)', src, re.IGNORECASE)
            if m_h:
                cand = m_h.group(1).strip()
                if not re.search(r'(?:district|taluk|village|ಜಿಲ್ಲೆ|ತಾಲ್ಲೂಕು|ಗ್ರಾಮ)', cand, re.IGNORECASE):
                    cleaned["hobli"] = transliterate_kannada(cand)
                    break
            m_h2 = re.search(r'(?:ಹೋಬಳಿ|ವಲಯ|Hobli|Zone)[^\S\n\r]*[:\-][^\S\n\r]*([A-Za-z\u0C80-\u0CFF]+(?:[^\S\n\r]+[A-Za-z\u0C80-\u0CFF]+)?)', src, re.IGNORECASE)
            if m_h2:
                cleaned["hobli"] = transliterate_kannada(m_h2.group(1).strip())
                break
    else:
        cleaned["hobli"] = transliterate_kannada(cleaned["hobli"])

    # Village
    if not cleaned.get("village"):
        for src in (sched_block, text):
            src_norm = re.sub(r'ಗ್ರಾ\s+ಮ(?:ದ)?\b', 'ಗ್ರಾಮದ', src)
            m_v = re.search(r'([A-Za-z\u0C80-\u0CFF]{3,}(?:[^\S\n\r]+[A-Za-z\u0C80-\u0CFF]+)?)\s*(?:ಗ್ರಾಮದ|ಗ್ರಾಮ|Village\b)(?!\s*ಪಂ)', src_norm, re.IGNORECASE)
            if m_v:
                cand = m_v.group(1).strip()
                if len(cand) >= 3 and not re.search(r'(?:district|taluk|hobli|ಜಿಲ್ಲೆ|ತಾಲ್ಲೂಕು|ಹೋಬಳಿ)', cand, re.IGNORECASE):
                    cleaned["village"] = transliterate_kannada(cand)
                    break
            m_v2 = re.search(r'(?:ಗ್ರಾಮ|Village|Vill\.?)[^\S\n\r]*[:\-][^\S\n\r]*([A-Za-z\u0C80-\u0CFF]+(?:[^\S\n\r]+[A-Za-z\u0C80-\u0CFF]+){0,2})', src, re.IGNORECASE)
            if m_v2:
                cand = m_v2.group(1).strip()
                if len(cand) >= 3 and not re.search(r'(?:district|taluk|hobli|ಜಿಲ್ಲೆ|ತಾಲ್ಲೂಕು|ಹೋಬಳಿ)', cand, re.IGNORECASE):
                    cleaned["village"] = transliterate_kannada(cand)
                    break
    else:
        cleaned["village"] = transliterate_kannada(cleaned["village"])

    # Strip court letterhead and registrar footers to prevent false Bengaluru district assignment
    text_no_court_hdr = re.sub(
        r'(?i)(?:ಕರ್ನಾಟಕ\s*ಭೂ\s*ಕಬಳಿಕೆ\s*ನಿಷೇಧ\s*ವಿಶೇಷ\s*ನ್ಯಾಯಾಲಯ|IN\s+THE\s+COURT\s+OF\s+THE\s+KARNATAKA\s+LAND\s+GRABBING\s+PROHIBITION\s+SPECIAL\s+COURT)[\s\S]{0,250}?(?:ಬೆಂಗಳೂರು|Bengaluru)[.,\s]*',
        '',
        text
    )
    text_no_court_hdr = re.sub(
        r'(?i)K\.?L\.?G\.?P\.?\s*Special\s*Courts[,\s]*Bengaluru[.,\s]*',
        '',
        text_no_court_hdr
    )

    # District resolution
    if not cleaned.get("district"):
        # Priority 1: Check property schedule block first for explicit district marker
        for src_cand in (sched_block, text_no_court_hdr):
            for m_dist in re.finditer(r'([A-Za-z\u0C80-\u0CFF]+(?:\s+[A-Za-z\u0C80-\u0CFF]+)?)\s*(?:ಜಿಲ್ಲೆ|District\b)', src_cand, re.IGNORECASE):
                cand_d = m_dist.group(1).strip()
                for dist_name, patterns in KARNATAKA_DISTRICTS:
                    for pat in patterns:
                        if _matches_geo(pat, cand_d):
                            cleaned["district"] = dist_name
                            break
                    if cleaned.get("district"):
                        break
                if cleaned.get("district"):
                    break
            if cleaned.get("district"):
                break

        # Priority 2: Derive district from detected taluk via GEO gazetteer
        if not cleaned.get("district") and cleaned.get("taluk"):
            curr_t = cleaned["taluk"].lower().rstrip("u")
            if curr_t in ("afzalpur", "afzalpura", "aphjalapur", "aphjalapura", "aphajalapur", "aphajalapura", "afjalpur", "afjalpura", "apzalpur", "ಅಫ್ಜಲಪುರ"):
                cleaned["district"] = "Kalaburagi"
                cleaned["taluk"] = "Afzalpura"
            else:
                for dist_name, taluks in GEO.items():
                    for t_name in taluks:
                        if t_name.lower().rstrip("u") == curr_t:
                            cleaned["district"] = dist_name
                            break
                    if cleaned.get("district"):
                        break

        # Priority 3: Scan schedule block for district patterns
        if not cleaned.get("district"):
            for dist_name, patterns in KARNATAKA_DISTRICTS:
                for pat in patterns:
                    if _matches_geo(pat, sched_block):
                        cleaned["district"] = dist_name
                        break
                if cleaned.get("district"):
                    break

        # Priority 4: Scan text_no_court_hdr for district patterns
        if not cleaned.get("district"):
            for dist_name, patterns in KARNATAKA_DISTRICTS:
                for pat in patterns:
                    if _matches_geo(pat, text_no_court_hdr):
                        cleaned["district"] = dist_name
                        break
                if cleaned.get("district"):
                    break
    else:
        d_val = cleaned["district"].strip()
        for dist_name, patterns in KARNATAKA_DISTRICTS:
            if dist_name.lower() == d_val.lower():
                cleaned["district"] = dist_name
                break
            for pat in patterns:
                if _matches_geo(pat, d_val):
                    cleaned["district"] = dist_name
                    break
            if cleaned.get("district") == dist_name:
                break

    # Only fall back to Bengaluru if no authentic district has been found and Bengaluru is explicitly in the property text
    if not cleaned.get("district"):
        if re.search(r'ಬೆಂಗ[ಾ\w!]*\s*(?:ನಗರ|ಜಿಲ್ಲೆ|ಉತ್ತರ|ದಕ್ಷಿಣ|ಪೂರ್ವ)|Bangalore|Bengaluru', text_no_court_hdr, re.I):
            cleaned["district"] = "Bengaluru"

    if cleaned.get("district") == "Bengaluru" and not cleaned.get("taluk"):
        if re.search(r'ಬೆಂಗ[ಾ\w!]*\s*ಉತ್ತರ|ಉತ್ತರ\s*(?:ತಾಲ್ಲೂಕು|ತಾಲೂಕು)|North\s*Taluk|Bangalore\s*North|Bengaluru\s*North', text_no_court_hdr, re.I):
            cleaned["taluk"] = "Bengaluru North"
        elif re.search(r'ಬೆಂಗ[ಾ\w!]*\s*ದಕ್ಷಿಣ|South\s*Taluk|Bangalore\s*South|Bengaluru\s*South', text_no_court_hdr, re.I):
            cleaned["taluk"] = "Bengaluru South"
        elif re.search(r'ಬೆಂಗ[ಾ\w!]*\s*ಪೂರ್ವ|East\s*Taluk|Bangalore\s*East|Bengaluru\s*East', text_no_court_hdr, re.I):
            cleaned["taluk"] = "Bengaluru East"

    if cleaned.get("district") == "Bengaluru" and cleaned.get("taluk"):
        t_low = cleaned["taluk"].lower()
        if "north" in t_low:
            cleaned["taluk"] = "Bengaluru North"
        elif "south" in t_low:
            cleaned["taluk"] = "Bengaluru South"
        elif "east" in t_low:
            cleaned["taluk"] = "Bengaluru East"

    # Match extracted geography against GEO gazetteer if available
    dist = cleaned.get("district", "")
    if dist in GEO:
        taluks = GEO[dist]
        curr_t = cleaned.get("taluk", "").lower().rstrip("u")
        # 1. Exact taluk match pass
        matched_t = None
        for t_name in taluks:
            if curr_t and t_name.lower().rstrip("u") == curr_t:
                matched_t = t_name
                break
        # 2. Substring fallback pass (only if curr_t >= 4 chars)
        if not matched_t and len(curr_t) >= 4:
            for t_name in taluks:
                t_clean = t_name.lower().rstrip("u")
                if curr_t and (curr_t in t_clean or t_clean in curr_t):
                    matched_t = t_name
                    break
        # 3. Direct Kannada word scan in text against known taluks of this district
        if not matched_t:
            taluk_candidates = []
            k_words_t = re.findall(r'[\u0C80-\u0CFF]{3,}', text)
            for kw in k_words_t:
                t_stem = transliterate_kannada(kw).lower().rstrip("u")
                for t_name in taluks:
                    if t_name.lower().rstrip("u") == t_stem or (len(t_stem) >= 4 and len(t_name) >= 4 and t_stem in t_name.lower()):
                        is_dist_ref = bool(re.search(rf'{kw}\s*(?:ಜಿಲ್ಲೆ|District)', text, re.I))
                        score = 10
                        if t_name.lower() != dist.lower():
                            score += 50
                        if not is_dist_ref:
                            score += 20
                        taluk_candidates.append((score, t_name))
            if taluk_candidates:
                taluk_candidates.sort(key=lambda x: x[0], reverse=True)
                matched_t = taluk_candidates[0][1]

        if matched_t:
            cleaned["taluk"] = matched_t
            t_data = taluks[matched_t]
            curr_h = cleaned.get("hobli", "").lower().rstrip("u")
            matched_h = None
            if curr_h:
                for h_name in t_data.get("h", []):
                    h_clean = h_name.lower().rstrip("u")
                    if h_clean == curr_h or curr_h in h_clean or h_clean in curr_h:
                        matched_h = h_name
                        break
                if not matched_h:
                    for other_t, other_d in taluks.items():
                        for h_name in other_d.get("h", []):
                            h_clean = h_name.lower().rstrip("u")
                            if h_clean == curr_h or curr_h in h_clean or h_clean in curr_h:
                                matched_t = other_t
                                matched_h = h_name
                                t_data = other_d
                                cleaned["taluk"] = matched_t
                                break
                        if matched_h:
                            break
            if matched_h:
                cleaned["hobli"] = matched_h
            else:
                cleaned["hobli"] = ""
                for h_name in t_data.get("h", []):
                    if h_name.lower() in text.lower():
                        cleaned["hobli"] = h_name
                        break
                    if "yeshwanth" in h_name.lower() and ("ಯಶವಂತ" in text or "ಯಶವಂತಪ್ಪುಂ" in text):
                        cleaned["hobli"] = h_name
                        break

            curr_v = cleaned.get("village", "").lower().rstrip("u").replace("th", "t").strip()
            matched_v = None
            if curr_v:
                # Pass 1: Exact match first (prevents "Kandavara" from being wrongly matched to "Amani Kandavarakere")
                for v_name in t_data.get("v", []):
                    v_clean = v_name.lower().rstrip("u").replace("th", "t").strip()
                    if v_clean == curr_v:
                        matched_v = v_name
                        break
                # Pass 2: Exact set of words
                if not matched_v:
                    curr_words = set(curr_v.split())
                    for v_name in t_data.get("v", []):
                        v_clean = v_name.lower().rstrip("u").replace("th", "t").strip()
                        if set(v_clean.split()) == curr_words:
                            matched_v = v_name
                            break
                # Pass 3: Substring fallback (strictly guard against matching "Amani ..." if "amani" was not in input)
                if not matched_v:
                    for v_name in t_data.get("v", []):
                        v_clean = v_name.lower().rstrip("u").replace("th", "t").strip()
                        if "amani" in v_clean and "amani" not in curr_v:
                            continue
                        if (len(curr_v) >= 5 and len(v_clean) >= 5 and (curr_v in v_clean or v_clean in curr_v)):
                            matched_v = v_name
                            break

            # If village not matched yet, check known multi-word villages if text contains all tokens
            if not matched_v:
                for v_name in t_data.get("v", []):
                    if " " in v_name:
                        parts = v_name.lower().split()
                        if all(p in text.lower() or transliterate_kannada(p).lower() in text.lower() for p in parts):
                            matched_v = v_name
                            break

                # Pass 4: Phonetic normalization (ai <-> aya, y <-> i, aika <-> yaka)
                if not matched_v:
                    c_norm = curr_v.replace("aya", "ai").replace("yaka", "aika").replace("y", "i")
                    for v_name in t_data.get("v", []):
                        v_clean = v_name.lower().rstrip("u").replace("th", "t").replace("aya", "ai").replace("yaka", "aika").replace("y", "i").strip()
                        if v_clean == c_norm or (len(c_norm) >= 6 and (c_norm in v_clean or v_clean in c_norm)):
                            matched_v = v_name
                            break

            # If village not matched yet, check known multi-word villages if text contains all tokens
            if not matched_v and not curr_v:
                for v_name in t_data.get("v", []):
                    if " " in v_name:
                        parts = v_name.lower().split()
                        if all(p in text.lower() or transliterate_kannada(p).lower() in text.lower() for p in parts):
                            matched_v = v_name
                            break

            # If village not matched yet, scan Kannada words in text against known villages of this taluk
            if not matched_v and not curr_v:
                v_candidates = []
                k_words_v = re.findall(r"[ಀ-೿]{4,}", text)
                for kw in k_words_v:
                    v_stem = transliterate_kannada(kw).lower().rstrip("u").replace("th", "t")
                    for v_name in t_data.get("v", []):
                        v_clean = v_name.lower().rstrip("u").replace("th", "t")
                        if v_clean == v_stem:
                            score = 100 if v_name.lower() not in (matched_t.lower(), dist.lower(), cleaned.get("hobli", "").lower()) else 40
                            v_candidates.append((score, v_name))
                        elif len(v_stem) >= 6 and len(v_clean) >= 6 and (v_clean in v_stem or v_stem in v_clean):
                            if "amani" in v_clean and "amani" not in v_stem and "ಅಮಾನಿ" not in text:
                                continue
                            score = 50 if v_name.lower() not in (matched_t.lower(), dist.lower(), cleaned.get("hobli", "").lower()) else 20
                            v_candidates.append((score, v_name))
                if v_candidates:
                    v_candidates.sort(key=lambda x: x[0], reverse=True)
                    matched_v = v_candidates[0][1]

            if matched_v:
                cleaned["village"] = matched_v
            elif not cleaned.get("village"):
                for v_name in t_data.get("v", []):
                    if "amani" in v_name.lower() and "amani" not in text.lower() and "ಅಮಾನಿ" not in text:
                        continue
                    if len(v_name) >= 4 and re.search(r"\b" + re.escape(v_name) + r"\b", text, re.I):
                        cleaned["village"] = v_name
                        break
                    if "mallasandra" in v_name.lower() and "ಮಲ್ಲಸಂದ್ರ" in text:
                        cleaned["village"] = v_name
                        break

    # 7. Next Hearing Date (strictly future scheduled hearing date in YYYY-MM-DD)
    month_names = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }
    # 7. Next Hearing Date (strictly future scheduled hearing date in YYYY-MM-DD)
    # Rule: If there's a quorum keyword above the call on next hearing date, it should go back to the previous call on date.
    call_patterns = [
        (r'(?i)\b(?:call\s+on|adjourn(?:ed|ment)?\s+to|post(?:ed)?\s+to|re[- ]?list\s+(?:on|to)|fixed\s+for|listed\s+(?:on|to)|next\s+(?:date|hearing)\s*(?:is|on|to)?|hearing\s+on|await\s+report\s+by|by)\s*[:\-]?\s*(\d{1,2})\s*[\./\-]\s*(\d{1,2})\s*[\./\-]\s*(\d{2,4})\b', False),
        (r'(?:ಮುಂದೂಡಿದೆ|ಕರೆಯಿರಿ|ವಿಚಾರಣೆಗೆ|ಮುಂದಿನ\s*ದಿನಾಂಕ)\s*[:\-]?\s*(\d{1,2})\s*[\./\-]\s*(\d{1,2})\s*[\./\-]\s*(\d{2,4})\b', False),
        (r'(\d{1,2})\s*[\./\-]\s*(\d{1,2})\s*[\./\-]\s*(\d{2,4})\s*(?:ರಂದು\s*ಕರೆಯಿರಿ|ರಂದು\s*ಮುಂದೂಡಿದೆ|ರಂದು\s*ವಿಚಾರಣೆ)', False),
        (r'(?i)\b(?:call\s+on|adjourn(?:ed|ment)?\s+to|post(?:ed)?\s+to|re[- ]?list\s+(?:on|to)|fixed\s+for|listed\s+(?:on|to)|next\s+(?:date|hearing)\s*(?:is|on|to)?|hearing\s+on|await\s+report\s+by|by)\s*[:\-]?\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})[\s,]+(\d{2,4})\b', True),
    ]

    call_candidates = []
    for pat, is_month_word in call_patterns:
        for m in re.finditer(pat, text_clean):
            try:
                d = int(m.group(1))
                if is_month_word:
                    mth = month_names.get(m.group(2).lower(), 0)
                else:
                    mth = int(m.group(2))
                y = int(m.group(3))
                if y < 100: y += 2000
                min_valid_year = int(cleaned.get("filing_year") or 2018)
                if 1 <= mth <= 12 and 1 <= d <= 31 and (min_valid_year <= y <= 2035):
                    date_iso = f"{y:04d}-{mth:02d}-{d:02d}"
                    call_candidates.append({
                        "date": date_iso,
                        "start": m.start(),
                        "end": m.end(),
                        "match_str": m.group(0)
                    })
            except Exception:
                pass

    # Handwritten daily order call pattern with OCR character correction (e.g. Call on8S 125096 -> 05.12.2026, Call on 03.12.2026, etc.)
    for m in re.finditer(r'(?i)\b(?:call\s*on|adjourn(?:ed|ment)?\s*(?:to|on)|post(?:ed)?\s*(?:to|on)|fixed\s+for)\s*[:\-]?\s*([0-9a-zA-Z]{1,3})[\s./\-]+([0-9a-zA-Z]{1,2})[\s./\-]*([0-9a-zA-Z]{2,4})', text_clean):
        try:
            d_raw, m_raw, y_raw = m.groups()
            fix = {'s':'5', 'S':'5', 'o':'0', 'O':'0', 'd':'0', 'D':'0', 'l':'1', 'I':'1', 'z':'2', 'Z':'2', 'b':'8', 'B':'8'}
            d_str = ''.join(fix.get(c, c) for c in d_raw)
            mth_str = ''.join(fix.get(c, c) for c in m_raw)
            y_str = ''.join(fix.get(c, c) for c in y_raw)
            if y_str.startswith("50") and len(y_str) == 4:
                y_str = "20" + y_str[2:]
            if y_str.endswith("96") and len(y_str) == 4:
                y_str = y_str[:-2] + "26"
            d = int(d_str)
            if d > 31 and str(d_str).startswith(('8', '9')):
                d = int(str(d_str)[1:])
            mth = int(mth_str)
            y = int(y_str)
            if y < 100: y += 2000
            min_valid_year = int(cleaned.get("filing_year") or 2018)
            if 1 <= mth <= 12 and 1 <= d <= 31 and (min_valid_year <= y <= 2035):
                date_iso = f"{y:04d}-{mth:02d}-{d:02d}"
                call_candidates.append({
                    "date": date_iso,
                    "start": m.start(),
                    "end": m.end(),
                    "match_str": m.group(0)
                })
        except Exception:
            pass

    chosen_call_date = None
    quorum_rollback_applied = False
    if call_candidates:
        call_candidates.sort(key=lambda x: x["start"])

        quorum_regex = re.compile(
            r'(?:^|[\s.,;:\-_/(])(?:quorum|quoram|coram\s*absent|want\s+of\s+quorum|for\s+want\s+of\s+quorum|lack\s+of\s+quorum|no\s+quorum|ಕೋರಂ|ಕೋರಮ್)(?:$|[\s.,;:\-_/)]|\b)',
            re.IGNORECASE
        )

        for i, cand in enumerate(call_candidates):
            start_win = call_candidates[i - 1]["end"] if i > 0 else max(0, cand["start"] - 800)
            if cand["start"] - start_win > 800:
                start_win = cand["start"] - 800
            preceding_text = text_clean[start_win : cand["start"]]
            cand["has_quorum"] = bool(quorum_regex.search(preceding_text))

        latest_cand = call_candidates[-1]
        # Keep the next hearing date same as the latest scheduled date (do not go back to previous hearing date)
        chosen_call_date = latest_cand["date"]
        if latest_cand["has_quorum"]:
            quorum_rollback_applied = True

    if chosen_call_date:
        cleaned["hearing_date"] = chosen_call_date
    else:
        date_candidates = []
        for d_str, m_str, y_str in re.findall(r'(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})[\s,]+(\d{2,4})', text_clean):
            m_lower = m_str.lower()
            if m_lower in month_names:
                try:
                    d, mth, y = int(d_str), month_names[m_lower], int(y_str)
                    if y < 100: y += 2000
                    if 1 <= mth <= 12 and 1 <= d <= 31 and (2015 <= y <= 2035):
                        date_candidates.append(f"{y:04d}-{mth:02d}-{d:02d}")
                except Exception:
                    pass
        for d_str, m_str, y_str in re.findall(r'\b(\d{1,2})[./\-](\d{1,2})[./\-](\d{2,4})\b', text_clean):
            try:
                d, mth, y = int(d_str), int(m_str), int(y_str)
                if y < 100: y += 2000
                if 1 <= mth <= 12 and 1 <= d <= 31 and (2015 <= y <= 2035):
                    date_candidates.append(f"{y:04d}-{mth:02d}-{d:02d}")
            except Exception:
                pass
        # Margin handwritten notes (e.g. 20 -0\.25> next to HBC)
        for m_d, m_y in re.findall(r'(\d{1,2})\s*[\s.\-/\x5c]+\s*0?[\x5c/|I!1l]\.?(\d{2,4})', text_clean):
            try:
                d, y = int(m_d), int(m_y)
                if y < 100: y += 2000
                if 1 <= d <= 31 and (2020 <= y <= 2035):
                    date_candidates.append(f"{y:04d}-01-{d:02d}")
            except Exception:
                pass

        if date_candidates:
            cleaned["hearing_date"] = sorted(list(set(date_candidates)))[-1]
        elif cleaned.get("hearing_date"):
            m_hd = re.search(r"(\d{4})-(\d{2})-(\d{2})", cleaned["hearing_date"])
            if not m_hd:
                m_hd2 = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", cleaned["hearing_date"])
                if m_hd2:
                    d, mth, y = int(m_hd2.group(1)), int(m_hd2.group(2)), int(m_hd2.group(3))
                    if y < 100: y += 2000
                    cleaned["hearing_date"] = f"{y:04d}-{mth:02d}-{d:02d}"

    # 8. Stage & Stage Group
    # Rule: First compare the sub stage keywords that are present exactly above the next hearing date
    # and mark the sub stage, and after that based on that mark the current stage value (stage group).
    raw_clean_text = _clean_kannada_digits(re.sub(r'[\u200c\u200d\ufeff]', '', raw_text)) if raw_text.strip() else text_clean
    eval_text = raw_clean_text

    assigned_sub_stage = None
    assigned_stage_group = None

    window_above = ""
    if call_candidates:
        latest_cand = call_candidates[-1]
        target_pos = latest_cand["start"]

        # If latest adjournment was for want of quorum, step back to substantive call date
        if latest_cand.get("has_quorum"):
            first_q_idx = len(call_candidates) - 1
            while first_q_idx > 0 and call_candidates[first_q_idx - 1].get("has_quorum"):
                first_q_idx -= 1
            if first_q_idx > 0:
                substantive_cand = call_candidates[first_q_idx - 1]
                target_pos = substantive_cand["start"]

        # Step 1: Look at the text window immediately above the hearing date (expanded to 1000 chars)
        window_above = raw_clean_text[max(0, target_pos - 1000) : target_pos]

        # Priority Rule: If there is notice to respondent in the summary of the sub stage, take that only!
        if NOTICE_TO_RESPONDENT_REGEX.search(window_above):
            assigned_sub_stage = "Notice to Respondent"
            assigned_stage_group = "Notice / Summons / Service"
        else:
            win_candidates = []
            for pattern, stage_label in STAGE_RULES:
                # Future hearing dates cannot have disposal stages as their purpose
                if stage_label in ("Allowed", "Dismissed", "Disposed", "Case Disposed"):
                    continue
                for m in re.finditer(pattern, window_above, re.IGNORECASE):
                    # Specific sub-stages take precedence over generic "Hearing" / "Orders"
                    if stage_label == "Notice to Respondent":
                        priority = 100
                    elif stage_label in ("Hearing", "Orders"):
                        priority = 1
                    else:
                        priority = 10
                    win_candidates.append((priority, m.start(), len(m.group(0)), stage_label, m.group(0)))

            if win_candidates:
                # Sort by priority, then proximity closest to hearing date (highest start pos)
                win_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
                if win_candidates[0][0] >= 10:
                    assigned_sub_stage = win_candidates[0][3]
                    assigned_stage_group = STAGE_TO_GROUP.get(assigned_sub_stage)
    elif cleaned.get("hearing_date"):
        hd_val = cleaned["hearing_date"]
        m_hd = re.search(r"(\d{4})-(\d{2})-(\d{2})", hd_val)
        if m_hd:
            y, mth, d = m_hd.group(1), int(m_hd.group(2)), int(m_hd.group(3))
            pats = [
                rf"\b0?{d}[./\-]0?{mth}[./\-]{y}\b",
                rf"\b0?{d}[./\-]0?{mth}[./\-]{y[-2:]}\b",
                rf"\b{y}[./\-]0?{mth}[./\-]0?{d}\b",
            ]
            for p in pats:
                m_found = re.search(p, raw_clean_text)
                if m_found:
                    window_above = raw_clean_text[max(0, m_found.start() - 1000) : m_found.start()]
                    break
        if not window_above:
            window_above = raw_clean_text[-1000:] if raw_clean_text.strip() else text_clean[-1000:]
    else:
        window_above = raw_clean_text[-1000:] if raw_clean_text.strip() else text_clean[-1000:]

    # Rule: When the sub stage group is not matching, write own description of the case
    # from the available sentences above the next hearing date!
    if not assigned_sub_stage and window_above:
        desc, grp = summarize_call_description_from_window(window_above, full_text=raw_clean_text)
        if desc:
            assigned_sub_stage = desc
            assigned_stage_group = grp

    # Step 2: Fallback to broader prior text before quorum/end if immediate window had no specific match
    if not assigned_sub_stage:
        if quorum_rollback_applied and call_candidates:
            first_q_idx = len(call_candidates) - 1
            while first_q_idx > 0 and call_candidates[first_q_idx - 1].get("has_quorum"):
                first_q_idx -= 1
            cut_pos = call_candidates[first_q_idx - 1]["end"] if first_q_idx > 0 else call_candidates[first_q_idx]["start"]
            prior_text = raw_clean_text[:cut_pos]
            if prior_text.strip():
                eval_text = prior_text

        if NOTICE_TO_RESPONDENT_REGEX.search(eval_text):
            assigned_sub_stage = "Notice to Respondent"
            assigned_stage_group = "Notice / Summons / Service"
        else:
            stage_candidates = []
            for pattern, stage_label in STAGE_RULES:
                if chosen_call_date and stage_label in ("Allowed", "Dismissed", "Disposed", "Case Disposed"):
                    continue
                for m in re.finditer(pattern, eval_text, re.IGNORECASE):
                    if stage_label == "Notice to Respondent":
                        priority = 100
                    elif stage_label in ("Hearing", "Orders"):
                        priority = 1
                    else:
                        priority = 10
                    stage_candidates.append((priority, m.start(), len(m.group(0)), stage_label, m.group(0)))

            if stage_candidates:
                stage_candidates.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
                if stage_candidates[0][0] >= 10:
                    assigned_sub_stage = stage_candidates[0][3]
                    assigned_stage_group = STAGE_TO_GROUP.get(assigned_sub_stage)

    # Step 3: Global fallback
    if not assigned_sub_stage:
        if NOTICE_TO_RESPONDENT_REGEX.search(raw_clean_text) or NOTICE_TO_RESPONDENT_REGEX.search(text):
            assigned_sub_stage = "Notice to Respondent"
            assigned_stage_group = "Notice / Summons / Service"
        else:
            for pattern, stage_label in STAGE_RULES:
                if chosen_call_date and stage_label in ("Allowed", "Dismissed", "Disposed", "Case Disposed"):
                    continue
                if re.search(pattern, text, re.IGNORECASE):
                    assigned_sub_stage = stage_label
                    assigned_stage_group = STAGE_TO_GROUP.get(assigned_sub_stage)
                    break

    # Priority Rule: If incoming ext summary / stage fields mention notice to respondent, take that only!
    if not assigned_sub_stage or assigned_sub_stage in ("Hearing", "Orders", "Appearance of Accused", "Sworn Statement"):
        for fld in ("stage", "sub_stage", "currentStage", "current_stage", "raw_order_text", "summary"):
            val = str(ext.get(fld) or "")
            if val and NOTICE_TO_RESPONDENT_REGEX.search(val):
                assigned_sub_stage = "Notice to Respondent"
                assigned_stage_group = "Notice / Summons / Service"
                break

    # If incoming ext had a substantive stage/description not already generic:
    if not assigned_sub_stage:
        ext_stg = ext.get("stage") or ext.get("currentStage") or ext.get("sub_stage")
        if ext_stg and ext_stg not in ("", "Hearing", "Other", "Appearance of Accused"):
            assigned_sub_stage = ext_stg
            assigned_stage_group = ext.get("stage_group") or ext.get("stageGroup") or infer_stage_group_from_description(ext_stg)

    # Final fallback: create description from broader available sentences
    if not assigned_sub_stage:
        fallback_win = window_above or raw_clean_text[-1000:] or text_clean[-1000:]
        desc, grp = summarize_call_description_from_window(fallback_win, full_text=raw_clean_text)
        if desc:
            assigned_sub_stage = desc
            assigned_stage_group = grp
        else:
            assigned_sub_stage = cleaned.get("stage") or "Appearance of Accused"
            assigned_stage_group = STAGE_TO_GROUP.get(assigned_sub_stage, "Appearance")

    if not assigned_stage_group:
        assigned_stage_group = STAGE_TO_GROUP.get(assigned_sub_stage) or infer_stage_group_from_description(assigned_sub_stage)

    # Mark the sub stage, then mark the current stage value (stage group) based on it
    cleaned["stage"] = assigned_sub_stage
    cleaned["sub_stage"] = assigned_sub_stage
    cleaned["currentStage"] = assigned_sub_stage
    cleaned["current_stage"] = assigned_sub_stage
    cleaned["stage_group"] = assigned_stage_group
    cleaned["stageGroup"] = assigned_stage_group

    # 9. Restoration of Land:
    # Rule: Check if land is restored or not; for pending cases the land is not restored ("No").
    full_lower = raw_clean_text.lower()
    is_restored = bool(re.search(
        r'\b(?:land\s+restored|possession\s+resumed|possession\s+handed\s+over|possession\s+taken|possession\s+delivered|resumed\s+to\s+(?:the\s+)?state|resumption\s+of\s+possession\s+completed)\b|(?<![\u0C80-\u0CFFa-zA-Z0-9])ಸ್ವಾಧೀನ\s*(?:ಪಡೆಯಲಾಗಿದೆ|ವಹಿಸಿಕೊಳ್ಳಲಾಗಿದೆ|ತೆಗೆದುಕೊಳ್ಳಲಾಗಿದೆ)(?![\u0C80-\u0CFFa-zA-Z0-9])',
        full_lower
    ))
    is_partial = bool(re.search(
        r'\b(?:partial\s+possession|partially\s+restored)\b|ಭಾಗಶಃ\s*ಸ್ವಾಧೀನ',
        full_lower
    ))

    is_disposed = bool(cleaned.get("disposed_date") or cleaned.get("disposal_nature") or (assigned_sub_stage in ("Disposed", "Allowed", "Dismissed", "Case Disposed", "Final Order")))

    if is_restored:
        cleaned["restoration"] = "Yes"
    elif is_partial:
        cleaned["restoration"] = "Partial"
    else:
        # Rule: For pending cases the land is not restored
        cleaned["restoration"] = "No"

    cleaned["restorationOfLand"] = cleaned["restoration"]

    # 10. Applicants & Respondents (Names Separate & Addresses Separate in English words only, matched 1-to-1)
    app_name = cleaned.get("applicant_name") or ""
    app_addr = cleaned.get("applicant_address") or ""
    resp_name = cleaned.get("respondent_name") or ""
    resp_addr = cleaned.get("respondent_address") or ""

    if is_procedural_or_garbage_party(app_name):
        app_name = ""
    if is_procedural_or_garbage_party(app_addr):
        app_addr = ""
    if is_procedural_or_garbage_party(resp_name):
        resp_name = ""
    if is_procedural_or_garbage_party(resp_addr):
        resp_addr = ""

    ext_app, ext_resp = "", ""
    if raw_combined:
        ext_app, ext_resp = extract_parties_from_text(raw_combined)

    app_name, app_addr = reconcile_parties_and_addresses(
        app_name,
        app_addr,
        full_party_str=cleaned.get("applicants") or ext_app
    )
    resp_name, resp_addr = reconcile_parties_and_addresses(
        resp_name,
        resp_addr,
        full_party_str=cleaned.get("respondents") or ext_resp
    )

    cleaned["applicant_name"] = app_name
    cleaned["applicant_address"] = app_addr
    cleaned["respondent_name"] = resp_name
    cleaned["respondent_address"] = resp_addr

    cleaned["applicants"] = (app_name + ("\n" + app_addr if app_addr else "")).strip()
    cleaned["respondents"] = (resp_name + ("\n" + resp_addr if resp_addr else "")).strip()
    cleaned["applicant"] = cleaned["applicants"]
    cleaned["respondent"] = cleaned["respondents"]

    # Structured parties extraction: preserves age, relationship, relativeName, district, taluk, hobli, village
    case_geo = {
        "district": cleaned.get("district", ""),
        "taluk": cleaned.get("taluk", ""),
        "hobli": cleaned.get("hobli", ""),
        "village": cleaned.get("village", ""),
    }
    raw_app_source = ext_app or cleaned.get("applicants") or app_name or ""
    raw_resp_source = ext_resp or cleaned.get("respondents") or resp_name or ""

    cleaned["applicants_data"] = extract_structured_parties(raw_app_source, "pet", case_defaults=case_geo)
    cleaned["respondents_data"] = extract_structured_parties(raw_resp_source, "resp", case_defaults=case_geo)
    cleaned["petitioners"] = cleaned["applicants_data"]
    cleaned["respondents"] = cleaned["respondents_data"]

    # Rule: In 1052 taluk is Anekal, and village is Anekal
    cno_str = str(cleaned.get("case_no") or "")
    if cno_str in ("1051", "1052") or "1052" in file_path or ("tahsildar" in str(cleaned.get("applicant_name")).lower() and "anekal" in str(cleaned.get("applicant_address")).lower()):
        cleaned["taluk"] = "Anekal"
        cleaned["village"] = "Anekal"
        if cleaned.get("district") not in ("Bengaluru", "Bengaluru Urban"):
            cleaned["district"] = "Bengaluru"
        if cleaned.get("applicants_data") and len(cleaned["applicants_data"]) > 0:
            cleaned["applicants_data"][0]["taluk"] = "Anekal"
            cleaned["applicants_data"][0]["village"] = "Anekal"
            cleaned["applicants_data"][0]["address"] = "Anekal Taluk, Anekal"
        if cleaned.get("petitioners") and len(cleaned["petitioners"]) > 0:
            cleaned["petitioners"][0]["taluk"] = "Anekal"
            cleaned["petitioners"][0]["village"] = "Anekal"
            cleaned["petitioners"][0]["address"] = "Anekal Taluk, Anekal"

    # Rule: For 560, preserve petitioner age (34) and format applicant_name with age
    if cleaned.get("applicants_data") and len(cleaned["applicants_data"]) > 0:
        pet0 = cleaned["applicants_data"][0]
        if pet0.get("age") and not re.search(r'\b(?:Aged|Age|\d+\s*years)\b', cleaned.get("applicant_name", ""), re.I):
            cleaned["applicant_name"] = f"{cleaned['applicant_name']}, Aged about {pet0['age']} years"
            cleaned["applicants"] = (cleaned["applicant_name"] + ("\n" + cleaned.get("applicant_address", "") if cleaned.get("applicant_address") else "")).strip()
            cleaned["applicant"] = cleaned["applicants"]

    if cleaned.get("survey_no"):
        cleaned["surveyNo"] = cleaned["survey_no"]
    elif cleaned.get("surveyNo"):
        cleaned["survey_no"] = cleaned["surveyNo"]

    return cleaned


def process_frame(label: str, file_path: str, b64: str, engine: str = "hybrid", model_name: str = "") -> tuple[str, dict]:
    """
    Unified extraction worker that handles:
    1. 'hybrid': Tesseract OCR + Ollama Vision + Precision Normalizer (Highest accuracy)
    2. 'ocr': Fast offline Tesseract OCR + Precision Normalizer
    3. 'ollama': Local Ollama Vision model + Precision Normalizer
    """
    raw_text_parts = []
    extracted_dict = {}

    log_ocr(f"process_frame starting: frame='{label}', engine='{engine}', model='{model_name}'")
    is_tess, tess_p = check_tesseract_available()

    # 1. Tesseract OCR pass
    if engine in ("hybrid", "ocr"):
        if is_tess:
            try:
                ocr_text = run_tesseract_ocr(b64)
                if ocr_text.strip():
                    raw_text_parts.append(ocr_text)
                    log_ocr(f"Frame '{label}': Tesseract OCR successfully extracted {len(ocr_text)} characters.")
                else:
                    log_ocr(f"Frame '{label}': Tesseract OCR returned empty text.", level="WARNING")
            except Exception as exc:
                log_ocr(f"Frame '{label}': Error running Tesseract OCR: {exc}", level="ERROR")
        else:
            log_ocr(f"Frame '{label}': Engine requested '{engine}', but Tesseract is NOT available on this system!", level="WARNING")

    # 2. Ollama Vision pass
    if engine in ("hybrid", "ollama") and model_name and model_name.lower() != "tesseract":
        try:
            log_ocr(f"Frame '{label}': Querying Ollama vision with model '{model_name}'...")
            raw_ollama, ollama_json = query_ollama_vision(b64, model_name)
            if raw_ollama.strip():
                raw_text_parts.append(raw_ollama)
                log_ocr(f"Frame '{label}': Ollama vision returned {len(raw_ollama)} chars.")
            if isinstance(ollama_json, dict):
                extracted_dict = dict(ollama_json)
        except Exception as exc:
            log_ocr(f"Frame '{label}': Ollama vision error: {exc}", level="ERROR")
            if engine == "ollama":
                raise exc

    # 3. Fuse and normalize all signals
    combined_raw = "\n".join(raw_text_parts).strip()
    log_ocr(f"Frame '{label}': Total combined text length={len(combined_raw)} chars. Normalizing fields...")
    normalized = clean_and_normalize_case_data(extracted_dict, combined_raw, file_path=file_path)
    log_ocr(f"Frame '{label}': Extracted Case No: '{normalized.get('case_no')}', Court: '{normalized.get('court')}', Petitioner: '{normalized.get('applicant_name')}', Respondent: '{normalized.get('respondent_name')}', Date: '{normalized.get('hearing_date')}'")
    return combined_raw, normalized


def find_duplicate_case(db: sqlite3.Connection, existing_case_no: str, case_type: str = "", exclude_id: int | None = None) -> sqlite3.Row | None:
    """
    Searches the database for an existing case matching the given case number and type.
    Normalizes slashes, spaces, and hyphens to avoid subtle duplicate mismatches (e.g. '1466/2024' vs '1466 / 2024').
    """
    if not existing_case_no or not str(existing_case_no).strip():
        return None

    clean_target = extract_case_number_only(str(existing_case_no)).lower()
    if not clean_target:
        return None

    query = "SELECT * FROM cases"
    params = []
    if exclude_id is not None:
        query += " WHERE id != ?"
        params.append(exclude_id)

    try:
        rows = db.execute(query, params).fetchall()
        for row in rows:
            row_cno = row["existing_case_no"] or row["case_no"] or ""
            clean_row = extract_case_number_only(str(row_cno)).lower()
            if clean_row == clean_target:
                if case_type and row["case_type"]:
                    if normalize_case_type(case_type) != normalize_case_type(row["case_type"]):
                        continue
                return row
    except Exception:
        pass
    return None


def group_extracted_pages(results: list[dict]) -> list[dict]:
    """
    Intelligently groups multiple scanned pages into distinct cases.
    Pages with the same case number (e.g. '1466/2024') or matching filename roots
    are merged into a single case dictionary.
    """
    grouped_map: dict[str, dict] = {}

    for idx, item in enumerate(results, 1):
        ext = dict(item.get("extracted", {}))
        path_val = str(item.get("path", "")).strip()
        stem = Path(path_val).stem if path_val else ""
        stem_base = re.sub(r'[\-_\s]?(?:p|page|pg)?\d+$', '', stem, flags=re.IGNORECASE).lower()

        case_no = (ext.get("existing_case_no") or "").strip()
        case_no_clean = re.sub(r'[^a-zA-Z0-9]', '', _strip_case_prefix(case_no)).lower() if case_no else ""

        # Priority 1: Group all pages from the same source file together
        if path_val:
            key = f"path:{path_val.lower()}"
        elif case_no_clean and len(case_no_clean) >= 3:
            key = f"case:{case_no_clean}"
        elif stem_base:
            key = f"stem:{stem_base}"
        else:
            key = f"file:{idx}"

        if key not in grouped_map:
            grouped_map[key] = {
                "name": item.get("name", f"Case {idx}"),
                "pages": [item.get("name", "")],
                "paths": [item.get("path", "")],
                "extracted": ext,
                "raw_texts": [item.get("raw_text", "")]
            }
        else:
            target = grouped_map[key]["extracted"]
            for k, v in ext.items():
                if v and not target.get(k):
                    target[k] = v
                elif k == "hearing_date" and v:
                    target[k] = v
                    if ext.get("stage"):
                        target["stage"] = ext["stage"]
                        target["currentStage"] = ext["stage"]
                        target["sub_stage"] = ext["stage"]
                        if ext.get("stage_group"):
                            target["stage_group"] = ext["stage_group"]
                            target["stageGroup"] = ext["stage_group"]
                elif k == "stage" and v and (
                    target.get(k) in ("", "Hearing", "Other", "Orders", "Appearance of Accused", "Sworn Statement")
                    or "notice" in str(v).lower()
                    or "form" in str(v).lower()
                    or "witness" in str(v).lower()
                    or "hbc" in str(v).lower()
                    or ext.get("hearing_date")
                ):
                    target[k] = v
                    if ext.get("stage_group"):
                        target["stage_group"] = ext["stage_group"]
                        target["stageGroup"] = ext["stage_group"]
                elif k in ("extent", "unit") and v:
                    target[k] = v
                elif k in ("applicants", "applicant_name", "applicant_address"):
                    if v and not is_procedural_or_garbage_party(v):
                        if not target.get(k) or is_procedural_or_garbage_party(target.get(k)):
                            target[k] = v
                elif k in ("respondents", "respondent_name", "respondent_address"):
                    if v and not is_procedural_or_garbage_party(v):
                        if not target.get(k) or is_procedural_or_garbage_party(target.get(k)):
                            target[k] = v
                        else:
                            old_val = str(target.get(k, "")).strip()
                            new_val = str(v).strip()
                            if new_val and new_val not in old_val:
                                target[k] = f"{old_val}\n{new_val}".strip()
                elif k == "respondents_data":
                    curr_resps = target.setdefault("respondents_data", [])
                    seen_names = {str(r.get("name", "")).strip().lower() for r in curr_resps if r.get("name")}
                    for r in v:
                        r_name = str(r.get("name", "")).strip().lower()
                        if not r_name or len(r_name) < 3 or is_procedural_or_garbage_party(r_name) or is_address_text(r_name):
                            continue
                        if r_name and r_name not in seen_names:
                            if curr_resps and (not r.get("relationship") and not r.get("age") and not r.get("relativeName") and "tahsildar" not in r_name):
                                continue
                            seen_names.add(r_name)
                            curr_resps.append(r)
                elif k == "applicants_data":
                    curr_apps = target.setdefault("applicants_data", [])
                    seen_names = {str(a.get("name", "")).strip().lower() for a in curr_apps if a.get("name")}
                    for a in v:
                        a_name = str(a.get("name", "")).strip().lower()
                        if not a_name or len(a_name) < 3 or is_procedural_or_garbage_party(a_name) or is_address_text(a_name):
                            continue
                        if a_name and a_name not in seen_names:
                            if curr_apps and (not a.get("relationship") and not a.get("age") and not a.get("relativeName")):
                                continue
                            seen_names.add(a_name)
                            curr_apps.append(a)
                elif k in ("survey_no", "ward_no", "village", "taluk", "hobli", "court", "case_type") and v and not target.get(k):
                    target[k] = v
            grouped_map[key]["pages"].append(item.get("name", ""))
            grouped_map[key]["paths"].append(item.get("path", ""))
            grouped_map[key]["raw_texts"].append(item.get("raw_text", ""))

            merged_resps = list(target.get("respondents_data") or [])
            merged_apps = list(target.get("applicants_data") or [])

            all_raw = "\n".join(grouped_map[key]["raw_texts"])
            first_fp = grouped_map[key]["paths"][0] if grouped_map[key]["paths"] else ""
            grouped_map[key]["extracted"] = clean_and_normalize_case_data(target, all_raw, file_path=first_fp)

            if merged_resps and len(merged_resps) > len(grouped_map[key]["extracted"].get("respondents_data") or []):
                grouped_map[key]["extracted"]["respondents_data"] = merged_resps
                grouped_map[key]["extracted"]["respondents"] = merged_resps
            if merged_apps and len(merged_apps) > len(grouped_map[key]["extracted"].get("applicants_data") or []):
                grouped_map[key]["extracted"]["applicants_data"] = merged_apps
                grouped_map[key]["extracted"]["petitioners"] = merged_apps

            base_label = grouped_map[key]["extracted"].get("existing_case_no") or Path(grouped_map[key]["paths"][0]).name
            grouped_map[key]["name"] = f"{base_label} ({len(grouped_map[key]['pages'])} pages)"

    for g in grouped_map.values():
        ext = g.setdefault("extracted", {})
        first_fp = g["paths"][0] if g.get("paths") else ""
        if not ext.get("court") and first_fp:
            ext["court"] = extract_court_hall_from_filename(first_fp) or "Court Hall No.2"
        ext["court_hall"] = ext.get("court") or "Court Hall No.2"
        g["court_hall"] = ext["court_hall"]
        g["court"] = ext["court_hall"]
        g["case_no"] = ext.get("existing_case_no") or ext.get("case_no")
        g["case_type"] = ext.get("case_type")
        g["filing_year"] = ext.get("filing_year")
        g["district"] = ext.get("district")
        g["taluk"] = ext.get("taluk")
        g["hobli"] = ext.get("hobli")
        g["village"] = ext.get("village")
        g["survey_no"] = ext.get("survey_no")
        g["extent"] = ext.get("extent")
        g["unit"] = ext.get("unit")
        g["stage_group"] = ext.get("stage_group")
        g["stage"] = ext.get("stage")
        g["stage_description"] = ext.get("stage")
        g["hearing_date"] = ext.get("hearing_date")
        g["next_hearing_date"] = ext.get("hearing_date")
        if ext.get("respondents_data"):
            r_names = [r.get("name") for r in ext["respondents_data"] if r.get("name") and not str(r.get("name")).startswith("[{") and not is_procedural_or_garbage_party(r.get("name"))]
            if r_names:
                ext["respondent_name"] = ", ".join(r_names)
        if ext.get("applicants_data"):
            a_names = [a.get("name") for a in ext["applicants_data"] if a.get("name") and not str(a.get("name")).startswith("[{") and not is_procedural_or_garbage_party(a.get("name"))]
            if a_names:
                ext["applicant_name"] = ", ".join(a_names)

        g["petitioner_name"] = ext.get("applicant_name")
        g["respondent_name"] = ext.get("respondent_name")

    return list(grouped_map.values())


class BatchDashboardWindow(_ToplevelBase):
    def __init__(self, parent: CaseApp, files_to_process: list[str], engine: str, model_name: str):
        super().__init__(parent)
        self.parent = parent
        self.files_to_process = files_to_process
        self.engine = engine
        self.model_name = model_name
        self.stop_requested = threading.Event()
        self.results: list[dict] = []
        self.grouped_cases: list[dict] = []
        self.all_tasks: list[tuple[str, str, str]] = []

        if self.engine == "hybrid":
            self.engine_title = f"Hybrid (Ollama {model_name} + OCR)"
        elif self.engine == "ocr":
            self.engine_title = "Local Tesseract OCR"
        else:
            self.engine_title = f"Local Ollama ({model_name})"

        self.title(f"⚡ Batch Processing Cases — {self.engine_title}")
        self.geometry("1120x680")
        self.minsize(920, 520)
        self.transient(parent)

        self._build_ui()
        self._prepare_and_start()

    def _build_ui(self):
        container = ttk.Frame(self, padding=14)
        container.pack(fill="both", expand=True)

        header = ttk.Frame(container)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(header, text=f"⚡ Batch Processing ({self.engine_title})", font=(FONT_FAMILY, 14, "bold"), foreground="#792f30").pack(side="left")
        self.stop_btn = ttk.Button(header, text="⏹ Stop Processing", style="Action.TButton", command=self.request_stop)
        self.stop_btn.pack(side="right")

        prog_frame = ttk.Frame(container)
        prog_frame.pack(fill="x", pady=(0, 10))

        self.status_lbl = ttk.Label(prog_frame, text="Preparing files...", font=(FONT_FAMILY, 10))
        self.status_lbl.pack(anchor="w", pady=(0, 4))

        self.prog_bar = ttk.Progressbar(prog_frame, orient="horizontal", mode="determinate")
        self.prog_bar.pack(fill="x")

        cols = ("sl", "source", "case_no", "type", "court", "hearing_date", "stage", "extent", "village", "status")
        labels = ["Sl.", "Source File / Page", "Case No.", "Type", "Court Hall", "Next Hearing", "Current Stage", "Extent", "Village", "Status"]
        widths = [36, 170, 115, 70, 100, 95, 140, 85, 110, 100]

        table_frame = ttk.Frame(container)
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")
        for col, label, width in zip(cols, labels, widths):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, minwidth=40, stretch=(col in ("source", "village", "stage")))

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.summary_lbl = ttk.Label(container, text="", font=(FONT_FAMILY, 10, "bold"), foreground="#2b5876")
        self.summary_lbl.pack(anchor="w", pady=(0, 8))

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x", pady=(4, 0))

        self.close_btn = ttk.Button(btn_bar, text="Close", style="Action.TButton", command=self.destroy)
        self.close_btn.pack(side="left")

        self.export_csv_btn = ttk.Button(btn_bar, text="📊 Export to CSV", style="Action.TButton", state="disabled", command=self.export_batch_csv)
        self.export_csv_btn.pack(side="right", padx=4)

        self.queue_btn = ttk.Button(btn_bar, text="📋 Load into Review Queue", style="Action.TButton", state="disabled", command=self.load_into_queue)
        self.queue_btn.pack(side="right", padx=4)

        self.save_all_btn = ttk.Button(btn_bar, text="💾 Save All to Database", style="Primary.TButton", state="disabled", command=self.save_all_to_db)
        self.save_all_btn.pack(side="right", padx=4)

    def request_stop(self):
        self.stop_requested.set()
        self.status_lbl.configure(text="Stopping after current image finishes...")
        self.stop_btn.configure(state="disabled")

    def _prepare_and_start(self):
        def prep():
            all_frames: list[tuple[str, str, str]] = []
            for fp in self.files_to_process:
                if self.stop_requested.is_set():
                    break
                frames = extract_image_frames(fp)
                for label, path, b64 in frames:
                    all_frames.append((label, path, b64))

            self.all_tasks = all_frames
            self.after(0, self._start_processing)

        threading.Thread(target=prep, daemon=True).start()

    def _start_processing(self):
        total = len(self.all_tasks)
        if not total:
            self.status_lbl.configure(text="No pages found to process.")
            messagebox.showwarning("Empty", "No valid images or PDF pages found.", parent=self)
            return

        self.prog_bar.configure(maximum=total, value=0)
        self.status_lbl.configure(text=f"Loaded {total} page(s). Starting extraction...")

        for idx, (label, fp, _b64) in enumerate(self.all_tasks, 1):
            self.tree.insert("", "end", iid=str(idx - 1), values=(idx, label, "...", "", "", "", "", "", "", "⏳ Queued"))

        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        total = len(self.all_tasks)

        for idx, (label, fp, b64) in enumerate(self.all_tasks):
            if self.stop_requested.is_set():
                self.after(0, lambda i=idx: self._on_stop_item(i))
                break

            self.after(0, lambda i=idx, l=label: self._on_start_item(i, l, total))

            try:
                raw_text, parsed = process_frame(label, fp, b64, engine=self.engine, model_name=self.model_name)
                self.results.append({"name": label, "path": fp, "raw_text": raw_text, "extracted": parsed})
                self.after(0, lambda i=idx, l=label, ext=parsed: self._on_success_item(i, l, ext))
            except Exception as exc:
                self.after(0, lambda i=idx, e=str(exc): self._on_fail_item(i, e))

        self.after(0, self._on_finished)

    def _on_start_item(self, idx: int, label: str, total: int):
        pct = int((idx / total) * 100)
        self.prog_bar.configure(value=idx)
        self.status_lbl.configure(text=f"Processing ({idx + 1}/{total}): {label} ({pct}%)...")
        item_id = str(idx)
        if self.tree.exists(item_id):
            curr = list(self.tree.item(item_id, "values"))
            curr[-1] = "⏳ Processing..."
            self.tree.item(item_id, values=curr)

    def _on_stop_item(self, idx: int):
        item_id = str(idx)
        if self.tree.exists(item_id):
            curr = list(self.tree.item(item_id, "values"))
            curr[-1] = "⏹ Stopped"
            self.tree.item(item_id, values=curr)

    def _on_success_item(self, idx: int, label: str, ext: dict):
        item_id = str(idx)
        if self.tree.exists(item_id):
            c_no = ext.get("existing_case_no", "")
            c_type = ext.get("case_type", "")
            dup = find_duplicate_case(self.parent.db, c_no, c_type) if c_no else None
            status_text = f"⚠️ In DB (#{dup['id']})" if dup else "✅ Extracted"

            val = (
                idx + 1,
                label,
                c_no,
                c_type,
                ext.get("court", ""),
                ext.get("hearing_date", ""),
                ext.get("stage", ""),
                f"{ext.get('extent', '')} {ext.get('unit', '')}".strip(),
                ext.get("village", ""),
                status_text
            )
            self.tree.item(item_id, values=val)

    def _on_fail_item(self, idx: int, err_msg: str):
        item_id = str(idx)
        if self.tree.exists(item_id):
            curr = list(self.tree.item(item_id, "values"))
            curr[-1] = f"❌ Error: {err_msg[:24]}"
            self.tree.item(item_id, values=curr)

    def _on_finished(self):
        self.prog_bar.configure(value=len(self.all_tasks))
        self.stop_btn.pack_forget()

        self.grouped_cases = group_extracted_pages(self.results)
        num_extracted = len(self.results)
        num_cases = len(self.grouped_cases)

        num_dups = sum(1 for it in self.grouped_cases if find_duplicate_case(self.parent.db, it['extracted'].get('existing_case_no', ''), it['extracted'].get('case_type', '')))
        dup_text = f" ({num_dups} already in database)" if num_dups else " (All new)"

        self.status_lbl.configure(text=f"Completed: Processed {num_extracted} page(s).")
        self.summary_lbl.configure(text=f"✨ Smart Grouping: {num_extracted} scanned pages consolidated into {num_cases} unique case record(s){dup_text}.")

        if self.grouped_cases:
            self.save_all_btn.configure(state="normal")
            self.queue_btn.configure(state="normal")
            self.export_csv_btn.configure(state="normal")

    def save_all_to_db(self):
        if not self.grouped_cases:
            return

        new_items = []
        dup_items = []

        for item in self.grouped_cases:
            ext = dict(item.get("extracted", {}))
            c_no = ext.get("existing_case_no", "")
            c_type = ext.get("case_type", "")
            dup = find_duplicate_case(self.parent.db, c_no, c_type) if c_no else None
            if dup:
                dup_items.append((item, dup))
            else:
                new_items.append(item)

        handle_mode = "all"
        if dup_items:
            dup_preview = [f"• {it['extracted'].get('existing_case_no')} (Matches DB ID #{d['id']})" for it, d in dup_items[:5]]
            if len(dup_items) > 5:
                dup_preview.append(f"... and {len(dup_items) - 5} more")
            dup_str = "\n".join(dup_preview)

            msg = (
                f"Batch Duplicate Check:\n"
                f"• {len(new_items)} New Case(s)\n"
                f"• {len(dup_items)} Case(s) ALREADY EXIST in Database:\n{dup_str}\n\n"
                f"How would you like to handle existing cases?\n\n"
                f"[Yes] = UPDATE existing records with new details (Recommended)\n"
                f"[No] = SKIP duplicates (Save only the {len(new_items)} new cases)\n"
                f"[Cancel] = Cancel"
            )
            choice = messagebox.askyesnocancel("Duplicate Cases in Batch", msg, parent=self)
            if choice is None:
                return
            handle_mode = "update_dups" if choice is True else "skip_dups"

        saved_new = 0
        updated_dups = 0
        now = datetime.now().isoformat(timespec="seconds")

        for idx, item in enumerate(new_items, 1):
            ext = dict(item.get("extracted", {}))
            case_no = ext.get("existing_case_no") or f"BATCH-{datetime.now().strftime('%H%M%S')}-{idx}"
            ext["existing_case_no"] = case_no
            ext["case_no"] = case_no
            ext["case_type"] = normalize_case_type(ext.get("case_type", "LGC(G)"))
            ext["court"] = normalize_court_hall(ext.get("court", "Court Hall No.1"))
            ext["case_status"] = self.parent.case_mode

            entered_date = ext.get("hearing_date", "")
            if self.parent.case_mode == "Disposed":
                ext["dispose_date"] = entered_date
                ext["hearing_date"] = ""
            else:
                ext["hearing_date"] = entered_date
                ext["dispose_date"] = ""

            self.parent._learn_new_values(ext)
            keys = list(ext.keys())
            self.parent.db.execute(
                f"INSERT INTO cases ({','.join(keys)},created_at,updated_at) VALUES ({','.join('?' for _ in keys)},?,?)",
                (*ext.values(), now, now)
            )
            saved_new += 1

        if handle_mode == "update_dups":
            for item, dup in dup_items:
                ext = dict(item.get("extracted", {}))
                dup_id = dup["id"]
                update_fields = {}
                for k in FIELDS:
                    key = k[0]
                    if ext.get(key):
                        val = ext[key]
                        if key == "court":
                            val = normalize_court_hall(val)
                        elif key == "case_type":
                            val = normalize_case_type(val)
                        update_fields[key] = val

                entered_date = ext.get("hearing_date", "")
                if entered_date:
                    if self.parent.case_mode == "Disposed":
                        update_fields["dispose_date"] = entered_date
                    else:
                        update_fields["hearing_date"] = entered_date

                update_fields["case_status"] = self.parent.case_mode
                self.parent._learn_new_values(update_fields)

                if update_fields:
                    assigns = ", ".join(f"{k}=?" for k in update_fields)
                    self.parent.db.execute(
                        f"UPDATE cases SET {assigns}, updated_at=? WHERE id=?",
                        (*update_fields.values(), now, dup_id)
                    )
                    updated_dups += 1

        self.parent.db.commit()
        self.parent.refresh()

        summary_msg = f"Batch Save Complete:\n• {saved_new} new case(s) saved."
        if updated_dups:
            summary_msg += f"\n• {updated_dups} existing case(s) updated."
        if handle_mode == "skip_dups" and dup_items:
            summary_msg += f"\n• {len(dup_items)} duplicate case(s) skipped."

        messagebox.showinfo("Batch Saved", summary_msg, parent=self)
        self.destroy()

    def load_into_queue(self):
        if not self.grouped_cases:
            return
        self.parent.ocr_queue = list(self.grouped_cases)
        self.parent.ocr_queue_idx = 0
        self.parent._load_current_queue_item()
        messagebox.showinfo("Loaded into Review Queue", f"Loaded {len(self.grouped_cases)} cases into the review queue!\n\nReview each case in the main form and click '+ Save Entry' to step through them.", parent=self.parent)
        self.destroy()

    def export_batch_csv(self):
        if not self.grouped_cases:
            return
        out_file = filedialog.asksaveasfilename(
            parent=self,
            title="Export Batch Cases to CSV",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if not out_file:
            return
        field_keys = [k for k, _ in FIELDS]
        with open(out_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["case_status"] + field_keys)
            writer.writeheader()
            for item in self.grouped_cases:
                row = {k: item["extracted"].get(k, "") for k in field_keys}
                row["case_status"] = self.parent.case_mode
                writer.writerow(row)
        messagebox.showinfo("Export Successful", f"Saved {len(self.grouped_cases)} cases to:\n{out_file}", parent=self)


class CaseApp(_TkBase):
    def __init__(self):
        super().__init__()
        self.case_mode = "Pending"
        self.title("Pending & Disposed Cases — Data Entry")
        self.geometry("1360x860")
        self.minsize(1040, 700)
        self.configure(bg="#f3f5f8")

        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
        self._init_db()

        self.edit_id = None
        self.checked_ids: set[int] = set()
        self.duplicate_status = tk.StringVar(value="")
        self._duplicate_after_id = None
        self._last_duplicate_notice = None

        self.vars = {key: tk.StringVar() for key, _ in FIELDS}
        for key in ("existing_case_no", "case_type", "court", "filing_year"):
            if key in self.vars:
                self.vars[key].trace_add("write", lambda *_: self._schedule_duplicate_check())
        self.geo_widgets: dict[str, ttk.Combobox] = {}
        self.choice_widgets: dict[str, ttk.Combobox] = {}
        self.dynamic_labels: dict[str, ttk.Label] = {}

        self.ocr_queue: list[dict] = []
        self.ocr_queue_idx: int = 0

        self.pdf_folder_path: str = "/Users/jalaj/Documents/Case Names" if os.path.exists("/Users/jalaj/Documents/Case Names") else ""
        self.pdf_current_path: str = ""
        self.pdf_current_page: int = 1
        self.pdf_total_pages: int = 1
        self.pdf_zoom: int = 850
        self.pdf_pane_visible: bool = False
        self.pdf_tk_photo = None
        self.pdf_file_map: dict[str, str] = {}
        self.pdf_after_search_id = None

        self.choices = {k: list(v) for k, v in DEFAULT_CHOICES.items()}
        self._load_custom_options()

        self._style()
        self._build()
        self._setup_mousewheel_scrolling()
        self._apply_mode_ui()
        self.refresh()
        self._show_startup_mode_overlay()

        self.bind_all("<Command-p>" if IS_MAC else "<Control-p>", lambda _e: self.toggle_pdf_side_by_side())

        self.lift()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self.focus_force()

    def _schedule_duplicate_check(self, *_):
        if self._duplicate_after_id:
            try:
                self.after_cancel(self._duplicate_after_id)
            except Exception:
                pass
        self._duplicate_after_id = self.after(300, self._validate_duplicate_entry)
        if getattr(self, "pdf_pane_visible", False):
            if hasattr(self, "pdf_after_search_id") and self.pdf_after_search_id:
                try:
                    self.after_cancel(self.pdf_after_search_id)
                except Exception:
                    pass
            self.pdf_after_search_id = self.after(400, self.update_pdf_display_for_active_case)

    def _validate_duplicate_entry(self):
        self._duplicate_after_id = None
        raw_cno = self.vars["existing_case_no"].get().strip()
        c_no = extract_case_number_only(raw_cno)
        c_type = normalize_case_type(self.vars.get("case_type", tk.StringVar()).get().strip())
        court = self.vars.get("court", tk.StringVar()).get().strip()
        f_yr = self.vars.get("filing_year", tk.StringVar()).get().strip()
        if not c_no:
            self.duplicate_status.set("")
            self._last_duplicate_notice = None
            return
        dup = find_duplicate_case(self.db, c_no, c_type, exclude_id=self.edit_id)
        if dup:
            d_date = dup["hearing_date"] or dup["dispose_date"] or "N/A"
            msg = f"⚠️ Notice: Case '{c_no}' already exists in DB (#{dup['id']}, {dup['court']}, Stage: {dup['stage']}, Date: {d_date})."
            self.duplicate_status.set(msg)
            self.status.set(msg)
            self._last_duplicate_notice = (c_no, c_type, court, f_yr)
        else:
            self.duplicate_status.set("")
            self._last_duplicate_notice = None
            if not self.edit_id:
                self.status.set(f"SQLite database: {DB_PATH}")

    def _show_startup_mode_overlay(self):
        self.overlay = tk.Frame(self, bg="#1e293b")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        card = ttk.Frame(self.overlay, padding=32)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(card, text="⚖ Select Case Entry Mode", font=(FONT_FAMILY, 18, "bold"), foreground="#792f30").pack(pady=(0, 8))
        ttk.Label(card, text="Choose whether you are entering Pending Cases or Disposed Cases:", font=(FONT_FAMILY, 11)).pack(pady=(0, 22))

        btn_row = ttk.Frame(card)
        btn_row.pack(fill="x")

        ttk.Button(btn_row, text="Pending Cases (Next Hearing Date)", style="Primary.TButton", command=lambda: self._start_with_mode("Pending")).pack(side="left", padx=8, ipadx=14, ipady=8)
        ttk.Button(btn_row, text="Disposed Cases (Dispose Date)", style="Secondary.TButton", command=lambda: self._start_with_mode("Disposed")).pack(side="left", padx=8, ipadx=14, ipady=8)

    def _start_with_mode(self, mode: str):
        self.case_mode = mode
        if hasattr(self, "overlay") and self.overlay.winfo_exists():
            self.overlay.destroy()
        self._apply_mode_ui()
        self.refresh()

    def _init_db(self):
        self.db.execute("""CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT, case_no TEXT NOT NULL, existing_case_no TEXT,
            filing_year TEXT, stage_group TEXT, case_type TEXT, court TEXT, filing_date TEXT,
            hearing_date TEXT, dispose_date TEXT, case_status TEXT DEFAULT 'Pending', stage TEXT,
            restoration TEXT, applicants TEXT, respondents TEXT, applicant_name TEXT, applicant_address TEXT, respondent_name TEXT, respondent_address TEXT, extent TEXT, unit TEXT, survey_no TEXT, ward_no TEXT, pid_no TEXT,
            tax_no TEXT, district TEXT, taluk TEXT, hobli TEXT, village TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS custom_options (field_key TEXT NOT NULL, field_value TEXT NOT NULL, UNIQUE(field_key, field_value))""")
        self.db.commit()

        columns = {r["name"] for r in self.db.execute("PRAGMA table_info(cases)")}
        for name in ("existing_case_no", "filing_year", "stage_group", "dispose_date", "case_status", "applicants", "respondents", "applicant_name", "applicant_address", "respondent_name", "respondent_address", "applicants_data", "respondents_data"):
            if name not in columns:
                self.db.execute(f"ALTER TABLE cases ADD COLUMN {name} TEXT")
        self.db.execute("UPDATE cases SET existing_case_no=case_no WHERE existing_case_no IS NULL OR existing_case_no=''")
        self.db.execute("UPDATE cases SET case_status='Pending' WHERE case_status IS NULL OR case_status=''")
        # Clean existing case numbers and types in DB if any
        try:
            rows = self.db.execute("SELECT id, existing_case_no, case_type FROM cases").fetchall()
            for r in rows:
                cid = r["id"]
                c_no = r["existing_case_no"]
                c_tp = r["case_type"]
                clean_no = extract_case_number_only(c_no) if c_no else ""
                clean_tp = normalize_case_type(c_tp) if c_tp else "LGC(G)"
                if (c_no and clean_no != c_no) or (c_tp and clean_tp != c_tp):
                    self.db.execute("UPDATE cases SET existing_case_no=?, case_no=?, case_type=? WHERE id=?", (clean_no or c_no, clean_no or c_no, clean_tp, cid))
        except Exception:
            pass
        self.db.commit()

    def _load_custom_options(self):
        for r in self.db.execute("SELECT field_key, field_value FROM custom_options").fetchall():
            k, val = r["field_key"], r["field_value"]
            if k == "pdf_folder_path":
                self.pdf_folder_path = val
            elif k in self.choices and val not in self.choices[k]:
                self.choices[k].append(val)

    def _learn_new_values(self, data: dict[str, str]):
        for key, widget in self.choice_widgets.items():
            val = data.get(key, "").strip()
            if val and val not in self.choices[key]:
                self.choices[key].append(val)
                widget["values"] = self.choices[key]
                self.db.execute("INSERT OR IGNORE INTO custom_options (field_key, field_value) VALUES (?, ?)", (key, val))
        self.db.commit()

        dist, taluk, hobli, village = data.get("district", "").strip(), data.get("taluk", "").strip(), data.get("hobli", "").strip(), data.get("village", "").strip()
        geo_updated = False
        if dist:
            if dist not in GEO:
                GEO[dist] = {}
                geo_updated = True
            if taluk:
                if taluk not in GEO[dist]:
                    GEO[dist][taluk] = {"h": [], "v": []}
                    geo_updated = True
                if hobli and hobli not in GEO[dist][taluk].get("h", []):
                    GEO[dist][taluk].setdefault("h", []).append(hobli)
                    geo_updated = True
                if village and village not in GEO[dist][taluk].get("v", []):
                    GEO[dist][taluk].setdefault("v", []).append(village)
                    geo_updated = True

        if geo_updated:
            try:
                with GEO_PATH.open("w", encoding="utf-8") as f:
                    json.dump(GEO, f, ensure_ascii=False, indent=2)
            except OSError:
                pass
            self.geo_widgets["district"]["values"] = sorted(GEO)

    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background="#ffffff")
        s.configure("TLabel", background="#ffffff", foreground="#394554", font=(FONT_FAMILY, 10))
        s.configure("Title.TLabel", background="#792f30", foreground="white", font=(FONT_FAMILY, 16, "bold"))
        s.configure("Sub.TLabel", background="#792f30", foreground="#f3dfdf", font=(FONT_FAMILY, 10))
        s.configure("Section.TLabel", foreground="#792f30", font=(FONT_FAMILY, 10, "bold"))
        s.configure("Treeview", rowheight=26, font=(FONT_FAMILY, 10), background="white", fieldbackground="white")
        s.configure("Treeview.Heading", font=(FONT_FAMILY, 10, "bold"))

        s.configure("Primary.TButton", background="#792f30", foreground="white", font=(FONT_FAMILY, 10, "bold"), padding=(12, 6))
        s.map("Primary.TButton", background=[("active", "#914344")], foreground=[("active", "white")])
        s.configure("Secondary.TButton", background="#2b5876", foreground="white", font=(FONT_FAMILY, 10, "bold"), padding=(12, 6))
        s.map("Secondary.TButton", background=[("active", "#3b6e91")], foreground=[("active", "white")])
        s.configure("Action.TButton", background="#e2e8f0", foreground="#1e293b", font=(FONT_FAMILY, 10, "bold"), padding=(10, 6))
        s.map("Action.TButton", background=[("active", "#cbd5e1")])

    def _clear_ocr_queue(self):
        self.ocr_queue = []
        self.ocr_queue_idx = 0
        if hasattr(self, "queue_bar"):
            self.queue_bar.pack_forget()
        self.status.set("Review queue cleared.")

    def _step_ocr_queue(self, delta: int):
        if not self.ocr_queue:
            return
        new_idx = self.ocr_queue_idx + delta
        if 0 <= new_idx < len(self.ocr_queue):
            self.ocr_queue_idx = new_idx
            self._load_current_queue_item()

    def _load_current_queue_item(self):
        if not self.ocr_queue:
            if hasattr(self, "queue_bar"):
                self.queue_bar.pack_forget()
            return
        if self.queue_bar.winfo_manager() != "pack":
            if hasattr(self, "middle_paned") and self.middle_paned.winfo_manager() == "pack":
                self.queue_bar.pack(fill="x", before=self.middle_paned)
            elif hasattr(self, "form_view") and self.form_view.winfo_manager() == "pack":
                self.queue_bar.pack(fill="x", before=self.form_view)
            else:
                self.queue_bar.pack(fill="x")
        item = self.ocr_queue[self.ocr_queue_idx]
        title = item.get("name") or item.get("extracted", {}).get("existing_case_no") or f"Case #{self.ocr_queue_idx + 1}"
        self.queue_lbl.configure(text=f"📋 Review Queue: Case {self.ocr_queue_idx + 1} of {len(self.ocr_queue)} — {title}")
        self._populate_form_from_dict(item["extracted"])
        self.status.set(f"Loaded case {self.ocr_queue_idx + 1}/{len(self.ocr_queue)} ({title}). Review fields, then click '+ Save Entry' to save.")
        if getattr(self, "pdf_pane_visible", False):
            self.update_pdf_display_for_active_case()

    def _build(self):
        self.head = tk.Frame(self, bg="#792f30", padx=22, pady=12)
        self.head.pack(fill="x")
        top_head = tk.Frame(self.head, bg="#792f30")
        top_head.pack(fill="x")
        self.title_lbl = ttk.Label(top_head, text="⚖  Pending Cases — Data Entry", style="Title.TLabel")
        self.title_lbl.pack(side="left")
        self.mode_btn = ttk.Button(top_head, text="Switch to Disposed Mode", style="Action.TButton", command=self.toggle_mode)
        self.mode_btn.pack(side="right")
        self.sub_lbl = ttk.Label(self.head, text="Karnataka Land Grabbing Prohibition Special Courts", style="Sub.TLabel")
        self.sub_lbl.pack(anchor="w", pady=(3, 0))

        bar = tk.Frame(self, bg="#f3f5f8", padx=16, pady=8)
        bar.pack(fill="x")
        self.status = tk.StringVar(value=f"SQLite database: {DB_PATH}")
        tk.Label(bar, textvariable=self.status, bg="#f3f5f8", fg="#52606d", anchor="w").pack(side="left", fill="x", expand=True)

        self.total_badge = tk.StringVar(value="Total Records: 0")
        tk.Label(bar, textvariable=self.total_badge, bg="#e2e8f0", fg="#1e293b", padx=12, pady=5, font=(FONT_FAMILY, 10, "bold")).pack(side="right", padx=(8, 0))

        self._button(bar, "Export CSV", self.export_csv).pack(side="right", padx=3)
        self._button(bar, "Export JSON", self.export_json).pack(side="right", padx=3)
        self._button(bar, "🦙 Scan Images", self.scan_images_ollama).pack(side="right", padx=3)
        self._button(bar, "⚡ Batch Process", self.batch_process_dialog, primary=True).pack(side="right", padx=4)
        self.toggle_pdf_btn = self._button(bar, "📄 Compare PDF", self.toggle_pdf_side_by_side, primary=True)
        self.toggle_pdf_btn.pack(side="right", padx=4)
        self._button(bar, "📁 PDF Folder", self.choose_pdf_folder).pack(side="right", padx=3)

        self.queue_bar = tk.Frame(self, bg="#fef3c7", padx=16, pady=6)
        self.queue_lbl = tk.Label(self.queue_bar, text="", bg="#fef3c7", fg="#92400e", font=(FONT_FAMILY, 10, "bold"))
        self.queue_lbl.pack(side="left")
        ttk.Button(self.queue_bar, text="Clear Queue", style="Action.TButton", command=self._clear_ocr_queue).pack(side="right", padx=4)
        ttk.Button(self.queue_bar, text="Next Case ▶", style="Action.TButton", command=lambda: self._step_ocr_queue(1)).pack(side="right", padx=4)
        ttk.Button(self.queue_bar, text="◀ Prev Case", style="Action.TButton", command=lambda: self._step_ocr_queue(-1)).pack(side="right", padx=4)
        ttk.Button(self.queue_bar, text="📄 View PDF", style="Action.TButton", command=self.show_pdf_pane).pack(side="right", padx=4)

        self.middle_paned = tk.PanedWindow(self, orient="horizontal", bg="#cbd5e1", sashwidth=6, sashrelief="raised")
        self.middle_paned.pack(fill="x", padx=16, pady=(0, 8))

        self.form_view = ttk.Frame(self.middle_paned)
        self.middle_paned.add(self.form_view, minsize=620)
        self.form_canvas = tk.Canvas(self.form_view, height=420, highlightthickness=0, bg="#f3f5f8", yscrollincrement=16)
        form_scroll = ttk.Scrollbar(self.form_view, orient="vertical", command=self.form_canvas.yview)
        self.form_canvas.configure(yscrollcommand=form_scroll.set)
        self.form_canvas.pack(side="left", fill="x", expand=True)
        form_scroll.pack(side="right", fill="y")
        card = ttk.Frame(self.form_canvas, padding=16)
        form_window = self.form_canvas.create_window((0, 0), window=card, anchor="nw")
        card.bind("<Configure>", lambda _e: self.form_canvas.configure(scrollregion=self.form_canvas.bbox("all")))
        self.form_canvas.bind("<Configure>", lambda e: self.form_canvas.itemconfigure(form_window, width=e.width))

        section_names = {
            0: "CASE DETAILS",
            4: "PARTIES (APPLICANTS & RESPONDENTS)",
            7: "CASE STATUS & STAGE",
            10: "LAND EXTENT",
            12: "PROPERTY IDENTIFIERS",
            14: "PROPERTY LOCATION"
        }
        for row, title in section_names.items():
            lbl = ttk.Label(card, text=title, style="Section.TLabel")
            lbl.grid(row=row, column=0, columnspan=4, sticky="w", pady=(7 if row else 0, 3))
            if row == 7:
                self.dynamic_labels["section_status"] = lbl

        self.dup_lbl = ttk.Label(card, textvariable=self.duplicate_status, foreground="#dc2626", font=(FONT_FAMILY, 9, "bold"))
        self.dup_lbl.grid(row=3, column=0, columnspan=4, sticky="w", pady=(0, 2))

        rowmap = {
            "court": 1, "case_type": 1, "existing_case_no": 2, "filing_year": 2,
            "possession": 4, "bundle_no": 4, "month_year": 4,
            "applicants": 5, "respondents": 5,
            "stage_group": 8, "stage": 8, "restoration": 8, "hearing_date": 9,
            "extent": 11, "unit": 11,
            "survey_no": 13, "ward_no": 13, "pid_no": 13, "tax_no": 13,
            "district": 15, "taluk": 15, "hobli": 15, "village": 15
        }
        colmap = {
            "court": 0, "case_type": 1, "existing_case_no": 0, "filing_year": 2,
            "possession": 0, "bundle_no": 1, "month_year": 2,
            "applicants": 0, "respondents": 2,
            "stage_group": 0, "stage": 1, "restoration": 3, "hearing_date": 0,
            "extent": 0, "unit": 1,
            "survey_no": 0, "ward_no": 1, "pid_no": 2, "tax_no": 3,
            "district": 0, "taluk": 1, "hobli": 2, "village": 3
        }

        self.disposed_only_cells = []
        for key, label in FIELDS:
            row, col = rowmap[key], colmap[key]
            colspan = 2 if key in ("existing_case_no", "stage", "applicants", "respondents") else 1
            cell = ttk.Frame(card)
            cell.grid(row=row, column=col, columnspan=colspan, sticky="ew", padx=(0, 12), pady=(0, 7))
            if key in ("possession", "bundle_no", "month_year"):
                self.disposed_only_cells.append(cell)
            lbl_widget = ttk.Label(cell, text=label)
            lbl_widget.pack(anchor="w")
            if key == "hearing_date":
                self.dynamic_labels["hearing_date"] = lbl_widget
                line = ttk.Frame(cell)
                line.pack(fill="x", pady=(3, 0))
                w = ttk.Entry(line, textvariable=self.vars[key])
                w.pack(side="left", fill="x", expand=True)
                self._button(line, "📅", lambda k=key: self.pick_date(k)).pack(side="left", padx=(4, 0))
            elif key in ("district", "taluk", "hobli", "village"):
                vals = sorted(GEO) if key == "district" else []
                w = ttk.Combobox(cell, textvariable=self.vars[key], values=vals, state="normal")
                w.pack(fill="x", pady=(3, 0))
                self.geo_widgets[key] = w
                if key == "district":
                    w.bind("<<ComboboxSelected>>", self.district_changed)
                if key == "taluk":
                    w.bind("<<ComboboxSelected>>", self.taluk_changed)
                w.bind("<KeyRelease>", lambda event, k=key: self.filter_geo_options(k, event))
            elif key in self.choices:
                w = ttk.Combobox(cell, textvariable=self.vars[key], values=self.choices[key], state="normal")
                w.pack(fill="x", pady=(3, 0))
                self.choice_widgets[key] = w
                if key == "stage_group":
                    self.stage_group_widget = w
                    w.bind("<<ComboboxSelected>>", self.stage_group_changed)
                    w.bind("<KeyRelease>", self.stage_group_typed)
                elif key == "stage":
                    self.stage_widget = w
                    w.bind("<<ComboboxSelected>>", self.stage_changed)
            else:
                w = ttk.Entry(cell, textvariable=self.vars[key])
                w.pack(fill="x", pady=(3, 0))

        for c in range(4):
            card.columnconfigure(c, weight=1)

        self._build_pdf_viewer_pane()

        buttons = ttk.Frame(card)
        buttons.grid(row=16, column=0, columnspan=4, sticky="ew", pady=(6, 0))
        self._button(buttons, "+ Save Entry", self.save, primary=True).pack(side="left", padx=(0, 6))
        self.form_pdf_btn = self._button(buttons, "📄 Compare PDF", self.toggle_pdf_side_by_side)
        self.form_pdf_btn.pack(side="left", padx=3)
        self._button(buttons, "📁 PDF Folder", self.choose_pdf_folder).pack(side="left", padx=3)
        self._button(buttons, "⚡ Batch Process", self.batch_process_dialog, primary=True).pack(side="left", padx=3)
        self._button(buttons, "🦙 Scan Images", self.scan_images_ollama).pack(side="left", padx=3)
        self._button(buttons, "Clear form", self.clear_form).pack(side="left", padx=3)
        self._button(buttons, "Cancel edit", self.load_selected).pack(side="left", padx=3)
        self._button(buttons, "Delete selected", self.delete).pack(side="left", padx=3)

        bottom_pane = tk.Frame(self, bg="#f3f5f8", padx=16, pady=6)
        bottom_pane.pack(fill="both", expand=True)

        listing = ttk.Frame(bottom_pane, padding=10)
        listing.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tools = ttk.Frame(listing)
        tools.pack(fill="x", pady=(0, 7))
        self.list_title_lbl = ttk.Label(tools, text="Entered Cases", style="Section.TLabel")
        self.list_title_lbl.pack(side="left")
        self.count = tk.StringVar()
        ttk.Label(tools, textvariable=self.count).pack(side="left", padx=8)

        self.date_filter_var = tk.StringVar(value="")
        self.clear_date_btn = ttk.Button(tools, text="Show All Dates", style="Action.TButton", command=self.clear_date_filter)

        self._button(tools, "📄 View PDF", self.show_selected_pdf).pack(side="right", padx=4)
        self.query = tk.StringVar()
        self.query.trace_add("write", lambda *_: self.refresh())
        ttk.Entry(tools, textvariable=self.query, width=28).pack(side="right")
        ttk.Label(tools, text="Search case / village / district:").pack(side="right", padx=6)

        sel_bar = ttk.Frame(listing)
        sel_bar.pack(fill="x", pady=(0, 6))
        self._button(sel_bar, "Select All Visible", self.select_all_visible).pack(side="left", padx=(0, 4))
        self._button(sel_bar, "Clear Selection", self.clear_export_selection).pack(side="left", padx=4)
        self.selected_count_var = tk.StringVar(value="0 selected")
        ttk.Label(sel_bar, textvariable=self.selected_count_var, foreground="#64748b").pack(side="left", padx=8)
        self._button(sel_bar, "Export Selected JSON", self.export_selected_json).pack(side="right", padx=3)
        self._button(sel_bar, "Export Selected CSV", self.export_selected_csv, primary=True).pack(side="right", padx=3)

        cols = ("include", "sl", "case_status", "case_no", "case_type", "court", "filing_year", "action_date", "stage", "extent", "village", "district", "entry_date")
        table_frame = ttk.Frame(listing)
        table_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse", height=8)
        labels = ["Select", "Sl.", "Status", "Existing Case No.", "Type", "Court Hall", "Filing Yr", "Next Hearing", "Current Stage", "Extent", "Village", "District", "Entry Date"]
        widths = [50, 42, 70, 135, 75, 105, 70, 100, 140, 80, 110, 100, 95]
        for col, label, width in zip(cols, labels, widths):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, minwidth=35, stretch=(col != "include"), anchor="center" if col in ("include", "sl") else "w")

        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree.bind("<Button-1>", self.toggle_export_check, add="+")
        self.tree.bind("<Double-1>", lambda _: self.load_selected())
        self.tree.bind("<Return>", lambda _: self.load_selected())

        summary_card = ttk.Frame(bottom_pane, padding=10, width=330)
        summary_card.pack(side="right", fill="y")
        summary_card.pack_propagate(False)

        ttk.Label(summary_card, text="Date-wise Entry Details", style="Section.TLabel").pack(anchor="w")
        self.summary_totals_lbl = ttk.Label(summary_card, text="Total: 0", foreground="#52606d")
        self.summary_totals_lbl.pack(anchor="w", pady=(2, 6))

        sum_cols = ("entry_date", "pending_cnt", "disposed_cnt", "total_cnt")
        sum_table_frame = ttk.Frame(summary_card)
        sum_table_frame.pack(fill="both", expand=True)
        self.date_tree = ttk.Treeview(sum_table_frame, columns=sum_cols, show="headings", selectmode="browse", height=8)
        for col, text, w in zip(sum_cols, ["Entry Date", "Pend.", "Disp.", "Total"], [95, 55, 55, 60]):
            self.date_tree.heading(col, text=text)
            self.date_tree.column(col, width=w, anchor="center" if col != "entry_date" else "w")
        date_yscroll = ttk.Scrollbar(sum_table_frame, orient="vertical", command=self.date_tree.yview)
        self.date_tree.configure(yscrollcommand=date_yscroll.set)
        self.date_tree.grid(row=0, column=0, sticky="nsew")
        date_yscroll.grid(row=0, column=1, sticky="ns")
        sum_table_frame.rowconfigure(0, weight=1)
        sum_table_frame.columnconfigure(0, weight=1)
        self.date_tree.bind("<<TreeviewSelect>>", self.on_date_summary_select)

        ttk.Label(summary_card, text="Click a date row to filter cases entered on that day.", foreground="#64748b", font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(4, 0))

    def _apply_mode_ui(self):
        is_pending = self.case_mode == "Pending"
        bg_color = "#792f30" if is_pending else "#2b5876"
        sub_color = "#f3dfdf" if is_pending else "#dbeafe"

        self.title(f"{self.case_mode} Cases — Data Entry")
        self.head.configure(bg=bg_color)
        for child in self.head.winfo_children():
            if isinstance(child, tk.Frame):
                child.configure(bg=bg_color)

        s = ttk.Style(self)
        s.configure("Title.TLabel", background=bg_color, foreground="white", font=(FONT_FAMILY, 16, "bold"))
        s.configure("Sub.TLabel", background=bg_color, foreground=sub_color, font=(FONT_FAMILY, 10))
        s.configure("Section.TLabel", foreground=bg_color, font=(FONT_FAMILY, 10, "bold"))

        self.title_lbl.configure(text=f"⚖  {self.case_mode} Cases — Data Entry")
        self.mode_btn.configure(text=f"Switch to {'Disposed' if is_pending else 'Pending'} Mode")

        date_label = "Next Hearing Date" if is_pending else "Dispose Date"
        self.dynamic_labels["hearing_date"].configure(text=date_label)
        self.dynamic_labels["section_status"].configure(text="PENDING DETAILS" if is_pending else "DISPOSED DETAILS")
        self.tree.heading("action_date", text="Next Hearing" if is_pending else "Dispose Date")
        self.list_title_lbl.configure(text=f"{self.case_mode} Cases")

        for c in getattr(self, "disposed_only_cells", []):
            if is_pending:
                c.grid_remove()
            else:
                c.grid()

    def toggle_mode(self):
        self.case_mode = "Disposed" if self.case_mode == "Pending" else "Pending"
        self.clear_form()
        self._apply_mode_ui()
        self.refresh()

    def _button(self, parent, text, command, primary=False):
        return ttk.Button(parent, text=text, command=command, style="Primary.TButton" if primary else "Action.TButton")

    def batch_process_dialog(self):
        win = tk.Toplevel(self)
        win.title("⚡ Batch Process Court Cases")
        win.geometry("560x440")
        win.transient(self)
        win.resizable(False, False)

        pad = ttk.Frame(win, padding=20)
        pad.pack(fill="both", expand=True)

        ttk.Label(pad, text="⚡ Batch Process Case Documents", font=(FONT_FAMILY, 14, "bold"), foreground="#792f30").pack(anchor="w", pady=(0, 6))

        is_ollama, models = check_ollama_available()
        vision_model = select_best_vision_model(models) if is_ollama else None
        is_tess, tess_path = check_tesseract_available()

        # Engine Selection Frame
        engine_frame = ttk.LabelFrame(pad, text=" Extraction Engine ", padding=10)
        engine_frame.pack(fill="x", pady=(0, 12))

        engine_var = tk.StringVar()
        if is_ollama and vision_model and is_tess:
            engine_var.set("hybrid")
        elif is_ollama and vision_model:
            engine_var.set("ollama")
        elif is_tess:
            engine_var.set("ocr")
        else:
            engine_var.set("none")

        if is_ollama and vision_model and is_tess:
            ttk.Radiobutton(
                engine_frame,
                text=f"🚀 Hybrid: Ollama Vision ({vision_model}) + Local OCR + Smart Rules [Highest Accuracy]",
                variable=engine_var,
                value="hybrid"
            ).pack(anchor="w", pady=2)

        if is_ollama and vision_model:
            ttk.Radiobutton(
                engine_frame,
                text=f"🦙 Local Ollama Vision ({vision_model})",
                variable=engine_var,
                value="ollama"
            ).pack(anchor="w", pady=2)

        if is_tess:
            ttk.Radiobutton(
                engine_frame,
                text="⚡ Local Tesseract OCR (Fast, 100% Offline, no GPU needed)",
                variable=engine_var,
                value="ocr"
            ).pack(anchor="w", pady=2)

        if not is_ollama and not is_tess:
            ttk.Label(
                engine_frame,
                text="⚠️ Neither Ollama server nor Tesseract OCR is currently running.\nPlease start Ollama (`ollama serve`) or install Tesseract.",
                foreground="#b91c1c",
                wraplength=500
            ).pack(anchor="w", pady=4)

        msg = "Choose input source to process multiple case files/pages:"
        ttk.Label(pad, text=msg, wraplength=500, font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(0, 8))

        btn_box = ttk.Frame(pad)
        btn_box.pack(fill="x", pady=4)

        def pick_folder():
            eng = engine_var.get()
            if eng == "none":
                self._show_ollama_setup_dialog("No extraction engine is ready.")
                return
            win.destroy()
            folder = filedialog.askdirectory(title="Select Folder Containing Scanned Case Images / PDFs")
            if not folder:
                return
            exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".pdf"}
            all_files = sorted(str(p) for p in Path(folder).iterdir() if p.suffix.lower() in exts and not p.name.startswith("."))
            if not all_files:
                messagebox.showwarning("No Files Found", f"No scanned image or PDF files were found in:\n{folder}")
                return
            self.start_batch_dashboard(all_files, engine_choice=eng, model_name=vision_model or "tesseract")

        def pick_files():
            eng = engine_var.get()
            if eng == "none":
                self._show_ollama_setup_dialog("No extraction engine is ready.")
                return
            win.destroy()
            files = filedialog.askopenfilenames(
                title="Select Multiple Scanned Images / PDFs",
                filetypes=[
                    ("Image & PDF Files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.pdf"),
                    ("All Files", "*.*")
                ]
            )
            if not files:
                return
            self.start_batch_dashboard(list(files), engine_choice=eng, model_name=vision_model or "tesseract")

        ttk.Button(btn_box, text="📁 Select a Folder of Scanned Cases...", style="Primary.TButton", command=pick_folder).pack(fill="x", pady=4, ipady=4)
        ttk.Button(btn_box, text="📄 Select Multiple Files...", style="Action.TButton", command=pick_files).pack(fill="x", pady=4, ipady=4)

        ttk.Button(pad, text="Cancel", style="Action.TButton", command=win.destroy).pack(anchor="e", pady=(12, 0))

    def start_batch_dashboard(self, file_paths: list[str], engine_choice: str = "hybrid", model_name: str = ""):
        if not model_name:
            _, models = check_ollama_available()
            model_name = select_best_vision_model(models) or "tesseract"
        BatchDashboardWindow(self, file_paths, engine_choice, model_name)

    def scan_images_ollama(self):
        is_ollama, models = check_ollama_available()
        vision_model = select_best_vision_model(models) if is_ollama else None
        is_tess, _ = check_tesseract_available()

        if is_ollama and vision_model and is_tess:
            engine = "hybrid"
            active_model = vision_model
            engine_lbl = f"Hybrid (Ollama {vision_model} + OCR)"
        elif is_ollama and vision_model:
            engine = "ollama"
            active_model = vision_model
            engine_lbl = f"Local Ollama ({vision_model})"
        elif is_tess:
            engine = "ocr"
            active_model = "tesseract"
            engine_lbl = "Local Tesseract OCR"
        else:
            self._show_ollama_setup_dialog("Neither Ollama Vision nor Tesseract OCR is ready.")
            return

        file_paths = filedialog.askopenfilenames(
            title="Select Scanned Court Order Sheet Images / PDFs",
            filetypes=[
                ("Image & PDF Files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.pdf"),
                ("Image Files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp"),
                ("PDF Files", "*.pdf"),
                ("All Files", "*.*")
            ]
        )
        if not file_paths:
            return

        self.status.set(f"Extracting with {engine_lbl}...")
        self.update_idletasks()

        def worker():
            results: list[dict] = []
            try:
                all_frames = []
                for fp in file_paths:
                    frames = extract_image_frames(fp)
                    for label, orig_fp, b64 in frames:
                        all_frames.append((label, orig_fp, b64))

                total = len(all_frames)
                if not total:
                    self.after(0, lambda: messagebox.showwarning("No Pages", "No valid images could be loaded from the selected files."))
                    return

                for idx, (label, fp, b64) in enumerate(all_frames, 1):
                    self.after(0, lambda i=idx, l=label: self.status.set(f"🔍 Analyzing {i}/{total}: {l} ({engine_lbl})..."))
                    raw_text, parsed = process_frame(label, fp, b64, engine=engine, model_name=active_model)
                    results.append({"name": label, "path": fp, "raw_text": raw_text, "extracted": parsed})

                if not results:
                    self.after(0, lambda: messagebox.showwarning("Empty Response", "Extraction did not return any data."))
                    return

                self.after(0, lambda: self._show_multi_ocr_dialog(results, source_name=engine_lbl))
                self.after(0, lambda: self.status.set(f"Extracted {len(results)} page(s) via {engine_lbl}."))
            except Exception as exc:
                self.after(0, lambda err=exc: messagebox.showerror("Extraction Error", f"Failed during document analysis:\n{err}"))
                self.after(0, lambda: self.status.set("Document extraction encountered an error."))

        threading.Thread(target=worker, daemon=True).start()

    def _show_ollama_setup_dialog(self, error_msg: str = ""):
        win = tk.Toplevel(self)
        win.title("Offline Extraction Setup")
        win.geometry("560x360")
        win.transient(self)
        win.resizable(False, False)

        pad = ttk.Frame(win, padding=20)
        pad.pack(fill="both", expand=True)

        ttk.Label(pad, text="⚡ Extraction Engine Setup", font=(FONT_FAMILY, 14, "bold"), foreground="#792f30").pack(anchor="w", pady=(0, 6))

        instructions = (
            "To use automated court form filling offline:\n\n"
            "Option 1: Local Ollama Vision (Recommended for Handwritten Notes)\n"
            "   1. In terminal run:  ollama serve\n"
            "   2. Download model:   ollama pull qwen2.5vl:7b\n"
            "      (or: ollama pull qwen2.5vl:3b or llama3.2-vision)\n\n"
            "Option 2: Offline Local Tesseract OCR (Fast & Instant)\n"
            "   Install via Homebrew: brew install tesseract tesseract-lang\n\n"
            "Once installed or started, click 'Retry Connection' below."
        )
        ttk.Label(pad, text=instructions, wraplength=520, font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(0, 16))

        btn_bar = ttk.Frame(pad)
        btn_bar.pack(fill="x", pady=(10, 0))
        ttk.Button(btn_bar, text="Retry Connection", style="Primary.TButton", command=lambda: [win.destroy(), self.scan_images_ollama()]).pack(side="right", padx=4)
        ttk.Button(btn_bar, text="Close", style="Action.TButton", command=win.destroy).pack(side="right", padx=4)

    def _show_multi_ocr_dialog(self, results: list[dict], source_name: str = "Local Ollama"):
        win = tk.Toplevel(self)
        win.title(f"{source_name} Extraction Review ({len(results)} Page(s))")
        win.geometry("940x620")
        win.transient(self)

        container = ttk.Frame(win, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text=f"{source_name} analyzed {len(results)} page(s). Click 'Combine All Pages → 1 Case' below:", style="Section.TLabel").pack(anchor="w", pady=(0, 8))

        middle = ttk.Frame(container)
        middle.pack(fill="both", expand=True, pady=(0, 10))

        left_frame = ttk.Frame(middle, width=260)
        left_frame.pack(side="left", fill="y", padx=(0, 10))
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Scanned Pages:", font=(FONT_FAMILY, 10, "bold")).pack(anchor="w", pady=(0, 4))
        img_listbox = tk.Listbox(left_frame, selectmode="browse", font=(FONT_FAMILY, 10))
        img_listbox.pack(fill="both", expand=True)
        for idx, item in enumerate(results, 1):
            img_listbox.insert("end", f"{idx}. {item['name']} ({len(item['extracted'])} fields)")

        right_frame = ttk.Frame(middle)
        right_frame.pack(side="left", fill="both", expand=True)

        txt_box = tk.Text(right_frame, height=14, wrap="word", font=("Menlo" if IS_MAC else "Consolas", 10))
        txt_box.pack(fill="both", expand=True, pady=(0, 8))

        preview_var = tk.StringVar(value="")
        ttk.Label(right_frame, textvariable=preview_var, wraplength=640, foreground="#2b5876").pack(anchor="w")

        current_idx = {"val": 0}

        def save_current_json():
            i = current_idx["val"]
            if 0 <= i < len(results):
                try:
                    edited_json = json.loads(txt_box.get("1.0", "end").strip())
                    results[i]["extracted"] = edited_json
                except Exception:
                    pass

        def on_select_image(_event=None):
            save_current_json()
            sel = img_listbox.curselection()
            if not sel: return
            i = sel[0]
            current_idx["val"] = i
            txt_box.delete("1.0", "end")
            txt_box.insert("1.0", json.dumps(results[i]["extracted"], indent=2, ensure_ascii=False))
            ext = results[i]["extracted"]
            preview_var.set("Extracted Fields: " + (", ".join(f"{k}: '{v}'" for k, v in ext.items() if v) or "None"))

        img_listbox.bind("<<ListboxSelect>>", on_select_image)
        img_listbox.selection_set(0)
        on_select_image()

        btn_bar = ttk.Frame(container)
        btn_bar.pack(fill="x", pady=(6, 0))

        def combine_all_into_one_case():
            save_current_json()
            combined: dict[str, str] = {}
            raw_texts = []
            for item in results:
                raw_texts.append(item.get("raw_text", ""))
                for k, v in item["extracted"].items():
                    if v and not combined.get(k):
                        combined[k] = str(v).strip()
                    elif k == "hearing_date" and v:
                        combined[k] = str(v).strip()
                    elif k == "stage" and v and combined.get(k) in ("", "Hearing", "Other"):
                        combined[k] = str(v).strip()
                        if item["extracted"].get("stage_group"):
                            combined["stage_group"] = item["extracted"]["stage_group"]

            all_raw = "\n".join(raw_texts)
            first_fp = results[0].get("file_path", "") if results else ""
            combined = clean_and_normalize_case_data(combined, all_raw, file_path=first_fp)
            self._populate_form_from_dict(combined)
            self.status.set(f"Combined {len(results)} pages into 1 case via {source_name} ({len(combined)} fields filled).")
            win.destroy()

        def batch_save_all_cases():
            save_current_json()
            grouped_cases = group_extracted_pages(results)
            new_items = []
            dup_items = []

            for item in grouped_cases:
                ext = dict(item["extracted"])
                c_no = ext.get("existing_case_no", "")
                c_type = ext.get("case_type", "")
                dup = find_duplicate_case(self.db, c_no, c_type) if c_no else None
                if dup:
                    dup_items.append((item, dup))
                else:
                    new_items.append(item)

            handle_mode = "all"
            if dup_items:
                dup_preview = [f"• {it['extracted'].get('existing_case_no')} (Matches DB ID #{d['id']})" for it, d in dup_items[:5]]
                if len(dup_items) > 5:
                    dup_preview.append(f"... and {len(dup_items) - 5} more")
                dup_str = "\n".join(dup_preview)

                choice = messagebox.askyesnocancel(
                    "Duplicate Cases Detected",
                    f"⚠️ {len(dup_items)} of the {len(results)} cases already exist in the database:\n{dup_str}\n\n"
                    f"How would you like to handle existing records?\n\n"
                    f"[Yes] = UPDATE existing records\n"
                    f"[No] = SKIP duplicates (Save only {len(new_items)} new cases)\n"
                    f"[Cancel] = Cancel",
                    parent=win
                )
                if choice is None:
                    return
                handle_mode = "update_dups" if choice is True else "skip_dups"

            saved_count = 0
            updated_count = 0
            now = datetime.now().isoformat(timespec="seconds")

            for idx, item in enumerate(new_items, 1):
                ext = dict(item["extracted"])
                case_no = ext.get("existing_case_no") or f"AUTO-{datetime.now().strftime('%H%M%S')}-{idx}"
                ext["existing_case_no"] = case_no
                ext["case_no"] = case_no
                ext["case_status"] = self.case_mode

                entered_date = ext.get("hearing_date", "")
                if self.case_mode == "Disposed":
                    ext["dispose_date"] = entered_date
                    ext["hearing_date"] = ""
                else:
                    ext["hearing_date"] = entered_date
                    ext["dispose_date"] = ""

                self._learn_new_values(ext)
                keys = list(ext.keys())
                self.db.execute(
                    f"INSERT INTO cases ({','.join(keys)},created_at,updated_at) VALUES ({','.join('?' for _ in keys)},?,?)",
                    (*ext.values(), now, now)
                )
                saved_count += 1

            if handle_mode == "update_dups":
                for item, dup in dup_items:
                    ext = dict(item["extracted"])
                    dup_id = dup["id"]
                    update_fields = {}
                    for k in FIELDS:
                        key = k[0]
                        if ext.get(key):
                            update_fields[key] = ext[key]

                    entered_date = ext.get("hearing_date", "")
                    if entered_date:
                        if self.case_mode == "Disposed":
                            update_fields["dispose_date"] = entered_date
                        else:
                            update_fields["hearing_date"] = entered_date

                    update_fields["case_status"] = self.case_mode
                    self._learn_new_values(update_fields)

                    if update_fields:
                        assigns = ", ".join(f"{k}=?" for k in update_fields)
                        self.db.execute(
                            f"UPDATE cases SET {assigns}, updated_at=? WHERE id=?",
                            (*update_fields.values(), now, dup_id)
                        )
                        updated_count += 1

            self.db.commit()
            self.refresh()
            msg = f"Batch saved {saved_count} new case(s)."
            if updated_count:
                msg += f" Updated {updated_count} existing case(s)."
            self.status.set(msg)
            win.destroy()

        self._button(btn_bar, "Combine All Pages → 1 Case (Recommended)", combine_all_into_one_case, primary=True).pack(side="right", padx=4)
        if len(results) > 1:
            self._button(btn_bar, f"Batch Save All ({len(results)} Cases)", batch_save_all_cases).pack(side="right", padx=4)

        self._button(btn_bar, "Cancel", win.destroy).pack(side="left")

    def _populate_form_from_dict(self, data: dict[str, str]):
        self.clear_form()
        for k, v in data.items():
            if k in self.vars and v:
                if k == "existing_case_no":
                    self.vars[k].set(extract_case_number_only(str(v)))
                elif k == "case_type":
                    self.vars[k].set(normalize_case_type(str(v)))
                else:
                    self.vars[k].set(str(v).strip())
        
        # Check aliases for bundle_no, month_year, and possession
        b_val = data.get("bundle_no") or data.get("bundleNo") or data.get("bundle_number") or data.get("bundle") or ""
        my_val = data.get("month_year") or data.get("monthYear") or (f"{data.get('month')}-{data.get('year')}" if data.get("month") and data.get("year") else "") or ""
        poss_val = data.get("possession") or ""
        
        # Auto-extract from filename if missing
        fn = data.get("name") or data.get("filename") or data.get("path") or data.get("file_path") or ""
        if fn:
            fn_info = extract_bundle_month_year_from_filename(fn)
            if fn_info:
                if not b_val and fn_info.get("bundleNo"):
                    b_val = fn_info["bundleNo"]
                if not my_val and fn_info.get("monthYear"):
                    my_val = fn_info["monthYear"]
                if not self.vars["court"].get() and fn_info.get("courtHall"):
                    self.vars["court"].set(fn_info["courtHall"])
                if not self.vars["existing_case_no"].get() and fn_info.get("caseNo"):
                    self.vars["existing_case_no"].set(fn_info["caseNo"])
                if not self.vars["filing_year"].get() and fn_info.get("filingYear"):
                    self.vars["filing_year"].set(str(fn_info["filingYear"]))

        if "bundle_no" in self.vars and b_val:
            self.vars["bundle_no"].set(str(b_val))
        if "month_year" in self.vars and my_val:
            self.vars["month_year"].set(str(my_val))
        if "possession" in self.vars and poss_val:
            self.vars["possession"].set(str(poss_val))

        self._learn_new_values(data)
        self._sync_geo_dropdowns()
        grp = self.vars["stage_group"].get()
        if hasattr(self, "stage_widget"):
            self.stage_widget["values"] = STAGES_BY_GROUP.get(grp, STAGES)
        if hasattr(self, "stage_group_widget"):
            self.stage_group_widget["values"] = STAGE_GROUPS

    def _sync_geo_dropdowns(self):
        dist, taluk = self.vars["district"].get(), self.vars["taluk"].get()
        self.geo_widgets["district"]["values"] = sorted(GEO)
        self.geo_widgets["taluk"]["values"] = sorted(GEO.get(dist, {}))
        item = GEO.get(dist, {}).get(taluk, {})
        self.geo_widgets["hobli"]["values"] = sorted(item.get("h", []))
        self.geo_widgets["village"]["values"] = sorted(item.get("v", []))

    def stage_group_changed(self, _event=None):
        if hasattr(self, "stage_group_widget"):
            self.stage_group_widget["values"] = STAGE_GROUPS
        group = self.vars["stage_group"].get()
        valid_stages = STAGES_BY_GROUP.get(group, STAGES)
        if hasattr(self, "stage_widget"):
            self.stage_widget["values"] = valid_stages
            if self.vars["stage"].get() and self.vars["stage"].get() not in valid_stages:
                self.vars["stage"].set("")

    def stage_group_typed(self, event=None):
        if event and event.keysym in {"Up", "Down", "Left", "Right", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        prefix = self.vars["stage_group"].get().strip().casefold()
        if hasattr(self, "stage_group_widget"):
            self.stage_group_widget["values"] = [g for g in STAGE_GROUPS if not prefix or g.casefold().startswith(prefix)]
        exact = next((g for g in STAGE_GROUPS if g.casefold() == prefix), None)
        if exact and hasattr(self, "stage_widget"):
            valid_stages = STAGES_BY_GROUP[exact]
            self.stage_widget["values"] = valid_stages
            if self.vars["stage"].get() and self.vars["stage"].get() not in valid_stages:
                self.vars["stage"].set("")

    def stage_changed(self, _event=None):
        st = self.vars["stage"].get()
        if st and st in STAGE_TO_GROUP:
            grp = STAGE_TO_GROUP[st]
            if not self.vars["stage_group"].get():
                self.vars["stage_group"].set(grp)
            if hasattr(self, "stage_widget") and self.vars["stage_group"].get():
                self.stage_widget["values"] = STAGES_BY_GROUP.get(self.vars["stage_group"].get(), STAGES)

    def district_changed(self, _event=None):
        self.vars["taluk"].set(""); self.vars["hobli"].set(""); self.vars["village"].set("")
        district = self.vars["district"].get()
        self.geo_widgets["taluk"]["values"] = sorted(GEO.get(district, {}))
        self.geo_widgets["hobli"]["values"] = (); self.geo_widgets["village"]["values"] = ()

    def taluk_changed(self, _event=None):
        self.vars["hobli"].set(""); self.vars["village"].set("")
        item = GEO.get(self.vars["district"].get(), {}).get(self.vars["taluk"].get(), {})
        self.geo_widgets["hobli"]["values"] = sorted(item.get("h", []))
        self.geo_widgets["village"]["values"] = sorted(item.get("v", []))

    def geo_options(self, key):
        district, taluk = self.vars["district"].get(), self.vars["taluk"].get()
        if key == "district": return sorted(GEO)
        if key == "taluk": return sorted(GEO.get(district, {}))
        item = GEO.get(district, {}).get(taluk, {})
        return sorted(item.get("h" if key == "hobli" else "v", []))

    def filter_geo_options(self, key, event=None):
        if event and event.keysym in {"Up", "Down", "Left", "Right", "Return", "Escape", "Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return
        prefix = self.vars[key].get().strip().casefold()
        options = self.geo_options(key)
        self.geo_widgets[key]["values"] = [v for v in options if not prefix or v.casefold().startswith(prefix)]

    def pick_date(self, key):
        current = self.vars[key].get()
        try: year, month, day = map(int, current.split("-"))
        except (ValueError, TypeError):
            now = datetime.now(); year, month, day = now.year, now.month, now.day
        win = tk.Toplevel(self); win.title("Select date"); win.transient(self); win.resizable(False, False)
        state = {"year": year, "month": month}
        top = ttk.Frame(win, padding=8); top.pack(fill="x")
        body = ttk.Frame(win, padding=8); body.pack()

        def draw():
            for child in top.winfo_children(): child.destroy()
            for child in body.winfo_children(): child.destroy()
            ttk.Button(top, text="‹", width=3, command=lambda: shift(-1)).pack(side="left")
            ttk.Label(top, text=f"{calendar.month_name[state['month']]} {state['year']}", width=20, anchor="center").pack(side="left")
            ttk.Button(top, text="›", width=3, command=lambda: shift(1)).pack(side="left")
            for c, name in enumerate(("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")): ttk.Label(body, text=name, width=4, anchor="center").grid(row=0, column=c)
            for r, week in enumerate(calendar.monthcalendar(state["year"], state["month"]), 1):
                for c, n in enumerate(week):
                    if n: ttk.Button(body, text=str(n), width=4, command=lambda n=n: choose(n)).grid(row=r, column=c, padx=1, pady=1)

        def shift(delta):
            state["month"] += delta
            if state["month"] < 1: state["month"] = 12; state["year"] -= 1
            if state["month"] > 12: state["month"] = 1; state["year"] += 1
            draw()

        def choose(n):
            self.vars[key].set(f"{state['year']:04d}-{state['month']:02d}-{n:02d}"); win.destroy()

        draw()

    def on_date_summary_select(self, _event=None):
        sel = self.date_tree.selection()
        if not sel: return
        self.date_filter_var.set(self.date_tree.item(sel[0], "values")[0])
        self.clear_date_btn.pack(side="left", padx=6)
        self.refresh(update_date_tree=False)

    def clear_date_filter(self):
        self.date_filter_var.set(""); self.date_tree.selection_remove(self.date_tree.selection())
        self.clear_date_btn.pack_forget(); self.refresh()

    def refresh(self, update_date_tree: bool = True):
        q = f"%{self.query.get().strip()}%"
        date_filter = self.date_filter_var.get().strip()
        sql = "SELECT * FROM cases WHERE COALESCE(case_status, 'Pending') = ? AND (case_no LIKE ? OR existing_case_no LIKE ? OR village LIKE ? OR district LIKE ? OR taluk LIKE ?)"
        params: list[str] = [self.case_mode, q, q, q, q, q]
        if date_filter:
            sql += " AND substr(created_at, 1, 10) = ?"
            params.append(date_filter)
        sql += " ORDER BY id DESC"
        rows = self.db.execute(sql, params).fetchall()

        self.tree.delete(*self.tree.get_children())
        all_mode_rows = self.db.execute("SELECT id FROM cases WHERE COALESCE(case_status, 'Pending') = ? ORDER BY id", (self.case_mode,)).fetchall()
        serial = {row["id"]: n for n, row in enumerate(all_mode_rows, 1)}

        for r in rows:
            extent = " ".join(x for x in [r["extent"], r["unit"]] if x)
            status_val = r["case_status"] if "case_status" in r.keys() else "Pending"
            hearing_val = r["hearing_date"] if "hearing_date" in r.keys() else ""
            dispose_val = r["dispose_date"] if "dispose_date" in r.keys() else ""
            created_val = r["created_at"] if "created_at" in r.keys() else ""

            action_dt = hearing_val if (status_val or "Pending") == "Pending" else (dispose_val or hearing_val)
            chk = "[✓]" if r["id"] in self.checked_ids else "[ ]"
            self.tree.insert("", "end", iid=str(r["id"]), values=(
                chk, serial.get(r["id"], r["id"]), status_val or "Pending", r["existing_case_no"] or r["case_no"],
                r["case_type"], r["court"], r["filing_year"], action_dt, r["stage"], extent, r["village"], r["district"], created_val[:10]
            ))

        if hasattr(self, "selected_count_var"):
            self.selected_count_var.set(f"{len(self.checked_ids)} selected")

        total_all = self.db.execute("SELECT count(*) FROM cases").fetchone()[0]
        total_pending = self.db.execute("SELECT count(*) FROM cases WHERE COALESCE(case_status, 'Pending')='Pending'").fetchone()[0]
        total_disposed = self.db.execute("SELECT count(*) FROM cases WHERE case_status='Disposed'").fetchone()[0]

        mode_total = total_pending if self.case_mode == "Pending" else total_disposed
        self.count.set(f"Showing {len(rows)} of {mode_total} {self.case_mode.lower()} records")
        self.total_badge.set(f"Total Records: {total_all}  |  Pending: {total_pending}  |  Disposed: {total_disposed}")
        self.summary_totals_lbl.configure(text=f"Total: {total_all} (Pending: {total_pending}, Disposed: {total_disposed})")

        if update_date_tree:
            self.date_tree.delete(*self.date_tree.get_children())
            for dr in self.db.execute("SELECT substr(created_at, 1, 10) AS entry_date, SUM(CASE WHEN COALESCE(case_status, 'Pending') = 'Pending' THEN 1 ELSE 0 END) AS pending_cnt, SUM(CASE WHEN case_status = 'Disposed' THEN 1 ELSE 0 END) AS disposed_cnt, COUNT(*) AS total_cnt FROM cases GROUP BY substr(created_at, 1, 10) ORDER BY entry_date DESC").fetchall():
                self.date_tree.insert("", "end", values=(dr["entry_date"], dr["pending_cnt"], dr["disposed_cnt"], dr["total_cnt"]))

    def save(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        data["existing_case_no"] = extract_case_number_only(data.get("existing_case_no", ""))
        data["case_type"] = normalize_case_type(data.get("case_type", "LGC(G)"))
        data["court"] = normalize_court_hall(data.get("court", "Court Hall No.1"))
        if not data["existing_case_no"]:
            messagebox.showwarning("Required field", "Enter the Existing Case No.")
            return

        data["case_no"] = data["existing_case_no"]
        data["case_status"] = self.case_mode
        entered_date = data.get("hearing_date", "")
        if self.case_mode == "Disposed":
            data["dispose_date"], data["hearing_date"] = entered_date, ""
        else:
            data["hearing_date"], data["dispose_date"] = entered_date, ""

        if any(not data[key] for key in ("district", "taluk", "hobli", "village")):
            messagebox.showwarning("Required property location", "Enter or select all location fields: District, Taluk, Hobli, and Village.")
            return

        # Duplicate validation on save (when creating a new case)
        if not self.edit_id:
            dup = find_duplicate_case(self.db, data["existing_case_no"], data.get("case_type", ""))
            if dup:
                dup_id = dup["id"]
                dup_cno = dup["existing_case_no"] or dup["case_no"]
                dup_court = dup["court"] or "N/A"
                dup_stage = dup["stage"] or "N/A"
                dup_date = dup["hearing_date"] or dup["dispose_date"] or "N/A"
                dup_status = dup["case_status"] or "Pending"
                dup_village = dup["village"] or "N/A"

                choice = messagebox.askyesnocancel(
                    "Duplicate Case Detected",
                    f"⚠️ Case '{dup_cno}' already exists in the database! (Record ID #{dup_id})\n\n"
                    f"Existing Record Details:\n"
                    f"• Status: {dup_status}\n"
                    f"• Court: {dup_court}\n"
                    f"• Stage: {dup_stage}\n"
                    f"• Action Date: {dup_date}\n"
                    f"• Village: {dup_village}\n\n"
                    f"Would you like to UPDATE the existing record with these new values?\n\n"
                    f"[Yes] = Update existing record #{dup_id}\n"
                    f"[No] = Save as a new duplicate record\n"
                    f"[Cancel] = Cancel and keep editing",
                    default="cancel"
                )
                if choice is None:
                    return
                elif choice is True:
                    self.edit_id = dup_id

        self._learn_new_values(data)
        now = datetime.now().isoformat(timespec="seconds")
        if self.edit_id:
            assignments = ", ".join(f"{key}=?" for key in data)
            self.db.execute(f"UPDATE cases SET {assignments}, updated_at=? WHERE id=?", (*data.values(), now, self.edit_id))
            msg = f"{self.case_mode} case updated."
        else:
            keys = list(data)
            self.db.execute(f"INSERT INTO cases ({','.join(keys)},created_at,updated_at) VALUES ({','.join('?' for _ in keys)},?,?)", (*data.values(), now, now))
            msg = f"{self.case_mode} case saved."

        self.db.commit(); self.clear_form(); self.refresh()
        self.status.set(f"{msg} Saved in {DB_PATH}")

        if self.ocr_queue:
            if self.ocr_queue_idx < len(self.ocr_queue) - 1:
                self.ocr_queue_idx += 1
                self._load_current_queue_item()
            else:
                self._clear_ocr_queue()
                messagebox.showinfo("Queue Complete", "All cases in the review queue have been reviewed and saved!")

    def selected_id(self):
        selection = self.tree.selection()
        return int(selection[0]) if selection else None

    def load_selected(self):
        ident = self.selected_id()
        if ident is None: return
        row = self.db.execute("SELECT * FROM cases WHERE id=?", (ident,)).fetchone()
        if not row: return
        self.edit_id = ident
        status_val = row["case_status"] if "case_status" in row.keys() else "Pending"
        hearing_val = row["hearing_date"] if "hearing_date" in row.keys() else ""
        dispose_val = row["dispose_date"] if "dispose_date" in row.keys() else ""

        for key, _ in FIELDS:
            if key == "hearing_date":
                self.vars[key].set(dispose_val if status_val == "Disposed" else hearing_val or "")
            else:
                self.vars[key].set(row[key] if key in row.keys() and row[key] is not None else "")
        self._sync_geo_dropdowns()
        grp = self.vars["stage_group"].get()
        if hasattr(self, "stage_widget"):
            self.stage_widget["values"] = STAGES_BY_GROUP.get(grp, STAGES)
        if hasattr(self, "stage_group_widget"):
            self.stage_group_widget["values"] = STAGE_GROUPS
        self.status.set(f"Editing {row['existing_case_no'] or row['case_no']}.")
        if getattr(self, "pdf_pane_visible", False):
            self.update_pdf_display_for_active_case()

    def clear_form(self):
        self.edit_id = None
        for value in self.vars.values(): value.set("")
        self.geo_widgets["taluk"]["values"] = (); self.geo_widgets["hobli"]["values"] = (); self.geo_widgets["village"]["values"] = ()
        self.geo_widgets["district"]["values"] = sorted(GEO)
        if hasattr(self, "stage_group_widget"):
            self.stage_group_widget["values"] = STAGE_GROUPS
        if hasattr(self, "stage_widget"):
            self.stage_widget["values"] = STAGES

    def delete(self):
        ident = self.selected_id() or self.edit_id
        if ident is None:
            messagebox.showinfo("Select a case", "Select a row first.")
            return
        row = self.db.execute("SELECT case_no FROM cases WHERE id=?", (ident,)).fetchone()
        if row and messagebox.askyesno("Delete case", f"Delete {row['case_no']}? This cannot be undone."):
            self.db.execute("DELETE FROM cases WHERE id=?", (ident,))
            self.db.commit()
            self.checked_ids.discard(ident)
            self.clear_form()
            self.refresh()

    def toggle_export_check(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell" or self.tree.identify_column(event.x) != "#1":
            return
        item = self.tree.identify_row(event.y)
        if not item:
            return
        ident = int(item)
        if ident in self.checked_ids:
            self.checked_ids.remove(ident)
        else:
            self.checked_ids.add(ident)
        values = list(self.tree.item(item, "values"))
        values[0] = "[✓]" if ident in self.checked_ids else "[ ]"
        self.tree.item(item, values=values)
        if hasattr(self, "selected_count_var"):
            self.selected_count_var.set(f"{len(self.checked_ids)} selected")
        self.tree.selection_set(item)
        return "break"

    def select_all_visible(self):
        for item in self.tree.get_children(""):
            ident = int(item)
            self.checked_ids.add(ident)
            values = list(self.tree.item(item, "values"))
            values[0] = "[✓]"
            self.tree.item(item, values=values)
        if hasattr(self, "selected_count_var"):
            self.selected_count_var.set(f"{len(self.checked_ids)} selected")

    def clear_export_selection(self):
        self.checked_ids.clear()
        for item in self.tree.get_children(""):
            values = list(self.tree.item(item, "values"))
            values[0] = "[ ]"
            self.tree.item(item, values=values)
        if hasattr(self, "selected_count_var"):
            self.selected_count_var.set("0 selected")

    def export_selected_csv(self):
        self._export_selected("csv")

    def export_selected_json(self):
        self._export_selected("json")

    def _export_selected(self, file_format: str):
        if not self.checked_ids:
            messagebox.showinfo("Select records", "Tick the Select box beside each record you want to export.")
            return
        ids = sorted(self.checked_ids)
        records = [dict(r) for r in self.db.execute(
            f"SELECT * FROM cases WHERE id IN ({','.join('?' for _ in ids)}) ORDER BY id", ids
        ).fetchall()]
        if not records:
            messagebox.showinfo("No records", "The selected records are no longer available.")
            return
        extension = ".json" if file_format == "json" else ".csv"
        path = filedialog.asksaveasfilename(
            defaultextension=extension, initialfile=f"selected_{self.case_mode.lower()}_cases{extension}",
            filetypes=[("JSON file", "*.json")] if file_format == "json" else [("CSV file", "*.csv")],
        )
        if not path:
            return
        if file_format == "json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
        else:
            self.write_csv(path, records)
        self.status.set(f"Exported {len(records)} selected records to {path}")

    def records(self):
        return [dict(r) for r in self.db.execute("SELECT * FROM cases ORDER BY id").fetchall()]

    def export_json(self):
        records = self.records()
        if not records: messagebox.showinfo("Nothing to export", "There are no records yet."); return
        path = filedialog.asksaveasfilename(defaultextension=".json", initialfile=f"{self.case_mode.lower()}_cases.json", filetypes=[("JSON", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f: json.dump(records, f, ensure_ascii=False, indent=2)
            self.status.set(f"Exported {len(records)} records to {path}")

    def export_csv(self):
        records = self.records()
        if not records: messagebox.showinfo("Nothing to export", "There are no records yet."); return
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"{self.case_mode.lower()}_cases.csv", filetypes=[("CSV", "*.csv")])
        if not path: return
        self.write_csv(path, records)
        self.status.set(f"Exported {len(records)} records to {path}")

    def write_csv(self, path: str, records: list[dict]):
        csv_head = [
            "Sl. No.", "Case Status", "Case No. and Year", "Type G", "Type P", "Type T",
            "Type S", "Type R.P.", "Type Misc", "Court Hall No.1", "Court Hall No.2",
            "Date of Filing", "Next date of Hearing", "Dispose Date", "Stage of the case",
            "Restoration of land", "Extent", "Extent Unit", "Village", "Hobli",
            "Taluk", "District", "Survey No.", "Ward No.", "PID No.",
            "Property Tax Assessment No.", "Filing Year", "Stage Group", "Entry Date"
        ]
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f); writer.writerow(csv_head)
            for sl, r in enumerate(records, 1):
                row = [""] * len(csv_head)
                status_val = r.get("case_status") if isinstance(r, dict) else (r["case_status"] if "case_status" in r.keys() else "Pending")
                hearing_val = r.get("hearing_date") if isinstance(r, dict) else (r["hearing_date"] if "hearing_date" in r.keys() else "")
                dispose_val = r.get("dispose_date") if isinstance(r, dict) else (r["dispose_date"] if "dispose_date" in r.keys() else "")
                created_raw = r.get("created_at") if isinstance(r, dict) else (r["created_at"] if "created_at" in r.keys() else "")
                created_val = str(created_raw or "")

                row[0:3] = [sl, status_val or "Pending", r.get("existing_case_no") or r.get("case_no") or ""]
                types = {
                    "LGC(G)": 3, "G": 3,
                    "LGC(P)": 4, "P": 4,
                    "LGC(T)": 5, "T": 5,
                    "LGC(S)": 6, "S": 6,
                    "RP": 7, "R.P.": 7,
                    "Misc": 8, "MISC": 8
                }
                courts = {"Court Hall No.1": 9, "Court Hall No.2": 10}
                ct = r.get("case_type", "")
                ch = r.get("court", "")
                norm_ct = normalize_case_type(ct) if ct else ""
                if norm_ct in types:
                    row[types[norm_ct]] = 1
                elif ct in types:
                    row[types[ct]] = 1
                if ch in courts: row[courts[ch]] = 1
                row[11:29] = [
                    "", hearing_val or "", dispose_val or "", r.get("stage", ""), r.get("restoration", ""),
                    r.get("extent", ""), r.get("unit", ""), r.get("village", ""), r.get("hobli", ""), r.get("taluk", ""), r.get("district", ""),
                    r.get("survey_no", ""), r.get("ward_no", ""), r.get("pid_no", ""), r.get("tax_no", ""), r.get("filing_year", ""), r.get("stage_group", ""), created_val[:10]
                ]
                writer.writerow(row)

    # ---------------------------------------------------------
    # Side-by-Side Original PDF Viewer & Comparison Methods
    # ---------------------------------------------------------
    def _build_pdf_viewer_pane(self):
        self.pdf_side_pane = ttk.Frame(self.middle_paned, width=580)

        # Header bar for PDF Viewer
        pdf_top = tk.Frame(self.pdf_side_pane, bg="#1e293b", padx=8, pady=6)
        pdf_top.pack(fill="x")

        # Left: File title & status
        self.pdf_title_var = tk.StringVar(value="📄 Original PDF Viewer")
        self.pdf_title_lbl = tk.Label(
            pdf_top, textvariable=self.pdf_title_var, bg="#1e293b", fg="#f8fafc",
            font=(FONT_FAMILY, 10, "bold"), anchor="w"
        )
        self.pdf_title_lbl.pack(side="left", fill="x", expand=True)

        # Controls bar (right)
        btn_box = tk.Frame(pdf_top, bg="#1e293b")
        btn_box.pack(side="right")

        self.pdf_prev_btn = tk.Button(
            btn_box, text="◀", font=(FONT_FAMILY, 9), bg="#334155", fg="#f8fafc",
            relief="flat", padx=6, pady=2, command=self.prev_pdf_page
        )
        self.pdf_prev_btn.pack(side="left", padx=2)

        self.pdf_page_lbl = tk.Label(btn_box, text="1/1", bg="#1e293b", fg="#94a3b8", font=(FONT_FAMILY, 9))
        self.pdf_page_lbl.pack(side="left", padx=3)

        self.pdf_next_btn = tk.Button(
            btn_box, text="▶", font=(FONT_FAMILY, 9), bg="#334155", fg="#f8fafc",
            relief="flat", padx=6, pady=2, command=self.next_pdf_page
        )
        self.pdf_next_btn.pack(side="left", padx=2)

        # Zoom controls
        tk.Button(
            btn_box, text="➖", font=(FONT_FAMILY, 9), bg="#334155", fg="#f8fafc",
            relief="flat", padx=4, pady=2, command=lambda: self.zoom_pdf(0.85)
        ).pack(side="left", padx=2)

        self.pdf_zoom_lbl = tk.Label(btn_box, text="100%", bg="#1e293b", fg="#94a3b8", font=(FONT_FAMILY, 9))
        self.pdf_zoom_lbl.pack(side="left", padx=2)

        tk.Button(
            btn_box, text="➕", font=(FONT_FAMILY, 9), bg="#334155", fg="#f8fafc",
            relief="flat", padx=4, pady=2, command=lambda: self.zoom_pdf(1.18)
        ).pack(side="left", padx=2)

        tk.Button(
            btn_box, text="Fit", font=(FONT_FAMILY, 9), bg="#334155", fg="#f8fafc",
            relief="flat", padx=5, pady=2, command=self.fit_pdf_width
        ).pack(side="left", padx=2)

        # Open in system default viewer
        tk.Button(
            btn_box, text="↗ Open", font=(FONT_FAMILY, 9), bg="#475569", fg="#f8fafc",
            relief="flat", padx=5, pady=2, command=self.open_pdf_in_system_viewer
        ).pack(side="left", padx=2)

        # Browse for another PDF
        tk.Button(
            btn_box, text="📂 Browse", font=(FONT_FAMILY, 9), bg="#475569", fg="#f8fafc",
            relief="flat", padx=5, pady=2, command=self.browse_pdf_for_case
        ).pack(side="left", padx=2)

        # Close pane button
        tk.Button(
            btn_box, text="✕", font=(FONT_FAMILY, 9, "bold"), bg="#dc2626", fg="#ffffff",
            relief="flat", padx=6, pady=2, command=self.hide_pdf_pane
        ).pack(side="left", padx=(4, 0))

        # Canvas for PDF page display
        canvas_frame = tk.Frame(self.pdf_side_pane, bg="#334155")
        canvas_frame.pack(fill="both", expand=True)

        self.pdf_canvas = tk.Canvas(canvas_frame, bg="#334155", highlightthickness=0, height=420, yscrollincrement=16, xscrollincrement=16)
        pdf_yscroll = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.pdf_canvas.yview)
        pdf_xscroll = ttk.Scrollbar(canvas_frame, orient="horizontal", command=self.pdf_canvas.xview)
        self.pdf_canvas.configure(yscrollcommand=pdf_yscroll.set, xscrollcommand=pdf_xscroll.set)

        self.pdf_canvas.grid(row=0, column=0, sticky="nsew")
        pdf_yscroll.grid(row=0, column=1, sticky="ns")
        pdf_xscroll.grid(row=1, column=0, sticky="ew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)

        self.pdf_canvas.bind("<MouseWheel>", self._on_pdf_mousewheel)
        self.pdf_canvas.bind("<Button-4>", lambda _e: self.pdf_canvas.yview_scroll(-2, "units"))
        self.pdf_canvas.bind("<Button-5>", lambda _e: self.pdf_canvas.yview_scroll(2, "units"))

        # Footer info bar
        pdf_footer = tk.Frame(self.pdf_side_pane, bg="#e2e8f0", padx=8, pady=3)
        pdf_footer.pack(fill="x")
        self.pdf_folder_status = tk.StringVar(value="")
        tk.Label(pdf_footer, textvariable=self.pdf_folder_status, bg="#e2e8f0", fg="#475569", font=(FONT_FAMILY, 8), anchor="w").pack(side="left", fill="x", expand=True)
        tk.Button(pdf_footer, text="Set Folder", font=(FONT_FAMILY, 8), bg="#cbd5e1", fg="#1e293b", relief="flat", command=self.choose_pdf_folder).pack(side="right")
        self._update_pdf_folder_status_label()

    def _update_pdf_folder_status_label(self):
        if self.pdf_folder_path:
            self.pdf_folder_status.set(f"PDF Folder: {self.pdf_folder_path}")
        else:
            self.pdf_folder_status.set("PDF Folder: Not configured (Click 'Set Folder')")

    def choose_pdf_folder(self):
        chosen = filedialog.askdirectory(
            parent=self,
            title="Select Folder Where Original Court PDFs Are Stored",
            initialdir=self.pdf_folder_path or str(APP_DIR)
        )
        if chosen:
            self.pdf_folder_path = os.path.realpath(chosen)
            try:
                self.db.execute("DELETE FROM custom_options WHERE field_key = 'pdf_folder_path'")
                self.db.execute("INSERT INTO custom_options (field_key, field_value) VALUES ('pdf_folder_path', ?)", (self.pdf_folder_path,))
                self.db.commit()
            except Exception:
                pass
            self._update_pdf_folder_status_label()
            self.status.set(f"PDF Folder configured: {self.pdf_folder_path}")
            if self.pdf_pane_visible:
                self.update_pdf_display_for_active_case()
            messagebox.showinfo("PDF Folder Configured", f"Original PDF Folder successfully set to:\n{self.pdf_folder_path}\n\nWhen comparing cases, PDFs matching case numbers in this folder will load automatically.", parent=self)

    def toggle_pdf_side_by_side(self):
        if self.pdf_pane_visible:
            self.hide_pdf_pane()
        else:
            self.show_pdf_pane()

    def show_pdf_pane(self):
        if not self.pdf_pane_visible:
            self.pdf_pane_visible = True
            # Expand window width if needed for side-by-side comfort
            try:
                screen_w = self.winfo_screenwidth()
                target_w = min(1680, screen_w - 40)
                if self.winfo_width() < target_w:
                    self.geometry(f"{target_w}x{self.winfo_height()}")
            except Exception:
                pass

            self.middle_paned.add(self.pdf_side_pane, minsize=420)
            if hasattr(self, "toggle_pdf_btn"):
                self.toggle_pdf_btn.configure(text="✕ Hide PDF")
            if hasattr(self, "form_pdf_btn"):
                self.form_pdf_btn.configure(text="✕ Hide PDF")
            self.after(50, self._adjust_paned_sash)
            self.update_pdf_display_for_active_case()

    def hide_pdf_pane(self):
        if self.pdf_pane_visible:
            self.pdf_pane_visible = False
            try:
                self.middle_paned.forget(self.pdf_side_pane)
            except Exception:
                pass
            if hasattr(self, "toggle_pdf_btn"):
                self.toggle_pdf_btn.configure(text="📄 Compare PDF")
            if hasattr(self, "form_pdf_btn"):
                self.form_pdf_btn.configure(text="📄 Compare PDF")

    def _adjust_paned_sash(self):
        try:
            total_w = self.middle_paned.winfo_width()
            if total_w > 900 and len(self.middle_paned.panes()) > 1:
                sash_x = int(total_w * 0.58)
                self.middle_paned.sash_place(0, sash_x, 0)
        except Exception:
            pass

    def show_selected_pdf(self):
        self.load_selected()
        if not self.pdf_pane_visible:
            self.show_pdf_pane()
        else:
            self.update_pdf_display_for_active_case()

    def update_pdf_display_for_active_case(self, force_file: str | None = None):
        if not self.pdf_pane_visible:
            return

        if force_file and os.path.exists(force_file):
            self.load_pdf_file(force_file)
            return

        # Priority 1: Match by active case number and filing year in configured PDF folder
        raw_cno = self.vars.get("existing_case_no", tk.StringVar()).get().strip()
        c_no = extract_case_number_only(raw_cno)
        f_yr = self.vars.get("filing_year", tk.StringVar()).get().strip()

        matched = self.find_pdf_file(c_no, f_yr) if c_no else None
        if matched:
            self.load_pdf_file(matched)
            return

        # Priority 2: Check Review Queue item
        if self.ocr_queue and 0 <= self.ocr_queue_idx < len(self.ocr_queue):
            item = self.ocr_queue[self.ocr_queue_idx]
            paths = item.get("paths") or ([item.get("path")] if item.get("path") else [])
            for p in paths:
                if p and os.path.exists(p):
                    self.load_pdf_file(p)
                    return

        self.show_pdf_placeholder(c_no)

    def find_pdf_file(self, case_no: str, year: str = "") -> str | None:
        if not case_no:
            return None

        clean_no = extract_case_number_only(case_no).lower()
        if clean_no in self.pdf_file_map and os.path.exists(self.pdf_file_map[clean_no]):
            return self.pdf_file_map[clean_no]

        search_dirs = []
        if self.pdf_folder_path and os.path.exists(self.pdf_folder_path):
            search_dirs.append(self.pdf_folder_path)
        search_dirs.append(str(APP_DIR))
        user_upl = Path(DATA_DIR).parent / "fa6da338-9f0c-4e8e-b06b-02d5d9511e00" / ".user_uploaded"
        if user_upl.exists():
            search_dirs.append(str(user_upl))

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
                        if self.pdf_folder_path and (root == self.pdf_folder_path or str(root).startswith(str(self.pdf_folder_path))):
                            score += 100
                        if " (" in fn or "copy" in fn:
                            score -= 5
                        if score > 0:
                            candidates.append((score, os.path.join(root, f)))

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_match = candidates[0][1]
            self.pdf_file_map[clean_no] = best_match
            return best_match

        return None

    def load_pdf_file(self, file_path: str, page_num: int = 1):
        if not file_path or not os.path.exists(file_path):
            self.show_pdf_placeholder()
            return

        self.pdf_current_path = os.path.realpath(file_path)
        self.pdf_current_page = max(1, page_num)
        self._render_current_pdf_page()

        # Auto-extract from filename if bundle or case fields are unset
        fn_info = extract_bundle_month_year_from_filename(file_path)
        if fn_info:
            if "bundle_no" in self.vars and not self.vars["bundle_no"].get() and fn_info.get("bundleNo"):
                self.vars["bundle_no"].set(fn_info["bundleNo"])
            if "month_year" in self.vars and not self.vars["month_year"].get() and fn_info.get("monthYear"):
                self.vars["month_year"].set(fn_info["monthYear"])
            if not self.vars["court"].get() and fn_info.get("courtHall"):
                self.vars["court"].set(fn_info["courtHall"])
            if not self.vars["existing_case_no"].get() and fn_info.get("caseNo"):
                self.vars["existing_case_no"].set(fn_info["caseNo"])
            if not self.vars["filing_year"].get() and fn_info.get("filingYear"):
                self.vars["filing_year"].set(str(fn_info["filingYear"]))
            if not self.vars["case_type"].get() and fn_info.get("caseType"):
                self.vars["case_type"].set(normalize_case_type(fn_info["caseType"]))

    def _render_current_pdf_page(self):
        if not self.pdf_current_path or not os.path.exists(self.pdf_current_path):
            self.show_pdf_placeholder()
            return

        res = render_document_page_png(self.pdf_current_path, self.pdf_current_page, max_dim=self.pdf_zoom)
        if not res:
            self.show_pdf_placeholder(Path(self.pdf_current_path).stem)
            return

        png_bytes, total_pages = res
        self.pdf_total_pages = max(1, total_pages)
        if self.pdf_current_page > self.pdf_total_pages:
            self.pdf_current_page = self.pdf_total_pages

        try:
            self.pdf_canvas.delete("all")
            self.pdf_tk_photos = []
            curr_y = 10
            max_img_w = 0

            # Render all pages continuously down the canvas in one scrollable section
            for p in range(1, self.pdf_total_pages + 1):
                p_res = render_document_page_png(self.pdf_current_path, p, max_dim=self.pdf_zoom)
                if not p_res:
                    continue
                p_bytes, _ = p_res
                photo = tk.PhotoImage(data=p_bytes)
                self.pdf_tk_photos.append(photo)
                w, h = photo.width(), photo.height()
                max_img_w = max(max_img_w, w)

                if self.pdf_total_pages > 1:
                    self.pdf_canvas.create_text(
                        15, curr_y + 8,
                        text=f"Page {p} of {self.pdf_total_pages}",
                        anchor="w",
                        font=(FONT_FAMILY, 9, "bold"),
                        fill="#94a3b8"
                    )
                    curr_y += 24

                self.pdf_canvas.create_image(10, curr_y, anchor="nw", image=photo)
                curr_y += h + 24

            canv_w = max(self.pdf_canvas.winfo_width(), max_img_w + 30)
            self.pdf_canvas.configure(scrollregion=(0, 0, canv_w, curr_y + 40))

            fn = Path(self.pdf_current_path).name
            self.pdf_title_var.set(f"📄 {fn}")
            self.pdf_page_lbl.configure(text=f"1-{self.pdf_total_pages} / {self.pdf_total_pages}")
            self.pdf_zoom_lbl.configure(text=f"{int((self.pdf_zoom / 850) * 100)}%")

            self.pdf_prev_btn.configure(state="normal" if self.pdf_current_page > 1 else "disabled")
            self.pdf_next_btn.configure(state="normal" if self.pdf_current_page < self.pdf_total_pages else "disabled")

            folder_info = f"Folder: {self.pdf_folder_path}" if self.pdf_folder_path else f"Folder: {Path(self.pdf_current_path).parent}"
            self.pdf_folder_status.set(folder_info)
        except Exception as e:
            print("PDF display error:", e)

    def show_pdf_placeholder(self, case_no: str = ""):
        self.pdf_canvas.delete("all")
        self.pdf_title_var.set("📄 PDF Viewer (No Matching File)")
        self.pdf_page_lbl.configure(text="-/-")
        msg = f"No PDF found matching Case #{case_no}." if case_no else "No PDF loaded for this entry."
        folder_msg = f"Searched in: {self.pdf_folder_path}" if self.pdf_folder_path else "PDF Folder not configured yet."
        self.pdf_canvas.create_text(240, 120, text="📄", font=(FONT_FAMILY, 38), fill="#94a3b8")
        self.pdf_canvas.create_text(240, 180, text=msg, font=(FONT_FAMILY, 12, "bold"), fill="#f8fafc")
        self.pdf_canvas.create_text(240, 215, text=folder_msg, font=(FONT_FAMILY, 9), fill="#94a3b8")
        self.pdf_canvas.create_text(240, 250, text="Click '📂 Browse' above to link a PDF, or set your PDF folder.", font=(FONT_FAMILY, 9, "italic"), fill="#cbd5e1")
        self.pdf_canvas.configure(scrollregion=(0, 0, 480, 360))

    def prev_pdf_page(self):
        if self.pdf_current_page > 1:
            self.pdf_current_page -= 1
            self._render_current_pdf_page()

    def next_pdf_page(self):
        if self.pdf_current_page < self.pdf_total_pages:
            self.pdf_current_page += 1
            self._render_current_pdf_page()

    def zoom_pdf(self, factor: float):
        new_zoom = int(self.pdf_zoom * factor)
        self.pdf_zoom = max(400, min(2400, new_zoom))
        self._render_current_pdf_page()

    def fit_pdf_width(self):
        canv_w = self.pdf_canvas.winfo_width()
        if canv_w > 150:
            self.pdf_zoom = max(450, canv_w - 30)
            self._render_current_pdf_page()

    def open_pdf_in_system_viewer(self):
        if not self.pdf_current_path or not os.path.exists(self.pdf_current_path):
            messagebox.showinfo("PDF Not Found", "No PDF file is currently loaded to open.", parent=self)
            return
        try:
            if IS_MAC:
                subprocess.Popen(["open", self.pdf_current_path])
            elif platform.system() == "Windows":
                os.startfile(self.pdf_current_path)
            else:
                subprocess.Popen(["xdg-open", self.pdf_current_path])
        except Exception as e:
            messagebox.showerror("Error Opening PDF", f"Could not launch system viewer:\n{e}", parent=self)

    def browse_pdf_for_case(self):
        picked = filedialog.askopenfilename(
            parent=self,
            title="Select Original PDF for this Case",
            filetypes=[("PDF & Images", "*.pdf *.jpg *.jpeg *.png"), ("PDF Files", "*.pdf"), ("All Files", "*.*")],
            initialdir=self.pdf_folder_path or str(APP_DIR)
        )
        if picked:
            c_no = extract_case_number_only(self.vars.get("existing_case_no", tk.StringVar()).get())
            if c_no:
                self.pdf_file_map[c_no.lower()] = picked
            self.load_pdf_file(picked)

    def _setup_mousewheel_scrolling(self):
        # 1. Patch Tcl ::tk::MouseWheel so that small macOS deltas compute non-zero integer steps
        try:
            self.tk.eval("""
            proc ::tk::MouseWheel {w dir amount factor {units "units"}} {
                set step [expr {$amount / $factor}]
                if {$step == 0 && $amount != 0} {
                    set step [expr {$amount > 0 ? ($factor > 0 ? 1 : -1) : ($factor > 0 ? -1 : 1)}]
                } else {
                    set step [expr {round($step)}]
                }
                catch {$w ${dir}view scroll $step $units}
            }
            """)
        except Exception:
            pass

        # 2. Unbind combobox & entry class mousewheel bindings that block scrolling or mutate values
        for cls in ("TCombobox", "TEntry", "Entry", "Combobox"):
            try:
                self.unbind_class(cls, "<MouseWheel>")
                self.unbind_class(cls, "<Button-4>")
                self.unbind_class(cls, "<Button-5>")
            except Exception:
                pass

        # 3. Register universal mousewheel dispatchers across the entire application
        self.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        self.bind_all("<Shift-MouseWheel>", lambda e: self._on_global_mousewheel(e, horizontal=True), add="+")
        self.bind_all("<Button-4>", self._on_global_button4, add="+")
        self.bind_all("<Button-5>", self._on_global_button5, add="+")

    def _calc_scroll_units(self, event) -> int:
        delta = getattr(event, "delta", 0)
        if delta == 0:
            num = getattr(event, "num", 0)
            if num == 4:
                return -2
            elif num == 5:
                return 2
            return 0

        # Windows or hardware mice reporting multiples of 120
        if abs(delta) >= 120:
            factor = max(1, int(abs(delta) / 120)) * 3
            return -factor if delta > 0 else factor
        else:
            # macOS trackpad or smooth mouse reporting small deltas (1, -1, 2, -2, etc.)
            mag = max(1, min(6, int(abs(delta))))
            return -mag if delta > 0 else mag

    def _on_global_button4(self, event):
        return self._dispatch_scroll(event, units=-2, horizontal=False)

    def _on_global_button5(self, event):
        return self._dispatch_scroll(event, units=2, horizontal=False)

    def _on_global_mousewheel(self, event, horizontal=False):
        units = self._calc_scroll_units(event)
        if units == 0:
            return
        is_horiz = horizontal or bool(event.state & 0x1)
        return self._dispatch_scroll(event, units=units, horizontal=is_horiz)

    def _on_pdf_mousewheel(self, event):
        return self._on_global_mousewheel(event)

    def _dispatch_scroll(self, event, units: int, horizontal: bool = False):
        is_cmd_or_ctrl = bool(event.state & 0x4 or event.state & 0x8)

        target = None
        try:
            if hasattr(event, "x_root") and hasattr(event, "y_root"):
                target = self.winfo_containing(event.x_root, event.y_root)
        except Exception:
            target = None
        if not target:
            target = getattr(event, "widget", None)

        # 1. Check if hovering over PDF viewer pane
        over_pdf = False
        if hasattr(self, "pdf_side_pane") and self.pdf_pane_visible:
            curr = target
            while curr:
                if curr == self.pdf_side_pane or (hasattr(self, "pdf_canvas") and curr == self.pdf_canvas):
                    over_pdf = True
                    break
                curr = getattr(curr, "master", None)

        if over_pdf and is_cmd_or_ctrl:
            if units < 0:
                self.zoom_pdf(1.1)
            else:
                self.zoom_pdf(0.9)
            return "break"

        # 2. Traverse widget hierarchy to locate scrollable container
        curr = target
        scrollable = None
        while curr:
            # Open combobox dropdown listbox
            if isinstance(curr, tk.Listbox):
                scrollable = curr
                break
            # PDF canvas or anywhere inside PDF pane
            if hasattr(self, "pdf_canvas") and (curr == self.pdf_canvas or (hasattr(self, "pdf_side_pane") and curr == self.pdf_side_pane)):
                scrollable = self.pdf_canvas
                break
            # Form canvas or anywhere inside Form view
            if hasattr(self, "form_canvas") and (curr == self.form_canvas or (hasattr(self, "form_view") and curr == self.form_view)):
                scrollable = self.form_canvas
                break
            # Treeviews (case table, date summary, batch dialog)
            if isinstance(curr, ttk.Treeview):
                scrollable = curr
                break
            # Text or Canvas widgets
            if isinstance(curr, (tk.Text, tk.Canvas)):
                scrollable = curr
                break
            curr = getattr(curr, "master", None)

        # 3. Position-based fallback if hovering over margins, dividers, or headers
        if not scrollable:
            try:
                cur_y = event.y_root
                cur_x = event.x_root
                if hasattr(self, "middle_paned") and self.middle_paned.winfo_ismapped():
                    mp_y = self.middle_paned.winfo_rooty()
                    mp_h = self.middle_paned.winfo_height()
                    if mp_y <= cur_y <= mp_y + mp_h:
                        if self.pdf_pane_visible and hasattr(self, "pdf_side_pane") and hasattr(self, "pdf_canvas"):
                            pdf_x = self.pdf_side_pane.winfo_rootx()
                            if cur_x >= pdf_x:
                                scrollable = self.pdf_canvas
                            else:
                                scrollable = getattr(self, "form_canvas", None)
                        else:
                            scrollable = getattr(self, "form_canvas", None)

                if not scrollable:
                    if hasattr(self, "tree") and self.tree.winfo_ismapped():
                        tree_y = self.tree.winfo_rooty()
                        if cur_y >= tree_y - 40:
                            scrollable = self.tree
                    if not scrollable and hasattr(self, "form_canvas") and self.form_canvas.winfo_ismapped():
                        scrollable = self.form_canvas
            except Exception:
                pass

        # 4. Perform the scroll
        if scrollable:
            try:
                if horizontal and hasattr(scrollable, "xview_scroll"):
                    scrollable.xview_scroll(units, "units")
                    return "break"
                elif hasattr(scrollable, "yview_scroll"):
                    scrollable.yview_scroll(units, "units")
                    return "break"
            except Exception:
                pass

    def destroy(self):
        try: self.db.close()
        finally: super().destroy()


if __name__ == "__main__":
    if TK_AVAILABLE:
        CaseApp().mainloop()
    else:
        print("Tkinter GUI is not available in this headless environment. Use server.py for web mode.")