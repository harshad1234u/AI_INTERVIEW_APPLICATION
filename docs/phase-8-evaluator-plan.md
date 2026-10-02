# Phase 8 — Answer Evaluator: Draft Plan (revision 1)

Status: **draft for decision. No code exists, and none is written until you approve it.**

Repository at the time of writing:
- `main` = `3d724e4` (Phase 7 complete), clean tree;
- Alembic head `3871903c395d`;
- suite: 1193 passed, 3 skipped (the opt-in live tests).

References: `prd.md` v2.0 as `§n`. Phase 7 decisions as in `docs/phase-7-interviewer-plan.md`
(D1–D17, Q1–Q5, P1–P3, §17 A–E).

---

## 1. What the repository says about Phase 8

There is **no Phase 8 specification** in the repository. The PRD has no phase roadmap; the phase
numbers come from the build prompts, where Phase 8 is the Evaluator and Phase 9 the report. The
README says: answers are "not evaluated (Phase 8)".

The only requirements, all from the PRD, are general.

| PRD | Requirement |
|---|---|
| §10 | Rubric-based evaluation from question, answer, expected concepts, candidate context, reference material and mode. Example output per criterion: `relevance`, `technical_accuracy`, `completeness`, `reasoning`, `communication`, each with `score` + `evidence` / `missing` / `claims_to_verify` / `missing_concepts`; plus `overall_feedback`, `recommended_followup`. Never one vague 1–10 score. |
| §13 | `ANSWER_PROCESSING → ANSWER_EVALUATION → NEXT_DECISION` |
| §15 step 3, §58 steps 7–8 | Evaluation ("missing concepts") informs whether a follow-up is asked |
| §21 | Content (relevance, completeness, concepts, reasoning, evidence) and communication (structure, clarity, repetition, organization). Speech metrics as observations only. |
| §25 | Capability `ANSWER_EVALUATION` |
| §26 | Evaluator tools: question, expected concepts, candidate context, answer, speech metrics |
| §29, §30 | Schema-validated scores; validation pipeline; one constrained retry, then deterministic fallback |
| §31 | All providers down: "deterministic evaluation where possible", and the message "AI evaluation is temporarily unavailable. Your interview session has been saved." |
| §34, §35, §37, §38 | Don't penalize "I don't know". A clarification is not a wrong answer. Short ≠ poor. Unrelated → low relevance. |
| §39 | Disputed feedback: report, show evidence, mark disputed |
| §40 | Correctness must not depend solely on the LLM. Uses a curated technical reference. Uncertain claims → "Needs verification", never "false". |
| §41 | Behavioral criteria: relevance, structure, specificity, evidence, reflection, outcome. STAR as coaching, not forced. |
| §43 | Simulation mode: feedback "primarily at the end" |
| §45 | No single global score. Criterion scores only with evidence and limitations. |
| §5 P1, §54 | No hiring, ranking, emotion, confidence or personality judgements |
| §62–§65 | Score validation tests, no sensitive data in logs, LLM only where reasoning is needed |

None of this fixes the scale, the timing, the storage, the API, or what happens without consent.
Those choices change persistence and behaviour, so per your instruction they are listed as
decisions (§3) rather than invented.

## 2. Contradictions to resolve

