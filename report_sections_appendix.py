"""Appendix A (Source Code), Appendix B (Screen Shots), and References generator for AI Interview Coach.
"""

import os
from docx.shared import Inches, Pt, RGBColor
from make_academic_report import (
    doc, add_title, add_body, add_bullet, add_shot, add_code, style_p,
    C_NAVY, C_DARK, C_MUTED
)

def build_appendix_and_references():
    # ==========================================
    # APPENDIX A – SOURCE CODE
    # ==========================================
    add_title("APPENDIX A – SOURCE CODE", level=1)
    add_body(
        "This appendix provides key excerpts of the core architectural implementations governing "
        "state machine transitions, provider-independent model gateways, verbatim resume parsing, turn orchestration, "
        "and client-side document export."
    )

    # A.1 State Machine
    add_title("A.1 Finite State Machine Transition Engine (app/services/interview_state_machine.py)", level=2)
    add_body(
        "The following excerpt illustrates the declarative transition matrix, client actions, system events, "
        "and transactional update logic enforcing session state boundaries:"
    )
    add_code(
'''class ClientAction(StrEnum):
    CONFIRM_PROFILE = "CONFIRM_PROFILE"
    START_INTERVIEW = "START_INTERVIEW"
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    END_INTERVIEW = "END_INTERVIEW"

TRANSITIONS: dict[tuple[InterviewStatus, SessionEvent], InterviewStatus] = {
    (S.CREATED, E.PROFILE_PROCESSING_STARTED): S.PROFILE_PROCESSING,
    (S.PROFILE_PROCESSING, E.PROFILE_READY): S.PROFILE_REVIEW,
    (S.PROFILE_REVIEW, E.CONFIRM_PROFILE): S.INTERVIEW_PLANNING,
    (S.INTERVIEW_PLANNING, E.PLAN_READY): S.READY,
    (S.READY, E.START_INTERVIEW): S.ASKING,
    (S.ASKING, E.QUESTION_ASKED): S.WAITING_FOR_ANSWER,
    (S.WAITING_FOR_ANSWER, E.ANSWER_SUBMITTED): S.ANSWER_PROCESSING,
    (S.ANSWER_PROCESSING, E.ANSWER_PROCESSED): S.ANSWER_EVALUATION,
    (S.ANSWER_EVALUATION, E.ANSWER_EVALUATED): S.NEXT_DECISION,
    (S.NEXT_DECISION, E.FOLLOW_UP): S.ASKING,
    (S.NEXT_DECISION, E.NEXT_TOPIC): S.ASKING,
    (S.NEXT_DECISION, E.REPHRASE): S.ASKING,
    (S.NEXT_DECISION, E.FINISH): S.REPORT_GENERATION,
    (S.ASKING, E.FINISH): S.REPORT_GENERATION,
    (S.REPORT_GENERATION, E.REPORT_READY): S.COMPLETED,
    (S.WAITING_FOR_ANSWER, E.PAUSE): S.PAUSED,
    (S.PAUSED, E.RESUME): S.WAITING_FOR_ANSWER,
    (S.WAITING_FOR_ANSWER, E.END_INTERVIEW): S.REPORT_GENERATION,
    (S.PAUSED, E.END_INTERVIEW): S.REPORT_GENERATION,
    (S.ASKING, E.TIME_EXPIRED): S.REPORT_GENERATION,
    (S.WAITING_FOR_ANSWER, E.TIME_EXPIRED): S.REPORT_GENERATION,
}

def next_status(status: object, event: object) -> InterviewStatus:
    try:
        return TRANSITIONS[(InterviewStatus(status), SessionEvent(event))]
    except (KeyError, ValueError):
        raise InvalidTransition(status, event) from None'''
    )

    # A.2 Model Gateway
    add_title("A.2 Provider-Independent Model Gateway (app/ai/gateway.py)", level=2)
    add_body(
        "The excerpt below demonstrates how the Model Gateway abstracts provider APIs, enforces timeouts, "
        "executes bounded exponential backoff retries, and validates structured JSON schemas:"
    )
    add_code(
'''class ModelGateway:
    def __init__(self, providers: list[ModelProvider], timeout_seconds: float = 20.0,
                 max_retries: int = 1, daily_budget_limit: int = 2000):
        self.providers = providers
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

    async def generate_structured(self, request: ModelRequest, schema: type[T], *,
                                  deadline: float | None = None) -> ModelResult[T]:
        attempts = 0
        last_error = None
        for provider in self.providers:
            for retry in range(self.max_retries + 1):
                attempts += 1
                try:
                    with anyio.fail_after(self.timeout_seconds):
                        raw = await provider.complete(request, schema.model_json_schema())
                        parsed = schema.model_validate_json(raw.text)
                        return ModelResult(output=parsed, record=CallRecord(
                            request_id=str(uuid.uuid4()), capability=request.capability,
                            provider=provider.name, model=provider.model, attempts=attempts,
                            fallback_used=(provider != self.providers[0])
                        ))
                except Exception as err:
                    last_error = err
                    if not self._is_retryable(err) or retry == self.max_retries:
                        break
                    await anyio.sleep(0.5 * (2 ** retry))
        raise ModelUnavailableError(f"All configured providers failed: {last_error}")'''
    )

    # A.3 Resume Extractor
    add_title("A.3 Verbatim Heuristic Resume Extractor (app/services/resume_extractor.py)", level=2)
    add_body(
        "The resume extraction logic parses PDF text in memory and extracts candidate facts strictly as verbatim substrings:"
    )
    add_code(
'''def extract_facts_from_pdf(pdf_bytes: bytes) -> tuple[ResumeStatus, list[ExtractedFact], dict]:
    reader = PdfReader(BytesIO(pdf_bytes))
    if len(reader.pages) > 10:
        return ResumeStatus.UNSUPPORTED, [], {"error": "PDF exceeds 10 pages maximum"}
    
    raw_text = ""
    for page in reader.pages:
        raw_text += page.extract_text() or ""
        
    normalized = unicodedata.normalize("NFKC", raw_text)
    sections = detect_sections(normalized)
    facts = []
    
    for section_name, lines in sections.items():
        category = HEADINGS.get(section_name.lower())
        if not category:
            continue
        for line in lines:
            line_clean = line.strip()
            if 3 <= len(line_clean) <= 200:
                facts.append(ExtractedFact(
                    category=category, fact=line_clean, extracted_fact=line_clean,
                    source_section=section_name, source_text=line,
                    status=FactStatus.PENDING_REVIEW, extracted_by=ExtractionType.RULES
                ))
    return ResumeStatus.PROCESSED, facts, {"section_count": len(sections)}'''
    )

    # A.4 Interviewer Execution
    add_title("A.4 Interviewer Decision Engine and Pacing Guard (app/services/interviewer.py)", level=2)
    add_body(
        "The interviewer service decides next actions, verifies the 60-second minimum reserve, and validates anchor terms:"
    )
    add_code(
'''def decide_next_action(session: InterviewSession, questions: list[InterviewQuestion],
                       active_seconds: float) -> tuple[ActionType, object]:
    total_allowed = session.plan["settings"]["duration_minutes"] * 60
    time_remaining = total_allowed - active_seconds
    
    # 60s minimum reserve guard
    if time_remaining < 60.0:
        return ActionType.FINISH, FinishReason.TIME_LIMIT
        
    if not questions:
        return ActionType.TOPIC, session.plan["topics"][0]
        
    last_q = questions[-1]
    if last_q.answer_kind == AnswerKind.CLARIFY and last_q.rephrase_index < 2:
        return ActionType.REPHRASE, last_q
        
    if last_q.answer_kind == AnswerKind.ANSWER and last_q.follow_up_index < 2:
        term = find_matching_anchor(last_q.answer_text, session.plan["topics"][last_q.topic_position])
        if term:
            return ActionType.FOLLOW_UP, term
            
    # Move to next topic or finish
    next_pos = last_q.topic_position + 1
    if next_pos < len(session.plan["topics"]):
        return ActionType.TOPIC, session.plan["topics"][next_pos]
        
    return ActionType.FINISH, FinishReason.PLAN_COMPLETED'''
    )

    # A.5 Evaluator Rubrics
    add_title("A.5 Rubric Answer Evaluator with Verbatim Substring Quotes (app/services/evaluator.py)", level=2)
    add_body(
        "The evaluation engine ensures that criterion scores are backed exclusively by verbatim substring quotes from student answers:"
    )
    add_code(
'''def validate_and_record_evaluation(answer_text: str, model_proposal: EvaluationProposal,
                                   rubric: str) -> AnswerEvaluation:
    validated_criteria = []
    for crit in model_proposal.criteria:
        # Every criterion score requires at least one verbatim evidence quote
        for quote in crit.evidence:
            if quote not in answer_text:
                raise ValidationError(f"Quote '{quote}' is not a verbatim substring of answer!")
        validated_criteria.append(crit)
        
    return AnswerEvaluation(
        rubric=rubric, criteria=validated_criteria,
        missing_concepts=model_proposal.missing_concepts,
        claims_to_verify=model_proposal.claims_to_verify,
        feedback=model_proposal.feedback, source=EvaluationSource.AI
    )'''
    )

    # A.6 Client-Side Document Exporter
    add_title("A.6 Client-Side Self-Contained Document Exporter (frontend/lib/exportDoc.ts)", level=2)
    add_body(
        "The export utility compiles interview plans and practice reports into standalone HTML files with strict CSP:"
    )
    add_code(
'''export function buildReportDocument(report: InterviewReportData, sessionNum: number): string {
    const safeTitle = escapeHtml(`Interview Report #${sessionNum}`);
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline';" />
  <title>${safeTitle}</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; padding: 2rem; }
    .card { border: 1px solid #cbd5e1; border-radius: 0.5rem; padding: 1.5rem; margin-bottom: 1.5rem; }
    .score-badge { font-weight: bold; color: #1e3a8a; }
    blockquote { border-left: 3px solid #2563eb; padding-left: 1rem; color: #475569; }
  </style>
</head>
<body>
  <h1>${safeTitle}</h1>
  <div class="card">
    <h2>Summary</h2>
    <p>Role: ${escapeHtml(report.summary.role)} | Finish Reason: ${escapeHtml(report.summary.finish_reason)}</p>
  </div>
  ${report.shown_clearly.map(item => `
    <div class="card">
      <p class="score-badge">Criterion: ${escapeHtml(item.criterion)} (Score: ${item.score}/5)</p>
      <blockquote>${escapeHtml(item.evidence.join(' '))}</blockquote>
    </div>`).join('')}
</body>
</html>`;
}'''
    )

    doc.add_page_break()

    # ==========================================
    # APPENDIX B – SCREEN SHOTS
    # ==========================================
    add_title("APPENDIX B – SCREEN SHOTS", level=1)
    add_body(
        "This appendix documents the graphical user interfaces and live operational workflows of the AI Interview Coach platform, "
        "captured during real browser validation execution (e2e/out/shots/)."
    )

    # B.1 Login
    add_shot("01-login.png", "Figure B.1: Authentication and Sign-In Interface (/login)")
    add_body(
        "Figure B.1 displays the clean, accessible sign-in and registration screen. The interface provides secure authentication "
        "controls with immediate client-side validation, password length bounds (8–128 characters), and clear informational guidance "
        "detailing how the coaching platform functions."
    )

    # B.2 Resume Facts
    add_shot("02-resume-facts.png", "Figure B.2: Verbatim Resume Extraction and Fact Review Dashboard")
    add_body(
        "Figure B.2 illustrates the human-in-the-loop fact review dashboard. Uploaded resume facts are categorized by competency "
        "(Skills, Projects, Experience, Education) with exact provenance lines. Candidates review, edit, approve, or reject items before "
        "confirming their profile."
    )

    # B.3 Interview Plan
    add_shot("03-plan.png", "Figure B.3: Interview Configuration and Planning Screen")
    add_body(
        "Figure B.3 shows the interview configuration interface. Candidates select target mode, difficulty, and duration, and toggle "
        "explicit AI consent. The generated topic sequence cites specific approved candidate facts, and offers one-click HTML/PDF export."
    )

    # B.4 Active Turn
    add_shot("09-camera-in-interview.png", "Figure B.4: In-Progress Interview Turn with Local Pacing Timer")
    add_body(
        "Figure B.4 depicts an active interview turn. The interface renders the current question, candidate response textarea "
        "(with character count indicator), turn controls (Submit, Rephrase, I don't know, Skip, Pause), and active server-synchronized timer."
    )

    # B.5 Camera Observation
    add_shot("08-camera-ready.png", "Figure B.5: On-Device Facial Expression Observation Signal Panel")
    add_body(
        "Figure B.5 illustrates the optional on-device expression observation panel. Operating locally via WebGL and face-api.js, "
        "the panel displays real-time categorical signal distributions without transmitting raw camera frames or generating evaluative judgments."
    )

    # B.6 Report
    add_shot("04-report.png", "Figure B.6: Comprehensive Non-Aggregated Interview Evaluation Report")
    add_body(
        "Figure B.6 presents the formative practice report. Individual criteria are scored 1–5 with exact quote evidence. "
        "The report highlights competencies shown clearly, identifies specific areas to practice, and provides an immediate retry trigger."
    )

    # B.7 History & Retry
    add_shot("05-history.png", "Figure B.7: Multi-Attempt Interview History and Targeted Retry Session Link")
    add_body(
        "Figure B.7 shows the multi-attempt interview history dashboard. Each attempt is recorded independently with its completion "
        "status and report. Retries explicitly indicate the source interview attempt they reinforce."
    )

    # B.8 Mobile Report
    add_shot("06-mobile-report.png", "Figure B.8: Responsive Mobile View of Practice Report and Feedback")
    add_body(
        "Figure B.8 confirms the mobile responsiveness of the platform on phone-sized viewports (390px width), verifying "
        "horizontal overflow prevention, readable typography, and accessible button tap targets."
    )

    doc.add_page_break()

    # ==========================================
    # REFERENCES
    # ==========================================
    add_title("REFERENCES", level=1)
    
    add_body("BOOKS:", bold_prefix=None, italic=True)
    add_bullet("Bass, L., Clements, P., & Kazman, R. (2021). Software Architecture in Practice (4th ed.). Addison-Wesley Professional.")
    add_bullet("Fowler, M. (2018). Refactoring: Improving the Design of Existing Code (2nd ed.). Addison-Wesley Professional.")
    add_bullet("Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). Design Patterns: Elements of Reusable Object-Oriented Software. Addison-Wesley.")
    add_bullet("Larman, C. (2004). Applying UML and Patterns: An Introduction to Object-Oriented Analysis and Design and Iterative Development (3rd ed.). Prentice Hall.")
    add_bullet("Pressman, R. S., & Maxim, B. R. (2020). Software Engineering: A Practitioner's Approach (9th ed.). McGraw-Hill Education.")
    add_bullet("Sommerville, I. (2016). Software Engineering (10th ed.). Pearson.")

    add_body("RESEARCH PAPERS & ARTICLES:", bold_prefix=None, italic=True)
    add_bullet("Achiam, J., et al. (2023). GPT-4 Technical Report. arXiv preprint arXiv:2303.08774.")
    add_bullet("Bommasani, R., et al. (2021). On the Opportunities and Risks of Foundation Models. arXiv preprint arXiv:2108.07258.")
    add_bullet("Dwork, C., & Roth, A. (2014). The Algorithmic Foundations of Differential Privacy. Foundations and Trends in Theoretical Computer Science, 9(3–4), 211–407.")
    add_bullet("Ribeiro, M. T., Singh, S., & Guestrin, C. (2016). 'Why Should I Trust You?': Explaining the Predictions of Any Classifier. ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD), 1135–1144.")
    add_bullet("Vaswani, A., et al. (2017). Attention Is All You Need. Advances in Neural Information Processing Systems (NeurIPS), 30, 5998–6008.")

    add_body("TECHNICAL STANDARDS & DOCUMENTATION:", bold_prefix=None, italic=True)
    add_bullet("ECMAScript Language Specification (ECMA-262). (2024). https://tc39.es/ecma262/")
    add_bullet("FastAPI Framework Documentation. (2026). https://fastapi.tiangolo.com/")
    add_bullet("Next.js App Router Documentation. (2026). https://nextjs.org/docs")
    add_bullet("OpenAI API Specification for Structured JSON Outputs. (2024). https://platform.openai.com/docs/guides/structured-outputs")
    add_bullet("PostgreSQL 16 Documentation. (2024). PostgreSQL Global Development Group. https://www.postgresql.org/docs/")
    add_bullet("Pydantic V2 Documentation. (2024). https://docs.pydantic.dev/")
    add_bullet("SQLAlchemy 2.0 Unified Documentation. (2024). https://docs.sqlalchemy.org/")
    add_bullet("W3C Web Content Accessibility Guidelines (WCAG) 2.1. (2018). https://www.w3.org/TR/WCAG21/")

    print("Appendix and References built successfully.")

if __name__ == "__main__":
    build_appendix_and_references()
    doc.save(DOCX_OUT)
    print("Saved preview to DOCX.")
