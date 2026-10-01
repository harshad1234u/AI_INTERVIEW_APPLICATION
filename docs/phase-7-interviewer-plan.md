# Phase 7 — Interviewer: Final Implementation Specification (revision 4)

Status: **final plan. Decisions approved on 2026-10-01. Implementation not started; it needs your
explicit go-ahead.** One open item (O1, §4) is recorded rather than decided, because it was not
part of the approved wording.

References: `prd.md` v2.0 as `§n (Lx)`, where Lx is the line number. Code: `main` after commit
`489e853`.

---

## 1. Repository state at the time of writing

| Item | State |
|---|---|
| `1307770` | Baseline: Phases 1–6 and plan revision 1 |
| `489e853` | `fix(planner): normalize fallback project deduplication`. Four files: `README.md`, `backend/app/api/routes/interview_sessions.py`, `backend/app/services/interview_planner.py`, `backend/tests/test_interview_planner.py`. |
| This document | Committed on its own, after `489e853` |
| Phase 7 code | None exists. The only match for Phase 7 identifiers in the source is the pre-existing provider field `CallRecord.finish_reason`: the model's stop reason, unrelated to the session finish reason in §9. |
| Tests before the fix B commit | Planner files: 371 passed. Full suite: 918 passed, 2 skipped (the opt-in live-provider tests). |

### Fix B (committed in `489e853`)
- `uncited_project` now applies to AI proposals only (`planner_agent.py:146` is the only AI
  caller). Fallback text is fixed catalog wording whose only candidate text is the cited project.
  `basis` is still derived from citations, so generic topics stay `GENERIC` with no facts.
- Fallback projects are deduped with `_key()`, the same normalization as the duplicate
  topic/question rules.
- Regression tests:
  - 14 common-word names × 4 modes × 3 durations;
  - a project named `Project`;
  - case/space/punctuation variants;
  - a guard on the catalog placeholders;
  - AI proposals naming an uncited project are still rejected.

---

## 2. Approved decisions

| # | Decision (as approved) |
|---|---|
| D1 | Bounded, answer-grounded follow-ups, at most **2 per question**. No evaluation-based claims before Phase 8. |
| D2 | Explicit, persisted, **session-level** AI consent. Checked before every relevant model call and again immediately before saving model output. No consent → deterministic operation. |
| D2b | The same consent policy governs **Phase 6 Planner** model calls |
| D2c | Consent changes are recorded with a timestamp and the resulting state. Answers, prompts, provider payloads and secrets are never logged. |
| D3 | At most **2 rephrases per question** |
| D4a | Count **active interview time**, excluding explicit pauses |
| D4b | Reject late answers with a documented conflict response, preserve earlier answers, and do not let a late submission change the interview |
| D4c | Closing the browser tab does **not** pause. Only an explicit PAUSE stops active time. |
| D5 | Answers of at most **10,000 characters**, validated consistently, with a clear error when oversized |
| D6 | **Simulation mode only.** No hiring decisions, employer evaluations or candidate rankings. |
| D7 | The model proposes question wording and a phrase grounded in the answer. Code owns topic selection, competency, difficulty, action selection and completion. |
| D8 | Skip topics that depend on facts the candidate has withdrawn. Fact approval is revalidated before a fact-dependent topic is used and before AI output is persisted. |
| D9 | Answers are retained until the session or candidate is deleted, with documented safeguards. The conflict with §48 is documented. |
| D10 / D10a | Persisted `evaluation_status = NOT_EVALUATED` per answer, with documented semantics. No fabricated evaluation. |
| D11 | Finished sessions may stay in `REPORT_GENERATION` until Phase 9. An ungenerated report is **never** shown as completed. |
| D12 | The validated plan's opening question is used verbatim. Stored plan text is treated as untrusted. |
| D13 | Git baseline (done: `1307770`) |
| D14 | Follow-ups triggered by deterministic rules, never by judging correctness or completeness |
| D15 | Deterministic follow-up templates when consent or AI is absent. If no suitable follow-up exists, advance to the next planned topic. |
| D16 | After the follow-up limit, go to the next **topic** (§13, §58). The §17 conflict is documented (C1). |
| D17 | A controlled, application-determined `finish_reason`, separate from status: `PLAN_COMPLETED`, `TIME_LIMIT`, `CANDIDATE_ENDED`. The model never selects it. Sessions finished earlier keep NULL. |
| Q1 | New system event `TIME_EXPIRED` with explicit transitions into `REPORT_GENERATION`. `END_INTERVIEW` gains no new edge. |
| Q2 | A late-answer request **atomically** closes the expired interview (`TIME_LIMIT`) without saving the answer and returns a conflict. It is safe under concurrency. |
| Q3 | No new question starts with **less than 60 s** remaining. Completion follows the approved path. |
| Q4 | Follow-ups respect the current topic's deterministic time allocation **and** the cap of 2 |
| Q5 | The planner's `use_ai` flag is **removed**. Session consent is authoritative. |
| Wording | Follow-up template `"You mentioned {term}. Can you tell me more about that?"`, fallback `"Could you elaborate on your answer?"`. Late-answer message `"The interview time limit was reached, so this answer was not saved."` |

---

## 3. PRD traceability and documented contradictions

