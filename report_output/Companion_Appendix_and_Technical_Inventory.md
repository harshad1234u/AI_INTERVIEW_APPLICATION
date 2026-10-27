# Companion Appendix and Technical Inventory
## AI Interview Coach Project Report

**Institution:** K. Ramakrishnan College of Technology (Autonomous), Samayapuram  
**Department:** Computer Science and Engineering  
**Course:** CSB1303 – Object Oriented Analysis and Design  
**Date:** November 2026  

---

### 1. Source Code Inventory

| Subsystem | Directory / File | Lines of Code | Technical Purpose & Implemented Invariants | Status |
|---|---|---|---|---|
| **Backend Core** | `app/main.py` | 134 | Application factory, CORS middleware, 503 database degradation handler, production health guard | Implemented |
| **Backend Core** | `app/core/config.py` | 118 | Typed Pydantic settings loading from `.env`, SecretStr credentials, strict validator constraints | Implemented |
| **Backend Core** | `app/core/security.py` | 76 | `hashlib.scrypt` password hashing (N=16384, r=8, p=5), cryptographic session token generation | Implemented |
| **Backend DB** | `app/db/base.py` & `session.py` | 64 | Declarative Base with explicit naming conventions, connection engine, scoped session factory | Implemented |
| **Backend Models** | `app/models/candidate.py` | 52 | Candidate entity, scrypt hash, failed login counter, locked_until timestamp | Implemented |
| **Backend Models** | `app/models/auth_session.py` | 38 | SHA-256 session token hash, candidate foreign key cascade, absolute 7-day expiry check | Implemented |
| **Backend Models** | `app/models/resume.py` | 148 | Resume & CandidateFact entities, composite FK `(resume_id, candidate_id)`, provenance check | Implemented |
| **Backend Models** | `app/models/interview_session.py`| 162 | InterviewSession & ConsentEvent, plan JSONB, finish_reason check, active time tracking | Implemented |
| **Backend Models** | `app/models/interview_question.py`| 98 | InterviewQuestion entity, 10,000 char answer limit, evaluation status enum | Implemented |
| **Backend Models** | `app/models/answer_evaluation.py`| 112 | AnswerEvaluation & Criteria entities, 1-5 score bounds, verbatim evidence quote storage | Implemented |
| **Backend Models** | `app/models/expression.py` | 65 | QuestionExpressionObservation entity, 9 categorical observation counts (0-10,000 bound) | Implemented |
| **Backend Models** | `app/models/provider_call.py` | 54 | ProviderCall operational audit entity; zero candidate IDs, prompts, or outputs stored | Implemented |
| **Backend Models** | `app/models/usage_counter.py` | 42 | UsageCounter rate-limiting entity, compound PK `(scope, key, window_start)` | Implemented |
| **Backend AI** | `app/ai/gateway.py` | 266 | ModelGateway: routing, 20s timeout, bounded backoff, fallback cascade, schema validation | Implemented |
| **Backend AI** | `app/ai/providers.py` | 234 | Provider adapters for Gemini, Groq, NVIDIA over HTTPX Chat Completions | Implemented |
| **Backend AI** | `app/ai/profile_agent.py` | 145 | ProfileAgent: prompt boundary, verbatim grounding check against resume text | Implemented |
| **Backend AI** | `app/ai/planner_agent.py` | 186 | PlannerAgent: closed-set settings instructions, topic proposal schema, 1 re-request | Implemented |
| **Backend AI** | `app/ai/interviewer_agent.py`| 210 | InterviewerAgent: follow-up wording proposal, anchor term validation, presumption rules | Implemented |
| **Backend AI** | `app/ai/evaluator_agent.py` | 240 | EvaluatorAgent: rubric scoring proposal, evidence quote validation, neutral feedback rule | Implemented |
| **Backend Services** | `app/services/interview_state_machine.py` | 257 | Finite State Machine: transition table, row lock acquisition, atomic state writer | Implemented |
| **Backend Services** | `app/services/interviewer.py` | 385 | Turn decision engine, 60s deadline guard, anchor term matcher, pacing calculation | Implemented |
| **Backend Services** | `app/services/evaluator.py` | 340 | Rubric scoring, exact substring evidence verification, deterministic observation fallback | Implemented |
| **Backend Services** | `app/services/report.py` | 290 | Deterministic report compiler: shown clearly vs to practise items, zero aggregated scores | Implemented |
| **Backend Services** | `app/services/resume_extractor.py`| 470 | Pure Python pypdf text extraction, heading detection dictionary, verbatim fact parser | Implemented |
| **Backend Services** | `app/services/retry.py` | 185 | Retry session generator: copies to_practise topics into fresh READY session | Implemented |
| **Backend Services** | `app/services/limits.py` | 175 | Atomic PostgreSQL counter upsert, network SHA-256 keys, daily AI request budget | Implemented |
| **Backend Services** | `app/services/manual_facts.py`| 130 | Manual fact management, 100-fact cap, case-insensitive duplicate check | Implemented |
| **Frontend App** | `frontend/app/page.tsx` | 220 | Landing page, authentication guard, candidate profile card, resume upload card | Implemented |
| **Frontend App** | `frontend/app/interview/page.tsx` | 340 | Multi-stage interview screen coordinator, unfinished session recovery prompt | Implemented |
| **Frontend Components** | `frontend/components/interview/*` | 1,450 | UI components: `InterviewFlow`, `InterviewSetup`, `InterviewTurn`, `CameraPanel`, `VoicePanel`, `InterviewReport` | Implemented |
| **Frontend Lib** | `frontend/lib/api.ts` | 180 | Client-side fetch wrapper with credentials: "include", CSRF Origin headers | Implemented |
| **Frontend Lib** | `frontend/lib/exportDoc.ts` | 260 | Standalone escaped HTML document generator for plans and reports with strict CSP | Implemented |
| **Frontend Lib** | `frontend/lib/expressions.ts` | 170 | Face expression classification, sampling pacing, aggregate breakdown calculation | Implemented |
| **Frontend Lib** | `frontend/lib/voice.ts` | 195 | Speech chunking, voice selection heuristics, neutral speech metric measurements | Implemented |

