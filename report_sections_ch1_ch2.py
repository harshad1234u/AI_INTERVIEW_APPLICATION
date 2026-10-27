"""Chapter 1 (Introduction) and Chapter 2 (SRS) generator for AI Interview Coach.
"""

from docx.shared import Inches, Pt, RGBColor
from make_academic_report import (
    doc, add_title, add_body, add_bullet, add_tbl, style_p,
    C_NAVY, C_DARK, C_MUTED
)

def build_ch1_introduction():
    add_title("CHAPTER 1", level=1)
    add_title("INTRODUCTION", level=1)

    # 1.1 Introduction about Domain
    add_title("1.1 INTRODUCTION ABOUT DOMAIN", level=2)
    add_body(
        "In the contemporary software engineering landscape, securing internships and entry-level positions requires "
        "candidates to navigate rigorous, multi-stage technical interviews. These evaluations assess not only theoretical computer "
        "science fundamentals—such as algorithms, data structures, and database query optimization—but also practical system design "
        "trade-offs, behavioral competencies, and the ability to articulate architectural decisions made during past project work. "
        "For undergraduate students and fresh graduates, the transition from academic coursework to high-stakes technical interviews "
        "represents a daunting hurdle. Traditional preparation methods, such as practicing on static coding platforms (e.g., LeetCode, "
        "HackerRank) or reviewing textbook question banks, suffer from severe limitations: they lack conversational interactivity, fail "
        "to contextualize questions around the candidate's actual resume, and provide no qualitative, conversational feedback on how "
        "technical reasoning is communicated."
    )
    add_body(
        "With the rapid advancements in Large Language Models (LLMs) and conversational artificial intelligence, generative AI has "
        "emerged as a transformative paradigm for educational simulations and personalized tutoring. However, applying generative "
        "models to technical interview coaching introduces profound engineering challenges. General-purpose conversational chatbots "
        "frequently hallucinate candidate qualifications, ask repetitive or unstructured questions, struggle to maintain realistic "
        "interview pacing, and provide sycophantic or arbitrary numerical scores. Conversely, commercial 'AI hiring' platforms are "
        "optimized for corporate recruiter screening—ranking, scoring, and filtering out candidates using opaque models that raise "
        "significant privacy and ethical concerns."
    )
    add_body(
        "There is an urgent academic and practical necessity for an open, candidate-centric interview practice platform that combines "
        "the conversational adaptability of LLMs with deterministic software engineering rigor. Such a system must function as a "
        "formative coaching tool rather than an evaluative gatekeeper, enforcing strict privacy boundaries, deterministic lifecycle "
        "orchestration, and fact-grounded interview personalization."
    )

    # 1.2 Problem Description
    add_title("1.2 PROBLEM DESCRIPTION", level=2)
    add_body(
        "Candidates preparing for software development interviews face three primary impediments in existing preparation paradigms:"
    )
    add_bullet(
        " Static, non-interactive question repositories fail to simulate the dynamic back-and-forth of a live technical interview. "
        "They cannot probe deeper into a candidate's specific implementation decisions, clarify ambiguous statements, or evaluate "
        "communication clarity under realistic interview time constraints.",
        bold_prefix="Lack of Adaptive, Contextual Dialogue:"
    )
    add_bullet(
        " When unconstrained generative AI tools are used for practice, they tend to fabricate candidate experiences (e.g., assuming "
        "the candidate has mastered distributed caching when their resume only mentions basic SQL). Furthermore, prompt-injection attacks "
        "or adversarial inputs within resumes can hijack the model's instructions, resulting in arbitrary evaluation behavior.",
        bold_prefix="Hallucination and Ungrounded Inquiries:"
    )
    add_bullet(
        " Commercial automated interviewing platforms often record high-resolution video and audio, transmitting sensitive biometric "
        "and personal data to third-party cloud servers. Many claim to assess 'employability' or 'confidence' through opaque emotion-recognition "
        "algorithms, creating high anxiety and algorithmic bias without offering actionable educational feedback.",
        bold_prefix="Intrusive Surveillance and Flawed Assessment:"
    )
    add_body(
        "To address these critical shortcomings, there is a distinct requirement for an intelligent coaching platform that isolates "
        "candidate data, extracts verifiable facts from resumes with explicit candidate approval, enforces deterministic interview pacing "
        "and time limits, validates all model proposals against strict schemas, and offers rubric-grounded feedback backed exclusively "
        "by verbatim quote evidence."
    )

    # 1.3 Objective of the Project
    add_title("1.3 OBJECTIVE OF THE PROJECT", level=2)
    add_body(
        "The primary objective of this project is to architect, develop, and empirically validate the AI Interview Coach—a "
        "resume-aware, adaptive technical interview practice platform for students and entry-level software developers. The specific "
        "technical objectives include:"
    )
    add_bullet(
        "To design and implement a secure, multi-tenant candidate management subsystem featuring scrypt password hashing, "
        "cryptographic session token generation stored in HttpOnly cookies, and strict candidate ownership isolation across all database entities."
    )
    add_bullet(
        "To develop a deterministic, rule-based resume parsing engine capable of extracting verbatim skills, projects, experience, "
        "and education facts from multi-page PDFs, coupled with a human-in-the-loop review workflow that treats all unapproved facts as untrusted data."
    )
    add_bullet(
        "To engineer a provider-independent Model Gateway that interfaces with state-of-the-art LLMs (Gemini, Groq, NVIDIA) over "
        "standardized JSON-schema protocols, incorporating bounded retries, per-attempt timeouts, and automatic fallback cascades."
    )
    add_bullet(
        "To construct a deterministic Finite State Machine (FSM) in PostgreSQL that controls session lifecycles, turn deadlines, "
        "and transitions, strictly adhering to the architectural invariant: 'LLM proposes, orchestrator decides, validator verifies, database stores'."
    )
    add_bullet(
        "To establish a rubric-based evaluation engine that scores answers against four objective technical criteria (1–5 scale), "
        "mandating exact verbatim quotes as evidence and explicitly prohibiting aggregated single-score rankings."
    )
    add_bullet(
        "To implement privacy-preserving, on-device facial-expression signal observation using client-side WebGL/TensorFlow.js, "
        "transmitting only aggregate categorical sample counts and decoupling observations entirely from technical scoring."
    )
    add_bullet(
        "To provide client-side document generation enabling candidates to export clean, self-contained HTML/PDF interview plans "
        "and practice reports with zero server-side tracking."
    )

    # 1.4 Scope of the Project
    add_title("1.4 SCOPE OF THE PROJECT", level=2)
    add_body(
        "The scope of this project encompasses the end-to-end design, implementation, and automated verification of the AI Interview Coach "
        "system, covering both the Next.js frontend client and the FastAPI backend service:"
    )
    add_bullet("Target Role Specialization: Exclusively tailored for Software Developer Intern and Entry-Level Developer positions.")
    add_bullet("Interview Competencies Covered: Programming fundamentals, data structures and algorithms, database management systems, web development architectures, project understanding, and behavioral teamwork.")
    add_bullet("Interview Operational Modes: Technical, Behavioral, Project Deep Dive, and Mixed comprehensive assessment.")
    add_bullet("Deterministic Rule Fallbacks: Complete functional capability maintained via deterministic catalogs even when external AI providers are offline, unconfigured, or rate-limited.")
    add_bullet("Client-Side On-Device Processing: Expression observation occurs entirely within the candidate's browser runtime; raw audio and camera frames are never transmitted, recorded, or permanently stored.")
    add_body(
        "Explicit Exclusions from Scope:", bold_prefix="Scope Delimitations: "
    )
    add_body(
        "This platform is strictly an educational coaching tool. It does not provide recruitment decisions, hiring recommendations, "
        "candidate ranking algorithms, or automated job matching. It does not perform Optical Character Recognition (OCR) on scanned image PDFs, "
        "nor does it support voice transcription on the server side (all voice inputs utilize browser-native SpeechRecognition APIs and "
        "are reviewed as text prior to submission)."
    )

    doc.add_page_break()