| Decision | PRD basis |
|---|---|
| D1, D14, D15 | §16 (L622–660): follow up only on what the candidate actually mentioned, no invented tech, not indefinitely. §17 (L670): max 2. §37 (L1281): don't classify short answers as poor. §65 (L2236–2242): deterministic logic where possible. |
| D2–D2c | §48 (L1614, L1620): "explicit consent", "third-party AI processing disclosure". §64 (L2207): don't log sensitive raw data. §28 (L1059–1088): user content is untrusted. |
| D4, Q1–Q4 | §12 (L500): orchestrator owns "interview timeout". §14 (L562–563): `duration_limit`, `time_remaining`. §15 (L606–616): follow-up limit, next topic, "Reserve time for interview completion". §16 (L662): "topic coverage/time remaining". §65 (L2219, L2236). |
| D6 | §3 (L64–75): not hiring or ranking software. §5 P1 (L133–145). §43 (L1440–1457). §54 (L1792–1795). |
| D7 | §5 P2 (L149–164). §12 (L503) "The LLM does not directly control these". §29 (L1105–1122). §57 (L1904–1910). |
| D8 | §18 (L709): only trust levels 1–2 personalize |
| D10 | §13 (L524–528): the evaluation step. §31 (L1184): wording precedent. §45 (L1519): no unsupported scores. |
| D11, D17 | §13 (L542–546). §44 (L1468) "Questions Completed". §59 (L2054) partial report. |
| D12 | §32 (L1188–1198): curated questions. §28: stored text is data. |

| ID | Contradiction | Recorded resolution |
|---|---|---|
| C1 | §17 (L677–680) "move to next competency" vs §13 (L534) / §58 (L1999–2001) "next topic" | D16: next topic |
| C2 | §61 (L2089–2093) "If the user closes the browser: Session = PAUSED" vs D4c | Deliberate deviation (D4c). The candidate keeps control via explicit PAUSE (§61 L2103). |
| C3 | §60 (L2083) "Do not lose the candidate's response" vs D4b | Deliberate deviation (D4b). Mitigated by the 409 message and the frontend keeping the unsent draft locally (F7). |
| C4 | §48 (L1622) "no permanent storage by default" vs D9 | Deliberate deviation (D9) with safeguards (§10.3). A project-wide retention policy remains future work. |
| C5 | §12 owns the timeout, but §13 has no timeout edge | Resolved by Q1 (`TIME_EXPIRED`) |

---

## 4. Open item (recorded, not decided)

**O1: duplicate scope of the fallback question.** `"Could you elaborate on your answer?"` is fixed
text, but §33 (L1202–1216) duplicate protection compares every question against the whole
session's history. Applied literally, the elaboration question could be asked only **once per
interview**. The second time, it is a duplicate, so code advances to the next topic (D15).
Options:
- **A** apply §33 literally (once per interview);
- **B** exempt this one fixed prompt from the session-wide check, but allow it at most once per
  topic question (it refers to a different answer each time).

The implementation follows **A** unless you choose B: A applies existing rules unchanged and
needs no new exemption. This affects only consent-off or AI-failure interviews.

---

## 5. Architecture

Unchanged principles:
- `decide()`, a pure code function, chooses every action and the finish reason.
- The InterviewerAgent writes wording only, and only for a FOLLOW_UP or REPHRASE that code already
  chose.