---

### 2. Architecture & Design Invariant Summary

1. **LLM Proposes, Orchestrator Decides, Validator Verifies, Database Stores:**
   External AI models possess zero authority over application state, session transitions, candidate scoring, or timer progression.
2. **Untrusted Input Boundaries:**
   Resumes and student answers are treated as untrusted text strings. Prompt injection attempts remain inert text data and cannot influence system prompts or ratings.
3. **Verbatim Fact Provenance:**
   Candidate facts must originate from verified resume line substrings or explicit candidate manual entries. Only `APPROVED` facts are ingested into interview prompts.
4. **Deterministic Pacing & Time Limits:**
   Active elapsed time is calculated using database clock timestamps. If less than 60 seconds remain before a turn, the interview automatically concludes with `TIME_LIMIT`.
5. **Formative, Non-Aggregated Feedback:**
   Rubric evaluations require exact substring quotes from student answers. Criterion scores (1–5) are never summed, averaged, or converted into ranking scores.
6. **Privacy-by-Design Biometrics:**
   Facial expression signals are evaluated locally on-device via WebGL neural networks. Raw camera frames and audio are never transmitted or permanently stored.

---

### 3. Automated Test Evidence Summary

- **Backend Pytest Suite:** 4,693 automated tests collected across 26 test modules in `backend/tests/`. All tests pass against an isolated PostgreSQL test database (`ai_interview_coach_test`).
- **Frontend Test Suite:** 45 automated unit tests in `frontend/lib/*.test.ts` executed via `node --test` with 100% pass rate.
- **Browser E2E Journey:** 37 comprehensive browser checks executed by `e2e/journey.mjs` using headless Microsoft Edge over Chrome DevTools Protocol against real backend and database services. All 37 checks passed.
- **Static Analysis:** TypeScript compilation (`tsc --noEmit`) and ESLint checks report zero errors.

---

### 4. Known Limitations & Constraints

1. **Production Flag:** In production mode (`ENVIRONMENT=production`), application routes are disabled by design, serving only `/api/health` until full domain HTTPS and email recovery pipelines are provisioned.
2. **Account Recovery:** Password reset and email verification workflows are not yet implemented and require integration with an external transactional email provider (e.g., SendGrid or AWS SES).
3. **Linguistic Scope:** Heuristic regexes and heading detection rules are optimized for English-language technical resumes and responses.
4. **Scanned Documents:** PDF parsing requires text-based PDF formats; scanned, image-only documents require future integration of an asynchronous OCR pipeline.
