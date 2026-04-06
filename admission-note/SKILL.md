---
name: admission-note
description: "Use this skill to generate a patient hospital admission note as a Word (.docx) file. Trigger whenever the user mentions 'admission note', '住院病歷', '入院紀錄', or asks to create a medical document for a hospitalized patient. Also trigger when the user provides patient data from a screenshot, image, Word file, Excel file, CSV, or typed text and wants a formatted clinical document or hospital note. Use this skill even if the user says 'help me write' or 'generate for me' in a medical or clinical context. Do NOT use for outpatient notes, discharge summaries, or non-medical documents."
---

# Admission Note Generator

Generate a hospital Admission Note as a `.docx` Word file from patient data provided as screenshots, Word files, Excel/CSV files, or plain text.

---

## Step 1 — Read the Input

- **Screenshot/image**: Read directly — Claude can see it. Extract all visible patient data.
- **Word (.docx)**: Run `pandoc "<file>" -o /tmp/patient.md` then read the markdown.
- **Excel (.xlsx)**: Use openpyxl to iterate rows and extract field-value pairs.
- **CSV**: Use the Read tool or Python `csv` module.
- **Text**: Extract directly from the conversation.

---

## Step 2 — Organize Patient Information

Map extracted content to these variables. Write `"Not documented"` for any missing field.

| Variable | Description |
|----------|-------------|
| `patient_name` | Full name |
| `mrn` | Medical Record Number |
| `dob`, `age`, `gender` | Demographics |
| `admission_date` | Today if not specified |
| `physician` | Attending physician |
| `admitting_dx` | Primary admitting diagnosis |
| `room_ward` | Room/ward number |
| `cc` | Chief Complaint |
| `hpi` | History of Present Illness (narrative) |
| `pmh_list` | List of chronic conditions |
| `psh_list` | List of prior surgeries |
| `medications` | List of current medications with doses |
| `allergies` | Drug/food allergies and reaction types |
| `family_history` | Relevant family history |
| `social_history` | Smoking, alcohol, occupation, living |
| `ros` | Review of Systems |
| `temp`, `hr`, `bp`, `rr`, `spo2`, `weight`, `height` | Vital signs |
| `pe_findings` | Dict: system → finding |
| `lab_results` | List of lab values |
| `imaging` | Imaging/diagnostic findings |
| `assessment_plan` | List of tuples: (problem, [plan steps]) |
| `output_path` | Full path for the output .docx file |

---

## Step 3 — Generate the Word Document

Use **Python with python-docx**:
- Try: `python` or `python3`
- Anaconda: `C:\Users\<username>\anaconda3\python.exe`
- Install if missing: `pip install python-docx`

Name the output: `<PatientLastName>_AdmissionNote_<YYYYMMDD>.docx`

Write and run this script (fill in ALL variables from Step 2 first):

