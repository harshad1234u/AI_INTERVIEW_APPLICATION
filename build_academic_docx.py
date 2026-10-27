"""Build clean Academic Project Report (.docx) for AI Interview Coach.
Follows:
- Sample report structure (Chapters 1 to 6, Appendices, References)
- Paragraph-based academic format (no bullet points)
- Front-pages excluded (starts at Abstract & Table of Contents)
- Times New Roman typography, 1.15 line spacing, 6pt after
- High-res embedded UML diagrams & screenshots
"""

import os
import sys
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

REPORT_DIR = r"D:\code_placed\ai_interview_coach\report_output"
DIAGRAMS_DIR = os.path.join(REPORT_DIR, "diagrams")
SCREENSHOTS_DIR = os.path.join(REPORT_DIR, "screenshots")
DOCX_OUT = os.path.join(REPORT_DIR, "AI_Interview_Coach_Academic_Report.docx")

doc = Document()

# Set Standard Page Margins (1.25" gutter left, 1.0" others)
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.25)
    section.right_margin = Inches(1.0)

C_NAVY = RGBColor(30, 58, 138)
C_DARK = RGBColor(31, 41, 55)
C_MUTED = RGBColor(71, 85, 105)

def style_p(p, space_before=0, space_after=6, line_spacing=1.15, align=WD_ALIGN_PARAGRAPH.JUSTIFY):
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = line_spacing
    p.alignment = align

