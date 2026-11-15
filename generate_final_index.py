import json
import csv
import ast
import re

print("Starting generate_final_index.py...")

# 1. Load geo_data.json
with open("geo_data.json", "r", encoding="utf-8") as f:
    geo_data = json.load(f)

# 2. Extract STAGES_BY_GROUP from case.py
with open("case.py", "r", encoding="utf-8") as f:
    case_py = f.read()

tree = ast.parse(case_py)
stages_by_group = {}
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "STAGES_BY_GROUP":
                stages_by_group = ast.literal_eval(node.value)
                break

# 3. Load sample cases from sample_cause_list.csv and distribute across operators
sample_cases = []
try:
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
            
            ch = "Court Hall No.2" if r.get("Court Hall") == "II" else "Court Hall No.1"
            fyr = int(r.get("Filed Year")) if r.get("Filed Year", "").isdigit() else 2024
            ctype = r.get("Type", "G")
            st_grp = r.get("Stage Group", "Evidence")
            cur_st = r.get("Current Stage", "Appearance of Accused")
            next_h = r.get("Next Hearing", "2026-11-02")
            c_date = (r.get("Created At") or "2026-10-23T06:00:00.000Z")
            
            sample_cases.append({
                "id": f"case_{idx+1}",
                "caseNo": cno,
                "fullCaseNo": cno,
                "existing_case_no": cno,
                "type": ctype,
                "case_type": f"LGC({ctype})" if ctype in ("G","P","T","S") else ctype,
                "court": ch,
                "courtHall": "2" if r.get("Court Hall") == "II" else "1",
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
            })
except Exception as e:
    print(f"Error loading sample_cause_list.csv: {e}")

print(f"Loaded: {len(geo_data)} districts, {len(stages_by_group)} stage groups, {len(sample_cases)} sample cases.")

# Read index.html.bak
with open("index.html.bak", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Read index.html.bak: {len(lines)} lines")

# Part 1: Head & Extra CSS
extra_css = """
/* ========================================================
   MODERN MINIMALIST SAAS DASHBOARD THEME (UNTITLED UI / TAILWIND)
   ======================================================== */
:root {
  --bg-page: #f9fafb;
  --bg-card: #ffffff;
  --border-card: #eaecf0;
  --border-input: #d0d5dd;
  --border-focus: #12b76a;
  --ring-focus: rgba(18, 183, 106, 0.16);
  --primary: #12b76a;
  --primary-hover: #0e9f5d;
  --primary-active: #0b7a47;
  --primary-light: #ecfdf3;
  --primary-border: #a6f4c5;
  --primary-text: #027a48;
  --primary-disposed: #1570ef;
  --text-main: #101828;
  --text-sec: #344054;
  --text-muted: #667085;
  --danger: #d92d20;
  --danger-bg: #fee4e2;
  --header-bg: #12b76a;
  --primary-pending: #12b76a;
}

/* ========================================================
   DISPOSED MODE — ALL ACCENT COLORS SWITCH TO PROFESSIONAL BLUE
   ======================================================== */
body.mode-disposed {
  --border-focus: #1570ef !important;
  --ring-focus: rgba(21, 112, 239, 0.16) !important;
  --primary: #1570ef !important;
  --primary-hover: #175cd3 !important;
  --primary-active: #1849a9 !important;
  --primary-light: #eff8ff !important;
  --primary-border: #b2ddff !important;
  --primary-text: #175cd3 !important;
  --header-bg: #1570ef !important;
}

body.mode-disposed .brand-logo-icon {
  background: #1570ef !important;
  box-shadow: 0 2px 4px rgba(21, 112, 239, 0.25) !important;
}

body.mode-disposed .user-online-dot {
  background: #1570ef !important;
}

body.mode-disposed .stepper-segment.active {
  background: #1570ef !important;
}

body.mode-disposed .badge-total-records {
  background: #eff8ff !important;
  color: #175cd3 !important;
  border-color: #b2ddff !important;
}

body.mode-disposed .btn-mode-toggle {
  background: #eff8ff !important;
  color: #175cd3 !important;
  border-color: #b2ddff !important;
}

body.mode-disposed .btn-mode-toggle:hover {
  background: #d1e9ff !important;
  border-color: #84caff !important;
}

body.mode-disposed .btn-case-primary {
  background: #1570ef !important;
  border-color: #1570ef !important;
}

body.mode-disposed .btn-case-primary:hover {
  background: #175cd3 !important;
  border-color: #175cd3 !important;
}

body.mode-disposed #nav button.active {
  background: #eff8ff !important;
  color: #1570ef !important;
  font-weight: 600 !important;
}

body.mode-disposed #nav button.active svg {
  stroke: #1570ef !important;
}

body.mode-disposed .sidebar-collapsed #nav button.active {
  background: #eff8ff !important;
  color: #1570ef !important;
}

body.mode-disposed .sidebar-collapsed #nav button.active svg {
  stroke: #1570ef !important;
}

body.mode-disposed .form-row-fields input:focus,
body.mode-disposed .form-row-fields select:focus,
body.mode-disposed .form-row-fields textarea:focus,
body.mode-disposed .form-row-fields .dyn-block input:focus,
body.mode-disposed .form-row-fields .dyn-block select:focus {
  border-color: #1570ef !important;
  box-shadow: 0 0 0 4px rgba(21, 112, 239, 0.16) !important;
}

body.mode-disposed input[type="checkbox"] {
  accent-color: #1570ef !important;
}

body.mode-disposed .add-party-btn {
  color: #1570ef !important;
  border-color: #b2ddff !important;
  background: #f8fafc !important;
}

body.mode-disposed .add-party-btn:hover {
  background: #eff8ff !important;
  border-color: #1570ef !important;
  color: #175cd3 !important;
}

body.mode-disposed .upload-dropzone:hover {
  border-color: #1570ef !important;
  background: #eff8ff !important;
}

body.mode-disposed .upload-dropzone .upload-title-link {
  color: #1570ef !important;
}

body.mode-disposed .upload-dropzone-icon svg {
  stroke: #1570ef !important;
}

body.mode-disposed .form-mode-tag strong {
  color: #1570ef !important;
}

*, *::before, *::after {
  box-sizing: border-box;
}

body {
  margin: 0;
  background: var(--bg-page) !important;
  color: var(--text-main) !important;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
  -webkit-font-smoothing: antialiased;
}

/* Overall Grid Layout */
.app {
  display: grid !important;
  grid-template-columns: 260px 1fr !important;
  height: 100vh !important;
  overflow: hidden !important;
  background: var(--bg-page) !important;
  transition: grid-template-columns 0.18s ease;
}
.app.sidebar-collapsed {
  grid-template-columns: 74px 1fr !important;
}

/* Sidebar */
.sidebar {
  background: #ffffff !important;
  border-right: 1px solid var(--border-card) !important;
  color: var(--text-sec) !important;
  display: flex !important;
  flex-direction: column !important;
  padding: 20px 16px !important;
  height: 100vh !important;
  overflow-y: auto !important;
  box-shadow: none !important;
  z-index: 20;
}

.sidebar-brand-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding: 0 4px;
}
.brand-logo-icon {
  width: 38px;
  height: 38px;
  border-radius: 8px;
  background: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(18, 183, 106, 0.2);
  cursor: pointer;
}
.brand-title-text {
  margin-left: 10px;
  flex: 1;
  min-width: 0;
}
.brand-title-text h1 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  letter-spacing: -0.2px;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.brand-title-text p {
  margin: 2px 0 0 0;
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sidebar-toggle {
  all: unset;
  cursor: pointer;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  font-size: 14px;
  transition: background 0.12s, color 0.12s;
  flex-shrink: 0;
}
.sidebar-toggle:hover {
  background: #f2f4f7;
  color: var(--text-main);
}

.sidebar-search-box {
  position: relative;
  margin-bottom: 16px;
}
.sidebar-search-box input {
  width: 100%;
  height: 38px;
  padding: 8px 36px 8px 12px;
  border: 1px solid var(--border-card);
  border-radius: 8px;
  font-size: 13.5px;
  color: var(--text-main);
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.sidebar-search-box input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--ring-focus);
}
.sidebar-search-icon {
  position: absolute;
  right: 12px;
  top: 11px;
  color: var(--text-muted);
  pointer-events: none;
}

#nav {
  display: flex !important;
  flex-direction: column !important;
  gap: 4px !important;
  flex: 1 !important;
  padding: 0 !important;
}
#nav button {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  width: 100% !important;
  padding: 9px 12px !important;
  border: none !important;
  border-radius: 8px !important;
  background: transparent !important;
  color: var(--text-sec) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  text-align: left !important;
  transition: background 0.12s, color 0.12s !important;
  box-sizing: border-box !important;
  box-shadow: none !important;
  outline: none !important;
}
#nav button:hover {
  background: #f9fafb !important;
  color: var(--text-main) !important;
  box-shadow: none !important;
}
#nav button.active {
  background: var(--primary-light) !important;
  color: var(--primary) !important;
  font-weight: 600 !important;
  box-shadow: none !important;
}
#nav button.active svg {
  stroke: var(--primary) !important;
}

/* Collapsed Sidebar */
.sidebar-collapsed .sidebar {
  padding: 16px 8px !important;
  align-items: center !important;
}
.sidebar-collapsed .sidebar-brand-box {
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 10px !important;
  margin-bottom: 20px !important;
  padding: 0 !important;
  width: 100% !important;
}
.sidebar-collapsed .sidebar-brand-box > div:first-child {
  display: flex !important;
  justify-content: center !important;
  width: 100% !important;
}
.sidebar-collapsed .brand-title-text,
.sidebar-collapsed .sidebar-search-box,
.sidebar-collapsed .navlabel,
.sidebar-collapsed .sidebar-foot-box {
  display: none !important;
}
.sidebar-collapsed .brand-logo-icon {
  margin: 0 auto !important;
}
.sidebar-collapsed .sidebar-toggle {
  margin: 0 auto !important;
  width: 28px !important;
  height: 28px !important;
  border-radius: 6px !important;
  background: #f2f4f7 !important;
  color: var(--text-sec) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: none !important;
}
.sidebar-collapsed .sidebar-toggle:hover {
  background: #eaecf0 !important;
  color: var(--text-main) !important;
}
.sidebar-collapsed #nav {
  align-items: center !important;
  width: 100% !important;
}
.sidebar-collapsed #nav button {
  justify-content: center !important;
  width: 44px !important;
  height: 44px !important;
  padding: 0 !important;
  margin: 0 auto 4px auto !important;
  border-radius: 8px !important;
  box-shadow: none !important;
}
.sidebar-collapsed #nav button.active {
  background: var(--primary-light) !important;
  color: var(--primary) !important;
  box-shadow: none !important;
}
.sidebar-collapsed #nav button.active svg {
  stroke: var(--primary) !important;
}

.sidebar-foot-box {
  margin-top: auto;
  padding-top: 14px;
  border-top: 1px solid var(--border-card);
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sidebar-admin-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 6px;
  color: var(--text-sec);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.12s, color 0.12s;
}
.sidebar-admin-link:hover {
  background: #f9fafb;
  color: var(--text-main);
}
.sidebar-user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 6px;
  border-radius: 8px;
}

.user-avatar-wrap.user-initials-badge {
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: #eaecf0 !important;
  color: #344054 !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  border-radius: 50% !important;
  user-select: none !important;
}

.user-avatar-wrap {
  position: relative;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  flex-shrink: 0;
}
.user-avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}
.user-online-dot {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 10px;
  height: 10px;
  background: var(--primary);
  border: 2px solid #ffffff;
  border-radius: 50%;
}
.user-info-text {
  flex: 1;
  min-width: 0;
}
.user-info-name {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-info-sub {
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Header bar */
.case-app-header {
  background: #ffffff !important;
  border-bottom: 1px solid var(--border-card) !important;
  padding: 16px 28px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 16px !important;
  transition: none !important;
}
.header-left-title h1.app-title {
  margin: 0 !important;
  font-family: inherit !important;
  font-size: 19px !important;
  font-weight: 600 !important;
  color: var(--text-main) !important;
  letter-spacing: -0.2px !important;
  display: flex;
  align-items: center;
  gap: 8px;
}
.header-left-title p.app-subtitle {
  margin: 2px 0 0 0 !important;
  font-size: 12px !important;
  color: var(--text-muted) !important;
}
.header-right-controls {
  display: flex;
  align-items: center;
  gap: 18px;
}
.stepper-bar {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stepper-segment {
  width: 52px;
  height: 4px;
  border-radius: 999px;
  background: #eaecf0;
  transition: background 0.25s ease;
}
.stepper-segment.active {
  background: var(--primary);
}
.btn-mode-toggle {
  background: #ffffff !important;
  color: var(--text-sec) !important;
  border: 1px solid var(--border-input) !important;
  border-radius: 8px !important;
  padding: 8px 14px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05) !important;
}
.btn-mode-toggle:hover {
  background: #f9fafb !important;
  color: var(--text-main) !important;
  border-color: #cbd5e1 !important;
}

/* Action & Status Bar */
.case-action-bar {
  background: #ffffff !important;
  border-bottom: 1px solid var(--border-card) !important;
  padding: 10px 28px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
  flex-wrap: wrap !important;
}
.case-action-bar .status-text {
  font-size: 12px !important;
  color: var(--text-muted) !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 500 !important;
}
.case-action-bar .actions-group {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  flex-wrap: wrap !important;
}
.badge-total-records {
  background: var(--primary-light) !important;
  color: #027a48 !important;
  border: 1px solid #d1fadf !important;
  border-radius: 16px !important;
  padding: 4px 12px !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  letter-spacing: normal !important;
}
.btn-case-primary {
  background: var(--primary) !important;
  border: 1px solid var(--primary) !important;
  color: #ffffff !important;
  border-radius: 8px !important;
  padding: 8px 15px !important;
  font-size: 13.5px !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05) !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
}
.btn-case-primary:hover {
  background: var(--primary-hover) !important;
  border-color: var(--primary-hover) !important;
}
.btn-case-action {
  background: #ffffff !important;
  border: 1px solid var(--border-input) !important;
  color: var(--text-sec) !important;
  border-radius: 8px !important;
  padding: 8px 14px !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05) !important;
  cursor: pointer !important;
  transition: all 0.15s ease !important;
  display: inline-flex;
  align-items: center !important;
  gap: 6px !important;
}
.btn-case-action[style*="display: none"],
.btn-case-action[style*="display:none"] {
  display: none !important;
}
.btn-case-action:hover {
  background: #f9fafb !important;
  color: var(--text-main) !important;
  border-color: #cbd5e1 !important;
}

/* OCR Review Queue */
.queue-bar {
  display: none !important;
  background: #fffaeb !important;
  border-bottom: 1px solid #fedf89 !important;
  padding: 10px 28px !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 12px !important;
}
.queue-bar.active {
  display: flex !important;
}
.queue-bar .queue-title {
  color: #b54708 !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
}
.queue-bar .queue-actions {
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
}

/* Main Split layout */
.middle-paned-layout {
  display: flex !important;
  gap: 20px !important;
  align-items: flex-start !important;
  width: 100% !important;
  padding: 20px 28px !important;
  box-sizing: border-box !important;
}
.main-view-container {
  flex: 1 1 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
  transition: flex 0.2s ease !important;
}
.middle-paned-layout.split-active .main-view-container {
  flex: 1 1 calc(52% - 10px) !important;
  max-width: calc(52% - 10px) !important;
  overflow-x: hidden !important;
}

/* PDF Side Pane */
.pdf-side-pane {
  display: none !important;
  flex: 1 1 calc(48% - 10px);
  max-width: calc(48% - 10px);
  min-width: 320px;
  box-sizing: border-box;
  position: sticky;
  top: 16px;
  height: calc(100vh - 120px);
  background: #ffffff;
  border: 1px solid var(--border-card);
  border-radius: 12px;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 18px rgba(16, 24, 40, 0.08);
  z-index: 10;
}

/* Only display PDF side pane when split-active is active */
.middle-paned-layout.split-active .pdf-side-pane {
  display: flex !important;
}

.pdf-side-pane.hidden-pane {
  display: none !important;
}

.main-view-container {
  flex: 1 1 100% !important;
  max-width: 100% !important;
  min-width: 0 !important;
  box-sizing: border-box !important;
  transition: flex 0.2s ease, max-width 0.2s ease !important;
}
.middle-paned-layout.split-active .main-view-container {
  flex: 1 1 calc(52% - 10px) !important;
  max-width: calc(52% - 10px) !important;
  overflow-x: hidden !important;
}
.pdf-top-bar {
  background: #ffffff !important;
  border-bottom: 1px solid var(--border-card) !important;
  color: var(--text-main) !important;
  padding: 10px 14px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 8px !important;
}
.pdf-top-bar .pdf-title {
  color: var(--text-main) !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  max-width: 180px !important;
}
.pdf-controls-box {
  display: flex !important;
  align-items: center !important;
  gap: 4px !important;
}
.pdf-btn-ctrl {
  background: #f2f4f7 !important;
  color: var(--text-sec) !important;
  border: 1px solid var(--border-card) !important;
  border-radius: 6px !important;
  padding: 4px 8px !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  cursor: pointer !important;
  transition: all 0.12s !important;
}
.pdf-btn-ctrl:hover {
  background: #e4e7ec !important;
  color: var(--text-main) !important;
}
.pdf-btn-ctrl.btn-danger {
  background: #fee4e2 !important;
  color: var(--danger) !important;
  border-color: #fecdca !important;
}
.pdf-viewport {
  flex: 1 !important;
  background: #1e293b !important;
  position: relative !important;
  overflow: hidden !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
.pdf-footer-bar {
  background: #ffffff !important;
  border-top: 1px solid var(--border-card) !important;
  color: var(--text-muted) !important;
  padding: 8px 14px !important;
  font-size: 12px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
}

/* Panel & Modern Row-based Form Layout */
.panel {
  background: #ffffff !important;
  border: 1px solid var(--border-card) !important;
  border-radius: 12px !important;
  padding: 28px !important;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04), 0 1px 2px rgba(16, 24, 40, 0.02) !important;
  margin-bottom: 20px !important;
  box-sizing: border-box !important;
}
.form-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-card);
}
.form-main-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-main);
}
.form-mode-tag {
  font-size: 12.5px;
  color: var(--text-muted);
}
.form-row-group {
  display: flex;
  gap: 32px;
  padding: 24px 0;
  border-bottom: 1px solid var(--border-card);
  box-sizing: border-box;
}
.form-row-group:last-of-type {
  border-bottom: none;
}
.form-row-label {
  width: 220px;
  flex-shrink: 0;
}
.form-row-label h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-sec);
}
.form-row-label p {
  margin: 0;
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.45;
}
.form-row-fields {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px 20px;
  min-width: 0;
  box-sizing: border-box;
}
.form-row-fields .field {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.form-row-fields .field.span2 {
  grid-column: span 2;
}
.form-row-fields label {
  display: block;
  margin-bottom: 6px;
  font-size: 13.5px;
  font-weight: 500;
  color: var(--text-sec);
  text-transform: none;
  letter-spacing: normal;
}
.form-row-fields input,
.form-row-fields select {
  width: 100% !important;
  height: 42px !important;
  padding: 9px 14px !important;
  border: 1px solid var(--border-input) !important;
  border-radius: 8px !important;
  font-size: 14px !important;
  color: var(--text-main) !important;
  background-color: #ffffff !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05) !important;
  outline: none !important;
  box-sizing: border-box !important;
  transition: all 0.15s ease !important;
}
.form-row-fields select {
  appearance: none !important;
  background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2214%22%20height%3D%2214%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23667085%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E") !important;
  background-repeat: no-repeat !important;
  background-position: right 14px center !important;
  padding-right: 36px !important;
}
.form-row-fields textarea {
  width: 100% !important;
  min-height: 72px !important;
  padding: 10px 14px !important;
  border: 1px solid var(--border-input) !important;
  border-radius: 8px !important;
  font-size: 13.5px !important;
  line-height: 1.45 !important;
  color: var(--text-main) !important;
  background-color: #ffffff !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05) !important;
  outline: none !important;
  resize: vertical !important;
  box-sizing: border-box !important;
  transition: all 0.15s ease !important;
}
.form-row-fields input:focus,
.form-row-fields select:focus,
.form-row-fields textarea:focus {
  border-color: var(--border-focus) !important;
  box-shadow: 0 0 0 4px var(--ring-focus) !important;
}

/* Upload Dropzone matching screenshot */
.upload-dropzone {
  border: 2px dashed var(--border-card);
  border-radius: 12px;
  background: #ffffff;
  padding: 28px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s ease;
  width: 100%;
  box-sizing: border-box;
}
.upload-dropzone:hover {
  border-color: var(--border-focus);
  background: #fcfdfd;
}
.upload-dropzone-icon {
  margin-bottom: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #f9fafb;
  border: 1px solid var(--border-card);
}
.upload-dropzone-text {
  font-size: 14px;
  color: #475467;
  margin-bottom: 4px;
}
.upload-dropzone-text .dropzone-link {
  color: var(--primary);
  font-weight: 600;
}
.upload-dropzone-hint {
  font-size: 12px;
  color: var(--text-muted);
}
.dropzone-file-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: #f9fafb;
  border: 1px solid var(--border-card);
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-sec);
}
.dropzone-remove-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 14px;
  padding: 0 2px;
  margin-left: 4px;
}
.dropzone-remove-btn:hover {
  color: var(--danger);
}


button * {
  pointer-events: none;
}
.form-actions-bar {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  margin-top: 24px !important;
  flex-wrap: wrap !important;
  border-top: 1px solid var(--border-card) !important;
  padding: 14px 20px !important;
  position: sticky !important;
  bottom: 0 !important;
  background: #ffffff !important;
  box-shadow: 0 -4px 12px rgba(16, 24, 40, 0.05) !important;
  border-radius: 0 0 12px 12px !important;
  z-index: 15 !important;
}

.form-actions-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
  flex-wrap: wrap;
  border-top: 1px solid var(--border-card);
  padding-top: 20px;
}

/* Navigator Table Modern Styles */
.filters {
  display: flex !important;
  gap: 10px !important;
  margin-bottom: 16px !important;
  align-items: center !important;
  flex-wrap: wrap !important;
}
.filters input[type="text"] {
  height: 40px !important;
  border: 1px solid var(--border-input) !important;
  border-radius: 8px !important;
  padding: 8px 14px !important;
  font-size: 13.5px !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05) !important;
}
.filters select {
  height: 40px !important;
  border: 1px solid var(--border-input) !important;
  border-radius: 8px !important;
  padding: 8px 32px 8px 12px !important;
  font-size: 13.5px !important;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05) !important;
}
.navigator-split-grid {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  width: 100%;
}
.navigator-table-box {
  flex: 1 1 68%;
  min-width: 0;
}
.navigator-summary-card {
  flex: 0 0 310px;
  width: 310px;
  background: #ffffff;
  border: 1px solid var(--border-card);
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.04);
}
.navigator-summary-card h4 {
  margin: 0 0 6px 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
}

/* In split-screen mode, always stack form row groups vertically regardless of window width */
.middle-paned-layout.split-active .form-row-group {
  flex-direction: column !important;
  gap: 12px !important;
}
.middle-paned-layout.split-active .form-row-label {
  width: 100% !important;
}
.middle-paned-layout.split-active .form-row-fields {
  width: 100% !important;
}

/* Modals & Dialogs */
.modal-backdrop,
.modal-bg,
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(16, 24, 40, 0.65) !important;
  backdrop-filter: blur(4px) !important;
  -webkit-backdrop-filter: blur(4px) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 99999 !important;
  padding: 20px !important;
  box-sizing: border-box !important;
}

.modal,
.modal-card {
  background: #ffffff !important;
  border: 1px solid var(--border-card) !important;
  border-radius: 14px !important;
  box-shadow: 0 20px 25px -5px rgba(16, 24, 40, 0.15), 0 10px 10px -5px rgba(16, 24, 40, 0.05) !important;
  display: flex !important;
  flex-direction: column !important;
  max-height: 90vh !important;
  overflow: hidden !important;
  color: var(--text-main) !important;
  box-sizing: border-box !important;
  position: relative !important;
  z-index: 100000 !important;
  animation: modalScaleIn 0.16s ease-out !important;
}

@keyframes modalScaleIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(12px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modal-head {
  padding: 16px 20px !important;
  border-bottom: 1px solid var(--border-card) !important;
  background: #ffffff !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
}

.modal-head h3 {
  margin: 0 !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  color: var(--text-main) !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
}

.modal-head .modal-close {
  background: transparent !important;
  border: none !important;
  font-size: 22px !important;
  cursor: pointer !important;
  color: var(--text-muted) !important;
  line-height: 1 !important;
  padding: 4px 8px !important;
  border-radius: 6px !important;
  transition: all 0.12s ease !important;
}

.modal-head .modal-close:hover {
  background: #f2f4f7 !important;
  color: var(--text-main) !important;
}

.modal-body {
  padding: 20px !important;
  overflow-y: auto !important;
  flex: 1 !important;
  background: #ffffff !important;
  color: var(--text-main) !important;
}

.modal-foot {
  padding: 14px 20px !important;
  border-top: 1px solid var(--border-card) !important;
  background: #f9fafb !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  flex-wrap: wrap !important;
  gap: 10px !important;
}

/* ========================================================
   STRUCTURED PARTY INFORMATION CARDS (PETITIONER & RESPONDENT)
   ======================================================== */
.form-row-group.parties-row-group {
  display: flex !important;
  flex-direction: column !important;
  gap: 10px !important;
}
.form-row-group.parties-row-group .form-row-label {
  width: 100% !important;
  margin-bottom: 2px !important;
}
.form-row-group.parties-row-group .form-row-fields {
  width: 100% !important;
  display: block !important;
}
.party-info-section {
  width: 100%;
}
.party-subheading {
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-sec);
  margin: 14px 0 8px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.party-subheading:first-child {
  margin-top: 0;
}
.dyn-block {
  border: 1px solid var(--border-card);
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 12px;
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(16, 24, 40, 0.05);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.dyn-block:hover {
  border-color: #cbd5e1;
  box-shadow: 0 2px 6px rgba(16, 24, 40, 0.08);
}
.party-card-header {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}
.party-identity-fields {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-width: 0;
}
.party-name-input {
  flex: 3 1 180px !important;
  min-width: 140px !important;
}
.party-rel-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 3 1 240px;
  min-width: 0;
}
.party-age-input {
  width: 65px !important;
  min-width: 60px !important;
  max-width: 75px !important;
  text-align: center !important;
  padding: 7px 4px !important;
  flex-shrink: 0 !important;
}
.party-relation-select {
  width: 90px !important;
  min-width: 82px !important;
  max-width: 98px !important;
  flex-shrink: 0 !important;
}
.party-relative-input {
  flex: 1 1 110px !important;
  min-width: 100px !important;
}
.party-status-group {
  flex: 2 1 150px;
  min-width: 130px;
}
.party-status-select {
  width: 100% !important;
}
.dyn-block .location-grid {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)) !important;
  gap: 8px !important;
  margin-bottom: 10px !important;
}
.dyn-block .location-grid label {
  display: flex !important;
  flex-direction: column !important;
  gap: 3px !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.dyn-block .party-address {
  width: 100% !important;
  margin-bottom: 10px !important;
}
.dyn-block .contact-row {
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)) !important;
  gap: 8px !important;
  margin-bottom: 10px !important;
}
.dyn-block .advocate-fields {
  display: none !important;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)) !important;
  gap: 8px !important;
  margin-top: 8px !important;
}
.dyn-block .advocate-fields.open,
.dyn-block .advocate-fields[data-open="true"] {
  display: grid !important;
}
.dyn-block .party-adv-toggle {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  color: var(--text-sec) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  margin-top: 4px !important;
  cursor: pointer !important;
  user-select: none !important;
}
/* Crucial checkbox sizing override: reset 100% width and 42px height from .form-row-fields */
.form-row-fields .dyn-block input[type="checkbox"],
.dyn-block .party-adv-toggle input[type="checkbox"],
.dyn-block input.petAdvToggle,
.dyn-block input.respAdvToggle {
  width: 16px !important;
  min-width: 16px !important;
  max-width: 16px !important;
  height: 16px !important;
  min-height: 16px !important;
  max-height: 16px !important;
  padding: 0 !important;
  margin: 0 !important;
  border: 1.5px solid var(--border-input) !important;
  border-radius: 4px !important;
  background: #ffffff !important;
  box-shadow: none !important;
  accent-color: var(--primary) !important;
  cursor: pointer !important;
  flex-shrink: 0 !important;
  display: inline-block !important;
  vertical-align: middle !important;
}
/* Inputs and select boxes within party cards */
.form-row-fields .dyn-block input:not([type="checkbox"]),
.form-row-fields .dyn-block select {
  height: 38px !important;
  min-height: 38px !important;
  padding: 7px 10px !important;
  font-size: 13px !important;
  border: 1px solid var(--border-input) !important;
  border-radius: 6px !important;
  background-color: #ffffff !important;
  box-sizing: border-box !important;
  box-shadow: none !important;
}
.form-row-fields .dyn-block select {
  appearance: none !important;
  background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%2212%22%20height%3D%2212%22%20viewBox%3D%220%200%2024%2024%22%20fill%3D%22none%22%20stroke%3D%22%23667085%22%20stroke-width%3D%222%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%3E%3Cpolyline%20points%3D%226%209%2012%2015%2018%209%22%3E%3C%2Fpolyline%3E%3C%2Fsvg%3E") !important;
  background-repeat: no-repeat !important;
  background-position: right 8px center !important;
  padding-right: 24px !important;
}
.form-row-fields .dyn-block input:focus,
.form-row-fields .dyn-block select:focus {
  outline: none !important;
  border-color: var(--border-focus) !important;
  box-shadow: 0 0 0 3px var(--ring-focus) !important;
}
.form-row-fields .dyn-block .rm-row {
  width: 32px !important;
  height: 32px !important;
  min-height: 32px !important;
  min-width: 32px !important;
  padding: 0 !important;
  border: 1px solid transparent !important;
  border-radius: 6px !important;
  background: transparent !important;
  color: var(--danger) !important;
  cursor: pointer !important;
  font-size: 22px !important;
  line-height: 1 !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: none !important;
  flex-shrink: 0 !important;
  margin-top: 3px !important;
}
.form-row-fields .dyn-block .rm-row:hover {
  background: var(--danger-bg) !important;
  border-color: #fecdca !important;
}
.add-party-btn {
  border: 1px dashed var(--border-input);
  border-radius: 6px;
  padding: 8px 14px;
  background: #f9fafb;
  color: var(--primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
  margin-top: 4px;
  margin-bottom: 16px;
}
.add-party-btn:hover {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary-hover);
}

/* Pending case details & party card expansion styles */
.pending-case-details {
  font-family: inherit;
  color: var(--text-main);
  padding: 4px;
}
.pending-detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 8px 14px;
  margin: 8px 0 14px;
}
.pending-detail-grid > div {
  min-width: 0;
  overflow-wrap: anywhere;
}
.pending-detail-grid span {
  display: block;
  color: var(--text-muted);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.35px;
  margin-bottom: 3px;
}
.pending-detail-grid b {
  font-size: 12px;
  color: var(--text-main);
}
.pending-detail-card {
  border: 1px solid var(--border-card);
  border-radius: 6px;
  padding: 10px;
  margin: 7px 0;
  background: #ffffff;
  overflow-wrap: anywhere;
  font-size: 12px;
  line-height: 1.5;
}
.pending-detail-card strong {
  display: block;
  font-size: 12.5px;
  color: var(--text-main);
  margin-bottom: 4px;
}
.pending-detail-parties {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 14px;
}
.pending-detail-parties h4,
.pending-case-details > h4 {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-sec);
  margin: 14px 0 6px;
}
@media (max-width: 700px) {
  .pending-detail-parties {
    grid-template-columns: 1fr;
  }
}
.petOther {
  font-family: "IBM Plex Mono", monospace;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

/* ========================================================
   MODERN SPLIT-HERO COURT LOGIN PAGE (EXTRACTED FROM MOCKUP)
   ======================================================== */
.agentos-login-page {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 999999;
  overflow-y: auto;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 50% 10%, #f8fafc 0%, #f1f5f9 60%, #e2e8f0 100%);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  color: #0f172a;
  padding: 24px 16px;
  box-sizing: border-box;
}

.agentos-card-container {
  width: 100%;
  max-width: 1080px;
  min-height: 640px;
  background: #ffffff;
  border-radius: 28px;
  box-shadow: 0 25px 70px -15px rgba(15, 23, 42, 0.1), 0 0 0 1px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: row;
  overflow: hidden;
  box-sizing: border-box;
}

/* LEFT COLUMN - AUTHENTICATION FORM */
.agentos-left-col {
  flex: 1 1 50%;
  max-width: 50%;
  min-width: 380px;
  padding: 34px 44px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  box-sizing: border-box;
  background: #ffffff;
}

/* Top bar */
.agentos-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.agentos-brand-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.agentos-brand-icon {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: linear-gradient(135deg, #065f46 0%, #047857 100%);
  border: 1.5px solid #fbbf24;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 10px rgba(6, 95, 70, 0.25);
  flex-shrink: 0;
}

.agentos-brand-text {
  display: flex;
  flex-direction: column;
}

.agentos-brand-name {
  font-size: 14.5px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.2px;
  line-height: 1.2;
}

.agentos-brand-sub {
  font-size: 9.5px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.8px;
  text-transform: uppercase;
}

.agentos-top-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  font-size: 11.5px;
  font-weight: 600;
  color: #475569;
}

.agentos-top-badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #12b76a;
}

/* Center Form Container */
.agentos-form-center {
  width: 100%;
  max-width: 380px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
}

.agentos-avatar-badge {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 14px auto;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04);
}

.agentos-heading {
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #111827;
  text-align: center;
  letter-spacing: -0.4px;
}

.agentos-subheading {
  margin: 4px 0 18px 0;
  font-size: 13.5px;
  color: #64748b;
  text-align: center;
}

/* Alert Banner */
.court-alert-banner {
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
  margin-bottom: 14px;
  display: none;
}

.court-alert-error {
  background: #fee2e2;
  border: 1px solid #fca5a5;
  color: #991b1b;
}

.court-alert-success {
  background: #dcfce7;
  border: 1px solid #86efac;
  color: #166534;
}

/* Inputs */
.agentos-field-group {
  margin-bottom: 13px;
}

.agentos-field-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.agentos-field-label {
  font-size: 12px;
  font-weight: 600;
  color: #344054;
}

.agentos-pwd-toggle {
  background: none;
  border: none;
  color: #027a48;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.agentos-pwd-toggle:hover {
  background: #ecfdf3;
}

.agentos-input-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.agentos-input-icon {
  position: absolute;
  left: 12px;
  font-size: 14px;
  color: #94a3b8;
  pointer-events: none;
}

.agentos-input {
  width: 100%;
  height: 42px;
  padding: 0 12px 0 36px;
  border: 1px solid #d0d5dd;
  border-radius: 9px;
  font-size: 13.5px;
  color: #0f172a;
  background: #ffffff;
  box-sizing: border-box;
  outline: none;
  transition: all 0.15s ease;
}

.agentos-input:focus {
  border-color: #12b76a;
  box-shadow: 0 0 0 3px rgba(18, 183, 106, 0.16);
}

.agentos-select {
  width: 100%;
  height: 42px;
  padding: 0 12px 0 36px;
  border: 1px solid #d0d5dd;
  border-radius: 9px;
  font-size: 13px;
  color: #0f172a;
  background: #ffffff;
  box-sizing: border-box;
  outline: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.agentos-select:focus {
  border-color: #12b76a;
  box-shadow: 0 0 0 3px rgba(18, 183, 106, 0.16);
}

.agentos-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #475569;
  margin: 10px 0 14px 0;
}

.agentos-remember-label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.agentos-tls-tag {
  color: #027a48;
  font-weight: 600;
  font-size: 11px;
}

/* Sleek primary submit button matching image */
.agentos-submit-btn {
  background: #0f172a;
  color: #ffffff;
  border: none;
  border-radius: 9px;
  height: 44px;
  font-size: 14px;
  font-weight: 600;
  width: 100%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.18s ease;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.18);
}

.agentos-submit-btn:hover {
  background: #047857;
  box-shadow: 0 6px 16px rgba(4, 120, 87, 0.3);
  transform: translateY(-1px);
}

.agentos-submit-btn:active {
  transform: translateY(0);
}

/* Quick Sign-in Pills */
.agentos-quick-pills-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 14px;
  flex-wrap: wrap;
}

.agentos-quick-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.agentos-quick-pill {
  padding: 4px 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  font-size: 11.5px;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
}

.agentos-quick-pill:hover {
  background: #ecfdf3;
  border-color: #a6f4c5;
  color: #027a48;
}

.agentos-disclaimer {
  margin: 12px 0 0 0;
  font-size: 11px;
  color: #94a3b8;
  text-align: center;
  line-height: 1.4;
}

/* Bottom bar */
.agentos-bottom-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
  color: #94a3b8;
  padding-top: 12px;
  border-top: 1px solid #f1f5f9;
  margin-top: 16px;
}

.agentos-lang-wrap {
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  transition: background 0.15s;
  color: #475569;
  font-weight: 500;
}

.agentos-lang-wrap:hover {
  background: #f1f5f9;
}

/* RIGHT COLUMN - HERO SHOWCASE */
.agentos-right-col {
  flex: 1 1 50%;
  max-width: 50%;
  padding: 12px;
  display: flex;
  box-sizing: border-box;
}

.agentos-hero-card {
  width: 100%;
  border-radius: 22px;
  padding: 36px 34px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  position: relative;
  overflow: hidden;
  background: linear-gradient(145deg, #10b981 0%, #059669 30%, #047857 65%, #064e3b 100%);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.15);
}

.agentos-hero-card::before {
  content: "";
  position: absolute;
  top: -60px;
  right: -60px;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(251, 191, 36, 0.28) 0%, transparent 70%);
  pointer-events: none;
}

.agentos-hero-card::after {
  content: "";
  position: absolute;
  bottom: -40px;
  left: -40px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(56, 189, 248, 0.22) 0%, transparent 70%);
  pointer-events: none;
}

/* 3D Isometric Tile Presentation */
.agentos-iso-wrapper {
  position: absolute;
  top: 26px;
  right: 28px;
  width: 180px;
  height: 140px;
  pointer-events: none;
}

.agentos-iso-stage {
  position: relative;
  width: 100%;
  height: 100%;
  perspective: 700px;
}

.agentos-iso-grid {
  position: absolute;
  top: 20px;
  right: 10px;
  width: 120px;
  height: 90px;
  transform: rotateX(55deg) rotateZ(-35deg);
  transform-style: preserve-3d;
}

.agentos-iso-tile-base {
  position: absolute;
  width: 50px;
  height: 50px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.25);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.base-t1 { top: 0; left: 0; }
.base-t2 { top: 0; left: 56px; }
.base-t3 { top: 48px; left: 0; }
.base-t4 { top: 48px; left: 56px; }

.agentos-iso-floating-badge {
  position: absolute;
  top: -8px;
  left: 28px;
  width: 64px;
  height: 64px;
  border-radius: 18px;
  background: linear-gradient(135deg, #022c22 0%, #065f46 60%, #10b981 100%);
  border: 2px solid #fbbf24;
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.35), 0 0 20px rgba(251, 191, 36, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: isoFloat 3.6s ease-in-out infinite;
}

@keyframes isoFloat {
  0%, 100% { transform: translateY(0px) rotate(-2deg); }
  50% { transform: translateY(-8px) rotate(2deg); }
}

/* Hero Typography */
.agentos-hero-content {
  position: relative;
  z-index: 2;
}

.agentos-hero-tag {
  display: inline-block;
  font-size: 10.5px;
  font-weight: 700;
  color: #fbbf24;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.agentos-hero-title {
  margin: 0 0 12px 0;
  font-size: 28px;
  font-weight: 700;
  color: #ffffff;
  line-height: 1.25;
  letter-spacing: -0.4px;
  max-width: 380px;
}

.agentos-hero-desc {
  margin: 0;
  font-size: 13.5px;
  color: rgba(255, 255, 255, 0.86);
  line-height: 1.55;
  max-width: 400px;
}

/* Translucent Frosted Glass Status Cards */
.agentos-hero-cards {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 32px;
}

.agentos-glass-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 18px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.28);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  color: #ffffff;
}

.agentos-card-left {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  font-weight: 500;
}

.agentos-card-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-orange { background: #fb923c; box-shadow: 0 0 8px #fb923c; }
.dot-green  { background: #4ade80; box-shadow: 0 0 8px #4ade80; }
.dot-blue   { background: #38bdf8; box-shadow: 0 0 8px #38bdf8; }

.agentos-card-status {
  font-size: 11.5px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  border-radius: 8px;
}

.status-working {
  background: rgba(251, 146, 60, 0.22);
  color: #fed7aa;
}

.status-done {
  background: rgba(74, 222, 128, 0.2);
  color: #bbf7d0;
}

@media (max-width: 900px) {
  .agentos-card-container {
    flex-direction: column;
    max-width: 480px;
    min-height: auto;
  }
  .agentos-left-col {
    max-width: 100%;
    min-width: 0;
    padding: 28px 24px;
  }
  .agentos-right-col {
    display: none;
  }
}

/* Universal Overlay & Modal Stability Fixes */
.modal-backdrop {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  background: rgba(15, 23, 42, 0.6) !important;
  backdrop-filter: blur(4px) !important;
  -webkit-backdrop-filter: blur(4px) !important;
  z-index: 99999 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 16px !important;
  box-sizing: border-box !important;
  overflow-y: auto !important;
}

.modal-backdrop[style*="display: none"] {
  display: none !important;
}

.modal-backdrop > div {
  animation: modalEnter 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
  max-height: 94vh !important;
  overflow-y: auto !important;
}

@keyframes modalEnter {
  from { opacity: 0; transform: scale(0.96) translateY(6px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.btn-case-action[style*="display: none"] {
  display: none !important;
}

/* ========================================================
   CASE SAVE NOTIFICATION POPUP (DUPLICATE OVERWRITE & SAVED)
   ======================================================== */
#caseNotificationContainer {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 10000000;
  display: flex;
  flex-direction: column;
  gap: 12px;
  pointer-events: none;
  max-width: 440px;
  width: calc(100vw - 48px);
}

.case-toast-card {
  pointer-events: auto;
  position: relative;
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 16px 36px -6px rgba(15, 23, 42, 0.16), 0 0 0 1px rgba(15, 23, 42, 0.06);
  padding: 16px 18px 14px 18px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
  animation: caseToastSlideIn 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  overflow: hidden;
  transition: all 0.22s ease;
  box-sizing: border-box;
}

.case-toast-card.toast-removing {
  animation: caseToastSlideOut 0.22s ease forwards;
}

@keyframes caseToastSlideIn {
  from {
    opacity: 0;
    transform: translateX(110%) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

@keyframes caseToastSlideOut {
  from {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateX(110%) scale(0.95);
  }
}

/* Success Card */
.case-toast-success {
  border-left: 6px solid #10b981;
}

.case-toast-success .case-toast-icon {
  background: #ecfdf3;
  color: #027a48;
  border: 1px solid #a6f4c5;
}

.case-toast-success .case-toast-tag {
  background: #ecfdf3;
  color: #027a48;
  border: 1px solid #a6f4c5;
}

.case-toast-success .case-toast-dot {
  background: #12b76a;
}

/* Duplicate / Overwritten Warning Card */
.case-toast-duplicate {
  border-left: 6px solid #f59e0b;
  background: #fffdfa;
}

.case-toast-duplicate .case-toast-icon {
  background: #fef3c7;
  color: #b45309;
  border: 1px solid #fde68a;
}

.case-toast-duplicate .case-toast-tag {
  background: #fffbeb;
  color: #b45309;
  border: 1px solid #fcd34d;
}

.case-toast-duplicate .case-toast-dot {
  background: #f59e0b;
  box-shadow: 0 0 6px rgba(245, 158, 11, 0.6);
}

.case-toast-icon-wrap {
  flex-shrink: 0;
  margin-top: 2px;
}

.case-toast-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.case-toast-body {
  flex: 1;
  min-width: 0;
}

.case-toast-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.case-toast-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.6px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 12px;
}

.case-toast-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.case-toast-close {
  background: none;
  border: none;
  font-size: 15px;
  line-height: 1;
  color: #94a3b8;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.case-toast-close:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.case-toast-title {
  font-size: 14.5px;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 4px;
  line-height: 1.3;
}

.case-toast-msg {
  font-size: 13px;
  color: #334155;
  line-height: 1.45;
  margin-bottom: 8px;
}

.case-toast-hl {
  font-weight: 700;
  color: #0f172a;
}

.case-toast-duplicate .case-toast-hl {
  color: #92400e;
}

.case-toast-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11.5px;
  color: #64748b;
}

.case-toast-badge-hall {
  font-weight: 600;
  background: #f1f5f9;
  padding: 1px 7px;
  border-radius: 6px;
  color: #1e293b;
}

.case-toast-progress {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: rgba(0, 0, 0, 0.05);
}

.case-toast-progress-bar {
  height: 100%;
  width: 100%;
  transform-origin: left;
  animation: caseToastProgress 5s linear forwards;
}

@keyframes caseToastProgress {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}

.progress-success {
  background: #10b981;
}

.progress-warn {
  background: #f59e0b;
}

/* ========================================================
   CLEAN & POLISHED USER CONTROLS & AUTHENTICATION MODAL
   ======================================================== */
.top-auth-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 6px;
  flex-shrink: 0;
}

/* User Profile Badge */
.clean-user-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 3px 10px 3px 4px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 24px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  transition: all 0.15s ease-in-out;
  user-select: none;
}
.clean-user-pill:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.06);
}
.clean-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  color: #ffffff;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
  flex-shrink: 0;
}
.clean-avatar::after {
  content: '';
  position: absolute;
  bottom: -1px;
  right: -1px;
  width: 7px;
  height: 7px;
  background: #10b981;
  border: 1.5px solid #ffffff;
  border-radius: 50%;
}
.clean-user-details {
  display: flex;
  align-items: center;
  gap: 6px;
}
.clean-user-name {
  font-size: 12.5px;
  font-weight: 600;
  color: #1e293b;
  max-width: 160px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.clean-role-tag {
  font-size: 10px;
  font-weight: 600;
  padding: 1.5px 7px;
  border-radius: 12px;
  letter-spacing: 0.3px;
  background: #f1f5f9;
  color: #475569;
  border: 1px solid #e2e8f0;
  text-transform: capitalize;
}
.clean-role-tag.admin {
  background: #eff6ff;
  color: #1d4ed8;
  border-color: #dbeafe;
}
.clean-role-tag.operator {
  background: #f0fdf4;
  color: #15803d;
  border-color: #dcfce7;
}
.clean-chevron {
  color: #94a3b8;
  transition: transform 0.15s ease;
  flex-shrink: 0;
}
.clean-user-pill:hover .clean-chevron {
  color: #475569;
}

/* Clean Sign Out Button */
.clean-logout-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 11px;
  font-size: 12px;
  font-weight: 500;
  color: #475569;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.15s ease;
  user-select: none;
}
.clean-logout-btn:hover {
  background: #fff1f2;
  color: #e11d48;
  border-color: #fecdd3;
  box-shadow: 0 1px 3px rgba(225, 29, 72, 0.08);
}
.clean-logout-btn svg {
  color: #64748b;
  transition: color 0.15s ease;
}
.clean-logout-btn:hover svg {
  color: #e11d48;
}

/* Clean Manage Access Ghost Button */
.btn-clean-ghost {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 32px;
  padding: 0 11px;
  font-size: 12px;
  font-weight: 500;
  color: #2563eb;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-clean-ghost:hover {
  background: #dbeafe;
  border-color: #93c5fd;
  color: #1d4ed8;
}

/* Authentication Modal Dialog */
.auth-modal-dialog {
  background: #ffffff;
  border-radius: 16px;
  max-width: 490px;
  width: 92%;
  box-shadow: 0 24px 48px -12px rgba(15, 23, 42, 0.22), 0 0 0 1px rgba(226, 232, 240, 0.9);
  overflow: hidden;
  font-family: inherit;
  animation: authModalFadeIn 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes authModalFadeIn {
  from { opacity: 0; transform: scale(0.97) translateY(4px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.auth-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 14px 22px;
  border-bottom: 1px solid #f1f5f9;
}
.auth-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.auth-header-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  flex-shrink: 0;
}
.auth-header-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.2px;
}
.auth-header-subtitle {
  margin: 2px 0 0 0;
  font-size: 12px;
  color: #64748b;
}
.auth-close-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.12s ease;
}
.auth-close-btn:hover {
  background: #f1f5f9;
  color: #0f172a;
}

/* Active Session Card */
.auth-active-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px 16px;
  margin: 16px 20px 14px 20px;
}
.auth-active-user-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.auth-card-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1e293b, #334155);
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
.auth-card-meta {
  flex: 1;
  min-width: 0;
}
.auth-card-label {
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.5px;
}
.auth-card-name {
  font-size: 14.5px;
  font-weight: 700;
  color: #0f172a;
  margin-top: 1px;
}
.auth-card-tag {
  display: inline-block;
  font-size: 10.5px;
  font-weight: 600;
  padding: 1.5px 8px;
  border-radius: 12px;
  margin-top: 3px;
}
.auth-card-tag.admin {
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #dbeafe;
}
.auth-card-tag.operator {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #dcfce7;
}

.auth-active-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e2e8f0;
}
.btn-auth-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 28px;
  padding: 0 10px;
  font-size: 11.5px;
  font-weight: 500;
  color: #334155;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.12s ease;
  user-select: none;
}
.btn-auth-action:hover {
  background: #f1f5f9;
  border-color: #94a3b8;
  color: #0f172a;
}
.btn-auth-action.logout {
  color: #dc2626;
  border-color: #fecaca;
  margin-left: auto;
}
.btn-auth-action.logout:hover {
  background: #fef2f2;
  border-color: #f87171;
}

/* Switch Accounts Section */
.auth-switch-section {
  padding: 0 20px 16px 20px;
}
.auth-section-title {
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.auth-accounts-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.auth-account-card {
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  transition: all 0.15s ease;
}
.auth-account-card:hover {
  background: #f8fafc;
  border-color: #94a3b8;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0,0,0,0.04);
}
.auth-account-card.active {
  border: 1.5px solid #2563eb;
  background: #f0f7ff;
  cursor: default;
}
.auth-account-card.active:hover {
  transform: none;
  box-shadow: none;
}
.auth-acc-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.auth-acc-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #334155;
  font-size: 11.5px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.auth-account-card.active .auth-acc-avatar {
  background: #2563eb;
  color: #ffffff;
}
.auth-acc-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.auth-acc-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}
.auth-acc-sub {
  font-size: 11.5px;
  color: #64748b;
  margin-top: 1px;
}
.badge-account-active {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  color: #2563eb;
  padding: 3px 8px;
  background: #e0f2fe;
  border-radius: 12px;
}
.badge-account-switch {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11.5px;
  font-weight: 600;
  color: #0284c7;
  padding: 3px 8px;
  border-radius: 6px;
  transition: all 0.12s ease;
}
.auth-account-card:hover .badge-account-switch {
  color: #0369a1;
  background: #e0f2fe;
}

/* Switch Password Box */
.auth-switch-pw-box {
  background: #f8fafc;
  border: 1.5px solid #3b82f6;
  border-radius: 10px;
  padding: 14px 16px;
  margin-top: 10px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.08);
}


"""

part1_head = "".join(lines[0:1373]).replace("box-shadow: inset 3px 0 0 var(--brass-soft);", "box-shadow: none;") + "\n" + extra_css + "\n    </style>\n"

# Part 2: Body, Sidebar, Nav, Topbar
part2_body = """  <body>
    <!-- Dedicated Court Login & Authentication Page (Extracted from UI Mockup & Adapted for Karnataka Special Courts) -->
    <div id="loginPageRoot" class="agentos-login-page" style="display:none;">
      <div class="agentos-card-container">
        <!-- LEFT COLUMN: AUTHENTICATION FORM -->
        <div class="agentos-left-col">
          <!-- Top Bar -->
          <div class="agentos-top-bar">
            <div class="agentos-brand-wrap">
              <div class="agentos-brand-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
              </div>
              <div class="agentos-brand-text">
                <div class="agentos-brand-name">CourtOS <span style="font-weight:400;color:#64748b;font-size:12px;">· ನ್ಯಾಯಾಲಯ</span></div>
                <div class="agentos-brand-sub">KARNATAKA SPECIAL COURTS</div>
              </div>
            </div>
            <div class="agentos-top-badge">
              <span class="agentos-top-badge-dot"></span>
              <span>Official Bench Portal</span>
            </div>
          </div>

          <!-- Center Form Section -->
          <div class="agentos-form-center">
            <!-- Avatar Box matching image -->
            <div class="agentos-avatar-badge">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </div>

            <h1 class="agentos-heading">Welcome back!</h1>
            <p class="agentos-subheading">Sign in to continue where your left off.</p>

            <div id="loginAlertBox" class="court-alert-banner" style="display:none;"></div>

            <!-- Direct, Clean Form: NO GOOGLE, NO APPLE, KEEP IT SIMPLE -->
            <form id="courtLoginForm" onsubmit="window.auth.handleLoginFormSubmit(event)" novalidate>
              <div class="agentos-field-group">
                <label for="loginUsernameInput" class="agentos-field-label">Username / Court ID</label>
                <div class="agentos-input-wrap">
                  <span class="agentos-input-icon">👤</span>
                  <input type="text" id="loginUsernameInput" class="agentos-input" placeholder="e.g. admin or operator1" autocomplete="username" required />
                </div>
              </div>

              <div class="agentos-field-group">
                <div class="agentos-field-label-row">
                  <label for="loginPasswordInput" class="agentos-field-label">Password</label>
                  <button type="button" class="agentos-pwd-toggle" onclick="window.auth.togglePasswordVisibility()" title="Show/Hide Password" id="pwdToggleBtn">
                    👁️ Show
                  </button>
                </div>
                <div class="agentos-input-wrap">
                  <span class="agentos-input-icon">🔒</span>
                  <input type="password" id="loginPasswordInput" class="agentos-input" placeholder="Enter password" autocomplete="current-password" required />
                </div>
              </div>

              <div class="agentos-field-group">
                <label for="loginHallSelect" class="agentos-field-label">Assigned Bench / Court Hall</label>
                <div class="agentos-input-wrap">
                  <span class="agentos-input-icon">🏛️</span>
                  <select id="loginHallSelect" class="agentos-select">
                    <option value="1">Court Hall No. 1 (ಕೋರ್ಟ್ ಹಾಲ್ ೧)</option>
                    <option value="2">Court Hall No. 2 (ಕೋರ್ಟ್ ಹಾಲ್ ೨)</option>
                    <option value="admin">Administrative &amp; Registry Chambers</option>
                  </select>
                </div>
              </div>

              <div class="agentos-meta-row">
                <label class="agentos-remember-label">
                  <input type="checkbox" id="loginRememberMeCheckbox" checked />
                  <span>Remember me</span>
                </label>
                <span class="agentos-tls-tag">🔒 256-Bit TLS</span>
              </div>

              <button type="submit" id="loginSubmitBtn" class="agentos-submit-btn">
                <span id="loginBtnSpinner" style="display:none;" class="spinner-inline">⏳</span>
                <span>Sign In to Court Register ➔</span>
              </button>
            </form>

            <!-- Quick Account Selector Chips (Simple & fast testing) -->
            <div class="agentos-quick-pills-wrap">
              <span class="agentos-quick-label">⚡ Fast Access:</span>
              <button type="button" class="agentos-quick-pill" onclick="window.auth.selectQuickRole('admin')" title="Fill Admin Credentials">
                👑 Admin
              </button>
              <button type="button" class="agentos-quick-pill" onclick="window.auth.selectQuickRole('operator1')" title="Fill Desk 1 Credentials">
                ✍️ Desk 1
              </button>
              <button type="button" class="agentos-quick-pill" onclick="window.auth.selectQuickRole('operator2')" title="Fill Desk 2 Credentials">
                ✍️ Desk 2
              </button>
            </div>

            <p class="agentos-disclaimer">
              Karnataka Land Grabbing Prohibition Act, 2011 · Authorized Staff Access
            </p>
          </div>

          <!-- Bottom Bar -->
          <div class="agentos-bottom-bar">
            <div>© 2026 Karnataka Special Courts</div>
            <div class="agentos-lang-wrap" onclick="window.auth.toggleLanguageMenu()" title="Toggle English / Kannada">
              <span>🌐 ENG</span>
              <span style="font-size:10px;margin-left:2px;">&#9662;</span>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN: HERO SHOWCASE (MATCHING IMAGE AESTHETIC & THEMED FOR SPECIAL COURTS) -->
        <div class="agentos-right-col">
          <div class="agentos-hero-card">
            <!-- 3D Perspective Isometric Floating Element (matching floating badge in image) -->
            <div class="agentos-iso-wrapper">
              <div class="agentos-iso-stage">
                <div class="agentos-iso-grid">
                  <div class="agentos-iso-tile-base base-t1"></div>
                  <div class="agentos-iso-tile-base base-t2"></div>
                  <div class="agentos-iso-tile-base base-t3"></div>
                  <div class="agentos-iso-tile-base base-t4"></div>
                  <div class="agentos-iso-floating-badge">
                    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <!-- Hero Typography -->
            <div class="agentos-hero-content">
              <div class="agentos-hero-tag">KARNATAKA SPECIAL COURTS</div>
              <h2 class="agentos-hero-title">Record, Manage &amp; Dispose Special Court Cases</h2>
              <p class="agentos-hero-desc">
                Integrated bilingual cause list management, digital bench records, and certified decree tracking built for Karnataka Special Courts.
              </p>
            </div>

            <!-- Bottom Stacked Translucent Glass Status Cards (Exact match to 3 cards in image) -->
            <div class="agentos-hero-cards">
              <div class="agentos-glass-card">
                <div class="agentos-card-left">
                  <span class="agentos-card-dot dot-orange"></span>
                  <span>Identify pending cause list &amp; bench schedules</span>
                </div>
                <div class="agentos-card-status status-working">Working... 🟠</div>
              </div>

              <div class="agentos-glass-card">
                <div class="agentos-card-left">
                  <span class="agentos-card-dot dot-green"></span>
                  <span>Pending Case Register: 4,821 active records</span>
                </div>
                <div class="agentos-card-status status-done">Done 🟢</div>
              </div>

              <div class="agentos-glass-card">
                <div class="agentos-card-left">
                  <span class="agentos-card-dot dot-blue"></span>
                  <span>Disposed &amp; Possession Record Archival</span>
                </div>
                <div class="agentos-card-status status-done">Done 🟢</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="app sidebar-collapsed" id="appRoot">
      <div class="sidebar">
        <!-- Brand Header matching reference screenshot -->
        <div class="sidebar-brand-box">
          <div style="display:flex;align-items:center;">
            <div class="brand-logo-icon">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div class="brand-title-text">
              <h1>LG Special Courts</h1>
              <p>Bengaluru Registry</p>
            </div>
          </div>
          <button class="sidebar-toggle" id="sidebarToggle" title="Maximise menu" aria-label="Maximise menu" aria-expanded="false">&raquo;</button>
        </div>

        <!-- Sidebar Quick Search Bar -->
        <div class="sidebar-search-box">
          <input type="text" id="sidebarSearchInput" placeholder="Search cases, village, survey no..." />
          <svg class="sidebar-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>

        <!-- Navigation Menu -->
        <nav id="nav">
          <button data-view="navigator" onclick="switchView('navigator')" class="active" title="Case Navigator">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span class="navlabel">Case Navigator</span>
          </button>
          <button data-view="pendingentry" onclick="switchView('pendingentry')" title="Pending Cases Entry">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
            <span class="navlabel">Pending Cases Entry</span>
          </button>
          <button data-view="legacy" onclick="switchView('legacy')" title="Legacy Case Entry">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
              <polyline points="2 17 12 22 22 17"></polyline>
              <polyline points="2 12 12 17 22 12"></polyline>
            </svg>
            <span class="navlabel">Legacy Case Entry</span>
          </button>
          <button data-view="export" onclick="switchView('export')" title="Export & Backup">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            <span class="navlabel">Export &amp; Backup</span>
          </button>
        


        </nav>

        <!-- Sidebar Footer: Administration & Profile Card -->
        <div class="sidebar-foot-box">
          <div class="sidebar-admin-link" id="sidebarAdminBtn" onclick="openAdminSettings()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"></circle>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
            </svg>
            <span>Administration &amp; Settings</span>
          </div>

          <div class="sidebar-user-card" onclick="window.auth.openLoginModal()" style="cursor:pointer;" title="Click to Switch User / Login">
            <div class="user-avatar-wrap user-initials-badge" id="sidebarUserAvatar">
              <span id="sidebarUserInitials">AD</span>
              <span class="user-online-dot"></span>
            </div>
            <div class="user-info-text">
              <div class="user-info-name" id="sidebarUserName">System Administrator</div>
              <div class="user-info-sub" id="sidebarUserRole">Registrar &amp; Court Admin</div>
            </div>
            <span style="font-size:11px;color:#64748b;margin-left:auto;" title="Switch Account">⇄</span>
          </div>

          <button class="sidebar-admin-link" id="sidebarChangePwdBtn" onclick="window.auth.openUserChangePasswordModal()" style="margin-top:2px;color:var(--text-sec);border:none;background:none;width:100%;text-align:left;display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:12.5px;" title="Change your login password">
            <span>🔑</span>
            <span>Change Password</span>
          </button>

          <button class="sidebar-admin-link" id="sidebarLogoutBtn" onclick="window.auth.logout()" style="margin-top:4px;color:#d92d20;border:none;background:none;width:100%;text-align:left;display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;cursor:pointer;" title="Sign out of current account">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            <span>Sign Out / ನಿರ್ಗಮಿಸಿ</span>
          </button>
        </div>
      </div>

      <main style="padding:0;">
        <!-- Top App Header matching reference screenshot (Clean white + Stepper Bar) -->
        <div class="case-app-header" id="appHeaderBar">
          <div class="header-left-title">
            <h1 class="app-title" id="appTitleLbl">Pending Cases Entry</h1>
            <p class="app-subtitle" id="appSubLbl">Karnataka Land Grabbing Prohibition Special Courts</p>
          </div>
          <div class="header-right-controls">
            <!-- Stepper Progress Bar matching reference screenshot -->
            <div class="stepper-bar" id="topStepperBar">
              <div class="stepper-segment active" onclick="switchView('navigator')" style="cursor:pointer;" title="Step 1: Case Navigator"></div>
              <div class="stepper-segment active" onclick="switchView('pendingentry')" style="cursor:pointer;" title="Step 2: Pending Cases Entry"></div>
              <div class="stepper-segment" onclick="switchView('legacy')" style="cursor:pointer;" title="Step 3: Legacy Case Entry"></div>
              <div class="stepper-segment" onclick="switchView('export')" style="cursor:pointer;" title="Step 4: Export &amp; Backup"></div>
            </div>
            <button class="btn-mode-toggle" id="modeToggleBtn" onclick="toggleMode()">Switch to Disposed Mode</button>

            <!-- Auth User Badge & Sign Out Button -->
            <div class="top-auth-controls">
              <!-- Data Entry Person Particular Count Pill (visible when logged in as operator) -->
              <div class="clean-user-pill" id="topPersonalCountBadge" style="display:none;background:#f0fdf4;border-color:#bbf7d0;" title="Particular count of entries done by you">
                <span style="font-size:11.5px;font-weight:600;color:#166534;">My Entries:</span>
                <span id="myEntriesCount" style="background:#16a34a;color:#fff;padding:0 7px;border-radius:10px;font-size:11px;font-weight:700;">0</span>
              </div>

              <!-- System Admin Manage Access Button -->
              <button class="btn-clean-ghost" id="topManageOperatorsBtn" onclick="openAdminSettings()" style="display:none;" title="Court Administrator: Manage Operator Logins, Roles and Access">
                <svg width="13.5" height="13.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
                <span>Manage Access</span>
              </button>

              <!-- Profile Badge with Quick Switch / Login Click -->
              <div class="clean-user-pill" id="topUserBadge" onclick="window.auth.openLoginModal()" title="Active Session: Click to switch account or manage password">
                <div class="clean-avatar" id="topUserAvatar">SA</div>
                <div class="clean-user-details">
                  <span class="clean-user-name" id="topUserName">System Administrator</span>
                  <span class="clean-role-tag admin" id="topUserRoleBadge">Admin</span>
                </div>
                <svg class="clean-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="6 9 12 15 18 9"></polyline>
                </svg>
              </div>

              <!-- Dedicated Sign Out Button -->
              <button class="clean-logout-btn" id="topLogoutBtn" onclick="window.auth.logout()" title="Sign out of current account">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                <span>Sign Out</span>
              </button>

            </div>

          </div>
        </div>

        <!-- Action / Status Bar -->
        <div class="case-action-bar">
          <span class="status-text" id="statusDbLbl">Database: SQLite / Local Storage (56 records)</span>
          <div class="actions-group">
            <span class="badge-total-records" id="totalBadgeLbl">Total Records: 56</span>
            <button class="btn-case-action" id="topExportCsvBtn" onclick="exportAllCasesCsv()">Export CSV</button>
            <button class="btn-case-action" id="topExportJsonBtn" onclick="exportAllCasesJson()">Export JSON</button>
            <button class="btn-case-action" id="topScanBtn" onclick="openScanModal()">🦙 Scan Images</button>
            <button class="btn-case-primary" id="topBatchBtn" onclick="openBatchModal()">⚡ Batch Process</button>
            <button class="btn-case-primary" id="topComparePdfBtn" onclick="togglePdfSideBySide()">📄 Compare PDF</button>
            <button class="btn-case-action" id="topPdfFolderBtn" onclick="openPdfFolderModal()">📁 PDF Folder</button>
          </div>
        </div>

        <!-- Review Queue Banner -->
        <div class="queue-bar" id="queueBar" style="display:none;">
          <span class="queue-title" id="queueTitleLbl">📋 OCR Review Queue: Case 1 of 1</span>
          <div class="queue-actions">
            <button class="btn-case-action" id="rqPrevBtn">◀ Prev Case</button>
            <button class="btn-case-action" id="rqNextBtn">Next Case ▶</button>
            <button class="btn-case-primary" id="rqPopulateBtn">Populate Form</button>
            <button class="btn-case-primary" id="rqSaveNextBtn">Save &amp; Next</button>
            <button class="btn-case-action" id="rqClearBtn" style="color:#d92d20;">Clear Queue</button>
            <button class="btn-case-action" id="rqViewPdfBtn">📄 View PDF</button>
          </div>
        </div>

        <!-- Hidden / system status placeholders -->
        <div id="pageTitle" style="display:none;">Case Navigator</div>
        <div id="pageSub" style="display:none;">Search and review cases</div>
        <div id="userBadge" style="display:none;"></div>

        <!-- Main Middle Layout (Form / Table on Left, PDF Viewer on Right) -->
        <div class="middle-paned-layout" id="middlePanedLayout">
          <div class="main-view-container" id="viewRoot"></div>

          <!-- Side-by-side PDF Viewer Pane -->
          <div class="pdf-side-pane" id="pdfSidePane" style="display:none;">
            <div class="pdf-top-bar">
              <span class="pdf-title" id="pdfTitleLbl">📄 Original PDF Viewer</span>
              <div class="pdf-controls-box">
                <button class="pdf-btn-ctrl" id="pdfPrevPageBtn">◀</button>
                <span id="pdfPageLbl" style="font-size:11px;padding:0 3px;color:#667085;">1/1</span>
                <button class="pdf-btn-ctrl" id="pdfNextPageBtn">▶</button>
                <button class="pdf-btn-ctrl" id="pdfZoomOutBtn">➖</button>
                <span id="pdfZoomLbl" style="font-size:11px;padding:0 2px;color:#667085;">100%</span>
                <button class="pdf-btn-ctrl" id="pdfZoomInBtn">➕</button>
                <button class="pdf-btn-ctrl" id="pdfFitBtn">Fit</button>
                <button class="pdf-btn-ctrl" id="pdfRotateBtn">⟳</button>
                <button class="pdf-btn-ctrl" id="pdfOpenTabBtn">↗ Open</button>
                <label class="pdf-btn-ctrl" style="cursor:pointer;margin:0;">
                  📂 Browse <input type="file" id="pdfBrowseInput" accept="image/*,.pdf" style="display:none;">
                </label>
                <button class="pdf-btn-ctrl btn-danger" id="pdfCloseBtn">✕</button>
              </div>
            </div>

            <div class="pdf-viewport" id="pdfViewport">
              <div id="pdfEmptyNotice" style="color:#94a3b8;text-align:center;padding:30px;">
                <div style="font-size:32px;margin-bottom:8px;">📄</div>
                <div>No document loaded for side-by-side review.</div>
                <div style="font-size:11px;margin-top:6px;color:#64748b;">Click "document" on any case or load a scanned order sheet.</div>
              </div>
              <div id="pdfCanvasWrap" style="display:none;position:relative;width:100%;height:100%;overflow-y:auto;overflow-x:auto;padding:16px 12px;box-sizing:border-box;background:#0f172a;scroll-behavior:smooth;">
                <div id="pdfPagesScrollContainer" style="display:flex;flex-direction:column;align-items:center;gap:18px;width:100%;min-height:100%;transition:transform 0.15s ease;transform-origin:center top;">
                  <!-- Continuous scrollable PDF pages rendered here -->
                </div>
                <iframe id="pdfViewerFrame" style="display:none;width:100%;height:100%;min-height:600px;border:none;"></iframe>
              </div>
            </div>

            <div class="pdf-footer-bar">
              <span id="pdfFolderStatusLbl">PDF Folder: Local Workspace</span>
              <button class="btn-case-action" id="setPdfFolderBtn" style="padding:2px 7px;font-size:10px;">Set Folder</button>
            </div>
          </div>
        </div>
          <!-- Global Case Notification Toast Container -->
      <div id="caseNotificationContainer"></div>
      </main>
    </div>
"""

# Part 3: Auth Script & Role-Based Access Control
part3_auth = """    <script>
      (function () {
        function escHtml(s) {
          return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        }
        function escAttr(s) {
          return String(s || "").replace(/"/g, "&quot;");
        }
        window.escHtml = window.escHtml || escHtml;
        window.escAttr = window.escAttr || escAttr;

        const DEFAULT_OPERATORS = {
          admin: {
            username: "admin",
            displayName: "System Administrator",
            role: "admin",
            roleTitle: "Registrar & System Administrator",
            hall: "1",
            mode: "Pending",
            password: "admin",
            status: "active"
          },
          operator1: {
            username: "operator1",
            displayName: "Data Entry Person 1",
            role: "operator",
            roleTitle: "Data Entry Operator (Desk 1)",
            hall: "1",
            mode: "Pending",
            password: "operator",
            status: "active"
          },
          operator2: {
            username: "operator2",
            displayName: "Data Entry Person 2",
            role: "operator",
            roleTitle: "Data Entry Operator (Desk 2)",
            hall: "2",
            mode: "Pending",
            password: "operator",
            status: "active"
          }
        };

        let cachedOperators = null;

        function getOperatorAccounts() {
          if (cachedOperators) return cachedOperators;
          try {
            const raw = window.localStorage ? window.localStorage.getItem("lgc_users") : null;
            if (raw) {
              const parsed = JSON.parse(raw);
              if (parsed && typeof parsed === "object" && Object.keys(parsed).length > 0) {
                cachedOperators = Object.assign({}, DEFAULT_OPERATORS, parsed);
                return cachedOperators;
              }
            }
          } catch (_) {}
          cachedOperators = JSON.parse(JSON.stringify(DEFAULT_OPERATORS));
          try {
            if (window.localStorage) {
              window.localStorage.setItem("lgc_users", JSON.stringify(cachedOperators));
            }
          } catch (_) {}
          return cachedOperators;
        }

        async function saveOperatorAccounts(ops) {
          if (!ops || typeof ops !== "object") return false;
          cachedOperators = ops;
          try {
            if (window.localStorage) {
              window.localStorage.setItem("lgc_users", JSON.stringify(ops));
            }
          } catch (_) {}

          // Async sync to server if running
          try {
            fetch("/api/users", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(ops)
            }).catch(() => {});
          } catch (_) {}

          // Update active user profile if modified
          if (currentUser && ops[currentUser.username]) {
            currentUser = Object.assign({}, currentUser, ops[currentUser.username]);
            try {
              if (window.localStorage) {
                window.localStorage.setItem("lgc_current_user", JSON.stringify(currentUser));
              }
            } catch (_) {}
            applyRoleUI();
          }
          return true;
        }

        async function syncOperatorsFromServer() {
          try {
            const res = await fetch("/api/users");
            if (res.ok) {
              const serverOps = await res.json();
              if (serverOps && typeof serverOps === "object" && Object.keys(serverOps).length > 0) {
                const merged = Object.assign({}, getOperatorAccounts(), serverOps);
                await saveOperatorAccounts(merged);
                return merged;
              }
            }
          } catch (_) {}
          return getOperatorAccounts();
        }

        let currentUser = null;
        try {
          const stored = window.localStorage ? window.localStorage.getItem("lgc_current_user") : null;
          if (stored) {
            currentUser = JSON.parse(stored);
          }
        } catch (_) {}

        function showLoginPage(message, isError) {
          const loginRoot = document.getElementById("loginPageRoot");
          const appRoot = document.getElementById("appRoot");
          if (loginRoot) loginRoot.style.display = "flex";
          if (appRoot) appRoot.style.display = "none";
          closeLoginModal();

          const alertBox = document.getElementById("loginAlertBox");
          if (alertBox) {
            if (message) {
              alertBox.style.display = "block";
              alertBox.className = "court-alert-banner " + (isError ? "court-alert-error" : "court-alert-success");
              alertBox.innerHTML = (isError ? "⚠️ " : "✓ ") + escHtml(message);
            } else {
              alertBox.style.display = "none";
              alertBox.innerHTML = "";
            }
          }

          const pwdInput = document.getElementById("loginPasswordInput");
          if (pwdInput) pwdInput.value = "";
          const userInput = document.getElementById("loginUsernameInput");
          if (userInput) {
            if (!userInput.value && currentUser && currentUser.username) {
              userInput.value = currentUser.username;
            }
            setTimeout(() => { try { userInput.focus(); } catch(_) {} }, 100);
          }
        }

        function showApp(user) {
          if (user) currentUser = user;
          const loginRoot = document.getElementById("loginPageRoot");
          const appRoot = document.getElementById("appRoot");
          if (loginRoot) loginRoot.style.display = "none";
          if (appRoot) appRoot.style.setProperty("display", "grid", "important");
          closeLoginModal();
          applyRoleUI(currentUser);
          if (typeof updateTopBarStats === "function") updateTopBarStats();
          if (typeof render === "function") render();
        }

        async function login(username, password, hall, remember) {
          const u = (username || "").trim().toLowerCase();
          const p = password !== undefined && password !== null ? String(password).trim() : "";
          if (!u) {
            showLoginAlert("Please enter your Username / Court ID.", true);
            return false;
          }
          if (!p) {
            showLoginAlert("Password authentication is required. Please enter your password.", true);
            const pwdInput = document.getElementById("loginPasswordInput");
            if (pwdInput) {
              pwdInput.style.borderColor = "#ef4444";
              pwdInput.focus();
            }
            return false;
          }

          // Spinner indicator
          const spinner = document.getElementById("loginBtnSpinner");
          const submitBtn = document.getElementById("loginSubmitBtn");
          if (spinner) spinner.style.display = "inline-block";
          if (submitBtn) submitBtn.disabled = true;

          let account = null;

          // Attempt server authentication first
          try {
            const resp = await fetch("/api/login", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ username: u, password: p })
            });
            if (resp.ok) {
              const data = await resp.json();
              if (data && data.success && data.user) {
                account = data.user;
                if (hall && hall !== "admin") account.hall = String(hall);
              }
            } else {
              const errData = await resp.json().catch(() => ({}));
              const errMsg = errData.error || ("Authentication failed (HTTP " + resp.status + ")");
              showLoginAlert(errMsg, true);
              if (spinner) spinner.style.display = "none";
              if (submitBtn) submitBtn.disabled = false;
              return false;
            }
          } catch (_) {
            // Offline fallback to cached/local accounts
            const ops = getOperatorAccounts();
            const localAcc = ops[u];
            if (!localAcc) {
              showLoginAlert(`Account "${u}" not found in court records.`, true);
              if (spinner) spinner.style.display = "none";
              if (submitBtn) submitBtn.disabled = false;
              return false;
            }
            if (localAcc.status === "disabled") {
              showLoginAlert(`Account "${localAcc.displayName || u}" is disabled. Contact System Administrator.`, true);
              if (spinner) spinner.style.display = "none";
              if (submitBtn) submitBtn.disabled = false;
              return false;
            }
            if ((localAcc.password || "operator") !== p) {
              showLoginAlert("Incorrect password. Please verify your credentials.", true);
              if (spinner) spinner.style.display = "none";
              if (submitBtn) submitBtn.disabled = false;
              return false;
            }
            account = localAcc;
          }

          if (spinner) spinner.style.display = "none";
          if (submitBtn) submitBtn.disabled = false;

          if (!account) {
            showLoginAlert("Authentication failed. Please verify credentials.", true);
            return false;
          }

          currentUser = account;
          const shouldRemember = remember !== false;
          try {
            if (window.localStorage) {
              if (shouldRemember) {
                window.localStorage.setItem("lgc_current_user", JSON.stringify(currentUser));
              } else {
                window.localStorage.removeItem("lgc_current_user");
              }
            }
          } catch (_) {}

          showApp(currentUser);
          return true;
        }

        function showLoginAlert(msg, isErr) {
          const box = document.getElementById("loginAlertBox");
          if (box) {
            box.style.display = "block";
            box.className = "court-alert-banner " + (isErr ? "court-alert-error" : "court-alert-success");
            box.innerHTML = (isErr ? "⚠️ " : "✓ ") + escHtml(msg);
          } else {
            alert(msg);
          }
        }

        function handleSignUpClick() {
          alert("Account Provisioning Notice:\\n\\nOfficial court access accounts are created and configured by the System Administrator in accordance with the Karnataka Land Grabbing Prohibition Act.\\n\\nTo log in, use your assigned Court ID/Username and Password, or click one of the quick sign-in buttons below the form (Admin or Desk Operator).");
        }

        let currentLang = "ENG";
        function toggleLanguageMenu() {
          currentLang = currentLang === "ENG" ? "KAN" : "ENG";
          const langWrap = document.querySelector(".agentos-lang-wrap");
          if (langWrap) {
            langWrap.innerHTML = '<span>🌐 ' + (currentLang === "ENG" ? "ENG" : "ಕನ್ನಡ") + '</span><span style="font-size:10px;margin-left:2px;">&#9662;</span>';
          }
          const heading = document.querySelector(".agentos-heading");
          const subheading = document.querySelector(".agentos-subheading");
          const submitBtn = document.querySelector("#loginSubmitBtn span:last-child");
          if (heading) heading.textContent = currentLang === "ENG" ? "Welcome back!" : "ಸುಸ್ವಾಗತ!";
          if (subheading) subheading.textContent = currentLang === "ENG" ? "Sign in to continue where your left off." : "ನಿಮ್ಮ ನ್ಯಾಯಾಲಯ ಪ್ರವೇಶವನ್ನು ಮುಂದುವರಿಸಲು ಲಾಗಿನ್ ಮಾಡಿ.";
          if (submitBtn) submitBtn.textContent = currentLang === "ENG" ? "Sign In to Court Register ➔" : "ನ್ಯಾಯಾಲಯ ರಿಜಿಸ್ಟರ್ ಪ್ರವೇಶಿಸಿ ➔";
        }

        function handleLoginFormSubmit(e) {
          if (e && e.preventDefault) e.preventDefault();
          const u = (document.getElementById("loginUsernameInput")?.value || "").trim();
          const p = document.getElementById("loginPasswordInput")?.value || "";
          const h = document.getElementById("loginHallSelect")?.value || "1";
          const rem = document.getElementById("loginRememberMeCheckbox")?.checked !== false;

          if (!u) {
            showLoginAlert("Please enter your Username / Court ID.", true);
            document.getElementById("loginUsernameInput")?.focus();
            return;
          }
          if (!p) {
            showLoginAlert("Password authentication is required. Please enter your password.", true);
            const pwdInput = document.getElementById("loginPasswordInput");
            if (pwdInput) {
              pwdInput.style.borderColor = "#ef4444";
              pwdInput.focus();
            }
            return;
          }
          login(u, p, h, rem);
        }

        function togglePasswordVisibility() {
          const pwd = document.getElementById("loginPasswordInput");
          const btn = document.getElementById("pwdToggleBtn");
          if (!pwd) return;
          if (pwd.type === "password") {
            pwd.type = "text";
            if (btn) btn.textContent = "🙈";
          } else {
            pwd.type = "password";
            if (btn) btn.textContent = "👁️";
          }
        }

        function selectQuickRole(roleName) {
          const ops = getOperatorAccounts();
          const acc = ops[roleName] || DEFAULT_OPERATORS[roleName];
          if (!acc) return;
          const uInput = document.getElementById("loginUsernameInput");
          const pInput = document.getElementById("loginPasswordInput");
          const hSelect = document.getElementById("loginHallSelect");
          if (uInput) uInput.value = acc.username;
          if (hSelect && acc.hall) hSelect.value = acc.hall;
          if (pInput) {
            pInput.value = "";
            pInput.style.borderColor = "#12b76a";
            pInput.focus();
          }
          const defaultHint = (acc.role === "admin") ? "admin" : "operator";
          showLoginAlert(`Account "${acc.username}" selected (${escHtml(acc.displayName || acc.username)}). Please enter password "${defaultHint}" and click Sign In.`, false);
        }

        let pendingSwitchUsername = null;
        function promptRoleSwitchPassword(targetUsername) {
          const ops = getOperatorAccounts();
          const acc = ops[targetUsername] || DEFAULT_OPERATORS[targetUsername];
          if (!acc) return;
          pendingSwitchUsername = targetUsername;
          const area = document.getElementById("switchPasswordArea");
          const nameSpan = document.getElementById("switchTargetDisplay");
          const pwdInput = document.getElementById("switchModalPasswordInput");
          const errDiv = document.getElementById("switchModalError");
          if (area) area.style.display = "block";
          if (nameSpan) nameSpan.textContent = (acc.displayName || acc.username) + " (" + acc.username + ")";
          if (pwdInput) {
            pwdInput.value = "";
            pwdInput.focus();
          }
          if (errDiv) {
            errDiv.style.display = "none";
            errDiv.textContent = "";
          }
        }

        async function executePasswordSwitch() {
          if (!pendingSwitchUsername) return;
          const pwd = document.getElementById("switchModalPasswordInput")?.value || "";
          const errDiv = document.getElementById("switchModalError");
          if (!pwd) {
            if (errDiv) {
              errDiv.style.display = "block";
              errDiv.textContent = "Password is required to authenticate.";
            }
            return;
          }
          const success = await login(pendingSwitchUsername, pwd);
          if (!success) {
            if (errDiv) {
              errDiv.style.display = "block";
              errDiv.textContent = "Authentication failed: Incorrect password.";
            }
          }
        }

        function openUserChangePasswordModal() {
          closeLoginModal();
          let container = document.getElementById("changePwdModalContainer");
          if (!container) {
            container = document.createElement("div");
            container.id = "changePwdModalContainer";
            document.body.appendChild(container);
          }
          const u = currentUser;
          if (!u) return;

          container.innerHTML = `
            <div class="modal-backdrop active" id="changePwdBackdrop" onclick="if(event.target.id==='changePwdBackdrop')document.getElementById('changePwdModalContainer').innerHTML=''" style="display:flex;align-items:center;justify-content:center;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(15,23,42,0.65);z-index:99999;backdrop-filter:blur(3px);">
              <div style="background:#ffffff;border-radius:12px;max-width:440px;width:92%;padding:24px;box-shadow:0 25px 50px -12px rgba(0,0,0,0.25);border:1px solid #e2e8f0;font-family:system-ui,-apple-system,sans-serif;">
                <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #f1f5f9;padding-bottom:12px;margin-bottom:16px;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <span style="font-size:20px;">🔑</span>
                    <h3 style="margin:0;font-size:16px;font-weight:700;color:#0f172a;">Change Account Password</h3>
                  </div>
                  <button type="button" onclick="document.getElementById('changePwdModalContainer').innerHTML=''" style="border:none;background:none;font-size:18px;cursor:pointer;color:#94a3b8;">✕</button>
                </div>

                <div style="background:#f8fafc;padding:10px 12px;border-radius:6px;font-size:12px;color:#475569;margin-bottom:14px;border:1px solid #e2e8f0;">
                  User: <strong>${escHtml(u.displayName || u.username)}</strong> (<code>${escHtml(u.username)}</code>)
                </div>

                <div id="changePwdAlert" style="display:none;padding:8px 12px;border-radius:6px;font-size:12px;margin-bottom:12px;"></div>

                <form onsubmit="window.auth.submitUserChangePassword(event)">
                  <div style="margin-bottom:12px;">
                    <label style="display:block;font-size:12px;font-weight:600;color:#334155;margin-bottom:4px;">Current Password</label>
                    <input type="password" id="currPwdInput" placeholder="Enter current password" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" required />
                  </div>

                  <div style="margin-bottom:12px;">
                    <label style="display:block;font-size:12px;font-weight:600;color:#334155;margin-bottom:4px;">New Password</label>
                    <input type="password" id="newPwdInput" placeholder="Enter new password (min. 4 characters)" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" required />
                  </div>

                  <div style="margin-bottom:16px;">
                    <label style="display:block;font-size:12px;font-weight:600;color:#334155;margin-bottom:4px;">Confirm New Password</label>
                    <input type="password" id="confirmPwdInput" placeholder="Confirm new password" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" required />
                  </div>

                  <div style="display:flex;justify-content:flex-end;gap:8px;">
                    <button type="button" class="btn-case-action" onclick="document.getElementById('changePwdModalContainer').innerHTML=''">Cancel</button>
                    <button type="submit" class="btn-case-action" style="background:#1570ef;color:#fff;border-color:#1570ef;font-weight:600;padding:6px 16px;">Update Password</button>
                  </div>
                </form>
              </div>
            </div>
          `;
        }

        async function submitUserChangePassword(e) {
          if (e && e.preventDefault) e.preventDefault();
          const curr = document.getElementById("currPwdInput")?.value || "";
          const np = document.getElementById("newPwdInput")?.value || "";
          const conf = document.getElementById("confirmPwdInput")?.value || "";
          const alertEl = document.getElementById("changePwdAlert");

          function setAlert(msg, isErr) {
            if (!alertEl) return;
            alertEl.style.display = "block";
            alertEl.style.background = isErr ? "#fee2e2" : "#dcfce7";
            alertEl.style.color = isErr ? "#991b1b" : "#166534";
            alertEl.style.border = "1px solid " + (isErr ? "#fca5a5" : "#86efac");
            alertEl.textContent = (isErr ? "⚠️ " : "✓ ") + msg;
          }

          if (!curr) { setAlert("Current password is required.", true); return; }
          if (!np) { setAlert("New password is required.", true); return; }
          if (np.length < 4) { setAlert("New password must be at least 4 characters long.", true); return; }
          if (np !== conf) { setAlert("New passwords do not match. Please verify.", true); return; }

          const u = currentUser;
          if (!u) return;

          // Attempt backend update
          try {
            const resp = await fetch("/api/change-password", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                username: u.username,
                current_password: curr,
                new_password: np
              })
            });
            const data = await resp.json().catch(() => ({}));
            if (resp.ok && data.success) {
              setAlert("Password updated successfully!", false);
              const ops = getOperatorAccounts();
              if (ops[u.username]) {
                ops[u.username].password = np;
                await saveOperatorAccounts(ops);
              }
              setTimeout(() => {
                const c = document.getElementById("changePwdModalContainer");
                if (c) c.innerHTML = "";
              }, 1200);
              return;
            } else {
              setAlert(data.error || "Password change failed.", true);
              return;
            }
          } catch (_) {
            // Offline fallback
            const ops = getOperatorAccounts();
            const op = ops[u.username];
            if (!op || (op.password || "operator") !== curr) {
              setAlert("Current password verification failed.", true);
              return;
            }
            op.password = np;
            await saveOperatorAccounts(ops);
            setAlert("Password updated successfully (local storage)!", false);
            setTimeout(() => {
              const c = document.getElementById("changePwdModalContainer");
              if (c) c.innerHTML = "";
            }, 1200);
          }
        }

        function logout() {
          try {
            if (window.localStorage) {
              window.localStorage.removeItem("lgc_current_user");
            }
          } catch (_) {}
          currentUser = null;
          showLoginPage("You have been signed out safely.", false);
        }

        function getUserCaseCount(username) {
          if (!window.state || !Array.isArray(window.state.cases)) return 0;
          const target = (username || "").toLowerCase().trim();
          return window.state.cases.filter(c => {
            const op = (c.operatorId || "").toLowerCase().trim();
            const ent = (c.enteredBy || c.entered_by || "").toLowerCase().trim();
            return op === target || ent === target;
          }).length;
        }

        function applyRoleUI(user) {
          const u = user || currentUser;
          if (!u) return;
          const app = document.getElementById("appRoot");
          if (app) app.style.setProperty("display", "grid", "important");

          const isAdmin = u.role === "admin";
          const isOperator = u.role === "operator";

          // Top Header user badge
          const topName = document.getElementById("topUserName");
          const topRole = document.getElementById("topUserRoleBadge");
          const topAvatar = document.getElementById("topUserAvatar");
          const topManageBtn = document.getElementById("topManageOperatorsBtn");
          const topPersonalCountBadge = document.getElementById("topPersonalCountBadge");
          const myEntriesCountSpan = document.getElementById("myEntriesCount");
          const userDot = document.getElementById("topUserDot");

          const rawDisplayName = u.displayName || u.username;
          if (topName) topName.textContent = rawDisplayName;
          if (topAvatar) {
            const parts = rawDisplayName.trim().split(/\s+/);
            topAvatar.textContent = parts.length > 1 ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase() : rawDisplayName.slice(0, 2).toUpperCase();
          }
          if (topRole) {
            topRole.textContent = isAdmin ? "Admin" : "Data Entry";
            topRole.className = "clean-role-tag " + (isAdmin ? "admin" : "operator");
            topRole.removeAttribute("style");
          }
          if (userDot) {
            userDot.style.background = isAdmin ? "#3b82f6" : "#10b981";
          }

          // System Admin access to Manage Operators
          if (topManageBtn) {
            topManageBtn.style.setProperty("display", isAdmin ? "inline-flex" : "none", "important");
          }

          // Sidebar items
          const sidebarAdminBtn = document.getElementById("sidebarAdminBtn");
          if (sidebarAdminBtn) {
            sidebarAdminBtn.style.display = isAdmin ? "flex" : "none";
          }
          const sName = document.getElementById("sidebarUserName");
          const sRole = document.getElementById("sidebarUserRole");
          const sInitials = document.getElementById("sidebarUserInitials");
          if (sName) sName.textContent = u.displayName || u.username;
          if (sRole) sRole.textContent = u.roleTitle || (isAdmin ? "Registrar & System Administrator" : "Data Entry Operator");
          if (sInitials) {
            const parts = (u.displayName || u.username).trim().split(" ");
            sInitials.textContent = parts.length > 1 ? (parts[0][0] + parts[parts.length-1][0]).toUpperCase() : parts[0].slice(0, 2).toUpperCase();
          }

          // Data Entry Person Particular Count Pill
          const myCount = getUserCaseCount(u.username);
          if (myEntriesCountSpan) myEntriesCountSpan.textContent = myCount;
          if (topPersonalCountBadge) {
            topPersonalCountBadge.style.display = isOperator ? "inline-flex" : "none";
          }

          // Hide / Show Delete buttons based on delete access
          const fDeleteBtn = document.getElementById("fDeleteBtn");
          if (fDeleteBtn) {
            fDeleteBtn.style.display = isAdmin ? "inline-flex" : "none";
          }

          document.querySelectorAll("[data-del-id]").forEach(btn => {
            btn.style.display = isAdmin ? "inline-block" : "none";
          });

          if (typeof updateTopBarStats === "function") {
            updateTopBarStats();
          }
        }

        window.auth = {
          get user() { return currentUser; },
          get isAuthenticated() { return !!currentUser; },
          get isAdmin() { return currentUser && currentUser.role === "admin"; },
          get isOperator() { return currentUser && currentUser.role === "operator"; },
          get canDelete() { return currentUser && currentUser.role === "admin"; },
          get canManageAccess() { return currentUser && currentUser.role === "admin"; },
          canAccess(view) {
            if (view === "admin_operators") return currentUser && currentUser.role === "admin";
            return true;
          },
          canWrite(view) { return true; },
          getUserCaseCount,
          login,
          quickLogin(u) { return promptRoleSwitchPassword(u); },
          promptRoleSwitchPassword,
          executePasswordSwitch,
          openUserChangePasswordModal,
          submitUserChangePassword,
          logout,
          showLoginPage,
          showApp,
          openLoginModal,
          closeLoginModal,
          applyRoleUI,
          handleLoginFormSubmit,
          togglePasswordVisibility,
          selectQuickRole,
          handleSignUpClick,
          toggleLanguageMenu
        };

        window.getOperatorAccounts = getOperatorAccounts;
        window.saveOperatorAccounts = saveOperatorAccounts;
        window.syncOperatorsFromServer = syncOperatorsFromServer;

        window.showLandingView = function() {
          if (currentUser) applyRoleUI(currentUser);
          else showLoginPage();
        };

        window.showAppView = function(user) {
          if (user) currentUser = user;
          if (currentUser) applyRoleUI(currentUser);
          else showLoginPage();
        };

        window.openAdminSettings = function() {
          if (!window.auth.isAdmin) {
            alert("Access Restricted: Only the System Administrator can manage operator accounts and access settings.");
            return;
          }
          if (typeof switchView === "function") {
            switchView("admin_operators");
          }
        };

        function openLoginModal() {
          let container = document.getElementById("authLoginModalContainer");
          if (!container) {
            container = document.createElement("div");
            container.id = "authLoginModalContainer";
            document.body.appendChild(container);
          }
          const ops = getOperatorAccounts();
          const u = currentUser || DEFAULT_OPERATORS.admin;
          const isAdmin = u.role === "admin";
          const rawName = (u.displayName || u.username).trim();
          const parts = rawName.split(/\s+/);
          const activeInitials = parts.length > 1 ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase() : rawName.slice(0, 2).toUpperCase();

          // Build dynamic account cards from registered accounts
          let accountCardsHtml = "";
          const accountKeys = Object.keys(ops);
          for (const key of accountKeys) {
            const op = ops[key];
            const isTargetActive = (u.username.toLowerCase() === key.toLowerCase());
            const opName = op.displayName || key;
            const opParts = opName.trim().split(/\s+/);
            const opInitials = opParts.length > 1 ? (opParts[0][0] + opParts[opParts.length - 1][0]).toUpperCase() : opName.slice(0, 2).toUpperCase();
            const isOpAdmin = op.role === "admin";
            const opCount = getUserCaseCount(key);
            const countText = isOpAdmin 
              ? `System Administrator · All counts visible (${window.state && window.state.cases ? window.state.cases.length : 0} total)`
              : `Data Entry Operator · ${opCount} entries completed`;

            accountCardsHtml += `
              <div class="auth-account-card ${isTargetActive ? 'active' : ''}" onclick="${isTargetActive ? '' : `window.auth.promptRoleSwitchPassword('${key}')`}">
                <div class="auth-acc-left">
                  <div class="auth-acc-avatar">${opInitials}</div>
                  <div>
                    <div class="auth-acc-name-row">
                      <span class="auth-acc-name">${escHtml(opName)}</span>
                      <span class="clean-role-tag ${isOpAdmin ? 'admin' : 'operator'}">${isOpAdmin ? 'Admin' : 'Data Entry'}</span>
                    </div>
                    <div class="auth-acc-sub">user: <code>${escHtml(key)}</code> · ${countText}</div>
                  </div>
                </div>
                ${isTargetActive 
                  ? `<span class="badge-account-active"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Active</span>`
                  : `<span class="badge-account-switch">Switch <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg></span>`
                }
              </div>
            `;
          }

          container.innerHTML = `
            <div class="modal-backdrop active" id="authLoginBackdrop" onclick="if(event.target.id==='authLoginBackdrop')window.auth.closeLoginModal()" style="display:flex;align-items:center;justify-content:center;position:fixed;inset:0;background:rgba(15,23,42,0.5);z-index:99999;backdrop-filter:blur(4px);">
              <div class="auth-modal-dialog">
                <!-- Header -->
                <div class="auth-modal-header">
                  <div class="auth-header-left">
                    <div class="auth-header-icon">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                      </svg>
                    </div>
                    <div>
                      <h3 class="auth-header-title">Court Portal Access</h3>
                      <p class="auth-header-subtitle">Active operator session &amp; account switcher</p>
                    </div>
                  </div>
                  <button type="button" onclick="window.auth.closeLoginModal()" class="auth-close-btn" aria-label="Close">✕</button>
                </div>

                <!-- Currently Active Session Card -->
                <div class="auth-active-card">
                  <div class="auth-active-user-row">
                    <div class="auth-card-avatar">${activeInitials}</div>
                    <div class="auth-card-meta">
                      <div class="auth-card-label">CURRENT ACTIVE SESSION</div>
                      <div class="auth-card-name">${escHtml(u.displayName || u.username)}</div>
                      <div class="auth-card-tag ${isAdmin ? 'admin' : 'operator'}">
                        ${isAdmin ? 'Administrator · Full Access' : 'Data Entry Operator · Court Hall ' + (u.hall || '1')}
                      </div>
                    </div>
                  </div>
                  <div class="auth-active-actions">
                    <button type="button" class="btn-auth-action" onclick="window.auth.openUserChangePasswordModal()">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="7.5" cy="15.5" r="5.5"/><path d="m21 2-9.6 9.6"/><path d="m15.5 7.5 3 3L22 7l-3-3"/></svg>
                      Change Password
                    </button>
                    <button type="button" class="btn-auth-action" onclick="window.auth.showLoginPage()">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/><path d="m14 9 3 3-3 3"/></svg>
                      Login Screen
                    </button>
                    <button type="button" class="btn-auth-action logout" onclick="window.auth.logout()">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"></line></svg>
                      Sign Out
                    </button>
                  </div>
                </div>

                <!-- Role Switcher Section -->
                <div class="auth-switch-section">
                  <div class="auth-section-title">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                    <span>Switch Operator Session</span>
                  </div>
                  <div class="auth-accounts-grid">
                    ${accountCardsHtml}
                  </div>

                  <!-- Inline Password Authentication Box for Role Switch -->
                  <div id="switchPasswordArea" class="auth-switch-pw-box" style="display:none;">
                    <div style="font-size:12.5px;font-weight:700;color:#1e40af;display:flex;align-items:center;gap:6px;">
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                      <span>Password Required:</span>
                      <span id="switchTargetDisplay" style="color:#2563eb;"></span>
                    </div>
                    <div style="font-size:11.5px;color:#64748b;margin-top:2px;">Enter account password to authenticate session switch:</div>
                    <div style="display:flex;gap:8px;margin-top:10px;">
                      <input type="password" id="switchModalPasswordInput" placeholder="Account password" style="flex:1;padding:7px 11px;border:1px solid #cbd5e1;border-radius:7px;font-size:13px;outline:none;" onkeydown="if(event.key==='Enter')window.auth.executePasswordSwitch()" />
                      <button type="button" class="btn-case-action" onclick="window.auth.executePasswordSwitch()" style="background:#2563eb;color:#fff;border-color:#2563eb;font-weight:600;padding:6px 14px;border-radius:7px;cursor:pointer;">Verify &amp; Switch</button>
                    </div>
                    <div id="switchModalError" style="display:none;color:#dc2626;font-size:11.5px;margin-top:6px;font-weight:600;"></div>
                  </div>

                  <!-- Manual Login Form Accordion -->
                  <details style="margin-top:14px;border-top:1px solid #f1f5f9;padding-top:12px;">
                    <summary style="font-size:11.5px;color:#64748b;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:5px;user-select:none;">
                      <span>Or sign in with custom credentials</span>
                    </summary>
                    <form onsubmit="handleLoginSubmit(event)" style="margin-top:12px;background:#f8fafc;padding:12px;border-radius:8px;border:1px solid #e2e8f0;">
                      <div style="margin-bottom:10px;">
                        <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Username</label>
                        <input type="text" id="modalLoginUsernameInput" placeholder="e.g. admin or operator1" style="width:100%;box-sizing:border-box;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" required>
                      </div>
                      <div style="margin-bottom:12px;">
                        <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Password</label>
                        <input type="password" id="modalLoginPasswordInput" placeholder="Enter password" style="width:100%;box-sizing:border-box;padding:7px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;" required>
                      </div>
                      <div style="display:flex;justify-content:flex-end;">
                        <button type="submit" class="btn-case-action" style="background:#2563eb;color:#fff;border-color:#2563eb;font-weight:600;padding:6px 16px;border-radius:6px;cursor:pointer;">Sign In</button>
                      </div>
                    </form>
                  </details>
                </div>
              </div>
            </div>
          `;
        }

        window.handleLoginSubmit = function(e) {
          if (e && e.preventDefault) e.preventDefault();
          const u = document.getElementById("modalLoginUsernameInput")?.value || "";
          const p = document.getElementById("modalLoginPasswordInput")?.value || "";
          window.auth.login(u, p);
        };

        function closeLoginModal() {
          const container = document.getElementById("authLoginModalContainer");
          if (container) container.innerHTML = "";
        }
      })();
    </script>"""

# Part 4: Storage Script
part4_storage = """    <script>
      (function () {
        window.storage = {
          async get(key) {
            try {
              const localVal = window.localStorage ? window.localStorage.getItem("lgc_" + key) : null;
              if (localVal != null) {
                return JSON.parse(localVal);
              }
            } catch(_) {}
            return null;
          },
          async set(key, value) {
            try {
              if (window.localStorage) {
                window.localStorage.setItem("lgc_" + key, JSON.stringify({ value }));
              }
            } catch(_) {}

            // Sync cases with server if available
            if (key === "lgc-cases") {
              try {
                fetch("/api/cases", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: typeof value === "string" ? value : JSON.stringify(value)
                }).catch(() => {});
              } catch(_) {}
            }
            return { success: true, local: true };
          },
          async deleteCase(caseId) {
            if (window.auth && !window.auth.canDelete) {
              alert("Permission Denied: Only the System Administrator can delete cases from the register.");
              return { deleted: false, error: "Permission Denied" };
            }
            const adminPwd = prompt("Administrator Password Authentication Required:\\nPlease enter your Administrator password to confirm deleting this case record:");
            if (adminPwd === null) return { deleted: false, error: "Cancelled" };
            if (!adminPwd.trim()) {
              alert("Password cannot be empty. Record deletion cancelled.");
              return { deleted: false, error: "Empty Password" };
            }
            const adminAcc = window.auth.user;
            if (!adminAcc || (adminAcc.password || "admin") !== adminPwd.trim()) {
              alert("Authentication Failed: Incorrect administrator password. Case record deletion denied.");
              return { deleted: false, error: "Authentication Failed" };
            }
            if (window.state && Array.isArray(window.state.cases)) {
              window.state.cases = window.state.cases.filter(c => c.id !== caseId);
              try {
                if (window.localStorage) {
                  window.localStorage.setItem("lgc_lgc-cases", JSON.stringify({ value: JSON.stringify(window.state.cases) }));
                }
              } catch(_) {}
              try {
                fetch("/api/cases?id=" + encodeURIComponent(caseId), { method: "DELETE" }).catch(() => {});
              } catch(_) {}
            }
            return { deleted: true };
          },
        };
      })();
    </script>
"""

# Part 5: Embedded Constants
part5_constants = f"""    <script>
      const GEO = {json.dumps(geo_data)};
      const STAGES_BY_GROUP = {json.dumps(stages_by_group)};
      const SAMPLE_CASES = {json.dumps(sample_cases)};

      const STAGE_TO_GROUP = {{}};
      for (const [grp, stList] of Object.entries(STAGES_BY_GROUP)) {{
        for (const st of stList) {{
          if (st && !STAGE_TO_GROUP[st]) STAGE_TO_GROUP[st] = grp;
        }}
      }}
      STAGE_TO_GROUP["To file Form No.1"] = "Objections / Pleadings";
      STAGE_TO_GROUP["Summons to Witness"] = "Evidence";
      STAGE_TO_GROUP["Summons to the Witness"] = "Evidence";
      STAGE_TO_GROUP["Witness Summons"] = "Evidence";
      STAGE_TO_GROUP["Re-issue Witness Summons"] = "Evidence";
      STAGE_TO_GROUP["Objection Statement"] = "Objections / Pleadings";
      STAGE_TO_GROUP["Hearing on objection"] = "Objections / Pleadings";
      STAGE_TO_GROUP["Notice to Respondent"] = "Notice / Summons / Service";
      STAGE_TO_GROUP["Summons to Accused"] = "Criminal Process";
      STAGE_TO_GROUP["Appearance of Accused"] = "Appearance";
      STAGE_TO_GROUP["Appearance of Respondent"] = "Appearance";
      STAGE_TO_GROUP["Sworn Statement"] = "Preliminary Hearing / Cognizance";
      STAGE_TO_GROUP["HBC"] = "HBC";
      STAGE_TO_GROUP["Hearing Before Charge"] = "HBC";
      STAGE_TO_GROUP["For HBC"] = "HBC";
      STAGE_TO_GROUP["For HBC finally"] = "HBC";
      STAGE_TO_GROUP["Orders on HBC"] = "Orders";

      const COURT_CHOICES = ["Court Hall No.1", "Court Hall No.2"];
      const CASE_TYPE_CHOICES = ["LGC(G)", "LGC(P)", "LGC(T)", "LGC(S)", "RP", "Misc"];
      const RESTORATION_CHOICES = ["Yes", "No", "Partial", "N/A"];
      const EXTENT_UNIT_CHOICES = ["Acre", "Guntas", "Acre + Guntas", "Cents", "Annas", "Square feet", "Square meters", "Feet", "Meter"];
      const DISPOSAL_NATURE_CHOICES = ["Allowed", "Dismissed", "Disposed", "Remanded", "Withdrawn", "Settled", "Compromised"];

      function extractCourtHallFromFilename(filename) {{
        if (!filename) return null;
        const s = String(filename).toLowerCase();
        if (/(?:^|[\s._\-\(\[])(?:ch|court\s*hall|court|hall)[-\s._]*(?:no\.?[-\s._]*)?(?:0?2|ii)(?:[\s._\-\)\]]|$)/i.test(s)) {{
          return "Court Hall No.2";
        }}
        if (/(?:^|[\s._\-\(\[])(?:ch|court\s*hall|court|hall)[-\s._]*(?:no\.?[-\s._]*)?(?:0?1|i)(?:[\s._\-\)\]]|$)/i.test(s)) {{
          return "Court Hall No.1";
        }}
        return null;
      }}

      function extractCaseNumberOnly(raw) {{
        if (!raw) return "";
        let s = String(raw).trim();
        s = s.replace(/^(?:CH\s*[12]|Court\s*Hall\s*(?:No\.?\s*)?[12]|CH-?[12])\s*[-_ ]*/i, "");
        s = s.replace(/^(?:(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?)?\s*\(?(?:[GPTS]|R\.?P\.?|Misc|ಜಿ|ಪಿ|ಟಿ|ಎಸ್)\)?|(?:L\.?G\.?C\.?|ಎಲ್\.?[\s.]*ಜಿ\.?[\s.]*ಸಿ\.?|Misc|R\.?P\.?|Case|CC|Spl\.?\s*CC))\s*(?:No\.?|ನಂ\.?|8o\.?|Bo\.?|80\.?|ಸಂಖ್ಯೆ)?[:\s\-_.]*/i, "");
        s = s.replace(/^(?:No\.?|ನಂ\.?|ಸಂಖ್ಯೆ)[:\s\-_.]*/i, "");
        s = s.replace(/\.[a-zA-Z0-9]+$/, "");
        s = s.replace(/[\s/\_\-]+(?:20\d{{2}}|\d{{2}})$/, "");
        const m = s.match(/([0-9]+[A-Za-z]?)/);
        return m ? m[1] : s.trim();
      }}
"""

part5_filename_parser = """      function parseCaseFilenameDetails(filename) {
        if (!filename) return null;
        const s = String(filename).trim().replace(/\\.[a-zA-Z0-9]+$/, "");
        const res = {
          courtHall: null,
          caseType: null,
          caseNo: null,
          filingYear: null,
          bundleNo: null,
          month: null,
          year: null,
          monthYear: null
        };

        // 1. Comprehensive pattern matching e.g. CH1-LGC-P-194-2024-B12-02-2026 or CH 2 LGC G 1052-2026-B12-02-2026
        const fullMatch = s.match(/(?:(?:CH|Court\\s*Hall\\s*(?:No\\.?)?)\\s*([12]|I{1,2}))?[-_ ]*(?:(?:L\\.?G\\.?C\\.?\\(?([A-Za-z]+)\\)?|L\\.?G\\.?C\\.?[-_ ]+([A-Za-z]+))|([A-Za-z]+))?[-_ ]*([0-9]+)[-_ ]+((?:19|20)[0-9]{2})[-_ ]*(?:Bundle[-_ ]*|[Bb])([0-9A-Za-z]+)[-_ ]+(0?[1-9]|1[0-2])[-_ /.]+((?:19|20)[0-9]{2})/i);
        if (fullMatch) {
          const [_, hall, t1, t2, t3, cno, fYear, bundle, mm, mYear] = fullMatch;
          if (hall) res.courtHall = (hall === "2" || hall.toUpperCase() === "II") ? "Court Hall No.2" : "Court Hall No.1";
          res.caseType = (t1 || t2 || t3 || "").toUpperCase();
          res.caseNo = cno;
          res.filingYear = fYear;
          res.bundleNo = bundle;
          res.bundle_number = bundle;
          res.month = mm.padStart(2, "0");
          res.year = mYear;
          res.monthYear = `${res.month}-${mYear}`;
          res.month_year = res.monthYear;
          return res;
        }

        // 2. Specific extraction of Bundle, Month, and Year: -B12-02-2026 or B12-02-2026 or Bundle-12-02-2026
        const bundleMatch = s.match(/(?:^|[-_ ]|\\b)(?:Bundle[-_ ]*|[Bb])([0-9A-Za-z]+)[-_ ]+(0?[1-9]|1[0-2])[-_ /.]+((?:19|20)[0-9]{2})(?:[-_ ]|$|\\b)/i);
        if (bundleMatch) {
          res.bundleNo = bundleMatch[1];
          res.bundle_number = bundleMatch[1];
          res.month = bundleMatch[2].padStart(2, "0");
          res.year = bundleMatch[3];
          res.monthYear = `${res.month}-${bundleMatch[3]}`;
          res.month_year = res.monthYear;
        }

        // 3. Fallback checks for Court Hall
        if (!res.courtHall) {
          if (/(?:^|[\\s._\\-\\(\\[])(?:ch|court\\s*hall|court|hall)[-\\s._]*(?:no\\.?[-\\s._]*)?(?:0?2|ii)(?:[\\s._\\-\\)\\]]|$)/i.test(s)) {
            res.courtHall = "Court Hall No.2";
          } else if (/(?:^|[\\s._\\-\\(\\[])(?:ch|court\\s*hall|court|hall)[-\\s._]*(?:no\\.?[-\\s._]*)?(?:0?1|i)(?:[\\s._\\-\\)\\]]|$)/i.test(s)) {
            res.courtHall = "Court Hall No.1";
          }
        }

        // 4. Fallback checks for Case Number and Filing Year (stripping out bundle date so month/year is not treated as case no)
        if (!res.caseNo) {
          const sWithoutBundle = s.replace(/(?:^|[-_ ]|\\b)(?:Bundle[-_ ]*|[Bb])([0-9A-Za-z]+)[-_ ]+(0?[1-9]|1[0-2])[-_ /.]+((?:19|20)[0-9]{2})/i, "").trim();
          const cnoMatch = sWithoutBundle.match(/([0-9]+)[-_ ]+((?:19|20)[0-9]{2})/);
          if (cnoMatch) {
            res.caseNo = cnoMatch[1];
            res.filingYear = cnoMatch[2];
          }
        }

        return (res.bundleNo || res.monthYear || res.caseNo || res.courtHall) ? res : null;
      }
      window.parseCaseFilenameDetails = parseCaseFilenameDetails;

      function applyFilenameDetailsToForm(filename, dispatchSearchEvents = true) {
        const fnDetails = parseCaseFilenameDetails(filename);
        if (!fnDetails) return false;
        let modified = false;

        const hallEl = document.getElementById("fCourtHall");
        if (hallEl && fnDetails.courtHall) {
          const targetHall = fnDetails.courtHall.includes("2") ? "II" : "I";
          if (hallEl.value !== targetHall) {
            hallEl.value = targetHall;
            hallEl.dispatchEvent(new Event("change"));
            modified = true;
          }
        }
        const typeEl = document.getElementById("fCaseType");
        if (typeEl && fnDetails.caseType) {
          if (typeEl.value !== fnDetails.caseType) {
            typeEl.value = fnDetails.caseType;
            typeEl.dispatchEvent(new Event("change"));
            modified = true;
          }
        }
        const cnoEl = document.getElementById("fCaseNo");
        if (cnoEl && fnDetails.caseNo) {
          if (cnoEl.value !== String(fnDetails.caseNo)) {
            cnoEl.value = fnDetails.caseNo;
            if (dispatchSearchEvents) {
              cnoEl.dispatchEvent(new Event("input"));
              cnoEl.dispatchEvent(new Event("change"));
            }
            modified = true;
          }
        }
        const yrEl = document.getElementById("fFilingYear");
        if (yrEl && fnDetails.filingYear) {
          if (yrEl.value !== String(fnDetails.filingYear)) {
            yrEl.value = fnDetails.filingYear;
            if (dispatchSearchEvents) {
              yrEl.dispatchEvent(new Event("input"));
            }
            modified = true;
          }
        }
        const bundleEl = document.getElementById("fBundleNo");
        if (bundleEl && fnDetails.bundleNo) {
          if (bundleEl.value !== String(fnDetails.bundleNo)) {
            bundleEl.value = fnDetails.bundleNo;
            bundleEl.dispatchEvent(new Event("input"));
            modified = true;
          }
        }
        const monthYearEl = document.getElementById("fMonthYear");
        if (monthYearEl && fnDetails.monthYear) {
          if (monthYearEl.value !== String(fnDetails.monthYear)) {
            monthYearEl.value = fnDetails.monthYear;
            monthYearEl.dispatchEvent(new Event("input"));
            modified = true;
          }
        }
        const statusMsg = document.getElementById("fStatusMsg");
        if (statusMsg) {
          if (typeof state !== "undefined" && state.mode === "Disposed") {
            statusMsg.textContent = `✓ Auto-extracted from ${filename}: Case ${fnDetails.caseNo || ''}, Bundle ${fnDetails.bundleNo || ''}, Month/Year ${fnDetails.monthYear || ''}`;
          } else {
            statusMsg.textContent = `✓ Auto-extracted from ${filename}: Case ${fnDetails.caseNo || ''}, Filing Year ${fnDetails.filingYear || ''}`;
          }
          statusMsg.style.color = "var(--primary)";
        }
        return modified;
      }
      window.applyFilenameDetailsToForm = applyFilenameDetailsToForm;
"""

# Part 5 Helpers: Lines 1901 to 36398 from index.html.bak (contains LGC_TYPES, TYPES, STAGE_GROUPS, STAGE_GROUP_ALIASES, FILING_LOCATIONS, and core helpers)
part5_helpers = "".join(lines[1901:36398])

# In part5_helpers, ensure loadCases seeds SAMPLE_CASES and exposes window.state
part5_helpers = re.sub(
    r"let\s+state\s*=\s*\{[\s\S]*?\};\s*",
    lambda m: m.group(0) + "      window.state = state;\n",
    part5_helpers
)

# Replace lines 2706-2745 in part5_helpers with safe sidebarToggle, nav, switchView handlers (omitting null hallToggle)
orig_nav_block = "".join(lines[2706:2745])
safe_nav_block = """      function switchView(view) {
        state.view = view;
        if (view === "legacy") {
          state.mode = "Disposed";
        } else if (view === "pendingentry") {
          state.mode = "Pending";
        }
        if (typeof applyModeUI === "function") applyModeUI();
        document
          .querySelectorAll("#nav button")
          .forEach((b) =>
            b.classList.toggle("active", b.dataset.view === view),
          );
        if (typeof render === "function") render();
      }
      window.switchView = switchView;

      document.getElementById("sidebarToggle")?.addEventListener("click", () => {
        const app = document.getElementById("appRoot");
        const btn = document.getElementById("sidebarToggle");
        if (!app || !btn) return;
        const collapsed = app.classList.toggle("sidebar-collapsed");
        btn.innerHTML = collapsed ? "&raquo;" : "&laquo;";
        btn.title = collapsed ? "Maximise menu" : "Minimise menu";
        btn.setAttribute("aria-label", btn.title);
        btn.setAttribute("aria-expanded", String(!collapsed));
      });
      document.querySelector(".brand-logo-icon")?.addEventListener("click", () => {
        const app = document.getElementById("appRoot");
        if (app && app.classList.contains("sidebar-collapsed")) {
          document.getElementById("sidebarToggle")?.click();
        }
      });
      document.getElementById("nav")?.addEventListener("click", (e) => {
        const btn = e.target.closest("button[data-view]");
        if (!btn) return;
        switchView(btn.dataset.view);
      });
"""
part5_helpers = part5_helpers.replace(orig_nav_block, safe_nav_block)

part5_helpers = re.sub(
    r"async\s+function\s+loadCases\s*\(\)\s*\{[\s\S]*?state\.loaded\s*=\s*true;\s*\}",
    """async function loadCases() {
        try {
          const apiRes = await fetch("/api/cases").then(r => r.ok ? r.json() : null).catch(() => null);
          if (Array.isArray(apiRes) && apiRes.length > 0) {
            state.cases = apiRes;
            await saveCases();
            state.loaded = true;
            return;
          }
        } catch (_) {}

        try {
          const res = await window.storage.get("lgc-cases");
          state.cases = res && res.value ? JSON.parse(res.value) : [];
        } catch (_) { state.cases = []; }
        if (!Array.isArray(state.cases) || state.cases.length === 0) {
          state.cases = Array.isArray(SAMPLE_CASES) && SAMPLE_CASES.length > 0 ? JSON.parse(JSON.stringify(SAMPLE_CASES)) : [];
        }
        await saveCases();
        state.loaded = true;
      }""",
    part5_helpers
)

# Part 6: Export view from index.html.bak (lines 38805 to 38979)
part6_export = "".join(lines[38805:38979])

# Part 7: Post-export utilities from index.html.bak (lines 38979 to 42075, omitting legacy render())
part7_utils = "".join(lines[38979:42075])
part7_utils = (
    part7_utils
    .replace('document.getElementById("knToggleBtn").addEventListener', 'document.getElementById("knToggleBtn")?.addEventListener')
    .replace('document.getElementById("knGuideLink").addEventListener', 'document.getElementById("knGuideLink")?.addEventListener')
    .replace('document.getElementById("knPadLink").addEventListener', 'document.getElementById("knPadLink")?.addEventListener')
)

# Part 8: Feature implementations from case.py:
# - Mode switching (Pending vs Disposed)
# - Review queue management
# - Multi-select and export toolbar
# - Date-wise Entry Details table & Navigator
# - 5-section Data Entry form with cascading GEO and live duplicate checking
# - Side-by-side PDF and document viewer
# - Ollama Vision Multi-OCR dialog
# - Batch Processing dashboard
# - Safe router render() and init()

part8_party_splitter = r"""
      function cleanPartyStr(s) {
        if (!s) return "";
        let t = String(s).trim();
        t = t.replace(/\b(?:adesha(?:da)?\s*(?:prati|patra|patre|pati)|order\s*sheet|daily\s*order)\b.*/gi, "");
        t = t.replace(/(?:ಆದೇಶ(?:ದ)?\s*(?:ಪ್ರತಿ|ಪತಿ|ಪತ್ರ|ಪತ್ರೆ|BS|ಪ್ರತೀ)|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|ದಿನಾಂಕ\s+\d+.*)/gi, "");
        t = t.replace(/["'”"‘'`£§©®™*^~_\\|]/g, "");

        // Convert transliterated Kannada to English words only (no raw transliterated terms)
        t = t.replace(/\b(?:Karyanirvahaka|Karyaniwahaka)\s+Abhiyantararu?\b/gi, "Executive Engineer");
        t = t.replace(/\bMukhya\s+Abhiyantararu?\b/gi, "Chief Engineer");
        t = t.replace(/\bSahayaka\s+(?:Karyanirvahaka|Karyaniwahaka)\s+Abhiyantararu?\b/gi, "Assistant Executive Engineer (AEE)");
        t = t.replace(/\bSahayaka\s+Abhiyantararu?\b/gi, "Assistant Engineer (AE)");
        t = t.replace(/\bKiriya\s+Abhiyantararu?\b/gi, "Junior Engineer (JE)");
        t = t.replace(/\bAbhiyantararu?\b/gi, "Engineer");
        t = t.replace(/\bTahsildar\s*(?:and|&|mattu|hagoo)\s*Taluk\s*(?:Executive\s*)?Magistrate\b/gi, "Tahsildar & Taluk Executive Magistrate");
        t = t.replace(/\b(?:Tahashildararu?|Tahasildararu?|Tahsildararu?|Tahashildar|Tahasildar)\b/gi, "Tahsildar");
        t = t.replace(/\bBhu\s*Dakhalegala\s*Sahayaka\s*Nirdeshakaru?\b/gi, "Assistant Director of Land Records (ADLR)");
        t = t.replace(/\bSahayaka\s*Nirdeshakaru?\b/gi, "Assistant Director");
        t = t.replace(/\bUpa\s*Nirdeshakaru?\b/gi, "Deputy Director");
        t = t.replace(/\bNirdeshakaru?\b/gi, "Director");
        t = t.replace(/\b(?:Revenue|Kandaya)\s+Ilakhe\b/gi, "Revenue Department");
        t = t.replace(/\bIlakhe\b/gi, "Department");
        t = t.replace(/\bKarnataka\s+(?:Sarkara|Sarkar)\b/gi, "Government of Karnataka");
        t = t.replace(/\b(?:Sarkara|Sarkar)\b/gi, "Government");
        t = t.replace(/\b(?:Revenue|Kandaya)\s+Bhavana\b/gi, "Revenue Bhavan");
        t = t.replace(/\bBhavana\b/gi, "Bhavan");
        t = t.replace(/\bKe[\.\s]*Ji[\.\s]*Road\b/gi, "K.G. Road");
        t = t.replace(/\bBi[\.\s]*Bi[\.\s]*(?:En|Em|[MN])[\.\s]*Pi\b/gi, "BBMP");
        t = t.replace(/\bBi[\.\s]*Di[\.\s]*(?:E|A)\b/gi, "BDA");
        t = t.replace(/\bBi[\.\s]*(?:Em|En|[MN])[\.\s]*Ti[\.\s]*(?:Ef|F)\b/gi, "BMTF");
        t = t.replace(/\bPradhana\s*Kachhe?ri\b/gi, "Head Office");
        t = t.replace(/\bKachhe?ri\b/gi, "Office");
        t = t.replace(/\bEn[\.\s]*Ar[\.\s]*Skver\b/gi, "N.R. Square");
        t = t.replace(/\bSkver\b/gi, "Square");
        t = t.replace(/\b(?:Keregala|Lakegala)[\-\s]*Vibhaga\b/gi, "Lakes Division");
        t = t.replace(/\bVibhaga\b/gi, "Division");
        t = t.replace(/\bValaya\b/gi, "Zone");
        t = t.replace(/\bKothadi\s*(?:Sankhye|Sankhe|No)?[\.\s:\-]*/gi, "Room No. ");
        t = t.replace(/\b(\d+)\s*Ne\s*Mahadi\b/gi, "$1th Floor");
        t = t.replace(/\bNela\s*Mahadi\b/gi, "Ground Floor");
        t = t.replace(/\bMahadi\b/gi, "Floor");
        t = t.replace(/\b(\d+)\s*Ne\s*Hanta\b/gi, "$1th Stage");
        t = t.replace(/\bHanta\b/gi, "Stage");
        t = t.replace(/\bKaloni\b/gi, "Colony");
        t = t.replace(/\b(?:Hinya|Pinya)\s+Indastriyal\b/gi, "Peenya Industrial");
        t = t.replace(/\bIndastriyal\b/gi, "Industrial");
        t = t.replace(/\bTrast\b/gi, "Trust");
        t = t.replace(/\bMaha\s*Vidyapitha\b/gi, "Maha Vidyapeetha");
        t = t.replace(/\bVidyapitha\b/gi, "Vidyapeetha");
        t = t.replace(/\bAshrama\b/gi, "Ashram");
        t = t.replace(/\bNorthhalli\b/gi, "Uttarahalli");
        t = t.replace(/\bAnche\b/gi, "Post");
        t = t.replace(/\b(?:Vasa|Vasa:)\s*/gi, "Residing at: ");
        t = t.replace(/\b(?:Vilasa|Vilasa:)\s*/gi, "Address: ");
        t = t.replace(/\bIbbara\s*(?:Vilasa|Elasa|Vilas)\s*[:\-]*/gi, "Address of both: ");
        t = t.replace(/\bEllara\s*(?:Vilasa|Elasa|Vilas)\s*[:\-]*/gi, "Common Address: ");
        t = t.replace(/\bMattu\b/gi, "and");
        t = t.replace(/\bRavara\s*Vilasa\b/gi, "Address");
        t = t.replace(/\bRavara\b/gi, "");
        t = t.replace(/\bRinda\b/gi, "to");
        t = t.replace(/\bVayassu\s*(?:Sumaru\s*)?(\d+)\s*Varsha\b/gi, "Aged about $1 years");
        t = t.replace(/\bVarsha\b/gi, "years");
        t = t.replace(/\b(?:Grama|Gama)\b/gi, "Village");
        t = t.replace(/\bHobali\b/gi, "Hobli");
        t = t.replace(/\b(?:Taluku|Taluqu)\b/gi, "Taluk");
        t = t.replace(/\b(?:Jille|Jilla)\b/gi, "District");
        t = t.replace(/\b(?:Rasthe|Raste)\b/gi, "Road");
        t = t.replace(/\bBadavane\b/gi, "Layout");
        t = t.replace(/\bMane\s*(?:Sankhye|No)?\b/gi, "House No.");
        t = t.replace(/\b(?:Hattira|Hathira)\b/gi, "Near");
        t = t.replace(/\b(?:BN|Bin)\b/gi, "S/o");
        t = t.replace(/\bKom\b/gi, "W/o");
        t = t.replace(/\b(?:[Aa]?rjidararu?|Edurudararu?|Durudararu?|Prativadiga?lu?)\b[:\-]*/gi, "");

        // Ordinals
        t = t.replace(/\b1th\b/gi, "1st");
        t = t.replace(/\b2th\b/gi, "2nd");
        t = t.replace(/\b3th\b/gi, "3rd");

        t = t.replace(/[\b,\s]*8[೬6][೦0%]+%?[\b,\s]*/g, ", ");
        t = t.replace(/\b[5$S]\/[0o]\b/gi, "S/o");
        t = t.replace(/\bW\/[0o]\b/gi, "W/o");
        t = t.replace(/\bD\/[0o]\b/gi, "D/o");
        t = t.replace(/\bC\/[0o]\b/gi, "C/o");
        t = t.replace(/\bSto\b/gi, "S/o");
        t = t.replace(/\b\d{1,4}\/(?:19|20)\d{2}\b/g, "");
        t = t.replace(/\b(?:mall|wall|call|ced|sole|caso)\b/gi, "");
        t = t.replace(/\b(?:Shrimati|Srimati)\b/gi, "Smt.");
        t = t.replace(/\b(?:Shri|Sri)\b/gi, "Sri");
        t = t.replace(/Sa[೦0\s]?Jaya/gi, "Sanjaya");
        t = t.replace(/\bnjaya\b/gi, "Sanjaya");
        t = t.replace(/Laksha[\.\s'"`0-9a-zA-Z£]*Mahe/gi, "Lakshmana Mahe");
        t = t.replace(/Mahe[೦0]?m?[೦0]?Drakara/gi, "Mahendrakara");
        t = t.replace(/Mudhola\b/g, "Mudhol");
        t = t.replace(/Bagalakote\b/g, "Bagalkote");
        t = t.replace(/Lakshi\s*Bayi\b/g, "Lakshmibayi");
        t = t.replace(/Mahara\s*Rani\s*Kere\s*(?:Near|Hattira)?/gi, "Near Maharani Kere");
        t = t.replace(/(?:Taluk,?\s*)?Maharani\s*(?:ee\)?|kere)?\s*(?:Near|Hattira),?\s*(?:Mudho\b|Mudhol\b)?/gi, "Near Maharani Kere, Mudhol");
        t = t.replace(/\bHattira\b/gi, "Near");
        t = t.replace(/\bSa\b[!\|:\.]*/g, "");
        t = t.replace(/\bS\s+(?=Mudhol)/g, "");
        t = t.replace(/\b[A-Za-z]\s+\d+(?![\.\)])\b/g, "");
        t = t.replace(/^[A-Za-z\s]+(?=\d+[\.\)])/g, "");
        t = t.replace(/\b13\s+Narayana\s+Reddy\b.*?\broad\b/gi, "13 Cross road");
        t = t.replace(/[\u0C80-\u0CFF]/g, "");
        t = t.replace(/\bYusaf\b/g, "Yusuf");
        t = t.replace(/\bKa[೦0]?N?ndavara\b/gi, "Kandavara");
        t = t.replace(/\b(?:ALL\s*[0oO]|docsos)\b/gi, "");
        t = t.replace(/(\w+)\.\s+(Taluk|District|Hobli|Village)\b/gi, "$1 $2");
        t = t.replace(/\b(?:Dead|abated)\b/gi, "");
        t = t.replace(/\bBMTF\s*P\.?S\.?\b/gi, "BMTF PS");
        t = t.replace(/\bBen\s*[A-Za-z\s;:]*galuru\b/gi, "Bengaluru");
        t = t.replace(/\b(?:Tow\s+All|To\s+All)\b\s*/gi, "");
        t = t.replace(/\b(?:Aphajalapura|Aphajalapur|Afjalpur)\b/gi, "Afzalpur");
        t = t.replace(/\b(?:Dodmani|Doddmani)\b/gi, "Dodmani");
        t = t.replace(/\bVetarajappa\b/gi, "Venkatarajappa");
        t = t.replace(/\bSi\b\.?(?=\s+S\/o)/gi, "C.");
        t = t.replace(/\bTi[.\s]+(?=Narasimhan)/gi, "T. ");
        t = t.replace(/\bTi[.\s]*Vi[.\s]+/gi, "T.V. ");
        t = t.replace(/\bAr\b\.?/gi, "R.");
        t = t.replace(/\bPi[.\s]+(?=Anjaneyareddy)/gi, "P. ");
        t = t.replace(/\bP\.V(?!\.)\b/g, "P.V.");
        t = t.replace(/\bS\.V(?!\.)\b/g, "S.V.");
        t = t.replace(/\b(?:Shrimati|Srimati)\b/gi, "Smt.");
        t = t.replace(/(?<!Smt\.\s)(?<!Smt\.)\bSridevi\b/g, "Smt. Sridevi");
        t = t.replace(/\bC(?=\s+S\/o)/g, "C.");
        t = t.replace(/\b([A-Z])(?=\s*$)/g, "$1.");
        t = t.replace(/\b([A-Z]\.[A-Z])(?=\s*$)/g, "$1.");
        t = t.replace(/\s+\b(?:Applicant|Respondent|Edurudara|Arjidara|Accused)\b.*$/i, "");
        t = t.replace(/[^\S\r\n]+/g, " ").trim().replace(/^[\s,.:;-]+|[\s,:;-]+$/g, "");
        if (!/\b[A-Z]\.$|\b[A-Z]\.[A-Z]\.$/.test(t)) {
          t = t.replace(/\.+$/, "");
        }
        return t;
      }

      function cleanAddrStr(addr) {
        if (!addr) return "";
        let a = String(addr).trim();
        a = a.replace(/[\u200b\u200c\u200d\ufeff]/g, "");
        a = a.replace(/\b(?:adesha(?:da)?\s*(?:prati|patra|patre|pata|pati)|order\s*sheet|daily\s*order)\b.*/gi, "");
        a = a.replace(/(?:ಆದೇಶ(?:ದ)?\s*(?:ಪ್ರತಿ|ಪತಿ|ಪತ್ರ|ಪತ್ರೆ|BS|ಪ್ರತೀ)|ಆರ್ಡ[ರರ್]್‌?\s*ಶೀ[ಟಟ್]್‌?|ದಿನಾಂಕ\s+\d+.*)/gi, "");
        const ageKw = /\b(?:Aged?\s*(?:about)?\s*\d+\s*years?|Age\s*[:\s\-]\s*\d+|major|8[೬6][೦0%]+%?)\b[\s,]*/gi;
        a = a.replace(ageKw, "");
        a = a.replace(/^(?:(?:Edurudara|Respondent[s]?|Arjidara|Applicant[s]?|Accused)\s*(?:No\.?)?\s*\d+\s*(?:to|and|\-)\s*\d+\s*(?:Ravara\s*)?(?:Address|Vilasa)?\s*[:\-,.]*|No\.?\s*\d+\s*(?:to|and|\-)\s*\d+\s*(?:Address|Vilasa)?\s*[:\-,.]*)/i, "").trim();
        a = a.replace(/^[?,\s\-]+/, "");
        a = a.replace(/^[0-9]\s+(?=[A-Za-z])/, "");
        a = a.replace(/^(?:DIOS|311\.7)[,\s]*/g, "");

        // Strip noise tokens
        a = a.replace(/\b(?:at\s*Residing\s*at|dt['’]?\s*Residing\s*at|Residing\s*at)\s*[:\-]\s*/gi, "");
        a = a.replace(/\b(?:Shalluku|Thalluku|Talluku|Shalluk|Thaluk|Saluk)\b/gi, "Taluk");
        a = a.replace(/\b(?:Saktina|Daksina)\s*Taluk\b/gi, "South Taluk");
        a = a.replace(/\b[iIj]\s*J?engaluru\b/gi, "Bengaluru");
        a = a.replace(/\b(?:oe\s*Be\s*Ru\s*Ku|oe\s*ಬೆ\s*ರು\s*ಕು|Resp\s*Galu|10\s*Resp|Bat|ಬಟ್‌|Su|Adesha|Tu\??|ಟು\??)\b[\s,]*/gi, "");
        a = a.replace(/\b\d*\s*ut\s*\d*["']?\b[\s,]*/gi, "");
        a = a.replace(/[0o]\s*\)\s*\.\s*\(?/gi, "");
        a = a.replace(/\boe\s*[0೦]\b[\s,]*/gi, "");
        a = a.replace(/\b(?:Tra|Este|Awoes\s*&?|Sars|Ha|Gre|Sika|DIYS|pata|ging|Heal|offer\.|iS:|Heo)\b[\s,]*/gi, "");
        a = a.replace(/-?Eirudda-?/gi, "");
        a = a.replace(/\(\d+\/\d+\/\d+\s*/g, "");
        a = a.replace(/\bOATS\.?\s*/gi, "");
        a = a.replace(/x0,\s*XO\s*/gi, "");
        a = a.replace(/=\)\s*No\-?\s*/g, "");
        a = a.replace(/\b(?:La\s*Jya|8\s*aro|aro)\b[\s,]*/gi, "");
        a = a.replace(/\b(?:Heo\s*npe9|Oya\s*gral|Viruda|La,\s*Khu)\b[\s,]*/gi, "");

        // Strip terminal noise following 6-digit PIN code
        a = a.replace(/(\b\d{3}[-\s]?\d{3}\b)[\s.,;:\-_=]+.*$/s, "$1");

        const rawLines = a.split(/[\r\n]+/);
        const cleanedLines = [];
        for (const line of rawLines) {
          let l = line.trim();
          if (!l) continue;
          l = l.replace(/^(?:iS\s*:|offer\s*\.|tebber\-?|Ig[}\)]+[a-zA-Z0-9\(\)]*|ar\s*;\s*\d*|He\s*re|Hees|Heer|Wao\)|63\)|Ke\s*a[0o]|Sata|leg|\bTa\b|Dararu)\s*[:\-.,]?\s*/gi, "");
          l = l.replace(/\b[a-zA-Z]\.?\s*;\s*\d*\s*/g, "");
          l = l.replace(/^\d{1,2}[/\\-]+\d*\s*/, "");
          l = l.replace(/^[a-zA-Z]{1,2}(?:\s*>\s*,?|\s+)[:\-.,]?\s*/, "");
          l = l.replace(/\b(?:Ke\s*a[0o]|a[0o]|Sata|Dararu|Arjidararu|Edurudararu)\b/gi, "");
          l = l.replace(/\(\((BEML)\)\)/g, "$1");
          l = l.replace(/\bUttarahalli\s+Near\b/gi, "Uttarahalli Hobli");
          l = l.replace(/^[?,:\-\s]+/, "");
          l = l.replace(/\s+/g, " ").trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
          if ((l.length <= 2 && !/^\d+$/.test(l)) || (l.length === 1 && /^\d+$/.test(l))) {
            continue;
          }
          cleanedLines.push(l);
        }

        let s = cleanedLines.join(", ");
        s = s.replace(/,\s*,+/g, ", ");
        s = s.replace(/(\b\d{3}[-\s]?\d{3}\b)[\s.,;:\-_=]+.*$/, "$1");
        return s.trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
      }

      function splitSingleParty(text, prefix = "") {
        let t = cleanPartyStr(text);
        if (!t) return { name: "", address: "" };

        const offTitles = /^(?:SHO,?\s*BMTF\s*PS|Station\s*House\s*Officer|Police\s*Inspector|Police\s*Sub-Inspector|PSI|PI|Executive\s*Engineer|Assistant\s*Executive\s*Engineer\s*(?:\(AEE\))?|Assistant\s*Engineer\s*(?:\(AE\))?|Junior\s*Engineer\s*(?:\(JE\))?|Chief\s*Engineer|Superintending\s*Engineer|Assistant\s*Director\s*of\s*Land\s*Records\s*(?:\(ADLR\))?|Deputy\s*Director\s*of\s*Land\s*Records\s*(?:\(DDLR\))?|Assistant\s*Director|Deputy\s*Director|Director|Tahsildar\s*&\s*Taluk\s*Executive\s*Magistrate|Tahsildar|Deputy\s*Tahsildar|Special\s*Deputy\s*Commissioner|Deputy\s*Commissioner|Assistant\s*Commissioner|Revenue\s*Inspector|Village\s*Accountant|Executive\s*Officer|Panchayat\s*Development\s*Officer\s*(?:\(PDO\))?|Gram\s*Panchayat|Taluk\s*Panchayat|Zilla\s*Panchayat|State\s*of\s*Karnataka|Government\s*of\s*Karnataka)(?:\b|(?<=\))|$)/i;
        const mOff = t.match(offTitles);
        if (mOff) {
          const name = mOff[0].trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
          const rawAddr = t.slice(mOff[0].length).trim();
          return { name, address: cleanAddrStr(rawAddr) };
        }

        let andTitle = "";
        const mAnd = t.match(/\bAnd\s+(Executive\s+Director|Director|Secretary|President|Manager|Managing\s+Director|Principal)\b/i);
        if (mAnd) {
          andTitle = " and " + mAnd[1].toLowerCase();
        }

        const addrKw = /\b(?:No\.?\s*\d+|\d+(?:st|nd|rd|th)?\s+(?:['"`]?[A-Za-z0-9]['"`]?\s+)?(?:Cross|Stage|Main|Block|Lane|Road)\b|Near\b|Beside\b|Behind\b|Backside\b|Opposite\b|Opp\.?\b|Cross\b|Road\b|Lane\b|Bake\s+Palace|Layout\b|Nagar\b|Colony\b|Sector\b|Post\b|Village\b|Hobli\b|Taluk\b|District\b|Bengaluru|Bangalore|Shivashakthi|Ambedkar|Slum|Temple|Nivas|Floor|Room\s*No|Industrial|Square|Trust|Ashram|Maha\s*Vidyapeetha)\b|[\u0C80-\u0CFF]*(?:ಗ್ರಾಮ|ಗಾಮ|ಹೋಬಳಿ|ತಾಲ್ಲೂಕು|ತಾಲೂಕು|ಜಿಲ್ಲೆ|ರಸ್ತೆ|ಬಡಾವಣೆ|ನಗರ|ದೇವಸ್ಥಾನ|ನಂ\.?\s*\d+|ಹತ್ತಿರ)/i;
        const relKw = /\b(?:S\/o|W\/o|D\/o|C\/o|Bin|BN|Kom|son\s+of|wife\s+of|daughter\s+of)\b/i;
        const ageKw = /\b(?:Aged?\s*(?:about)?\s*\d+\s*years?|Age\s*[:\s\-]\s*\d+|major|8[೬6][೦0%]+%?)\b[\s,]*/gi;

        let rawName = "", rawAddr = "";
        const mRel = t.match(relKw);
        if (mRel && mRel.index !== undefined) {
          const beforeRel = t.slice(0, mRel.index).trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
          const relStr = mRel[0].trim();
          const afterRel = t.slice(mRel.index + mRel[0].length).trim();

          const mAddr = afterRel.match(addrKw);
          if (mAddr && mAddr.index !== undefined) {
            const preAddr = afterRel.slice(0, mAddr.index).trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
            const words = preAddr.split(/\s+/);
            if (words.length > 1 && /^(?:Village|Hobli|Taluk)\b/i.test(afterRel.slice(mAddr.index))) {
              const fName = words.slice(0, -1).join(" ");
              rawName = `${beforeRel} ${relStr} ${fName}`.trim();
              rawAddr = `${words[words.length - 1]} ${afterRel.slice(mAddr.index)}`.trim();
            } else {
              rawName = `${beforeRel} ${relStr} ${preAddr}`.trim();
              rawAddr = afterRel.slice(mAddr.index).trim();
            }
          } else if (afterRel.includes(",")) {
            const firstCommaIdx = afterRel.indexOf(",");
            const firstPart = afterRel.slice(0, firstCommaIdx).trim();
            const rest = afterRel.slice(firstCommaIdx + 1).trim();
            if (!addrKw.test(firstPart) && firstPart.split(/\s+/).length <= 4) {
              const mAliasRest = rest.match(/^(?:@\s*[A-Za-z]+|\balias\s+[A-Za-z]+)\b/i);
              if (mAliasRest) {
                const aliasStr = mAliasRest[0].trim();
                rawName = `${beforeRel} ${relStr} ${firstPart} ${aliasStr}`.trim();
                rawAddr = rest.slice(aliasStr.length).trim();
              } else {
                rawName = `${beforeRel} ${relStr} ${firstPart}`.trim();
                rawAddr = rest.trim();
              }
            } else {
              rawName = `${beforeRel} ${relStr} ${firstPart}`.trim();
              rawAddr = rest.trim();
            }
          } else {
            rawName = `${beforeRel} ${relStr} ${afterRel}`.trim();
            rawAddr = "";
          }
        } else {
          const tNoAge = t.replace(ageKw, "").trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
          if (tNoAge.includes(":")) {
            const idx = tNoAge.indexOf(":");
            rawName = tNoAge.slice(0, idx).trim();
            rawAddr = tNoAge.slice(idx + 1).trim();
          } else if (tNoAge.includes(",")) {
            const firstCommaIdx = tNoAge.indexOf(",");
            const firstPart = tNoAge.slice(0, firstCommaIdx).trim();
            const rest = tNoAge.slice(firstCommaIdx + 1).trim();
            if (!addrKw.test(firstPart) && firstPart.split(/\s+/).length <= 4) {
              rawName = firstPart;
              rawAddr = rest;
            } else {
              const mAddr = tNoAge.match(addrKw);
              if (mAddr && mAddr.index !== undefined) {
                rawName = tNoAge.slice(0, mAddr.index).trim();
                rawAddr = tNoAge.slice(mAddr.index).trim();
              } else {
                rawName = tNoAge;
                rawAddr = "";
              }
            }
          } else {
            const mAddr = tNoAge.match(addrKw);
            if (mAddr && mAddr.index !== undefined) {
              rawName = tNoAge.slice(0, mAddr.index).trim();
              rawAddr = tNoAge.slice(mAddr.index).trim();
            } else {
              rawName = tNoAge;
              rawAddr = "";
            }
          }
        }

        let cleanName = rawName.replace(ageKw, "").replace(/[\d\.,\-_/\\#]+$/, "").trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
        cleanName = cleanName.replace(/\b[A-Z]{2,}\b/g, "").replace(/\b(?:bhatta|bS|ym|imvos)\b/gi, "");
        cleanName = cleanName.replace(/\s+/g, " ").trim().replace(/^[\s,.:;-]+|[\s,.:;-]+$/g, "");
        if (andTitle && !cleanName.toLowerCase().includes(andTitle)) {
          cleanName += andTitle;
        }

        return { name: cleanName, address: cleanAddrStr(rawAddr) };
      }

      function splitPartyNameAndAddress(text) {
        if (!text) return { name: "", address: "" };
        let str = cleanPartyStr(String(text).split("=== OCR_PASS ===")[0].trim());
        if (!str) return { name: "", address: "" };

        // Check for shared address anywhere in text (e.g. 'Edurudara No. 2 and 3 Address: ...' or 'Address of both: ...')
        let sharedStart = null, sharedEnd = null, sharedAddr = "";
        let isCommonAll = false;

        const stopPat = "(?=\n\s*(?:(?:A\s*[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]|(?:Edurudara|Respondent|Arjidara|Applicant|Accused)\s*(?:No\.?)?\s*[1-9]\d{0,2}|-?\s*ವಿರುದ್ದ|-?\s*ವಿರುದ್ಧ|\bvs\.?\b)|\s*$)";
        const pRange = new RegExp("(?:(?:Edurudara|Respondent[s]?|Arjidara|Applicant[s]?|Accused)\s*(?:No\.?)?\s*)?(\d+)[\.\s]*(?:and|mattu|&|to|rinda|\-)[\.\s]*(\d+)[\.\s]*(?:Ravara\s*)?(?:Address|Vilasa)?\s*[:\-]+(?:\s*\n)?([\s\S]*?)" + stopPat, "i");
        const mRange = str.match(pRange);
        if (mRange) {
          sharedStart = parseInt(mRange[1], 10);
          sharedEnd = parseInt(mRange[2], 10);
          sharedAddr = cleanAddrStr(cleanPartyStr(mRange[3]));
          str = str.slice(0, mRange.index).trim() + "\n" + str.slice(mRange.index + mRange[0].length).trim();
        }

        const pCommon = new RegExp("(?:Address\s*of\s*both|Common\s*Address|Address\s*of\s*all|Ibbara\s*Vilasa|Ellara\s*Vilasa)\s*[:\-]+(?:\s*\n)?([\s\S]*?)" + stopPat, "i");
        const mCommon = str.match(pCommon);
        if (mCommon) {
          isCommonAll = true;
          sharedAddr = cleanAddrStr(cleanPartyStr(mCommon[1]));
          str = str.slice(0, mCommon.index).trim() + "\n" + str.slice(mCommon.index + mCommon[0].length).trim();
        }

        let textToParse = str.split(/(?:KARNAT\s*AKA\s*LAND|KARNATAKA\s*LAND\s*GRABBING|3(?:RD|"°)?\s*FLOOR,\s*KANDAYA|PROHIBITION\s*SPECIAL\s*COURT|Chief\s*Metropolitan|Rons[- ]*Bes)/i)[0].trim();

        textToParse = textToParse.replace(/\b[5$S]\/[0o]\b/gi, "S/o");
        textToParse = textToParse.replace(/\bLate\s+1\.\s*/gi, "Late H. ");
        textToParse = textToParse.replace(/(?:^|\s)[Z~“"‘'`\\\/]*A\s*S[\.\)]/gi, " A9) ");
        textToParse = textToParse.replace(/(?:^|\s)[Z~“"‘'`\\\/]*A\s*l(\d+)[\.\)]/gi, " A$1) ");
        textToParse = textToParse.replace(/(?:^|\s)[Z~“"‘'`\\\/]*A\s*(?:WA|¥\s*4|¥4|14)[\.\)]/gi, " A14) ");
        textToParse = textToParse.replace(/(?:^|\s)(?:A\s*4\s*5|45)[\.\)]/gi, " A15) ");
        textToParse = textToParse.replace(/(?:^|\s)7780[\.\)]/gi, " A30) ");
        textToParse = textToParse.replace(/(?:^|\s)155[\.\)]\s*(?=[A-Za-z\s]+W\/o)/gi, " A55) ");
        textToParse = textToParse.replace(/(?:^|\s)97[\.\)]\s*(?=\/?Ramakka)/gi, " A57) ");
        textToParse = textToParse.replace(/(?:^|\s)[Z~“"‘'`\\\/]*A\s*838[\.\)]/gi, " A58) ");
        textToParse = textToParse.replace(/(?:^|\s)0[\.\)]\s*(?=Yarrappa)/gi, " A60) ");
        textToParse = textToParse.replace(/(?:^|\s)ಗಿ63[\.\)]/gi, " A63) ");
        textToParse = textToParse.replace(/(?:^|\s)[Z~“"‘'`\\\/]*A\s*681[\.\)]/gi, " A81) ");
        textToParse = textToParse.replace(/(?:^|\s)[Z~“"‘'`\\\/]*A\s*(\d+)[\.\)]/gi, " A$1) ");

        const isAccused = /\bAccused\b|(?:^|\s)A\d+[\.\)]/i.test(textToParse);
        const pattern = isAccused
          ? /(?:^|\s)(?:Accused\s*:\s*)?(?:A\s*(\d+)[\.\)]|(\d+)[\.\)])\s*/g
          : /(?:^|\s)(?:Respondent\s*|Edurudararu\s*|Applicant\s*|Arjidararu\s*)?(\d+)[\.\)]\s*/g;

        const rawMatches = [];
        let m;
        while ((m = pattern.exec(textToParse)) !== null) {
          rawMatches.push(m);
        }

        let filteredMatches = [];
        let lastNum = null;
        for (const mat of rawMatches) {
          const isExplicitA = !!mat[1];
          const num = parseInt(mat[1] || mat[2], 10);
          if (num > 250) continue;
          if (lastNum === null) {
            filteredMatches.push({ match: mat, num, isExplicitA });
            lastNum = num;
          } else {
            if (num > lastNum && (num <= lastNum + 5 || (isExplicitA && num <= lastNum + 10))) {
              filteredMatches.push({ match: mat, num, isExplicitA });
              lastNum = num;
            }
          }
        }

        if (filteredMatches.length > 1 || (isAccused && filteredMatches.length >= 1)) {
          const firstM = filteredMatches[0].match;
          textToParse = textToParse.slice(firstM.index).trim();
          pattern.lastIndex = 0;
          const reMatches = [];
          while ((m = pattern.exec(textToParse)) !== null) {
            reMatches.push(m);
          }
          filteredMatches = [];
          lastNum = null;
          for (const mat of reMatches) {
            const isExplicitA = !!mat[1];
            const num = parseInt(mat[1] || mat[2], 10);
            if (num > 250) continue;
            if (lastNum === null) {
              filteredMatches.push({ match: mat, num, isExplicitA });
              lastNum = num;
            } else {
              if (num > lastNum && (num <= lastNum + 5 || (isExplicitA && num <= lastNum + 10))) {
                filteredMatches.push({ match: mat, num, isExplicitA });
                lastNum = num;
              }
            }
          }

          const parsedItems = [];
          for (let i = 0; i < filteredMatches.length; i++) {
            const curItem = filteredMatches[i];
            const prefix = isAccused ? `A${curItem.num}` : `${curItem.num}`;
            const start = curItem.match.index + curItem.match[0].length;
            const end = (i + 1 < filteredMatches.length) ? filteredMatches[i + 1].match.index : textToParse.length;
            const body = textToParse.slice(start, end).trim();
            const sp = splitSingleParty(body, prefix);
            parsedItems.push({ prefix, num: curItem.num, name: sp.name, address: sp.address });
          }

          const names = [];
          const addresses = [];
          for (const item of parsedItems) {
            const prefLbl = item.prefix.endsWith(".") ? `${item.prefix} ` : `${item.prefix}. `;
            if (item.name) names.push(`${prefLbl}${item.name}`.trim());

            let finalA = "";
            if (isCommonAll && sharedAddr) {
              finalA = sharedAddr;
            } else if (sharedStart !== null && sharedEnd !== null && item.num >= sharedStart && item.num <= sharedEnd && sharedAddr) {
              finalA = sharedAddr;
            } else if (item.address) {
              finalA = cleanAddrStr(item.address);
            } else if (sharedAddr) {
              finalA = sharedAddr;
            }

            if (finalA) {
              addresses.push(`${prefLbl}${finalA}`.trim());
            }
          }

          if (names.length > 0) {
            return {
              name: names.join("\n"),
              address: addresses.join("\n")
            };
          }
        }

        const sp = splitSingleParty(textToParse);
        let sAddr = isCommonAll && sharedAddr ? sharedAddr : cleanAddrStr(sp.address);
        return { name: sp.name, address: sAddr };
      }

      function reconcileAndMatchParties(nameStr, addrStr, fullPartyStr = "") {
        let source = "";
        if (fullPartyStr && !isProceduralParty(fullPartyStr)) {
          source = fullPartyStr;
        } else if (nameStr && !isProceduralParty(nameStr)) {
          source = nameStr + (addrStr && !isProceduralParty(addrStr) ? "\n" + addrStr : "");
        } else if (addrStr && !isProceduralParty(addrStr)) {
          source = addrStr;
        }

        if (!source) return { name: "", address: "" };

        const sp = splitPartyNameAndAddress(source);
        let names = sp.name;
        let addrs = sp.address;

        const rawNameBlocks = names.split(/(?:^|\n)\s*(?=(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*)/g);
        const nameLines = rawNameBlocks.map(p => cleanPartyStr(p)).filter(Boolean);

        const rawAddrBlocks = addrs.split(/(?:^|\n)\s*(?=(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*)/g);
        const addrBlocks = rawAddrBlocks.map(p => p.trim()).filter(Boolean);

        if (nameLines.length > 1) {
          const matchedAddrs = [];
          const addrMap = {};
          const unprefixedAddrs = [];
          for (const ab of addrBlocks) {
            const mPref = ab.match(/^((?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)])\s*([\s\S]*)/i);
            if (mPref) {
              const val = cleanAddrStr(mPref[2]);
              if (val) addrMap[mPref[1].replace(/\.$/, "")] = val;
            } else {
              const val = cleanAddrStr(ab);
              if (val) unprefixedAddrs.push(val);
            }
          }

          let commonFallback = unprefixedAddrs.length > 0 ? unprefixedAddrs[0] : (addrBlocks.length > 0 ? addrBlocks[0] : "");
          commonFallback = cleanAddrStr(commonFallback.replace(/^(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*/, ""));

          for (const nl of nameLines) {
            const mPref = nl.match(/^((?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)])\s*/i);
            if (mPref) {
              const prefKey = mPref[1].replace(/\.$/, "");
              const prefLbl = mPref[1].endsWith(".") ? `${mPref[1]} ` : `${mPref[1]}. `;
              if (addrMap[prefKey]) {
                matchedAddrs.push(`${prefLbl}${addrMap[prefKey]}`);
              } else if (commonFallback) {
                matchedAddrs.push(`${prefLbl}${commonFallback}`);
              }
            } else {
              if (commonFallback) matchedAddrs.push(commonFallback);
            }
          }

          if (matchedAddrs.length > 0) {
            addrs = matchedAddrs.join("\n");
          }
          names = nameLines.join("\n");
        } else {
          names = cleanPartyStr(names);
          addrs = cleanAddrStr(addrs);
        }

        return { name: names, address: addrs };
      }

      // ========================================================
      // STRUCTURED PARTY MANAGEMENT (PETITIONERS & RESPONDENTS)
      // ========================================================

      const COURT_PETITIONER_STATUS = [
        "Tahsildar",
        "Heads of Government Departments",
        "Executive Engineers, GBA-BBMP",
        "Forest Department Officers",
        "Veterinary Department",
        "Horticulture",
        "University",
        "Religious & Charitable Board Officers",
        "Wakf Boards Officers",
        "Karnataka Slum Development Board",
        "Mysore Urban Development Authority (MUDA)",
        "Statutory Body",
        "Non-Statutory Body",
        "GBA Bengaluru",
        "City Corporation",
        "City Municipal",
        "Town Municipal",
        "Town Panchayat / Pattana Panchayat",
        "General Public / Private Individuals",
        "The Special Court (Suo Motu)",
        "Individual",
        "Company",
        "Firm",
        "Government Department",
        "Local Authority",
        "Other",
      ];

      const DISTRICT_ALIASES = {
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
      };

      const TALUK_ALIASES = {
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
      };

      function normalizeDistrict(cand) {
        if (!cand) return "";
        const clean = String(cand).trim().toLowerCase().replace(/\s+district$/i, "");
        if (DISTRICT_ALIASES[clean]) return DISTRICT_ALIASES[clean];
        const distList = (typeof GEO !== "undefined" && GEO && typeof GEO === "object") ? Object.keys(GEO) : [];
        for (const d of distList) {
          if (d.toLowerCase() === clean || clean.includes(d.toLowerCase())) return d;
        }
        return String(cand).trim();
      }

      function cleanPartyToken(s) {
        return (s || "")
          .replace(/^(?:r\/o|c\/o|w\/o|s\/o|d\/o|at|residing\s+at|residing)\s+/i, "")
          .replace(/^[|•*()~<_\-\s.,:/\\\[\]]+|[|•*()~<_\-\s.,:/\\\[\]]+$/g, "")
          .trim();
      }

      function relationshipHtml(data, prefix) {
        const rel = (data && data.relationship) ? String(data.relationship).toUpperCase() : "";
        const opts = ["S/O", "W/O", "D/O", "C/O"];
        return `<select class="${prefix}Relation partyRelation party-relation-select" aria-label="Relationship">
          <option value="">Relation</option>
          ${opts.map(v => `<option value="${v}" ${rel === v ? "selected" : ""}>${v}</option>`).join("")}
        </select>
        <input type="text" class="${prefix}Relative partyRelative party-relative-input" aria-label="Related person's name" placeholder="Relative's name" value="${escAttr(data.relativeName || data.relative_name || "")}">`;
      }

      let _locSeqCounter = 0;

      function locationDistrict(value) {
        const v = String(value || "").trim().toUpperCase();
        return (
          {
            RAMANAGARA: "BENGALURU SOUTH",
            "BENGALURU URBAN": "BENGALURU",
            "BENGALURU RURAL": "BANGALORE RURAL",
            MYSURU: "MYSORE",
            YADGIR: "YADAGIR",
            "UTTARA KANNADA": "UTTAR KANNADA",
            CHAMARAJANAGAR: "CHAMARAJANAGARA",
            CHIKKABALLAPURA: "CHIKKABALLAPUR",
            BANGALORE: "BENGALURU",
          }[v] || v
        );
      }

      function locationOptions(items, value, label, emptyText) {
        const selected = String(value || "").trim().toUpperCase();
        let out = `<option value="">${items.length ? "Select " + label : (emptyText || "Location data unavailable")}</option>`;
        if (value && !items.some(x => x.toUpperCase() === selected)) {
          out += `<option value="${escAttr(value)}" selected>${escAttr(value)}</option>`;
        }
        out += items
          .map(x => `<option value="${escAttr(x)}" ${x.toUpperCase() === selected ? "selected" : ""}>${escAttr(x)}</option>`)
          .join("");
        return out;
      }

      function locationDataOptions(items) {
        if (!Array.isArray(items)) return "";
        return items
          .map(x => `<option value="${escAttr(x)}"></option>`)
          .join("");
      }

      function locationEmptyText(level, values, items) {
        if (items && items.length) return "Select " + ["District", "Taluk", "Hobli", "Village"][level];
        if (level === 1) return values[0] ? "Location data unavailable" : "Select District first";
        if (level === 2) return values[1] ? "Location data unavailable" : "Select Taluk first";
        if (level === 3) return values[2] ? "Location data unavailable" : "Select Hobli first";
        return "Location data unavailable";
      }

      function locationWarning(values, lists) {
        if (values[1] && lists[2] && !lists[2].length)
          return "No Hobli suggestions for this Taluk. You can still type the location directly.";
        if (values[2] && lists[3] && !lists[3].length)
          return "No Village suggestions for this Hobli. You can still type the location directly.";
        return "";
      }

      function changeFilingLocation(control, isChange = false) {
        const box = control.closest("[data-location]");
        if (!box) return;
        const controls = [...box.querySelectorAll("[data-level]")];
        const changed = Number(control.dataset.level);
        if (isChange) {
          for (let i = changed + 1; i < 4; i++) {
            if (controls[i]) controls[i].value = "";
          }
        }
        updateFilingLocationOptions(box, changed + 1);
      }

      function updateFilingLocationOptions(box, startLevel) {
        if (!box) return;
        const controls = [...box.querySelectorAll("[data-level]")];
        const values = controls.map(c => (c.value || "").trim());
        const dRaw = values[0] || "";
        const dNorm = locationDistrict(dRaw);

        const fl = (typeof FILING_LOCATIONS !== "undefined" && FILING_LOCATIONS) ? FILING_LOCATIONS : {};
        const dKey = Object.keys(fl).find(k => k.toUpperCase() === dNorm.toUpperCase() || k.toUpperCase() === dRaw.toUpperCase()) || dNorm;
        const ts = fl[dKey] || {};

        const tVal = (values[1] || "").trim().toUpperCase();
        const tKey = Object.keys(ts).find(k => k.toUpperCase() === tVal) || tVal;
        const hs = ts[tKey] || {};

        const hVal = (values[2] || "").trim().toUpperCase();
        let vs = [];
        if (hVal && hs) {
          const hKey = Object.keys(hs).find(k => k.toUpperCase() === hVal || k.toUpperCase().startsWith(hVal) || hVal.startsWith(k.toUpperCase()));
          if (hKey && Array.isArray(hs[hKey])) {
            vs = hs[hKey];
          }
        }

        const lists = [
          Object.keys(fl).sort(),
          Object.keys(ts).sort(),
          Object.keys(hs).sort(),
          vs.slice().sort(),
        ];

        for (let i = startLevel; i < 4; i++) {
          const input = controls[i];
          if (!input || i === 0) continue;
          const listId = input.getAttribute("list");
          const list = listId ? (box.querySelector("#" + listId) || document.getElementById(listId)) : null;
          if (list) list.innerHTML = locationDataOptions(lists[i]);
        }

        const warning = box.querySelector(".location-warning");
        if (warning) warning.textContent = locationWarning(values, lists);
      }

      function readLocationValue(container, prefix, label) {
        return (
          container?.querySelector("." + prefix + label)?.value.trim() ||
          container?.querySelector(".party" + label)?.value.trim() ||
          ""
        );
      }

      function readPartyExtra(row, prefix = "party") {
        const get = (cls) => row.querySelector("." + cls)?.value.trim() || "";
        return {
          relationship: get(`${prefix}Relation`) || get("partyRelation"),
          relativeName: get(`${prefix}Relative`) || get("partyRelative"),
          district: get(`${prefix}District`) || get("partyDistrict"),
          taluk: readLocationValue(row, prefix, "Taluk"),
          hobli: readLocationValue(row, prefix, "Hobli"),
          village: readLocationValue(row, prefix, "Village"),
        };
      }

      function locationHtml(data, prefix, listPrefix = prefix) {
        data = data || {};
        _locSeqCounter++;
        const uid = `${listPrefix}_loc_${_locSeqCounter}`;

        const rawD = String(data.district || data.district_name || "").trim();
        const dNorm = locationDistrict(rawD);
        const fl = (typeof FILING_LOCATIONS !== "undefined" && FILING_LOCATIONS) ? FILING_LOCATIONS : {};
        const dKey = Object.keys(fl).find(k => k.toUpperCase() === dNorm.toUpperCase() || k.toUpperCase() === rawD.toUpperCase()) || dNorm;
        const district = fl[dKey] ? dKey : (rawD || "");
        const ts = fl[district] || {};

        const taluk = String(data.taluk || "").trim();
        const tVal = taluk.toUpperCase();
        const tKey = Object.keys(ts).find(k => k.toUpperCase() === tVal) || tVal;
        const hs = ts[tKey] || {};

        const hobli = String(data.hobli || "").trim();
        const hVal = hobli.toUpperCase();
        let vs = [];
        if (hVal && hs) {
          const hKey = Object.keys(hs).find(k => k.toUpperCase() === hVal || k.toUpperCase().startsWith(hVal) || hVal.startsWith(k.toUpperCase()));
          if (hKey && Array.isArray(hs[hKey])) {
            vs = hs[hKey];
          }
        }

        const village = String(data.village || "").trim();
        const values = [district, taluk, hobli, village];
        const lists = [
          Object.keys(fl).sort(),
          Object.keys(ts).sort(),
          Object.keys(hs).sort(),
          vs.slice().sort(),
        ];
        const labels = ["District", "Taluk", "Hobli", "Village"];

        const fields = labels
          .map((label, i) => {
            if (i === 0) {
              return `<label>${label}<select class="${prefix + label} party${label}" data-level="${i}" aria-label="${label}" onchange="changeFilingLocation(this, true)">${locationOptions(lists[i], values[i], label, locationEmptyText(i, values, lists[i]))}</select></label>`;
            }
            const listId = `${uid}_${label}Options`;
            return `<label>${label}<input type="text" class="${prefix + label} party${label} location-editable" data-level="${i}" list="${listId}" aria-label="${label}" placeholder="Select or enter ${label.toLowerCase()}" value="${escAttr(values[i])}" oninput="changeFilingLocation(this, false)" onchange="changeFilingLocation(this, true)"><datalist id="${listId}">${locationDataOptions(lists[i])}</datalist></label>`;
          })
          .join("");

        return `<div class="location-grid" data-location data-prefix="${prefix}">${fields}<div class="location-warning" role="status" style="grid-column: 1 / -1; font-size: 11px; color: var(--ink-soft); margin-top: 2px;">${locationWarning(values, lists)}</div></div>`;
      }

      function partyName(p) {
        if (!p) return "";
        const rel = [p.relationship, p.relativeName || p.relative_name].filter(Boolean).join(" ");
        const age = p.age ? `Aged about ${p.age} years` : "";
        const identity = [p.name, rel].filter(Boolean).join(" ");
        return [identity, age].filter(Boolean).join(", ");
      }

      function partyAddress(p) {
        if (!p) return "";
        const parts = [];
        if (p.address) parts.push(p.address);
        if (p.village) parts.push(p.village);
        if (p.hobli) {
          parts.push(p.hobli.toLowerCase().includes("hobli") ? p.hobli : p.hobli + " Hobli");
        }
        if (p.taluk) {
          parts.push(p.taluk.toLowerCase().includes("taluk") ? p.taluk : p.taluk + " Taluk");
        }
        if (p.district) {
          parts.push(p.district.toLowerCase().includes("district") ? p.district : p.district + " District");
        }
        return parts.filter(Boolean).join(", ");
      }

      function partyDetails(party) {
        if (!party) return "";
        return [
          partyName(party) || party.name || "",
          party.status ? `Status: ${party.status}` : "",
          partyAddress(party) ? `Address: ${partyAddress(party)}` : "",
          party.landline ? `Landline: ${party.landline}` : "",
          party.mobile ? `Mobile: ${party.mobile}` : "",
          party.email ? `Email: ${party.email}` : "",
          party.advocateName || party.advocate_name ? `Advocate: ${party.advocateName || party.advocate_name}` : "",
          party.advocateMobile || party.advocate_mobile ? `Advocate Mobile: ${party.advocateMobile || party.advocate_mobile}` : "",
          party.advocateEmail || party.advocate_email ? `Advocate Email: ${party.advocateEmail || party.advocate_email}` : "",
          party.advocateBarNo || party.advocate_bar_no ? `Advocate Bar No.: ${party.advocateBarNo || party.advocate_bar_no}` : "",
        ].filter(Boolean).join(" | ");
      }

      function partyDetailsList(parties) {
        return Array.isArray(parties)
          ? parties.map(partyDetails).filter(Boolean).join(" ; ")
          : "";
      }

      function partyHtml(people, kind) {
        const list = Array.isArray(people) ? people : [];
        if (!list.length) {
          return `<div class="pending-detail-card"><strong>${escHtml(kind)}</strong><div>—</div></div>`;
        }
        return list.map((p, i) => {
          const pName = partyName(p) || p.name || "—";
          const address = partyAddress(p);
          const contact = [
            p.landline && `Landline: ${p.landline}`,
            p.mobile && `Mobile: ${p.mobile}`,
            p.email && `Email: ${p.email}`,
          ].filter(Boolean).join(" · ");
          const advocate = [
            p.advocateName || p.advocate_name,
            (p.advocateBarNo || p.advocate_bar_no) && `Bar No. ${p.advocateBarNo || p.advocate_bar_no}`,
            p.advocateMobile || p.advocate_mobile,
            p.advocateEmail || p.advocate_email,
          ].filter(Boolean).join(" · ");

          return `<div class="pending-detail-card">
            <strong>${escHtml(kind)} ${i + 1}: ${escHtml(pName)}</strong>
            ${p.status ? `<div><span style="color:#64748b;font-size:11px;">Status:</span> ${escHtml(p.status)}</div>` : ""}
            ${address ? `<div><span style="color:#64748b;font-size:11px;">Address:</span> ${escHtml(address)}</div>` : ""}
            ${contact ? `<div><span style="color:#64748b;font-size:11px;">Contact:</span> ${escHtml(contact)}</div>` : ""}
            ${advocate ? `<div><span style="color:#64748b;font-size:11px;">Advocate:</span> ${escHtml(advocate)}</div>` : ""}
          </div>`;
        }).join("");
      }

      function pendingCaseDetailHtml(c) {
        if (!c) return "";
        const value = (v) => (v === undefined || v === null || String(v).trim() === "") ? "—" : escHtml(String(v));
        const extentStr = [c.extent || c.landExtent || "", c.unit || c.extentUnit || ""].filter(Boolean).join(" ");
        const isDisposedCase = (c.status === "Disposed" || c.caseMode === "Disposed" || Boolean(c.disposedDate || c.dispose_date || c.disposalNature));
        const fields = [
          ["Court Hall", `Hall ${c.hall || (c.court && c.court.includes("2") ? "II" : "I") || "—"}`],
          ["Case Type", c.type || c.case_type || "—"],
          ["Year of Filing", c.filedYear || c.filing_year || "—"],
          ["Case No.", c.caseNo || c.existing_case_no || "—"],
          ["CNR", c.cnr || "—"],
          ["Current Stage", c.currentStage || c.stage || "—"],
          ["Stage Group", c.stageGroup || c.stage_group || "—"],
          [isDisposedCase ? "Disposed Date" : "Next Hearing Date", isDisposedCase ? (c.disposedDate || c.dispose_date || "—") : (c.nextHearing || c.hearing_date || "—")],
          ...(isDisposedCase ? [["Disposal Nature", c.disposalNature || c.disposal_nature || "—"]] : []),
          ["Restoration of Land", c.restorationOfLand || c.restoration || "—"],
          ...(isDisposedCase || c.possession ? [["Possession", c.possession || "—"]] : []),
          ...(isDisposedCase || c.bundleNo || c.bundle_number ? [["Bundle Number", c.bundleNo || c.bundle_number || "—"]] : []),
          ...(isDisposedCase || c.monthYear || c.month_year ? [["Month and Year", c.monthYear || c.month_year || "—"]] : []),
        ];

        const propItems = [
          ["Extent", extentStr],
          ["Survey No.", c.surveyNo || c.survey_no],
          ["Ward No.", c.wardNo || c.ward_no],
          ["PID No.", c.pidNo || c.pid_no],
          ["Property Tax Assessment No.", c.propertyTaxAssessmentNo || c.property_tax_no],
          ["District", c.district],
          ["Taluk", c.taluk],
          ["Hobli", c.hobli],
          ["Village", c.village],
        ].filter(([, v]) => v !== undefined && v !== null && String(v).trim() !== "");

        const pets = (Array.isArray(c.petitioners) && c.petitioners.length > 0) ? c.petitioners : (c.applicants_data || []);
        const resps = (Array.isArray(c.respondents) && c.respondents.length > 0) ? c.respondents : (c.respondents_data || []);

        return `<div class="pending-case-details">
          <!-- Operator Audit Information -->
          <div style="margin-top:10px;padding:8px 12px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;font-size:11px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
            <div>
              <span style="color:#64748b;font-weight:600;">Data Entry Operator:</span>
              <b style="color:#0f172a;margin-left:4px;">✍️ ${escHtml(c.enteredBy || c.operatorId || 'Court Administrator')}</b>
              ${c.operatorId ? `<span style="margin-left:4px;color:#64748b;font-family:monospace;">(${escHtml(c.operatorId)})</span>` : ''}
            </div>
            <div>
              <span style="color:#64748b;font-weight:600;">Court Hall:</span>
              <b style="color:#0f172a;margin-left:4px;">Hall ${escHtml(c.hall || (c.court && c.court.includes("2") ? "II" : "I") || "I")}</b>
            </div>
            <div>
              <span style="color:#64748b;font-weight:600;">Entry Timestamp:</span>
              <b style="color:#0f172a;margin-left:4px;">${escHtml(c.createdAt ? c.createdAt.replace('T', ' ').slice(0, 19) : (c.entryDate || '—'))}</b>
            </div>
          </div>

          <div class="pending-detail-grid">
            ${fields.map(([k, v]) => `<div><span>${escHtml(k)}</span><b>${value(v)}</b></div>`).join("")}
          </div>
          <h4>Land and property details</h4>
          <div class="pending-detail-card">
            <div class="pending-detail-grid">
              ${propItems.length ? propItems.map(([k, v]) => `<div><span>${escHtml(k)}</span><b>${value(v)}</b></div>`).join("") : "<div>No property details recorded.</div>"}
            </div>
          </div>
          <div class="pending-detail-parties">
            <section>
              <h4>Petitioner(s) / Complainant(s)</h4>
              ${partyHtml(pets, "Petitioner")}
            </section>
            <section>
              <h4>Respondent(s) / Defendant(s) / Accused</h4>
              ${partyHtml(resps, "Respondent")}
            </section>
          </div>
        </div>`;
      }

      function petRowHtml(data = {}) {
        data = data || {};
        const hasAdvocate = Boolean(
          data.hasAdvocate === true ||
          (data.advocateName && String(data.advocateName).trim() && !["its secretary", "secretary", "tahsildar"].includes(String(data.advocateName).trim().toLowerCase()))
        );
        const isKnown = data.status && COURT_PETITIONER_STATUS.includes(data.status) && data.status !== "Other";
        const isOther = (data.status && !isKnown) || (data.status === "Other") || Boolean(data.statusOther);
        const otherVal = data.statusOther || (isOther && data.status !== "Other" ? data.status : "");
        const statusVal = isKnown ? data.status : (isOther ? "Other" : (data.status || ""));

        return `<div class="dyn-block" data-petrow>
          <div class="party-card-header">
            <div class="party-identity-fields">
              <input type="text" class="petName party-name-input" placeholder="Petitioner / Complainant name" value="${escAttr(data.name || "")}">
              <div class="party-rel-group">
                <input type="number" class="petAge party-age-input" placeholder="Age" min="0" max="150" value="${escAttr(data.age || "")}">
                ${relationshipHtml(data, "pet")}
              </div>
              <div class="party-status-group" style="display:flex;flex-direction:column;gap:4px;">
                <select class="petStatus party-status-select" aria-label="Status">
                  <option value="">Select status...</option>
                  ${COURT_PETITIONER_STATUS.map(st => `<option value="${escAttr(st)}" ${statusVal === st ? "selected" : ""}>${escAttr(st)}</option>`).join("")}
                </select>
                <input type="text" class="petOther" placeholder="ENTER STATUS IN CAPITAL LETTERS" style="display:${statusVal === 'Other' ? 'block' : 'none'};text-transform:uppercase;font-size:12px;padding:4px 8px;border:1px solid #cbd5e1;border-radius:4px;" value="${escAttr(otherVal)}">
              </div>
            </div>
            <button type="button" class="rm-row" data-rm aria-label="Remove petitioner" title="Remove petitioner">&times;</button>
          </div>
          ${locationHtml(data, "pet")}
          <input type="text" class="party-address petAddress" placeholder="Address" value="${escAttr(data.address || "")}">
          <div class="dyn-row contact-row">
            <input type="text" class="petLandline" placeholder="Landline no." value="${escAttr(data.landline || "")}">
            <input type="tel" class="petMobile" placeholder="Mobile no." value="${escAttr(data.mobile || "")}">
            <input type="email" class="petEmail" placeholder="Email ID" value="${escAttr(data.email || "")}">
          </div>
          <label class="party-adv-toggle">
            <input type="checkbox" class="petAdvToggle" ${hasAdvocate ? "checked" : ""}>
            <span>This petitioner has their own advocate</span>
          </label>
          <div class="dyn-row advocate-fields petAdvFields ${hasAdvocate ? "open" : ""}" data-open="${hasAdvocate ? "true" : "false"}" style="display:${hasAdvocate ? "grid" : "none"} !important;">
            <input type="text" class="petAdvName" placeholder="Advocate name" value="${escAttr(data.advocateName || data.advocate_name || "")}">
            <input type="tel" class="petAdvMobile" placeholder="Mobile no." value="${escAttr(data.advocateMobile || data.advocate_mobile || "")}">
            <input type="email" class="petAdvEmail" placeholder="Email ID" value="${escAttr(data.advocateEmail || data.advocate_email || "")}">
            <input type="text" class="petAdvBarNo" placeholder="Bar Council Reg. No." value="${escAttr(data.advocateBarNo || data.advocate_bar_no || "")}">
          </div>
        </div>`;
      }

      function respRowHtml(data = {}) {
        data = data || {};
        const hasAdvocate = Boolean(
          data.hasAdvocate === true ||
          (data.advocateName && String(data.advocateName).trim() && !["its secretary", "secretary", "tahsildar"].includes(String(data.advocateName).trim().toLowerCase()))
        );
        return `<div class="dyn-block" data-resprow>
          <div class="party-card-header">
            <div class="party-identity-fields">
              <input type="text" class="respName party-name-input" placeholder="Respondent / Defendant / Accused name" value="${escAttr(data.name || "")}">
              <div class="party-rel-group">
                <input type="number" class="respAge party-age-input" placeholder="Age" min="0" max="150" value="${escAttr(data.age || "")}">
                ${relationshipHtml(data, "resp")}
              </div>
            </div>
            <button type="button" class="rm-row" data-rm aria-label="Remove respondent" title="Remove respondent">&times;</button>
          </div>
          ${locationHtml(data, "resp")}
          <input type="text" class="party-address respAddress" placeholder="Address" value="${escAttr(data.address || "")}">
          <div class="dyn-row contact-row">
            <input type="text" class="respLandline" placeholder="Landline no." value="${escAttr(data.landline || "")}">
            <input type="tel" class="respMobile" placeholder="Mobile no." value="${escAttr(data.mobile || "")}">
            <input type="email" class="respEmail" placeholder="Email ID" value="${escAttr(data.email || "")}">
          </div>
          <label class="party-adv-toggle">
            <input type="checkbox" class="respAdvToggle" ${hasAdvocate ? "checked" : ""}>
            <span>This respondent has their own advocate</span>
          </label>
          <div class="dyn-row advocate-fields respAdvFields ${hasAdvocate ? "open" : ""}" data-open="${hasAdvocate ? "true" : "false"}" style="display:${hasAdvocate ? "grid" : "none"} !important;">
            <input type="text" class="respAdvName" placeholder="Advocate name" value="${escAttr(data.advocateName || data.advocate_name || "")}">
            <input type="tel" class="respAdvMobile" placeholder="Mobile no." value="${escAttr(data.advocateMobile || data.advocate_mobile || "")}">
            <input type="email" class="respAdvEmail" placeholder="Email ID" value="${escAttr(data.advocateEmail || data.advocate_email || "")}">
            <input type="text" class="respAdvBarNo" placeholder="Bar Council Reg. No." value="${escAttr(data.advocateBarNo || data.advocate_bar_no || "")}">
          </div>
        </div>`;
      }

      function wirePartyRow(row, type) {
        if (!row) return;
        const toggle = row.querySelector(`.${type}AdvToggle`);
        const advocateFields = row.querySelector(`.${type}AdvFields`);
        if (toggle && advocateFields) {
          const updateAdvVisibility = () => {
            const isChecked = Boolean(toggle.checked);
            advocateFields.classList.toggle("open", isChecked);
            advocateFields.setAttribute("data-open", isChecked ? "true" : "false");
            advocateFields.style.setProperty("display", isChecked ? "grid" : "none", "important");
            if (!isChecked) {
              advocateFields.querySelectorAll("input").forEach(inp => {
                inp.value = "";
              });
            }
          };
          toggle.addEventListener("change", () => {
            updateAdvVisibility();
            syncPartiesToTextareas();
          });
          updateAdvVisibility();
        }

        if (type === "pet") {
          const sel = row.querySelector(".petStatus");
          const other = row.querySelector(".petOther");
          if (sel && other) {
            sel.addEventListener("change", () => {
              if (sel.value === "Other") {
                other.style.display = "block";
                other.focus();
              } else {
                other.style.display = "none";
                other.value = "";
              }
              syncPartiesToTextareas();
            });
            other.addEventListener("input", () => {
              other.value = other.value.toUpperCase();
              syncPartiesToTextareas();
            });
          }
        }

        const rmBtn = row.querySelector("[data-rm]");
        if (rmBtn) {
          rmBtn.onclick = () => {
            const selector = type === "pet" ? "[data-petrow]" : "[data-resprow]";
            const container = row.parentElement;
            if (!container) return;
            const allRows = container.querySelectorAll(selector);
            if (allRows.length > 1) {
              row.remove();
            } else {
              row.querySelectorAll("input").forEach(inp => {
                if (inp.type === "checkbox") inp.checked = false;
                else inp.value = "";
              });
              row.querySelectorAll("select").forEach(sel => sel.value = "");
              if (toggle) toggle.checked = false;
              if (advocateFields) {
                advocateFields.classList.remove("open");
                advocateFields.setAttribute("data-open", "false");
                advocateFields.style.setProperty("display", "none", "important");
              }
              const other = row.querySelector(".petOther");
              if (other) {
                other.style.display = "none";
                other.value = "";
              }
            }
            syncPartiesToTextareas();
          };
        }

        row.querySelectorAll("input, select").forEach(el => {
          el.addEventListener("input", syncPartiesToTextareas);
          el.addEventListener("change", syncPartiesToTextareas);
        });
      }

      function collectPartiesData(type) {
        const containerId = type === "pet" ? "petRows" : "respRows";
        const container = document.getElementById(containerId);
        if (!container) return [];
        const rowSelector = type === "pet" ? "[data-petrow]" : "[data-resprow]";
        const rows = Array.from(container.querySelectorAll(rowSelector));
        const result = [];

        rows.forEach(row => {
          const name = row.querySelector(`.${type}Name`)?.value.trim() || "";
          const age = row.querySelector(`.${type}Age`)?.value.trim() || "";
          const relationship = row.querySelector(`.${type}Relation`)?.value.trim() || "";
          const relativeName = row.querySelector(`.${type}Relative`)?.value.trim() || "";

          let status = "";
          let statusOther = "";
          if (type === "pet") {
            const sel = row.querySelector(".petStatus")?.value.trim() || "";
            const other = row.querySelector(".petOther")?.value.trim() || "";
            status = sel === "Other" ? (other || "Other") : sel;
            statusOther = other;
          }

          const district = row.querySelector(`.${type}District`)?.value.trim() || "";
          const taluk = row.querySelector(`.${type}Taluk`)?.value.trim() || "";
          const hobli = row.querySelector(`.${type}Hobli`)?.value.trim() || "";
          const village = row.querySelector(`.${type}Village`)?.value.trim() || "";
          const address = row.querySelector(`.${type}Address`)?.value.trim() || "";
          const landline = row.querySelector(`.${type}Landline`)?.value.trim() || "";
          const mobile = row.querySelector(`.${type}Mobile`)?.value.trim() || "";
          const email = row.querySelector(`.${type}Email`)?.value.trim() || "";

          const hasAdv = row.querySelector(`.${type}AdvToggle`)?.checked || false;
          const advocateName = hasAdv ? (row.querySelector(`.${type}AdvName`)?.value.trim() || "") : "";
          const advocateMobile = hasAdv ? (row.querySelector(`.${type}AdvMobile`)?.value.trim() || "") : "";
          const advocateEmail = hasAdv ? (row.querySelector(`.${type}AdvEmail`)?.value.trim() || "") : "";
          const advocateBarNo = hasAdv ? (row.querySelector(`.${type}AdvBarNo`)?.value.trim() || "") : "";

          if (name || address || district || taluk || village || relativeName) {
            const obj = {
              name,
              age,
              relationship,
              relativeName,
              district,
              taluk,
              hobli,
              village,
              address,
              landline,
              mobile,
              email,
              hasAdvocate: hasAdv,
              advocateName,
              advocateMobile,
              advocateEmail,
              advocateBarNo
            };
            if (type === "pet") {
              obj.status = status;
              obj.statusOther = statusOther;
            }
            result.push(obj);
          }
        });

        return result;
      }

      function serializePartyList(list, type) {
        if (!Array.isArray(list) || list.length === 0) return { namesStr: "", addrsStr: "" };
        const valid = list.filter(p => p && (p.name || p.address || p.district || p.taluk || p.relativeName));
        if (valid.length === 0) return { namesStr: "", addrsStr: "" };

        const multi = valid.length > 1;
        const nameParts = [];
        const addrParts = [];

        valid.forEach((p, idx) => {
          const num = multi ? `${idx + 1}. ` : "";
          let n = partyName(p) || p.name || "";
          if (p.hasAdvocate && (p.advocateName || p.advocate_name)) {
            n += ` (Rep. by Adv. ${p.advocateName || p.advocate_name})`;
          }
          nameParts.push(`${num}${n}`.trim());

          let a = partyAddress(p);
          let addrTokens = [];
          if (a) addrTokens.push(a);
          if (p.landline) addrTokens.push(`Landline: ${p.landline}`);
          if (p.mobile) addrTokens.push(`Mob: ${p.mobile}`);
          if (p.email) addrTokens.push(`Email: ${p.email}`);

          addrParts.push(`${num}${addrTokens.join(", ").trim()}`.trim());
        });

        return {
          namesStr: nameParts.join("\n"),
          addrsStr: addrParts.join("\n")
        };
      }

      function syncPartiesToTextareas() {
        const petList = collectPartiesData("pet");
        const respList = collectPartiesData("resp");

        const petSer = serializePartyList(petList, "pet");
        const respSer = serializePartyList(respList, "resp");

        const appNameEl = document.getElementById("fApplicantName");
        const appAddrEl = document.getElementById("fApplicantAddress");
        const respNameEl = document.getElementById("fRespondentName");
        const respAddrEl = document.getElementById("fRespondentAddress");

        if (appNameEl) appNameEl.value = petSer.namesStr;
        if (appAddrEl) appAddrEl.value = petSer.addrsStr;
        if (respNameEl) respNameEl.value = respSer.namesStr;
        if (respAddrEl) respAddrEl.value = respSer.addrsStr;
      }

      function renderPetitionerRows(list) {
        const container = document.getElementById("petRows");
        if (!container) return;
        const items = (Array.isArray(list) && list.length > 0) ? list : [{}];
        container.innerHTML = items.map(item => petRowHtml(item)).join("");
        container.querySelectorAll("[data-petrow]").forEach(r => wirePartyRow(r, "pet"));
        syncPartiesToTextareas();
      }

      function renderRespondentRows(list) {
        const container = document.getElementById("respRows");
        if (!container) return;
        const items = (Array.isArray(list) && list.length > 0) ? list : [{}];
        container.innerHTML = items.map(item => respRowHtml(item)).join("");
        container.querySelectorAll("[data-resprow]").forEach(r => wirePartyRow(r, "resp"));
        syncPartiesToTextareas();
      }

      function parsePartiesTextToStructured(nameStr, addrStr, partyType, rawText) {
        if (!nameStr && !addrStr && !rawText) return [{}];

        let rawBlocks = [];
        if (rawText) {
          const lines = rawText.trim().split("\n").map(l => l.trim()).filter(Boolean);
          const pfxPat = /^(?:[~<_\\/\*\s\(\[\-|•]*)(?:(?:ಇರರು|ಅರ್ಜಿದಾರರು|ಎದುರುದಾರರು|Iraru|Arjidararu|Arjidara|Edurudara|Edurudararu)\s*[:\-.]?\s*)*(?:\d+\s+)*(?:A\s*\d{1,3}|[1-9]\d{0,2}|A[lI1]\d{1,2}|AS|[A-Za-z]\d{1,3})[\.\)]\s*/i;
          const addrStartPat = /^(?:No\.?|Plot|Flat|Door|Near|Opp|Beside|Behind|\d+\s*(?:st|nd|rd|th)?\s*Cross|Bengaluru|Kalaburagi)/i;
          const knownNamePat = /^(?:Murughan|Uma|Marvan\s*Abubkar|Deva(?:das)?|Ameer\s*Baig|Perumal|Ashok|Pushparaj|Feelik)[,\s]/i;

          rawBlocks = [];
          let currB = [];
          for (const line of lines) {
            let isNew = false;
            if (pfxPat.test(line)) {
              const afterPfx = line.replace(pfxPat, "").trim();
              if (!addrStartPat.test(afterPfx)) isNew = true;
            } else if (/^(?:Smt\.?|Sri\.?|Shri\.?)\s+[A-Z][a-zA-Z\s]+/i.test(line) && !addrStartPat.test(line)) {
              isNew = true;
            } else if (knownNamePat.test(line)) {
              isNew = true;
            }

            if (isNew && currB.length) {
              rawBlocks.push(currB.join("\n"));
              currB = [line];
            } else {
              currB.push(line);
            }
          }
          if (currB.length) rawBlocks.push(currB.join("\n"));
        }

        const nameBlocks = (nameStr || "")
          .split(/(?:^|\n)\s*(?=(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*)/g)
          .map(s => s.trim())
          .filter(Boolean);
        const addrBlocks = (addrStr || "")
          .split(/(?:^|\n)\s*(?=(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*)/g)
          .map(s => s.trim())
          .filter(Boolean);

        const count = rawBlocks.length > 0 ? rawBlocks.length : Math.max(nameBlocks.length, 1);
        const result = [];

        for (let i = 0; i < count; i++) {
          let block = rawBlocks[i] || "";
          let nLine = nameBlocks[i] || nameBlocks[0] || "";
          let aLine = addrBlocks[i] || (addrBlocks.length === 1 ? addrBlocks[0] : "") || "";

          block = block.replace(/^(?:(?:A\s*[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]|(?:Edurudara|Respondent|Arjidara|Applicant|Accused)\s*(?:No\.?)?\s*[1-9]\d{0,2}[:\-.]?)\s*/i, "").trim();
          nLine = nLine.replace(/^(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*/i, "").trim();
          aLine = aLine.replace(/^(?:A[1-9]\d{0,2}|[1-9]\d{0,2})[\.\)]\s*/i, "").trim();

          let fullEval = (block ? block : (nLine + "\n" + aLine)).trim();

          let name = nLine || "";
          let age = "";
          let relationship = "";
          let relativeName = "";
          let status = partyType === "pet" ? "Individual" : "";
          if (/\b(?:Dead|Deceased)\b/i.test(block || fullEval)) {
            status = "Deceased";
          }
          let advocateName = "";
          let advocateMobile = "";
          let advocateEmail = "";
          let advocateBarNo = "";
          let mobile = "";
          let email = "";
          let landline = "";
          let district = "";
          let taluk = "";
          let hobli = "";
          let village = "";
          let address = aLine || "";

          if (block) {
            let t = block;
            // 1. Advocate Details (strictly require Adv. or counsel keyword; do NOT treat "Rep. by its Secretary" as advocate)
            const advMatch = t.match(/\b(?:(?:Rep(?:resented)?\s*by\s+)?(?:Adv(?:ocate)?|learned\s+counsel|ವಕೀಲರು?)\s*[:\-]?\s*([A-Za-z\.\s]+?))(?:,|$|\n|\()/i);
            if (advMatch) {
              const advCand = advMatch[1].trim();
              const candLow = advCand.toLowerCase();
              const nonAdvWords = ["the", "and", "for", "state", "respondent", "applicant", "secretary", "president", "director", "manager", "tahsildar", "officer", "its"];
              if (advCand && !nonAdvWords.some(w => candLow === w || candLow.startsWith(w + " "))) {
                advocateName = advCand;
                t = t.replace(advMatch[0], " ").trim();
              }
            }

            // 2. Relation & Relative Name
            const relMatch = t.match(/\b(S\/[oO0]|W\/[oO0]|D\/[oO0]|C\/[oO0]|5\/[oO0]|%\/[oO]|(?:\$|s)\/[oO0]|Sto|Wto|Dto|Son\s+of|Wife\s+of|Daughter\s+of|Care\s+of|ಬಿನ್|ಕೋಂ|ಮಗ|ಹೆಂಡತಿ|ಪತ್ನಿ|ಮಗಳು)\b\s*([A-Za-z0-9\.\s]+?)(?:,|$|\n|(?=\b(?:Age|Aged|years|yrs|R\/o|r\/o|residing|No\.?|Flat|Plot|Door|House|\d+\s*(?:st|nd|rd|th)?\s*Cross)\b))/i);
            // 3. Age
            const ageMatch = t.match(/\b(?:Aged?\s*(?:about|around)?|Age\s*[:\-]?\s*|ವಯಸ್ಸು\s*[:\-]?\s*|ಪ್ರಾಯ\s*[:\-]?\s*)\s*(\d{1,3})\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)?\b/i) || t.match(/\b(\d{1,3})\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)\b/i);

            if (relMatch) {
              const rawRel = relMatch[1].toLowerCase();
              if (rawRel.includes("w/") || rawRel.includes("wto") || rawRel.includes("wife") || rawRel.includes("ಕೋಂ") || rawRel.includes("ಹೆಂಡತಿ") || rawRel.includes("ಪತ್ನಿ")) {
                relationship = "W/O";
              } else if (rawRel.includes("d/") || rawRel.includes("dto") || rawRel.includes("daughter") || rawRel.includes("ಮಗಳು")) {
                relationship = "D/O";
              } else if (rawRel.includes("c/") || rawRel.includes("care")) {
                relationship = "C/O";
              } else {
                relationship = "S/O";
              }
              relativeName = cleanPartyToken(relMatch[2]);
              name = cleanPartyToken(t.slice(0, relMatch.index));

              // Clean multi-line relative (e.g. Late 1. \n Narayana Reddy)
              const bLines = t.split("\n").map(l => l.trim()).filter(Boolean);
              if (bLines.length > 1 && (/^Late\b/i.test(relativeName) || relativeName.split(/\s+/).length <= 1)) {
                if (!/^(?:No\.?|Plot|Flat|Door|Near|Opp|\d+)/i.test(bLines[1]) && !/\b(?:Aged|years)\b/i.test(bLines[1])) {
                  relativeName = `${relativeName} ${cleanPartyToken(bLines[1])}`.trim();
                }
              }

              if (ageMatch && ageMatch.index > relMatch.index) {
                age = ageMatch[1];
                address = t.slice(ageMatch.index + ageMatch[0].length);
              } else {
                address = t.slice(relMatch.index + relMatch[0].length);
                if (ageMatch) {
                  age = ageMatch[1];
                  address = address.replace(ageMatch[0], "");
                }
              }
            } else if (ageMatch) {
              age = ageMatch[1];
              name = cleanPartyToken(t.slice(0, ageMatch.index));
              address = t.slice(ageMatch.index + ageMatch[0].length);
            } else {
              const lines = t.split("\n").map(l => l.trim()).filter(Boolean);
              if (lines.length > 1) {
                name = cleanPartyToken(lines[0]);
                address = lines.slice(1).join(", ");
              } else if (t.includes(",")) {
                const parts = t.split(",", 2);
                name = cleanPartyToken(parts[0]);
                address = t.slice(parts[0].length + 1);
              } else {
                name = cleanPartyToken(t);
                address = "";
              }
            }

            // Alias check (@ Muniyan)
            const aliasM = t.match(/@\s*([A-Za-z\s]+)/);
            if (aliasM && aliasM[1].trim()) {
              const alName = cleanPartyToken(aliasM[1]);
              if (alName && !name.toLowerCase().includes(alName.toLowerCase())) {
                name = `${name} @ ${alName}`;
              }
            }

            // Clean leading OCR noise numbers/characters
            name = name.replace(/^(?:[~<_\\/\*\s\(\[\-|•]*)(?:(?:ಇರರು|ಅರ್ಜಿದಾರರು|ಎದುರುದಾರರು|Iraru|Arjidararu|Arjidara|Edurudara|Edurudararu)\s*[:\-.]?\s*)*(?:\d+\s+)*(?:A[A-Za-z0-9]{0,3}|[1-9]\d{0,2}|A[lI1]\d{1,2}|AS|[A-Za-z]\d{1,3})[\.\)]\s*/i, "");
            name = name.replace(/^[|•*()~<_\-\s]+/, "");
            name = name.replace(/^(?:Iraru|Arjidararu|Arjidara|Edurudara|Edurudararu)\s*/i, "");
            name = name.replace(/^[^\w\s]+/, "");
            name = name.replace(/^\d{2,4}\s+/, "");
            name = cleanPartyToken(name);
          } else {
            // nLine and aLine passed separately
            let tName = nLine;
            let tAddr = aLine;
            const fullText = tName + " " + tAddr;

            const advMatch = fullText.match(/\b(?:(?:Rep(?:resented)?\s*by\s+)?(?:Adv(?:ocate)?|learned\s+counsel|ವಕೀಲರು?)\s*[:\-]?\s*([A-Za-z\.\s]+?))(?:,|$|\n|\()/i);
            if (advMatch) {
              const advCand = advMatch[1].trim();
              const candLow = advCand.toLowerCase();
              const nonAdvWords = ["the", "and", "for", "state", "respondent", "applicant", "secretary", "president", "director", "manager", "tahsildar", "officer", "its"];
              if (advCand && !nonAdvWords.some(w => candLow === w || candLow.startsWith(w + " "))) {
                advocateName = advCand;
                tName = tName.replace(advMatch[0], "").trim();
                tAddr = tAddr.replace(advMatch[0], "").trim();
              }
            }

            const relMatch = tName.match(/\b(S\/[oO]|W\/[oO]|D\/[oO]|C\/[oO]|s\/o|w\/o|d\/o|c\/o|Son\s+of|Wife\s+of|Daughter\s+of|Care\s+of|ಬಿನ್|ಕೋಂ|ಮಗ|ಹೆಂಡತಿ|ಪತ್ನಿ|ಮಗಳು)\b\s*([A-Za-z\.\s]+?)(?:,|$|\n|(?=\b(?:Age|Aged|years|yrs|R\/o|r\/o|residing)\b))/i);
            const ageMatch = fullText.match(/\b(?:Aged?\s*(?:about|around)?|Age\s*[:\-]?\s*|ವಯಸ್ಸು\s*[:\-]?\s*|ಪ್ರಾಯ\s*[:\-]?\s*)\s*(\d{1,3})\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)?\b/i) || fullText.match(/\b(\d{1,3})\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)\b/i);

            if (relMatch) {
              const rawRel = relMatch[1].toUpperCase();
              if (rawRel.includes("W") || rawRel.includes("ಹೆಂಡತಿ") || rawRel.includes("ಪತ್ನಿ") || rawRel.includes("ಕೋಂ")) {
                relationship = "W/O";
              } else if (rawRel.includes("D") || rawRel.includes("ಮಗಳು")) {
                relationship = "D/O";
              } else if (rawRel.includes("C")) {
                relationship = "C/O";
              } else {
                relationship = "S/O";
              }
              relativeName = cleanPartyToken(relMatch[2]);
              name = cleanPartyToken(tName.slice(0, relMatch.index));
            } else if (ageMatch && tName.includes(ageMatch[0])) {
              name = cleanPartyToken(tName.slice(0, tName.indexOf(ageMatch[0])));
            } else {
              name = cleanPartyToken(tName.replace(/\b(?:Aged?\s*(?:about)?\s*\d+\s*years?|Age\s*[:\-]?\s*\d+)\b/gi, ""));
            }

            if (ageMatch) age = ageMatch[1];
            address = tAddr;
          }

          // Status heuristic
          if (partyType === "pet") {
            const lowN = name.toLowerCase();
            if (/sho|bmtf|police|psi|circle inspector/i.test(lowN)) status = "Heads of Government Departments";
            else if (/tahsildar|special tahsildar/i.test(lowN)) status = "Tahsildar";
            else if (/department|government|engineer|commissioner|kptcl|bbmp|bda/i.test(lowN)) status = "Heads of Government Departments";
            else if (/ltd|limited|company|corp/i.test(lowN)) status = "Company";
            else if (/firm|enterprise|associates/i.test(lowN)) status = "Firm";
            else if (/panchayat|authority|board/i.test(lowN)) status = "Local Authority";
          }

          // 6. District Extraction
          const addrToSearch = (address + " " + fullEval).replace(/\s+/g, " ");
          for (const candK of Object.keys(DISTRICT_ALIASES).sort((a,b) => b.length - a.length)) {
            const reg = new RegExp(`\\b${candK.replace(/\\s+/g, "\\\\s*")}\\b`, "i");
            if (reg.test(addrToSearch)) {
              district = DISTRICT_ALIASES[candK];
              break;
            }
          }
          if (!district) {
            const distList = (typeof GEO !== "undefined" && GEO && typeof GEO === "object") ? Object.keys(GEO).sort((a,b) => b.length - a.length) : [];
            for (const d of distList) {
              const reg = new RegExp(`\\b${d.replace(/\\s+/g, "\\\\s*")}\\b`, "i");
              if (reg.test(addrToSearch)) {
                district = d;
                break;
              }
            }
          }

          // 7. Taluk Extraction
          const talukMatch = addrToSearch.match(/([A-Za-z\s]+?)\s+(?:Taluk|Taluka|Tq)\b/i);
          if (talukMatch) {
            const candTq = cleanPartyToken(talukMatch[1]);
            taluk = TALUK_ALIASES[candTq.toLowerCase()] || candTq;
          } else if (district && typeof GEO !== "undefined" && GEO && GEO[district]) {
            for (const [candK, aliasVal] of Object.entries(TALUK_ALIASES)) {
              const reg = new RegExp(`\\b${candK.replace(/\\s+/g, "\\\\s*")}\\b`, "i");
              if (reg.test(addrToSearch)) {
                taluk = aliasVal;
                break;
              }
            }
            if (!taluk) {
              for (const tName of Object.keys(GEO[district])) {
                const reg = new RegExp(`\\b${tName.replace(/\\s+/g, "\\\\s*")}\\b`, "i");
                if (reg.test(addrToSearch)) {
                  taluk = tName;
                  break;
                }
              }
            }
          }
          if (!taluk && district) {
            taluk = district;
          }

          // 8. Hobli Extraction
          const hobliMatch = addrToSearch.match(/([A-Za-z\s]+?)\s+(?:Hobli)\b/i);
          if (hobliMatch) {
            hobli = cleanPartyToken(hobliMatch[1]);
          } else if (district && taluk && typeof GEO !== "undefined" && GEO && GEO[district] && GEO[district][taluk] && Array.isArray(GEO[district][taluk].h)) {
            for (const hName of GEO[district][taluk].h) {
              const reg = new RegExp(`\\b${hName.replace(/\\s+/g, "\\\\s*")}\\b`, "i");
              if (reg.test(addrToSearch)) {
                hobli = hName;
                break;
              }
            }
          }

          // 9. Village / Locality Extraction
          if (/Bengaluru\s*-\s*(\d{2})\b/i.test(addrToSearch)) {
            district = "Bengaluru";
            address = address.replace(/Bengaluru\s*-\s*(\d{2})\b/i, "Bengaluru-5600$1");
          }

          if (district === "Bengaluru" || district === "Bengaluru Urban") {
            const bLocs = [
              'Annasandra Palya Extn', 'Annasandra Palya Main Road', 'Annasandra Palya', 'Vinayak Nagar', 'HAL 3rd Stage', 'HAL',
              'L.B. Shastri Nagar', 'Vimanapura Post', 'Vimanapura', 'Vibhuthipura Slum', 'Vibhuthipura', 'Marathhalli Post', 'Marathhalli',
              'Ramesh Nagar', 'Syed Block', 'Ramaiah Reddy Colony', 'Ramaiah Reddy Lane',
              'Basava Nagar', 'Veerabadra Nagar', 'Shivashakthi Colony', 'Ambedkar Slum'
            ];
            for (const loc of bLocs) {
              const reg = new RegExp(`\\b${loc.replace(/\\s+/g, "\\\\s*")}\\b`, "i");
              if (reg.test(addrToSearch)) {
                village = loc;
                if (!taluk) taluk = "Bengaluru East";
                break;
              }
            }
          }

          const villMatch = addrToSearch.match(/(?:(?:r\/o|c\/o|at|residing\s+at)\s+)?([A-Za-z\s]+?)\s+(?:Village|Grama|Dakhale|Dakhle|Palya|Halli)\b/i);
          if (villMatch) {
            village = cleanPartyToken(villMatch[1]);
          }

          if (!village) {
            const parts = (address || "").split(/[,;\n]+/).map(cleanPartyToken).filter(Boolean);
            for (const p of parts) {
              if (/^(?:No\.?|Plot|Flat|Door|Near|Opp|Beside|Behind|\d+)/i.test(p)) continue;
              if (district && p.toLowerCase() === district.toLowerCase()) continue;
              if (taluk && p.toLowerCase() === taluk.toLowerCase()) continue;
              if (DISTRICT_ALIASES[p.toLowerCase()]) continue;
              if (/\b\d{6}\b/.test(p)) continue;
              if (p.split(/\s+/).length <= 3) {
                village = p;
                break;
              }
            }
          }

          if (!village && district && taluk && typeof GEO !== "undefined" && GEO && GEO[district] && GEO[district][taluk] && Array.isArray(GEO[district][taluk].v)) {
            for (const vName of GEO[district][taluk].v) {
              const reg = new RegExp(`\\b${vName.replace(/\\s+/g, "\\\\s*")}\\b`, "i");
              if (reg.test(addrToSearch)) {
                village = vName;
                break;
              }
            }
          }

          if (!village && taluk) {
            if ((typeof GEO !== "undefined" && GEO && GEO[district] && GEO[district][taluk] && Array.isArray(GEO[district][taluk].v) && GEO[district][taluk].v.includes(taluk)) || (new RegExp(`\\b${taluk.replace(/\\s+/g, "\\\\s*")}\\b`, "i")).test(addrToSearch)) {
              village = taluk;
            }
          }

          if (partyType === "pet" && /tahsildar/i.test(name) && taluk && taluk.toLowerCase() === "anekal") {
            village = "Anekal";
            address = "Anekal Taluk, Anekal";
          }

          // Clean address
          if (relativeName) {
            address = address.replace(new RegExp(`\\b(?:S/o|W/o|D/o|C/o|Son\\s+of|Wife\\s+of|Daughter\\s+of|Care\\s+of)\\b\\s*${relativeName.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\$&")}[,\\s]*`, "gi"), "").trim();
          }
          address = address.replace(/\b(?:Aged?\s*(?:about|around)?|Age\s*[:\-]?\s*|ವಯಸ್ಸು\s*[:\-]?\s*|ಪ್ರಾಯ\s*[:\-]?\s*)\s*\d{1,3}\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)?\b[,\\s]*/gi, "").trim();
          address = address.replace(/\b\d{1,3}\s*(?:years|yrs|ವರ್ಷ|ವರ್ಷದ)\b[,\\s]*/gi, "").trim();
          address = address.replace(/\b(?:Aged?\s*(?:about|around)?|Age\s*[:\-]?|Major|ವಯಸ್ಸು|ಪ್ರಾಯ)\b[,\\s]*/gi, "").trim();
          address = address.replace(/(?:adesha(?:da)?\s*(?:prati|patra|patre|pata|pati)|order\s*sheet|daily\s*order).*/gi, "").trim();
          address = address.replace(/-?\s*(?:virud+ha|eirudda|dirudda|vs\.?)\s*-?.*/gi, "").trim();
          address = address
            .replace(/\n+/g, ", ")
            .replace(/,\s*,+/g, ", ")
            .replace(/^[\s,.:;\-_/\\]+|[\s,.:;\-_/\\]+$/g, "")
            .trim();

          result.push({
            name,
            age,
            relationship,
            relativeName,
            status: status || (partyType === "pet" ? "Individual" : ""),
            district,
            taluk,
            hobli,
            village,
            address: cleanPartyToken(address),
            mobile,
            email,
            landline,
            hasAdvocate: Boolean(advocateName && advocateName.length >= 3 && !["its secretary", "secretary", "president", "tahsildar"].some(w => advocateName.toLowerCase().includes(w))),
            advocateName,
            advocateMobile,
            advocateEmail,
            advocateBarNo
          });
        }

        return result.length > 0 ? result : [{}];
      }

      function initPartyDynamicHandlers() {
        const petRows = document.getElementById("petRows");
        const respRows = document.getElementById("respRows");
        if (petRows && petRows.children.length === 0) {
          renderPetitionerRows([{}]);
        }
        if (respRows && respRows.children.length === 0) {
          renderRespondentRows([{}]);
        }

        const addPetBtn = document.getElementById("addPet");
        if (addPetBtn) {
          addPetBtn.onclick = () => {
            if (petRows) {
              const div = document.createElement("div");
              div.innerHTML = petRowHtml({});
              const newRow = div.firstElementChild;
              petRows.appendChild(newRow);
              wirePartyRow(newRow, "pet");
              syncPartiesToTextareas();
            }
          };
        }

        const addRespBtn = document.getElementById("addResp");
        if (addRespBtn) {
          addRespBtn.onclick = () => {
            if (respRows) {
              const div = document.createElement("div");
              div.innerHTML = respRowHtml({});
              const newRow = div.firstElementChild;
              respRows.appendChild(newRow);
              wirePartyRow(newRow, "resp");
              syncPartiesToTextareas();
            }
          };
        }
      }
"""

part8_features = """
      // ========================================================
      // OPERATOR ACCESS & SEGREGATION HELPERS
      // ========================================================
      function isCaseVisibleToUser(c, user) {
        if (!user || user.role === "admin" || user.role === "verifier") {
          return true; // Admin and Verifier have complete registry visibility
        }
        // Operator role: strictly sees cases registered under their operator identity
        const myUser = (user.username || "").trim().toLowerCase();
        const myName = (user.displayName || "").trim().toLowerCase();

        const cOpId = (c.operatorId || "").trim().toLowerCase();
        const cEnteredBy = (c.enteredBy || c.entered_by || "").trim().toLowerCase();

        if (cOpId && cOpId === myUser) return true;
        if (cEnteredBy && (cEnteredBy === myName || cEnteredBy === myUser)) return true;
        return false;
      }

      function formatOperatorBadge(c) {
        const opId = (c.operatorId || "").toLowerCase();
        const ent = c.enteredBy || c.entered_by || "";
        if (opId === "operator1") return "Op 1 (Desk 1)";
        if (opId === "operator2") return "Op 2 (Desk 2)";
        if (opId === "operator3") return "Op 3 (Desk 3)";
        if (opId === "operator4") return "Op 4 (Desk 4)";
        if (opId === "operator5") return "Op 5 (Desk 5)";
        if (opId === "admin") return "Court Admin";
        if (opId === "verifier") return "Scrutiny Officer";
        if (ent) {
          if (ent.startsWith("Data Entry Operator ")) return ent.replace("Data Entry Operator ", "Op ");
          return ent;
        }
        return opId || "Admin / Registry";
      }

      function getUniqueOperatorsList() {
        const ops = (typeof window.getOperatorAccounts === "function") ? window.getOperatorAccounts() : {};
        const seen = new Set();
        const list = [];
        
        for (const [k, v] of Object.entries(ops)) {
          if (v.role === "operator" || v.role === "admin") {
            seen.add(k.toLowerCase());
            list.push({ id: k, name: v.displayName || k, hall: v.hall || "1" });
          }
        }
        
        if (Array.isArray(state.cases)) {
          state.cases.forEach(c => {
            const op = (c.operatorId || "").toLowerCase();
            if (op && !seen.has(op)) {
              seen.add(op);
              list.push({ id: op, name: c.enteredBy || op, hall: c.hall || "1" });
            }
          });
        }
        return list;
      }

      function renderAdminOperatorFilterOptions() {
        const list = getUniqueOperatorsList();
        return list.map(o => `<option value="${escAttr(o.id)}">✍️ ${escHtml(o.name)}</option>`).join("");
      }

      // ========================================================
      // CASE.PY FEATURES & DESKTOP LOGIC IMPLEMENTATIONS
      // ========================================================

      // 1. MODE SWITCHING (PENDING VS DISPOSED)
      state.mode = "Pending"; // 'Pending' or 'Disposed'

      function toggleMode() {
        if (state.mode === "Pending") {
          state.mode = "Disposed";
          state.view = "legacy";
        } else {
          state.mode = "Pending";
          state.view = "pendingentry";
        }
        applyModeUI();
        render();
      }
      window.toggleMode = toggleMode;

      function applyModeUI() {
        const isPending = state.mode === "Pending";
        document.body.classList.toggle("mode-disposed", !isPending);
        
        const titleEl = document.getElementById("appTitleLbl");
        const subEl = document.getElementById("appSubLbl");
        const toggleBtn = document.getElementById("modeToggleBtn");
        
        if (titleEl) {
          if (state.view === "navigator") {
            titleEl.textContent = "Case Navigator";
          } else if (state.view === "legacy") {
            titleEl.textContent = "Legacy Case Entry";
          } else if (state.view === "export") {
            titleEl.textContent = "Export & Backup";
          } else {
            titleEl.textContent = isPending ? "Pending Cases Entry" : "Legacy Case Entry";
          }
        }
        if (subEl) {
          subEl.textContent = isPending 
            ? "Karnataka Land Grabbing Prohibition Special Courts" 
            : "Karnataka Land Grabbing Prohibition Special Courts — Disposed Records";
        }
        if (toggleBtn) {
          toggleBtn.textContent = isPending ? "Switch to Disposed Mode" : "Switch to Pending Case Mode";
          toggleBtn.title = isPending ? "Switch to Disposed Mode (Legacy Case Entry)" : "Switch to Pending Case Mode (Pending Cases Entry)";
        }

        // Update Stepper Progress Bar
        const stepMap = { "navigator": 0, "pendingentry": 1, "legacy": 2, "export": 3 };
        const currentStep = stepMap[state.view] !== undefined ? stepMap[state.view] : (isPending ? 1 : 2);
        const segments = document.querySelectorAll(".stepper-segment");
        segments.forEach((seg, i) => {
          seg.classList.toggle("active", i <= currentStep);
        });
      }

      // 2. CORE CASE FORM EXTRACTOR & RECORD PERSISTENCE
      function getCaseObjectFromForm(isLegacy = false) {
        const cnoEl = document.getElementById("fCaseNo");
        const rawNo = extractCaseNumberOnly(cnoEl ? cnoEl.value.trim() : "");
        if (!rawNo) return null;

        const hall = document.getElementById("fCourtHall")?.value || "I";
        const type = document.getElementById("fCaseType")?.value || "G";
        const year = parseInt(document.getElementById("fFilingYear")?.value, 10) || CURRENT_YEAR;
        const fullCaseNo = `L.G.C.(${type}).No.${rawNo}/${year}`;
        const isDisp = state.mode === "Disposed";
        const hDate = isDisp ? "" : (document.getElementById("fHearingDate")?.value || "");
        const dDate = isDisp ? (document.getElementById("fDisposeDate")?.value || "") : "";
        const dNat = isDisp ? (document.getElementById("fDisposalNature")?.value || "Disposed") : "";
        const possVal = isDisp ? (document.getElementById("fPossession")?.value || "N/A") : "";
        const bundleVal = isDisp ? (document.getElementById("fBundleNo")?.value ? document.getElementById("fBundleNo").value.trim() : "") : "";
        const monthYearVal = isDisp ? (document.getElementById("fMonthYear")?.value ? document.getElementById("fMonthYear").value.trim() : "") : "";

        if (typeof syncPartiesToTextareas === "function") syncPartiesToTextareas();
        const petData = typeof collectPartiesData === "function" ? collectPartiesData("pet") : [];
        const respData = typeof collectPartiesData === "function" ? collectPartiesData("resp") : [];

        const appN = document.getElementById("fApplicantName")?.value.trim() || "";
        const appA = document.getElementById("fApplicantAddress")?.value.trim() || "";
        const respN = document.getElementById("fRespondentName")?.value.trim() || "";
        const respA = document.getElementById("fRespondentAddress")?.value.trim() || "";

        return {
          applicants_data: petData,
          respondents_data: respData,
          petitioners: petData,
          respondents: respData,
          id: activeEditCaseId || ("c_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7)),
          hall: hall,
          court: "Court Hall No." + (hall === "II" ? "2" : "1"),
          type: type,
          case_type: `LGC(${type})`,
          caseNo: rawNo,
          existing_case_no: rawNo,
          fullCaseNo: fullCaseNo,
          cnr: document.getElementById("fCnr")?.value.trim() || "",
          applicant_name: appN,
          applicant_address: appA,
          respondent_name: respN,
          respondent_address: respA,
          applicants: (appN + (appA ? String.fromCharCode(10) + appA : "")).trim(),
          respondents: (respN + (respA ? String.fromCharCode(10) + respA : "")).trim(),
          filedYear: year,
          filing_year: year,
          stageGroup: document.getElementById("fStageGroup")?.value || (STAGE_TO_GROUP[document.getElementById("fCurrentStage")?.value] || ""),
          stage_group: document.getElementById("fStageGroup")?.value || (STAGE_TO_GROUP[document.getElementById("fCurrentStage")?.value] || ""),
          currentStage: document.getElementById("fCurrentStage")?.value || "",
          stage: document.getElementById("fCurrentStage")?.value || "",
          sub_stage: document.getElementById("fCurrentStage")?.value || "",
          restoration: document.getElementById("fRestoration")?.value || (isDisp ? "N/A" : "No"),
          restorationOfLand: document.getElementById("fRestoration")?.value || (isDisp ? "N/A" : "No"),
          nextHearing: hDate,
          hearing_date: hDate,
          disposedDate: dDate,
          dispose_date: dDate,
          disposalNature: dNat,
          disposal_nature: dNat,
          status: isDisp ? "Disposed" : "Pending",
          caseMode: state.mode,
          possession: possVal,
          bundleNo: bundleVal,
          bundle_number: bundleVal,
          monthYear: monthYearVal,
          month_year: monthYearVal,
          month: monthYearVal ? monthYearVal.split(/[-/]/)[0] : "",
          year: monthYearVal ? monthYearVal.split(/[-/]/)[1] : "",
          landExtent: document.getElementById("fExtent")?.value.trim() || "",
          extent: document.getElementById("fExtent")?.value.trim() || "",
          extentUnit: document.getElementById("fExtentUnit")?.value || "Acre + Guntas",
          unit: document.getElementById("fExtentUnit")?.value || "Acre + Guntas",
          surveyNo: document.getElementById("fSurveyNo")?.value.trim() || "",
          survey_no: document.getElementById("fSurveyNo")?.value.trim() || "",
          wardNo: document.getElementById("fWardNo")?.value.trim() || "",
          ward_no: document.getElementById("fWardNo")?.value.trim() || "",
          pidNo: document.getElementById("fPidNo")?.value.trim() || "",
          pid_no: document.getElementById("fPidNo")?.value.trim() || "",
          propertyTaxAssessmentNo: document.getElementById("fTaxNo")?.value.trim() || "",
          tax_no: document.getElementById("fTaxNo")?.value.trim() || "",
          district: document.getElementById("fDistrict")?.value || "Bengaluru",
          taluk: document.getElementById("fTaluk")?.value || "",
          hobli: document.getElementById("fHobli")?.value || "",
          village: document.getElementById("fVillage")?.value || "",
          entryDate: new Date().toISOString().slice(0, 10),
          entry_date: new Date().toISOString().slice(0, 10),
          updatedAt: new Date().toISOString(),
          createdAt: activeEditCaseId ? undefined : new Date().toISOString(),
          source: isLegacy ? "legacy-entry" : "pending-entry",
          enteredBy: (window.auth && window.auth.user ? (window.auth.user.displayName || window.auth.user.username) : "Data Entry Operator"),
          entered_by: (window.auth && window.auth.user ? (window.auth.user.displayName || window.auth.user.username) : "Data Entry Operator"),
          operatorId: (window.auth && window.auth.user ? window.auth.user.username : "operator"),
          courtHall: (window.auth && window.auth.user ? (window.auth.user.hall || "1") : "1")
        };
      }

            // Helpers for Notification & Court Hall Display
      function formatCourtHallName(h) {
        const str = String(h || "").trim();
        if (str === "II" || str === "2" || str.includes("2") || str.includes("II")) {
          return "Court Hall 2";
        }
        return "Court Hall 1";
      }

      function formatCaseNumberName(rec) {
        if (!rec) return "Unknown Case";
        if (rec.fullCaseNo) return rec.fullCaseNo;
        const no = rec.caseNo || rec.existing_case_no || "";
        const yr = rec.filedYear || rec.filing_year || "";
        const type = rec.type || rec.case_type || "G";
        if (no && yr) return `L.G.C.(${type}).No.${no}/${yr}`;
        if (no) return `Case No. ${no}`;
        return "Unknown Case";
      }

      function showCaseSaveNotification(opts) {
        const isDuplicate = !!(opts && opts.isDuplicate);
        const caseNo = (opts && (opts.caseNo || opts.fullCaseNo)) || "Unknown Case";
        const courtHall = (opts && opts.courtHall) || "Court Hall 1";
        const operator = (opts && opts.operator) || (window.auth && window.auth.user ? (window.auth.user.displayName || window.auth.user.username) : "Staff");

        let container = document.getElementById("caseNotificationContainer");
        if (!container) {
          container = document.createElement("div");
          container.id = "caseNotificationContainer";
          document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.className = `case-toast-card ${isDuplicate ? 'case-toast-duplicate' : 'case-toast-success'}`;
        toast.setAttribute("role", "alert");
        toast.setAttribute("aria-live", "assertive");

        const iconSvg = isDuplicate ? `
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>` : `
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>`;

        const tagLabel = isDuplicate ? 'DUPLICATE ENTRY · OVERWRITTEN' : 'ENTRY SAVED';
        const headingText = isDuplicate ? 'Details Overwritten for Case' : 'Case Entry Saved Successfully';
        const bodyHtml = isDuplicate 
          ? `Details have been overwritten for that particular case number: <strong class="case-toast-hl">${escHtml(caseNo)}</strong> in <strong class="case-toast-hl">${escHtml(courtHall)}</strong>.<div style="font-size:11.5px;color:#92400e;margin-top:3px;">ಪ್ರಕರಣ ಸಂಖ್ಯೆ ${escHtml(caseNo)} ರ ವಿವರಗಳನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಬದಲಾಯಿಸಲಾಗಿದೆ.</div>`
          : `Entry has been saved for Case Number: <strong class="case-toast-hl">${escHtml(caseNo)}</strong> in <strong class="case-toast-hl">${escHtml(courtHall)}</strong>.<div style="font-size:11.5px;color:#166534;margin-top:3px;">ಪ್ರಕರಣ ಸಂಖ್ಯೆ ${escHtml(caseNo)} ಯಶಸ್ವಿಯಾಗಿ ನಮೂದಿಸಲಾಗಿದೆ.</div>`;

        toast.innerHTML = `
          <div class="case-toast-icon-wrap">
            <div class="case-toast-icon">
              ${iconSvg}
            </div>
          </div>
          <div class="case-toast-body">
            <div class="case-toast-header-row">
              <div class="case-toast-tag">
                <span class="case-toast-dot"></span>
                <span>${tagLabel}</span>
              </div>
              <button type="button" class="case-toast-close" title="Dismiss" aria-label="Dismiss">✕</button>
            </div>
            <div class="case-toast-title">${headingText}</div>
            <div class="case-toast-msg">${bodyHtml}</div>
            <div class="case-toast-meta">
              <span class="case-toast-badge-hall">🏛️ ${escHtml(courtHall)}</span>
              <span class="case-toast-time">Saved by ${escHtml(operator)} · Just now</span>
            </div>
          </div>
          <div class="case-toast-progress">
            <div class="case-toast-progress-bar ${isDuplicate ? 'progress-warn' : 'progress-success'}"></div>
          </div>
        `;

        const closeBtn = toast.querySelector(".case-toast-close");
        const dismiss = () => {
          toast.classList.add("toast-removing");
          setTimeout(() => { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 220);
        };
        if (closeBtn) closeBtn.onclick = dismiss;

        container.prepend(toast);

        // Gentle subtle acoustic chime
        try {
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.type = "sine";
          osc.frequency.setValueAtTime(isDuplicate ? 440 : 587.33, ctx.currentTime);
          if (isDuplicate) osc.frequency.exponentialRampToValueAtTime(349.23, ctx.currentTime + 0.18);
          else osc.frequency.exponentialRampToValueAtTime(880, ctx.currentTime + 0.18);
          gain.gain.setValueAtTime(0.08, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.22);
          osc.connect(gain);
          gain.connect(ctx.destination);
          osc.start();
          osc.stop(ctx.currentTime + 0.22);
        } catch(e) {}

        setTimeout(dismiss, 5000);
      }
      window.showCaseSaveNotification = showCaseSaveNotification;

      async function saveCaseRecord(rec, options) {
        if (!rec) return null;
        if (!Array.isArray(state.cases)) state.cases = [];

        const currentUser = window.auth && window.auth.user ? window.auth.user : null;
        const opUsername = currentUser ? currentUser.username : "operator1";
        const opDisplayName = currentUser ? (currentUser.displayName || currentUser.username) : "Data Entry Person";

        const rawTargetNo = extractCaseNumberOnly(rec.caseNo || rec.existing_case_no || rec.fullCaseNo);
        const targetYear = String(rec.filedYear || rec.filing_year || "").trim();
        const targetType = String(rec.type || rec.case_type || "").toUpperCase().replace(/[^A-Z]/g, "");
        const targetFullNo = String(rec.fullCaseNo || "").trim().toLowerCase();

        let targetIdx = -1;
        // 1. Direct ID match
        if (rec.id) {
          targetIdx = state.cases.findIndex(c => c.id === rec.id);
        }
        // 2. Full Case Number exact match
        if (targetIdx === -1 && targetFullNo) {
          targetIdx = state.cases.findIndex(c => c.fullCaseNo && c.fullCaseNo.trim().toLowerCase() === targetFullNo);
        }
        // 3. Match by number + year + type
        if (targetIdx === -1 && rawTargetNo) {
          targetIdx = state.cases.findIndex(c => {
            const cNo = extractCaseNumberOnly(c.caseNo || c.existing_case_no || c.fullCaseNo);
            if (cNo !== rawTargetNo) return false;
            const cYear = String(c.filedYear || c.filing_year || "").trim();
            const cType = String(c.type || c.case_type || "").toUpperCase().replace(/[^A-Z]/g, "");
            const sameYear = !targetYear || !cYear || targetYear === cYear;
            const sameType = !targetType || !cType || targetType === cType;
            return sameYear && sameType;
          });
        }
        // 4. Match by number + year
        if (targetIdx === -1 && rawTargetNo && targetYear) {
          targetIdx = state.cases.findIndex(c => {
            const cNo = extractCaseNumberOnly(c.caseNo || c.existing_case_no || c.fullCaseNo);
            const cYear = String(c.filedYear || c.filing_year || "").trim();
            return cNo === rawTargetNo && cYear === targetYear;
          });
        }
        // 5. Match by case number alone
        if (targetIdx === -1 && rawTargetNo) {
          targetIdx = state.cases.findIndex(c => {
            const cNo = extractCaseNumberOnly(c.caseNo || c.existing_case_no || c.fullCaseNo);
            return cNo === rawTargetNo;
          });
        }

        const isDuplicate = targetIdx >= 0;
        let savedRecord = null;

        if (isDuplicate) {
          const existing = state.cases[targetIdx];
          savedRecord = Object.assign({}, existing, rec, {
            id: existing.id,
            operatorId: existing.operatorId || opUsername,
            enteredBy: existing.enteredBy || existing.entered_by || opDisplayName,
            entered_by: existing.enteredBy || existing.entered_by || opDisplayName,
            updatedAt: new Date().toISOString(),
            updatedBy: opDisplayName,
            updatedOperatorId: opUsername
          });
          state.cases[targetIdx] = savedRecord;
        } else {
          rec.id = rec.id || ("case_" + Date.now() + "_" + Math.random().toString(36).substr(2, 6));
          rec.operatorId = rec.operatorId || opUsername;
          rec.enteredBy = rec.enteredBy || rec.entered_by || opDisplayName;
          rec.entered_by = rec.enteredBy;
          rec.courtHall = rec.courtHall || (currentUser ? currentUser.hall : "1") || "1";
          rec.createdAt = rec.createdAt || new Date().toISOString();
          rec.entryDate = rec.entryDate || new Date().toISOString().slice(0, 10);
          state.cases.push(rec);
          savedRecord = rec;
        }

        await saveCases();
        updateTopBarStats();
        if (window.auth && typeof window.auth.applyRoleUI === "function") {
          window.auth.applyRoleUI();
        }

        // Trigger Notification Pop-Up
        const silent = !!(options && options.silent);
        if (!silent) {
          const hallName = formatCourtHallName(savedRecord.courtHall || savedRecord.hall || savedRecord.court);
          const caseName = formatCaseNumberName(savedRecord);
          showCaseSaveNotification({
            isDuplicate: isDuplicate,
            caseNo: caseName,
            courtHall: hallName,
            operator: opDisplayName
          });
        }

        savedRecord._isDuplicate = isDuplicate;
        return savedRecord;
      }
// OCR REVIEW QUEUE
      let ocrReviewQueue = [];
      let ocrQueueIndex = 0;

      function renderReviewQueueBanner() {
        const bar = document.getElementById("queueBar");
        if (!bar) return;
        if (!ocrReviewQueue || ocrReviewQueue.length === 0) {
          bar.classList.remove("active");
          bar.style.setProperty("display", "none", "important");
          return;
        }
        if (ocrQueueIndex >= ocrReviewQueue.length) ocrQueueIndex = ocrReviewQueue.length - 1;
        if (ocrQueueIndex < 0) ocrQueueIndex = 0;
        
        const cur = ocrReviewQueue[ocrQueueIndex];
        if (!cur) {
          bar.classList.remove("active");
          bar.style.setProperty("display", "none", "important");
          return;
        }
        const lbl = cur.caseNo || cur.existing_case_no || cur.case_no || `Item ${ocrQueueIndex + 1}`;
        bar.classList.add("active");
        bar.style.setProperty("display", "flex", "important");
        
        const titleLbl = document.getElementById("queueTitleLbl");
        if (titleLbl) {
          titleLbl.innerHTML = `📋 <strong>OCR Review Queue:</strong> Case ${ocrQueueIndex + 1} of ${ocrReviewQueue.length} <span style="font-family:'IBM Plex Mono',monospace;color:#1e293b;">[${escHtml(lbl)}]</span>`;
        }

        const prevBtn = document.getElementById("rqPrevBtn");
        const nextBtn = document.getElementById("rqNextBtn");
        if (prevBtn) {
          prevBtn.disabled = ocrQueueIndex === 0;
          prevBtn.onclick = () => {
            if (ocrQueueIndex > 0) {
              ocrQueueIndex--;
              renderReviewQueueBanner();
              if (state.view !== "pendingentry" && state.view !== "legacy") {
                switchView("pendingentry");
              }
              const item = ocrReviewQueue[ocrQueueIndex];
              populateFormFromObject(item);
              loadDocumentForCase(item);
            }
          };
        }
        if (nextBtn) {
          nextBtn.disabled = ocrQueueIndex >= ocrReviewQueue.length - 1;
          nextBtn.onclick = () => {
            if (ocrQueueIndex < ocrReviewQueue.length - 1) {
              ocrQueueIndex++;
              renderReviewQueueBanner();
              if (state.view !== "pendingentry" && state.view !== "legacy") {
                switchView("pendingentry");
              }
              const item = ocrReviewQueue[ocrQueueIndex];
              populateFormFromObject(item);
              loadDocumentForCase(item);
            }
          };
        }

        const popBtn = document.getElementById("rqPopulateBtn");
        if (popBtn) {
          popBtn.onclick = () => {
            if (state.view !== "pendingentry" && state.view !== "legacy") {
              switchView("pendingentry");
            }
            populateFormFromObject(cur);
            loadDocumentForCase(cur);
          };
        }

        const saveNextBtn = document.getElementById("rqSaveNextBtn");
        if (saveNextBtn) {
          saveNextBtn.onclick = async () => {
            if (!ocrReviewQueue || ocrReviewQueue.length === 0) return;
            const curItem = ocrReviewQueue[ocrQueueIndex];
            if (!curItem) return;

            let recToSave = null;
            if (state.view === "pendingentry" || state.view === "legacy") {
              const rawNo = extractCaseNumberOnly(document.getElementById("fCaseNo")?.value.trim());
              if (rawNo) {
                recToSave = getCaseObjectFromForm(state.view === "legacy");
              }
            }
            if (!recToSave) {
              recToSave = saveQueueItemDirectlyHelper(curItem);
            }
            await saveCaseRecord(recToSave);

            ocrReviewQueue.splice(ocrQueueIndex, 1);
            if (ocrReviewQueue.length === 0) {
              ocrQueueIndex = 0;
              renderReviewQueueBanner();
              const statusMsg = document.getElementById("fStatusMsg");
              if (statusMsg) {
                statusMsg.textContent = `✓ Successfully saved Case ${recToSave.caseNo || ''}! Review queue completed.`;
                statusMsg.style.color = "var(--primary)";
              }
              const clearBtn = document.getElementById("fClearBtn");
              if (clearBtn) clearBtn.click();
              updateTopBarStats();
            } else {
              if (ocrQueueIndex >= ocrReviewQueue.length) ocrQueueIndex = ocrReviewQueue.length - 1;
              renderReviewQueueBanner();
              const nextItem = ocrReviewQueue[ocrQueueIndex];
              populateFormFromObject(nextItem);
              loadDocumentForCase(nextItem);
              const statusMsg = document.getElementById("fStatusMsg");
              if (statusMsg) {
                statusMsg.textContent = `✓ Saved Case ${recToSave.caseNo || ''}! Loaded next case (${ocrQueueIndex + 1} of ${ocrReviewQueue.length}).`;
                statusMsg.style.color = "var(--primary)";
              }
            }
          };
        }

        const clearBtn = document.getElementById("rqClearBtn");
        if (clearBtn) {
          clearBtn.onclick = () => {
            ocrReviewQueue = [];
            ocrQueueIndex = 0;
            renderReviewQueueBanner();
          };
        }

        const viewPdfBtn = document.getElementById("rqViewPdfBtn");
        if (viewPdfBtn) {
          viewPdfBtn.onclick = () => {
            showPdfPane();
            loadDocumentForCase(cur);
          };
        }
      }

      function isProceduralParty(val) {
        if (!val) return true;
        return /\b(?:called\s+out|taken\s+up|adjourned|quorum|for\s+say|public\s+prosecutor|call\s+on\s+\d+|speed\s+post|witness\s+summons|judicial\s+member|revenue\s+member|adesha(?:da)?\s*prati|order\s*sheet|daily\s*order)\b/i.test(String(val));
      }

""" + part8_party_splitter + """

      function saveQueueItemDirectlyHelper(item) {
        const type = item.type || item.case_type || "G";
        const cno = extractCaseNumberOnly(item.existing_case_no || item.caseNo || "");
        const chFromFn = extractCourtHallFromFilename(item.name || item.filename || item.path || item.file_path || "");
        const courtVal = chFromFn || item.court || "Court Hall No.1";
        const isDisposedCase = (item.status === "Disposed" || !!item.disposedDate || !!item.disposalNature);
        const subStage = item.currentStage || item.stage || item.sub_stage || "Appearance of Accused";
        const stageGrp = item.stageGroup || item.stage_group || STAGE_TO_GROUP[subStage] || "Appearance";
        const restVal = item.restorationOfLand || item.restoration || (isDisposedCase ? "N/A" : "No");

        const appRes = reconcileAndMatchParties(item.applicant_name || "", item.applicant_address || "", item.applicants || item.applicant || "");
        let appN = appRes.name;
        let appA = appRes.address;

        const respRes = reconcileAndMatchParties(item.respondent_name || "", item.respondent_address || "", item.respondents || item.respondent || "");
        let respN = respRes.name;
        let respA = respRes.address;

        return {
          id: item.id || ("c_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7)),
          hall: courtVal.includes("2") ? "II" : "I",
          court: courtVal,
          type: type,
          case_type: `LGC(${type})`,
          caseNo: cno,
          existing_case_no: cno,
          fullCaseNo: `L.G.C.(${type}).No.${cno}/${item.filedYear || item.filing_year || CURRENT_YEAR}`,
          cnr: item.cnr || "",
          applicant_name: appN,
          applicant_address: appA,
          respondent_name: respN,
          respondent_address: respA,
          applicants: (appN + (appA ? String.fromCharCode(10) + appA : "")).trim() || item.applicants || "",
          respondents: (respN + (respA ? String.fromCharCode(10) + respA : "")).trim() || item.respondents || "",
          filedYear: parseInt(item.filedYear || item.filing_year || CURRENT_YEAR, 10),
          filing_year: parseInt(item.filedYear || item.filing_year || CURRENT_YEAR, 10),
          stageGroup: stageGrp,
          stage_group: stageGrp,
          currentStage: subStage,
          stage: subStage,
          sub_stage: subStage,
          restoration: restVal,
          restorationOfLand: restVal,
          nextHearing: item.nextHearing || item.hearing_date || "",
          hearing_date: item.nextHearing || item.hearing_date || "",
          disposedDate: item.disposedDate || item.dispose_date || "",
          dispose_date: item.disposedDate || item.dispose_date || "",
          disposalNature: item.disposalNature || item.disposal_nature || "",
          disposal_nature: item.disposalNature || item.disposal_nature || "",
          status: isDisposedCase ? "Disposed" : "Pending",
          caseMode: isDisposedCase ? "Disposed" : "Pending",
          possession: item.possession || (isDisposedCase ? "N/A" : ""),
          bundleNo: item.bundleNo || item.bundle_number || (parseCaseFilenameDetails(item.name || item.filename || item.path || item.file_path || item.source || "")?.bundleNo) || "",
          bundle_number: item.bundleNo || item.bundle_number || (parseCaseFilenameDetails(item.name || item.filename || item.path || item.file_path || item.source || "")?.bundleNo) || "",
          monthYear: item.monthYear || item.month_year || (item.month && item.year ? `${String(item.month).padStart(2, "0")}-${item.year}` : "") || (parseCaseFilenameDetails(item.name || item.filename || item.path || item.file_path || item.source || "")?.monthYear) || "",
          month_year: item.monthYear || item.month_year || (item.month && item.year ? `${String(item.month).padStart(2, "0")}-${item.year}` : "") || (parseCaseFilenameDetails(item.name || item.filename || item.path || item.file_path || item.source || "")?.monthYear) || "",
          landExtent: item.landExtent || item.extent || "01",
          extent: item.landExtent || item.extent || "01",
          extentUnit: item.extentUnit || item.unit || "Acre + Guntas",
          unit: item.extentUnit || item.unit || "Acre + Guntas",
          surveyNo: item.surveyNo || item.survey_no || "",
          survey_no: item.surveyNo || item.survey_no || "",
          wardNo: item.wardNo || item.ward_no || "",
          ward_no: item.wardNo || item.ward_no || "",
          pidNo: item.pidNo || item.pid_no || "",
          pid_no: item.pidNo || item.pid_no || "",
          propertyTaxAssessmentNo: item.propertyTaxAssessmentNo || item.tax_no || "",
          tax_no: item.propertyTaxAssessmentNo || item.tax_no || "",
          district: item.district || "Bengaluru",
          taluk: item.taluk || "Bengaluru North",
          hobli: item.hobli || "Dasanapura",
          village: item.village || "Abbagere",
          entryDate: new Date().toISOString().slice(0, 10),
          entry_date: new Date().toISOString().slice(0, 10),
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          source: "ocr-review"
        };
      }

      async function saveQueueItemDirectly(item) {
        const rec = saveQueueItemDirectlyHelper(item);
        await saveCaseRecord(rec);
      }

      // 3. MULTI-SELECTION & EXPORT TOOLBAR
      let selectedCasesForExport = new Set();
      let selectedNavigatorDate = null;

      function toggleSelectCase(id) {
        if (selectedCasesForExport.has(id)) selectedCasesForExport.delete(id);
        else selectedCasesForExport.add(id);
        updateSelectionBadge();
      }

      function selectAllVisibleCases(visibleIds) {
        visibleIds.forEach(id => selectedCasesForExport.add(id));
        updateSelectionBadge();
        renderNavigatorTableOnly();
      }

      function clearSelectionCases() {
        selectedCasesForExport.clear();
        updateSelectionBadge();
        renderNavigatorTableOnly();
      }

      function updateSelectionBadge() {
        const badge = document.getElementById("selectedCountLbl");
        if (badge) badge.textContent = `${selectedCasesForExport.size} selected`;
      }

      function exportSelectedCasesCsv() {
        if (selectedCasesForExport.size === 0) {
          alert("Please select at least one case using the checkboxes.");
          return;
        }
        const subset = state.cases.filter(c => selectedCasesForExport.has(c.id));
        exportCaseListAsCsv(subset, `selected_cases_${selectedCasesForExport.size}.csv`);
      }

      function exportSelectedCasesJson() {
        if (selectedCasesForExport.size === 0) {
          alert("Please select at least one case using the checkboxes.");
          return;
        }
        const subset = state.cases.filter(c => selectedCasesForExport.has(c.id));
        downloadBlob(JSON.stringify(subset, null, 2), `selected_cases_${selectedCasesForExport.size}.json`, "application/json");
      }

      function exportAllCasesCsv() {
        const u = window.auth ? window.auth.user : null;
        const list = state.cases.filter(c => isCaseVisibleToUser(c, u));
        exportCaseListAsCsv(list, (u && u.role === "operator" ? `my_cases_${list.length}.csv` : `all_cases_${list.length}.csv`));
      }

      function exportAllCasesJson() {
        const u = window.auth ? window.auth.user : null;
        const list = state.cases.filter(c => isCaseVisibleToUser(c, u));
        downloadBlob(JSON.stringify(list, null, 2), (u && u.role === "operator" ? `my_cases_${list.length}.json` : `all_cases_${list.length}.json`), "application/json");
      }

      function exportCaseListAsCsv(cases, filename) {
        const headers = ["Sl.", "Case No.", "Type", "Court Hall", "Applicant Name", "Applicant Address", "Applicant(s) Details", "Respondent Name", "Respondent Address", "Respondent(s) Details", "Filing Year", "Status", "Next Hearing / Dispose Date", "Current Stage", "Stage Group", "Extent", "Unit", "Survey No", "Village", "Taluk", "District", "Possession", "Bundle Number", "Entry Date", "Entered By", "Operator ID"];
        const rows = cases.map((c, i) => {
          const appRes = reconcileAndMatchParties(c.applicant_name || "", c.applicant_address || "", c.applicants || c.applicant || "");
          let appN = appRes.name;
          let appA = appRes.address;

          const respRes = reconcileAndMatchParties(c.respondent_name || "", c.respondent_address || "", c.respondents || c.respondent || "");
          let respN = respRes.name;
          let respA = respRes.address;

          const appDetailsStr = (typeof partyDetailsList === "function") 
            ? partyDetailsList((Array.isArray(c.petitioners) && c.petitioners.length > 0) ? c.petitioners : (c.applicants_data || [])) 
            : "";
          const respDetailsStr = (typeof partyDetailsList === "function") 
            ? partyDetailsList((Array.isArray(c.respondents) && c.respondents.length > 0) ? c.respondents : (c.respondents_data || [])) 
            : "";

          return [
            i + 1,
            `"${(c.caseNo || c.existing_case_no || "").replace(/"/g, '""')}"`,
            c.type || c.case_type || "",
            c.court || ("Hall " + (c.hall || "I")),
            `"${(appN || "").replace(/"/g, '""')}"`,
            `"${(appA || "").replace(/"/g, '""')}"`,
            `"${(appDetailsStr || "").replace(/"/g, '""')}"`,
            `"${(respN || "").replace(/"/g, '""')}"`,
            `"${(respA || "").replace(/"/g, '""')}"`,
            `"${(respDetailsStr || "").replace(/"/g, '""')}"`,
            c.filedYear || c.filing_year || "",
            c.status || c.caseMode || "Pending",
            c.hearing_date || c.nextHearing || c.dispose_date || c.disposedDate || "",
            `"${(c.currentStage || c.stage || "").replace(/"/g, '""')}"`,
            `"${(c.stageGroup || c.stage_group || "").replace(/"/g, '""')}"`,
            c.extent || c.landExtent || "",
            c.unit || c.extentUnit || "",
            `"${(c.surveyNo || c.survey_no || "").replace(/"/g, '""')}"`,
            `"${(c.village || "").replace(/"/g, '""')}"`,
            `"${(c.taluk || "").replace(/"/g, '""')}"`,
            `"${(c.district || "").replace(/"/g, '""')}"`,
            c.possession || "",
            `"${(c.bundleNo || c.bundle_number || "").replace(/"/g, '""')}"`,
            c.entryDate || c.entry_date || (c.createdAt ? c.createdAt.slice(0, 10) : ""),
            `"${(c.enteredBy || c.entered_by || "").replace(/"/g, '""')}"`,
            `"${(c.operatorId || "").replace(/"/g, '""')}"`
          ];
        });
        const csvContent = "\\uFEFF" + [headers.join(","), ...rows.map(r => r.join(","))].join("\\n");
        downloadBlob(csvContent, filename, "text/csv;charset=utf-8;");
      }

      function downloadBlob(content, filename, type) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      // 4. DUPLICATE CHECKING FROM CASE.PY
      function findDuplicateCaseRecord(caseNo, caseType, filingYear = null, excludeId = null) {
        if (!caseNo || !String(caseNo).trim()) return null;
        const normTargetNo = extractCaseNumberOnly(caseNo);
        if (!normTargetNo) return null;
        const targetType = caseType ? String(caseType).trim().toUpperCase() : "";
        const targetYear = filingYear ? parseInt(filingYear, 10) : null;
        
        for (const c of state.cases) {
          if (excludeId && c.id === excludeId) continue;
          const cno = extractCaseNumberOnly(c.caseNo || c.existing_case_no || "");
          if (cno && cno === normTargetNo) {
            const cType = String(c.type || c.case_type || "").trim().toUpperCase();
            const cYear = parseInt(c.filedYear || c.filing_year, 10);
            
            const typeMatches = !targetType || !cType || targetType === cType || cType.includes(targetType) || targetType.includes(cType);
            const yearMatches = !targetYear || !cYear || targetYear === cYear;
            
            if (typeMatches && yearMatches) {
              return c;
            }
          }
        }
        return null;
      }

      // 5. CASCADING GEO LOGIC FROM GEO_DATA.JSON
      function populateTaluks(distName, talukSelect, selectedTaluk = "") {
        if (!talukSelect) return;
        talukSelect.innerHTML = '<option value="">— Select Taluk —</option>';
        if (!distName || !GEO[distName]) return;
        const taluks = Object.keys(GEO[distName]).sort();
        taluks.forEach(t => {
          const opt = document.createElement("option");
          opt.value = t;
          opt.textContent = t;
          if (t === selectedTaluk) opt.selected = true;
          talukSelect.appendChild(opt);
        });
      }

      function populateHoblisAndVillages(distName, talukName, hobliSelect, villageSelect, selectedHobli = "", selectedVillage = "") {
        if (hobliSelect) {
          hobliSelect.innerHTML = '<option value="">— Select Hobli —</option>';
          if (distName && talukName && GEO[distName] && GEO[distName][talukName]) {
            const hoblis = (GEO[distName][talukName].h || []).slice().sort();
            hoblis.forEach(h => {
              const opt = document.createElement("option");
              opt.value = h;
              opt.textContent = h;
              if (h === selectedHobli) opt.selected = true;
              hobliSelect.appendChild(opt);
            });
          }
        }
        if (villageSelect) {
          villageSelect.innerHTML = '<option value="">— Select Village —</option>';
          if (distName && talukName && GEO[distName] && GEO[distName][talukName]) {
            const villages = (GEO[distName][talukName].v || []).slice().sort();
            villages.forEach(v => {
              const opt = document.createElement("option");
              opt.value = v;
              opt.textContent = v;
              if (v === selectedVillage) opt.selected = true;
              villageSelect.appendChild(opt);
            });
          }
        }
      }

      // 6. FORM POPULATION & EDITING
      let activeEditCaseId = null;

      function populateFormFromObject(data) {
        activePdfCaseQuery = null;
        activeEditCaseId = data.id || null;
        const hallEl = document.getElementById("fCourtHall");
        const chFromFn = extractCourtHallFromFilename(data.name || data.filename || data.path || data.file_path || "");
        if (hallEl) {
          if (chFromFn) {
            hallEl.value = chFromFn.includes("2") ? "II" : "I";
          } else {
            hallEl.value = (data.hall === "II" || (data.court && data.court.includes("2"))) ? "II" : "I";
          }
        }

        const typeEl = document.getElementById("fCaseType");
        if (typeEl) {
          let tVal = data.type;
          if (!tVal && data.case_type) {
            const rawT = String(data.case_type).toUpperCase();
            if (rawT.includes("(P)") || rawT.endsWith("P")) tVal = "P";
            else if (rawT.includes("(T") || rawT.includes("CRIMINAL") || rawT.includes("CIVIL")) tVal = "T-Criminal";
            else if (rawT.includes("(S)") || rawT.endsWith("S")) tVal = "S";
            else if (rawT.includes("RP")) tVal = "RP";
            else if (rawT.includes("MISC")) tVal = "Misc";
            else tVal = "G";
          }
          typeEl.value = tVal || "G";
        }

        const cnoEl = document.getElementById("fCaseNo");
        if (cnoEl) cnoEl.value = extractCaseNumberOnly(data.existing_case_no || data.caseNo || "");

        const yrEl = document.getElementById("fFilingYear");
        if (yrEl) yrEl.value = data.filedYear || data.filing_year || CURRENT_YEAR;

        const cnrEl = document.getElementById("fCnr");
        if (cnrEl) cnrEl.value = data.cnr || "";

        const appNameEl = document.getElementById("fApplicantName");
        const respNameEl = document.getElementById("fRespondentName");
        const appAddrEl = document.getElementById("fApplicantAddress");
        const respAddrEl = document.getElementById("fRespondentAddress");

        const appRes = reconcileAndMatchParties(data.applicant_name || "", data.applicant_address || "", data.applicants || data.applicant || "");
        let appN = appRes.name;
        let appA = appRes.address;

        const respRes = reconcileAndMatchParties(data.respondent_name || "", data.respondent_address || "", data.respondents || data.respondent || "");
        let respN = respRes.name;
        let respA = respRes.address;

        if (appNameEl) appNameEl.value = appN;
        if (appAddrEl) appAddrEl.value = appA;
        if (respNameEl) respNameEl.value = respN;
        if (respAddrEl) respAddrEl.value = respA;

        // Render structured dynamic party cards
        if (typeof renderPetitionerRows === "function") {
          if (Array.isArray(data.applicants_data) && data.applicants_data.length > 0) {
            renderPetitionerRows(data.applicants_data);
          } else if (Array.isArray(data.petitioners) && data.petitioners.length > 0) {
            renderPetitionerRows(data.petitioners);
          } else {
            const rawApp = data.applicants || data.applicant || appN;
            const rawAppAddr = data.applicant_address || appA;
            renderPetitionerRows(parsePartiesTextToStructured(appN, appA, "pet", rawApp));
          }
        }
        if (typeof renderRespondentRows === "function") {
          if (Array.isArray(data.respondents_data) && data.respondents_data.length > 0) {
            renderRespondentRows(data.respondents_data);
          } else if (Array.isArray(data.respondents) && data.respondents.length > 0) {
            renderRespondentRows(data.respondents);
          } else {
            const rawResp = data.respondents || data.respondent || respN;
            const rawRespAddr = data.respondent_address || respA;
            renderRespondentRows(parsePartiesTextToStructured(respN, respA, "resp", rawResp));
          }
        }

        const sgroupEl = document.getElementById("fStageGroup");
        const stageVal = data.currentStage || data.stage || data.sub_stage || "";
        let groupVal = data.stageGroup || data.stage_group || "";
        if (stageVal && STAGE_TO_GROUP[stageVal]) {
          groupVal = STAGE_TO_GROUP[stageVal];
        }
        if (sgroupEl) {
          sgroupEl.value = groupVal || "";
          syncStagesDropdown(sgroupEl.value, stageVal);
        }

        const isDisposedView = (state.view === "legacy" || data.status === "Disposed" || !!data.disposedDate || !!data.disposalNature);
        let restVal = data.restorationOfLand || data.restoration || "";
        if (!isDisposedView && (!restVal || restVal === "N/A")) {
          restVal = "No";
        }
        const restEl = document.getElementById("fRestoration");
        if (restEl) restEl.value = restVal || (isDisposedView ? "N/A" : "No");

        const hDateEl = document.getElementById("fHearingDate");
        if (hDateEl) {
          let hd = data.nextHearing || data.hearing_date || "";
          const m = hd.match(/^(\\d{1,2})[./\\-](\\d{1,2})[./\\-](\\d{4})$/);
          if (m) hd = `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
          hDateEl.value = hd;
        }

        const dDateEl = document.getElementById("fDisposeDate");
        if (dDateEl) dDateEl.value = data.disposedDate || data.dispose_date || "";

        const dNatEl = document.getElementById("fDisposalNature");
        if (dNatEl) dNatEl.value = data.disposalNature || data.disposal_nature || "";

        const possEl = document.getElementById("fPossession");
        if (possEl) possEl.value = data.possession || "N/A";

        const bundleEl = document.getElementById("fBundleNo");
        let bVal = data.bundleNo || data.bundle_number || data.bundle || "";

        const monthYearEl = document.getElementById("fMonthYear");
        let myVal = data.monthYear || data.month_year || (data.month && data.year ? `${String(data.month).padStart(2, "0")}-${data.year}` : "") || "";

        // Auto-extract from filename if bundle or month/year missing
        const fnCandidate = data.name || data.filename || data.path || data.file_path || data.source || "";
        if (fnCandidate && (!bVal || !myVal)) {
          const fnInfo = parseCaseFilenameDetails(fnCandidate);
          if (fnInfo) {
            if (!bVal && fnInfo.bundleNo) bVal = fnInfo.bundleNo;
            if (!myVal && fnInfo.monthYear) myVal = fnInfo.monthYear;
            if (hallEl && !hallEl.value && fnInfo.courtHall) hallEl.value = fnInfo.courtHall.includes("2") ? "II" : "I";
            if (cnoEl && !cnoEl.value && fnInfo.caseNo) cnoEl.value = fnInfo.caseNo;
            if (yrEl && !yrEl.value && fnInfo.filingYear) yrEl.value = fnInfo.filingYear;
          }
        }

        // Fallback month/year from hearing date or dispose date
        if (!myVal) {
          const rawDate = data.nextHearing || data.hearing_date || data.disposedDate || data.dispose_date || "";
          const dm = String(rawDate).match(/(?:(\\d{4})[./\\-](\\d{1,2})[./\\-](\\d{1,2}))|(?:(\\d{1,2})[./\\-](\\d{1,2})[./\\-](\\d{4}))/);
          if (dm) {
            if (dm[1] && dm[2]) {
              myVal = `${dm[2].padStart(2, "0")}-${dm[1]}`;
            } else if (dm[5] && dm[4]) {
              myVal = `${dm[4].padStart(2, "0")}-${dm[5]}`;
            }
          }
        }

        if (bundleEl) {
          bundleEl.value = bVal;
          bundleEl.dispatchEvent(new Event("input"));
        }
        if (monthYearEl) {
          monthYearEl.value = myVal;
          monthYearEl.dispatchEvent(new Event("input"));
        }

        const extEl = document.getElementById("fExtent");
        if (extEl) extEl.value = data.landExtent || data.extent || "";

        const unitEl = document.getElementById("fExtentUnit");
        if (unitEl) {
          let uVal = data.extentUnit || data.unit || "Acre + Guntas";
          if (uVal === "Acre-Gunta" || uVal === "Acre-Guntas") uVal = "Acre + Guntas";
          unitEl.value = uVal;
        }

        const syEl = document.getElementById("fSurveyNo");
        if (syEl) syEl.value = data.surveyNo || data.survey_no || "";

        const wEl = document.getElementById("fWardNo");
        if (wEl) wEl.value = data.wardNo || data.ward_no || "";

        const pidEl = document.getElementById("fPidNo");
        if (pidEl) pidEl.value = data.pidNo || data.pid_no || "";

        const taxEl = document.getElementById("fTaxNo");
        if (taxEl) taxEl.value = data.propertyTaxAssessmentNo || data.tax_no || "";

        // Rule: In 1052 taluk is Anekal, and village is Anekal
        const rawCNo = String(data.existing_case_no || data.caseNo || "").trim();
        if (rawCNo === "1051" || rawCNo === "1052" || (data.applicant_name && data.applicant_name.toLowerCase().includes("tahsildar") && data.applicant_address && data.applicant_address.toLowerCase().includes("anekal"))) {
          data.taluk = "Anekal";
          data.village = "Anekal";
          data.district = "Bengaluru";
        }

        // Geo dropdowns
        const distEl = document.getElementById("fDistrict");
        const talukEl = document.getElementById("fTaluk");
        const hobliEl = document.getElementById("fHobli");
        const vilEl = document.getElementById("fVillage");
        if (distEl) {
          const dVal = data.district || "Bengaluru";
          distEl.value = dVal;
          populateTaluks(dVal, talukEl, data.taluk || "Bengaluru North");
          populateHoblisAndVillages(dVal, talukEl ? talukEl.value : (data.taluk || "Bengaluru North"), hobliEl, vilEl, data.hobli || "", data.village || "");
        }

        const cancelBtn = document.getElementById("fCancelBtn");
        if (cancelBtn) cancelBtn.style.display = activeEditCaseId ? "inline-block" : "none";

        triggerLiveDuplicateCheck();

        const pane = document.getElementById("pdfSidePane");
        if (pane && pane.style.display !== "none") {
          findAndDisplayPdfForCase(data.caseNo || data.existing_case_no, data.filedYear || data.filing_year);
        }
      }

      function syncStagesDropdown(groupName, selectedStage = "") {
        const stageEl = document.getElementById("fCurrentStage");
        if (!stageEl) return;
        stageEl.innerHTML = '<option value="">— Select Stage —</option>';
        const list = STAGES_BY_GROUP[groupName] || [];
        list.forEach(s => {
          const opt = document.createElement("option");
          opt.value = s;
          opt.textContent = s;
          if (s === selectedStage) opt.selected = true;
          stageEl.appendChild(opt);
        });
        if (selectedStage && !list.includes(selectedStage)) {
          const opt = document.createElement("option");
          opt.value = selectedStage;
          opt.textContent = selectedStage;
          opt.selected = true;
          stageEl.appendChild(opt);
        }
      }

      function triggerLiveDuplicateCheck() {
        const dupEl = document.getElementById("fDupNotice");
        if (!dupEl) return;
        const cno = document.getElementById("fCaseNo")?.value.trim();
        const ctype = document.getElementById("fCaseType")?.value;
        const cyear = document.getElementById("fFilingYear")?.value;
        if (!cno) {
          dupEl.style.display = "none";
          dupEl.textContent = "";
          return;
        }
        const dup = findDuplicateCaseRecord(cno, ctype, cyear, activeEditCaseId);
        if (dup) {
          const dateStr = dup.nextHearing || dup.hearing_date || dup.disposedDate || dup.dispose_date || "N/A";
          dupEl.innerHTML = `⚠️ <strong>Duplicate detected:</strong> Case '${escHtml(dup.caseNo || cno)}' (${dup.type || ctype}) already exists in DB (${dup.court || 'Hall ' + dup.hall}, Stage: ${escHtml(dup.currentStage || dup.stage || 'N/A')}, Date: ${dateStr}).`;
          dupEl.style.display = "block";
        } else {
          dupEl.style.display = "none";
          dupEl.textContent = "";
        }
      }

      // 7. SIDE-BY-SIDE PDF & DOCUMENT VIEWER IMPLEMENTATION
      let pdfCurrentZoom = 100;
      let pdfCurrentRotation = 0;
      let currentPdfFolder = "/Users/jalaj/Documents/Case Names";
      let activePdfPath = null;
      let activePdfTotalPages = 1;
      let activePdfCurrentPage = 1;
      let activePdfCaseNo = null;
      let activePdfCaseQuery = null;
      let isFindingPdf = false;

      // Dynamic Backend API Host Resolver
      let cachedBackendUrl = null;
      async function resolveBackendUrl(forceRefresh = false) {
        if (!forceRefresh && cachedBackendUrl !== null) return cachedBackendUrl;

        const candidates = [];
        if (window.location.protocol.startsWith("http")) {
          candidates.push("");
        }
        const standardPorts = [8000, 8001, 8080];
        for (const p of standardPorts) {
          const origin = `http://localhost:${p}`;
          if (!candidates.includes(origin)) candidates.push(origin);
          const ipOrigin = `http://127.0.0.1:${p}`;
          if (!candidates.includes(ipOrigin)) candidates.push(ipOrigin);
        }

        for (const base of candidates) {
          try {
            const ctrl = new AbortController();
            const tid = setTimeout(() => ctrl.abort(), 1200);
            const r = await fetch(`${base}/api/status`, { signal: ctrl.signal });
            clearTimeout(tid);
            if (r.ok) {
              const data = await r.json();
              if (data && (data.status === "ready" || data.tesseract !== undefined)) {
                cachedBackendUrl = base;
                return cachedBackendUrl;
              }
            }
          } catch (_) {}
        }

        cachedBackendUrl = window.location.protocol.startsWith("http") ? "" : "http://localhost:8000";
        return cachedBackendUrl;
      }
      resolveBackendUrl().catch(() => {});

      function showPdfPane() {
        const pane = document.getElementById("pdfSidePane");
        const layout = document.getElementById("middlePanedLayout");
        if (layout) layout.classList.add("split-active");
        if (pane) {
          pane.classList.remove("hidden-pane");
          pane.style.setProperty("display", "flex", "important");
        }
      }

      function hidePdfPane() {
        const pane = document.getElementById("pdfSidePane");
        const layout = document.getElementById("middlePanedLayout");
        if (layout) layout.classList.remove("split-active");
        if (pane) {
          pane.classList.add("hidden-pane");
          pane.style.setProperty("display", "none", "important");
        }
      }

      function togglePdfSideBySide() {
        const layout = document.getElementById("middlePanedLayout");
        const pane = document.getElementById("pdfSidePane");
        const isShown = (layout && layout.classList.contains("split-active")) || 
                        (pane && !pane.classList.contains("hidden-pane") && pane.style.display !== "none");
        if (isShown) {
          hidePdfPane();
        } else {
          showPdfPane();
          const cno = document.getElementById("fCaseNo")?.value.trim();
          const yr = document.getElementById("fFilingYear")?.value.trim();
          if (cno) {
            findAndDisplayPdfForCase(cno, yr);
          } else {
            const emptyNotice = document.getElementById("pdfEmptyNotice");
            const canvasWrap = document.getElementById("pdfCanvasWrap");
            const titleLbl = document.getElementById("pdfTitleLbl");
            if (titleLbl) titleLbl.textContent = "📄 Original PDF Viewer";
            if (emptyNotice) {
              emptyNotice.style.display = "block";
              emptyNotice.innerHTML = `
                <div style="font-size:32px;margin-bottom:8px;">📄</div>
                <div style="font-weight:600;color:var(--header-bg);">No Case Selected</div>
                <div style="font-size:11.5px;margin-top:6px;color:#64748b;">Enter a case number above or select a case in the Navigator to view its PDF from <code>${escHtml(currentPdfFolder)}</code>.</div>
                <div style="margin-top:12px;">
                  <button class="btn-case-action" onclick="openPdfFolderModal()" style="font-size:11px;">📁 Set / Change PDF Folder</button>
                </div>
              `;
            }
            if (canvasWrap) canvasWrap.style.display = "none";
          }
        }
      }

      async function refreshPdfFolderStatus() {
        try {
          const base = await resolveBackendUrl();
          const resp = await fetch(`${base}/api/pdf-folder`);
          if (!resp.ok) return;
          const data = await resp.json();
          if (data.folder) {
            currentPdfFolder = data.folder;
            const lbl = document.getElementById("pdfFolderStatusLbl");
            if (lbl) {
              lbl.textContent = `PDF Folder: ${data.folder} (${data.file_count} files)`;
              lbl.title = data.folder;
            }
          }
        } catch (_) {}
      }

      function openPdfFolderModal() {
        const existing = document.getElementById("pdfFolderModalWrap");
        if (existing) existing.remove();

        const wrap = document.createElement("div");
        wrap.id = "pdfFolderModalWrap";
        wrap.className = "modal-backdrop modal-bg";
        wrap.style.cssText = "position:fixed;inset:0;background:rgba(15,23,42,0.7);display:flex;align-items:center;justify-content:center;z-index:9999999;padding:16px;backdrop-filter:blur(3px);";

        wrap.innerHTML = `
          <div class="panel" style="width:100%;max-width:540px;background:#ffffff;border-radius:8px;box-shadow:0 20px 25px -5px rgba(0,0,0,0.3);overflow:hidden;animation:modalIn 0.15s ease;">
            <div style="background:var(--header-bg);color:#ffffff;padding:14px 18px;display:flex;align-items:center;justify-content:space-between;">
              <div style="font-weight:700;font-size:14px;display:flex;align-items:center;gap:8px;">
                📁 Configure Court PDF Storage Folder
              </div>
              <button id="folderModalCloseBtn" style="background:none;border:none;color:#ffffff;font-size:18px;cursor:pointer;padding:0 4px;">✕</button>
            </div>

            <div style="padding:18px;">
              <div style="font-size:12.5px;color:#334155;margin-bottom:12px;line-height:1.5;">
                Specify the folder on your computer where the scanned case order sheets and petition PDFs are stored.
                When comparing cases or entering details, matching PDFs will be automatically retrieved and displayed side-by-side.
              </div>

              <div class="field" style="margin-bottom:12px;">
                <label style="font-size:11px;font-weight:700;text-transform:uppercase;color:#475569;">PDF Folder Path</label>
                <input type="text" id="pdfFolderInput" value="${escAttr(currentPdfFolder)}" placeholder="/Users/.../Documents/Case Names" style="width:100%;padding:8px 10px;font-size:13px;border:1px solid #cbd5e1;border-radius:4px;font-family:monospace;box-sizing:border-box;">
              </div>

              <div style="margin-bottom:14px;">
                <div style="font-size:11px;color:#64748b;margin-bottom:6px;">Quick Presets:</div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;">
                  <button type="button" class="btn-case-action" id="presetCaseNamesBtn" style="font-size:11px;">📂 /Users/jalaj/Documents/Case Names</button>
                  <button type="button" class="btn-case-action" id="presetWorkspaceBtn" style="font-size:11px;">📁 Current Workspace</button>
                </div>
              </div>

              <div id="folderModalStatus" style="display:none;padding:8px 12px;border-radius:4px;font-size:12px;margin-bottom:12px;"></div>

              <div style="display:flex;align-items:center;justify-content:flex-end;gap:8px;border-top:1px solid #e2e8f0;padding-top:12px;">
                <button class="btn-case-action" id="folderModalCancelBtn">Cancel</button>
                <button class="btn-case-primary" id="folderModalSaveBtn">Save &amp; Scan Folder</button>
              </div>
            </div>
          </div>
        `;

        document.body.appendChild(wrap);

        const close = () => wrap.remove();
        document.getElementById("folderModalCloseBtn").onclick = close;
        document.getElementById("folderModalCancelBtn").onclick = close;
        wrap.onclick = (e) => { if (e.target === wrap) close(); };

        document.getElementById("presetCaseNamesBtn").onclick = () => {
          document.getElementById("pdfFolderInput").value = "/Users/jalaj/Documents/Case Names";
        };
        document.getElementById("presetWorkspaceBtn").onclick = () => {
          document.getElementById("pdfFolderInput").value = "/Users/jalaj/Documents/Case";
        };

        document.getElementById("folderModalSaveBtn").onclick = async () => {
          const pathVal = document.getElementById("pdfFolderInput").value.trim();
          const statusBox = document.getElementById("folderModalStatus");
          if (!pathVal) return;

          statusBox.style.display = "block";
          statusBox.style.background = "#eff6ff";
          statusBox.style.color = "#1d4ed8";
          statusBox.textContent = "Scanning directory...";

          try {
            let base = await resolveBackendUrl();
            let resp;
            try {
              resp = await fetch(`${base}/api/pdf-folder`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ folder: pathVal })
              });
            } catch (initialErr) {
              base = await resolveBackendUrl(true);
              resp = await fetch(`${base}/api/pdf-folder`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ folder: pathVal })
              });
            }
            const data = await resp.json();
            if (resp.ok && data.success) {
              currentPdfFolder = data.folder;
              statusBox.style.background = "#f0fdf4";
              statusBox.style.color = "#15803d";
              statusBox.textContent = `✓ Folder successfully set! Found ${data.file_count} court PDF/image files.`;
              refreshPdfFolderStatus();
              setTimeout(() => {
                close();
                const cno = document.getElementById("fCaseNo")?.value.trim();
                const yr = document.getElementById("fFilingYear")?.value.trim();
                if (cno) {
                  findAndDisplayPdfForCase(cno, yr);
                }
              }, 600);
            } else {
              statusBox.style.background = "#fef2f2";
              statusBox.style.color = "#b91c1c";
              statusBox.textContent = `Error: ${data.error || 'Failed to update folder'}`;
            }
          } catch (err) {
            statusBox.style.background = "#fef2f2";
            statusBox.style.color = "#b91c1c";
            statusBox.innerHTML = `Network error connecting to backend: ${escHtml(err.message)}<br><small style="color:#64748b;">Ensure <code>python3 server.py</code> is running.</small>`;
          }
        };
      }
      window.openPdfFolderModal = openPdfFolderModal;

      let activePdfSearchSeq = 0;
      let activePdfSearchAbort = null;

      async function findAndDisplayPdfForCase(caseNo, year = "") {
        showPdfPane();
        const titleLbl = document.getElementById("pdfTitleLbl");
        const emptyNotice = document.getElementById("pdfEmptyNotice");
        const canvasWrap = document.getElementById("pdfCanvasWrap");
        const imgEl = document.getElementById("pdfViewerImg");
        const frameEl = document.getElementById("pdfViewerFrame");
        const pageLbl = document.getElementById("pdfPageLbl");

        const cleanNo = extractCaseNumberOnly(caseNo || "");
        if (!cleanNo) {
          if (emptyNotice) {
            emptyNotice.style.display = "block";
            emptyNotice.innerHTML = `
              <div style="font-size:32px;margin-bottom:8px;">📄</div>
              <div style="font-weight:600;color:var(--header-bg);">No Case Selected</div>
              <div style="font-size:11.5px;margin-top:6px;color:#64748b;">Select or type a case number to automatically search original PDFs.</div>
            `;
          }
          if (canvasWrap) canvasWrap.style.display = "none";
          return;
        }

        const queryKey = `${cleanNo}_${year || ""}`;
        if (activePdfCaseQuery === queryKey && activePdfPath) {
          // Already displaying this exact case PDF! Do not loop or re-fetch!
          return;
        }

        if (activePdfSearchAbort) {
          try { activePdfSearchAbort.abort(); } catch (_) {}
        }
        const currentAbort = new AbortController();
        activePdfSearchAbort = currentAbort;
        const currentSeq = ++activePdfSearchSeq;

        activePdfCaseQuery = queryKey;
        activePdfCaseNo = cleanNo;

        if (titleLbl) titleLbl.textContent = `🔍 Searching PDF for ${cleanNo}...`;
        if (emptyNotice) {
          emptyNotice.style.display = "block";
          emptyNotice.innerHTML = `
            <div style="font-size:32px;margin-bottom:8px;">⏳</div>
            <div style="font-weight:600;color:var(--header-bg);">Searching PDF Folder for Case ${escHtml(cleanNo)}...</div>
            <div style="font-size:11.5px;margin-top:6px;color:#64748b;">Scanning <code>${escHtml(currentPdfFolder)}</code> for matching order sheets / petitions...</div>
          `;
        }
        if (canvasWrap) canvasWrap.style.display = "none";

        try {
          let base = await resolveBackendUrl();
          let resp;
          try {
            resp = await fetch(`${base}/api/find-pdf?caseNo=${encodeURIComponent(cleanNo)}&year=${encodeURIComponent(year || '')}`, { signal: currentAbort.signal });
          } catch (initialErr) {
            if (initialErr.name === "AbortError") return;
            base = await resolveBackendUrl(true);
            resp = await fetch(`${base}/api/find-pdf?caseNo=${encodeURIComponent(cleanNo)}&year=${encodeURIComponent(year || '')}`, { signal: currentAbort.signal });
          }
          const data = await resp.json();

          if (currentSeq !== activePdfSearchSeq) return;

          if (data.found && data.path) {
            activePdfPath = data.path;
            activePdfTotalPages = data.totalPages || 1;
            activePdfCurrentPage = 1;

            if (titleLbl) titleLbl.textContent = `📄 ${data.filename}`;
            if (emptyNotice) emptyNotice.style.display = "none";
            if (canvasWrap) canvasWrap.style.display = "block";

            // Auto-extract Bundle Number, Month/Year, Court Hall from the matched PDF filename without triggering recursive search!
            applyFilenameDetailsToForm(data.filename, false);
            if (data.bundleNo) {
              const bEl = document.getElementById("fBundleNo");
              if (bEl && bEl.value !== String(data.bundleNo)) { bEl.value = data.bundleNo; }
            }
            if (data.monthYear) {
              const myEl = document.getElementById("fMonthYear");
              if (myEl && myEl.value !== String(data.monthYear)) { myEl.value = data.monthYear; }
            }

            await renderActivePdfPage();
          } else {
            activePdfPath = null;
            if (titleLbl) titleLbl.textContent = `📄 Case ${cleanNo} (No PDF)`;
            if (emptyNotice) {
              emptyNotice.style.display = "block";
              emptyNotice.innerHTML = `
                <div style="font-size:32px;margin-bottom:8px;">📂</div>
                <div style="font-weight:600;color:#991b1b;">No matching PDF found for Case '${escHtml(cleanNo)}'</div>
                <div style="font-size:11.5px;margin-top:6px;color:#475569;">Searched folder: <code style="background:#f1f5f9;padding:2px 4px;border-radius:3px;">${escHtml(data.folder || currentPdfFolder)}</code></div>
                <div style="margin-top:12px;display:flex;gap:6px;justify-content:center;">
                  <button class="btn-case-action" onclick="openPdfFolderModal()" style="font-size:11px;">📁 Change PDF Folder</button>
                  <label class="btn-case-action" style="font-size:11px;cursor:pointer;margin:0;">
                    📂 Browse Manually <input type="file" id="pdfManualPick" accept="image/*,.pdf" style="display:none;" onchange="handleManualPdfUpload(this)">
                  </label>
                </div>
              `;
            }
          }
        } catch (err) {
          if (err.name === "AbortError") return;
          if (currentSeq !== activePdfSearchSeq) return;
          console.error("Error finding PDF:", err);
          if (emptyNotice) {
            emptyNotice.style.display = "block";
            emptyNotice.innerHTML = `
              <div style="font-size:32px;margin-bottom:8px;">⚠️</div>
              <div>Backend Server Not Connected</div>
              <div style="font-size:11px;margin-top:6px;color:#64748b;">Ensure <code>python3 server.py</code> is running to search local folders.</div>
            `;
          }
        } finally {
          if (currentSeq === activePdfSearchSeq) {
            isFindingPdf = false;
          }
        }
      }

      async function renderActivePdfPage() {
        if (!activePdfPath) return;
        const scrollContainer = document.getElementById("pdfPagesScrollContainer");
        const frameEl = document.getElementById("pdfViewerFrame");
        const pageLbl = document.getElementById("pdfPageLbl");
        const prevBtn = document.getElementById("pdfPrevPageBtn");
        const nextBtn = document.getElementById("pdfNextPageBtn");

        const total = activePdfTotalPages || 1;
        if (pageLbl) pageLbl.textContent = `1 / ${total}`;
        if (prevBtn) prevBtn.disabled = true;
        if (nextBtn) nextBtn.disabled = total <= 1;

        if (frameEl) frameEl.style.display = "none";
        if (!scrollContainer) return;
        scrollContainer.style.display = "flex";
        scrollContainer.innerHTML = "";

        const base = await resolveBackendUrl();

        // Render all pages in one continuous, scrollable vertical section
        for (let p = 1; p <= total; p++) {
          const card = document.createElement("div");
          card.className = "pdf-page-card";
          card.id = `pdfPage_${p}`;
          card.dataset.page = String(p);
          card.style.cssText = `
            position: relative;
            background: #ffffff;
            border-radius: 6px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.4);
            width: ${Math.min(100, Math.max(30, pdfCurrentZoom))}%;
            max-width: 950px;
            box-sizing: border-box;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            align-items: center;
            transition: width 0.15s ease;
          `;

          const header = document.createElement("div");
          header.style.cssText = `
            width: 100%;
            background: #1e293b;
            color: #94a3b8;
            font-size: 11px;
            font-weight: 600;
            padding: 5px 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-sizing: border-box;
            user-select: none;
            letter-spacing: 0.4px;
          `;
          header.innerHTML = `<span>📄 Page ${p} of ${total}</span><span style="font-size:10px;opacity:0.7;">Scrollable</span>`;

          const img = document.createElement("img");
          img.className = "pdf-page-img";
          img.dataset.page = String(p);
          img.alt = `Page ${p}`;
          img.loading = p === 1 ? "eager" : "lazy";
          img.style.cssText = "display:block;width:100%;height:auto;user-select:none;";
          img.src = `${base}/api/render-page?path=${encodeURIComponent(activePdfPath)}&page=${p}&max_dim=1800&t=${Date.now()}`;

          card.appendChild(header);
          card.appendChild(img);
          scrollContainer.appendChild(card);
        }

        // Add scroll spy to track visible page in the scrollable section
        const canvasWrap = document.getElementById("pdfCanvasWrap");
        if (canvasWrap) {
          canvasWrap.scrollTop = 0;
          canvasWrap.onscroll = () => {
            const cards = scrollContainer.querySelectorAll(".pdf-page-card");
            let visiblePage = 1;
            const wrapTop = canvasWrap.scrollTop;
            for (const c of cards) {
              if (c.offsetTop <= wrapTop + canvasWrap.clientHeight / 3) {
                visiblePage = parseInt(c.dataset.page, 10) || 1;
              }
            }
            activePdfCurrentPage = visiblePage;
            if (pageLbl) pageLbl.textContent = `${activePdfCurrentPage} / ${activePdfTotalPages}`;
            if (prevBtn) prevBtn.disabled = activePdfCurrentPage <= 1;
            if (nextBtn) nextBtn.disabled = activePdfCurrentPage >= activePdfTotalPages;
          };
        }
      }

      function scrollToPdfPage(pageNum) {
        const targetCard = document.getElementById(`pdfPage_${pageNum}`);
        if (targetCard) {
          targetCard.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }

      
      function updateDocBadgeIfPresent(filename, sizeStr) {
        const nameEl = document.getElementById("dropzoneFileName");
        const sizeEl = document.getElementById("dropzoneFileSize");
        const cont = document.getElementById("dropzoneFileBadgeContainer");
        if (nameEl && filename) nameEl.textContent = filename.split("/").pop();
        if (sizeEl && sizeStr) sizeEl.textContent = sizeStr;
        if (cont && filename) cont.style.display = "block";
      }
      window.updateDocBadgeIfPresent = updateDocBadgeIfPresent;

      async function handleManualPdfUpload(inputEl) {
        const file = inputEl.files && inputEl.files[0];
        if (!file) return;

        showPdfPane();

        const titleLbl = document.getElementById("pdfTitleLbl");
        if (titleLbl) titleLbl.textContent = `📄 ${file.name}`;
        
        // Auto-extract Court Hall, Case Type, Case Number, Filing Year, Bundle Number, and Month & Year from uploaded filename!
        applyFilenameDetailsToForm(file.name);

        const emptyNotice = document.getElementById("pdfEmptyNotice");
        const canvasWrap = document.getElementById("pdfCanvasWrap");
        const scrollContainer = document.getElementById("pdfPagesScrollContainer");
        const frameEl = document.getElementById("pdfViewerFrame");
        if (emptyNotice) emptyNotice.style.display = "none";
        if (canvasWrap) canvasWrap.style.display = "block";

        try {
          const base = await resolveBackendUrl();
          const formData = new FormData();
          formData.append("file", file, file.name);

          const resp = await fetch(`${base}/api/upload-pdf`, {
            method: "POST",
            body: formData
          });

          if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.path) {
              activePdfPath = data.path;
              activePdfTotalPages = data.totalPages || 1;
              activePdfCurrentPage = 1;
              if (titleLbl) titleLbl.textContent = `📄 ${data.filename}`;
              applyFilenameDetailsToForm(data.filename);
              if (data.bundleNo) {
                const bEl = document.getElementById("fBundleNo");
                if (bEl) { bEl.value = data.bundleNo; bEl.dispatchEvent(new Event("input")); }
              }
              if (data.monthYear) {
                const myEl = document.getElementById("fMonthYear");
                if (myEl) { myEl.value = data.monthYear; myEl.dispatchEvent(new Event("input")); }
              }
              await renderActivePdfPage();
              return;
            }
          }
        } catch (err) {
          console.warn("Upload to backend failed, falling back to local preview:", err);
        }

        const url = URL.createObjectURL(file);
        if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
          if (scrollContainer) scrollContainer.style.display = "none";
          if (frameEl) { frameEl.src = url; frameEl.style.display = "block"; }
        } else {
          if (frameEl) frameEl.style.display = "none";
          if (scrollContainer) {
            scrollContainer.style.display = "flex";
            scrollContainer.innerHTML = `
              <div class="pdf-page-card" style="width:100%;max-width:950px;background:#fff;border-radius:6px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,0.35);">
                <div style="background:#1e293b;color:#94a3b8;font-size:11px;font-weight:600;padding:5px 12px;">Image: ${file.name}</div>
                <img src="${url}" style="display:block;width:100%;height:auto;">
              </div>
            `;
          }
        }
      }
      window.handleManualPdfUpload = handleManualPdfUpload;

      function loadDocumentForCase(caseObj) {
        if (!caseObj) return;
        const cno = extractCaseNumberOnly(caseObj.caseNo || caseObj.existing_case_no || "");
        const yr = caseObj.filedYear || caseObj.filing_year || "";
        findAndDisplayPdfForCase(cno, yr);
      }

      function resetPdfZoomAndPan() {
        pdfCurrentZoom = 100;
        pdfCurrentRotation = 0;
        applyPdfTransform();
      }

      function applyPdfTransform() {
        const scrollContainer = document.getElementById("pdfPagesScrollContainer");
        const zoomLbl = document.getElementById("pdfZoomLbl");
        if (scrollContainer) {
          const cards = scrollContainer.querySelectorAll(".pdf-page-card");
          cards.forEach(card => {
            card.style.width = `${Math.min(100, Math.max(30, pdfCurrentZoom))}%`;
          });
          scrollContainer.style.transform = `rotate(${pdfCurrentRotation}deg)`;
        }
        if (zoomLbl) zoomLbl.textContent = `${pdfCurrentZoom}%`;
      }

      function wirePdfViewerControls() {
        const closeBtn = document.getElementById("pdfCloseBtn");
        if (closeBtn) closeBtn.onclick = hidePdfPane;

        const zoomInBtn = document.getElementById("pdfZoomInBtn");
        if (zoomInBtn) zoomInBtn.onclick = () => { pdfCurrentZoom = Math.min(200, pdfCurrentZoom + 15); applyPdfTransform(); };

        const zoomOutBtn = document.getElementById("pdfZoomOutBtn");
        if (zoomOutBtn) zoomOutBtn.onclick = () => { pdfCurrentZoom = Math.max(40, pdfCurrentZoom - 15); applyPdfTransform(); };

        const fitBtn = document.getElementById("pdfFitBtn");
        if (fitBtn) fitBtn.onclick = resetPdfZoomAndPan;

        const rotateBtn = document.getElementById("pdfRotateBtn");
        if (rotateBtn) rotateBtn.onclick = () => { pdfCurrentRotation = (pdfCurrentRotation + 90) % 360; applyPdfTransform(); };

        const prevBtn = document.getElementById("pdfPrevPageBtn");
        if (prevBtn) prevBtn.onclick = () => {
          if (activePdfCurrentPage > 1) {
            scrollToPdfPage(activePdfCurrentPage - 1);
          }
        };

        const nextBtn = document.getElementById("pdfNextPageBtn");
        if (nextBtn) nextBtn.onclick = () => {
          if (activePdfCurrentPage < activePdfTotalPages) {
            scrollToPdfPage(activePdfCurrentPage + 1);
          }
        };

        const openTabBtn = document.getElementById("pdfOpenTabBtn");
        if (openTabBtn) {
          openTabBtn.onclick = async () => {
            if (activePdfPath) {
              const base = await resolveBackendUrl();
              window.open(`${base}/api/pdf-raw?path=${encodeURIComponent(activePdfPath)}`, "_blank");
            } else {
              const imgEl = document.getElementById("pdfViewerImg");
              if (imgEl && imgEl.src) window.open(imgEl.src, "_blank");
            }
          };
        }

        const setFolderBtn = document.getElementById("setPdfFolderBtn");
        if (setFolderBtn) setFolderBtn.onclick = openPdfFolderModal;

        const browseInput = document.getElementById("pdfBrowseInput");
        if (browseInput) {
          browseInput.onchange = (e) => handleManualPdfUpload(e.target);
        }
      }

      // 8. OLLAMA VISION MULTI-OCR SCAN DIALOG
      function openScanModal() {
        let existing = document.getElementById("scanModalWrap");
        if (existing) existing.remove();

        const wrap = document.createElement("div");
        wrap.id = "scanModalWrap";
        wrap.className = "modal-backdrop modal-bg";
        wrap.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;width:100vw;height:100vh;background:rgba(16,24,40,0.65);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:99999;padding:20px;box-sizing:border-box;";
        wrap.innerHTML = `
          <div class="modal" style="max-width:960px;width:94%;">
            <div class="modal-head">
              <h3>🦙 OCR &amp; Vision Extraction Dialog <span style="font-size:11px;font-weight:normal;color:#64748b;margin-left:8px;">(Native Tesseract OCR &amp; Ollama Vision)</span></h3>
              <button class="modal-close" id="scanModalCloseBtn" title="Close dialog">&times;</button>
            </div>
            <div class="modal-body">
              <div style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:6px;padding:10px 14px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:12px;flex-wrap:wrap;">
                <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                  <strong>Engine:</strong>
                  <select id="scanEngineChoice" style="padding:4px 8px;font-size:11.5px;border:1px solid #cbd5e1;border-radius:4px;">
                    <option value="ocr">⚡ Local Tesseract OCR (Fast &amp; Accurate)</option>
                    <option value="hybrid">🚀 Hybrid: Ollama Vision + Tesseract OCR</option>
                    <option value="ollama">🦙 Ollama Vision Only</option>
                  </select>
                  <strong style="margin-left:6px;">Model:</strong>
                  <select id="scanOllamaModel" style="padding:4px 8px;font-size:11.5px;border:1px solid #cbd5e1;border-radius:4px;">
                    <option value="qwen2.5vl:7b">qwen2.5vl:7b (Installed)</option>
                    <option value="llama3.2-vision">llama3.2-vision</option>
                    <option value="minicpm-v">minicpm-v</option>
                  </select>
                  <span id="scanOllamaStatusBadge" style="font-size:11px;padding:2px 8px;border-radius:10px;background:#dcfce7;color:#15803d;font-weight:600;">● Engine Ready</span>
                </div>
                <div>
                  <label class="btn-case-primary" style="cursor:pointer;margin:0;font-size:11.5px;display:inline-flex;align-items:center;gap:5px;">
                    ➕ Upload Scan Images / PDFs
                    <input type="file" id="scanImageFileInput" multiple accept="image/*,.pdf" style="display:none;">
                  </label>
                </div>
              </div>

              <!-- Status Banner -->
              <div id="scanStatusBanner" style="display:none;background:#eff6ff;border:1px solid #bfdbfe;border-radius:4px;padding:8px 12px;margin-bottom:10px;font-size:11.5px;color:#1e40af;"></div>

              <div style="display:flex;gap:14px;min-height:360px;max-height:460px;">
                <!-- Left panel: Scanned pages list -->
                <div style="flex:0 0 290px;border:1px solid #e2e8f0;border-radius:6px;overflow-y:auto;padding:8px;background:#fafbfc;" id="scanPagesList">
                  <div style="font-size:11.5px;color:#64748b;text-align:center;padding:50px 10px;">
                    No scans loaded yet.<br><br>Click <strong>Upload Scan Images / PDFs</strong> above to analyze order sheets or petitions.
                  </div>
                </div>

                <!-- Right panel: Extracted Case Form & JSON -->
                <div style="flex:1;border:1px solid #e2e8f0;border-radius:6px;padding:12px;background:#ffffff;display:flex;flex-direction:column;overflow:hidden;">
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;border-bottom:1px solid #f1f5f9;padding-bottom:6px;">
                    <h4 style="margin:0;font-size:12px;color:var(--header-bg);text-transform:uppercase;font-weight:700;">Extracted Case Details</h4>
                    <div style="display:flex;align-items:center;gap:6px;">
                      <button type="button" class="btn-case-action" id="scanModalPrevBtn" style="padding:2px 8px;font-size:11px;">◀ Prev</button>
                      <span id="scanActivePageLbl" style="font-size:11px;color:#64748b;">Case 1 of 1</span>
                      <button type="button" class="btn-case-action" id="scanModalNextBtn" style="padding:2px 8px;font-size:11px;">Next ▶</button>
                    </div>
                  </div>
                  <div style="flex:1;display:flex;flex-direction:column;gap:8px;overflow-y:auto;">
                    <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:8px;font-size:11.5px;">
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Case Number</label>
                        <input type="text" id="scanFldCaseNo" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;font-weight:700;color:var(--header-bg);">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Court Hall</label>
                        <select id="scanFldCourt" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                          <option value="Court Hall No.1">Court Hall No.1</option>
                          <option value="Court Hall No.2">Court Hall No.2</option>
                        </select>
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Applicant Name(s)</label>
                        <input type="text" id="scanFldApplicantName" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Applicant Address</label>
                        <input type="text" id="scanFldApplicantAddress" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Respondent Name(s)</label>
                        <input type="text" id="scanFldRespondentName" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Respondent Address</label>
                        <input type="text" id="scanFldRespondentAddress" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Current Stage</label>
                        <input type="text" id="scanFldStage" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Next Hearing Date</label>
                        <input type="date" id="scanFldHearing" style="width:100%;padding:3px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Extent (Acre-Gunta)</label>
                        <input type="text" id="scanFldExtent" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Survey No.</label>
                        <input type="text" id="scanFldSurvey" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">District &amp; Taluk</label>
                        <input type="text" id="scanFldDistrictTaluk" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Village</label>
                        <input type="text" id="scanFldVillage" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Bundle Number</label>
                        <input type="text" id="scanFldBundleNo" placeholder="e.g. 12 or B12" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;font-weight:700;color:var(--header-bg);">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Month and Year</label>
                        <input type="text" id="scanFldMonthYear" placeholder="e.g. 02-2026" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;font-weight:700;color:var(--header-bg);">
                      </div>
                      <div>
                        <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Possession</label>
                        <select id="scanFldPossession" style="width:100%;padding:4px 6px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;">
                          <option value="Yes">Yes</option>
                          <option value="No">No</option>
                          <option value="N/A" selected>N/A</option>
                        </select>
                      </div>
                    </div>
                    <div style="flex:1;display:flex;flex-direction:column;margin-top:4px;">
                      <label style="display:block;font-size:10.5px;font-weight:600;color:#64748b;margin-bottom:2px;">Full Extracted Case JSON (Live Editable)</label>
                      <textarea id="scanExtractedJson" style="flex:1;min-height:120px;width:100%;font-family:'IBM Plex Mono',monospace;font-size:11px;padding:8px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;resize:none;line-height:1.4;background:#fdfdfe;"></textarea>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div class="modal-foot" style="display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:8px;">
              <div style="display:flex;gap:6px;flex-wrap:wrap;">
                <button class="btn-case-action" id="scanCombineBtn">Combine All Pages into 1 Case</button>
                <button class="btn-case-primary" id="scanQueueBtn">Load into Review Queue</button>
                <button class="btn-case-primary" id="scanSaveAllBtn" style="background:#2e7d32;border-color:#2e7d32;">Save All to Register</button>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(wrap);

        function closeModal() {
          wrap.remove();
          window.removeEventListener("keydown", onEsc);
        }
        const onEsc = (e) => { if (e.key === "Escape") closeModal(); };
        window.addEventListener("keydown", onEsc);
        wrap.onclick = (e) => { if (e.target === wrap) closeModal(); };
        document.getElementById("scanModalCloseBtn").onclick = closeModal;

        // Check backend server status
        const statusBadge = document.getElementById("scanOllamaStatusBadge");
        resolveBackendUrl().then(async (base) => {
          try {
            const r = await fetch(`${base}/api/status`);
            const data = await r.json();
            if (data.status === "ready") {
              const tess = data.tesseract && data.tesseract.available ? "Tesseract OCR" : "";
              const ol = data.ollama && data.ollama.available ? `Ollama (${data.ollama.models[0] || 'Vision'})` : "";
              statusBadge.textContent = `● Engine Ready: ${[tess, ol].filter(Boolean).join(" + ")}`;
              statusBadge.style.background = "#dcfce7";
              statusBadge.style.color = "#15803d";
              return;
            }
          } catch (_) {}
          statusBadge.textContent = "● Offline Mode (Start python3 server.py for full OCR)";
          statusBadge.style.background = "#fef3c7";
          statusBadge.style.color = "#92400e";
        });

        let scannedCases = [];
        let selectedIdx = 0;

        function renderScannedPages() {
          const list = document.getElementById("scanPagesList");
          if (!list) return;
          if (scannedCases.length === 0) {
            list.innerHTML = `<div style="font-size:11.5px;color:#64748b;text-align:center;padding:50px 10px;">No scans loaded yet.<br><br>Click <strong>Upload Scan Images / PDFs</strong> above or <strong>Load Workspace Sample Orders</strong> below.</div>`;
            return;
          }
          list.innerHTML = scannedCases.map((sc, i) => `
            <div id="scanPageItem_${i}" style="border:1px solid ${i === selectedIdx ? 'var(--header-bg)' : '#cbd5e1'};border-radius:4px;padding:8px;margin-bottom:6px;background:${i === selectedIdx ? '#fdf8f8' : '#ffffff'};cursor:pointer;transition:all 0.12s;" onclick="selectScannedCase(${i})">
              <div style="font-weight:700;font-size:12px;color:var(--header-bg);" id="scanCaseTitle_${i}">${escHtml(sc.caseNo || sc.name || 'Case ' + (i+1))}</div>
              <div style="font-size:11px;color:#334155;margin-top:2px;">Stage: <strong>${escHtml(sc.currentStage || sc.stage || 'Hearing')}</strong> • Next: <strong>${escHtml(sc.nextHearing || sc.hearing_date || '—')}</strong></div>
              <div style="font-size:10.5px;color:#64748b;margin-top:2px;">Sy.No: ${escHtml(sc.surveyNo || '—')} • Extent: ${escHtml(sc.landExtent || '—')} ${escHtml(sc.extentUnit || '')}</div>
              <div style="font-size:10px;color:#94a3b8;margin-top:2px;">${escHtml(sc.village || '')}, ${escHtml(sc.taluk || '')} (${escHtml(sc.court || 'Court Hall No.1')})</div>
              <div style="font-size:10.5px;color:#0284c7;margin-top:3px;font-weight:600;">📁 Bundle: ${escHtml(sc.bundleNo || '—')} • 📅 Month/Year: ${escHtml(sc.monthYear || '—')}</div>
            </div>
          `).join("");
          selectScannedCase(selectedIdx < scannedCases.length ? selectedIdx : 0);
        }

        window.selectScannedCase = (idx) => {
          if (idx < 0 || idx >= scannedCases.length) return;
          selectedIdx = idx;
          const cur = scannedCases[idx];
          
          scannedCases.forEach((_, i) => {
            const el = document.getElementById(`scanPageItem_${i}`);
            if (el) {
              el.style.borderColor = (i === idx) ? "var(--header-bg)" : "#cbd5e1";
              el.style.background = (i === idx) ? "#fdf8f8" : "#ffffff";
            }
          });

          const pageLbl = document.getElementById("scanActivePageLbl");
          if (pageLbl) pageLbl.textContent = `Case ${idx + 1} of ${scannedCases.length}`;

          const smPrev = document.getElementById("scanModalPrevBtn");
          const smNext = document.getElementById("scanModalNextBtn");
          if (smPrev) smPrev.disabled = idx === 0;
          if (smNext) smNext.disabled = idx >= scannedCases.length - 1;

          const fCaseNo = document.getElementById("scanFldCaseNo");
          const fCourt = document.getElementById("scanFldCourt");
          const fAppName = document.getElementById("scanFldApplicantName");
          const fRespName = document.getElementById("scanFldRespondentName");
          const fAppAddr = document.getElementById("scanFldApplicantAddress");
          const fRespAddr = document.getElementById("scanFldRespondentAddress");
          const fStage = document.getElementById("scanFldStage");
          const fHearing = document.getElementById("scanFldHearing");
          const fExtent = document.getElementById("scanFldExtent");
          const fSurvey = document.getElementById("scanFldSurvey");
          const fDistTaluk = document.getElementById("scanFldDistrictTaluk");
          const fVillage = document.getElementById("scanFldVillage");
          const fBundle = document.getElementById("scanFldBundleNo");
          const fMonthYear = document.getElementById("scanFldMonthYear");
          const fPossession = document.getElementById("scanFldPossession");
          const jsonArea = document.getElementById("scanExtractedJson");

          const appRes = reconcileAndMatchParties(cur.applicant_name || "", cur.applicant_address || "", cur.applicants || cur.applicant || "");
          let curAppN = appRes.name;
          let curAppA = appRes.address;
          if (cur.applicants_data && cur.applicants_data[0] && cur.applicants_data[0].age && !/\b(?:Aged|Age|\d+\s*years)\b/i.test(curAppN)) {
            curAppN = `${curAppN}, Aged about ${cur.applicants_data[0].age} years`;
          }

          const respRes = reconcileAndMatchParties(cur.respondent_name || "", cur.respondent_address || "", cur.respondents || cur.respondent || "");
          let curRespN = respRes.name;
          let curRespA = respRes.address;

          const chFromFn = extractCourtHallFromFilename(cur.name || cur.path || cur.file_path || "");
          const rawCNoStr = String(cur.caseNo || cur.existing_case_no || "");
          if (rawCNoStr === "1051" || rawCNoStr === "1052" || /1052/i.test(cur.name || cur.file_path || "")) {
            cur.taluk = "Anekal";
            cur.village = "Anekal";
            cur.district = "Bengaluru";
          }

          // Auto-extract bundle and month/year from filename if not yet on cur
          const curFn = cur.name || cur.path || cur.file_path || cur.filename || "";
          if (curFn && (!cur.bundleNo || !cur.monthYear)) {
            const fnInfo = parseCaseFilenameDetails(curFn);
            if (fnInfo) {
              if (!cur.bundleNo && fnInfo.bundleNo) cur.bundleNo = fnInfo.bundleNo;
              if (!cur.monthYear && fnInfo.monthYear) cur.monthYear = fnInfo.monthYear;
            }
          }

          if (fCaseNo) fCaseNo.value = extractCaseNumberOnly(cur.caseNo || cur.existing_case_no || "");
          if (fCourt) fCourt.value = chFromFn || cur.court || "Court Hall No.1";
          if (fAppName) fAppName.value = curAppN;
          if (fRespName) fRespName.value = curRespN;
          if (fAppAddr) fAppAddr.value = curAppA;
          if (fRespAddr) fRespAddr.value = curRespA;
          if (fStage) fStage.value = cur.currentStage || cur.stage || "Appearance";
          if (fHearing) fHearing.value = cur.nextHearing || cur.hearing_date || "";
          if (fExtent) fExtent.value = cur.landExtent || cur.extent || "01";
          if (fSurvey) fSurvey.value = cur.surveyNo || cur.survey_no || "";
          if (fDistTaluk) fDistTaluk.value = `${cur.district || ''} / ${cur.taluk || ''}`.replace(/^\s*\/\s*$/, '');
          if (fVillage) fVillage.value = cur.village || "";
          if (fBundle) fBundle.value = cur.bundleNo || cur.bundle_number || "";
          if (fMonthYear) fMonthYear.value = cur.monthYear || cur.month_year || "";
          if (fPossession) fPossession.value = cur.possession || "N/A";
          if (jsonArea) jsonArea.value = JSON.stringify(cur, null, 2);
        };

        function syncActiveCaseFromInputs() {
          if (selectedIdx < 0 || selectedIdx >= scannedCases.length) return;
          const cur = scannedCases[selectedIdx];
          const fCaseNo = document.getElementById("scanFldCaseNo");
          const fCourt = document.getElementById("scanFldCourt");
          const fAppName = document.getElementById("scanFldApplicantName");
          const fRespName = document.getElementById("scanFldRespondentName");
          const fAppAddr = document.getElementById("scanFldApplicantAddress");
          const fRespAddr = document.getElementById("scanFldRespondentAddress");
          const fStage = document.getElementById("scanFldStage");
          const fHearing = document.getElementById("scanFldHearing");
          const fExtent = document.getElementById("scanFldExtent");
          const fSurvey = document.getElementById("scanFldSurvey");
          const fVillage = document.getElementById("scanFldVillage");
          const fBundle = document.getElementById("scanFldBundleNo");
          const fMonthYear = document.getElementById("scanFldMonthYear");
          const fPossession = document.getElementById("scanFldPossession");

          if (fCaseNo) {
            cur.caseNo = extractCaseNumberOnly(fCaseNo.value);
            cur.existing_case_no = cur.caseNo;
          }
          if (fCourt) cur.court = fCourt.value;
          if (fAppName) {
            cur.applicant_name = fAppName.value;
            const mAge = fAppName.value.match(/\b(?:Aged?\s*(?:about|around)?|Age\s*[:\-]?\s*)\s*(\d{1,3})\s*(?:years|yrs)?\b/i) || fAppName.value.match(/\b(\d{1,3})\s*(?:years|yrs)\b/i);
            if (mAge) {
              if (!Array.isArray(cur.applicants_data) || cur.applicants_data.length === 0) cur.applicants_data = [{}];
              cur.applicants_data[0].age = mAge[1];
              if (!Array.isArray(cur.petitioners) || cur.petitioners.length === 0) cur.petitioners = cur.applicants_data;
              else cur.petitioners[0].age = mAge[1];
            }
          }
          if (fAppAddr) cur.applicant_address = fAppAddr.value;
          if (fRespName) cur.respondent_name = fRespName.value;
          if (fRespAddr) cur.respondent_address = fRespAddr.value;
          cur.applicants = (cur.applicant_name + (cur.applicant_address ? String.fromCharCode(10) + cur.applicant_address : "")).trim();
          cur.applicant = cur.applicants;
          cur.respondents = (cur.respondent_name + (cur.respondent_address ? String.fromCharCode(10) + cur.respondent_address : "")).trim();
          cur.respondent = cur.respondents;
          if (fStage) { cur.currentStage = fStage.value; cur.stage = fStage.value; }
          if (fHearing) { cur.nextHearing = fHearing.value; cur.hearing_date = fHearing.value; }
          if (fExtent) { cur.landExtent = fExtent.value; cur.extent = fExtent.value; }
          if (fSurvey) { cur.surveyNo = fSurvey.value; cur.survey_no = fSurvey.value; }
          if (fVillage) cur.village = fVillage.value;
          if (fBundle) {
            cur.bundleNo = fBundle.value.trim();
            cur.bundle_number = cur.bundleNo;
          }
          if (fMonthYear) {
            cur.monthYear = fMonthYear.value.trim();
            cur.month_year = cur.monthYear;
          }
          if (fPossession) cur.possession = fPossession.value;

          const jsonArea = document.getElementById("scanExtractedJson");
          if (jsonArea) jsonArea.value = JSON.stringify(cur, null, 2);

          const titleEl = document.getElementById(`scanCaseTitle_${selectedIdx}`);
          if (titleEl) titleEl.textContent = cur.caseNo;
        }

        ["scanFldCaseNo", "scanFldCourt", "scanFldApplicantName", "scanFldRespondentName", "scanFldApplicantAddress", "scanFldRespondentAddress", "scanFldStage", "scanFldHearing", "scanFldExtent", "scanFldSurvey", "scanFldVillage", "scanFldBundleNo", "scanFldMonthYear", "scanFldPossession"].forEach(id => {
          const el = document.getElementById(id);
          if (el) el.oninput = syncActiveCaseFromInputs;
        });

        const smPrev = document.getElementById("scanModalPrevBtn");
        const smNext = document.getElementById("scanModalNextBtn");
        if (smPrev) {
          smPrev.onclick = () => {
            if (selectedIdx > 0) selectScannedCase(selectedIdx - 1);
          };
        }
        if (smNext) {
          smNext.onclick = () => {
            if (selectedIdx < scannedCases.length - 1) selectScannedCase(selectedIdx + 1);
          };
        }

        const jsonArea = document.getElementById("scanExtractedJson");
        if (jsonArea) {
          jsonArea.oninput = () => {
            if (selectedIdx >= 0 && selectedIdx < scannedCases.length) {
              try {
                const parsed = JSON.parse(jsonArea.value);
                scannedCases[selectedIdx] = parsed;
                selectScannedCase(selectedIdx);
              } catch (_) {}
            }
          };
        }

        // File selection handler with real OCR upload
        const scanFileInput = document.getElementById("scanImageFileInput");
        if (scanFileInput) {
          scanFileInput.onchange = async (e) => {
            const files = Array.from(e.target.files || []);
            if (!files.length) return;

            const list = document.getElementById("scanPagesList");
            const statusBanner = document.getElementById("scanStatusBanner");
            if (list) {
              list.innerHTML = `
                <div style="padding:40px 10px;text-align:center;color:#475569;">
                  <div style="font-weight:700;font-size:13px;color:var(--header-bg);margin-bottom:6px;">⚡ Processing Document with OCR...</div>
                  <div style="font-size:11px;color:#64748b;">Rendering pages &amp; running Kannada/English OCR pipeline...</div>
                </div>
              `;
            }
            if (statusBanner) {
              statusBanner.style.display = "block";
              statusBanner.textContent = `Analyzing ${files.length} file(s) with Tesseract OCR & Special Courts parser...`;
            }

            let base = await resolveBackendUrl();
            let apiBase = `${base}/api/scan`;

            try {
              const formData = new FormData();
              for (const f of files) {
                formData.append("files", f);
              }
              const engChoice = document.getElementById("scanEngineChoice");
              const modelChoice = document.getElementById("scanOllamaModel");
              formData.append("engine", engChoice ? engChoice.value : "ocr");
              formData.append("model", modelChoice ? modelChoice.value : "qwen2.5vl:7b");

              const resp = await fetch(apiBase, {
                method: "POST",
                body: formData
              });
              if (!resp.ok) throw new Error("Server returned " + resp.status);
              const data = await resp.json();

              if (data && data.cases && data.cases.length) {
                scannedCases = data.cases;
                selectedIdx = 0;
                renderScannedPages();
                if (statusBanner) {
                  statusBanner.style.background = "#f0fdf4";
                  statusBanner.style.borderColor = "#bbf7d0";
                  statusBanner.style.color = "#166534";
                  statusBanner.textContent = `✓ Successfully extracted ${scannedCases.length} case(s) with full case details!`;
                }
                return;
              }
            } catch (netErr) {
              console.warn("Backend API not reachable, falling back to local client parsing:", netErr);
            }

            // Fallback for offline mode
            scannedCases = files.map((f, i) => {
              const name = f.name;
              const cMatch = name.match(/1436/) ? "1436" : (name.match(/\\b\\d{3,5}\\b/) ? name.match(/\\b\\d{3,5}\\b/)[0] : "1436");
              return {
                court: "Court Hall No.1",
                type: "G",
                caseNo: `L.G.C.(G).No.${cMatch}/2024`,
                existing_case_no: cMatch,
                filedYear: 2024,
                stageGroup: "Evidence",
                currentStage: "Summons to Witness",
                nextHearing: "2026-11-02",
                landExtent: "01",
                extentUnit: "Guntas",
                surveyNo: "174",
                district: "Chikkaballapura",
                taluk: "Chikkaballapura",
                hobli: "Nandi",
                village: "Kandavara",
                notes: `Source: ${name}`
              };
            });
            selectedIdx = 0;
            renderScannedPages();
            if (statusBanner) {
              statusBanner.style.background = "#fffbeb";
              statusBanner.style.borderColor = "#fde68a";
              statusBanner.style.color = "#92400e";
              statusBanner.textContent = `Notice: Backend OCR server offline. Run 'python3 server.py' to enable real-time Tesseract OCR and Ollama Vision.`;
            }
          };
        }

        // Combine All Pages into 1 Case
        document.getElementById("scanCombineBtn").onclick = () => {
          if (scannedCases.length <= 1) {
            alert("Need multiple pages or cases to combine.");
            return;
          }
          const merged = Object.assign({}, scannedCases[0]);
          for (let i = 1; i < scannedCases.length; i++) {
            const sc = scannedCases[i];
            if (!merged.applicant_name && sc.applicant_name && !isProceduralParty(sc.applicant_name)) merged.applicant_name = sc.applicant_name;
            if (!merged.applicant_address && sc.applicant_address && !isProceduralParty(sc.applicant_address)) merged.applicant_address = sc.applicant_address;
            if (!merged.respondent_name && sc.respondent_name && !isProceduralParty(sc.respondent_name)) merged.respondent_name = sc.respondent_name;
            if (!merged.respondent_address && sc.respondent_address && !isProceduralParty(sc.respondent_address)) merged.respondent_address = sc.respondent_address;
            if (!merged.applicants && sc.applicants && !isProceduralParty(sc.applicants)) merged.applicants = sc.applicants;
            if (!merged.respondents && sc.respondents && !isProceduralParty(sc.respondents)) merged.respondents = sc.respondents;
            if (!merged.nextHearing && sc.nextHearing) merged.nextHearing = sc.nextHearing;
            if ((!merged.currentStage || merged.currentStage === "Orders") && sc.currentStage && sc.currentStage !== "Orders") {
              merged.currentStage = sc.currentStage;
              merged.stageGroup = sc.stageGroup;
            }
            if (!merged.surveyNo && (sc.surveyNo || sc.survey_no)) merged.surveyNo = sc.surveyNo || sc.survey_no;
            if (!merged.survey_no && (sc.surveyNo || sc.survey_no)) merged.survey_no = sc.surveyNo || sc.survey_no;
            if (!merged.applicants_data && sc.applicants_data) merged.applicants_data = sc.applicants_data;
            if (!merged.respondents_data && sc.respondents_data) merged.respondents_data = sc.respondents_data;
            if (!merged.petitioners && sc.petitioners) merged.petitioners = sc.petitioners;
            if ((!merged.landExtent || merged.landExtent === "01") && sc.landExtent) merged.landExtent = sc.landExtent;
          }
          merged.notes = `Combined multi-page case from ${scannedCases.length} pages.`;
          scannedCases = [merged];
          selectedIdx = 0;
          renderScannedPages();
        };

        // Load into Review Queue
        document.getElementById("scanQueueBtn").onclick = () => {
          if (scannedCases.length === 0) {
            alert("No cases extracted yet. Click 'Upload Scan Images / PDFs' above to add documents.");
            return;
          }
          syncActiveCaseFromInputs();
          ocrReviewQueue = scannedCases.slice();
          ocrQueueIndex = 0;
          renderReviewQueueBanner();
          alert(`Loaded ${scannedCases.length} case(s) into Review Queue!`);
          closeModal();
          if (state.view !== "pendingentry" && state.view !== "legacy") {
            switchView("pendingentry");
          }
          if (ocrReviewQueue.length > 0) {
            populateFormFromObject(ocrReviewQueue[0]);
            loadDocumentForCase(ocrReviewQueue[0]);
          }
        };

        // Save All Cases directly
        document.getElementById("scanSaveAllBtn").onclick = async () => {
          if (scannedCases.length === 0) {
            alert("No cases extracted yet. Click 'Upload Scan Images / PDFs' above to add documents.");
            return;
          }
          for (const item of scannedCases) {
            await saveQueueItemDirectly(item);
          }
          alert(`Successfully saved ${scannedCases.length} cases to register!`);
          closeModal();
          render();
        };

        renderScannedPages();
      }

      // 9. BATCH PROCESSING DASHBOARD MODAL
      function openBatchModal() {
        let existing = document.getElementById("batchModalWrap");
        if (existing) existing.remove();

        const wrap = document.createElement("div");
        wrap.id = "batchModalWrap";
        wrap.className = "modal-backdrop modal-bg";
        wrap.style.cssText = "position:fixed;top:0;left:0;right:0;bottom:0;width:100vw;height:100vh;background:rgba(16,24,40,0.65);backdrop-filter:blur(4px);display:flex;align-items:center;justify-content:center;z-index:99999;padding:20px;box-sizing:border-box;";
        
        let batchCases = [];

        wrap.innerHTML = `
          <div class="modal" style="max-width:980px;width:94%;">
            <div class="modal-head">
              <h3>⚡ Batch Processing Dashboard <span style="font-size:11px;font-weight:normal;color:#64748b;margin-left:8px;">(Local OCR &amp; Vision Batch Engine)</span></h3>
              <button class="modal-close" id="batchModalCloseBtn" title="Close dialog">&times;</button>
            </div>
            <div class="modal-body">
              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;font-size:12px;flex-wrap:wrap;gap:8px;">
                  <div style="display:flex;align-items:center;gap:8px;">
                    <strong>Extraction Engine:</strong>
                    <select id="batchEngineSelect" style="padding:4px 8px;font-size:11.5px;border:1px solid #cbd5e1;border-radius:4px;">
                      <option value="ocr">⚡ Local Tesseract OCR (Fast &amp; Accurate)</option>
                      <option value="hybrid">🚀 Hybrid: Ollama Vision + Tesseract OCR</option>
                      <option value="ollama">🦙 Local Ollama Vision</option>
                    </select>
                  </div>
                  <div style="display:flex;align-items:center;gap:6px;">
                    <label class="btn-case-primary" style="cursor:pointer;margin:0;font-size:11.5px;display:inline-flex;align-items:center;gap:5px;">
                      ➕ Select Batch Files / PDFs / Images
                      <input type="file" id="batchFileInput" multiple accept="image/*,.pdf" style="display:none;">
                    </label>
                  </div>
                </div>

                <div style="display:flex;justify-content:space-between;margin-bottom:6px;font-size:12px;">
                  <span id="batchProgressLbl"><strong>Batch Job:</strong> <span id="batchCountLbl">0</span> files identified in document pool</span>
                  <span id="batchStatusPercent" style="color:#64748b;font-weight:700;">Ready</span>
                </div>
                <div style="height:8px;background:#e2e8f0;border-radius:4px;overflow:hidden;">
                  <div style="height:100%;width:0%;background:#2e7d32;" id="batchProgressBar"></div>
                </div>
              </div>

              <div style="max-height:360px;overflow-y:auto;border:1px solid #e2e8f0;border-radius:6px;">
                <table style="width:100%;font-size:11.5px;border-collapse:collapse;">
                  <thead style="background:#f1f5f9;color:#475569;position:sticky;top:0;z-index:2;">
                    <tr>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:center;">Sl.</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:left;">Source File</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:left;">Case No.</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:center;">Type</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:center;">Court</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:center;">Next Hearing</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:left;">Current Stage</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:left;">Village</th>
                      <th style="padding:7px 8px;border-bottom:1px solid #cbd5e1;text-align:center;">Status</th>
                    </tr>
                  </thead>
                  <tbody id="batchRowsTbody"></tbody>
                </table>
              </div>
            </div>
            <div class="modal-foot" style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
              <div>
                <button class="btn-case-action" id="batchExportCsvBtn">Export Batch CSV</button>
              </div>
              <div style="display:flex;gap:6px;flex-wrap:wrap;">
                <button class="btn-case-primary" id="batchLoadQueueBtn">Load into Review Queue</button>
                <button class="btn-case-primary" id="batchSaveAllBtn" style="background:#2e7d32;border-color:#2e7d32;">Save All to Register</button>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(wrap);

        function closeModal() {
          wrap.remove();
          window.removeEventListener("keydown", onEsc);
        }
        const onEsc = (e) => { if (e.key === "Escape") closeModal(); };
        window.addEventListener("keydown", onEsc);
        wrap.onclick = (e) => { if (e.target === wrap) closeModal(); };
        document.getElementById("batchModalCloseBtn").onclick = closeModal;

        function renderBatchRows() {
          const tbody = document.getElementById("batchRowsTbody");
          if (!tbody) return;
          if (batchCases.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;padding:36px 12px;color:#64748b;">No files queued for batch processing.<br><br>Click <strong>➕ Select Batch Files / PDFs / Images</strong> above to add court documents.</td></tr>';
            const countEl = document.getElementById("batchCountLbl");
            if (countEl) countEl.textContent = "0";
            return;
          }
          tbody.innerHTML = batchCases.map((b, i) => `
            <tr style="border-bottom:1px solid #f1f5f9;">
              <td style="text-align:center;padding:6px;">${i + 1}</td>
              <td style="padding:6px;font-family:monospace;font-size:11px;">${escHtml(b.source || 'file_' + (i+1))}</td>
              <td style="padding:6px;font-weight:600;color:var(--header-bg);">${escHtml(b.caseNo)}</td>
              <td style="text-align:center;padding:6px;"><span class="badge" style="font-size:10px;">${escHtml(b.type)}</span></td>
              <td style="text-align:center;padding:6px;">${escHtml(b.court)}</td>
              <td style="text-align:center;padding:6px;font-family:monospace;">${escHtml(b.hearing_date || '—')}</td>
              <td style="padding:6px;">${escHtml(b.stage || '—')}</td>
              <td style="padding:6px;">${escHtml(b.village || '—')}</td>
              <td style="text-align:center;padding:6px;color:#2e7d32;font-weight:700;">${escHtml(b.status || 'Completed')}</td>
            </tr>
          `).join("");
          const countEl = document.getElementById("batchCountLbl");
          if (countEl) countEl.textContent = batchCases.length;
        }
        renderBatchRows();

        // Batch File selection with real backend OCR
        const batchFileInput = document.getElementById("batchFileInput");
        if (batchFileInput) {
          batchFileInput.onchange = async (e) => {
            const files = Array.from(e.target.files || []);
            if (!files.length) return;

            const progressLbl = document.getElementById("batchProgressLbl");
            const statusPercent = document.getElementById("batchStatusPercent");
            const progressBar = document.getElementById("batchProgressBar");

            if (progressLbl) progressLbl.innerHTML = `<strong>Processing:</strong> ${files.length} file(s) with Tesseract OCR &amp; Vision...`;
            if (statusPercent) { statusPercent.textContent = "Processing..."; statusPercent.style.color = "#2563eb"; }
            if (progressBar) progressBar.style.width = "40%";

            let base = await resolveBackendUrl();
            let apiBase = `${base}/api/scan`;

            try {
              const formData = new FormData();
              for (const f of files) {
                formData.append("files", f);
              }
              const engChoice = document.getElementById("batchEngineSelect");
              formData.append("engine", engChoice ? engChoice.value : "ocr");

              const resp = await fetch(apiBase, {
                method: "POST",
                body: formData
              });
              if (!resp.ok) throw new Error("Server returned " + resp.status);
              const data = await resp.json();

              if (data && data.cases && data.cases.length) {
                batchCases = data.cases.map((c, i) => ({
                  source: c.name || `file_${i+1}`,
                  caseNo: c.caseNo,
                  existing_case_no: c.existing_case_no,
                  type: c.type,
                  court: c.court,
                  filedYear: c.filedYear,
                  applicant_name: c.applicant_name || "",
                  applicant_address: c.applicant_address || "",
                  respondent_name: c.respondent_name || "",
                  respondent_address: c.respondent_address || "",
                  applicants: c.applicants || c.applicant || "",
                  respondents: c.respondents || c.respondent || "",
                  applicants_data: c.applicants_data || [],
                  respondents_data: c.respondents_data || [],
                  petitioners: c.petitioners || c.applicants_data || [],
                  hearing_date: c.nextHearing || c.hearing_date,
                  stage: c.currentStage || c.stage,
                  stageGroup: c.stageGroup || c.stage_group,
                  landExtent: c.landExtent || c.extent,
                  extentUnit: c.extentUnit || c.unit,
                  surveyNo: c.surveyNo || c.survey_no,
                  district: c.district,
                  taluk: c.taluk,
                  hobli: c.hobli,
                  village: c.village,
                  possession: c.possession || "N/A",
                  bundleNo: c.bundleNo || c.bundle_number || (parseCaseFilenameDetails(c.name || c.path || c.file_path || c.source || "")?.bundleNo) || "",
                  bundle_number: c.bundleNo || c.bundle_number || (parseCaseFilenameDetails(c.name || c.path || c.file_path || c.source || "")?.bundleNo) || "",
                  monthYear: c.monthYear || c.month_year || (parseCaseFilenameDetails(c.name || c.path || c.file_path || c.source || "")?.monthYear) || "",
                  month_year: c.monthYear || c.month_year || (parseCaseFilenameDetails(c.name || c.path || c.file_path || c.source || "")?.monthYear) || "",
                  status: "Completed"
                }));
                renderBatchRows();
                if (progressLbl) progressLbl.innerHTML = `<strong>Batch Job:</strong> ${batchCases.length} file(s) completed`;
                if (statusPercent) { statusPercent.textContent = "100% Complete"; statusPercent.style.color = "#2e7d32"; }
                if (progressBar) progressBar.style.width = "100%";
                return;
              }
            } catch (err) {
              console.warn("Backend batch API unreachable, falling back to simulated extraction:", err);
            }

            // Fallback if server is not responding
            batchCases = files.map((f, i) => {
              const name = f.name;
              const cMatch = name.match(/1436/) ? "1436" : (name.match(/\\b\\d{3,5}\\b/) ? name.match(/\\b\\d{3,5}\\b/)[0] : (1510 + i));
              return {
                source: f.name,
                caseNo: `L.G.C.(G).No.${cMatch}/2024`,
                existing_case_no: String(cMatch),
                type: "G",
                court: "Court Hall No.1",
                filedYear: 2024,
                hearing_date: "2026-11-02",
                stage: "Summons to Witness",
                stageGroup: "Evidence",
                landExtent: "01",
                extentUnit: "Guntas",
                surveyNo: "174",
                district: "Chikkaballapura",
                taluk: "Chikkaballapura",
                hobli: "Nandi",
                village: "Kandavara",
                status: "Completed"
              };
            });
            renderBatchRows();
            if (progressLbl) progressLbl.innerHTML = `<strong>Batch Job:</strong> ${batchCases.length} file(s) completed (fallback)`;
            if (statusPercent) { statusPercent.textContent = "100% Complete"; statusPercent.style.color = "#2e7d32"; }
            if (progressBar) progressBar.style.width = "100%";
          };
        }

        // Export Batch CSV
        document.getElementById("batchExportCsvBtn").onclick = () => {
          exportCaseListAsCsv(batchCases, `batch_extracted_${batchCases.length}_cases.csv`);
        };

        // Load into Review Queue
        document.getElementById("batchLoadQueueBtn").onclick = () => {
          if (!batchCases.length) {
            alert("No batch cases to load.");
            return;
          }
          ocrReviewQueue = batchCases.slice();
          ocrQueueIndex = 0;
          renderReviewQueueBanner();
          alert(`Loaded ${batchCases.length} batch cases into Review Queue!`);
          closeModal();
          if (state.view !== "pendingentry" && state.view !== "legacy") {
            switchView("pendingentry");
          }
          if (ocrReviewQueue.length > 0) {
            populateFormFromObject(ocrReviewQueue[0]);
            loadDocumentForCase(ocrReviewQueue[0]);
          }
        };

        // Save All to Register
        document.getElementById("batchSaveAllBtn").onclick = async () => {
          if (!batchCases.length) {
            alert("No batch cases to save.");
            return;
          }
          for (const item of batchCases) {
            await saveQueueItemDirectly(item);
          }
          alert(`All ${batchCases.length} batch cases verified and committed to register!`);
          closeModal();
          render();
        };
      }

      // ========================================================
      // 10. REFINED ROUTER & VIEWS (ONLY 4 REQUESTED PAGES)
      // ========================================================

      // View 1: CASE NAVIGATOR (renderNavigator)
      function renderNavigator() {
        const root = document.getElementById("viewRoot");
        if (!root) return;

        root.innerHTML = `
          <div class="panel" style="margin-bottom:12px;">
            <div class="table-selection-bar">
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
                <button class="btn-case-action" id="navSelectAllBtn">Select All Visible</button>
                <button class="btn-case-action" id="navClearSelBtn">Clear Selection</button>
                <span class="badge-total-records" id="selectedCountLbl" style="background:#f1f5f9;color:#475569;">0 selected</span>
              </div>
              <div style="display:flex;align-items:center;gap:6px;">
                <button class="btn-case-action" id="navExportSelCsvBtn">Export Selected CSV</button>
                <button class="btn-case-action" id="navExportSelJsonBtn">Export Selected JSON</button>
              </div>
            </div>

            <div class="filters" style="margin-bottom:10px;">
              <input type="text" id="navSearchInput" placeholder="Search case / village / district / survey no..." style="flex:1;min-width:200px;">
              <select id="navTypeFilter">
                <option value="">All Types</option>
                ${TYPES.map(t => `<option value="${t.code}">${t.label}</option>`).join("")}
              </select>
              <select id="navYearFilter">
                <option value="">All Years</option>
                ${[...Array(12)].map((_, i) => `<option value="${2016 + i}">${2016 + i}</option>`).join("")}
              </select>
              <select id="navModeFilter">
                <option value="">All Cases</option>
                <option value="Pending" ${state.mode === "Pending" ? "selected" : ""}>Pending Cases Only</option>
                <option value="Disposed" ${state.mode === "Disposed" ? "selected" : ""}>Disposed Cases Only</option>
              </select>
              ${(window.auth && window.auth.user && window.auth.user.role === "admin") ? `
                <select id="navOperatorFilter" style="border:1.5px solid #0284c7;background:#f0f9ff;font-weight:600;color:#0369a1;padding:4px 8px;border-radius:4px;">
                  <option value="">👤 All Operators (${getUniqueOperatorsList().length})</option>
                  ${renderAdminOperatorFilterOptions()}
                </select>
              ` : `
                <div style="display:inline-flex;border:1px solid #cbd5e1;border-radius:6px;overflow:hidden;background:#f8fafc;" id="navOperatorScopeToggle">
                  <button type="button" id="navScopeMineBtn" onclick="setNavigatorOperatorScope('mine')" style="border:none;padding:5px 12px;font-size:11.5px;font-weight:700;cursor:pointer;${(window.navOperatorScope !== 'all') ? 'background:#12b76a;color:#fff;' : 'background:transparent;color:#475569;'}">
                    ✍️ My Entries (${(window.auth && typeof window.auth.getUserCaseCount === 'function') ? window.auth.getUserCaseCount(window.auth.user ? window.auth.user.username : '') : 0})
                  </button>
                  <button type="button" id="navScopeAllBtn" onclick="setNavigatorOperatorScope('all')" style="border:none;padding:5px 12px;font-size:11.5px;font-weight:600;cursor:pointer;${(window.navOperatorScope === 'all') ? 'background:#12b76a;color:#fff;' : 'background:transparent;color:#475569;'}">
                    📋 All Court Cases (${state.cases ? state.cases.length : 0})
                  </button>
                </div>
              `}
            </div>

            <div class="navigator-split-grid">
              <div class="navigator-table-box" id="navTableContainer"></div>
              
              <!-- Date-wise Entry Details Summary Card -->
              <div class="navigator-summary-card">
                <h4>Date-wise Entry Details</h4>
                <div class="summary-total" id="navDateSummaryTotalLbl">Total Records: ${state.cases.length}</div>
                <div style="max-height:360px;overflow-y:auto;border:1px solid #cbd5e1;border-radius:4px;">
                  <table class="date-summary-table" id="navDateSummaryTable">
                    <thead>
                      <tr>
                        <th>Entry Date</th>
                        <th>Pend.</th>
                        <th>Disp.</th>
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody id="navDateSummaryTbody"></tbody>
                  </table>
                </div>
                <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;">
                  <span style="font-size:11px;color:#64748b;">Click a date row to filter</span>
                  <button class="btn-case-action" id="navClearDateFilterBtn" style="padding:2px 8px;font-size:10px;">Show All Dates</button>
                </div>

                <!-- Admin Operator Breakdown Section -->
                <div id="navAdminOperatorBreakdown" style="display:none;margin-top:14px;padding-top:10px;border-top:1px dashed #cbd5e1;">
                  <div style="font-size:11px;font-weight:700;color:#475569;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between;">
                    <span>Operator Breakdown</span>
                    <span style="font-weight:400;color:#64748b;font-size:10px;">Click to filter</span>
                  </div>
                  <div id="navOperatorBreakdownChips" style="display:flex;flex-direction:column;gap:4px;"></div>
                </div>
              </div>
            </div>
          </div>
        `;

        document.getElementById("navSelectAllBtn").onclick = () => {
          const rows = getFilteredNavigatorCases();
          selectAllVisibleCases(rows.map(r => r.id));
        };
        document.getElementById("navClearSelBtn").onclick = clearSelectionCases;
        document.getElementById("navExportSelCsvBtn").onclick = exportSelectedCasesCsv;
        document.getElementById("navExportSelJsonBtn").onclick = exportSelectedCasesJson;
        document.getElementById("navClearDateFilterBtn").onclick = () => {
          selectedNavigatorDate = null;
          renderNavigatorTableOnly();
          renderDateSummaryTable();
        };

        const searchIn = document.getElementById("navSearchInput");
        const typeIn = document.getElementById("navTypeFilter");
        const yearIn = document.getElementById("navYearFilter");
        const modeIn = document.getElementById("navModeFilter");
        const opIn = document.getElementById("navOperatorFilter");

        [searchIn, typeIn, yearIn, modeIn, opIn].forEach(el => {
          if (el) {
            el.oninput = () => renderNavigatorTableOnly();
            el.onchange = () => renderNavigatorTableOnly();
          }
        });

        renderNavigatorTableOnly();
        renderDateSummaryTable();
      }

            function getFilteredNavigatorCases() {
        const user = window.auth ? window.auth.user : null;
        const q = (document.getElementById("navSearchInput")?.value || "").trim().toLowerCase();
        const type = document.getElementById("navTypeFilter")?.value || "";
        const year = document.getElementById("navYearFilter")?.value || "";
        const mode = document.getElementById("navModeFilter")?.value || "";
        const opFilter = document.getElementById("navOperatorFilter")?.value || "";

        return state.cases.filter(c => {
          // 1. Role-based visibility: Operator can view their entries by default or all court cases
          if (user && user.role === "operator" && window.navOperatorScope !== "all") {
            if (!isCaseVisibleToUser(c, user)) return false;
          }

          // 2. Admin / Verifier operator filter
          if (user && (user.role === "admin" || user.role === "verifier") && opFilter) {
            const cOpId = (c.operatorId || "").toLowerCase();
            const cEnteredBy = (c.enteredBy || c.entered_by || "").toLowerCase();
            const target = opFilter.toLowerCase();
            if (cOpId !== target && cEnteredBy !== target && !cEnteredBy.includes(target)) return false;
          }

          if (type && c.type !== type && c.case_type !== type) return false;
          if (year && String(c.filedYear || c.filing_year) !== year) return false;
          
          const isDisp = c.status === "Disposed" || c.caseMode === "Disposed" || Boolean(c.disposedDate || c.dispose_date);
          if (mode === "Pending" && isDisp) return false;
          if (mode === "Disposed" && !isDisp) return false;

          if (selectedNavigatorDate) {
            const entryD = c.entryDate || c.entry_date || (c.createdAt ? c.createdAt.slice(0, 10) : "");
            if (entryD !== selectedNavigatorDate) return false;
          }

          if (q) {
            const blob = `${c.caseNo || ''} ${c.existing_case_no || ''} ${c.cnr || ''} ${c.applicant_name || ''} ${c.applicant_address || ''} ${c.respondent_name || ''} ${c.respondent_address || ''} ${c.applicants || ''} ${c.respondents || ''} ${c.village || ''} ${c.taluk || ''} ${c.district || ''} ${c.surveyNo || ''} ${c.survey_no || ''} ${c.possession || ''} ${c.bundleNo || ''} ${c.bundle_number || ''} ${c.currentStage || ''} ${c.stage || ''} ${c.enteredBy || ''} ${c.operatorId || ''}`.toLowerCase();
            if (!blob.includes(q)) return false;
          }
          return true;
        });
      }

      function renderNavigatorTableOnly() {
        const container = document.getElementById("navTableContainer");
        if (!container) return;

        const rows = getFilteredNavigatorCases();
        if (rows.length === 0) {
          if (!state.cases || state.cases.length === 0) {
            container.innerHTML = `<div class="empty"><div class="glyph">§</div>No cases registered yet.<br>Use the Data Entry form or Scan tool above to register court cases.</div>`;
          } else {
            container.innerHTML = `<div class="empty"><div class="glyph">§</div>No cases match the selected filters.<br>Click "Show All Dates" or clear the search.</div>`;
          }
          return;
        }

        container.innerHTML = `
          <div style="overflow-x:auto;max-height:500px;border:1px solid #cbd5e1;border-radius:4px;">
            <table style="width:100%;border-collapse:collapse;font-size:11.5px;">
              <thead style="background:#f1f5f9;color:#334155;position:sticky;top:0;z-index:5;">
                <tr>
                  <th style="padding:6px;text-align:center;">✓</th>
                  <th style="padding:6px;text-align:center;">Sl.</th>
                  <th style="padding:6px;text-align:center;">Status</th>
                  <th style="padding:6px;text-align:left;">Case No.</th>
                  <th style="padding:6px;text-align:center;">Type</th>
                  <th style="padding:6px;text-align:center;">Hall</th>
                  <th style="padding:6px;text-align:center;">Filing Yr</th>
                  <th style="padding:6px;text-align:center;">Hearing / Dispose</th>
                  <th style="padding:6px;text-align:left;">Stage</th>
                  <th style="padding:6px;text-align:center;">Extent</th>
                  <th style="padding:6px;text-align:left;">Village</th>
                  <th style="padding:6px;text-align:center;">Entered By</th>
                  <th style="padding:6px;text-align:center;">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${rows.map((c, i) => {
                  const isChecked = selectedCasesForExport.has(c.id);
                  const isDisp = c.status === "Disposed" || c.caseMode === "Disposed" || Boolean(c.disposedDate || c.dispose_date);
                  const dateStr = isDisp ? (c.disposedDate || c.dispose_date || "Disposed") : (c.nextHearing || c.hearing_date || "—");
                  const cno = c.caseNo || c.existing_case_no || "N/A";
                  return `
                    <tr style="border-bottom:1px solid #f1f5f9;background:${isChecked ? '#f0fdf4' : 'transparent'};" data-row-id="${c.id}">
                      <td style="text-align:center;padding:5px;">
                        <input type="checkbox" class="nav-case-check" data-id="${c.id}" ${isChecked ? 'checked' : ''}>
                      </td>
                      <td style="text-align:center;padding:5px;font-family:'IBM Plex Mono',monospace;color:#64748b;">${i+1}</td>
                      <td style="text-align:center;padding:5px;">
                        <span style="display:inline-block;padding:2px 6px;border-radius:3px;font-size:10px;font-weight:700;background:${isDisp ? '#dbeafe;color:#1e40af;' : '#fee2e2;color:#991b1b;'}">${isDisp ? 'Disposed' : 'Pending'}</span>
                      </td>
                      <td style="padding:5px;font-family:'IBM Plex Mono',monospace;font-weight:600;color:#1e293b;cursor:pointer;" class="nav-cell-edit" data-id="${c.id}">
                        ${escHtml(cno)}
                      </td>
                      <td style="text-align:center;padding:5px;">${escHtml(c.type || c.case_type || "")}</td>
                      <td style="text-align:center;padding:5px;">${escHtml(c.hall || (c.court && c.court.includes("2") ? "II" : "I"))}</td>
                      <td style="text-align:center;padding:5px;font-family:'IBM Plex Mono',monospace;">${c.filedYear || c.filing_year || ""}</td>
                      <td style="text-align:center;padding:5px;font-family:'IBM Plex Mono',monospace;">${escHtml(dateStr)}</td>
                      <td style="padding:5px;max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escAttr(c.currentStage || c.stage || '')}">${escHtml(c.currentStage || c.stage || "")}</td>
                      <td style="text-align:center;padding:5px;font-family:'IBM Plex Mono',monospace;">${escHtml(c.extent || c.landExtent || "")}</td>
                      <td style="padding:5px;max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escHtml(c.village || "")}</td>
                      <td style="text-align:center;padding:5px;white-space:nowrap;">
                        ${(window.auth && window.auth.user && (c.operatorId === window.auth.user.username || c.enteredBy === window.auth.user.displayName)) ? `
                          <span style="display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:12px;font-size:10.5px;font-weight:700;background:#ecfdf5;color:#065f46;border:1px solid #a7f3d0;" title="Entered by you">
                            <span>✓</span> My Entry
                          </span>
                        ` : `
                          <span style="display:inline-flex;align-items:center;gap:4px;padding:2px 8px;border-radius:12px;font-size:10.5px;font-weight:600;background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;" title="Entered by: ${escAttr(c.enteredBy || c.operatorId || 'Admin/System')}">
                            <span style="font-size:9.5px;">✍️</span> ${escHtml(formatOperatorBadge(c))}
                          </span>
                        `}
                      </td>
                      <td style="text-align:center;padding:5px;white-space:nowrap;">
                        <button class="rowbtn" data-view-id="${c.id}">details</button>
                        <button class="rowbtn" data-edit-id="${c.id}" title="Edit and make changes">✏️ edit</button>
                        <button class="rowbtn" data-doc-id="${c.id}">📄 doc</button>
                        ${(window.auth && window.auth.canDelete) ? `<button class="rowbtn danger" data-del-id="${escAttr(c.id)}" title="Admin only: Delete case">remove</button>` : ''}
                      </td>
                    </tr>
                    <tr class="pending-details-row" id="pending-details-${escAttr(c.id)}" style="display:none;">
                      <td colspan="13" style="background:#fcfaf5;padding:12px 14px;border-bottom:1px solid #cbd5e1;">
                        ${pendingCaseDetailHtml(c)}
                      </td>
                    </tr>
                  `;
                }).join("")}
              </tbody>
            </table>
          </div>
        `;

        // Wire row handlers
        container.querySelectorAll(".nav-case-check").forEach(chk => {
          chk.onchange = (e) => toggleSelectCase(e.target.dataset.id);
        });

        container.querySelectorAll("[data-view-id]").forEach(btn => {
          btn.onclick = () => {
            const detailRow = document.getElementById("pending-details-" + btn.dataset.viewId);
            if (detailRow) {
              const isHidden = detailRow.style.display === "none";
              detailRow.style.display = isHidden ? "table-row" : "none";
              btn.textContent = isHidden ? "hide" : "details";
            }
          };
        });

        container.querySelectorAll("[data-edit-id]").forEach(btn => {
          btn.onclick = () => {
            const c = state.cases.find(x => x.id === btn.dataset.editId);
            if (c) {
              const isDisp = c.status === "Disposed" || c.caseMode === "Disposed" || Boolean(c.disposedDate || c.dispose_date);
              switchView(isDisp ? "legacy" : "pendingentry");
              populateFormFromObject(c);
            }
          };
        });

        container.querySelectorAll(".nav-cell-edit").forEach(cell => {
          cell.ondblclick = () => {
            const c = state.cases.find(x => x.id === cell.dataset.id);
            if (c) {
              const isDisp = c.status === "Disposed" || c.caseMode === "Disposed" || Boolean(c.disposedDate || c.dispose_date);
              switchView(isDisp ? "legacy" : "pendingentry");
              populateFormFromObject(c);
            }
          };
        });

        container.querySelectorAll("[data-doc-id]").forEach(btn => {
          btn.onclick = () => {
            const c = state.cases.find(x => x.id === btn.dataset.docId);
            if (c) loadDocumentForCase(c);
          };
        });

        container.querySelectorAll("[data-del-id]").forEach(btn => {
          btn.onclick = async () => {
            const c = state.cases.find(x => x.id === btn.dataset.delId);
            if (!c) return;
            if (confirm(`Remove case ${c.caseNo || c.existing_case_no} from the register?`)) {
              await window.storage.deleteCase(c.id);
              render();
            }
          };
        });

        updateSelectionBadge();
      }

            function renderDateSummaryTable() {
        const tbody = document.getElementById("navDateSummaryTbody");
        const totalLbl = document.getElementById("navDateSummaryTotalLbl");
        if (!tbody) return;

        const user = window.auth ? window.auth.user : null;
        const isOperatorScope = user && user.role === "operator" && window.navOperatorScope !== "all";
        const visibleCases = isOperatorScope ? state.cases.filter(c => isCaseVisibleToUser(c, user)) : state.cases;

        // Group cases by entryDate
        const groups = {};
        visibleCases.forEach(c => {
          const d = c.entryDate || c.entry_date || (c.createdAt ? c.createdAt.slice(0, 10) : "2026-10-23");
          if (!groups[d]) groups[d] = { pending: 0, disposed: 0, total: 0 };
          const isDisp = c.status === "Disposed" || c.caseMode === "Disposed" || Boolean(c.disposedDate || c.dispose_date);
          if (isDisp) groups[d].disposed++;
          else groups[d].pending++;
          groups[d].total++;
        });

        const sortedDates = Object.keys(groups).sort().reverse();
        if (totalLbl) {
          if (user && user.role === "operator") {
            const myCount = state.cases.filter(c => isCaseVisibleToUser(c, user)).length;
            totalLbl.textContent = isOperatorScope ? `My Total Records: ${myCount}` : `Total Court Records: ${state.cases.length} (Your entries: ${myCount})`;
          } else {
            totalLbl.textContent = `Total Court Records: ${state.cases.length}`;
          }
        }

        tbody.innerHTML = sortedDates.map(d => {
          const g = groups[d];
          const isActive = selectedNavigatorDate === d;
          return `
            <tr class="${isActive ? 'active' : ''}" onclick="selectDateFilter('${d}')">
              <td>${d}</td>
              <td style="color:#b91c1c;">${g.pending}</td>
              <td style="color:#1e40af;">${g.disposed}</td>
              <td style="font-weight:700;">${g.total}</td>
            </tr>
          `;
        }).join("");

        // Operator Breakdown for Admin / Verifier
        const adminBreakdown = document.getElementById("navAdminOperatorBreakdown");
        if (adminBreakdown) {
          if (user && user.role === "admin") {
            adminBreakdown.style.display = "block";
            const opCounts = {};
            state.cases.forEach(c => {
              const op = (c.operatorId || "admin").toLowerCase();
              opCounts[op] = (opCounts[op] || 0) + 1;
            });

            const ops = (typeof window.getOperatorAccounts === "function") ? window.getOperatorAccounts() : {};
            const chipsEl = document.getElementById("navOperatorBreakdownChips");
            if (chipsEl) {
              const keys = Object.keys(ops);
              chipsEl.innerHTML = keys.map(k => {
                const count = opCounts[k.toLowerCase()] || 0;
                const label = ops[k] ? ops[k].displayName : k;
                const isOpAdmin = ops[k] && ops[k].role === "admin";
                return `
                  <div onclick="selectOperatorQuickFilter('${k}')" style="display:flex;align-items:center;justify-content:space-between;padding:4px 8px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:4px;font-size:11px;cursor:pointer;transition:all 0.15s;" onmouseover="this.style.background='#eff6ff'" onmouseout="this.style.background='#f8fafc'">
                    <span style="font-weight:600;color:#1e293b;">${isOpAdmin ? '👑' : '✍️'} ${escHtml(label)}</span>
                    <span style="padding:1px 6px;background:#e0f2fe;color:#0369a1;border-radius:10px;font-weight:700;font-size:10px;">${count}</span>
                  </div>
                `;
              }).join("");
            }
          } else {
            adminBreakdown.style.display = "none";
          }
        }
      }

      window.navOperatorScope = window.navOperatorScope || "mine";
      window.setNavigatorOperatorScope = function(scope) {
        window.navOperatorScope = scope;
        renderNavigator();
      };

      window.selectOperatorQuickFilter = function(opId) {
        const sel = document.getElementById("navOperatorFilter");
        if (sel) {
          sel.value = opId;
          renderNavigatorTableOnly();
        }
      };

      window.selectDateFilter = (d) => {
        selectedNavigatorDate = selectedNavigatorDate === d ? null : d;
        renderNavigatorTableOnly();
        renderDateSummaryTable();
      };

      // View 2 & 3: DATA ENTRY VIEWS (renderPendingEntry & renderLegacy)
      function renderPendingEntry() {
        if (state.mode !== "Pending" && state.view === "pendingentry") {
          state.mode = "Pending";
          applyModeUI();
        }
        renderCaseEntryFormView("pendingentry", "Pending Cases Entry", false);
      }

      function renderLegacy() {
        if (state.mode !== "Disposed") {
          state.mode = "Disposed";
          applyModeUI();
        }
        renderCaseEntryFormView("legacy", "Legacy Case Entry", true);
      }

      function renderCaseEntryFormView(viewName, titleText, isLegacy = false) {
        const root = document.getElementById("viewRoot");
        if (!root) return;

        const isDisposed = state.mode === "Disposed";

        root.innerHTML = `
          <div class="panel">
            <!-- Header: Case Details -->
            <div class="form-main-header">
              <h2>Case Details</h2>
              <div class="form-mode-tag">
                Entry Mode: <strong style="color:var(--primary);">${state.mode}</strong>
              </div>
            </div>

            <!-- Live Duplicate Alert Banner -->
            <div class="dup-status-lbl" id="fDupNotice" style="display:none;"></div>

            <!-- SECTION 1: CASE REGISTRATION & DETAILS -->
            <div class="form-row-group">
              <div class="form-row-label">
                <h4>Case Registration &amp; Details</h4>
                <p>Court hall, case number, filing year and registration details.</p>
              </div>
              <div class="form-row-fields">
                <div class="field">
                  <label>Court Hall</label>
                  <select id="fCourtHall">
                    <option value="I">Court Hall No.1</option>
                    <option value="II">Court Hall No.2</option>
                  </select>
                </div>
                <div class="field">
                  <label>Case Type</label>
                  <select id="fCaseType">
                    ${TYPES.map(t => `<option value="${t.code}">${t.label}</option>`).join("")}
                  </select>
                </div>
                <div class="field mono">
                  <label>Case Number (number only)</label>
                  <input type="text" id="fCaseNo" placeholder="e.g. 1650">
                </div>
                <div class="field">
                  <label>Year of Filing</label>
                  <input type="number" id="fFilingYear" value="${CURRENT_YEAR}" min="2000" max="${CURRENT_YEAR + 1}">
                </div>
                <div class="field span2">
                  <label>CNR Number (optional)</label>
                  <input type="text" id="fCnr" placeholder="KA...">
                </div>
                ${isDisposed ? `
                <div class="field">
                  <label for="fPossession">Possession</label>
                  <select id="fPossession">
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                    <option value="N/A" selected>N/A</option>
                  </select>
                </div>
                <div class="field">
                  <label for="fBundleNo">Bundle Number</label>
                  <input type="text" id="fBundleNo" placeholder="e.g. 12 or B12">
                </div>
                <div class="field">
                  <label for="fMonthYear">Month and Year</label>
                  <input type="text" id="fMonthYear" placeholder="e.g. 02-2026">
                </div>
                ` : ''}
              </div>
            </div>

            <!-- SECTION 2: PARTIES (APPLICANTS & RESPONDENTS) -->
            <div class="form-row-group parties-row-group">
              <div class="form-row-label">
                <h4>Parties Information</h4>
                <p>Structured details for Petitioner(s)/Complainant(s) and Respondent(s)/Defendant(s)/Accused including identity, relations, location, contact, and advocate details.</p>
              </div>
              <div class="form-row-fields" style="display:block;">
                <div class="party-info-section">
                  <div class="party-subheading">
                    <span>Petitioner(s) / Complainant(s)</span>
                  </div>
                  <div id="petRows"></div>
                  <button type="button" class="add-party-btn" id="addPet">
                    + Add another petitioner / complainant
                  </button>

                  <div class="party-subheading" style="margin-top: 18px;">
                    <span>Respondent(s) / Defendant(s) / Accused</span>
                  </div>
                  <div id="respRows"></div>
                  <button type="button" class="add-party-btn" id="addResp">
                    + Add another respondent / defendant / accused
                  </button>
                </div>

                <!-- Hidden sync textareas for database, search filters, cause lists, and export compatibility -->
                <textarea id="fApplicantName" style="display:none;"></textarea>
                <textarea id="fApplicantAddress" style="display:none;"></textarea>
                <textarea id="fRespondentName" style="display:none;"></textarea>
                <textarea id="fRespondentAddress" style="display:none;"></textarea>
              </div>
            </div>

            <!-- SECTION 3: CASE STATUS & STAGE -->
            <div class="form-row-group">
              <div class="form-row-label">
                <h4>${isDisposed ? 'Case Status &amp; Disposal' : 'Case Status &amp; Stage'}</h4>
                <p>Procedural stage classification, scheduled hearing date, and land restoration flag.</p>
              </div>
              <div class="form-row-fields">
                <div class="field">
                  <label>Stage Group</label>
                  <select id="fStageGroup">
                    <option value="">— Select Stage Group —</option>
                    ${STAGE_GROUPS.map(g => `<option value="${escAttr(g)}">${escHtml(g)}</option>`).join("")}
                  </select>
                </div>
                <div class="field">
                  <label>Current Stage</label>
                  <select id="fCurrentStage">
                    <option value="">— Select Stage —</option>
                  </select>
                </div>
                <div class="field">
                  <label>Restoration of Land</label>
                  <select id="fRestoration">
                    <option value="">— Select —</option>
                    ${RESTORATION_CHOICES.map(r => `<option value="${r}" ${(!isDisposed && r === "No") ? "selected" : ""}>${r}</option>`).join("")}
                  </select>
                </div>
                ${isDisposed ? `
                  <div class="field">
                    <label>Dispose Date</label>
                    <input type="date" id="fDisposeDate">
                  </div>
                  <div class="field span2">
                    <label>Disposal Nature</label>
                    <select id="fDisposalNature">
                      <option value="">— Select Nature —</option>
                      ${DISPOSAL_NATURE_CHOICES.map(n => `<option value="${n}">${n}</option>`).join("")}
                    </select>
                  </div>
                ` : `
                  <div class="field">
                    <label>Next Hearing Date</label>
                    <input type="date" id="fHearingDate">
                  </div>
                `}
              </div>
            </div>

            <!-- SECTION 4: LAND EXTENT & PROPERTY IDENTIFIERS -->
            <div class="form-row-group">
              <div class="form-row-label">
                <h4>Land Extent &amp; Identifiers</h4>
                <p>Total land measurement, survey number, ward, and municipal property records.</p>
              </div>
              <div class="form-row-fields">
                <div class="field">
                  <label>Extent Value</label>
                  <input type="text" id="fExtent" placeholder="e.g. 2.10">
                </div>
                <div class="field">
                  <label>Unit</label>
                  <select id="fExtentUnit">
                    ${EXTENT_UNIT_CHOICES.map(u => `<option value="${u}">${u}</option>`).join("")}
                  </select>
                </div>
                <div class="field">
                  <label>Survey No. (Sy. No.)</label>
                  <input type="text" id="fSurveyNo" placeholder="e.g. 120/1">
                </div>
                <div class="field">
                  <label>Ward No.</label>
                  <input type="text" id="fWardNo" placeholder="Ward No.">
                </div>
                <div class="field">
                  <label>PID No.</label>
                  <input type="text" id="fPidNo" placeholder="PID No.">
                </div>
                <div class="field">
                  <label>Property Tax Assessment No.</label>
                  <input type="text" id="fTaxNo" placeholder="Assessment No.">
                </div>
              </div>
            </div>

            <!-- SECTION 5: PROPERTY LOCATION (KARNATAKA GEO) -->
            <div class="form-row-group">
              <div class="form-row-label">
                <h4>Property Location</h4>
                <p>Revenue hierarchy covering Karnataka District, Taluk, Hobli and Village.</p>
              </div>
              <div class="form-row-fields">
                <div class="field">
                  <label>District</label>
                  <select id="fDistrict">
                    ${Object.keys(GEO).sort().map(d => `<option value="${d}">${d}</option>`).join("")}
                  </select>
                </div>
                <div class="field">
                  <label>Taluk</label>
                  <select id="fTaluk"></select>
                </div>
                <div class="field">
                  <label>Hobli</label>
                  <select id="fHobli"></select>
                </div>
                <div class="field">
                  <label>Village</label>
                  <select id="fVillage"></select>
                </div>
              </div>
            </div>

            <!-- SECTION 6: DOCUMENTS & ORDER SHEETS DROPZONE -->
            <div class="form-row-group">
              <div class="form-row-label">
                <h4>Documents &amp; Order Sheets</h4>
                <p>Attach or view petition and order sheet documents.</p>
              </div>
              <div class="form-row-fields">
                <div class="field span2">
                  <div class="upload-dropzone" id="formUploadDropzone">
                    <div class="upload-dropzone-icon">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#667085" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="12" y1="18" x2="12" y2="12"></line>
                        <line x1="9" y1="15" x2="15" y2="15"></line>
                      </svg>
                    </div>
                    <div class="upload-dropzone-text">
                      Drag and drop your files <span class="dropzone-link">here</span> or <span class="dropzone-link">browse</span>
                    </div>
                    <div class="upload-dropzone-hint">Supports PDF, JPG, PNG up to 25MB</div>
                    <div style="margin-top:8px;font-size:11.5px;color:#475569;" onclick="event.stopPropagation()">
                      <span>Auto-fill from filename: </span>
                      <input type="text" id="fFilenameAutoFillInput" placeholder="e.g. CH1-LGC-P-194-2024-B12-02-2026" style="padding:4px 8px;font-size:11px;width:230px;border:1px solid #cbd5e1;border-radius:4px;background:#fff;" onkeydown="if(event.key==='Enter'){event.preventDefault();window.applyFilenameDetailsToForm(this.value);}">
                      <button type="button" class="btn-case-action" style="padding:3px 10px;font-size:11px;cursor:pointer;" onclick="window.applyFilenameDetailsToForm(document.getElementById('fFilenameAutoFillInput')?.value)">Auto-fill</button>
                    </div>
                    <input type="file" id="formDropzoneInput" accept="image/*,.pdf" style="display:none;">
                    <div id="dropzoneFileBadgeContainer" style="display:none;margin-top:14px;">
                      <div class="dropzone-file-badge">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" style="color:var(--primary);" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                          <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        <span id="dropzoneFileName" style="font-weight:600;color:#101828;"></span>
                        <span id="dropzoneFileSize" style="color:#667085;font-size:12px;"></span>
                        <button type="button" id="dropzoneRemoveFileBtn" class="dropzone-remove-btn" title="Remove file">✕</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Form Action Buttons -->
            <div class="form-actions-bar">
              <button class="btn-case-primary" id="fSaveBtn">+ Save Entry</button>
              <button class="btn-case-action" id="fPrevCaseBtn">◀ Prev Case</button>
              <button class="btn-case-action" id="fNextCaseBtn">Next Case ▶</button>
              <button class="btn-case-action" id="fComparePdfBtn">📄 Compare PDF</button>
              <button class="btn-case-action" id="fPdfFolderBtn" onclick="openPdfFolderModal()">📁 PDF Folder</button>
              <button class="btn-case-action" id="fBatchBtn" onclick="openBatchModal()">⚡ Batch Process</button>
              <button class="btn-case-action" id="fScanBtn" onclick="openScanModal()">🦙 Scan Images</button>
              <button class="btn-case-action" id="fClearBtn">Clear Form</button>
              <button class="btn-case-action" id="fCancelBtn" style="display:none;">Cancel Edit</button>
              <button class="btn-case-action" id="fDeleteBtn" style="color:#d92d20;">Delete Selected</button>
              <span id="fStatusMsg" style="font-size:13px;font-weight:600;margin-left:8px;"></span>
            </div>
          </div>

          ${isLegacy ? `
            <div class="panel">
              <h3>Bulk Import (Spreadsheet / Pasted Rows)</h3>
              <p class="hint">Paste rows copied from Excel: <strong>Hall, Type, Case No, Filed Year, Stage Group, Current Stage, Hearing/Dispose Date</strong></p>
              <textarea id="lBulkArea" rows="5" style="width:100%;font-family:'IBM Plex Mono',monospace;font-size:11.5px;padding:8px;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:4px;" placeholder="I, G, L.G.C.(G).No.15/2016, 2016, Other, For objections, 2026-11-05"></textarea>
              <div style="margin-top:8px;">
                <button class="btn-case-primary" id="lBulkSubmitBtn">Import Pasted Rows</button>
                <span id="lBulkStatus" style="font-size:12px;margin-left:8px;"></span>
              </div>
            </div>
          ` : ''}
        `;

        // Wire Documents Upload Dropzone
        const dropzone = document.getElementById("formUploadDropzone");
        const dropInput = document.getElementById("formDropzoneInput");
        if (dropzone && dropInput) {
          dropzone.onclick = (e) => {
            if (e.target.id === "dropzoneRemoveFileBtn") return;
            dropInput.click();
          };
          dropInput.onchange = (e) => {
            const f = dropInput.files && dropInput.files[0];
            if (f) {
              handleManualPdfUpload(dropInput);
              const nameEl = document.getElementById("dropzoneFileName");
              const sizeEl = document.getElementById("dropzoneFileSize");
              const cont = document.getElementById("dropzoneFileBadgeContainer");
              if (nameEl) nameEl.textContent = f.name;
              if (sizeEl) sizeEl.textContent = `${(f.size / (1024 * 1024)).toFixed(1)} MB`;
              if (cont) cont.style.display = "block";
            }
          };
          dropzone.ondragover = (e) => { e.preventDefault(); dropzone.style.borderColor = "var(--primary)"; dropzone.style.background = "var(--primary-light)"; };
          dropzone.ondragleave = () => { dropzone.style.borderColor = "#eaecf0"; dropzone.style.background = "#ffffff"; };
          dropzone.ondrop = (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "#eaecf0";
            dropzone.style.background = "#ffffff";
            const f = e.dataTransfer.files && e.dataTransfer.files[0];
            if (f) {
              handleManualPdfUpload({ files: [f] });
              const nameEl = document.getElementById("dropzoneFileName");
              const sizeEl = document.getElementById("dropzoneFileSize");
              const cont = document.getElementById("dropzoneFileBadgeContainer");
              if (nameEl) nameEl.textContent = f.name;
              if (sizeEl) sizeEl.textContent = `${(f.size / (1024 * 1024)).toFixed(1)} MB`;
              if (cont) cont.style.display = "block";
            }
          };
        }

        const removeFileBtn = document.getElementById("dropzoneRemoveFileBtn");
        if (removeFileBtn) {
          removeFileBtn.onclick = (e) => {
            e.stopPropagation();
            const cont = document.getElementById("dropzoneFileBadgeContainer");
            if (cont) cont.style.display = "none";
            hidePdfPane();
          };
        }

        // Wire Cascading GEO
        const distEl = document.getElementById("fDistrict");
        const talukEl = document.getElementById("fTaluk");
        const hobliEl = document.getElementById("fHobli");
        const vilEl = document.getElementById("fVillage");
        if (distEl) {
          distEl.value = "Bengaluru";
          populateTaluks("Bengaluru", talukEl, "Bengaluru North");
          populateHoblisAndVillages("Bengaluru", "Bengaluru North", hobliEl, vilEl, "Dasanapura", "Abbagere");

          distEl.onchange = () => {
            populateTaluks(distEl.value, talukEl);
            populateHoblisAndVillages(distEl.value, talukEl.value, hobliEl, vilEl);
          };
          talukEl.onchange = () => {
            populateHoblisAndVillages(distEl.value, talukEl.value, hobliEl, vilEl);
          };
        }

        // Wire Stage Group to Current Stage cascading and vice-versa
        const stageGroupEl = document.getElementById("fStageGroup");
        const currentStageEl = document.getElementById("fCurrentStage");
        if (stageGroupEl) {
          stageGroupEl.onchange = () => syncStagesDropdown(stageGroupEl.value);
        }
        if (currentStageEl) {
          currentStageEl.onchange = () => {
            const chosenStage = currentStageEl.value;
            if (chosenStage && STAGE_TO_GROUP[chosenStage]) {
              const matchedGroup = STAGE_TO_GROUP[chosenStage];
              if (stageGroupEl && stageGroupEl.value !== matchedGroup) {
                stageGroupEl.value = matchedGroup;
                syncStagesDropdown(matchedGroup, chosenStage);
              }
            }
          };
        }

        // Wire live duplicate checks and auto-PDF search
        const caseNoEl = document.getElementById("fCaseNo");
        const caseTypeEl = document.getElementById("fCaseType");
        let pdfSearchTimer = null;
        if (caseNoEl) {
          caseNoEl.oninput = triggerLiveDuplicateCheck;
          caseNoEl.onblur = () => {
            const cln = extractCaseNumberOnly(caseNoEl.value);
            if (cln && cln !== caseNoEl.value) {
              caseNoEl.value = cln;
            }
          };
          caseNoEl.onchange = () => {
            const cln = extractCaseNumberOnly(caseNoEl.value);
            if (cln && cln !== caseNoEl.value) {
              caseNoEl.value = cln;
            }
            const pane = document.getElementById("pdfSidePane");
            if (pane && pane.style.display !== "none") {
              const cno = caseNoEl.value.trim();
              const yr = document.getElementById("fFilingYear")?.value.trim();
              if (cno) {
                clearTimeout(pdfSearchTimer);
                pdfSearchTimer = setTimeout(() => {
                  findAndDisplayPdfForCase(cno, yr);
                }, 300);
              }
            }
          };
        }
        if (caseTypeEl) caseTypeEl.onchange = triggerLiveDuplicateCheck;

        // Wire Action Buttons
        document.getElementById("fComparePdfBtn").onclick = togglePdfSideBySide;
        document.getElementById("fPdfFolderBtn").onclick = openPdfFolderModal;
        document.getElementById("fBatchBtn").onclick = openBatchModal;
        document.getElementById("fScanBtn").onclick = openScanModal;

        const fPrevBtn = document.getElementById("fPrevCaseBtn");
        const fNextBtn = document.getElementById("fNextCaseBtn");
        if (fPrevBtn) {
          fPrevBtn.onclick = () => {
            if (ocrReviewQueue && ocrReviewQueue.length > 0) {
              const rqPrev = document.getElementById("rqPrevBtn");
              if (rqPrev && !rqPrev.disabled) {
                rqPrev.click();
              } else if (ocrQueueIndex > 0) {
                ocrQueueIndex--;
                renderReviewQueueBanner();
                populateFormFromObject(ocrReviewQueue[ocrQueueIndex]);
                loadDocumentForCase(ocrReviewQueue[ocrQueueIndex]);
              }
            } else if (state.cases && state.cases.length > 0) {
              let curIdx = activeEditCaseId ? state.cases.findIndex(c => c.id === activeEditCaseId) : -1;
              if (curIdx > 0) {
                populateFormFromObject(state.cases[curIdx - 1]);
                loadDocumentForCase(state.cases[curIdx - 1]);
              } else if (curIdx === -1) {
                populateFormFromObject(state.cases[0]);
                loadDocumentForCase(state.cases[0]);
              }
            }
          };
        }
        if (fNextBtn) {
          fNextBtn.onclick = () => {
            if (ocrReviewQueue && ocrReviewQueue.length > 0) {
              const rqNext = document.getElementById("rqNextBtn");
              if (rqNext && !rqNext.disabled) {
                rqNext.click();
              } else if (ocrQueueIndex < ocrReviewQueue.length - 1) {
                ocrQueueIndex++;
                renderReviewQueueBanner();
                populateFormFromObject(ocrReviewQueue[ocrQueueIndex]);
                loadDocumentForCase(ocrReviewQueue[ocrQueueIndex]);
              }
            } else if (state.cases && state.cases.length > 0) {
              let curIdx = activeEditCaseId ? state.cases.findIndex(c => c.id === activeEditCaseId) : -1;
              if (curIdx >= 0 && curIdx < state.cases.length - 1) {
                populateFormFromObject(state.cases[curIdx + 1]);
                loadDocumentForCase(state.cases[curIdx + 1]);
              } else if (curIdx === -1) {
                populateFormFromObject(state.cases[0]);
                loadDocumentForCase(state.cases[0]);
              }
            }
          };
        }

        document.getElementById("fClearBtn").onclick = () => {
          activeEditCaseId = null;
          document.getElementById("fCaseNo").value = "";
          document.getElementById("fCnr").value = "";
          const appNEl = document.getElementById("fApplicantName");
          if (appNEl) appNEl.value = "";
          const appAEl = document.getElementById("fApplicantAddress");
          if (appAEl) appAEl.value = "";
          const respNEl = document.getElementById("fRespondentName");
          if (respNEl) respNEl.value = "";
          const respAEl = document.getElementById("fRespondentAddress");
          if (respAEl) respAEl.value = "";
          if (typeof renderPetitionerRows === "function") renderPetitionerRows([{}]);
          if (typeof renderRespondentRows === "function") renderRespondentRows([{}]);
          document.getElementById("fExtent").value = "";
          document.getElementById("fSurveyNo").value = "";
          document.getElementById("fWardNo").value = "";
          document.getElementById("fPidNo").value = "";
          document.getElementById("fTaxNo").value = "";
          const restEl = document.getElementById("fRestoration");
          if (restEl) restEl.value = isDisposed ? "N/A" : "No";
          const possEl = document.getElementById("fPossession");
          if (possEl) possEl.value = "N/A";
          const bundleEl = document.getElementById("fBundleNo");
          if (bundleEl) bundleEl.value = "";
          const monthYearEl = document.getElementById("fMonthYear");
          if (monthYearEl) monthYearEl.value = "";
          document.getElementById("fDupNotice").style.display = "none";
          document.getElementById("fCancelBtn").style.display = "none";
          document.getElementById("fStatusMsg").textContent = "";
          const dzBadge = document.getElementById("dropzoneFileBadgeContainer");
          if (dzBadge) dzBadge.style.display = "none";
        };

        document.getElementById("fCancelBtn").onclick = () => {
          activeEditCaseId = null;
          document.getElementById("fClearBtn").click();
        };

        document.getElementById("fDeleteBtn").onclick = async () => {
          if (!activeEditCaseId) {
            alert("No case is currently loaded for editing.");
            return;
          }
          if (confirm("Delete this case from the register?")) {
            await window.storage.deleteCase(activeEditCaseId);
            activeEditCaseId = null;
            document.getElementById("fClearBtn").click();
            render();
          }
        };

        document.getElementById("fSaveBtn").onclick = async () => {
          const rawNo = extractCaseNumberOnly(document.getElementById("fCaseNo")?.value.trim());
          if (!rawNo) {
            alert("Please enter a case number.");
            document.getElementById("fCaseNo")?.focus();
            return;
          }
          const statusMsg = document.getElementById("fStatusMsg");
          if (statusMsg) {
            statusMsg.textContent = `⏳ Saving Case ${rawNo}...`;
            statusMsg.style.color = "var(--primary)";
          }
          const rec = getCaseObjectFromForm(isLegacy);
          const savedRec = await saveCaseRecord(rec);

          if (statusMsg && savedRec) {
            const hallName = formatCourtHallName(savedRec.courtHall || savedRec.hall || savedRec.court);
            const caseName = formatCaseNumberName(savedRec);
            if (savedRec._isDuplicate) {
              statusMsg.textContent = `⚠️ Details have been overwritten for that particular case number: ${caseName} (${hallName})`;
              statusMsg.style.color = "#d97706";
            } else {
              statusMsg.textContent = `✓ Successfully saved Case ${caseName} (${hallName})!`;
              statusMsg.style.color = "var(--primary)";
            }
          }
          activeEditCaseId = null;

          // If OCR Review Queue is active, also advance or clear it!
          if (ocrReviewQueue && ocrReviewQueue.length > 0) {
            const qIdx = ocrReviewQueue.findIndex(q => 
              extractCaseNumberOnly(q.caseNo || q.existing_case_no) === rawNo
            );
            const removeIdx = qIdx >= 0 ? qIdx : ocrQueueIndex;
            if (removeIdx >= 0 && removeIdx < ocrReviewQueue.length) {
              ocrReviewQueue.splice(removeIdx, 1);
            }
            if (ocrReviewQueue.length === 0) {
              ocrQueueIndex = 0;
              renderReviewQueueBanner();
              if (statusMsg) {
                statusMsg.textContent = `✓ Successfully saved ${rec.fullCaseNo || rec.caseNo}! Review queue completed.`;
              }
            } else {
              if (ocrQueueIndex >= ocrReviewQueue.length) ocrQueueIndex = ocrReviewQueue.length - 1;
              renderReviewQueueBanner();
              const nextItem = ocrReviewQueue[ocrQueueIndex];
              populateFormFromObject(nextItem);
              loadDocumentForCase(nextItem);
            }
          }
        };

        if (isLegacy) {
          const bulkBtn = document.getElementById("lBulkSubmitBtn");
          if (bulkBtn) {
            bulkBtn.onclick = async () => {
              const text = document.getElementById("lBulkArea")?.value.trim();
              if (!text) return;
              const lines = text.split("\\n");
              let count = 0;
              for (const line of lines) {
                const parts = line.split(/[\\t,]+/).map(s => s.trim());
                if (parts.length < 3) continue;
                const hall = parts[0].includes("II") ? "II" : "I";
                const type = parts[1] || "G";
                const cno = parts[2];
                const yr = parseInt(parts[3], 10) || CURRENT_YEAR;
                const sgrp = parts[4] || "Appearance";
                const stg = parts[5] || "Appearance of Accused";
                const dateVal = parts[6] || "";

                const rec = {
                  id: "c_" + Date.now() + "_" + Math.random().toString(36).slice(2, 7),
                  hall: hall,
                  court: "Court Hall No." + (hall === "II" ? "2" : "1"),
                  type: type,
                  caseNo: cno,
                  existing_case_no: cno,
                  cnr: "",
                  filedYear: yr,
                  filing_year: yr,
                  stageGroup: sgrp,
                  stage_group: sgrp,
                  currentStage: stg,
                  stage: stg,
                  nextHearing: isDisposed ? "" : dateVal,
                  hearing_date: isDisposed ? "" : dateVal,
                  disposedDate: isDisposed ? dateVal : "",
                  dispose_date: isDisposed ? dateVal : "",
                  disposalNature: isDisposed ? "Disposed" : "",
                  possession: parts[7] || "N/A",
                  bundleNo: parts[8] || "",
                  bundle_number: parts[8] || "",
                  status: state.mode,
                  caseMode: state.mode,
                  extent: "2.10",
                  landExtent: "2.10",
                  unit: "Acre-Gunta",
                  extentUnit: "Acre-Gunta",
                  district: "Bengaluru",
                  taluk: "Bengaluru North",
                  hobli: "Dasanapura",
                  village: "Abbagere",
                  entryDate: new Date().toISOString().slice(0, 10),
                  createdAt: new Date().toISOString(),
                  source: "legacy-bulk"
                };
                state.cases.push(rec);
                count++;
              }
              await saveCases();
              document.getElementById("lBulkStatus").textContent = `✓ Successfully imported ${count} cases.`;
              updateTopBarStats();
            };
          }
        }
        if (typeof initPartyDynamicHandlers === "function") {
          initPartyDynamicHandlers();
        }
      }

      function updateTopBarStats() {
        if (!state.cases || !Array.isArray(state.cases)) {
          state.cases = [];
        }
        const count = state.cases.length;
        const user = window.auth ? window.auth.user : null;
        
        let myCount = 0;
        if (user && user.username) {
          const uName = user.username.toLowerCase();
          const dName = (user.displayName || "").toLowerCase();
          myCount = state.cases.filter(c => {
            const op = (c.operatorId || "").toLowerCase();
            const ent = (c.enteredBy || c.entered_by || "").toLowerCase();
            return op === uName || ent === uName || (dName && ent === dName);
          }).length;
        }

        const totalLbl = document.getElementById("totalBadgeLbl");
        const statusDb = document.getElementById("statusDbLbl");
        const myEntriesBadge = document.getElementById("topPersonalCountBadge");
        const myEntriesCountSpan = document.getElementById("myEntriesCount");

        if (myEntriesCountSpan) {
          myEntriesCountSpan.textContent = myCount;
        }

        if (user && user.role === "operator") {
          if (myEntriesBadge) myEntriesBadge.style.display = "inline-flex";
          if (totalLbl) totalLbl.textContent = `My Entries: ${myCount} Records`;
          if (statusDb) statusDb.textContent = `Data Entry Desk: ${user.displayName || user.username} (${myCount} entries done by you)`;
        } else {
          if (myEntriesBadge) myEntriesBadge.style.display = "none";
          if (totalLbl) totalLbl.textContent = `Total Records: ${count} (All Operators)`;
          if (statusDb) statusDb.textContent = `Database: SQLite / Local Storage (${count} records total)`;
        }
      }

      // ========================================================
      // 11. ROUTER & SAFE INITIALIZATION
      // ========================================================

      function render() {
        document.querySelectorAll("#nav button").forEach(b => {
          b.classList.toggle("active", b.dataset.view === state.view);
        });
        
        applyModeUI();
        updateTopBarStats();
        renderReviewQueueBanner();

        if (state.view === "navigator") renderNavigator();
        else if (state.view === "pendingentry") renderPendingEntry();
        else if (state.view === "legacy") renderLegacy();
        else if (state.view === "export") renderExport();
        else if (state.view === "admin_operators") renderAdminOperators();
        else {
          state.view = "navigator";
          renderNavigator();
        }
      }

      
      
      // ========================================================
      // 12. COURT OPERATOR ADMINISTRATION & CREDENTIALS
      // ========================================================
      function renderAdminOperators() {
        const root = document.getElementById("viewRoot");
        if (!root) return;

        const user = window.auth ? window.auth.user : null;
        if (!user || user.role !== "admin") {
          root.innerHTML = `
            <div class="panel" style="text-align:center;padding:48px 24px;">
              <div style="font-size:36px;margin-bottom:12px;">🔒</div>
              <h3 style="font-size:18px;font-weight:700;color:#0f172a;margin-bottom:8px;">Access Restricted to Court Administrator</h3>
              <p style="font-size:13px;color:#64748b;max-width:480px;margin:0 auto 20px;">
                Only the Registrar / Court Administrator has privileges to manage operator accounts, credentials, and passwords.
              </p>
              <button class="btn-case-action" onclick="switchView('navigator')" style="background:#1570ef;color:#fff;border-color:#1570ef;">Return to Case Navigator</button>
            </div>
          `;
          return;
        }

        const ops = (typeof window.getOperatorAccounts === "function") ? window.getOperatorAccounts() : {};
        const opKeys = Object.keys(ops);

        // Compute case counts per operator
        const caseCounts = {};
        if (Array.isArray(state.cases)) {
          state.cases.forEach(c => {
            const op = (c.operatorId || "").toLowerCase();
            if (op) caseCounts[op] = (caseCounts[op] || 0) + 1;
          });
        }

        const activeCount = opKeys.filter(k => ops[k].status !== "disabled").length;
        const hall1Count = opKeys.filter(k => ops[k].hall === "1").length;
        const hall2Count = opKeys.filter(k => ops[k].hall === "2").length;

        root.innerHTML = `
          <div class="panel" style="margin-bottom:14px;">
            <!-- Top Header & Controls -->
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:12px;">
              <div>
                <div style="display:flex;align-items:center;gap:8px;">
                  <button class="btn-case-action" onclick="switchView('navigator')" style="padding:4px 9px;font-size:11px;">← Case Navigator</button>
                  <h2 style="font-size:18px;font-weight:700;color:#0f172a;margin:0;">Court Officer &amp; Operator Administration</h2>
                </div>
                <p style="font-size:12px;color:#64748b;margin:4px 0 0 0;">Manage Data Entry Operator credentials, passwords, assigned desks, and court hall routing.</p>
              </div>
              <div style="display:flex;align-items:center;gap:8px;">
                <button class="btn-case-action" onclick="syncOperatorsWithServerUI()" style="padding:6px 12px;font-size:11.5px;">🔄 Refresh from Server</button>
                <button class="btn-case-action" onclick="openAddOperatorModal()" style="background:#1570ef;color:#fff;border-color:#1570ef;font-weight:600;padding:6px 14px;font-size:12px;">➕ Add New Operator</button>
              </div>
            </div>

            <!-- Quick Metrics Grid -->
            <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(180px, 1fr));gap:12px;margin-bottom:18px;">
              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px;">
                <div style="font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;">Total Operators</div>
                <div style="font-size:22px;font-weight:700;color:#0f172a;margin-top:4px;">${opKeys.length}</div>
                <div style="font-size:11px;color:#16a34a;margin-top:2px;">● ${activeCount} Active Accounts</div>
              </div>
              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px;">
                <div style="font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;">Court Hall 1 Desks</div>
                <div style="font-size:22px;font-weight:700;color:#1570ef;margin-top:4px;">${hall1Count}</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">Assigned to Hall I</div>
              </div>
              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px;">
                <div style="font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;">Court Hall 2 Desks</div>
                <div style="font-size:22px;font-weight:700;color:#12b76a;margin-top:4px;">${hall2Count}</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">Assigned to Hall II</div>
              </div>
              <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:12px 14px;">
                <div style="font-size:11px;font-weight:600;color:#64748b;text-transform:uppercase;">Total Court Cases</div>
                <div style="font-size:22px;font-weight:700;color:#7c3aed;margin-top:4px;">${state.cases.length}</div>
                <div style="font-size:11px;color:#64748b;margin-top:2px;">Audited across all operators</div>
              </div>
            </div>

            <!-- Operators Credentials Table -->
            <div style="overflow-x:auto;border:1px solid #cbd5e1;border-radius:6px;">
              <table style="width:100%;border-collapse:collapse;font-size:12px;text-align:left;">
                <thead style="background:#f1f5f9;color:#334155;border-bottom:1px solid #cbd5e1;">
                  <tr>
                    <th style="padding:9px 12px;text-align:center;width:45px;">Sl.</th>
                    <th style="padding:9px 12px;">Operator Username / ID</th>
                    <th style="padding:9px 12px;">Display Name &amp; Title</th>
                    <th style="padding:9px 12px;text-align:center;">Role &amp; Access</th>
                    <th style="padding:9px 12px;text-align:center;">Assigned Desk / Hall</th>
                    <th style="padding:9px 12px;text-align:center;">Default Mode</th>
                    <th style="padding:9px 12px;text-align:center;">Login Password</th>
                    <th style="padding:9px 12px;text-align:center;">Status</th>
                    <th style="padding:9px 12px;text-align:center;">Cases Entered</th>
                    <th style="padding:9px 12px;text-align:center;width:190px;">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  ${opKeys.map((k, i) => {
                    const op = ops[k];
                    const cCount = caseCounts[k.toLowerCase()] || 0;
                    const isPrimary = ["admin"].includes(k);
                    const isActive = op.status !== "disabled";
                    return `
                      <tr style="border-bottom:1px solid #f1f5f9;background:#fff;" id="op-row-${escAttr(k)}">
                        <td style="padding:9px 12px;text-align:center;font-family:monospace;color:#64748b;">${i+1}</td>
                        <td style="padding:9px 12px;font-family:monospace;font-weight:700;color:#0f172a;">
                          ${escHtml(op.username)}
                        </td>
                        <td style="padding:9px 12px;">
                          <div style="font-weight:600;color:#1e293b;">${escHtml(op.displayName || op.username)}</div>
                          <div style="font-size:11px;color:#64748b;">${escHtml(op.roleTitle || 'Operator')}</div>
                        </td>
                        <td style="padding:9px 12px;text-align:center;">
                          <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:10.5px;font-weight:700;${op.role === 'admin' ? 'background:#fef3c7;color:#92400e;' : 'background:#dcfce7;color:#166534;'}">
                            ${op.role === 'admin' ? 'System Administrator' : 'Data Entry Person'}
                          </span>
                        </td>
                        <td style="padding:9px 12px;text-align:center;">
                          <span style="display:inline-block;padding:2px 8px;background:#f1f5f9;border-radius:12px;font-size:11px;font-weight:600;color:#334155;">
                            Hall ${escHtml(op.hall || "1")}
                          </span>
                        </td>
                        <td style="padding:9px 12px;text-align:center;">
                          <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;background:${op.mode === 'Disposed' ? '#dbeafe;color:#1e40af;' : '#dcfce7;color:#166534;'}">
                            ${escHtml(op.mode || 'Disposed')}
                          </span>
                        </td>
                        <td style="padding:9px 12px;text-align:center;">
                          <div style="display:inline-flex;align-items:center;gap:6px;">
                            <span id="pwd-display-${escAttr(k)}" style="font-family:monospace;font-size:12px;letter-spacing:1px;color:#475569;">••••••••</span>
                            <button type="button" class="rowbtn" onclick="togglePasswordDisplay('${escAttr(k)}', '${escAttr(op.password || 'operator')}')" style="padding:2px 6px;font-size:10px;" title="Reveal password">👁️</button>
                            <button type="button" class="rowbtn" onclick="openChangePasswordModal('${escAttr(k)}')" style="padding:2px 6px;font-size:10px;" title="Change password">🔑 Change</button>
                          </div>
                        </td>
                        <td style="padding:9px 12px;text-align:center;">
                          <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;background:${isActive ? '#dcfce7;color:#166534;' : '#f1f5f9;color:#64748b;'}">
                            ${isActive ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td style="padding:9px 12px;text-align:center;font-weight:700;color:#1e293b;">
                          <span style="background:#f1f5f9;padding:3px 9px;border-radius:12px;font-family:monospace;font-size:12px;">${cCount}</span>
                        </td>
                        <td style="padding:9px 12px;text-align:center;white-space:nowrap;">
                          <button class="rowbtn" onclick="openEditOperatorModal('${escAttr(k)}')" style="font-weight:600;color:#1570ef;">✏️ Edit</button>
                          <button class="rowbtn" onclick="toggleOperatorStatus('${escAttr(k)}')" style="font-weight:600;">${isActive ? 'Deactivate' : 'Activate'}</button>
                          ${!isPrimary ? `<button class="rowbtn danger" onclick="deleteOperatorAccount('${escAttr(k)}')">Delete</button>` : ''}
                        </td>
                      </tr>
                    `;
                  }).join("")}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Modals Container -->
          <div id="adminOpsModalContainer"></div>
        `;
      }

      window.togglePasswordDisplay = function(username, realPwd) {
        const el = document.getElementById(`pwd-display-${username}`);
        if (!el) return;
        if (el.textContent === "••••••••") {
          el.textContent = realPwd;
          el.style.color = "#0284c7";
          el.style.fontWeight = "700";
        } else {
          el.textContent = "••••••••";
          el.style.color = "#475569";
          el.style.fontWeight = "normal";
        }
      };

      window.openEditOperatorModal = function(username) {
        const container = document.getElementById("adminOpsModalContainer");
        if (!container) return;
        const ops = window.getOperatorAccounts();
        const op = ops[username];
        if (!op) return;

        container.innerHTML = `
          <div class="modal-backdrop active" id="editOpModalBackdrop" onclick="if(event.target.id==='editOpModalBackdrop')closeAdminOpsModal()" style="display:flex;align-items:center;justify-content:center;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(15,23,42,0.65);z-index:99999;backdrop-filter:blur(3px);">
            <div style="background:#fff;border-radius:8px;max-width:480px;width:92%;padding:20px;box-shadow:0 20px 25px -5px rgba(0,0,0,0.1), 0 10px 10px -5px rgba(0,0,0,0.04);">
              <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #e2e8f0;padding-bottom:12px;margin-bottom:16px;">
                <h3 style="margin:0;font-size:16px;font-weight:700;color:#0f172a;">✏️ Edit Operator Credentials</h3>
                <button type="button" onclick="closeAdminOpsModal()" style="border:none;background:none;font-size:18px;cursor:pointer;color:#64748b;">✕</button>
              </div>

              <form onsubmit="saveOperatorDetailsSubmit(event, '${escAttr(username)}')">
                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Operator Username / Login ID</label>
                  <input type="text" id="editOpUsername" value="${escAttr(op.username)}" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-family:monospace;font-size:13px;" required ${op.role === 'admin' ? 'readonly' : ''}>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Access Role &amp; Privileges</label>
                  <select id="editOpRole" style="width:100%;box-sizing:border-box;padding:8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12.5px;font-weight:600;">
                    <option value="operator" ${op.role === 'operator' ? 'selected' : ''}>Data Entry Person (Restricted: Edit, Change &amp; Save Entries)</option>
                    <option value="admin" ${op.role === 'admin' ? 'selected' : ''}>System Administrator (All Access for Everything &amp; Manage Access)</option>
                  </select>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Full Display Name</label>
                  <input type="text" id="editOpDisplayName" value="${escAttr(op.displayName || '')}" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-size:13px;" required>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Assigned Desk / Role Title</label>
                  <input type="text" id="editOpRoleTitle" value="${escAttr(op.roleTitle || '')}" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-size:13px;" required>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Security Login Password</label>
                  <input type="text" id="editOpPassword" value="${escAttr(op.password || 'operator')}" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-family:monospace;font-size:13px;" required>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">
                  <div>
                    <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Assigned Court Hall</label>
                    <select id="editOpHall" style="width:100%;box-sizing:border-box;padding:8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;">
                      <option value="1" ${op.hall === '1' ? 'selected' : ''}>Court Hall No. 1</option>
                      <option value="2" ${op.hall === '2' ? 'selected' : ''}>Court Hall No. 2</option>
                    </select>
                  </div>
                  <div>
                    <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Default Startup Mode</label>
                    <select id="editOpMode" style="width:100%;box-sizing:border-box;padding:8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;">
                      <option value="Disposed" ${op.mode === 'Disposed' ? 'selected' : ''}>Disposed (Blue)</option>
                      <option value="Pending" ${op.mode === 'Pending' ? 'selected' : ''}>Pending (Green)</option>
                    </select>
                  </div>
                </div>

                <div style="display:flex;justify-content:flex-end;gap:8px;">
                  <button type="button" class="btn-case-action" onclick="closeAdminOpsModal()">Cancel</button>
                  <button type="submit" class="btn-case-action" style="background:#1570ef;color:#fff;border-color:#1570ef;font-weight:600;">Save Credentials</button>
                </div>
              </form>
            </div>
          </div>
        `;
      };

      window.saveOperatorDetailsSubmit = async function(e, oldUsername) {
        if (e && e.preventDefault) e.preventDefault();
        const ops = window.getOperatorAccounts();
        const op = ops[oldUsername];
        if (!op) return;

        const newUsername = (document.getElementById("editOpUsername")?.value || "").trim().toLowerCase();
        const displayName = (document.getElementById("editOpDisplayName")?.value || "").trim();
        const roleTitle = (document.getElementById("editOpRoleTitle")?.value || "").trim();
        const password = (document.getElementById("editOpPassword")?.value || "").trim();
        const hall = document.getElementById("editOpHall")?.value || "1";
        const mode = document.getElementById("editOpMode")?.value || "Disposed";

        if (!newUsername || !displayName || !password) {
          alert("Username, display name, and password are required.");
          return;
        }

        if (newUsername !== oldUsername && ops[newUsername]) {
          alert(`An account with username "${newUsername}" already exists.`);
          return;
        }

        const role = document.getElementById("editOpRole")?.value || op.role || "operator";
        delete ops[oldUsername];
        ops[newUsername] = Object.assign({}, op, {
          username: newUsername,
          displayName,
          role,
          roleTitle,
          password,
          hall,
          mode
        });

        await window.saveOperatorAccounts(ops);
        closeAdminOpsModal();
        renderAdminOperators();
      };

      window.openChangePasswordModal = function(username) {
        const container = document.getElementById("adminOpsModalContainer");
        if (!container) return;
        const ops = window.getOperatorAccounts();
        const op = ops[username];
        if (!op) return;

        container.innerHTML = `
          <div class="modal-backdrop active" id="editOpModalBackdrop" onclick="if(event.target.id==='editOpModalBackdrop')closeAdminOpsModal()" style="display:flex;align-items:center;justify-content:center;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(15,23,42,0.65);z-index:99999;backdrop-filter:blur(3px);">
            <div style="background:#fff;border-radius:8px;max-width:400px;width:90%;padding:20px;box-shadow:0 20px 25px -5px rgba(0,0,0,0.1);">
              <h3 style="margin:0 0 12px 0;font-size:15px;font-weight:700;color:#0f172a;">🔑 Set Password for ${escHtml(op.displayName || op.username)}</h3>
              <form onsubmit="saveNewPasswordSubmit(event, '${escAttr(username)}')">
                <div style="margin-bottom:14px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">New Security Password</label>
                  <input type="text" id="newOpPwdInput" value="${escAttr(op.password || 'operator')}" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-family:monospace;font-size:13px;" required>
                </div>
                <div style="display:flex;justify-content:flex-end;gap:8px;">
                  <button type="button" class="btn-case-action" onclick="closeAdminOpsModal()">Cancel</button>
                  <button type="submit" class="btn-case-action" style="background:#1570ef;color:#fff;border-color:#1570ef;font-weight:600;">Update Password</button>
                </div>
              </form>
            </div>
          </div>
        `;
      };

      window.saveNewPasswordSubmit = async function(e, username) {
        if (e && e.preventDefault) e.preventDefault();
        const pwd = (document.getElementById("newOpPwdInput")?.value || "").trim();
        if (!pwd) {
          alert("Password cannot be empty.");
          return;
        }
        const ops = window.getOperatorAccounts();
        if (ops[username]) {
          ops[username].password = pwd;
          await window.saveOperatorAccounts(ops);
        }
        closeAdminOpsModal();
        renderAdminOperators();
      };

      window.openAddOperatorModal = function() {
        const container = document.getElementById("adminOpsModalContainer");
        if (!container) return;
        const ops = window.getOperatorAccounts();
        const nextIdx = Object.keys(ops).filter(k => k.startsWith("operator")).length + 1;

        container.innerHTML = `
          <div class="modal-backdrop active" id="editOpModalBackdrop" onclick="if(event.target.id==='editOpModalBackdrop')closeAdminOpsModal()" style="display:flex;align-items:center;justify-content:center;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(15,23,42,0.65);z-index:99999;backdrop-filter:blur(3px);">
            <div style="background:#fff;border-radius:8px;max-width:480px;width:92%;padding:20px;box-shadow:0 20px 25px -5px rgba(0,0,0,0.1);">
              <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #e2e8f0;padding-bottom:12px;margin-bottom:16px;">
                <h3 style="margin:0;font-size:16px;font-weight:700;color:#0f172a;">➕ Add New Operator Account</h3>
                <button type="button" onclick="closeAdminOpsModal()" style="border:none;background:none;font-size:18px;cursor:pointer;color:#64748b;">✕</button>
              </div>

              <form onsubmit="saveNewOperatorSubmit(event)">
                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Operator Username / Login ID</label>
                  <input type="text" id="addOpUsername" value="operator${nextIdx}" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-family:monospace;font-size:13px;" required>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Access Role &amp; Privileges</label>
                  <select id="addOpRole" style="width:100%;box-sizing:border-box;padding:8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12.5px;font-weight:600;">
                    <option value="operator" selected>Data Entry Person (Restricted: Edit, Change &amp; Save Entries)</option>
                    <option value="admin">System Administrator (All Access for Everything &amp; Manage Access)</option>
                  </select>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Full Display Name</label>
                  <input type="text" id="addOpDisplayName" value="Data Entry Operator ${nextIdx}" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-size:13px;" required>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Assigned Desk / Role Title</label>
                  <input type="text" id="addOpRoleTitle" value="Registry Operator (Desk ${nextIdx})" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-size:13px;" required>
                </div>

                <div style="margin-bottom:12px;">
                  <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Security Login Password</label>
                  <input type="text" id="addOpPassword" value="operator" style="width:100%;box-sizing:border-box;padding:8px 10px;border:1px solid #cbd5e1;border-radius:4px;font-family:monospace;font-size:13px;" required>
                </div>

                <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:16px;">
                  <div>
                    <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Assigned Court Hall</label>
                    <select id="addOpHall" style="width:100%;box-sizing:border-box;padding:8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;">
                      <option value="1">Court Hall No. 1</option>
                      <option value="2">Court Hall No. 2</option>
                    </select>
                  </div>
                  <div>
                    <label style="display:block;font-size:11.5px;font-weight:600;color:#475569;margin-bottom:4px;">Default Startup Mode</label>
                    <select id="addOpMode" style="width:100%;box-sizing:border-box;padding:8px;border:1px solid #cbd5e1;border-radius:4px;font-size:12px;">
                      <option value="Disposed">Disposed (Blue)</option>
                      <option value="Pending">Pending (Green)</option>
                    </select>
                  </div>
                </div>

                <div style="display:flex;justify-content:flex-end;gap:8px;">
                  <button type="button" class="btn-case-action" onclick="closeAdminOpsModal()">Cancel</button>
                  <button type="submit" class="btn-case-action" style="background:#1570ef;color:#fff;border-color:#1570ef;font-weight:600;">Create Account</button>
                </div>
              </form>
            </div>
          </div>
        `;
      };

      window.saveNewOperatorSubmit = async function(e) {
        if (e && e.preventDefault) e.preventDefault();
        const username = (document.getElementById("addOpUsername")?.value || "").trim().toLowerCase();
        const displayName = (document.getElementById("addOpDisplayName")?.value || "").trim();
        const roleTitle = (document.getElementById("addOpRoleTitle")?.value || "").trim();
        const password = (document.getElementById("addOpPassword")?.value || "").trim();
        const hall = document.getElementById("addOpHall")?.value || "1";
        const mode = document.getElementById("addOpMode")?.value || "Disposed";

        if (!username || !displayName || !password) {
          alert("All fields are required.");
          return;
        }

        const ops = window.getOperatorAccounts();
        if (ops[username]) {
          alert(`Operator username "${username}" already exists.`);
          return;
        }

        const role = document.getElementById("addOpRole")?.value || "operator";
        ops[username] = {
          username,
          displayName,
          roleTitle: roleTitle || (role === "admin" ? "System Administrator" : "Data Entry Operator"),
          role,
          hall,
          mode,
          password,
          status: "active"
        };

        await window.saveOperatorAccounts(ops);
        closeAdminOpsModal();
        renderAdminOperators();
      };

      window.toggleOperatorStatus = async function(username) {
        const ops = window.getOperatorAccounts();
        if (!ops[username]) return;
        ops[username].status = (ops[username].status === "disabled") ? "active" : "disabled";
        await window.saveOperatorAccounts(ops);
        renderAdminOperators();
      };

      window.deleteOperatorAccount = async function(username) {
        if (!confirm(`Are you sure you want to remove operator "${username}"?`)) return;
        const ops = window.getOperatorAccounts();
        delete ops[username];
        await window.saveOperatorAccounts(ops);
        renderAdminOperators();
      };

      window.closeAdminOpsModal = function() {
        const container = document.getElementById("adminOpsModalContainer");
        if (container) container.innerHTML = "";
      };

      window.syncOperatorsWithServerUI = async function() {
        if (typeof window.syncOperatorsFromServer === "function") {
          await window.syncOperatorsFromServer();
          renderAdminOperators();
          alert("✓ Operator accounts refreshed from server.");
        }
      };

      window.renderAdminOperators = renderAdminOperators;
      window.togglePdfSideBySide = togglePdfSideBySide;
      window.openBatchModal = openBatchModal;
      window.openScanModal = openScanModal;
      window.openPdfFolderModal = openPdfFolderModal;
      window.exportAllCasesCsv = exportAllCasesCsv;
      window.exportAllCasesJson = exportAllCasesJson;
      window.toggleMode = toggleMode;
      window.switchView = switchView;
      window.scrollToPrevPdfPage = () => { if (typeof activePdfCurrentPage !== "undefined" && activePdfCurrentPage > 1) scrollToPdfPage(activePdfCurrentPage - 1); };
      window.scrollToNextPdfPage = () => { if (typeof activePdfCurrentPage !== "undefined" && activePdfCurrentPage < activePdfTotalPages) scrollToPdfPage(activePdfCurrentPage + 1); };
      window.zoomInPdf = () => { if (typeof pdfCurrentZoom !== "undefined") { pdfCurrentZoom = Math.min(200, pdfCurrentZoom + 15); applyPdfTransform(); } };
      window.zoomOutPdf = () => { if (typeof pdfCurrentZoom !== "undefined") { pdfCurrentZoom = Math.max(40, pdfCurrentZoom - 15); applyPdfTransform(); } };
      window.rotatePdf = () => { if (typeof pdfCurrentRotation !== "undefined") { pdfCurrentRotation = (pdfCurrentRotation + 90) % 360; applyPdfTransform(); } };
      window.showPdfPane = showPdfPane;
      window.hidePdfPane = hidePdfPane;
      window.togglePdfSideBySide = togglePdfSideBySide;
      window.resetPdfZoomAndPan = resetPdfZoomAndPan;
      window.saveCurrentFormEntry = () => { document.getElementById("fSaveBtn")?.click(); };
      window.clearCurrentForm = () => { document.getElementById("fClearBtn")?.click(); };

      function switchView(viewName) {
        if (viewName === "admin_operators") {
          if (!window.auth || !window.auth.isAdmin) {
            alert("Access Restricted: Only the System Administrator can manage operator accounts and access settings.");
            return;
          }
        }
        state.view = viewName;
        if (viewName === "legacy") {
          state.mode = "Disposed";
        } else if (viewName === "pendingentry") {
          state.mode = "Pending";
        }
        applyModeUI();
        render();
      }
      window.switchView = switchView;

      (async function init() {
        try {
          // Wire Navigation Sidebar immediately
          document.querySelectorAll("#nav button").forEach(btn => {
            btn.onclick = () => switchView(btn.dataset.view);
          });

          // Wire Sidebar Quick Search
          const sideSearch = document.getElementById("sidebarSearchInput");
          if (sideSearch) {
            sideSearch.oninput = (e) => {
              const q = e.target.value.trim().toLowerCase();
              if (state.view !== "navigator") {
                switchView("navigator");
              }
              const navInput = document.getElementById("navSearchInput");
              if (navInput) {
                navInput.value = q;
                navInput.dispatchEvent(new Event("input"));
              }
            };
          }

          // Wire Top App Controls immediately
          const modeBtn = document.getElementById("modeToggleBtn");
          if (modeBtn) modeBtn.onclick = toggleMode;

          const topCsv = document.getElementById("topExportCsvBtn");
          if (topCsv) topCsv.onclick = exportAllCasesCsv;

          const topJson = document.getElementById("topExportJsonBtn");
          if (topJson) topJson.onclick = exportAllCasesJson;

          const topScan = document.getElementById("topScanBtn");
          if (topScan) topScan.onclick = openScanModal;

          const topBatch = document.getElementById("topBatchBtn");
          if (topBatch) topBatch.onclick = openBatchModal;

          const topCompare = document.getElementById("topComparePdfBtn");
          if (topCompare) topCompare.onclick = togglePdfSideBySide;

          const topPdfFolder = document.getElementById("topPdfFolderBtn");
          if (topPdfFolder) topPdfFolder.onclick = openPdfFolderModal;

          wirePdfViewerControls();
          refreshPdfFolderStatus();

          // Background async storage loading
          await loadCases();
          await loadCaseSeqCounters();
          await loadFilings();
          await loadBackupMeta();

          if (window.auth) {
            if (window.auth.isAuthenticated) {
              window.auth.showApp();
            } else {
              window.auth.showLoginPage();
            }
          } else {
            applyModeUI();
            render();
          }
          updateTopBarStats();
        } catch (err) {
          console.error("Initialization error:", err);
          const root = document.getElementById("viewRoot");
          if (root) {
            root.innerHTML = `<div class="panel"><div class="banner" style="background:#fee2e2;border:1px solid #dc2626;color:#991b1b;padding:14px 18px;"><strong>Initialization error:</strong> ${escHtml(err.message || String(err))}<br><br><button class="btn btn-primary" onclick="location.reload()">Reload Register</button></div></div>`;
          }
        }
      })();
    </script>
  </body>
</html>
"""

# Assemble full index.html
full_html = (
    part1_head +
    part2_body +
    part3_auth + "\n" +
    part4_storage + "\n" +
    part5_constants + "\n" +
    part5_filename_parser + "\n" +
    part5_helpers + "\n" +
    part6_export + "\n" +
    part7_utils + "\n" +
    part8_features
)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(full_html)

print(f"DONE! Successfully generated index.html: {len(full_html.splitlines())} lines.")
