# Phase 10 — Retry Practice Sessions

Status: **approved (2026-10-02); implemented as specified.**

Baseline before Phase 10:
- `main` = `322e3ef` (Phase 9 complete), clean tree;
- Alembic head `3a4785ecf08e`;
- suite: 1394 passed, 3 skipped (the opt-in live tests).

References:
- `prd.md` v2.0 as `§n`;
- Phase 7–9 decisions as in `docs/phase-7-interviewer-plan.md`, `docs/phase-8-evaluator-plan.md`
  and `docs/phase-9-report-plan.md`.

## 1. Scope and source

The PRD has no phase roadmap. The user chose Retry for Phase 10 out of three candidates: Voice
(the original brief's Phase 10), adaptive orchestration (the roadmap Phases 1–9 followed, already
delivered by Phase 7) and Retry. Retry is an MVP MUST HAVE (§66) and a Definition of Done item:
"Weak areas produce retry tasks" (§67). The §44 report lists "Retry" as its last section.

**Objective.** A completed interview's current report names its topics to practise. The candidate
can create a new, ready-to-start interview session containing exactly those topics whose facts
are still valid, copied word for word. Retry is not a new interview engine: it builds a plan from
stored data and hands it to the existing lifecycle.

## 2. Architecture

```text
POST /retry ─► lock source row ─► COMPLETED? ─► session_report() ─► topics_to_practise
                                                                        │
            valid_positions() (D8, current facts) ◄─────────────────────┘
                    │
                    ▼
     retry_plan(): copy kept topics, renumber 1..n, recompute competencies
                    │
                    ▼
create_session ─► CONFIRM_PROFILE ─► PLAN_READY(plan) ─► READY ─► commit (caller)
```

| Piece | Where | Reused or new |
|---|---|---|
| What is "to practise" | `report.session_report().topics_to_practise` | Reused: the single definition (Phase 9 R1) |
| Fact validity | `interviewer.valid_positions` | Reused: the interviewer's own D8 check |
| Source lock | `interviewer.lock_session` | Reused |
| New session and its checks | `create_session`, `apply_event(CONFIRM_PROFILE)`, `apply_event(PLAN_READY, plan=…)` | Reused, unchanged |
| Plan construction | `retry.retry_plan` (pure) | New |
| Orchestration | `retry.create_retry` | New |
| Route | `POST /api/interview-sessions/{id}/retry` | New |
| Request body | `RetryRequest` (empty, `extra="forbid"`) | New, like `ReportRequest` |
| Response | `InterviewPlanView {session_id, status, plan}` | Reused |

## 3. API

`POST /api/interview-sessions/{id}/retry` with body `{}`.

| Status | When | Body |
|---|---|---|
| `201` | Created | `{session_id: <new>, status: "READY", plan}` |
| `404` | The source doesn't exist (or was deleted, including while the request waited on it) | `"Interview session not found"` |
| `409` | The source isn't `COMPLETED` | `"Retry is available after the report has been generated."` |
| `409` | The report has no topics to practise | `"There are no topics to retry."` |
| `409` | Every topic to practise lost a valid fact | `"No topic can be retried: the profile details they relied on have changed."` |
| `409` | The candidate already has an unfinished session | The existing create-session message, naming that session |
| `409` | The candidate has profile facts pending review | The existing `CONFIRM_PROFILE` message |
| `422` | Any body field, or a malformed id | Validation error |
| `503` | Database unavailable | The existing handler |

The client sends only the source session id. The candidate is read from the source row, so no
candidate id is accepted and no other candidate's session can be created. The route is not served
when `ENVIRONMENT=production`, like every session route (no authentication yet).

## 4. Topic selection and plan construction

- **Selection:** every topic in the report's `topics_to_practise` at request time, in plan order.
  A topic is there only if one of its AI-evaluated answers has a criterion scored 1 or 2, or a
  missing planned concept (Phase 9). Retry adds no rule of its own, and the client can't choose
  topics.
- **Copy:** each kept topic is copied from the source's stored plan snapshot unchanged. That
  includes its topic text, question templates, expected concepts, competency, question type,
  difficulty, basis and fact snapshots. Only `position` changes, renumbered 1..n because the plan
  schema and the report index topics by position.
- **Plan fields:** `version`, `settings`, `source`, `rules_reason` and `omitted_groups` are kept.
  `competencies` is recomputed from the kept topics, the same rule `build_plan` uses.