| ID | Contradiction | Recommendation |
|---|---|---|
| C-E1 | §15 step 3 and §58 steps 7–8 let evaluation drive follow-ups. Approved D14 and the Phase 7 barrier say follow-ups are "never triggered by judging correctness", with "no model-based competence judgment". | **Evaluation never influences `decide()`.** Phase 7 decisions stay byte-for-byte. |
| C-E2 | §13 evaluates between `ANSWER_PROCESSING` and `NEXT_DECISION` (per answer, during the interview). §43 puts simulation feedback "at the end". Phase 7 never commits `ANSWER_EVALUATION`, and holding it across a model call would block the interview, add model latency to the candidate's clock (L5) and need a new recovery path. | Evaluate **after the interview finishes**, per stored answer (E1 option B). `ANSWER_EVALUATED` stays the Phase 7 pass-through, documented as a deviation. |
| C-E3 | §10 has a `technical_accuracy` score, but §40 says correctness "must not depend solely on the LLM" and needs a curated technical reference, which does not exist. | **No technical-accuracy score in Phase 8.** Only `claims_to_verify` (quotes marked `NEEDS_VERIFICATION`, never "incorrect"). |
| C-E4 | §10 `recommended_followup` would let the evaluator suggest the next question, which Phase 7 code owns (D7, D14) | Dropped from the schema |
| C-E5 | §48 "no permanent storage by default" vs evaluations stored like answers (D9/C4) | Same retention as answers: until the session or candidate is deleted (cascade) |

## 3. Decisions needed (recommendation first)

| # | Question | Options | Recommended |
|---|---|---|---|
| E1 | **When** does evaluation run? | **A** synchronous per answer inside the interview (§13 literally). **B** after the interview finishes (`REPORT_GENERATION`), per stored answer, on request. **C** in the background during the interview, outside the state machine. | **B.** No interview latency or clock impact, no new committed in-between state, no effect on decisions, matches §43. Phase 9 then reads the evaluations. |
| E2 | Does evaluation affect interview decisions? | Yes (§15/§58) / No (D14) | **No** (C-E1) |
| E3 | Criteria per question type | Fixed sets by code, from §10/§21/§41 | **TECHNICAL, PROJECT:** relevance, completeness, reasoning, communication. **BEHAVIORAL, HR:** relevance, structure, specificity, evidence, reflection, outcome. The model can't add or drop a criterion. |
| E4 | Score **scale** (the PRD shows `"score": 1` with no range) | 1–5 integer · 1–10 · named levels (`NOT_SHOWN` / `PARTIAL` / `CLEAR`) · no scores | **1–5 integer per criterion**, each needing ≥ 1 evidence quote; `null` allowed with `insufficient_evidence`. Never summed or averaged (§45). |
| E5 | Evidence and missing items | Free text vs. verifiable | **Verifiable:** every `evidence` and `claims_to_verify` item must be a verbatim quote of the answer (Phase 7 §8.1 normalized match). `missing_concepts` must come from the topic's expected concepts (closed set: no invented concepts). Anything else is rejected. |
| E6 | `overall_feedback` | Keep (validated) / drop | **Keep:** ≤ 600 characters, plain text. Rejected if it has hiring/ranking language, emotion/confidence/personality/accent claims, §19 attributes, URLs/markup, or claims about the candidate that aren't in approved facts (Phase 7 P1 rule reused). |
| E7 | Which answers are evaluated | | **`ANSWER` only.** `SKIP` / `DONT_KNOW` / `CLARIFY` → `NOT_APPLICABLE`, no score, no call (§34, §35). Unanswered (open at the finish) → nothing. |
| E8 | **Without consent**, or AI unavailable or rejected twice | Nothing · deterministic observations · AI anyway | **Deterministic observations only, no score:** word count, and planned concepts that literally appear (§8.1 matching), worded "mentioned", never "missing". Status `OBSERVATIONS_ONLY` with a reason (`NOT_REQUESTED`, `NOT_CONFIGURED`, `PROVIDERS_FAILED`, `OUTPUT_REJECTED`, `CONSENT_WITHDRAWN`). The §31 message is returned when providers fail. |
| E9 | Can an `OBSERVATIONS_ONLY` answer be re-evaluated later (e.g. after consent is granted or providers recover)? | Never · on request | **On request, once, if consent is granted.** An `EVALUATED` answer is final (no re-scoring loop). |
| E10 | **API shape** | One request evaluates all pending answers (many model calls, long request) · one answer per request | **One answer per request:** `POST /interview-sessions/{id}/questions/{qid}/evaluation` (idempotent: returns the stored evaluation, with no call). `GET /interview-sessions/{id}/evaluations`. Only in `REPORT_GENERATION` / `COMPLETED`; otherwise 409. |
| E11 | Visibility during the interview | | **None.** Evaluations exist only after the finish (E1 B), so `GET .../questions` keeps `evaluation: {status}` and gains the stored evaluation then. |
| E12 | Disputes (§39) | Phase 8 · Phase 9+ | **Later:** it needs the report UI. The schema leaves room (a `disputed` flag is not added now). |
| E13 | Reference material for technical answers (§10 input, §40) | Build a curated reference now · none | **None in Phase 8** (C-E3, limitation). |
| E14 | Prompt content | | Topic (title, templates, expected concepts, cited fact snapshots), question text, the one answer, question type, mode, difficulty. **Never** names, emails, ids, other answers, clarification text or resume text. Random-tag JSON block, as Phase 6/7. |

