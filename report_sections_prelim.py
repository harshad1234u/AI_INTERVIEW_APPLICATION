"""Preliminary pages generator for AI Interview Coach Project Report.
Includes Cover Page, Title Page, Bonafide Certificate, Abstract, Acknowledgement,
Table of Contents, List of Figures, List of Tables, and List of Abbreviations.
"""

from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from make_academic_report import (
    doc, add_title, add_body, add_bullet, add_tbl, style_p,
    C_NAVY, C_DARK, C_MUTED
)

def build_preliminary_pages():
    # ==========================================
    # 1. COVER PAGE
    # ==========================================
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_inst, space_before=12, space_after=2)
    r1 = p_inst.add_run("K. RAMAKRISHNAN COLLEGE OF TECHNOLOGY\n")
    r1.font.name = "Times New Roman"
    r1.font.size = Pt(14)
    r1.bold = True
    r1.font.color.rgb = C_NAVY
    r2 = p_inst.add_run("(AUTONOMOUS)\nSAMAYAPURAM, TIRUCHIRAPPALLI – 621 112\n")
    r2.font.name = "Times New Roman"
    r2.font.size = Pt(11)
    r2.bold = True
    r3 = p_inst.add_run("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING\n\n")
    r3.font.name = "Times New Roman"
    r3.font.size = Pt(12)
    r3.bold = True

    # Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_title, space_before=36, space_after=18)
    r_t = p_title.add_run("AI INTERVIEW COACH:\nAN AUTOMATED MULTI-AGENT TECHNICAL INTERVIEW PRACTICE AND EVALUATION PLATFORM")
    r_t.font.name = "Times New Roman"
    r_t.font.size = Pt(18)
    r_t.bold = True
    r_t.font.color.rgb = C_NAVY

    # Subtitle
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_sub, space_before=12, space_after=24)
    r_s = p_sub.add_run("A PROJECT REPORT\n\nSubmitted by")
    r_s.font.name = "Times New Roman"
    r_s.font.size = Pt(12)
    r_s.bold = True

    # Student Names / Placeholders
    p_students = doc.add_paragraph()
    p_students.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_students, space_before=12, space_after=36)
    r_stu = p_students.add_run("JEYSHREE V\t\t2303811710422069\nMATHIARASI D\t\t2303811710422093\n")
    r_stu.font.name = "Times New Roman"
    r_stu.font.size = Pt(12)
    r_stu.bold = True

    # Degree details
    p_deg = doc.add_paragraph()
    p_deg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_deg, space_before=24, space_after=2)
    r_d1 = p_deg.add_run("in partial fulfillment of the requirements for the award degree of\n")
    r_d1.font.name = "Times New Roman"
    r_d1.font.size = Pt(11)
    r_d1.italic = True
    r_d2 = p_deg.add_run("Bachelor of Engineering\nin\nCOMPUTER SCIENCE AND ENGINEERING\n")
    r_d2.font.name = "Times New Roman"
    r_d2.font.size = Pt(12)
    r_d2.bold = True
    r_d3 = p_deg.add_run("CSB1303 – OBJECT ORIENTED ANALYSIS AND DESIGN\n\n")
    r_d3.font.name = "Times New Roman"
    r_d3.font.size = Pt(11)
    r_d3.bold = True

    p_date = doc.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_date, space_before=12, space_after=0)
    r_dt = p_date.add_run("NOVEMBER – 2026")
    r_dt.font.name = "Times New Roman"
    r_dt.font.size = Pt(12)
    r_dt.bold = True

    doc.add_page_break()

    # ==========================================
    # 2. TITLE PAGE (Exact institutional duplicate)
    # ==========================================
    p_tpage = doc.add_paragraph()
    p_tpage.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_tpage, space_before=12, space_after=2)
    r_t1 = p_tpage.add_run("AI INTERVIEW COACH:\nAN AUTOMATED MULTI-AGENT TECHNICAL INTERVIEW PRACTICE AND EVALUATION PLATFORM\n\n")
    r_t1.font.name = "Times New Roman"
    r_t1.font.size = Pt(16)
    r_t1.bold = True
    r_t1.font.color.rgb = C_NAVY

    r_t2 = p_tpage.add_run("A PROJECT REPORT\n\nSubmitted by\n\n")
    r_t2.font.name = "Times New Roman"
    r_t2.font.size = Pt(12)
    r_t2.bold = True

    r_t3 = p_tpage.add_run("JEYSHREE V\t\t2303811710422069\nMATHIARASI D\t\t2303811710422093\n\n")
    r_t3.font.name = "Times New Roman"
    r_t3.font.size = Pt(12)
    r_t3.bold = True

    r_t4 = p_tpage.add_run("in partial fulfillment of the requirements for the award degree of\nBachelor of Engineering\nin\nCOMPUTER SCIENCE AND ENGINEERING\nCSB1303 – OBJECT ORIENTED ANALYSIS AND DESIGN\n\n")
    r_t4.font.name = "Times New Roman"
    r_t4.font.size = Pt(11)

    r_t5 = p_tpage.add_run("DEPARTMENT OF COMPUTER SCIENCE AND ENGINEERING\nK. RAMAKRISHNAN COLLEGE OF TECHNOLOGY (AUTONOMOUS)\nSAMAYAPURAM, TIRUCHIRAPPALLI – 621 112\n\nNOVEMBER – 2026")
    r_t5.font.name = "Times New Roman"
    r_t5.font.size = Pt(11)
    r_t5.bold = True

    doc.add_page_break()

    # ==========================================
    # 3. BONAFIDE CERTIFICATE
    # ==========================================
    p_cert_hdr = doc.add_paragraph()
    p_cert_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_p(p_cert_hdr, space_before=12, space_after=18)
    r_ch1 = p_cert_hdr.add_run("K. RAMAKRISHNAN COLLEGE OF TECHNOLOGY (AUTONOMOUS)\nSAMAYAPURAM – 621 112\n\n")
    r_ch1.font.name = "Times New Roman"
    r_ch1.font.size = Pt(12)
    r_ch1.bold = True
    r_ch2 = p_cert_hdr.add_run("BONAFIDE CERTIFICATE")
    r_ch2.font.name = "Times New Roman"
    r_ch2.font.size = Pt(14)
    r_ch2.bold = True
    r_ch2.font.color.rgb = C_NAVY

    p_cert_body = doc.add_paragraph()
    style_p(p_cert_body, space_before=12, space_after=24, line_spacing=1.3)
    r_cb = p_cert_body.add_run(
        "The work embodied in the present project report entitled “AI INTERVIEW COACH: AN AUTOMATED MULTI-AGENT "
        "TECHNICAL INTERVIEW PRACTICE AND EVALUATION PLATFORM” has been carried out by the students JEYSHREE V (2303811710422069) "
        "and MATHIARASI D (2303811710422093). The work reported herein is original and we declare that the project is "
        "their own work, except where specifically acknowledged, and has not been copied from other sources or been "
        "previously submitted for any other degree or diploma examination."
    )
    r_cb.font.name = "Times New Roman"
    r_cb.font.size = Pt(11.5)

    p_viva = doc.add_paragraph()
    style_p(p_viva, space_before=12, space_after=36)
    r_v = p_viva.add_run("Date of Viva Voce: ……………………")
    r_v.font.name = "Times New Roman"
    r_v.font.size = Pt(11)
    r_v.bold = True

    # Signature Table
    sig_headers = ["SUPERVISOR", "HEAD OF THE DEPARTMENT"]
    sig_rows = [
        [
            "Mrs. S. GAYATHRI M.E.,\nSUPERVISOR\nAssistant Professor\nDepartment of CSE\nK. Ramakrishnan College of Technology\nSamayapuram – 621 112.",
            "Mr. R. RAJAVARMAN M.E., (Ph.D.,)\nHEAD OF THE DEPARTMENT\nAssistant Professor (Sr. Grade)\nDepartment of CSE\nK. Ramakrishnan College of Technology\nSamayapuram – 621 112."
        ]
    ]
    add_tbl(sig_headers, sig_rows, col_widths=[3.0, 3.0])

    p_exam = doc.add_paragraph()
    style_p(p_exam, space_before=36, space_after=0)
    p_exam.add_run("INTERNAL EXAMINER\t\t\t\t\tEXTERNAL EXAMINER").font.name = "Times New Roman"
    p_exam.runs[0].font.size = Pt(11)
    p_exam.runs[0].bold = True

    doc.add_page_break()

    # ==========================================
    # 4. ABSTRACT
    # ==========================================
    add_title("ABSTRACT", level=1)
    
    add_body(
        "The AI Interview Coach is an intelligent, resume-aware, adaptive technical interview practice and coaching "
        "platform designed specifically for undergraduate students and entry-level software engineering candidates. Unlike commercial "
        "automated recruitment tools that function as opaque screening mechanisms to filter applicants, this system is architected strictly "
        "as a private, formative coaching instrument. The platform bridges the gap between static algorithmic question repositories "
        "and expensive human mock interviews by providing dynamic, personalized technical interview simulations grounded verifiably "
        "in the candidate's self-reported background."
    )
    add_body(
        "The platform is engineered around an architectural invariant: 'The LLM proposes, the orchestrator decides, the validator "
        "verifies, and the database stores.' A four-tier multi-agent pipeline—comprising a ProfileAgent, PlannerAgent, "
        "InterviewerAgent, and EvaluatorAgent—operates through a unified, provider-independent Model Gateway supporting Google Gemini, "
        "Groq Cloud, and NVIDIA NIM. The Model Gateway enforces strict JSON schemas, bounded exponential backoff, per-call deadlines, "
        "and automatic provider fallback. Crucially, the system remains fully operational via deterministic fallback rule catalogs "
        "whenever AI consent is withheld, credentials are unconfigured, network latency spikes, or token quotas expire."
    )
    add_body(
        "Candidate data isolation is maintained across all layers: resume parsing extracts verbatim text heuristics with mandatory "
        "human-in-the-loop fact review before context ingestion. A finite state machine (FSM) implemented in PostgreSQL locks sessions "
        "and regulates turn pacing. Post-interview rubric evaluations assess four core technical competencies against concrete 1–5 anchors, "
        "requiring verbatim quotation evidence from student answers without ever aggregating scores into misleading single-score rankings. "
        "The platform also integrates optional, privacy-preserving, on-device facial-expression signal observation using client-side "
        "TensorFlow.js (face-api.js), ensuring raw video frames never leave the browser. Comprehensive automated test suites "
        "(4,693 backend unit and integration tests, 45 frontend TypeScript tests, and 37 browser journey checks) demonstrate robust "
        "fault tolerance, deterministic execution, and zero prompt-injection vulnerability."
    )
    
    p_kw = doc.add_paragraph()
    style_p(p_kw, space_before=12, space_after=12)
    r_kwh = p_kw.add_run("Keywords: ")
    r_kwh.font.name = "Times New Roman"
    r_kwh.bold = True
    r_kwh.font.size = Pt(10.5)
    r_kw = p_kw.add_run(
        "Technical Interview Simulation, Multi-Agent Architecture, Model Gateway, Finite State Machine, "
        "Rubric-Based Evaluation, Resume Parsing, Prompt Injection Defense, Formative Coaching, FastAPI, Next.js, "
        "PostgreSQL, Object-Oriented Analysis and Design (OOAD), UML."
    )
    r_kw.font.name = "Times New Roman"
    r_kw.font.size = Pt(10.5)

    doc.add_page_break()

    # ==========================================
    # 5. ACKNOWLEDGEMENT
    # ==========================================
    add_title("ACKNOWLEDGEMENT", level=1)
    
    add_body(
        "We express our sincere gratitude and deep sense of indebtedness to our esteemed Principal, Dr. N. Vasudevan, "
        "for providing excellent infrastructural facilities, technical resources, and continuous encouragement throughout "
        "the tenure of our academic curriculum."
    )
    add_body(
        "We extend our profound thanks to Mr. R. Rajavarman M.E., (Ph.D.,), Head of the Department and Assistant Professor "
        "(Sr. Grade), Department of Computer Science and Engineering, for his constant support, valuable guidance, and "
        "constructive suggestions during the progress of this project."
    )
    add_body(
        "We wish to record our deep sense of gratitude and heartfelt thanks to our Project Supervisor and Coordinator, "
        "Mrs. S. Gayathri M.E., Assistant Professor, Department of Computer Science and Engineering, for her keen interest, "
        "insightful advice, rigorous technical reviews, and constant inspiration from the inception of this system design "
        "to its successful fruition."
    )
    add_body(
        "We also convey our appreciation to all the faculty members and technical staff of the Department of Computer Science "
        "and Engineering, K. Ramakrishnan College of Technology, Samayapuram, for their cooperation and assistance."
    )
    add_body(
        "Finally, we express our heartfelt thanks to our parents, family members, and friends for their enduring moral support, "
        "patience, and motivation throughout the course of this work."
    )

    doc.add_page_break()

    # ==========================================
    # 6. TABLE OF CONTENTS
    # ==========================================
    add_title("TABLE OF CONTENTS", level=1)
    
    toc_headers = ["CHAPTER", "TITLE", "PAGE NO."]
    toc_rows = [
        ["", "ABSTRACT", "iii"],
        ["", "LIST OF FIGURES", "vii"],
        ["", "LIST OF TABLES", "viii"],
        ["", "LIST OF ABBREVIATIONS", "ix"],
        ["1", "INTRODUCTION", "1"],
        ["", "1.1 INTRODUCTION ABOUT DOMAIN", "1"],
        ["", "1.2 PROBLEM DESCRIPTION", "2"],
        ["", "1.3 OBJECTIVE OF THE PROJECT", "3"],
        ["", "1.4 SCOPE OF THE PROJECT", "4"],
        ["2", "SYSTEM REQUIREMENT SPECIFICATION (SRS)", "6"],
        ["", "2.1 FUNCTIONAL REQUIREMENTS", "6"],
        ["", "2.2 NON-FUNCTIONAL REQUIREMENTS", "10"],
        ["", "2.3 HARDWARE REQUIREMENTS", "13"],
        ["", "2.4 SOFTWARE REQUIREMENTS", "14"],
        ["", "2.5 USER CHARACTERISTICS", "15"],
        ["", "2.6 CONSTRAINTS", "16"],
        ["3", "ANALYSIS AND DESIGN", "18"],
        ["", "3.1 USE CASE DIAGRAM", "18"],
        ["", "3.2 CLASS DIAGRAM", "21"],
        ["", "3.3 ACTIVITY DIAGRAM", "24"],
        ["", "3.4 SEQUENCE DIAGRAM", "27"],
        ["", "3.5 STATE MACHINE DIAGRAM", "30"],
        ["", "3.6 COMMUNICATION DIAGRAM", "33"],
        ["", "3.7 COMPONENT DIAGRAM", "36"],
        ["", "3.8 DEPLOYMENT DIAGRAM", "39"],
        ["", "3.9 PACKAGE DIAGRAM", "42"],
        ["", "3.10 DESIGN PATTERNS USED", "44"],
        ["4", "IMPLEMENTATION", "47"],
        ["", "4.1 MODULE DESCRIPTION", "47"],
        ["", "4.2 TECHNOLOGY DESCRIPTION", "58"],
        ["5", "TESTING", "62"],
        ["", "5.1 UNIT TESTING", "62"],
        ["", "5.2 INTEGRATION TESTING", "65"],
        ["", "5.3 TEST RESULTS", "68"],
        ["6", "CONCLUSION AND FUTURE ENHANCEMENT", "74"],
        ["", "6.1 CONCLUSION", "74"],
        ["", "6.2 FUTURE ENHANCEMENT", "75"],
        ["", "APPENDIX A – SOURCE CODE", "77"],
        ["", "APPENDIX B – SCREEN SHOTS", "93"],
        ["", "REFERENCES", "101"],
    ]
    add_tbl(toc_headers, toc_rows, col_widths=[1.0, 4.5, 0.9])

    doc.add_page_break()

    # ==========================================
    # 7. LIST OF FIGURES
    # ==========================================
    add_title("LIST OF FIGURES", level=1)
    
    fig_headers = ["FIGURE NO.", "TITLE", "PAGE NO."]
    fig_rows = [
        ["3.1", "USE CASE DIAGRAM", "19"],
        ["3.2", "DOMAIN AND SYSTEM CLASS DIAGRAM", "22"],
        ["3.3", "END-TO-END ACTIVITY DIAGRAM", "25"],
        ["3.4", "INTERACTIVE TURN SEQUENCE DIAGRAM", "28"],
        ["3.5", "INTERVIEW SESSION STATE MACHINE DIAGRAM", "31"],
        ["3.6", "TURN PROCESSING COMMUNICATION DIAGRAM", "34"],
        ["3.7", "ARCHITECTURAL COMPONENT DIAGRAM", "37"],
        ["3.8", "PHYSICAL DEPLOYMENT DIAGRAM", "40"],
        ["3.9", "SYSTEM PACKAGE DECOMPOSITION DIAGRAM", "43"],
        ["B.1", "AUTHENTICATION AND SIGN-IN INTERFACE", "93"],
        ["B.2", "RESUME UPLOAD AND FACT REVIEW DASHBOARD", "94"],
        ["B.3", "INTERVIEW CONFIGURATION AND PLANNING SCREEN", "95"],
        ["B.4", "ACTIVE INTERVIEW TURN AND RESPONSE PACING", "96"],
        ["B.5", "CAMERA OBSERVATION SIGNAL PANEL", "97"],
        ["B.6", "PRACTICE REPORT AND NON-AGGREGATED FEEDBACK", "98"],
        ["B.7", "INTERVIEW ATTEMPT HISTORY AND RETRY LINK", "99"],
        ["B.8", "RESPONSIVE MOBILE VIEW OF CANDIDATE REPORT", "100"],
    ]
    add_tbl(fig_headers, fig_rows, col_widths=[1.2, 4.3, 0.9])

    doc.add_page_break()

    # ==========================================
    # 8. LIST OF TABLES
    # ==========================================
    add_title("LIST OF TABLES", level=1)
    
    tbl_headers = ["TABLE NO.", "TITLE", "PAGE NO."]
    tbl_rows = [
        ["2.1", "FUNCTIONAL REQUIREMENTS SPECIFICATION", "7"],
        ["2.2", "NON-FUNCTIONAL SYSTEM ATTRIBUTES", "11"],
        ["2.3", "HARDWARE CONFIGURATION SPECIFICATIONS", "13"],
        ["2.4", "SOFTWARE ENVIRONMENT AND RUNTIME DEPENDENCIES", "14"],
        ["4.1", "RELATIONAL SCHEMA ENTITIES AND CONSTRAINTS", "49"],
        ["4.2", "MODEL GATEWAY PROVIDER BENCHMARKS AND METRICS", "52"],
        ["4.3", "SYSTEM API ENDPOINTS AND AUTHORIZATION MATRIX", "56"],
        ["5.1", "AUTOMATED TEST SUITE COVERAGE BREAKDOWN", "63"],
        ["5.2", "CORE INTEGRATION AND FAULT-INJECTION SUITE", "66"],
        ["5.3", "END-TO-END SYSTEM VALIDATION TEST RESULTS", "69"],
    ]
    add_tbl(tbl_headers, tbl_rows, col_widths=[1.2, 4.3, 0.9])

    doc.add_page_break()

    # ==========================================
    # 9. LIST OF ABBREVIATIONS
    # ==========================================
    add_title("LIST OF ABBREVIATIONS", level=1)
    
    abbr_headers = ["ABBREVIATION", "EXPANSION / MEANING"]
    abbr_rows = [
        ["AI", "Artificial Intelligence"],
        ["API", "Application Programming Interface"],
        ["ASGI", "Asynchronous Server Gateway Interface"],
        ["CDP", "Chrome DevTools Protocol"],
        ["CORS", "Cross-Origin Resource Sharing"],
        ["CSRF", "Cross-Site Request Forgery"],
        ["CSV", "Comma-Separated Values"],
        ["DAO", "Data Access Object"],
        ["DB", "Database"],
        ["DOM", "Document Object Model"],
        ["E2E", "End-to-End Testing"],
        ["FK", "Foreign Key"],
        ["FSM", "Finite State Machine"],
        ["GoF", "Gang of Four (Software Design Patterns)"],
        ["GQL", "Graph Query Language"],
        ["GRASP", "General Responsibility Assignment Software Patterns"],
        ["HTML", "HyperText Markup Language"],
        ["HTTP", "Hypertext Transfer Protocol"],
        ["HTTPS", "Hypertext Transfer Protocol Secure"],
        ["JSON", "JavaScript Object Notation"],
        ["JSONB", "Binary JavaScript Object Notation (PostgreSQL)"],
        ["LLM", "Large Language Model"],
        ["ML", "Machine Learning"],
        ["MVC", "Model–View–Controller"],
        ["NFKC", "Unicode Normalization Form KC (Compatibility Decomposition)"],
        ["NIM", "NVIDIA Inference Microservice"],
        ["OCR", "Optical Character Recognition"],
        ["OOAD", "Object-Oriented Analysis and Design"],
        ["ORM", "Object-Relational Mapping"],
        ["PDF", "Portable Document Format"],
        ["PK", "Primary Key"],
        ["PRD", "Product Requirements Document"],
        ["RAM", "Random Access Memory"],
        ["REST", "Representational State Transfer"],
        ["RLS", "Row Level Security"],
        ["SHA", "Secure Hash Algorithm"],
        ["SPA", "Single Page Application"],
        ["SRS", "System Requirement Specification"],
        ["UI", "User Interface"],
        ["UML", "Unified Modeling Language"],
        ["UUID", "Universally Unique Identifier"],
        ["WASM", "WebAssembly"],
        ["WebGL", "Web Graphics Library"],
    ]
    add_tbl(abbr_headers, abbr_rows, col_widths=[1.8, 4.6])

    doc.add_page_break()
    print("Preliminary pages built successfully.")

if __name__ == "__main__":
    build_preliminary_pages()
    doc.save(DOCX_OUT)
    print("Saved preview to DOCX.")
