"""Generate Companion_Appendix_and_Technical_Inventory.docx from the markdown content.
"""

import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

REPORT_DIR = r"D:\code_placed\ai_interview_coach\report_output"
MD_FILE = os.path.join(REPORT_DIR, "Companion_Appendix_and_Technical_Inventory.md")
DOCX_OUT = os.path.join(REPORT_DIR, "Companion_Appendix_and_Technical_Inventory.docx")

doc = Document()
for s in doc.sections:
    s.top_margin = Inches(1.0)
    s.bottom_margin = Inches(1.0)
    s.left_margin = Inches(1.0)
    s.right_margin = Inches(1.0)

C_NAVY = RGBColor(30, 58, 138)
C_DARK = RGBColor(31, 41, 55)

def style_p(p, space_before=0, space_after=6, line_spacing=1.15):
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing

def add_title(text, level=1):
    h = doc.add_paragraph()
    style_p(h, space_before=14, space_after=6)
    r = h.add_run(text)
    r.font.name = "Times New Roman"
    r.bold = True
    if level == 1:
        r.font.size = Pt(16)
        r.font.color.rgb = C_NAVY
    elif level == 2:
        r.font.size = Pt(13)
        r.font.color.rgb = C_NAVY
    else:
        r.font.size = Pt(11.5)
        r.font.color.rgb = C_DARK
    return h

def add_body(text, bold_prefix=None, italic=False):
    p = doc.add_paragraph()
    style_p(p, space_before=0, space_after=6)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Times New Roman"
        r_pre.bold = True
        r_pre.font.size = Pt(11)
        r_pre.font.color.rgb = C_DARK
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.italic = italic
    r.font.color.rgb = C_DARK
    return p

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    style_p(p, space_before=0, space_after=3)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Times New Roman"
        r_pre.bold = True
        r_pre.font.size = Pt(11)
        r_pre.font.color.rgb = C_DARK
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11)
    r.font.color.rgb = C_DARK
    return p

def set_cell_background(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{color_hex}"/>')
    tcPr.append(shd)

def add_tbl(headers, rows, col_widths=None):
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    hdr_cells = table.rows[0].cells
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        set_cell_background(hdr_cells[i], "1E3A8A")
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_p(p, space_before=4, space_after=4)
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)

    for r_idx, row_data in enumerate(rows):
        row_cells = table.rows[r_idx + 1].cells
        bg_col = "F8FAFC" if r_idx % 2 == 0 else "FFFFFF"
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = str(val)
            set_cell_background(row_cells[c_idx], bg_col)
            p = row_cells[c_idx].paragraphs[0]
            style_p(p, space_before=3, space_after=3)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(9.5)
                r.font.color.rgb = C_DARK

    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

    p_after = doc.add_paragraph()
    style_p(p_after, space_before=0, space_after=8)
    return table

# Build content
add_title("AI INTERVIEW COACH", level=1)
add_title("Companion Appendix & Technical Implementation Inventory", level=2)
add_body("Department of Computer Science and Engineering, K. Ramakrishnan College of Technology (Autonomous)")
add_body("Academic Year: 2026 | Course: CSB1303 – Object Oriented Analysis and Design")

add_title("1. Source Code Inventory", level=2)
add_body("The table below details all major software files, lines of code, and architectural responsibilities.")