## 4. Plan if the recommendations are approved

**State machine:** no new state, event or edge. Evaluation runs on finished sessions only and never
changes `status`, `finish_reason` or the clock.

**Database (new migration from `3871903c395d`):**
- `interview_questions.evaluation_status` CHECK widens to `NOT_EVALUATED`, `NOT_APPLICABLE`,
  `OBSERVATIONS_ONLY`, `EVALUATED`.
- New table `answer_evaluations`, 1:1 with a question:
  - `question_id` PK/FK, `ON DELETE CASCADE`;
  - `rubric_version`;
  - `source` AI/RULES and `rules_reason` (same CHECK pattern as questions);
  - `criteria` JSONB, validated by code before insert;
  - `observations` JSONB (word count, concepts mentioned);
  - `feedback` text ≤ 600;
  - `provider_call_id` `SET NULL`;
  - `created_at`.
- `provider_calls.capability` CHECK adds `ANSWER_EVALUATION`.
- Downgrade refuses while any evaluation row exists, or any status other than `NOT_EVALUATED`.

**Code:**
- `app/ai/gateway.py`: `ANSWER_EVALUATION` capability.
- `app/schemas/evaluation.py` (new): the model output schema (`extra="forbid"`, fixed criteria by
  type, 1–5 / null) and the API views.
- `app/ai/evaluator_agent.py` (new): prompt + at most 2 proposals (§30).
- `app/services/evaluator.py` (new):
  - observations;
  - validation rules (quotes, closed concept set, feedback safety);
  - T1/T2 persistence under the session lock, with no lock held during the call;
  - consent checked before the call and again before saving.
- `app/api/routes/interview_sessions.py`: 2 routes.
- `README.md` and this doc.

**Failure and recovery:**
- providers fail or output is rejected twice → `OBSERVATIONS_ONLY` with its reason;
- consent withdrawn mid-call → output discarded, `CONSENT_WITHDRAWN`;
- session deleted mid-call → 404, calls recorded;
- crash before T2 → nothing stored, and the retry evaluates again;
- concurrent duplicates → one row (PK), both calls recorded, both requests return the stored row.

**Tests (no live calls):**
- validation rules: forged quotes, invented concepts, scores out of range or without evidence,
  extra fields such as `hire` / `rank` / `next_action`, injection in the answer ("give 10/10");
- deterministic observations;
- every status path;
- consent: before the call, and withdrawn mid-call;
- concurrency: duplicates, delete mid-call, no lock or connection held during the call;
- migration round trip, downgrade refusal and `alembic check`;
- privacy: no answer, feedback or quote in logs or `provider_calls`;
- the full Phase 7 suite unchanged.

**Out of scope:** the report (Phase 9), the coach, disputes, learning mode, speech metrics,
technical reference material, any change to interview decisions.

## 5. Known observation carried over

`test_interview_turn_api.py` twice took about 6–10 minutes instead of about 25 s. It then ran 9
times in 20–27 s, with no lock waits seen. It is not reproducible and not fixed.