```python
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import os

# === FILL IN ALL VARIABLES FROM STEP 2 ===
patient_name = "..."
mrn = "..."
dob = "..."
age = "..."
gender = "..."
admission_date = "..."
physician = "..."
admitting_dx = "..."
room_ward = "N/A"
cc = "..."
hpi = "..."
pmh_list = ["..."]
psh_list = ["..."]
medications = ["..."]
allergies = "..."
family_history = "..."
social_history = "..."
ros = "Not documented"
temp = "..."
hr = "..."
bp = "..."
rr = "..."
spo2 = "..."
weight = "..."
height = "..."
pe_findings = {"General": "...", "Cardiovascular": "...", "Pulmonary": "..."}
lab_results = ["..."]
imaging = "..."
assessment_plan = [("Problem name", ["Plan step 1", "Plan step 2"])]
output_path = "PatientLastName_AdmissionNote_YYYYMMDD.docx"
# ==========================================

doc = Document()
s = doc.sections[0]
s.page_width = Cm(21); s.page_height = Cm(29.7)
s.top_margin = s.bottom_margin = Cm(2)
s.left_margin = s.right_margin = Cm(2.5)

def sp(para, hc):
    pPr = para._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hc); pPr.append(shd)

def sc(cell, hc):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hc); tcPr.append(shd)

def hdr(t):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)
    sp(p, "1F4E79")
    r = p.add_run(t)
    r.bold = True; r.font.size = Pt(11); r.font.name = "Arial"
    r.font.color.rgb = RGBColor(255, 255, 255)

def cl(t, i=True):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    if i:
        p.paragraph_format.left_indent = Inches(0.2)
    r = p.add_run(t or "Not documented")
    r.font.size = Pt(10.5); r.font.name = "Arial"

# Title banner
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
sp(p, "1F4E79")
r = p.add_run("HOSPITAL ADMISSION NOTE")
r.bold = True; r.font.size = Pt(16); r.font.name = "Arial"
r.font.color.rgb = RGBColor(255, 255, 255)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
sp(p2, "1F4E79")
r2 = p2.add_run(patient_name)
r2.bold = True; r2.font.size = Pt(13); r2.font.name = "Arial"
r2.font.color.rgb = RGBColor(189, 215, 238)

# Demographics table
tbl = doc.add_table(rows=2, cols=4)
tbl.style = "Table Grid"
rd = [
    [("Patient Name", patient_name), ("MRN", mrn), ("Date of Birth", dob), ("Age / Gender", f"{age} / {gender}")],
    [("Date of Admission", admission_date), ("Attending Physician", physician), ("Admitting Diagnosis", admitting_dx), ("Room / Ward", room_ward)],
]
for ri, row_data in enumerate(rd):
    for ci, (lbl, val) in enumerate(row_data):
        cell = tbl.rows[ri].cells[ci]
        sc(cell, "EBF3FB")
        cell.paragraphs[0].clear()
        lr = cell.paragraphs[0].add_run(lbl + "\n")
        lr.bold = True; lr.font.size = Pt(8); lr.font.name = "Arial"
        lr.font.color.rgb = RGBColor(31, 78, 121)
        vr = cell.paragraphs[0].add_run(val or "N/A")
        vr.font.size = Pt(10); vr.font.name = "Arial"
doc.add_paragraph()

# Clinical sections
hdr("CHIEF COMPLAINT"); cl(cc)
hdr("HISTORY OF PRESENT ILLNESS"); cl(hpi)
hdr("PAST MEDICAL HISTORY")
for x in (pmh_list or ["Not documented"]): cl("  " + x)
hdr("PAST SURGICAL HISTORY")
for x in (psh_list or ["Not documented"]): cl("  " + x)
hdr("MEDICATIONS")
for x in (medications or ["Not documented"]): cl("  " + x)
hdr("ALLERGIES"); cl(allergies)
hdr("FAMILY HISTORY"); cl(family_history)
hdr("SOCIAL HISTORY"); cl(social_history)
hdr("REVIEW OF SYSTEMS"); cl(ros)
hdr("VITAL SIGNS")
cl(f"T: {temp}  |  HR: {hr}  |  BP: {bp}  |  RR: {rr}  |  SpO2: {spo2}  |  Wt: {weight}  |  Ht: {height}")
hdr("PHYSICAL EXAMINATION")
for k, v in pe_findings.items(): cl(f"{k}: {v}")
hdr("LABORATORY AND DIAGNOSTIC RESULTS")
for x in (lab_results or ["Not documented"]): cl("  " + x)
hdr("IMAGING AND DIAGNOSTICS"); cl(imaging)
hdr("ASSESSMENT AND PLAN")
for i, (prob, plan) in enumerate(assessment_plan, 1):
    cl(f"{i}. {prob}")
    for step in (plan if isinstance(plan, list) else [plan]):
        cl("   - " + step)
hdr("PHYSICIAN SIGNATURE")
cl(f"Attending: {physician}  |  Date: {admission_date}")
cl("Signature: ___________________________")

doc.save(output_path)
print(f"Saved: {output_path}")
```

---

## Step 4 — Validate and Deliver

Check the file was created and tell the user its full path.

---

## Important Notes

- **Every section must appear** — write "Not documented" if no data is available.
- **Language**: Content follows input language; section headings always in English.
- **Date format**: YYYY-MM-DD throughout.
- **Assessment & Plan**: Most critical section — numbered problems with specific plan steps.
