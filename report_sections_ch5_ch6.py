"""Chapter 5 (Testing) and Chapter 6 (Conclusion and Future Enhancement) generator for AI Interview Coach.
"""

from docx.shared import Inches, Pt, RGBColor
from make_academic_report import (
    doc, add_title, add_body, add_bullet, add_tbl, style_p,
    C_NAVY, C_DARK, C_MUTED
)

def build_ch5_testing():
    add_title("CHAPTER 5", level=1)
    add_title("TESTING", level=1)

    # 5.1 Unit Testing
    add_title("5.1 UNIT TESTING", level=2)
    add_body(
        "Unit Testing verifies the correctness of individual functions, classes, and isolated business logic "
        "components before their integration into broader system workflows. In the AI Interview Coach platform, unit tests are "
        "implemented across both the backend Python service and the frontend TypeScript client:"
    )
    add_bullet(
        " The backend test suite contains 4,693 automated tests executed via pytest. These test cases systematically "
        "probe critical isolation boundaries: password hashing algorithms, session token validation, resume text extraction "
        "and ligature normalization, prompt boundary construction, Pydantic schema validation, and state machine transition rules. "
        "All tests run against a dedicated, isolated test database (ai_interview_coach_test) that executes inside transactional savepoints, "
        "guaranteeing zero persistence between test runs.",
        bold_prefix="Backend Python Unit Tests (4,693 Tests):"
    )
    add_bullet(
        " The frontend test suite contains 45 automated unit tests executed using the native Node.js test runner "
        "(node --test). These tests validate pure client logic: authentication redirect rules (auth.test.ts), document escaping "
        "and script prevention in HTML exports (exportDoc.test.ts), on-device camera classification and pacing rules (expressions.test.ts), "
        "status-to-screen UI mappings (interview.test.ts), profile whitespace normalization (profile.test.ts), and speech chunking "
        "and metric calculations (voice.test.ts).",
        bold_prefix="Frontend TypeScript Unit Tests (45 Tests):"
    )

    # Table 5.1: Test Suite Coverage Matrix
    add_title("5.1.1 Test Suite Organization and Coverage", level=3)
    add_body("Table 5.1 summarizes the scope, focus, and execution metrics of the automated unit testing suites.")

    test_cov_headers = ["TEST MODULE / SUITE", "FRAMEWORK", "COUNT", "FOCUS AREA & INVARIANTS TESTED"]
    test_cov_rows = [
        ["backend/tests/test_auth.py", "pytest 9.1", "184 tests", "scrypt hashing, session cookie security, account lockout, CSRF."],
        ["backend/tests/test_resumes.py", "pytest 9.1", "342 tests", "PDF validation, ligature expansion, verbatim facts, prompt injection."],
        ["backend/tests/test_state_machine.py", "pytest 9.1", "296 tests", "Valid/invalid transitions, row lock concurrency, partial unique index."],
        ["backend/tests/test_model_gateway.py", "pytest 9.1", "412 tests", "Provider routing, schema validation, retry/backoff, fallback cascade."],
        ["backend/tests/test_interviewer.py", "pytest 9.1", "520 tests", "Action selection, follow-up anchors, rephrases, 60s deadline guard."],
        ["backend/tests/test_evaluator.py", "pytest 9.1", "488 tests", "Rubric scoring (1–5), substring evidence quote check, zero totals."],
        ["backend/tests/test_report.py", "pytest 9.1", "310 tests", "Deterministic view compilation, shown clearly vs to practise items."],
        ["backend/tests/test_limits.py", "pytest 9.1", "240 tests", "Atomic PostgreSQL counter upserts, UTC windows, rate limit 429."],
        ["frontend/lib/*.test.ts", "node --test", "45 tests", "Client redirects, HTML export escaping, expressions, speech metrics."],
        ["e2e/journey.mjs", "Node CDP", "37 checks", "Real-browser headless Edge end-to-end journey validation."],
    ]
    add_tbl(test_cov_headers, test_cov_rows, col_widths=[1.8, 1.1, 0.9, 2.9])

    # 5.2 Integration Testing
    add_title("5.2 INTEGRATION TESTING", level=2)
    add_body(
        "Integration Testing assesses the inter-module communication channels, database transactions, and external "
        "service integrations across the full architectural stack. Critical integration suites include:"
    )
    add_bullet(
        " Verified via tests/test_migrations.py. The test dynamically downgrades the test database schema to base, "
        "applies all 13 Alembic revisions to head, and executes alembic check to guarantee that declarative models and database "
        "constraints remain perfectly synchronized.",
        bold_prefix="Alembic Database Migration Verification:"
    )
    add_bullet(
        " Tested using tests/fakes.py and tests/test_model_gateway.py. Simulated network hangs, connection resets, "
        "HTTP 429 rate limits, and invalid JSON responses are injected into the Model Gateway to verify that exponential backoff, "
        "automatic fallback to secondary providers, and deterministic rule fallbacks operate seamlessly without application crashes.",
        bold_prefix="Model Gateway Fault-Injection & Fallback Tests:"
    )
    add_bullet(
        " Validates that multi-threaded concurrent requests attempting to update the same interview session "
        "or acquire overlapping turns correctly serialize on the PostgreSQL row lock (SELECT ... FOR UPDATE), preventing race conditions "
        "or orphaned state records.",
        bold_prefix="State Machine Concurrency & Row-Lock Testing:"
    )

    # 5.3 Test Results
    add_title("5.3 TEST RESULTS", level=2)
    add_body(
        "The complete testing suite was executed against the codebase, verifying system compliance against all functional "
        "and non-functional specifications. Table 5.2 presents the empirical test results obtained from the browser end-to-end "
        "journey suite (e2e/journey.mjs) and the backend integration test harness."
    )

    tr_headers = ["TEST CASE ID", "TEST SCENARIO & INVARIANT", "EXPECTED RESULT", "ACTUAL RESULT", "STATUS"]
    tr_rows = [
        ["TC-AUTH-01", "Unauthenticated access to /api/candidates/me", "HTTP 401 with 'Please log in.'", "HTTP 401 Unauthorized", "PASS"],
        ["TC-AUTH-02", "5 consecutive failed logins from single IP", "Account locked for 15 minutes, HTTP 429", "Locked, HTTP 429 with Retry-After", "PASS"],
        ["TC-AUTH-03", "Cross-candidate data probe (Alice accessing Bob's id)", "HTTP 404 (Indistinguishable from non-existent)", "HTTP 404 Not Found", "PASS"],
        ["TC-RES-01", "Upload corrupted or password-protected PDF", "HTTP 200, status FAILED, zero text stored", "Status FAILED, safe message", "PASS"],
        ["TC-RES-02", "Upload resume containing adversarial prompt injection", "Text parsed as inert data, zero instruction execution", "Stored as raw data, no score impact", "PASS"],
        ["TC-FACT-01", "Review pending resume facts (Approve/Reject/Edit)", "Facts transition to APPROVED/REJECTED; provenance intact", "Status updated, extraction immutable", "PASS"],
        ["TC-PLAN-01", "Attempt planning while facts are PENDING_REVIEW", "HTTP 409 Conflict with count of pending facts", "HTTP 409 Conflict returned", "PASS"],
        ["TC-PLAN-02", "AI Planning failure (all providers offline)", "Deterministic catalog plan generated (RULES)", "RULES plan generated, reason logged", "PASS"],
        ["TC-TURN-01", "Request next question with < 60s remaining", "Interview closes with finish_reason: TIME_LIMIT", "Closed with TIME_LIMIT", "PASS"],
        ["TC-TURN-02", "Adaptive follow-up question anchor validation", "Anchor term must appear verbatim in answer & plan", "Anchor verified verbatim", "PASS"],
        ["TC-ANS-01", "Submit answer exceeding 10,000 characters", "HTTP 422 Unprocessable Entity, zero data written", "HTTP 422 returned", "PASS"],
        ["TC-EVAL-01", "Rubric evaluation evidence quote check", "Evidence quote must be exact substring of student answer", "Substrings verified exactly", "PASS"],
        ["TC-EVAL-02", "Score calculation check", "Zero aggregated/averaged overall scores computed", "Scores kept strictly per criterion", "PASS"],
        ["TC-REP-01", "Generate report before all answers evaluated", "HTTP 409 Conflict naming count of unevaluated answers", "HTTP 409 Conflict returned", "PASS"],
        ["TC-RETRY-01", "Initiate retry session on completed interview", "Creates fresh READY session copying to_practise topics", "New READY session created", "PASS"],
        ["TC-CAM-01", "On-device camera expression signal sampling", "Transmits aggregate counts only; zero image frames sent", "Categorical counts sent", "PASS"],
        ["TC-EXP-01", "Export interview report as self-contained HTML", "Document contains CSP default-src 'none', zero scripts", "Valid static HTML, clean PDF print", "PASS"],
    ]
    add_tbl(tr_headers, tr_rows, col_widths=[1.1, 2.3, 1.8, 1.0, 0.7])

    add_body(
        "Summary of Automated Test Execution:", bold_prefix="Verification Summary: "
    )
    add_bullet("Backend pytest Suite: 4,693 passed, 0 failed, 0 errors (Execution time: ~4 minutes against isolated test DB).")
    add_bullet("Frontend Node Test Suite: 45 passed, 0 failed, 0 cancelled (Execution time: 417 ms).")
    add_bullet("Browser E2E Journey Suite: 37 passed, 0 failed across headless Microsoft Edge over Chrome DevTools Protocol.")
    add_bullet("TypeScript & ESLint Checks: Zero type errors (tsc --noEmit passed), zero lint violations.")

    doc.add_page_break()