- **Provenance:** `source` and `rules_reason` are kept, not set to a new "RETRY" value. The
  interviewer labels each topic question AI or RULES from `plan.source`, so a new value would
  relabel AI-written templates.
- **Validation:** the result is validated with `InterviewPlan.model_validate`, the schema every
  stored plan passes. `build_plan` is not rerun: it is the proposal validator, and it rejects any
  plan that leaves out a group of the mode (`missing_group`), which a retry does by design. The
  copied topics already passed `build_plan` when the source was planned.

## 5. Fact revalidation (D8)

Before anything is created, `valid_positions` reads the candidate's current facts. A topic is kept
only if every fact it cites still exists, belongs to the candidate, is `APPROVED`, and has the
same category and text as its snapshot. A withdrawn, rejected, edited, recategorised or deleted
fact drops its topic. If no topic is left, the response is `409` and nothing is created.

A fact changed after this check but before the question is asked is caught again by the
interviewer at ask time (D8), as for any plan.

## 6. State machine

No new state, event or transition. The new session takes the normal path in one transaction:
CREATED → PROFILE_PROCESSING → PROFILE_REVIEW (`create_session`) → `CONFIRM_PROFILE` →
INTERVIEW_PLANNING → `PLAN_READY` → READY. The source stays `COMPLETED` and is not written.

## 7. AI and consent

- No model call and no new capability. Provider credits: 0.
- The new session's `ai_consent` is its column default (`false`) with no consent events. Consent
  is per session and never copied. The candidate grants it on the new session if they want AI
  wording during the interview.

## 8. Privacy and deletion

- **Copied:** only plan data, meaning the kept topics and their fact snapshots (approved profile
  details).
- **Never copied:** answers, evaluations, scores, evidence quotes, feedback, report text, prompts
  or provider payloads.
- **After creation** the retry is an independent session with no link to its source.
- **Deleting the source** leaves the retry session (and its copied plan) intact. This is
  deliberate.
- **Deleting the candidate** removes both (cascade).
- **Logs** hold session ids and topic counts only.

## 9. Concurrency and atomicity

- `create_retry` locks the source row (`FOR UPDATE`) and does everything in the request's
  transaction. The route commits once. Any exception rolls back, so no half-created session
  remains.
- **Two simultaneous retries** serialize on the source row lock. The first creates the session;
  the second hits the one-active-session unique index and gets `409`. The protection is the
  database index, not an application check.
- **Deleting the source during a retry:** the retry waits on the row, finds it gone and returns
  `404`. Nothing is created. A retry that already holds the lock commits first, and the deletion
  then removes only the source.
- No lock is held across an external call (there is none).

## 10. Phase 9 change

The report's `retry` section now states availability. It is computed by code from
`topics_to_practise` and nothing else:
- with topics: `{available: true, note: "You can retry the topics to practise in a new interview."}`;
- without: `{available: false, note: "Nothing to retry."}`.

Whether the facts are still valid is checked when the retry is requested, not in the report. The
report stays pure: it creates nothing and calls no model. This is the only change to its output.

## 11. Tests

`backend/tests/test_retry.py` covers:
- **The pure plan:** copying, renumbering, settings, competencies, and RULES/AI provenance.
- **The API:** success; the retry session runs the normal interview; all topics included; every
  404/409/422/503 case; not served in production.
- **Fact safety:** withdrawn, edited, recategorised and deleted facts drop their topic; an
  unchanged approved fact keeps it; all topics invalid gives 409.
- **Request-time report:** a re-evaluation in `COMPLETED` changes the next retry.
- **Consent and model use:** consent not copied; no provider call; no model code in the service.
- **Privacy:** nothing copied but the plan; source deletion keeps the retry; candidate deletion
  removes it; logs hold ids only.
- **Injection:** instructions inside an answer don't change the selection or the candidate.
- **Atomicity:** a failure after the insert, and a failed commit, both leave nothing.
- **Real concurrency:** two simultaneous retries give 201 and 409; a source deleted meanwhile
  gives 404.

`tests/test_report.py` asserts the new `retry` output.

## 12. Limitations and deferred work

- No link between a retry and its source: no `source_session_id`, no retry history, no
  cross-session progress tracking (§46) or learning memory (§47).
- No topic selection by the candidate.
- No frontend Retry UI.
- No voice/speech and no adaptive orchestration.
- A retry keeps the source's settings, including `duration_minutes`. A short retry ends early
  with `PLAN_COMPLETED`.
- The retry repeats the same question templates on purpose. Duplicate-question protection works
  within one session only, as before.