- The gateway routes `QUESTION_GENERATION`.
- The state machine applies every event under a row lock.
- No agent framework and no new dependency (same justification as Phase 6, README "Agent
  framework"). The stdlib (`difflib`, `re`, `unicodedata`, `secrets`) suffices.
- The agent imports only `app.ai.gateway`, never a provider SDK.

### 5.1 `decide()`: in order, first match wins

```text
1. time_limit_reached (elapsed ≥ limit)                         → finish TIME_LIMIT
2. a question would start and remaining < 60 s (Q3)             → finish TIME_LIMIT
3. no question yet (ASKING)                                     → TOPIC(first valid topic)
4. last answer CLARIFY and rephrase_index < 2 (D3)              → REPHRASE(last question)
5. last answer CLARIFY (limit) / SKIP / DONT_KNOW               → NEXT_TOPIC
6. last answer ANSWER and follow_up_due() (§7) and wording available (§8)
                                                                → FOLLOW_UP
7. otherwise                                                    → NEXT_TOPIC
NEXT_TOPIC with no valid topic left (D8 skips included)         → finish PLAN_COMPLETED
```

"Finish" means `FINISH(reason)` from NEXT_DECISION, or `TIME_EXPIRED` from ASKING/WAITING
(§6.1). Inputs: the stored plan (schema-revalidated on load), the question history, the
still-approved facts, the active clock, consent and gateway availability. **Never** model output
or any judgement of answer quality.

### 5.2 Where each question's text comes from

| Action | Consent granted and gateway configured | Otherwise, or AI wording rejected or failed |
|---|---|---|
| TOPIC | The plan topic's first template, verbatim (D12). If it is a duplicate (§33), the next template. If all are duplicates, the topic is skipped. | Same (no model call either way) |
| FOLLOW_UP | Agent returns `{question, anchor}`, validated (§8.2) | Deterministic template (§8.1) |
| REPHRASE | Agent returns `{question}`, validated | Next unused template of the topic; else `"Let me put that another way. This question is about {topic}: {question}"` |
| FINISH / TIME_EXPIRED | No question | Same |

---

## 6. State machine, deadline and time accounting

### 6.1 Transition table changes (Q1)

| Change | Detail |
|---|---|
| New system event | `TIME_EXPIRED`: raised only by the application, never accepted over HTTP (not a `ClientAction`) |
| New edges | `(ASKING, TIME_EXPIRED) → REPORT_GENERATION`, `(WAITING_FOR_ANSWER, TIME_EXPIRED) → REPORT_GENERATION` |
| NEXT_DECISION | Uses the existing `FINISH` with a reason |
| PAUSED | No edge needed: the clock is stopped while paused, so a paused session cannot expire |
| `END_INTERVIEW` | Unchanged: still only from WAITING_FOR_ANSWER and PAUSED |
| `finish_reason` in `apply_event` | Set on entering REPORT_GENERATION. `END_INTERVIEW` → `CANDIDATE_ENDED`. `TIME_EXPIRED` → `TIME_LIMIT`. `FINISH` **must** carry `PLAN_COMPLETED` or `TIME_LIMIT`, just as `PLAN_READY` must carry a plan; anything else raises `ValueError`. |

### 6.2 Active-time clock (D4a, D4c)

- Session columns `active_seconds` (double precision, accumulated) and `active_since` (timestamptz,
  non-null while running). They are kept by `apply_event`, using `clock_timestamp()` (database
  time, never the application server's clock):
  - START_INTERVIEW and RESUME: `active_since = clock_timestamp()`;
  - PAUSE and every transition into REPORT_GENERATION: `active_seconds += clock_timestamp() −
    active_since`, then `active_since = NULL`.
- `elapsed = active_seconds + (clock_timestamp() − active_since if running)`,
  `limit = plan.settings.duration_minutes × 60`, `remaining = limit − elapsed`. Values are exact
  seconds (float); there is no rounding in decisions.
- **Pauses** stop the clock (explicit PAUSE only).
- **Tab closure** stops nothing: the clock runs on (C2).
- **Server restarts / outages** also count, because the clock is wall time minus explicit pauses
  (limitation L5). All clock state is in the database, so a restart loses nothing and the next
  request computes the same elapsed value.
- **API display:** `time_remaining_seconds = max(0, floor(remaining))`. This is display only;
  decisions use the exact value.

### 6.3 Deadline enforcement: atomic, lazy, deterministic

There are no background jobs. **Every interview write request** first runs `enforce_deadline`
inside its locked transaction: `POST /answers`, `POST /questions/next` (T1 and T2) and
`POST /actions` (PAUSE, RESUME, END_INTERVIEW).

| Status at lock time | Condition | Effect (same transaction) |
|---|---|---|
| ASKING | `elapsed ≥ limit` **or** `remaining < 60 s` (no question may start) | `TIME_EXPIRED` → REPORT_GENERATION, `TIME_LIMIT` |
| WAITING_FOR_ANSWER | `elapsed ≥ limit` | `TIME_EXPIRED` → REPORT_GENERATION, `TIME_LIMIT`. The open question stays unanswered. |
| NEXT_DECISION | `elapsed ≥ limit` | `FINISH(TIME_LIMIT)`. (`remaining < 60 s` is handled by `decide()` step 2, same result.) |
| PAUSED, READY, REPORT_GENERATION, COMPLETED, pre-plan | — | Nothing |

- **Exactly 60 s remaining:** a question may start (the rule is `remaining < 60` → finish).
- **Inside the reserve while WAITING:** the open question can still be answered until
  `elapsed ≥ limit`.
- **Interviews shorter than the reserve:** durations are `Literal[15, 30, 45]` minutes, so this
  cannot happen through the API. The rule still covers it uniformly: from ASKING with
  `remaining < 60`, no question starts and the session goes `TIME_EXPIRED` → `TIME_LIMIT` with zero
  questions. A unit test calls `decide()`/`enforce_deadline` directly with a 30 s limit.

### 6.4 Late answers (D4b, Q2)

`POST /answers` with the session lock held:

1. The question must belong to the session; otherwise `404`.
2. The question is already answered: identical → `200` replay, nothing written; different → `409`.
3. `enforce_deadline`. If it fires, the closure is committed.
4. If status is now REPORT_GENERATION with `TIME_LIMIT` and the question is unanswered: `409`
   `{"detail": "The interview time limit was reached, so this answer was not saved."}`. The
   answer text is never stored, logged or sent anywhere. Earlier answers are untouched.

**Concurrency:** requests serialize on the row lock. The first request after expiry applies
`TIME_EXPIRED` exactly once. Every later late answer finds REPORT_GENERATION/`TIME_LIMIT` and gets
the same `409`. A concurrent `END_INTERVIEW` either wins before expiry (`CANDIDATE_ENDED`) or
loses after it (`409` naming REPORT_GENERATION). A request that already succeeded before expiry,
when retried, is an identical replay (`200`), because step 2 precedes step 3.

**Frontend requirement (not implemented here):** on this 409, keep the unsent draft locally and
show it with the message (F7, §60 L2069–2083).

### 6.5 In-flight model calls and the deadline

- The gateway call deadline is `min(now + 30 s, moment remaining reaches 60 s)`, so no model call
  is started or continued into the reserve.
- In T2, under the lock, `enforce_deadline` and the reserve check run again. If either fires, the
  generated wording is discarded, the provider calls are recorded, and the session finishes
  (`TIME_EXPIRED` from ASKING, `FINISH(TIME_LIMIT)` from NEXT_DECISION). The response is
  `200 {question: null, finish_reason: "TIME_LIMIT"}`.

---

## 7. Topic-time allocation and follow-ups (Q4, D1, D14)

- `topic_share = limit / topics_total`, where `topics_total` = the number of topics in the stored
  plan. It is computed in exact seconds, fixed for the session, never rounded, and never
  redistributed when a topic is skipped (D8). A skipped topic's unused time simply remains as
  overall slack.
- `topic_used = elapsed_now − clock_at_ask(first question of the current topic)`. Every question
  row stores `clock_at_ask` (the elapsed active seconds when it was asked). Rephrases, follow-ups
  and generation latency within the topic all count.
- `follow_up_due()` is true only if all of these hold:
  - the last answer's kind is `ANSWER`;
  - the last question's `followup_index < 2`;
  - `topic_used < topic_share`;
  - `remaining ≥ 60 s` (Q3).
- **Exhausted budget:** `topic_used ≥ topic_share` → no follow-up, next topic, even if fewer than 2
  follow-ups were asked.
- Rephrases (CLARIFY) are capped by D3 and the reserve only: the candidate asked for
  clarification, so the topic share does not block it.
- **Example:** 15 min and 5 topics give `topic_share` = 180 s. 45 min and 15 topics also give 180 s.
  Shorter shares cannot occur with the allowed durations and the planner budget
  (`duration // 3` topics).
- A follow-up never claims anything about answer quality (D1). It is not triggered by answer
  length or content quality, only by kind, cap and time.

---

## 8. Follow-up and rephrase wording

### 8.1 Deterministic template (D15; no consent, no gateway, or AI wording rejected or failed)

1. **Candidate phrases:** the current topic's vocabulary, in plan order: cited fact snapshots,
   then the planned expected concepts. For each, look for a whole-phrase, case-insensitive match
   (NFKC-normalized) **in the current answer**.
2. **Inserted term** = the matched span copied exactly from the answer. It is a short exact
   phrase from the answer that is also known plan vocabulary. Arbitrary spans are never extracted,
   so injected instructions in an answer cannot be echoed back as a question.
3. **Term safety checks.** The term is rejected (try the next phrase) unless all of these hold:
   - 1–60 characters, at most 6 words, contains a letter;
   - no control characters or newlines;
   - none of `{ } < > [ ] \``;
   - no URL;
   - no §19 attribute (`SENSITIVE`);
   - not used as a term or anchor earlier in this topic.
4. A term passes → `"You mentioned {term}. Can you tell me more about that?"`. The result also
   passes duplicate protection (§33).
5. No term passes → `"Could you elaborate on your answer?"`. If that is a duplicate (O1), there is
   no suitable follow-up and code advances to the next topic (D15).

"You mentioned …" is used only when the phrase literally occurs in the answer, so the template
never invents a candidate fact.

### 8.2 AI wording (consent granted, gateway configured)

Output schemas (`extra="forbid"`):
- `FollowUpWording {question: 1–300 chars, anchor: 2–100 chars}`;
- `RephraseWording {question: 1–300 chars}`.

There is no field for an action, status, event, id, topic, competency, difficulty, score, finish
or reason.

Deterministic rules (codes only, never content):

| Code | Rule |
|---|---|
| `anchor_not_in_answer` | The anchor (NFKC, casefold, whitespace-collapsed) is a substring of the answer and contains a letter |
| `anchor_not_mentioned` | The question names the anchor |
| `unanchored_reference` | "you mentioned/said/told/described" without an anchor |
| `uncited_project` | The model's own words name a plan project the topic doesn't cite |
| `ungrounded_claim` | A question that presumes something about the candidate uses a technical term found nowhere in the cited facts, plan topic or this topic's answers |
| `evaluative_language` | Right/wrong/correct/incorrect/incomplete/"you missed"/"you forgot"/"good answer"/"not quite" (D1) |
| `hiring_language` | Hire/hired/hiring/unsuitable/rank/ranking/employable (D6, §5 P1) |
| `sensitive_attribute` | §19 words outside the cited facts (the anchor is not exempt) |
| `url_or_markup` | URLs, HTML tags, markdown links |
| `duplicate_question`, `rephrase_identical` | §33: NFKC/casefold/punctuation-normalized equality, or `difflib` ratio ≥ 0.85, against the session's questions (a rephrase excludes its source but must differ from it) |

One constrained re-request names the codes (§30). If that fails, the §8.1 path or the §5.2
REPHRASE fallback is used. Residual risks: L1.

### 8.3 Prompt-injection protection

- Untrusted inputs: answers, approved facts, the stored plan (including AI-written text) and
  generated question text.
- The system message contains only closed-set values the application writes (enums, limits,
  counts).
- Data goes in the user message as JSON strings inside a tag with a random name per request:
  - only the current topic (title, templates, expected concepts, cited fact snapshots);
  - the last answer only for FOLLOW_UP;
  - **never** clarification text, other answers, other topics, ids, names, emails or resume text.
- Model output is untrusted. It is schema-validated, rule-validated, stored as data, and rendered
  as plain text (F3).

---

## 9. Consent (D2, D2b, D2c, Q5)

- **State:** `interview_sessions.ai_consent` (bool, default false) is the value checked under the
  row lock. Every change also inserts `interview_consent_events(session_id, granted, changed_at)`
  in the same transaction. A request that repeats the current value records nothing.
- **API:** `PUT /api/interview-sessions/{id}/ai-consent {"granted": bool}`.
  - Granting is allowed in every status except COMPLETED (`409`). Withdrawing is always allowed.
  - Available from PROFILE_REVIEW on, so consent can precede planning.
  - `GET` returns the current value and the history `[{granted, changed_at}]`.
- **Planner (D2b, Q5):** `PlanRequest` loses `use_ai`; sending it now gives `422`.
  - `prepare_planning` reads consent: no consent → no model call, `rules_reason = NOT_REQUESTED`.
    The value is kept so stored plans stay valid; the README redefines it as "AI not consented".
  - `save_plan` re-reads consent under the lock: withdrawn → the AI plan is discarded, and
    `fallback_plan(…, CONSENT_WITHDRAWN)` is built and saved in the same transaction. The calls
    are recorded.
- **Interviewer:** same two checks in `prepare_turn` (T1) and `save_turn` (T2). A withdrawal
  during a call → output discarded, deterministic wording computed and saved inside T2,
  `rules_reason = CONSENT_WITHDRAWN`, calls recorded.
- **What withdrawal cannot do:** data sent before a withdrawal cannot be recalled from a provider.
  The disclosure (F2) must say so.
- **Logging:** session id and the new value only. Never answers, prompts, payloads or keys.
- **Outside session consent:** the Phase 4 ProfileAgent (a resume-level button with its own
  disclosure) is not governed by session consent. This is out of D2b's scope (limitation L6).

---

## 10. Persistence, migration and API changes (exact)

### 10.1 Migration `<rev>_add_interviewer` (revises `b8d14f2a9c63`)

| Table | Change |
|---|---|
| `interview_sessions` | + `ai_consent boolean NOT NULL DEFAULT false`; + `active_since timestamptz NULL`; + `active_seconds double precision NOT NULL DEFAULT 0` with CHECK `active_seconds >= 0`; + `finish_reason varchar(20) NULL` with CHECK `IN ('PLAN_COMPLETED','TIME_LIMIT','CANDIDATE_ENDED')`; + CHECK `finish_reason IS NULL OR status IN ('REPORT_GENERATION','COMPLETED')`. Existing rows: consent false, clock 0/NULL, finish_reason NULL (no guessing). No reverse CHECK, because existing tests insert raw rows in those statuses. |
| `interview_consent_events` (new) | `id bigint GENERATED ALWAYS AS IDENTITY PK`, `session_id uuid NOT NULL` FK → sessions **ON DELETE CASCADE**, `granted boolean NOT NULL`, `changed_at timestamptz NOT NULL DEFAULT clock_timestamp()`, index `(session_id, id)` |
| `interview_questions` (new) | `id uuid PK default gen_random_uuid()` · `session_id` FK **CASCADE** · `seq int ≥ 1`, `UNIQUE(session_id, seq)` · `topic_position int ≥ 1` · `kind` CHECK `IN ('TOPIC','FOLLOW_UP','REPHRASE')` · `followup_index smallint` CHECK 0–2 (TOPIC ⇒ 0, FOLLOW_UP ⇒ ≥ 1) · `rephrase_index smallint` CHECK 0–2 (REPHRASE ⇔ ≥ 1) · `text varchar(400)` non-blank · `source` CHECK `IN ('AI','RULES')` · `rules_reason` (CHECK `(source='AI') = (rules_reason IS NULL)`) · `anchor varchar(100) NULL` (only AI follow-ups) · `provider_call_id` FK → provider_calls **SET NULL** · `asked_at timestamptz DEFAULT clock_timestamp()` · `clock_at_ask double precision ≥ 0` · `answer_kind` CHECK `IN ('ANSWER','CLARIFY','DONT_KNOW','SKIP')` · `answer_text text` CHECK `char_length ≤ 10000` · `answered_at timestamptz` · `evaluation_status` CHECK `IN ('NOT_EVALUATED')` · CHECK all of `answer_kind, answered_at, evaluation_status` are NULL together or non-NULL together · partial unique index `(session_id) WHERE answered_at IS NULL` (one open question) |
| `provider_calls` | capability CHECK adds `'QUESTION_GENERATION'` |
| Downgrade | Refuses while any `interview_questions` or `interview_consent_events` row exists (Phase 6 precedent), then reverses everything and deletes `QUESTION_GENERATION` call metadata |

`RulesReason` gains `CONSENT_WITHDRAWN`. Plans store this in JSONB and questions in a CHECKed
column, so both are updated together.

### 10.2 API (all in the existing router; none served in production)

| Endpoint | Change | Responses |
|---|---|---|
| `PUT /api/interview-sessions/{id}/ai-consent` | **new** `{"granted": bool}` | `200 {session_id, granted, changed_at}` · `404` · `409` (grant after COMPLETED) · `422` |
| `GET /api/interview-sessions/{id}/ai-consent` | **new** | `200 {session_id, granted, history[]}` · `404` |
| `POST /api/interview-sessions/{id}/questions/next` | **new** `{}` | `200 TurnResult` (new question; or the open question with no model call; or `question: null` with `finish_reason`) · `409` PAUSED "Resume the interview first." / not started / profile changed · `404` · `422` · `503` |
| `POST /api/interview-sessions/{id}/answers` | **new** `{"question_id", "kind", "text"}` | `200` (stored → NEXT_DECISION, or identical replay) · `409` late-answer message / answered differently / wrong status · `404` · `422` · `503` |
| `GET /api/interview-sessions/{id}/questions` | **new** | `200` history with `evaluation: {"status": "NOT_EVALUATED"}` per answer · `404` |
| `POST /api/interview-sessions/{id}/plan` | **changed**: no `use_ai`; consent governs | as Phase 6, plus `422` for `use_ai` |
| `POST /api/interview-sessions/{id}/actions` | **changed**: deadline enforcement first | as Phase 5 |
| `GET /api/interview-sessions/{id}` | **unchanged** (key set pinned by a Phase 5 test) | — |

- **`TurnResult`:** `{session_id, status, finish_reason, ai_consent, question: QuestionView|null,
  progress: {topics_total, time_remaining_seconds, deadline_reached}, model_calls[]}`.
- **`QuestionView`:** `{id, seq, topic_position, topic, competency, question_type, difficulty,
  basis, kind, followup_index, rephrase_index, text, source, rules_reason, asked_at}`, plus
  `answer: {kind, text, answered_at, evaluation: {status}}` once answered.
- **Not exposed:** anchor, provider call id.
- **D5 validation:** `text` is required and non-blank for `ANSWER`, optional otherwise, and at most
  10,000 characters after stripping. The same limit is enforced in Pydantic **and** by the DB
  CHECK. Oversized input → `422` with `"Answer is too long: the limit is 10,000 characters."`.
  Nothing is stored.

### 10.3 Answers, `NOT_EVALUATED`, finish reasons, retention, deletion

- **`evaluation_status = NOT_EVALUATED` (D10a):** the answer is stored and has **not** been
  evaluated. No score, rubric result, evidence or missing-concept analysis exists for it.
  - It is set in the same transaction as the answer.
  - Phase 7 decisions never read it.
  - Phase 8 adds values and may evaluate stored answers later.
- **Finish reasons (D17):** set only by `apply_event` from code paths; no model output can reach
  them.
  - `PLAN_COMPLETED`: no valid topic left.
  - `TIME_LIMIT`: deadline or reserve.
  - `CANDIDATE_ENDED`: `END_INTERVIEW`.
- **D11:** the session stays in `REPORT_GENERATION`. No API field says a report exists, and
  `COMPLETED` is reachable only via Phase 9's `REPORT_READY`.
- **Retention (D9) safeguards:**
  - answers are kept only in `interview_questions`;
  - never in logs, `provider_calls`, error messages or exception text;
  - sent to a provider only with consent, and only the last answer for a FOLLOW_UP;
  - `DELETE /interview-sessions/{id}` and `DELETE /candidates/{id}` remove questions, answers and
    consent events by cascade;
  - `provider_calls` keep no link.
  - The conflict with §48 L1622 is recorded (C4).

---

## 11. Concurrency, idempotency, recovery, provider credits

- **No transaction or lock during model calls.**
  - T1 reads, then commits (connection released).
  - The model call runs.
  - T2 locks and re-checks: status, turn token (question count), deadline and reserve, consent,
    and cited facts (D8).
  - Test pattern from Phase 6: `pool.checkedout() == 0` and `FOR UPDATE NOWAIT` succeed during
    the call.
- **D8 revalidation:**
  - T1 drops topics whose cited facts are no longer APPROVED and unchanged
    (`require_cited_facts_unchanged`, reused).
  - T2 re-checks them before persisting **any** question of a fact-dependent topic, AI or RULES.
    If they changed: `409` "Your approved profile changed. Please try again."; the retry skips the
    topic.
- **Idempotency:**
  - `/questions/next` while WAITING returns the open question (no model call).
  - An identical `/answers` replay → `200`, nothing written.
  - A consent PUT with the same value is a no-op.
  - Unique `(session_id, seq)` and one open question per session are DB backstops.
- **Duplicates and races:**
  - Two concurrent `/questions/next` may both call a model. Both calls are recorded, one question
    persists, and both requests return it.
  - `/answers` vs PAUSE/END/consent/expiry serialize on the row lock (§6.4).
- **Interrupted calls:**
  - A crash or timeout before T2 commits leaves the previous resting state (ASKING, NEXT_DECISION
    or WAITING); the next request continues.
  - Answers committed before an interruption are never lost.
  - Clock state is in the DB (§6.2).
- **Provider credits:** spent but unused when
  - concurrent duplicates race;
  - a constrained re-request follows rejected wording;
  - consent is withdrawn mid-call;
  - time expires mid-call;
  - a fact changes mid-call.

  Every such call is recorded in `provider_calls`. Bounds per turn: at most 2 proposals, each
  bounded by the gateway policy, the whole turn by the 30 s turn deadline, and neither can run
  into the 60 s reserve. TOPIC and FINISH make **no** call, and retries while WAITING make no
  call.

---

## 12. Existing tests that must change (deliberately)

| File | Change | Why |
|---|---|---|
| `tests/test_interview_state_machine.py` | Add the two `TIME_EXPIRED` edges to `PRD_EDGES` (`test_table_is_exactly_the_prd_lifecycle`). The complement count becomes `13 × 18 − 20` (`test_forbidden_list_is_the_full_complement`). Add `TIME_EXPIRED` to the system-event set (`test_client_actions_are_exactly_the_five_and_no_system_event`). The parametrized permitted/forbidden tests derive from `PRD_EDGES` automatically. | Q1. The file says changes must be made "on purpose". |
| `tests/test_interview_sessions.py` | The `drive` helper passes `finish_reason="PLAN_COMPLETED"` when it applies `FINISH` (used at L310–311) | D17: FINISH must carry a reason |
| `tests/test_interview_plan_api.py` | The **13** `use_ai=True` call sites grant session consent first instead: 12 via the `plan()` helper (L143, 163, 201, 210, 225, 279, 311, 329, 345, 359, 374, 431) and 1 raw JSON body (L492). The L123 comment mentions `use_ai` and is reworded. A new assertion checks that `use_ai` is now `422`. | Q5 |

Every other existing test must pass unchanged.

---

## 13. File-by-file scope

| File | Change |
|---|---|
| `backend/app/services/interview_state_machine.py` | `TIME_EXPIRED` + 2 edges; clock bookkeeping; `finish_reason` handling |
| `backend/app/models/interview_session.py` | 4 columns + CHECKs; `InterviewConsentEvent` model |
| `backend/app/models/interview_question.py` (new), `backend/app/models/__init__.py` | question/answer model |
| `backend/alembic/versions/<rev>_add_interviewer.py` (new) | §10.1 |
| `backend/app/ai/gateway.py` | `ModelCapability.QUESTION_GENERATION`; optional absolute `deadline` (`None` = today's behavior) |
| `backend/app/ai/interviewer_agent.py` (new) | prompt builder, wording proposals, one constrained re-request |
| `backend/app/schemas/interview_turn.py` (new) | API and model schemas, enums |
| `backend/app/schemas/interview_plan.py` | remove `PlanRequest.use_ai`; `RulesReason.CONSENT_WITHDRAWN` |
| `backend/app/services/interviewer.py` (new) | `decide`, `enforce_deadline`, topic allocation, templates and term extraction, wording validation, duplicates, `submit_answer`, `prepare_turn`/`save_turn`, consent service |
| `backend/app/services/interview_planner.py` | consent checks in `prepare_planning`/`save_plan`; grounding helpers made public for reuse |
| `backend/app/api/routes/interview_sessions.py` | the 5 new routes; planner consent; deadline enforcement in `/actions` |
| `README.md` | Phase 7 section: routes, consent, deadline, placeholder, finish reasons, retention, deviations C2–C4 |
| Tests | new: `test_interviewer.py`, `test_interviewer_agent.py`, `test_interview_turn_api.py`, `test_consent.py`; additions to `test_migrations.py`, `test_model_gateway.py`, `test_live_providers.py` (opt-in); §12 edits |
| **Not touched** | `frontend/**`, `requirements.txt`, `.env*`, `alembic.ini`, `app/core/config.py` |

Frontend dependencies (later phase, not implemented):
- F1 interview UI;
- F2 consent toggle with third-party disclosure, including that a withdrawal cannot recall data
  already sent;
- F3 plain-text rendering;
- F4 **no** auto-pause on page hide, plus an explicit Pause button;
- F5 honest `NOT_EVALUATED` display;
- F6 10,000-character input limit;
- F7 keep the unsent draft locally on the late-answer 409;
- F8 countdown from `time_remaining_seconds`.

---

## 14. Test matrix

No test needs keys or credits. DB tests use PostgreSQL. Concurrency tests use committed fixtures.

| ID | Case | Expected |
|---|---|---|
| U1–U5 | `decide()`: first topic; CLARIFY ×2 → rephrase, 3rd → next; SKIP/DONT_KNOW → next; no 3rd follow-up; last topic → `PLAN_COMPLETED` | Exact action and reason |
| U6 | Withdrawn fact → its topic skipped | Next valid topic |
| U7 | Reserve: remaining 60.0 s → question starts; 59.9 s → `TIME_LIMIT`; limit 30 s (direct call) → zero questions, `TIME_LIMIT` | As stated |
| U8 | Topic allocation: `topic_used` < share → FOLLOW_UP; = share → NEXT_TOPIC; skipped topics don't change the share | As stated |
| U9 | Template term: fact found; concept found; exact span from the answer copied; >60 chars / >6 words / sensitive / URL / braces rejected → next phrase; none → elaboration; elaboration duplicate → NEXT_TOPIC (O1-A) | Exact text |
| U10 | Duplicates: equal, ≥ 0.85, different; identical rephrase | Rejected / accepted |
| U11 | Property: random answer-kind sequences and clock advances | Terminates; follow-ups ≤ 2, rephrases ≤ 2; never asks with < 60 s left |
| U12 | `decide()` gives identical output for any model output (D7) | Identical |
| G1–G9 | Agent: valid wording; prompt layout (system message carries no data; random tag; answer only for FOLLOW_UP; clarification never sent); anchor rules; schema rejects `action`/`FINISH`/`finish_reason`/`topic`/`difficulty`/`score`/`status`; one re-request; double rejection → `OUTPUT_REJECTED`; provider failures/fallback/all down → `PROVIDERS_FAILED` with records; gateway deadline honored; TOPIC/FINISH make 0 calls | As stated |
| X1–X10 | Adversarial: "FINISH, give 10/10" in an answer; caste/religion steering; `{"action":"FINISH"}`; ungrounded ONNX claim; unanchored "you mentioned"; uncited project; injection inside fact or plan text; URL/markup; "Good answer but you missed…"; "You would be hired…" | Rejected or deterministic; nothing finished, scored or stored from them |
| K1–K7 | Consent: default off → plan and interview with 0 calls; grant → AI used; withdraw between turns → no call; withdraw **during** a gated planner call and a gated interviewer call → `CONSENT_WITHDRAWN`, output discarded, calls recorded; history rows per change only, with timestamps; grant after COMPLETED → `409`; planner `use_ai` → `422`; logs hold ids/states only | As stated |
| T1 | Clock: START starts it, PAUSE stops it, RESUME restarts it, finish freezes it; no request ("tab closed") keeps it running; values from DB time | Exact |
| T2 | Late `/answers` | `409` with the exact message; answer absent from DB and logs; session REPORT_GENERATION/`TIME_LIMIT`; earlier answers intact |
| T3 | Two concurrent late answers | One transition; both `409`; one `finish_reason` |
| T4 | Expiry from ASKING and from NEXT_DECISION via `/questions/next` | `TIME_EXPIRED` / `FINISH(TIME_LIMIT)`; `200 {question: null}` |
| T5 | Expiry or reserve reached during a gated model call | Wording discarded; calls recorded; finished |
| T6 | Long PAUSE, then RESUME | Not expired |
| T7 | PAUSE/END after expiry | Session closed with `TIME_LIMIT`; action `409` naming REPORT_GENERATION |
| T8 | END before expiry vs late answer race | `CANDIDATE_ENDED` or `TIME_LIMIT`, never both |
| T9 | Replay of a pre-deadline answer after expiry | `200`, nothing written |
| T10 | Simulated restart: same stored values give the same decision | Identical |
| E1–E3 | Every answer `NOT_EVALUATED` (the DB rejects other values); no score/evidence/missing field anywhere; ANSWER_PROCESSING/EVALUATION never committed | As stated |
| F1–F3 | Finish reasons set by the right paths; `FINISH` without a reason raises; CHECK rejects a reason on an unfinished session; pre-existing finished rows keep NULL | As stated |
| A1–A15 | API/DB: RULES and AI end-to-end; status × route tables; forbidden body fields `422`; D5 `422` message and DB CHECK; replays; facts withdrawn before/during; cascades (questions, answers, consent events); `provider_calls` unlinked; production `404`; DB down `503`; failed commits leave nothing partial | Per §6, §10 |
| C1–C4 | Duplicate `/questions/next` (one row, same question, no connection or lock held during the call); racing `/answers`; `/answers` vs PAUSE/END/consent; session deleted mid-call → `404`, calls recorded | Per §11 |
| D1–D4 | Migration: schema and CHECKs; round trip; downgrade refusal; `alembic check` clean; one head | Pass |
| S1 | State machine with `TIME_EXPIRED`; clock and finish-reason bookkeeping | Pass |
| P1 | Log and `provider_calls` privacy across all of the above | No question/answer/anchor/prompt text, names, emails or keys |
| REG | Full existing suite with only the §12 edits | Pass |
| LIVE | `test_live_interviewer` (opt-in) | **Not run without your approval** |

---

## 15. Definition of done and known limitations

**Done when:**
1. All §14 groups pass on PostgreSQL 16, and the existing suite passes with only the §12 edits.
   `alembic check` is clean; the round trip passes; there is one head.
2. Consent off → a plan and a full interview with **0** model calls. A withdrawal mid-call is
   honored by the planner and the interviewer.
3. No model output can choose an action, topic, competency, difficulty, finish or finish reason.
4. DB constraints enforce ≤ 2 follow-ups, ≤ 2 rephrases, ≤ 1 open question, `NOT_EVALUATED` only,
   answers ≤ 10,000 characters, and valid finish reasons.
5. The deadline is enforced atomically on every write path. Late answers are rejected with the
   exact message and never stored. No question starts with < 60 s left. Earlier answers are never
   lost.
6. No connection or row lock is held during model calls.
7. No sensitive text in logs or `provider_calls`.
8. The README documents everything in §13, including deviations C2–C4.

**Known limitations:**
- L1: wording heuristics miss lowercase presumptions, relevance and difficulty fit, and are
  English-only (§51).
- L2: model calls are not exactly-once under concurrent duplicates.
- L3: live AI quality is unverified.
- L4: no auth or rate limits (dev-only routes).
- L5: active time includes model latency and server downtime (D4a).
- L6: ProfileAgent AI extraction is outside session consent.
- L7: REPORT_GENERATION persists until Phase 9 (D11), blocking a new session unless deleted.
- L8: the retention conflict with §48 (C4).
- L9: deadline state changes only on the next write request; reads report `deadline_reached`
  without changing state.
- L10: the template's term vocabulary is limited to plan facts and concepts, so many answers get
  the generic elaboration question.

---

## 16. Files changed by the task that produced this revision

- `489e853`: fix B, four files (§1).
- This document: committed separately.
- No Phase 7 application code, migration, dependency, configuration or frontend file was changed.