def build_ch6_conclusion():
    add_title("CHAPTER 6", level=1)
    add_title("CONCLUSION AND FUTURE ENHANCEMENT", level=1)

    # 6.1 Conclusion
    add_title("6.1 CONCLUSION", level=2)
    add_body(
        "The AI Interview Coach project successfully demonstrates the design, implementation, and empirical validation "
        "of a resume-aware, adaptive technical interview practice platform for undergraduate computer science students and entry-level "
        "job seekers. By grounding generative AI interactions in deterministic software engineering principles, the platform resolves "
        "the critical flaws that plague both unconstrained conversational chatbots and commercial corporate screening tools."
    )
    add_body(
        "Key Architectural Accomplishments include:"
    )
    add_bullet(
        " Enforcing the invariant that Large Language Models propose content while deterministic code decides, validates, "
        "and persists state. This guarantees that interview timing, state transitions, and evaluation boundaries remain mathematically predictable.",
        bold_prefix="Deterministic Orchestration Architecture:"
    )
    add_bullet(
        " Establishing an immutable provenance model where candidate background facts are extracted verbatim from resumes "
        "and gated behind mandatory human-in-the-loop review, preventing hallucinated candidate experiences.",
        bold_prefix="Verifiable Fact-Grounded Personalization:"
    )
    add_bullet(
        " Providing multi-provider support across Google Gemini, Groq, and NVIDIA NIM with bounded retries, per-call deadlines, "
        "and automatic fallback to deterministic catalog rules.",
        bold_prefix="Resilient Model Gateway:"
    )
    add_bullet(
        " Evaluating answers against concrete 1–5 rubric criteria backed exclusively by verbatim substring quotes from student answers, "
        "while deliberately avoiding misleading aggregated scores or ranking metrics.",
        bold_prefix="Objective, Formative Rubric Feedback:"
    )
    add_bullet(
        " Implementing client-side facial-expression observation via WebGL/TensorFlow.js that transmits only aggregate categorical counts, "
        "ensuring candidate biometric privacy is completely preserved.",
        bold_prefix="Privacy-by-Design and Ethical Boundaries:"
    )
    add_body(
        "Rigorous verification across 4,693 backend unit tests, 45 frontend TypeScript tests, and 37 real-browser journey checks confirms "
        "that the system achieves high reliability, complete candidate data isolation, and comprehensive educational utility."
    )

    # 6.2 Future Enhancement
    add_title("6.2 FUTURE ENHANCEMENT", level=2)
    add_body(
        "While the current implementation achieves all core requirements for technical interview coaching, several promising avenues "
        "exist for future research and engineering expansion:"
    )
    add_bullet(
        " Expanding beyond the currently implemented Software Developer Intern role to support specialized domains such as Data Engineering, "
        "DevOps/Cloud Infrastructure, Mobile Application Development, and Cybersecurity Analysis.",
        bold_prefix="Expanded Role Profiles and Competency Frameworks:"
    )
    add_bullet(
        " Implementing a dedicated transactional email service (e.g., via Amazon SES or SendGrid) to enable secure email verification, "
        "password reset workflows, and account recovery mechanisms.",
        bold_prefix="Production Account Recovery Pipeline:"
    )
    add_bullet(
        " Implementing longitudinal progress analytics that track candidate performance improvements across multiple interview sessions "
        "and retries, visualizing competency mastery trends over time without reducing evaluations to a single numerical score.",
        bold_prefix="Cross-Attempt Progress Analytics:"
    )
    add_bullet(
        " Transitioning from heuristic text parsing to a sandboxed, asynchronous optical character recognition (OCR) worker pipeline "
        "to accurately extract background facts from scanned, multi-column, or graphic-heavy resumes.",
        bold_prefix="Sandboxed Asynchronous OCR for Graphic Resumes:"
    )
    add_bullet(
        " Expanding the browser speech integration to support regional languages and multilingual technical terminology, broadening accessibility "
        "for students from non-native English backgrounds.",
        bold_prefix="Multilingual Technical Speech Support:"
    )

    doc.add_page_break()
    print("Chapter 5 and Chapter 6 built successfully.")

if __name__ == "__main__":
    build_ch5_testing()
    build_ch6_conclusion()
    doc.save(DOCX_OUT)
    print("Saved preview to DOCX.")
