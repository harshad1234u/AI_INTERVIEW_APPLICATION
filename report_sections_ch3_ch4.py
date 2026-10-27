"""Chapter 3 (Analysis and Design) and Chapter 4 (Implementation) generator for AI Interview Coach.
"""

from docx.shared import Inches, Pt, RGBColor
from make_academic_report import (
    doc, add_title, add_body, add_bullet, add_tbl, add_fig, style_p,
    C_NAVY, C_DARK, C_MUTED
)

def build_ch3_analysis_and_design():
    add_title("CHAPTER 3", level=1)
    add_title("ANALYSIS AND DESIGN", level=1)

    # 3.1 Use Case Diagram
    add_title("3.1 USE CASE DIAGRAM", level=2)
    add_fig("3.1_use_case_diagram.png", "Figure 3.1: Use Case Diagram — System Actor Interactions and Boundary")
    
    add_title("3.1.1 Use Case Diagram Description", level=3)
    add_body(
        "The Use Case Diagram depicted in Figure 3.1 defines the behavioral boundaries of the AI Interview Coach platform "
        "and delineates the interactions between primary, secondary, and system actors. The system features three principal actors:"
    )
    add_bullet(
        " The student or job seeker who authenticates via credentials, uploads a resume, manually manages facts, "
        "reviews extracted background context, configures and takes mock interviews, reviews rubric feedback, and initiates retries.",
        bold_prefix="Candidate (Primary Human Actor):"
    )
    add_bullet(
        " External Large Language Model services (Google Gemini, Groq, NVIDIA NIM) that act as stateless text generation "
        "engines accessed strictly through structured, provider-independent JSON contracts.",
        bold_prefix="External AI Providers (Secondary Cloud Actor):"
    )
    add_bullet(
        " The core backend finite state machine and rate-limiting subsystem that deterministically enforces "
        "session state transitions, validates prompt inputs, applies time limits, and triggers fallback logic.",
        bold_prefix="Deterministic Orchestrator (System Actor):"
    )
    add_body(
        "The diagram illustrates critical «include» and «extend» associations reflecting actual code relationships. "
        "The 'Register & Authenticate' use case includes cookie-based session verification. 'Upload PDF Resume' includes the deterministic "
        "section extraction heuristic, while 'Review Extracted Facts' can be optionally extended by 'Request AI Fact Extraction' when the "
        "candidate explicitly clicks the opt-in extraction trigger. 'Execute Interview Turn' is extended by 'Request Clarification / Rephrase' "
        "and includes the active turn timer check. The 'Generate Practice Report' use case requires evaluated answers and is extended by "
        "'Initiate Targeted Retry Session' only when topics requiring practice are identified."
    )

    # 3.2 Class Diagram
    add_title("3.2 CLASS DIAGRAM", level=2)
    add_fig("3.2_class_diagram.png", "Figure 3.2: Domain & System Class Diagram — Structural Entity Model")

    add_title("3.2.1 Class Diagram Description", level=3)
    add_body(
        "Figure 3.2 presents the static structural model of the system, capturing the SQLAlchemy database entities, "
        "Pydantic schemas, and core service classes. The architecture enforces strict separation between domain data models "
        "and stateless service orchestrators:"
    )
    add_bullet(
        " Serves as the root account entity holding authentication credentials (scrypt-hashed passwords), account lockout timestamps, "
        "and failed login counters. Maintains 1-to-many cascading relationships with AuthSession, Resume, CandidateFact, and InterviewSession.",
        bold_prefix="Candidate Entity:"
    )
    add_bullet(
        " Represents an uploaded PDF document. Stores file metadata, page counts, raw text, and structured section JSON. "
        "Enforces composite foreign key constraints linking extracted facts to both the resume and candidate.",
        bold_prefix="Resume Entity:"
    )
    add_bullet(
        " Stores individual skill, project, experience, or education facts. Features a provenance model tracking source (RESUME vs. MANUAL), "
        "original extracted text, candidate edits, review status (PENDING_REVIEW, APPROVED, REJECTED), and extraction mechanism (RULES vs. AI).",
        bold_prefix="CandidateFact Entity:"
    )
    add_bullet(
        " Encapsulates the complete interview lifecycle. Maintains the validated plan snapshot in JSONB, active time counters, "
        "AI consent flags, and finish reasons. A database partial unique index guarantees that only one unfinished session exists per candidate.",
        bold_prefix="InterviewSession Entity:"
    )
    add_bullet(
        " Records individual interview turns, including sequence numbers, topic positions, question text, answer text (up to 10,000 characters), "
        "and evaluation status (NOT_EVALUATED, NOT_APPLICABLE, OBSERVATIONS_ONLY, EVALUATED).",
        bold_prefix="InterviewQuestion Entity:"
    )
    add_bullet(
        " Implements rubric-based scoring across specific criteria. Stores verbatim evidence quotes extracted as exact substrings "
        "from student answers, missing concepts, and claims requiring verification.",
        bold_prefix="AnswerEvaluation Entity:"
    )
    add_bullet(
        " Core stateless services that orchestrate lifecycle transitions, external provider communication, and rubric validation.",
        bold_prefix="Service Classes (InterviewStateMachine, ModelGateway, Interviewer, Evaluator):"
    )

    # 3.3 Activity Diagram
    add_title("3.3 ACTIVITY DIAGRAM", level=2)
    add_fig("3.3_activity_diagram.png", "Figure 3.3: Activity Diagram — End-to-End Operational Lifecycle")

    add_title("3.3.1 Activity Diagram Description", level=3)
    add_body(
        "The Activity Diagram in Figure 3.3 details the sequential, decision-driven control flow governing a candidate's journey "
        "through the platform. The workflow proceeds through several distinct operational phases:"
    )
    add_bullet(
        " The candidate signs in and uploads a PDF resume. The system normalizes whitespace, parses section headings, "
        "and extracts verbatim candidate facts. If unreviewed facts exist, a mandatory gating condition prevents interview planning until the "
        "candidate explicitly reviews and confirms the profile facts.",
        bold_prefix="Profile Ingestion & Review Gate:"
    )
    add_bullet(
        " The candidate specifies target mode, difficulty, duration, and toggles AI consent. The system builds an interview plan. "
        "If an AI provider fails or consent is withheld, the system immediately generates a deterministic catalog plan.",
        bold_prefix="Planning & Consent Verification:"
    )
    add_bullet(
        " The interview proceeds turn-by-turn. Before asking a question, the server verifies remaining active time. If less than 60 seconds "
        "remain, the interview terminates with TIME_LIMIT. Otherwise, the orchestrator selects the next action (Topic, Follow-up, or Rephrase). "
        "The candidate can submit text, request clarification, pause the session, or end early.",
        bold_prefix="Turn Execution & Time Guard Loop:"
    )
    add_bullet(
        " Once the interview concludes, each stored answer is evaluated individually against rubric criteria. The system generates "
        "a deterministic practice report highlighting demonstrated strengths and topics needing practice, providing an immediate path to retry.",
        bold_prefix="Evaluation & Formative Reporting:"
    )

    # 3.4 Sequence Diagram
    add_title("3.4 SEQUENCE DIAGRAM", level=2)
    add_fig("3.4_sequence_diagram.png", "Figure 3.4: Sequence Diagram — Interactive Turn Orchestration & Verification")

    add_title("3.4.1 Sequence Diagram Description", level=3)
    add_body(
        "Figure 3.4 models the chronological message exchange between system objects during a live interview turn. "
        "The sequence demonstrates how the system maintains transactional integrity while interacting with external AI providers:"
    )
    add_bullet(
        " The candidate clicks 'Start Interview' or submits an answer, prompting the Next.js client to call POST /questions/next.",
        bold_prefix="Turn Initiation:"
    )
    add_bullet(
        " The API router initiates a database transaction, acquiring an exclusive row lock on the session (SELECT ... FOR UPDATE). "
        "The Interviewer service checks active elapsed time, verifying whether the 60-second minimum reserve is met.",
        bold_prefix="Lock Acquisition & Decision:"
    )
    add_bullet(
        " If the decision involves generating adaptive wording via AI, the database transaction commits and releases the row lock "
        "prior to invoking the external model. This guarantees that external network latency never holds open a database connection.",
        bold_prefix="Lock Release & External Invocation:"
    )
    add_bullet(
        " The Model Gateway routes the request, enforces timeouts, and validates the returned JSON against Pydantic schemas. "
        "It verifies that anchor terms appear verbatim within both the student's answer and approved plan facts.",
        bold_prefix="Gateway Routing & Anchor Grounding:"
    )
    add_bullet(
        " The router re-acquires the row lock, re-verifies that AI consent has not been revoked during the model call, records "
        "the question entity, transitions the state machine to WAITING_FOR_ANSWER, and commits the transaction.",
        bold_prefix="Re-Locking, Persistence & State Transition:"
    )

    # 3.5 State Machine Diagram
    add_title("3.5 STATE MACHINE DIAGRAM", level=2)
    add_fig("3.5_state_machine_diagram.png", "Figure 3.5: State Machine Diagram — Complete Session State Transitions")

    add_title("3.5.1 State Machine Diagram Description", level=3)
    add_body(
        "The State Machine Diagram in Figure 3.5 formalizes the exact finite state machine implemented within "
        "app/services/interview_state_machine.py. The state machine serves as the single source of truth for session status, "
        "rejecting any transition not explicitly declared in its transition matrix:"
    )
    add_bullet(
        " A session is created in CREATED, immediately advancing via system events through PROFILE_PROCESSING to PROFILE_REVIEW. "
        "The candidate must execute CONFIRM_PROFILE (guarded by zero pending facts) to transition into INTERVIEW_PLANNING.",
        bold_prefix="Pre-Interview States:"
    )
    add_bullet(
        " Upon receipt of PLAN_READY, the session enters READY. Invoking START_INTERVIEW transitions to ASKING, which immediately "
        "advances to WAITING_FOR_ANSWER upon QUESTION_ASKED.",
        bold_prefix="Active Turn Execution:"
    )
    add_bullet(
        " While in WAITING_FOR_ANSWER, the candidate may invoke PAUSE (transitioning to PAUSED, which halts the active clock) and RESUME. "
        "Submitting an answer triggers ANSWER_SUBMITTED -> ANSWER_PROCESSING -> ANSWER_PROCESSED -> ANSWER_EVALUATION -> NEXT_DECISION.",
        bold_prefix="Answer Submission & Decision Loop:"
    )
    add_bullet(
        " From NEXT_DECISION, the orchestrator triggers FOLLOW_UP, NEXT_TOPIC, or REPHRASE (all returning to ASKING), or FINISH "
        "(transitioning to REPORT_GENERATION with finish reason PLAN_COMPLETED or TIME_LIMIT). Early exits via END_INTERVIEW or TIME_EXPIRED "
        "also lead to REPORT_GENERATION. Finally, POST /report triggers REPORT_READY, transitioning the session to COMPLETED.",
        bold_prefix="Terminal Transitions & Finish Reasons:"
    )

    # 3.6 Communication Diagram
    add_title("3.6 COMMUNICATION DIAGRAM", level=2)
    add_fig("3.6_communication_diagram.png", "Figure 3.6: Communication Diagram — Object Collaboration Model")

    add_title("3.6.1 Communication Diagram Description", level=3)
    add_body(
        "Figure 3.6 illustrates the structural collaboration and numbered message passing between runtime objects during "
        "turn processing and answer evaluation. Unlike the time-centric sequence diagram, the communication diagram emphasizes "
        "object relationships and link topology. The diagram shows how the InterviewRouter coordinates with the StateMachine, "
        "InterviewerService, ModelGateway, EvaluatorService, and DatabaseSession, demonstrating low coupling and high cohesion."
    )

    # 3.7 Component Diagram
    add_title("3.7 COMPONENT DIAGRAM", level=2)
    add_fig("3.7_component_diagram.png", "Figure 3.7: Component Diagram — Architectural Subsystems and Dependencies")

    add_title("3.7.1 Component Diagram Description", level=3)
    add_body(
        "The Component Diagram in Figure 3.7 outlines the high-level software subsystems and their contractual dependencies. "
        "The architecture is organized into five decoupled layers:"
    )
    add_bullet("Frontend Presentation Subsystem: Next.js pages, UI components, camera/voice hooks, and client-side export utilities.")
    add_bullet("FastAPI Backend Service Application: REST endpoints, ASGI middleware, dependency injection, and security guards.")
    add_bullet("AI Model Gateway Subsystem: Provider-independent model gateway, adapter implementations, and specialized agent boundaries.")
    add_bullet("Data Persistence Layer: Declarative SQLAlchemy ORM models, Alembic migrations, and PostgreSQL connection pooling.")
    add_bullet("External Execution Runtimes: Google Generative AI, Groq Cloud, NVIDIA NIM, and client-side WebGL face-api.js.")

    # 3.8 Deployment Diagram
    add_title("3.8 DEPLOYMENT DIAGRAM", level=2)
    add_fig("3.8_deployment_diagram.png", "Figure 3.8: Deployment Diagram — Distributed System Infrastructure")

    add_title("3.8.1 Deployment Diagram Description", level=3)
    add_body(
        "Figure 3.8 represents the physical execution topology across hardware nodes and network communication channels. "
        "The candidate client machine runs a modern web browser executing the Single Page Application, WebGL face-api.js neural networks, "
        "and Web Speech APIs. The client connects over HTTP/HTTPS to the application server hosting Uvicorn and FastAPI. The backend interacts "
        "with an enterprise PostgreSQL relational database over port 5432 using psycopg binary protocol, and dispatches external outbound "
        "AI calls over HTTPS (TLS 1.3, port 443) using bearer authorization tokens."
    )

    # 3.9 Package Diagram
    add_title("3.9 PACKAGE DIAGRAM", level=2)
    add_fig("3.9_package_diagram.png", "Figure 3.9: Package Diagram — Namespace Hierarchy and Modularity")

    add_title("3.9.1 Package Diagram Description", level=3)
    add_body(
        "The Package Diagram in Figure 3.9 maps the logical code organization across directories and modules. The backend is partitioned "
        "into app.api (HTTP routes), app.core (configuration and security), app.db (database session management), app.models (SQLAlchemy entities), "
        "app.schemas (Pydantic contracts), app.services (business logic and state machine), and app.ai (model gateway and agents). The frontend "
        "is organized into app (App Router pages), components (React UI elements), and lib (pure business logic and tests). Automated test "
        "packages in tests/ and e2e/ verify the integrity of these namespaces."
    )

    # 3.10 Design Patterns Used
    add_title("3.10 DESIGN PATTERNS USED", level=2)
    add_body(
        "To ensure modularity, maintainability, and architectural robustness, the system implements proven Object-Oriented "
        "software design patterns categorized under GRASP and Gang of Four (GoF) principles:"
    )
    add_bullet(
        " The InterviewStateMachine acts as a strict Controller and Information Expert, encapsulating all valid transition "
        "logic and preventing external entities from directly modifying session states. Low Coupling is maintained by isolating "
        "provider-specific API formats inside adapter classes, shielding core services from external changes.",
        bold_prefix="GRASP Patterns (Controller, Information Expert, Low Coupling):"
    )
    add_bullet(
        " Applied within app/services/interview_state_machine.py, where session status transitions are governed by an explicit "
        "transition table, decoupling state behavior from the session model.",
        bold_prefix="GoF State Pattern:"
    )
    add_bullet(
        " The ModelGateway utilizes the Strategy Pattern to dynamically switch between external provider adapters "
        "(Gemini, Groq, NVIDIA) based on configured priority order and runtime health.",
        bold_prefix="GoF Strategy & Adapter Patterns:"
    )
    add_bullet(
        " The ModelGateway encapsulates the complexity of HTTP calls, retries, exponential backoffs, and JSON schema "
        "parsing behind a clean generate_structured() method.",
        bold_prefix="GoF Facade / Gateway Pattern:"
    )
    add_bullet(
        " 'The LLM proposes, the orchestrator decides, the validator verifies, and the database stores.' "
        "This foundational pattern guarantees that generative models are restricted to proposing content, while deterministic code "
        "maintains absolute authority over system state and business decisions.",
        bold_prefix="Architectural Pattern (Orchestrator-Validator-Store):"
    )

    doc.add_page_break()