inv_headers = ["SUBSYSTEM", "MODULE / FILE", "LOC", "RESPONSIBILITY & INVARIANTS", "STATUS"]
inv_rows = [
    ["Backend Core", "app/main.py", "134", "Application factory, CORS, 503 db degradation handler", "Implemented"],
    ["Backend Core", "app/core/config.py", "118", "Typed Pydantic settings loading, SecretStr API keys", "Implemented"],
    ["Backend Core", "app/core/security.py", "76", "scrypt password hashing (N=16384), session tokens", "Implemented"],
    ["Backend DB", "app/db/base.py & session.py", "64", "Declarative Base with naming conventions, engine", "Implemented"],
    ["Backend Models", "app/models/candidate.py", "52", "Candidate entity, scrypt hash, failed login counter", "Implemented"],
    ["Backend Models", "app/models/auth_session.py", "38", "SHA-256 session token hash, 7-day expiry check", "Implemented"],
    ["Backend Models", "app/models/resume.py", "148", "Resume & CandidateFact entities, provenance check", "Implemented"],
    ["Backend Models", "app/models/interview_session.py", "162", "InterviewSession, plan JSONB, finish_reason check", "Implemented"],
    ["Backend Models", "app/models/interview_question.py", "98", "InterviewQuestion entity, 10k char limit, eval status", "Implemented"],
    ["Backend Models", "app/models/answer_evaluation.py", "112", "AnswerEvaluation & Criteria, 1-5 score bounds", "Implemented"],
    ["Backend Models", "app/models/expression.py", "65", "QuestionExpressionObservation, 9 categorical counts", "Implemented"],
    ["Backend Models", "app/models/provider_call.py", "54", "ProviderCall operational audit; zero candidate IDs", "Implemented"],
    ["Backend Models", "app/models/usage_counter.py", "42", "UsageCounter rate-limiting entity, UTC windows", "Implemented"],
    ["Backend AI", "app/ai/gateway.py", "266", "ModelGateway: routing, 20s timeout, retry, fallback", "Implemented"],
    ["Backend AI", "app/ai/providers.py", "234", "Adapters for Gemini, Groq, NVIDIA over HTTPX", "Implemented"],
    ["Backend AI", "app/ai/profile_agent.py", "145", "ProfileAgent: prompt boundary, verbatim grounding", "Implemented"],
    ["Backend AI", "app/ai/planner_agent.py", "186", "PlannerAgent: closed-set instructions, plan schema", "Implemented"],
    ["Backend AI", "app/ai/interviewer_agent.py", "210", "InterviewerAgent: follow-up wording, anchor rules", "Implemented"],
    ["Backend AI", "app/ai/evaluator_agent.py", "240", "EvaluatorAgent: rubric scoring, quote evidence", "Implemented"],
    ["Backend Services", "app/services/interview_state_machine.py", "257", "Finite State Machine: transition table, row locks", "Implemented"],
    ["Backend Services", "app/services/interviewer.py", "385", "Turn decision engine, 60s deadline guard", "Implemented"],
    ["Backend Services", "app/services/evaluator.py", "340", "Rubric scoring, exact substring quote check", "Implemented"],
    ["Backend Services", "app/services/report.py", "290", "Deterministic report compiler, zero aggregated scores", "Implemented"],
    ["Backend Services", "app/services/resume_extractor.py", "470", "Pure Python pypdf text extraction, verbatim parser", "Implemented"],
    ["Backend Services", "app/services/retry.py", "185", "Retry session generator, copies to_practise topics", "Implemented"],
    ["Backend Services", "app/services/limits.py", "175", "PostgreSQL atomic counter upsert, rate limiter", "Implemented"],
    ["Backend Services", "app/services/manual_facts.py", "130", "Manual facts, 100-fact cap, duplicate check", "Implemented"],
    ["Frontend App", "frontend/app/page.tsx", "220", "Landing page, auth guard, profile card, resume upload", "Implemented"],
    ["Frontend App", "frontend/app/interview/page.tsx", "340", "Interview coordinator, session recovery prompt", "Implemented"],
    ["Frontend Components", "frontend/components/interview/*", "1450", "Flow, Setup, Turn, CameraPanel, VoicePanel, Report", "Implemented"],
    ["Frontend Lib", "frontend/lib/api.ts", "180", "fetch wrapper, credentials: include, CSRF Origin", "Implemented"],
    ["Frontend Lib", "frontend/lib/exportDoc.ts", "260", "HTML document generator for plans/reports with CSP", "Implemented"],
    ["Frontend Lib", "frontend/lib/expressions.ts", "170", "Face expression classification, pacing rules", "Implemented"],
    ["Frontend Lib", "frontend/lib/voice.ts", "195", "Speech chunking, voice selection, speech metrics", "Implemented"],
]
add_tbl(inv_headers, inv_rows, col_widths=[1.3, 1.8, 0.6, 2.3, 0.9])

add_title("2. Architecture & Design Invariant Summary", level=2)
add_bullet("LLM Proposes, Orchestrator Decides, Validator Verifies, Database Stores: External models have zero authority over state.")
add_bullet("Untrusted Input Isolation: Resumes and answers are treated as untrusted text; prompt injection attempts remain inert.")
add_bullet("Verbatim Fact Provenance: Extracted facts are verbatim substrings of resume lines; unapproved facts are never used.")
add_bullet("Deterministic Pacing & Time Limits: If less than 60s remain before a turn, the interview ends with TIME_LIMIT.")
add_bullet("Formative, Non-Aggregated Feedback: Rubric evaluations mandate exact substring quotes; zero combined/average scores.")
add_bullet("Privacy-by-Design Biometrics: Expression signals are processed client-side via WebGL; zero video frames leave device.")

add_title("3. Automated Test Evidence Summary", level=2)
add_bullet("Backend Pytest Suite: 4,693 automated tests across 26 modules (100% PASS against PostgreSQL test DB).")
add_bullet("Frontend Node Unit Tests: 45 automated TypeScript tests in frontend/lib/*.test.ts (100% PASS in 417 ms).")
add_bullet("Browser E2E Journey Suite: 37 browser journey checks via headless Edge over CDP (100% PASS).")
add_bullet("Static Type Checks & Lint: tsc --noEmit and ESLint reported zero errors.")

add_title("4. Known Limitations & Constraints", level=2)
add_bullet("Production Flag: In production mode, application routes are disabled by design, serving only /api/health.")
add_bullet("Account Recovery: Password reset and email verification require external transactional email provider integration.")
add_bullet("Linguistic Scope: Heuristic regexes and heading detection rules are optimized for English-language technical resumes.")
add_bullet("Scanned Documents: PDF parser requires text-based PDFs; scanned documents require future asynchronous OCR.")

doc.save(DOCX_OUT)
print(f"Companion DOCX saved to: {DOCX_OUT}")