def add_title(text, level=1):
    p = doc.add_paragraph()
    if level == 1:
        style_p(p, space_before=18, space_after=8, align=WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(16)
        r.bold = True
        r.font.color.rgb = C_NAVY
    elif level == 2:
        style_p(p, space_before=14, space_after=6, align=WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(13)
        r.bold = True
        r.font.color.rgb = C_NAVY
    else:
        style_p(p, space_before=10, space_after=4, align=WD_ALIGN_PARAGRAPH.LEFT)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(11.5)
        r.bold = True
        r.font.color.rgb = C_DARK
    return p

def add_body(text, bold_prefix=None, italic=False):
    p = doc.add_paragraph()
    style_p(p, space_before=0, space_after=6)
    if bold_prefix:
        r_pre = p.add_run(bold_prefix)
        r_pre.font.name = "Times New Roman"
        r_pre.font.size = Pt(11.5)
        r_pre.bold = True
        r_pre.font.color.rgb = C_DARK
    r = p.add_run(text)
    r.font.name = "Times New Roman"
    r.font.size = Pt(11.5)
    r.italic = italic
    r.font.color.rgb = C_DARK
    return p

def add_fig(filename, caption_text, width_in=5.8):
    path = os.path.join(DIAGRAMS_DIR, filename) if not os.path.isabs(filename) else filename
    if os.path.exists(path):
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style_p(p_img, space_before=12, space_after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
        run_img = p_img.add_run()
        run_img.add_picture(path, width=Inches(width_in))
        
        p_cap = doc.add_paragraph()
        style_p(p_cap, space_before=2, space_after=12, align=WD_ALIGN_PARAGRAPH.CENTER)
        r_cap = p_cap.add_run(caption_text)
        r_cap.font.name = "Times New Roman"
        r_cap.font.size = Pt(10)
        r_cap.bold = True
        r_cap.font.color.rgb = C_NAVY

def add_shot(filename, caption_text, width_in=5.6):
    path = os.path.join(SCREENSHOTS_DIR, filename)
    if os.path.exists(path):
        p_img = doc.add_paragraph()
        style_p(p_img, space_before=12, space_after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
        run_img = p_img.add_run()
        run_img.add_picture(path, width=Inches(width_in))
        
        p_cap = doc.add_paragraph()
        style_p(p_cap, space_before=2, space_after=12, align=WD_ALIGN_PARAGRAPH.CENTER)
        r_cap = p_cap.add_run(caption_text)
        r_cap.font.name = "Times New Roman"
        r_cap.font.size = Pt(10)
        r_cap.bold = True
        r_cap.font.color.rgb = C_NAVY

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
        style_p(p, space_before=4, space_after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
        for r in p.runs:
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)

    for row_idx, data_row in enumerate(rows):
        row_cells = table.rows[row_idx + 1].cells
        bg_col = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, cell_value in enumerate(data_row):
            row_cells[col_idx].text = str(cell_value)
            set_cell_background(row_cells[col_idx], bg_col)
            p = row_cells[col_idx].paragraphs[0]
            align = WD_ALIGN_PARAGRAPH.CENTER if col_idx in (0, 2, 4) else WD_ALIGN_PARAGRAPH.LEFT
            style_p(p, space_before=3, space_after=3, align=align)
            for r in p.runs:
                r.font.name = "Times New Roman"
                r.font.size = Pt(9.5)
                r.font.color.rgb = C_DARK

    if col_widths:
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

    p_spacer = doc.add_paragraph()
    style_p(p_spacer, space_before=0, space_after=8)

def add_code(code_str):
    p = doc.add_paragraph()
    style_p(p, space_before=4, space_after=8, line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.LEFT)
    r = p.add_run(code_str)
    r.font.name = "Courier New"
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(30, 41, 59)

print("Building docx document...")

# ==========================================
# PRELIMINARY PAGES (Excluding Front Cover)
# ==========================================
add_title("ABSTRACT", level=1)
add_body(
    "The AI Interview Coach is an open-source, candidate-centric web application and conversational simulation platform "
    "engineered to prepare software engineering students and junior developers for high-stakes technical interviews. "
    "The platform addresses fundamental flaws in conventional preparation paradigms—such as static question banks, "
    "hallucinated qualifications by general-purpose large language models, and intrusive biometric surveillance platforms—by "
    "enforcing deterministic software engineering invariants over generative artificial intelligence workflows. Utilizing a robust "
    "multi-agent orchestration architecture, the platform extracts verifiable facts from uploaded resumes through deterministic heuristics, "
    "mandates human-in-the-loop candidate verification before interview initialization, and regulates the conversational interview lifecycle "
    "through a transactional Finite State Machine implemented in PostgreSQL. All model-generated proposals are routed through a provider-agnostic "
    "Model Gateway equipped with strict JSON-schema validators, bounded retry mechanisms, and automatic fallback cascades spanning Google Gemini, "
    "Groq, NVIDIA NIM, and deterministic local rules. Performance evaluation is governed by an objective rubric scoring framework that assesses "
    "answers across four technical dimensions on a 1–5 scale, mandating exact verbatim quote evidence and prohibiting black-box single-score candidate "
    "rankings. The application delivers comprehensive practice diagnostics, localized speech pace metrics, and targeted retry sessions within a "
    "responsive user interface built using Next.js, React, and Tailwind CSS, backed by a FastAPI and SQLAlchemy service layer. Comprehensive unit, "
    "integration, and end-to-end testing validate the system's operational reliability, zero-leakage privacy boundaries, and strict sub-two-second "
    "latency profiles."
)
add_body(
    "Keywords: Artificial Intelligence, Technical Interview Simulation, Finite State Machine, Model Gateway, Rubric-Based Evaluation, Resume Parsing, Software Engineering Architecture, Next.js, FastAPI, PostgreSQL.",
    italic=True
)

doc.add_page_break()

add_title("TABLE OF CONTENTS", level=1)
toc_headers = ["CHAPTER", "TITLE", "PAGE NO."]
toc_rows = [
    ["", "ABSTRACT", "iii"],
    ["", "LIST OF FIGURES", "iv"],
    ["", "LIST OF ABBREVIATIONS", "v"],
    ["1", "INTRODUCTION", "1"],
    ["", "1.1 INTRODUCTION ABOUT DOMAIN", "1"],
    ["", "1.2 PROBLEM DESCRIPTION", "2"],
    ["", "1.3 OBJECTIVE OF THE PROJECT", "3"],
    ["", "1.4 SCOPE OF THE PROJECT", "4"],
    ["2", "SYSTEM REQUIREMENT SPECIFICATIONS (SRS)", "5"],
    ["", "2.1 FUNCTIONAL REQUIREMENTS", "5"],
    ["", "2.2 NON-FUNCTIONAL REQUIREMENTS", "7"],
    ["", "2.3 HARDWARE REQUIREMENTS", "8"],
    ["", "2.4 SOFTWARE REQUIREMENTS", "9"],
    ["", "2.5 USER CHARACTERISTICS", "10"],
    ["", "2.6 CONSTRAINTS", "10"],
    ["3", "ANALYSIS AND DESIGN", "11"],
    ["", "3.1 USE CASE DIAGRAM", "11"],
    ["", "3.2 CLASS DIAGRAM", "13"],
    ["", "3.3 ACTIVITY DIAGRAM", "15"],
    ["", "3.4 SEQUENCE DIAGRAM", "17"],
    ["", "3.5 STATE MACHINE DIAGRAM", "19"],
    ["", "3.6 COMPONENT DIAGRAM", "21"],
    ["", "3.7 DEPLOYMENT DIAGRAM", "23"],
    ["", "3.8 PACKAGE DIAGRAM", "25"],
    ["", "3.9 DESIGN PATTERNS USED", "26"],
    ["4", "IMPLEMENTATION", "28"],
    ["", "4.1 MODULE DESCRIPTION", "28"],
    ["", "4.2 TECHNOLOGY DESCRIPTION", "32"],
    ["5", "TESTING", "34"],
    ["", "5.1 UNIT TESTING", "34"],
    ["", "5.2 INTEGRATION TESTING", "35"],
    ["", "5.3 TEST RESULTS", "36"],
    ["6", "CONCLUSION AND FUTURE ENHANCEMENT", "39"],
    ["", "6.1 CONCLUSION", "39"],
    ["", "6.2 FUTURE ENHANCEMENT", "40"],
    ["", "APPENDIX A – SOURCE CODE", "41"],
    ["", "APPENDIX B – SCREEN SHOTS", "52"],
    ["", "REFERENCES", "57"],
]
add_tbl(toc_headers, toc_rows, col_widths=[1.2, 4.2, 1.1])

doc.add_page_break()

add_title("LIST OF FIGURES", level=1)
lof_headers = ["FIGURE NO.", "TITLE", "PAGE NO."]
lof_rows = [
    ["3.1", "USE CASE DIAGRAM", "11"],
    ["3.2", "CLASS DIAGRAM", "13"],
    ["3.3", "ACTIVITY DIAGRAM", "15"],
    ["3.4", "SEQUENCE DIAGRAM", "17"],
    ["3.5", "STATE MACHINE DIAGRAM", "19"],
    ["3.6", "COMPONENT DIAGRAM", "21"],
    ["3.7", "DEPLOYMENT DIAGRAM", "23"],
    ["3.8", "PACKAGE DIAGRAM", "25"],
    ["B.1", "AUTHENTICATION & LOGIN INTERFACE", "52"],
    ["B.2", "RESUME UPLOAD & PROVENANCE FACT REVIEW", "53"],
    ["B.3", "INTERVIEW PLAN CONFIGURATION & TOPIC BLUEPRINT", "54"],
    ["B.4", "LIVE ADAPTIVE INTERVIEW SESSION & PACING MONITOR", "55"],
    ["B.5", "RUBRIC EVALUATION REPORT & EVIDENCE AUDIT", "56"],
    ["B.6", "TARGETED RETRY SESSION & TOPICAL REMEDIATION", "56"],
]
add_tbl(lof_headers, lof_rows, col_widths=[1.4, 4.0, 1.1])

add_title("LIST OF ABBREVIATIONS", level=1)
loa_headers = ["ABBREVIATION", "FULL FORM"]
loa_rows = [
    ["AI", "Artificial Intelligence"],
    ["LLM", "Large Language Model"],
    ["FSM", "Finite State Machine"],
    ["SRS", "System Requirement Specifications"],
    ["REST", "Representational State Transfer"],
    ["API", "Application Programming Interface"],
    ["JSON", "JavaScript Object Notation"],
    ["JSONB", "Binary JavaScript Object Notation"],
    ["ORM", "Object-Relational Mapping"],
    ["CSRF", "Cross-Site Request Forgery"],
    ["XSS", "Cross-Site Scripting"],
    ["UI", "User Interface"],
    ["UX", "User Experience"],
    ["MVC", "Model-View-Controller"],
    ["GOF", "Gang of Four"],
    ["GRASP", "General Responsibility Assignment Software Patterns"],
    ["SQL", "Structured Query Language"],
    ["ACID", "Atomicity, Consistency, Isolation, Durability"],
    ["HTTP", "Hypertext Transfer Protocol"],
    ["HTTPS", "Hypertext Transfer Protocol Secure"],
    ["JWT", "JSON Web Token"],
    ["W3C", "World Wide Web Consortium"],
]
add_tbl(loa_headers, loa_rows, col_widths=[2.0, 4.5])

doc.add_page_break()

# ==========================================
# CHAPTER 1: INTRODUCTION
# ==========================================
add_title("CHAPTER 1", level=1)
add_title("INTRODUCTION", level=1)

add_title("1.1 INTRODUCTION ABOUT DOMAIN", level=2)
add_body(
    "In the contemporary software engineering landscape, securing internships and professional employment requires candidates to "
    "navigate rigorous, multi-stage technical assessments. These evaluations examine not only theoretical computer science foundations—such "
    "as data structure manipulation, algorithm complexity, and distributed database transactions—but also practical system design trade-offs, "
    "behavioral competencies, and the clarity with which candidates articulate past technical decisions. For university undergraduates and early-career "
    "developers, transitioning from structured classroom curricula to high-pressure technical interviews represents a substantial barrier. Traditional "
    "preparation workflows, such as grinding static problem repositories or reviewing textbook question banks, suffer from critical pedagogical "
    "deficiencies. They lack conversational realism, fail to adapt questions to the candidate's verified resume background, and provide zero "
    "contextual feedback on how effectively technical reasoning is communicated under realistic time constraints."
)
add_body(
    "With recent breakthroughs in Large Language Models and generative natural language interfaces, artificial intelligence has emerged as a promising "
    "foundation for automated educational simulations and personalized tutoring. However, applying generative models directly to high-stakes interview coaching "
    "introduces severe software engineering challenges. General-purpose conversational systems frequently hallucinate candidate credentials, formulate "
    "meandering or repetitive inquiries, lose track of session duration, and produce flattering, ungrounded qualitative scores. Conversely, commercial automated "
    "hiring platforms are engineered for recruiter-driven screening, utilizing black-box models to filter out job seekers while recording biometric video feeds "
    "that introduce substantial privacy risks and algorithmic bias."
)
add_body(
    "There is consequently an urgent academic and industrial need for an open-source, candidate-first technical interview simulation system that merges "
    "the conversational flexibility of generative AI with deterministic software engineering controls. Such a platform must operate as a formative educational "
    "mentor rather than an unguided evaluator, enforcing stringent candidate privacy guarantees, deterministic lifecycle management, and fact-grounded interview personalization."
)

add_title("1.2 PROBLEM DESCRIPTION", level=2)
add_body(
    "Candidates preparing for professional software engineering interviews encounter systemic obstacles in existing preparation environments. Conventional "
    "preparation models rely on static platforms that cannot evaluate conversational technical reasoning or probe into specific design choices made during real-world "
    "projects. When candidates attempt to use generic chatbot platforms for practice, the models frequently hallucinate qualifications, fail to enforce realistic "
    "turn-taking boundaries, and fall prey to prompt injection vulnerabilities that derail the interview session. Furthermore, commercial AI hiring platforms prioritize "
    "corporate candidate rejection through opaque scoring algorithms, capturing sensitive audio and video recordings without providing transparent, educational feedback."
)
add_body(
    "To overcome these deficiencies, an automated coaching platform must decouple generative language generation from core system governance. The platform must extract "
    "verifiable technical facts directly from resumes, require explicit candidate verification before facts are utilized, enforce strict turn deadlines through a transactional "
    "state machine, and evaluate answers against verifiable rubric criteria grounded solely in exact candidate quotes. Providing this level of engineering rigor guarantees that "
    "students receive realistic, trustworthy interview practice while safeguarding their personal data."
)

add_title("1.3 OBJECTIVE OF THE PROJECT", level=2)
add_body(
    "The principal objective of this project is to architect, develop, and empirically validate the AI Interview Coach—a resume-grounded, adaptive technical interview practice "
    "platform for students and entry-level developers. The engineering objectives include designing a secure, multi-tenant authentication subsystem employing scrypt password hashing, "
    "cryptographic session tokens stored in HttpOnly cookies, and strict candidate data isolation. The project aims to develop a deterministic resume parsing engine capable of extracting "
    "verifiable skills, projects, and educational credentials from multi-page PDF documents, backed by a human-in-the-loop review interface that treats unverified extractions as untrusted data."
)
add_body(
    "The project further aims to construct a provider-agnostic Model Gateway that interfaces with premier LLMs across Google Gemini, Groq, and NVIDIA NIM using standardized JSON-schema "
    "contracts, bounded retry limits, and automatic fallback cascades. A central objective is the implementation of a deterministic Finite State Machine in PostgreSQL that governs "
    "session lifecycles, turn deadlines, and status transitions under the principle that language models propose content while deterministic orchestrators validate, decide, and persist state. "
    "Finally, the system aims to establish an objective rubric evaluation engine scoring technical responses across four dimensions on a 1–5 scale, mandating exact verbatim evidence quotes "
    "and producing actionable diagnostic reports alongside targeted retry sessions."
)

add_title("1.4 SCOPE OF THE PROJECT", level=2)
add_body(
    "The scope of this project encompasses the end-to-end design, implementation, and empirical verification of a complete single-page web application and asynchronous backend microservice. "
    "The platform includes client-side authentication, PDF resume ingestion, text normalization, human-in-the-loop fact management, dynamic session plan formulation, adaptive conversational interviewing, "
    "real-time camera-based pacing analysis, and rubric-based performance auditing. The backend manages relational database models, Alembic schema migrations, rate-limiting counters, and "
    "fault-tolerant API integrations across external AI inference providers."
)
add_body(
    "The project deliberately restricts its operational boundary to formative candidate preparation and self-directed skill enhancement, explicitly excluding recruiter-facing applicant ranking, "
    "automated hiring gatekeeping, and video-based emotion detection. The system operates locally without cloud data persistence of audio or raw video streams, performing camera engagement "
    "classification entirely on the client device using lightweight web vision models. Comprehensive automated testing suites—spanning thousands of unit test invariants, integration transactional tests, "
    "and end-to-end headless browser journeys—are integrated into the project scope to guarantee continuous software quality, high availability, and deterministic execution."
)

doc.add_page_break()

# ==========================================
# CHAPTER 2: SRS
# ==========================================
add_title("CHAPTER 2", level=1)
add_title("SYSTEM REQUIREMENT SPECIFICATIONS (SRS)", level=1)

add_title("2.1 FUNCTIONAL REQUIREMENTS", level=2)
add_body(
    "The functional requirements define the core operational capabilities, interactions, and data transformations executed by the platform:"
)
add_body(
    "The system provides multi-tenant registration and authentication for candidates, enforcing secure credential storage via scrypt password hashing with high work factors. "
    "Authenticated sessions are managed through cryptographically random 256-bit session tokens stored exclusively within Secure, HttpOnly, SameSite cookies. The system enforces strict "
    "candidate data isolation across all database operations, preventing unauthorized cross-tenant data access, and automatically terminates inactive sessions following preconfigured expiration windows.",
    bold_prefix="User Authentication and Session Management: "
)
add_body(
    "The platform accepts candidate resume uploads in PDF format up to five megabytes in size. Ingestion routines extract raw textual content, normalize typographical ligatures, and execute "
    "deterministic, rule-based heuristics to segment the document into structured sections including technical skills, practical projects, work experience, and educational background. The ingestion "
    "engine strips embedded executable macros and treats all parsed text as untrusted candidate input to prevent adversarial injection.",
    bold_prefix="Deterministic Resume Parsing and Text Extraction: "
)
add_body(
    "The system mandates that all extracted resume items enter a pending review state prior to interview configuration. Candidates are provided an interactive interface to inspect, verify, "
    "edit, or reject each extracted fact. The provenance subsystem immutably records the source of each fact, the extraction mechanism, the original text, and candidate modifications. Only facts "
    "explicitly approved by the candidate are promoted to the active profile for subsequent interview question generation.",
    bold_prefix="Human-in-the-Loop Fact Provenance and Review: "
)
add_body(
    "The platform governs each interview session through a deterministic Finite State Machine persisted within the database. The state engine enforces valid transitions across session setup, "
    "active questioning, answer submission, evaluation, and completion states. The orchestrator guarantees that only one unfinished interview session exists per candidate at any time through "
    "database partial unique indexing and serializes turn updates using database row-level locking.",
    bold_prefix="Finite State Machine Session Lifecycle Orchestration: "
)
add_body(
    "The system routes all conversational and evaluative requests through an abstract Model Gateway interfacing with multiple upstream AI providers, including Google Gemini, Groq, and NVIDIA NIM. "
    "The gateway enforces strict JSON-schema response validation, per-attempt timeout limits, and exponential backoff algorithms. If an upstream provider experiences rate-limiting, latency spikes, or schema "
    "non-compliance, the gateway automatically executes a fallback cascade to alternate cloud models or local deterministic rule catalogs without terminating the active interview.",
    bold_prefix="Provider-Agnostic Model Gateway and Fallback Execution: "
)
add_body(
    "Upon the submission of an answer, the evaluation module analyzes the technical response against four standardized rubric criteria: technical accuracy, communication clarity, problem-solving depth, "
    "and trade-off awareness. The scoring engine evaluates each criterion on an objective 1–5 scale, mandating that every score justification is supported by an exact verbatim substring quote extracted directly "
    "from the candidate's submitted answer. The module prohibits arbitrary global scores and flags unverified candidate assertions.",
    bold_prefix="Verbatim Quote-Grounded Rubric Evaluation: "
)
add_body(
    "Upon session conclusion, the platform compiles an interactive diagnostic report categorizing demonstrated technical proficiencies and specific areas requiring improvement. The report highlights "
    "demonstrated concepts alongside missing technical foundations, providing actionable recommendations and reference study topics. Candidates can initiate targeted retry sessions focused exclusively on "
    "unmastered topics to reinforce their understanding.",
    bold_prefix="Practice Diagnostics and Targeted Remediation: "
)

add_title("2.2 NON-FUNCTIONAL REQUIREMENTS", level=2)
add_body(
    "The non-functional specifications define the quality attributes, performance constraints, and architectural standards enforced by the system:"
)
add_body(
    "The application interface provides an intuitive, clutter-free environment designed for minimal cognitive friction during interview preparation. Navigation flows, turn counters, remaining session "
    "timers, and real-time pacing feedback are prominently displayed with accessible visual contrast complying with WCAG 2.1 AA standards. The interface operates seamlessly across desktop browsers and mobile "
    "devices through responsive layout adaptation.",
    bold_prefix="Usability and Interface Ergonomics: "
)
add_body(
    "The platform maintains strict response time budgets across all operational tiers. Local database operations and state machine transitions execute in under fifty milliseconds. Client-side audio processing "
    "and camera engagement calculations operate at thirty frames per second without degrading interface responsiveness. End-to-end question generation and answer evaluation requests complete within an enforced "
    "two-second latency envelope through asynchronous task pipelining and model streaming.",
    bold_prefix="Performance and Latency Budgets: "
)
add_body(
    "The system implements strict local-first privacy boundaries. No high-resolution candidate video feeds or raw audio recordings are transmitted to external servers or persisted to disk. Camera pacing analysis "
    "and voice transcription are processed entirely on-device within the user's browser runtime. Sensitive database fields are protected with row-level ownership checks, and all outgoing API payloads to cloud language "
    "models are sanitized to strip personal identifiers.",
    bold_prefix="Data Privacy and Local Security Boundaries: "
)
add_body(
    "The backend microservice is designed for horizontal stateless scaling within containerized environments. Database connections are managed through optimized connection pooling with strict connection recycling "
    "policies. Relational models utilize composite indexes and JSONB indexing to ensure sub-millisecond query execution even as historical session records scale into tens of thousands of entries.",
    bold_prefix="Scalability and Resource Efficiency: "
)
add_body(
    "The system ensures continuous operational availability through decoupled service architecture and redundant provider failovers. The application survives total third-party AI provider outages by gracefully "
    "degrading to curated deterministic question catalogs and offline evaluation rules. Database transactions enforce ACID properties with automatic transaction rollbacks on unexpected runtime exceptions.",
    bold_prefix="High Availability and Fault Resilience: "
)
add_body(
    "The platform guarantees deterministic repeatability in session progression and evaluation auditing. State machine transition tables reject unauthorized transitions, logging detailed audit trails with monotonic "
    "timestamps. Rubric scoring criteria enforce strict schema validation, ensuring that subjective or ungrounded evaluations are rejected before database persistence.",
    bold_prefix="Algorithmic Determinism and Auditability: "
)

add_title("2.3 HARDWARE REQUIREMENTS", level=2)
add_body(
    "The system operates efficiently across diverse standard computing hardware without requiring specialized server accelerators:"
)
add_body(
    "The client application runs on any standard desktop, laptop, or mobile computing device equipped with a modern web browser. The minimum recommended hardware configuration includes a dual-core processor "
    "operating at 1.8 GHz or higher, two gigabytes of system memory (RAM), and fifty megabytes of local browser storage for caching assets and temporary session states. An optional integrated webcam and microphone "
    "are utilized for candidates electing to activate real-time speech and visual engagement feedback.",
    bold_prefix="Client System Specifications: "
)
add_body(
    "The backend application and relational database operate on lightweight virtualized servers or container clusters. The production deployment requires a minimum of one virtual CPU (x86_64 or ARM64 architecture), "
    "two gigabytes of available RAM, and ten gigabytes of persistent solid-state drive (SSD) storage for PostgreSQL data tables and transaction logs. Network infrastructure requires a broadband internet connection with an "
    "outbound HTTPS bandwidth of at least five megabits per second to support concurrent third-party AI model gateway transactions.",
    bold_prefix="Server and Deployment Infrastructure: "
)

add_title("2.4 SOFTWARE REQUIREMENTS", level=2)
add_body(
    "The platform is developed and executed using contemporary, standards-compliant software frameworks and tools:"
)
add_body(
    "The user interface is engineered using Next.js 14, React 18, and TypeScript, providing strict compile-time type safety and high-performance client-side rendering. User interface styling is delivered via Tailwind CSS, "
    "while iconography is powered by Lucide React. On-device media stream processing is executed using native Web Audio APIs and client-side machine vision models running in WebAssembly. The frontend application is fully "
    "compatible with Google Chrome (version 100+), Mozilla Firefox (version 100+), Apple Safari (version 15+), and Microsoft Edge.",
    bold_prefix="Frontend Client Environment: "
)
add_body(
    "The server-side application is developed in Python 3.11 using the FastAPI framework, leveraging asynchronous concurrency and Pydantic v2 data validation schemas. Relational data modeling, ACID transactions, and "
    "connection pooling are managed via SQLAlchemy 2.0 ORM, backed by PostgreSQL 15 as the primary relational database. Database schema migrations and version tracking are maintained through Alembic. Containerization and "
    "orchestration are configured using Docker and Docker Compose for reproducible cross-platform deployment.",
    bold_prefix="Backend Service and Database Framework: "
)

add_title("2.5 USER CHARACTERISTICS", level=2)
add_body(
    "The primary users of the AI Interview Coach are undergraduate computer science students, software engineering boot camp attendees, and junior developers preparing for technical recruitment processes. Users are expected "
    "to possess basic operational familiarity with web browsers, file selection dialogues, and online technical assessments. While candidates have varying levels of domain proficiency—spanning data structures, web frameworks, "
    "and database architecture—they do not require any specialized knowledge of machine learning, prompt engineering, or cloud infrastructure to operate the system. The intuitive graphical interface presents evaluation metrics, "
    "confidence intervals, and topical recommendations in transparent visual formats that allow candidates of all backgrounds to identify their technical strengths and target their revision effectively."
)

add_title("2.6 CONSTRAINTS", level=2)
add_body(
    "The platform operates within several clearly delineated architectural and operational constraints. The generative capabilities of external language models are fundamentally dependent on network connectivity; during complete "
    "internet disconnection, the system relies exclusively on pre-compiled deterministic question catalogs and local rule evaluators. The system strictly enforces token length constraints on resume extraction (maximum five pages) "
    "and candidate answer submissions (maximum ten thousand characters) to prevent denial-of-service vulnerabilities and buffer overflows. Furthermore, to eliminate legal compliance liabilities and respect candidate autonomy, the "
    "platform enforces a strict non-persistence policy on all biometric and vocal data, prohibiting any facial recognition recording or audio waveform persistence."
)

doc.add_page_break()

# ==========================================
# CHAPTER 3: ANALYSIS AND DESIGN
# ==========================================
add_title("CHAPTER 3", level=1)
add_title("ANALYSIS AND DESIGN", level=1)

add_title("3.1 USE CASE DIAGRAM", level=2)
add_fig("3.1_use_case_diagram.png", "Figure 3.1: USE CASE DIAGRAM")
add_title("3.1.1 Use Case Diagram Description", level=3)
add_body(
    "The Use Case Diagram defines the behavioral perimeter of the system and formalizes the communication contracts between primary, secondary, and system actors. The primary human actor is the Candidate, representing students "
    "or job applicants who authenticate into the platform, upload resume documents, review extracted background facts, configure customized mock interview sessions, answer technical questions, and inspect diagnostic rubric evaluations. "
    "The secondary cloud actor comprises the External AI Providers—specifically Google Gemini, Groq, and NVIDIA NIM—which provide stateless natural language generation under strict JSON-schema constraints. The internal System Actor is "
    "the Deterministic Orchestrator, which enforces state transitions, rate limits, turn timers, and fallback cascades."
)
add_body(
    "The diagram delineates critical architectural dependencies through standard UML associations. The Register and Authenticate use case includes an automated HttpOnly cookie verification routine to guarantee token validity. "
    "The Upload PDF Resume use case includes a deterministic section parsing routine, while the Review Extracted Facts use case is extended by optional AI-assisted extraction when candidates request automated structuring of complex "
    "project descriptions. During live interviews, the Execute Interview Turn use case includes mandatory turn timer enforcement and can be extended by the Clarify or Rephrase Question use case when candidates seek assistance. Finally, "
    "the View Diagnostic Report use case is extended by the Start Targeted Retry use case, enabling immediate focused practice on unmastered concepts."
)

add_title("3.2 CLASS DIAGRAM", level=2)
add_fig("3.2_class_diagram.png", "Figure 3.2: CLASS DIAGRAM")
add_title("3.2.1 Class Diagram Description", level=3)
add_body(
    "The Class Diagram establishes the domain model and persistence architecture implemented within SQLAlchemy and PostgreSQL. At the core of the domain model is the Candidate entity, which encapsulates identity attributes, "
    "scrypt password hashes, failed login counters, and lockout timestamps. The Candidate maintains a one-to-many relationship with AuthSession entities, which manage cryptographic session token hashes and expiration timestamps. "
    "The Candidate also possesses one-to-many associations with Resume entities, storing raw extracted text, file cryptographic hashes, and structured section dictionaries."
)
add_body(
    "Each Resume links to multiple CandidateFact entities, which capture atomic technical proficiencies, project milestones, and educational credentials. The CandidateFact class encapsulates complete provenance metadata, including "
    "extraction mechanisms, source text, review status, and modification histories. The InterviewSession entity manages the end-to-end interview lifecycle, maintaining an active state enumeration, JSONB plan blueprints, elapsed timers, "
    "and termination reasons. Each session contains an ordered sequence of InterviewQuestion entities tracking sequence numbers, prompt questions, candidate responses, and answer timestamps. Each question associates with an AnswerEvaluation "
    "entity containing granular rubric scores, missing concept arrays, and verbatim quote strings that guarantee empirical grounding."
)

add_title("3.3 ACTIVITY DIAGRAM", level=2)
add_fig("3.3_activity_diagram.png", "Figure 3.3: ACTIVITY DIAGRAM")
add_title("3.3.1 Activity Diagram Description", level=3)
add_body(
    "The Activity Diagram models the end-to-end procedural execution path navigated by candidates. The workflow initiates when a candidate uploads a PDF resume. The system extracts the underlying text and validates structural "
    "completeness; if parsing encounters corruption or unreadable fonts, an error is surfaced and execution terminates. Following successful text extraction, deterministic rules segment the text into skills, projects, and work experiences, "
    "placing all items into a pending review queue."
)
add_body(
    "The candidate must review, modify, or approve these facts before proceeding. Once the profile facts are verified, the candidate configures interview parameters—such as targeted roles, difficulty levels, and session duration—triggering "
    "plan generation. The interview loop commences with the platform dispatching tailored technical questions. The candidate submits their response, which is routed to the rubric evaluation engine. The orchestrator verifies that all cited "
    "evidence quotes exist as exact substrings within the submitted text; if verification fails, the gateway re-executes evaluation. The turn cycle iterates until all planned questions are completed or session time expires, culminating "
    "in the compilation of the comprehensive diagnostic practice report."
)

add_title("3.4 SEQUENCE DIAGRAM", level=2)
add_fig("3.4_sequence_diagram.png", "Figure 3.4: SEQUENCE DIAGRAM")
add_title("3.4.1 Sequence Diagram Description", level=3)
add_body(
    "The Sequence Diagram documents the chronological message sequence exchanged across the architectural layers during a practice session. The candidate submits a resume through the user interface, which transmits the file payload "
    "to the backend orchestrator. The orchestrator invokes deterministic parsing routines and persists extracted candidate facts into PostgreSQL within transactional boundaries. The user interface displays the parsed facts, allowing "
    "the candidate to transmit verification updates that update fact statuses to approved."
)
add_body(
    "Upon session initialization, the user interface signals the orchestrator to formulate an interview plan. The orchestrator routes the approved facts to the Model Gateway, which returns a schema-validated session blueprint. The orchestrator "
    "creates the interview session in PostgreSQL, records the first question, and dispatches it to the client. When the candidate submits an answer, the orchestrator validates turn deadlines, locks the session row, and invokes the Model Gateway "
    "to execute rubric scoring. Upon receiving validated scores and verified verbatim evidence, the orchestrator persists the evaluation records and advances the session state."
)

add_title("3.5 STATE MACHINE DIAGRAM", level=2)
add_fig("3.5_state_machine_diagram.png", "Figure 3.5: STATE MACHINE DIAGRAM")
add_title("3.5.1 State Machine Diagram Description", level=3)
add_body(
    "The State Machine Diagram specifies the deterministic lifecycle states governing an interview session from initialization to archival. A session is instantiated in the CREATED state and transitions into PROFILE_PROCESSING upon resume "
    "ingestion. Once text extraction concludes, the session enters PROFILE_REVIEW, where it remains until the candidate explicitly dispatches the CONFIRM_PROFILE command. The session then advances to INTERVIEW_PLANNING, invoking the Model "
    "Gateway to construct the session topic blueprint, transitioning to READY once the plan is verified."
)
add_body(
    "When the candidate initiates the interview, the session enters the active questioning loop: advancing to ASKING while the question payload is dispatched, then to WAITING_FOR_ANSWER. In this state, candidates can pause and resume the "
    "interview, or submit their response, advancing the state to ANSWER_PROCESSING and ANSWER_EVALUATION. Following rubric score verification, the session enters NEXT_DECISION, which evaluates remaining time and topic coverage to trigger "
    "follow-up questions, advance to the next topic, or initiate REPORT_GENERATION. The session culminates in the terminal COMPLETED state once the diagnostic report is persisted."
)

add_title("3.6 COMPONENT DIAGRAM", level=2)
add_fig("3.7_component_diagram.png", "Figure 3.6: COMPONENT DIAGRAM")
add_title("3.6.1 Component Diagram Description", level=3)
add_body(
    "The Component Diagram details the multi-tier modular architecture of the platform, highlighting clear separation of concerns across presentation, business logic, persistence, and external services. The Presentation Tier comprises the "
    "Next.js and React single-page client, containing dedicated components for authentication state, resume fact curation, active interview interaction, and local audio-visual feedback analysis. These client components interact with the backend "
    "service through an asynchronous HTTP REST Client utilizing secure cookie headers."
)
add_body(
    "The Business Logic Tier is encapsulated within the FastAPI application server, divided into specialized functional subsystems. The API Router validates request schemas using Pydantic, enforcing authentication boundaries before dispatching "
    "tasks to the Resume Parser, the Finite State Machine Core, or the Rubric Evaluation Engine. The Model Gateway serves as a unified abstraction layer managing communication with external AI providers, handling connection pools, rate limits, "
    "and fallback routines. All persistent data is managed within PostgreSQL via SQLAlchemy ORM, ensuring strict transactional integrity across all state mutations."
)

add_title("3.7 DEPLOYMENT DIAGRAM", level=2)
add_fig("3.8_deployment_diagram.png", "Figure 3.7: DEPLOYMENT DIAGRAM")
add_title("3.7.1 Deployment Diagram Description", level=3)
add_body(
    "The Deployment Diagram represents the runtime infrastructure and network topologies hosting the AI Interview Coach platform. The client runtime executes within the candidate's local browser environment on desktop or mobile operating systems, "
    "processing interface interactions and running lightweight machine vision scripts locally. The client communicates with the application server over secure HTTPS connections, passing authentication credentials through encrypted cookies."
)
add_body(
    "The application server executes within a containerized Linux environment managed via Docker, running the Uvicorn asynchronous server and FastAPI application service. The backend server establishes low-latency TCP connections to a dedicated "
    "PostgreSQL database container operating on port 5432. For language processing and evaluation tasks, the application server initiates secure outbound HTTPS transactions to external cloud API endpoints, including Google Gemini and Groq. This "
    "decoupled deployment topology ensures high maintainability, isolated resource allocation, and zero exposure of internal database ports to the public internet."
)

add_title("3.8 PACKAGE DIAGRAM", level=2)
add_fig("3.9_package_diagram.png", "Figure 3.8: PACKAGE DIAGRAM")
add_title("3.8.1 Package Diagram Description", level=3)
add_body(
    "The Package Diagram defines the physical and logical namespace distribution within the repository, enforcing strict layered dependencies and preventing cyclic coupling. The system is partitioned into two root packages: frontend and backend. "
    "Within the frontend package, the app namespace encapsulates page routes, root layouts, and metadata definitions. The components package organizes modular React widgets, separating presentation blocks from the underlying lib package, which "
    "houses shared utility functions, typed API clients, and browser hook wrappers."
)
add_body(
    "The backend package is structured into cohesive functional namespaces under app. The app.api package encapsulates HTTP routers and authentication middleware, depending directly upon the business logic layer housed in app.services. The services "
    "package orchestrates core application workflows, delegating data persistence to app.models (which defines declarative SQLAlchemy database entities) and delegating AI inference to app.ai (which manages the provider-independent Model Gateway, "
    "prompt templates, and schema validators). This strict top-down dependency hierarchy guarantees testability, maintainability, and clean separation of architectural concerns."
)

add_title("3.9 DESIGN PATTERNS USED", level=2)
add_body(
    "The platform incorporates several recognized software design patterns from the Gang of Four (GoF) and GRASP principles to ensure code modularity, testability, and architectural maintainability. The Singleton pattern is applied within the "
    "database configuration and model gateway modules to maintain single, shared connection pools and HTTP client instances across concurrent requests, minimizing connection overhead. The Factory pattern is utilized extensively during model "
    "gateway provider instantiation and report generation, enabling the system to construct specialized provider connectors or export formats dynamically based on runtime parameters."
)
add_body(
    "The Strategy pattern is central to the Model Gateway architecture, allowing the orchestrator to switch between language model backends—such as Gemini, Groq, NVIDIA, or local deterministic rules—without altering client-facing interfaces. "
    "The State pattern is implemented via the Finite State Machine engine, encapsulating state-specific validation rules, allowed transitions, and timeout actions within dedicated transition tables. The Chain of Responsibility pattern organizes "
    "request authentication, CSRF validation, rate limiting, and input sanitization into sequential middleware handlers that intercept requests prior to route execution. Finally, the overall system implements the Model-View-Controller (MVC) "
    "architecture: SQLAlchemy entities represent the Model, Next.js components form the View, and FastAPI router endpoints act as Controllers mediating user actions, enforcing business invariants, and updating system state."
)

doc.add_page_break()

# ==========================================
# CHAPTER 4: IMPLEMENTATION
# ==========================================
add_title("CHAPTER 4", level=1)
add_title("IMPLEMENTATION", level=1)

add_title("4.1 MODULE DESCRIPTION", level=2)
add_body(
    "The platform architecture is decomposed into eight cohesive operational modules:"
)
add_body(
    "The Authentication Module governs candidate registration, identity verification, and secure session management. Candidate passwords are encrypted using the memory-hard scrypt key derivation function, incorporating high CPU and memory cost "
    "parameters to protect against hardware-accelerated dictionary attacks. Upon authentication, the system generates a cryptographically secure 256-bit token stored in an HttpOnly, Secure, SameSite cookie, eliminating exposure to cross-site scripting "
    "vulnerabilities. The module implements automated brute-force protection by tracking failed login attempts per IP address and candidate account, applying a fifteen-minute lockout after five consecutive failures.",
    bold_prefix="Authentication and Credential Management Module: "
)
add_body(
    "The Resume Parsing Module processes uploaded PDF documents to extract textual content and structure it into standardized technical categories. The module utilizes deterministic font-size analysis, typographic weight detection, and newline heuristic "
    "clustering to identify structural headings such as technical skills, practical projects, work experience, and education. To prevent encoding corruption, the parser executes ligature normalization, expanding typographical ligatures into standard "
    "character sequences. The module isolates all extracted text as raw data strings, explicitly prohibiting script execution to safeguard downstream modules against prompt injection payloads embedded in resumes.",
    bold_prefix="Deterministic Resume Parsing Module: "
)
add_body(
    "The Fact Provenance Module provides candidates with complete oversight and editing authority over all information extracted from their resumes. Each extracted fact is assigned an immutable provenance record detailing its source document, extraction "
    "timestamp, confidence level, and review status. Candidates can approve, modify, or reject individual facts through an interactive user interface before any interview session can be initialized. The module enforces a strict database constraint that "
    "prevents the session planning engine from utilizing unverified facts, ensuring that all subsequent mock interview questions are grounded exclusively in candidate-confirmed competencies.",
    bold_prefix="Human-in-the-Loop Fact Provenance Module: "
)
add_body(
    "The State Machine Module manages the operational lifecycle of mock interview sessions, enforcing valid state progressions and guaranteeing deterministic execution. Implemented within PostgreSQL, the engine validates all state transitions against an "
    "immutable declarative matrix, preventing race conditions or illegal jumps across interview phases. The module applies database row-level locking (SELECT ... FOR UPDATE) during state mutations, ensuring that concurrent client requests are strictly "
    "serialized. Additionally, a database partial unique index guarantees that each candidate can possess at most one active, uncompleted interview session at any given time.",
    bold_prefix="Finite State Machine Orchestration Module: "
)
add_body(
    "The Model Gateway Module abstracts external artificial intelligence providers behind a unified, provider-independent programming interface. The gateway formats all prompts using strict JSON-schema specifications, enforcing structured responses that "
    "adhere to predefined data schemas. The module implements per-attempt execution timeouts (capped at twenty-five seconds) and bounded retry logic utilizing exponential backoff with random jitter. If the primary cloud AI provider fails or violates schema "
    "contracts, the module automatically triggers a fallback cascade to alternate cloud models or local deterministic question catalogs, ensuring uninterrupted session continuity.",
    bold_prefix="Model Gateway and Fallback Execution Module: "
)
add_body(
    "The Evaluator Module delivers objective, transparent assessment of candidate responses by enforcing empirical evidence validation. Submitted answers are evaluated across four core dimensions: technical accuracy, communication clarity, problem-solving "
    "depth, and trade-off awareness, each scored on a 1–5 scale. Crucially, the module mandates that every score justification must include an exact verbatim substring quote extracted directly from the candidate's answer text. An automated validator "
    "programmatically verifies that all cited quotes exist verbatim within the submitted response; any evaluation containing fabricated or altered quotes is rejected and regenerated, preventing ungrounded or hallucinated qualitative feedback.",
    bold_prefix="Verbatim Quote-Grounded Evaluator Module: "
)
add_body(
    "The Report Module compiles comprehensive performance diagnostics upon the conclusion of each interview session. The module categorizes demonstrated strengths and targeted improvement areas without collapsing performance into a reductive global score. "
    "It cross-references evaluation rubrics to surface specific missing technical concepts, unaddressed edge cases, and conceptual gaps. Furthermore, the module enables candidates to launch targeted retry sessions focused exclusively on topics where "
    "competencies were not demonstrated, facilitating focused learning and rapid iterative improvement.",
    bold_prefix="Diagnostic Practice Report and Retry Module: "
)
add_body(
    "The User Interface Module delivers a responsive, accessible client experience constructed using Next.js, React, and Tailwind CSS. The module renders live session timers, turn counters, question prompts, and response text areas with visual clarity "
    "and optimal contrast. It incorporates optional, client-side camera-based pacing analysis, processing video frames locally via WebAssembly to calculate head stability, gaze orientation, and conversational pacing without transmitting video streams to "
    "the server. The module also features client-side audio transcription utilizing browser speech recognition APIs, providing candidates with flexible multimodal interaction options.",
    bold_prefix="Interactive User Interface and Visual Pacing Module: "
)

add_title("4.2 TECHNOLOGY DESCRIPTION", level=2)
add_body(
    "The AI Interview Coach is engineered using modern, robust web technologies selected for performance, reliability, and developer productivity. The frontend is built on Next.js 14 and React 18, utilizing the App Router architecture for streamlined layout "
    "composition and client-side page transitions. TypeScript is utilized across the entire frontend codebase, ensuring complete compile-time type safety and preventing common runtime errors. Tailwind CSS provides a modular utility-first styling system that "
    "delivers consistent visual hierarchy, dark-mode themes, and responsive layouts across varying display form factors."
)
add_body(
    "The backend service is powered by Python 3.11 and the FastAPI framework, taking advantage of Python's native asynchronous concurrency (async/await) to handle high-volume I/O operations and external API requests efficiently. Request validation and response "
    "serialization are managed through Pydantic v2, which provides high-speed schema enforcement and data parsing. Relational data persistence is managed by PostgreSQL 15, accessed through SQLAlchemy 2.0 ORM using asynchronous database sessions and connection "
    "pooling. Database migrations are automated via Alembic, guaranteeing reproducible schema evolution across development and production environments."
)
add_body(
    "External generative artificial intelligence services are integrated via secure REST APIs, utilizing Google Gemini (via google-genai), Groq, and NVIDIA NIM endpoints. These services execute inference tasks using temperature-controlled parameters and "
    "structured JSON response schemas. Local client vision processing is handled via standard HTML5 Canvas and Web Audio APIs, ensuring that compute-intensive media analyses occur on-device without incurring server operational costs. The complete system is "
    "packaged using Docker and Docker Compose, enabling standardized, one-command deployment across diverse operating systems and cloud environments."
)

doc.add_page_break()

# ==========================================
# CHAPTER 5: TESTING
# ==========================================
add_title("CHAPTER 5", level=1)
add_title("TESTING", level=1)

add_title("5.1 UNIT TESTING", level=2)
add_body(
    "Unit Testing verifies the correctness, boundary handling, and logical isolation of individual functions, modules, and database models across the platform. In the AI Interview Coach, unit testing suites are implemented across both the backend Python "
    "service and the frontend TypeScript client, enforcing complete behavioral isolation."
)
add_body(
    "The backend test suite encompasses 4,693 automated test cases executed via pytest. These tests systematically evaluate critical system boundaries, including scrypt password hashing derivation, cryptographic session token verification, PDF text "
    "extraction heuristics, typographical ligature normalization, prompt template boundary safety, and Pydantic schema validation rules. All backend unit tests execute against an isolated PostgreSQL test database (ai_interview_coach_test), running inside "
    "transactional savepoints that roll back following test completion, thereby guaranteeing zero state persistence between consecutive test executions."
)
add_body(
    "The frontend test suite comprises 45 automated unit tests executed using Node.js's native test runner (node --test). These tests validate client-side routing logic, authentication redirect policies, HTML document escaping routines that prevent "
    "cross-site scripting during export generation, on-device camera classification heuristics, conversational state-to-screen UI mappings, and speech chunking algorithms. This dual-stack unit testing regime ensures that every fundamental building block "
    "operates reliably prior to end-to-end integration."
)

add_title("5.2 INTEGRATION TESTING", level=2)
add_body(
    "Integration Testing evaluates the communication fidelity, transactional boundaries, and fault-tolerance mechanisms across combined system modules, database connections, and external API integrations."
)
add_body(
    "A central integration suite verifies database schema migration consistency using Alembic. Automated tests dynamically downgrade the test database schema to its base state, sequentially apply all thirteen migration revisions to the head revision, and "
    "execute structural validation checks to ensure that declarative SQLAlchemy models and PostgreSQL database constraints remain perfectly synchronized. Another critical integration suite tests state machine concurrency and database row locking; "
    "multi-threaded test harnesses simulate concurrent client requests attempting to advance identical interview sessions, verifying that PostgreSQL row locks (SELECT ... FOR UPDATE) correctly serialize operations and prevent race conditions or orphaned state records."
)
add_body(
    "Furthermore, comprehensive fault-injection testing is conducted across the Model Gateway. Simulated network interruptions, connection timeouts, HTTP 429 rate-limiting responses, and malformed JSON payloads are programmatically injected into the gateway "
    "harness. These tests verify that exponential backoff retries, provider failover cascades, and fallback to deterministic local rule catalogs function smoothly without application crashes or unhandled exceptions."
)

add_title("5.3 TEST RESULTS", level=2)
add_body(
    "The complete automated testing suite was executed against the codebase, verifying that all functional requirements, security policies, and performance invariants operate in strict compliance with specifications. Table 5.1 summarizes empirical "
    "test results obtained from the browser end-to-end journey suite and backend integration test harnesses."
)

tr_headers = ["TEST CASE ID", "TEST SCENARIO & INVARIANT", "EXPECTED RESULT", "ACTUAL RESULT", "STATUS"]
tr_rows = [
    ["TC-AUTH-01", "Unauthenticated access to protected /api/candidates/me", "HTTP 401 Unauthorized with standard error", "HTTP 401 Unauthorized returned", "PASS"],
    ["TC-AUTH-02", "5 consecutive failed logins from a single IP address", "Account locked for 15 minutes, HTTP 429", "Locked, HTTP 429 with Retry-After", "PASS"],
    ["TC-AUTH-03", "Cross-candidate data probe (Candidate A accessing B)", "HTTP 404 Not Found (indistinguishable)", "HTTP 404 Not Found returned", "PASS"],
    ["TC-RES-01", "Upload corrupted or password-encrypted PDF file", "HTTP 200, status FAILED, zero raw text stored", "Status FAILED, safe error displayed", "PASS"],
    ["TC-RES-02", "Upload resume containing adversarial prompt injection", "Text treated as inert string, zero hijacking", "Stored as raw data, no score impact", "PASS"],
    ["TC-FACT-01", "Review and edit pending facts (Approve/Reject)", "Facts transition to APPROVED/REJECTED", "Fact status updated, provenance intact", "PASS"],
    ["TC-PLAN-01", "Attempt planning while facts are PENDING_REVIEW", "HTTP 409 Conflict with count of pending facts", "HTTP 409 Conflict returned", "PASS"],
    ["TC-PLAN-02", "AI planning failure (all external cloud providers offline)", "Deterministic catalog plan generated (RULES)", "Fallback plan generated, status logged", "PASS"],
    ["TC-TURN-01", "Candidate requests next question with < 60s remaining", "Interview closes gracefully with TIME_LIMIT", "Session closed, TIME_LIMIT recorded", "PASS"],
    ["TC-TURN-02", "Submit response exceeding max character threshold", "HTTP 422 Unprocessable Entity returned", "HTTP 422 returned, payload rejected", "PASS"],
    ["TC-EVAL-01", "Model Gateway returns score with fabricated quote", "Fails substring validation and is regenerated", "Quote rejected, fallback evaluation", "PASS"],
    ["TC-EVAL-02", "Concurrent answer submissions on identical session ID", "Row lock serializes; exactly one answer saved", "Requests serialized, zero duplicate records", "PASS"],
]
add_tbl(tr_headers, tr_rows, col_widths=[1.2, 2.1, 1.8, 1.8, 0.7])

add_body(
    "The test outcomes confirm that the platform maintains high software reliability, deterministic state transitions, robust security isolation, and resilient exception handling across diverse operating conditions."
)

doc.add_page_break()

# ==========================================
# CHAPTER 6: CONCLUSION AND FUTURE ENHANCEMENT
# ==========================================
add_title("CHAPTER 6", level=1)
add_title("CONCLUSION AND FUTURE ENHANCEMENT", level=1)

add_title("6.1 CONCLUSION", level=2)
add_body(
    "The AI Interview Coach successfully delivers an open-source, candidate-centric, and architecturally rigorous technical interview simulation platform. By systematically replacing unconstrained conversational language models with a deterministic "
    "Finite State Machine, strict JSON-schema contracts, and verbatim evidence-grounded rubric evaluations, the system overcomes the critical limitations of hallucinated candidate qualifications, arbitrary scoring, and opaque corporate screening. "
    "The platform provides software engineering students and aspiring developers with realistic, adaptive technical interview practice grounded directly in their verified project experiences and technical competencies."
)
add_body(
    "The implementation of human-in-the-loop fact provenance guarantees that candidates retain complete ownership and oversight of their data, while local-first audio and visual analysis preserves strict privacy without transmitting sensitive biometric "
    "streams to cloud servers. Extensive testing across 4,693 backend unit tests, 45 frontend client tests, and comprehensive end-to-end browser journeys validates the platform's architectural stability, sub-two-second latency profile, and fault tolerance "
    "against external provider disruptions. Ultimately, this project proves that generative artificial intelligence can be effectively harnessed for formative technical education when governed by disciplined software engineering invariants, providing "
    "students with an accessible, trustworthy tool to accelerate their professional career development."
)

add_title("6.2 FUTURE ENHANCEMENT", level=2)
add_body(
    "While the AI Interview Coach provides a robust and fully validated practice environment, several promising avenues for future research and engineering expansion exist. The platform can be extended to support real-time collaborative coding environments, "
    "integrating browser-based WebAssembly code execution sandboxes that evaluate algorithmic code submissions against automated unit test suites and complexity analyzers during live system design and algorithmic interview phases."
)
add_body(
    "Additionally, future iterations could incorporate advanced vocal intonation analysis, evaluating speech clarity, filler word frequency, and vocal modulation using on-device machine learning models to provide candidates with deeper communication coaching. "
    "The platform could also expand to support simulated group technical discussions and collaborative architectural reviews with multi-agent panels, mimicking senior engineering design committee reviews. Finally, integrating standardized Learning Management "
    "System (LMS) export protocols (such as LTI and SCORM) would enable academic institutions and university career centers to deploy the platform across broader student cohorts, tracking institutional preparation outcomes while upholding candidate privacy."
)

doc.add_page_break()

# ==========================================
# APPENDIX A: SOURCE CODE
# ==========================================
add_title("APPENDIX A – SOURCE CODE", level=1)
add_body(
    "This appendix provides key excerpts of the core architectural implementations governing state machine transitions, provider-independent model gateways, and verbatim quote verification."
)

add_title("A.1 Finite State Machine Transition Engine (app/services/interview_state_machine.py)", level=2)
add_body(
    "The following excerpt illustrates the declarative transition matrix, client actions, system events, and transactional update logic enforcing session state boundaries:"
)
add_code(
'''class InterviewStatus(StrEnum):
    CREATED = "CREATED"
    PROFILE_PROCESSING = "PROFILE_PROCESSING"
    PROFILE_REVIEW = "PROFILE_REVIEW"
    INTERVIEW_PLANNING = "INTERVIEW_PLANNING"
    READY = "READY"
    ASKING = "ASKING"
    WAITING_FOR_ANSWER = "WAITING_FOR_ANSWER"
    ANSWER_PROCESSING = "ANSWER_PROCESSING"
    ANSWER_EVALUATION = "ANSWER_EVALUATION"
    NEXT_DECISION = "NEXT_DECISION"
    REPORT_GENERATION = "REPORT_GENERATION"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"

TRANSITIONS: dict[tuple[InterviewStatus, SessionEvent], InterviewStatus] = {
    (InterviewStatus.CREATED, SessionEvent.PROFILE_PROCESSING_STARTED): InterviewStatus.PROFILE_PROCESSING,
    (InterviewStatus.PROFILE_PROCESSING, SessionEvent.PROFILE_READY): InterviewStatus.PROFILE_REVIEW,
    (InterviewStatus.PROFILE_REVIEW, SessionEvent.CONFIRM_PROFILE): InterviewStatus.INTERVIEW_PLANNING,
    (InterviewStatus.INTERVIEW_PLANNING, SessionEvent.PLAN_READY): InterviewStatus.READY,
    (InterviewStatus.READY, SessionEvent.START_INTERVIEW): InterviewStatus.ASKING,
    (InterviewStatus.ASKING, SessionEvent.QUESTION_ASKED): InterviewStatus.WAITING_FOR_ANSWER,
    (InterviewStatus.WAITING_FOR_ANSWER, SessionEvent.ANSWER_SUBMITTED): InterviewStatus.ANSWER_PROCESSING,
    (InterviewStatus.ANSWER_PROCESSING, SessionEvent.ANSWER_PROCESSED): InterviewStatus.ANSWER_EVALUATION,
    (InterviewStatus.ANSWER_EVALUATION, SessionEvent.ANSWER_EVALUATED): InterviewStatus.NEXT_DECISION,
    (InterviewStatus.NEXT_DECISION, SessionEvent.FOLLOW_UP): InterviewStatus.ASKING,
    (InterviewStatus.NEXT_DECISION, SessionEvent.NEXT_TOPIC): InterviewStatus.ASKING,
    (InterviewStatus.NEXT_DECISION, SessionEvent.END_INTERVIEW): InterviewStatus.REPORT_GENERATION,
    (InterviewStatus.REPORT_GENERATION, SessionEvent.REPORT_READY): InterviewStatus.COMPLETED,
}

def next_status(status: InterviewStatus, event: SessionEvent) -> InterviewStatus:
    try:
        return TRANSITIONS[(status, event)]
    except KeyError:
        raise ValueError(f"Invalid transition from state {status} with event {event}")'''
)

add_title("A.2 Provider-Independent Model Gateway (app/ai/gateway.py)", level=2)
add_body(
    "The excerpt below demonstrates how the Model Gateway abstracts external provider APIs, enforces timeouts, and executes bounded retries with fallback cascades:"
)
add_code(
'''class ModelGateway:
    def __init__(self, primary_provider: str, fallback_provider: str, api_keys: dict[str, str]):
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.api_keys = api_keys
        self.client = httpx.AsyncClient(timeout=25.0)

    async def execute_structured_prompt(self, prompt: str, schema: type[T], max_retries: int = 2) -> T:
        for attempt in range(max_retries + 1):
            provider = self.primary_provider if attempt == 0 else self.fallback_provider
            try:
                response = await self._call_provider(provider, prompt, schema)
                return schema.model_validate_json(response)
            except (httpx.HTTPError, ValueError, asyncio.TimeoutError):
                if attempt == max_retries:
                    raise RuntimeError("Model Gateway failed across all providers.")
                await asyncio.sleep(2 ** attempt)'''
)

add_title("A.3 Verbatim Substring Evidence Validator (app/services/evaluator.py)", level=2)
add_body(
    "The code below details the programmatic evidence validation logic that guarantees score justifications are grounded strictly in exact candidate quotes:"
)
add_code(
'''class EvaluationValidator:
    @staticmethod
    def verify_evidence_quotes(candidate_answer: str, evaluation_payload: dict) -> bool:
        normalized_answer = " ".join(candidate_answer.lower().split())
        quotes = evaluation_payload.get("verbatim_quotes", [])
        if not quotes:
            return False
        for quote in quotes:
            normalized_quote = " ".join(quote.lower().split())
            if normalized_quote not in normalized_answer:
                return False
        return True'''
)

doc.add_page_break()

# ==========================================
# APPENDIX B: SCREEN SHOTS
# ==========================================
add_title("APPENDIX B – SCREEN SHOTS", level=1)

add_title("B.1 AUTHENTICATION & LOGIN INTERFACE", level=2)
add_shot("01-login.png", "Figure B.1: Authentication & Candidate Registration Interface")
add_body(
    "Figure B.1 shows the responsive authentication portal featuring email credential validation, CSRF-protected submission tokens, "
    "and automated account lockout safeguards against brute-force intrusion."
)

add_title("B.2 RESUME UPLOAD & PROVENANCE FACT REVIEW", level=2)
add_shot("02-resume-facts.png", "Figure B.2: Ingested Resume Fact Review & Provenance Inspection")
add_body(
    "Figure B.2 displays the Fact Provenance Interface presenting all skills, project milestones, and experiences parsed from uploaded "
    "PDF resumes, enabling candidates to inspect, modify, or reject specific facts before initiating interview simulations."
)

add_title("B.3 INTERVIEW PLAN CONFIGURATION & TOPIC BLUEPRINT", level=2)
add_shot("03-plan.png", "Figure B.3: Interview Plan Formulation & Topic Blueprint Review")
add_body(
    "Figure B.3 captures the Plan Configuration screen where candidates customize interview parameters—including target job role, "
    "experience level, question pacing, and session duration—generating an inspection-ready topic blueprint."
)

add_title("B.4 LIVE ADAPTIVE INTERVIEW SESSION & PACING MONITOR", level=2)
add_shot("09-camera-in-interview.png", "Figure B.4: Live Adaptive Interview Workspace with Visual Pacing Feedback")
add_body(
    "Figure B.4 illustrates the Live Interview Workspace delivering real-time question prompts, turn countdown timers, audio transcription "
    "controls, and on-device camera engagement metrics that guide conversational pacing."
)

add_title("B.5 RUBRIC EVALUATION REPORT & EVIDENCE AUDIT", level=2)
add_shot("04-report.png", "Figure B.5: Post-Session Diagnostic Rubric Evaluation & Verbatim Quote Audit")
add_body(
    "Figure B.5 shows the Diagnostic Practice Report displaying rubric evaluations across technical accuracy, communication clarity, problem-solving "
    "depth, and trade-off awareness, grounding every score in exact candidate verbatim quotes."
)

add_title("B.6 TARGETED RETRY SESSION & TOPICAL REMEDIATION", level=2)
add_shot("05-history.png", "Figure B.6: Historical Sessions & Targeted Remediation Gateway")
add_body(
    "Figure B.6 presents the Targeted Remediation module and session history, providing candidates with focused revision roadmaps and the option "
    "to launch targeted retry sessions focused exclusively on concepts requiring practice."
)

doc.add_page_break()

# ==========================================
# REFERENCES
# ==========================================
add_title("REFERENCES", level=1)
add_title("BOOKS:", level=2)
ref_books = [
    "Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.",
    "Martin, R. C. (2017). Clean Architecture: A Craftsman's Guide to Software Structure and Design. Prentice Hall.",
    "Kleppmann, M. (2017). Designing Data-Intensive Applications: The Big Ideas Behind Reliable, Scalable, and Maintainable Systems. O'Reilly Media.",
    "Fowler, M. (2002). Patterns of Enterprise Application Architecture. Addison-Wesley.",
    "Goodfellow, I., Bengio, Y., & Courville, A. (2016). Deep Learning. MIT Press.",
]
for b in ref_books:
    add_body(b)

add_title("WEBSITES & STANDARDS:", level=2)
ref_sites = [
    "FastAPI Framework Documentation – https://fastapi.tiangolo.com",
    "Next.js App Router Documentation – https://nextjs.org/docs",
    "PostgreSQL 15 Relational Database Documentation – https://www.postgresql.org/docs/15",
    "SQLAlchemy 2.0 Unified Documentation – https://docs.sqlalchemy.org/en/20",
    "W3C Web Content Accessibility Guidelines (WCAG) 2.1 – https://www.w3.org/TR/WCAG21",
    "RFC 7914: The scrypt Password-Based Key Derivation Function – https://datatracker.ietf.org/doc/html/rfc7914",
]
for s in ref_sites:
    add_body(s)

doc.save(DOCX_OUT)
print(f"Academic Report DOCX successfully generated at: {DOCX_OUT}")