def build_ch4_implementation():
    add_title("CHAPTER 4", level=1)
    add_title("IMPLEMENTATION", level=1)

    # 4.1 Module Description
    add_title("4.1 MODULE DESCRIPTION", level=2)
    add_body(
        "The AI Interview Coach comprises eleven interconnected, highly cohesive architectural modules that implement "
        "the functional requirements specified in Chapter 2."
    )

    # 4.1.1 Authentication & Candidate Management
    add_title("4.1.1 Authentication and Candidate Management Module", level=3)
    add_body(
        "The authentication module (app/api/routes/auth.py, app/services/auth.py) manages candidate registration, credential verification, "
        "and session lifecycle. Password hashing is executed using standard-library hashlib.scrypt with parameters N=16384, r=8, p=5, "
        "and a 16-byte cryptographically secure random salt. Plaintext passwords are never logged or stored. Session tokens are 32-byte "
        "cryptographic random strings whose SHA-256 digests are stored in the auth_sessions table. The plaintext token is delivered exclusively "
        "via a secure HttpOnly, SameSite=Lax cookie (coach_session). Account lockout protection locks an account for 15 minutes after 5 consecutive "
        "failed login attempts, serializing attempts on the candidate row lock to prevent race conditions."
    )

    # 4.1.2 Resume Parsing & Candidate Facts
    add_title("4.1.2 Resume Parsing and Candidate Fact Management Module", level=3)
    add_body(
        "Resume processing (app/services/resume_extractor.py) operates deterministically in memory using pypdf 6.x without spooling temporary "
        "files to disk. The extractor normalizes typographic ligatures (e.g., ﬁ -> fi), strips non-content lines, and identifies sections "
        "using a curated heading dictionary. Facts within recognized sections (skills, projects, experience, education, certifications) are extracted "
        "exclusively as verbatim substrings of individual resume lines. Extracted facts are inserted into candidate_facts with status PENDING_REVIEW. "
        "The candidate must explicitly approve, reject, or edit these facts before interview planning. Alternatively, candidates may input manual facts "
        "via the manual profile interface (app/services/manual_facts.py), which enforces a 100-fact limit and duplicate detection."
    )

    # 4.1.3 AI Model Gateway
    add_title("4.1.3 AI Model Gateway and Provider Routing Module", level=3)
    add_body(
        "The Model Gateway (app/ai/gateway.py, app/ai/providers.py) acts as a provider-agnostic abstraction layer for generative AI operations. "
        "Agents request capabilities (PROFILE_EXTRACTION, INTERVIEW_PLANNING, QUESTION_GENERATION, ANSWER_EVALUATION) along with strict Pydantic schemas. "
        "The gateway routes calls across configured providers (Gemini, Groq, NVIDIA) in prioritized order. It wraps each call in a 20-second timeout "
        "with bounded exponential backoff retries for transient faults (timeouts, rate limits, 5xx errors). Before returning, the gateway validates "
        "raw JSON against the Pydantic schema with extra='forbid', guaranteeing that unexpected model fields are rejected."
    )

    # 4.1.4 Interview Planning
    add_title("4.1.4 Interview Planning and Catalog Rules Module", level=3)
    add_body(
        "The planning engine (app/services/interview_planner.py, app/ai/planner_agent.py) translates candidate profile facts and settings into a "
        "structured interview plan. The topic budget is calculated as duration // 3 (e.g., 15 minutes yields 5 topics). Topics cover required "
        "competencies (programming fundamentals, data structures, databases, web development, project understanding, behavioral). If AI consent "
        "is active, the PlannerAgent proposes custom topics citing approved candidate facts. If AI is disabled or fails, the catalog rules engine "
        "selects curated questions, ensuring that technical and project areas receive non-duplicate questions."
    )

    # 4.1.5 Deterministic State Machine
    add_title("4.1.5 Deterministic State Machine and Orchestrator Module", level=3)
    add_body(
        "The interview state machine (app/services/interview_state_machine.py) enforces strict lifecycle boundaries. Session transitions "
        "execute under an exclusive database row lock (SELECT ... FOR UPDATE). The state machine manages transitions between CREATED, PROFILE_PROCESSING, "
        "PROFILE_REVIEW, INTERVIEW_PLANNING, READY, ASKING, WAITING_FOR_ANSWER, PAUSED, ANSWER_PROCESSING, ANSWER_EVALUATION, NEXT_DECISION, "
        "REPORT_GENERATION, and COMPLETED. It computes elapsed active time, pausing the clock during candidate pauses."
    )

    # 4.1.6 Interview Execution
    add_title("4.1.6 Interview Execution and Dynamic Pacing Module", level=3)
    add_body(
        "Interview turn orchestration (app/services/interviewer.py) governs live Q&A. The engine checks the deadline prior to each question; "
        "if remaining time is under 60 seconds, it closes the interview with TIME_LIMIT. Decisions prioritize topic progression, followed by adaptive "
        "follow-ups (at most 2 per topic) or rephrases (at most 2 per chain). Follow-ups anchor strictly on terms found within both the candidate's "
        "answer and approved plan vocabulary. Candidate answers are capped at 10,000 characters and stored initially as NOT_EVALUATED."
    )

    # 4.1.7 Answer Evaluator
    add_title("4.1.7 Answer Evaluator and Rubric Verification Module", level=3)
    add_body(
        "Evaluation (app/services/evaluator.py, app/ai/evaluator_agent.py) executes post-interview on stored answers. Technical answers are scored "
        "against four criteria: relevance, completeness, reasoning, and communication (1–5 scale). Every assigned score mandates at least one exact "
        "substring evidence quote from the student's answer. Problematic statements are marked as 'Needs verification' rather than penalizing accuracy. "
        "Aggregated or combined overall scores are strictly prohibited to prevent misleading evaluative judgments."
    )

    # 4.1.8 Practice Report & Retry
    add_title("4.1.8 Practice Report Generation and Targeted Retry Module", level=3)
    add_body(
        "The report engine (app/services/report.py) compiles stored evaluations, questions, and active times into a deterministic summary. "
        "It categorizes criteria scored 4–5 as 'shown clearly' and criteria scored 1–2 (or missing concepts) as 'to practise'. The retry service "
        "(app/services/retry.py) enables candidates to generate a new READY interview session copying only the topics flagged for practice, "
        "linking attempts in the candidate's interview history."
    )

    # 4.1.9 On-Device Expression Observation
    add_title("4.1.9 On-Device Facial Expression Observation Module", level=3)
    add_body(
        "The camera subsystem (frontend/components/interview/useExpressionCamera.ts, lib/expressions.ts) runs lightweight neural networks "
        "(@vladmandic/face-api) locally in the browser via WebGL. The network samples visible expressions approximately once per second while a "
        "question is active. It aggregates samples into categorical counts (neutral, happy, sad, angry, fearful, disgusted, surprised, no face, "
        "multiple faces). Raw video frames never leave the client device, and expression counts are completely decoupled from technical scoring."
    )

    # 4.1.10 Voice Assistant
    add_title("4.1.10 Voice Assistant and Browser Speech Engine Module", level=3)
    add_body(
        "The voice assistant (frontend/components/interview/useVoice.ts, lib/voice.ts) provides text-to-speech reading of questions using browser "
        "speechSynthesis and speech-to-text input via browser SpeechRecognition. Audio is processed by the browser vendor's native engine and "
        "transcribed into the answer textarea, allowing candidates to review and edit their response before submitting text to the backend."
    )

    # 4.1.11 Usage Controls
    add_title("4.1.11 Usage Controls and Abuse Prevention Module", level=3)
    add_body(
        "The limits service (app/services/limits.py) tracks rate limits atomically in PostgreSQL using the usage_counters table. Windows are aligned "
        "in UTC. The system limits registrations (5/hour/network), login attempts (20/15min/network), resume uploads (10/day/candidate), AI planning "
        "(10/day/candidate), AI question wording (150/day/candidate), and global AI budget (2,000 requests/day)."
    )

    # 4.2 Technology Description
    add_title("4.2 TECHNOLOGY DESCRIPTION", level=2)
    add_body(
        "The implementation utilizes modern, robust software technologies selected for type safety, performance, and reliability:"
    )
    add_bullet(
        " FastAPI provides high-throughput asynchronous request handling built on Starlette and Pydantic v2. "
        "It enables automatic OpenAPI documentation generation and strict request body validation.",
        bold_prefix="FastAPI (Backend Web Framework):"
    )
    add_bullet(
        " Next.js 15 with React 19 App Router delivers a responsive, accessible Single Page Application with server-side "
        "rendering capabilities, client-side routing, and zero-flash theme persistence.",
        bold_prefix="Next.js & React (Frontend Client):"
    )
    add_bullet(
        " PostgreSQL 14+ serves as the primary data store, providing robust transactional isolation, native UUID "
        "generation (gen_random_uuid()), JSONB document indexing, and partial unique indexes.",
        bold_prefix="PostgreSQL & SQLAlchemy 2.0 (Persistence Tier):"
    )
    add_bullet(
        " pypdf 6.x provides pure-Python, dependency-free PDF text extraction, avoiding heavy C-libraries or external "
        "daemon processes.",
        bold_prefix="pypdf (Document Extraction):"
    )
    add_bullet(
        " A customized build of face-api.js running over WebGL/TensorFlow.js enables real-time client-side expression "
        "classification using only ~520 KB of quantized neural network weights.",
        bold_prefix="@vladmandic/face-api (Client Neural Network):"
    )

    # Relational Schema Table
    add_title("4.2.1 Relational Database Schema Summary", level=3)
    add_body("Table 4.1 summarizes the relational entities, primary keys, foreign keys, and integrity constraints enforced in PostgreSQL.")

    db_headers = ["TABLE NAME", "PRIMARY KEY", "FOREIGN KEYS & CASCADES", "CONSTRAINTS & INDEXES"]
    db_rows = [
        ["candidates", "id (UUID)", "None", "UNIQUE(email), CHECK(lower(email)), CHECK(name != '')"],
        ["auth_sessions", "token_hash (VARCHAR)", "candidate_id -> candidates (CASCADE)", "CHECK(expires_at > created_at), INDEX(candidate_id)"],
        ["resumes", "id (UUID)", "candidate_id -> candidates (CASCADE)", "UNIQUE(id, candidate_id), CHECK(status IN ('PROCESSED', ...))"],
        ["candidate_facts", "id (UUID)", "candidate_id, resume_id -> resumes (CASCADE)", "CHECK(provenance_matches_source), Partial Unique Index"],
        ["interview_sessions", "id (UUID)", "candidate_id -> candidates (CASCADE)", "Partial UNIQUE(candidate_id) WHERE status != 'COMPLETED'"],
        ["interview_questions", "id (UUID)", "session_id -> interview_sessions (CASCADE)", "UNIQUE(session_id, seq), CHECK(length(answer_text) <= 10000)"],
        ["answer_evaluations", "id (UUID)", "question_id -> interview_questions (CASCADE)", "UNIQUE(question_id), FK(session_id)"],
        ["answer_evaluation_criteria", "id (UUID)", "evaluation_id -> answer_evaluations (CASCADE)", "CHECK(score BETWEEN 1 AND 5), CHECK(criterion IN (...))"],
        ["question_expression_observations", "id (UUID)", "question_id -> interview_questions (CASCADE)", "UNIQUE(question_id), CHECK(counts BETWEEN 0 AND 10000)"],
        ["provider_calls", "id (UUID)", "None (Standalone Audit Log)", "INDEX(request_id), Stores zero candidate IDs or prompts"],
        ["usage_counters", "scope, key, window", "None (Ephemeral Rate Counters)", "CHECK(count >= 1), INDEX(expires_at)"],
    ]
    add_tbl(db_headers, db_rows, col_widths=[1.5, 1.1, 1.8, 2.3])

    doc.add_page_break()
    print("Chapter 3 and Chapter 4 built successfully.")

if __name__ == "__main__":
    build_ch3_analysis_and_design()
    build_ch4_implementation()
    doc.save(DOCX_OUT)
    print("Saved preview to DOCX.")