def build_ch2_srs():
    add_title("CHAPTER 2", level=1)
    add_title("SYSTEM REQUIREMENT SPECIFICATION (SRS)", level=1)

    # 2.1 Functional Requirements
    add_title("2.1 FUNCTIONAL REQUIREMENTS", level=2)
    add_body(
        "The functional requirements delineate the core services, behavioral workflows, and operational capabilities "
        "implemented within the AI Interview Coach platform. Table 2.1 specifies the functional requirements hierarchy."
    )

    fr_headers = ["REQ ID", "REQUIREMENT NAME", "MODULE", "OPERATIONAL DESCRIPTION"]
    fr_rows = [
        ["FR-01", "Candidate Registration & Auth", "Auth", "Secure registration, scrypt password hashing, HttpOnly session cookie creation."],
        ["FR-02", "Session Management & CSRF", "Auth / Security", "Absolute 7-day session expiry, Origin header verification on state-changing requests."],
        ["FR-03", "Manual Profile Facts Entry", "Profile", "Manual creation, editing, and deletion of up to 100 candidate facts with duplicate detection."],
        ["FR-04", "Verbatim Resume PDF Parsing", "Resume Extractor", "Deterministic parsing of text-based PDFs (<=10 pages), extracting verbatim section facts."],
        ["FR-05", "Human-in-the-Loop Fact Review", "Profile / Review", "Gating mechanism requiring candidate to Approve, Reject, or Edit extracted facts."],
        ["FR-06", "AI Profile Extraction", "ProfileAgent", "Opt-in LLM fact extraction with strict verbatim grounding against resume text."],
        ["FR-07", "Session Creation & Locking", "State Machine", "Enforcement of at most one active interview session per candidate via row lock."],
        ["FR-08", "AI Consent Management", "Consent Engine", "Explicit per-session AI consent toggle; revocation discards pending AI proposals."],
        ["FR-09", "Interview Planning Engine", "PlannerAgent", "Deterministic catalog or AI-assisted topic structuring covering required competencies."],
        ["FR-10", "Turn Execution & Pacing", "Interviewer", "Deterministic action selection (Topic, Follow-up, Rephrase, Finish) with 60s deadline guard."],
        ["FR-11", "Answer Submission & Checks", "Interviewer", "Answer storage under NOT_EVALUATED status; enforcement of 10,000-character upper bound."],
        ["FR-12", "Rubric Evaluation Engine", "EvaluatorAgent", "Criterion scoring (1–5) based strictly on exact substring evidence quotes from student answers."],
        ["FR-13", "Deterministic Practice Report", "Report Engine", "Report generation without aggregated scores; highlights clear strengths and areas to practice."],
        ["FR-14", "Targeted Retry Session", "Retry Service", "Creation of fresh interview session copying only topics marked 'to practise'."],
        ["FR-15", "On-Device Expression Signals", "Camera Subsystem", "Client-side face-api.js expression sampling; transmits aggregate categorical counts only."],
    ]
    add_tbl(fr_headers, fr_rows, col_widths=[0.9, 1.8, 1.3, 2.8])

    # 2.2 Non-Functional Requirements
    add_title("2.2 NON-FUNCTIONAL REQUIREMENTS", level=2)
    add_body(
        "Non-functional requirements define the architectural quality attributes, performance constraints, and privacy boundaries "
        "enforced across the software stack. Table 2.2 summarizes these constraints."
    )

    nfr_headers = ["ATTRIBUTE", "SPECIFICATION", "ENFORCEMENT MECHANISM"]
    nfr_rows = [
        ["Usability", "WCAG 2.1 AA Compliant UI", "High contrast light/dark mode, accessible focus rings, reduced motion support."],
        ["Performance", "Interactive Turn Response < 2s", "Deterministic rule fallbacks; per-attempt 20s AI timeout with bounded retry."],
        ["Security", "Zero Credential / Token Leaks", "scrypt hashing (N=16384, r=8, p=5); SecretStr API keys; scrubbed stderr logging."],
        ["Data Isolation", "Multi-Tenant Candidate Privacy", "Composite foreign keys; row-level query filtering; foreign resource probes return 404."],
        ["Reliability", "Deterministic Fault Tolerance", "Automated provider fallback (Gemini -> Groq -> NVIDIA -> RULES Catalog)."],
        ["Scalability", "Atomic Usage & Rate Limits", "PostgreSQL atomic upserts with fixed UTC windows; network and candidate budgets."],
        ["Privacy", "Zero Video / Audio Transmission", "Client-side WebGL face-api.js; Web Speech API recognition; plain text submissions."],
    ]
    add_tbl(nfr_headers, nfr_rows, col_widths=[1.3, 2.2, 3.3])

    # 2.3 Hardware Requirements
    add_title("2.3 HARDWARE REQUIREMENTS", level=2)
    add_body(
        "The platform is architected to operate efficiently on standard computing hardware for both host deployment "
        "and client browser execution, as outlined in Table 2.3."
    )

    hw_headers = ["SUBSYSTEM", "COMPONENT", "MINIMUM SPECIFICATION", "RECOMMENDED SPECIFICATION"]
    hw_rows = [
        ["Host Server", "CPU Processor", "Dual-Core x86_64 / ARM64, 2.0 GHz", "Quad-Core Intel Xeon / AMD EPYC, 3.2 GHz"],
        ["Host Server", "System Memory", "2 GB RAM Available", "8 GB RAM (Optimized Connection Pool)"],
        ["Host Server", "Disk Storage", "2 GB Free SSD Storage", "20 GB High-Throughput NVMe SSD"],
        ["Candidate Client", "Processor", "1.5 GHz Dual-Core CPU", "2.4 GHz Quad-Core with WebGL Acceleration"],
        ["Candidate Client", "Client RAM", "2 GB System RAM", "4 GB RAM (Smooth Local Model Inference)"],
        ["Candidate Client", "Peripherals", "Standard Keyboard / Display", "HD Webcam (720p) & Microphone (Optional)"],
    ]
    add_tbl(hw_headers, hw_rows, col_widths=[1.2, 1.4, 2.1, 2.1])

    # 2.4 Software Requirements
    add_title("2.4 SOFTWARE REQUIREMENTS", level=2)
    add_body(
        "The software stack leverages modern, type-safe open-source runtimes and frameworks, detailed in Table 2.4."
    )

    sw_headers = ["TIER / SUBSYSTEM", "TECHNOLOGY / LIBRARY", "VERSION", "OPERATIONAL ROLE"]
    sw_rows = [
        ["Backend Runtime", "Python", "3.11.9+", "Core asynchronous application runtime environment."],
        ["Backend Framework", "FastAPI / Starlette", "0.141.1 / 1.7.0", "Asynchronous ASGI REST API service layer."],
        ["Database Engine", "PostgreSQL", "14.0+ (17.x tested)", "Relational persistence with JSONB and UUID generation."],
        ["Database ORM", "SQLAlchemy / Alembic", "2.1.1 / 1.20.0", "Type-annotated declarative ORM and migration pipeline."],
        ["Data Validation", "Pydantic / Settings", "2.13.5 / 2.15.0", "Strict schema validation and typed environment config."],
        ["PDF Processing", "pypdf", "6.19.0", "Pure-Python in-memory PDF text and structure parser."],
        ["Frontend Runtime", "Node.js / npm", "20.x / 22.x LTS", "JavaScript build environment and test execution."],
        ["Frontend Framework", "Next.js / React", "15.x / 19.x", "App Router Single Page Application with SSR capabilities."],
        ["Client-Side ML", "@vladmandic/face-api", "1.7.15", "In-browser lightweight face detector and expression network."],
        ["Testing & Quality", "pytest / anyio", "9.1.1 / 4.15.1", "Automated backend unit and integration test runner."],
    ]
    add_tbl(sw_headers, sw_rows, col_widths=[1.5, 1.8, 1.2, 2.3])

    # 2.5 User Characteristics
    add_title("2.5 USER CHARACTERISTICS", level=2)
    add_body(
        "The primary end users of the AI Interview Coach are undergraduate engineering students, recent computer science "
        "graduates, and junior software developers preparing for internship or full-time placement drives. Users are assumed to possess "
        "basic familiarity with standard web browsers, resume creation tools, and technical software concepts. No background in artificial "
        "intelligence, prompt engineering, or machine learning is required to operate the application. The user interface abstracts "
        "all underlying orchestrator logic, presenting plain-language status indicators, clear navigation controls, and comprehensive "
        "educational rubrics."
    )

    # 2.6 Constraints
    add_title("2.6 CONSTRAINTS", level=2)
    add_body(
        "The architectural implementation is subject to several concrete system and domain constraints:"
    )
    add_bullet(
        " The system mandates PostgreSQL 14+ supporting native gen_random_uuid() and JSONB operations. "
        "SQLite is explicitly unsupported due to the requirement for row-level concurrency locks (SELECT ... FOR UPDATE) and partial unique indexes.",
        bold_prefix="Relational Concurrency Constraints:"
    )
    add_bullet(
        " To prevent fragmented state, the database enforces a partial unique index guaranteeing that each candidate "
        "can possess at most one active, unfinished interview session at any given moment.",
        bold_prefix="Single Active Session Policy:"
    )
    add_bullet(
        " To guarantee cost predictability and prevent quota exhaustion, external AI provider calls are subject "
        "to a global daily ceiling (default: 2,000 requests/day) and individual per-candidate throttles. When limits are exceeded, "
        "the system seamlessly shifts to deterministic catalog rules.",
        bold_prefix="API Quotas and Rate Limits:"
    )
    add_bullet(
        " All heuristics for section heading detection, ligature normalization, and question framing are optimized "
        "for English-language technical resumes and responses. Non-English text is safely accepted but not semantically segmented.",
        bold_prefix="Linguistic Scope:"
    )
    add_bullet(
        " Facial expression analysis is constrained to 7 predefined emotional categories evaluated on-device. "
        "The system explicitly prohibits the storage of raw video frames or the generation of pseudo-scientific 'honesty' or 'employability' scores.",
        bold_prefix="Privacy and Ethical Boundaries:"
    )

    doc.add_page_break()
    print("Chapter 1 and Chapter 2 built successfully.")

if __name__ == "__main__":
    build_ch1_introduction()
    build_ch2_srs()
    doc.save(DOCX_OUT)
    print("Saved preview to DOCX.")
