# Phase 11 — Text Interview UI

Status: **approved (2026-10-02); implemented as specified below.**

Baseline before Phase 11:
- `main` = `5247718` (Phase 10 complete), clean tree;
- Alembic head `3a4785ecf08e`;
- backend suite: 1434 passed, 3 skipped.

## 1. Scope

The browser client for the interview system that already exists (backend Phases 5–10). Before
Phase 11 none of the 16 interview-session endpoints had a frontend caller, and PRD §50 requires
that "text mode must remain a complete experience". It covers the MVP MUST HAVEs "Text interview",
"Final report" and "Retry" (§66) in the UI.

**Frontend only:**
- no backend file, API, schema, migration or state-machine change;
- no new AI behavior;
- no new runtime or dev dependency.

## 2. Approved decisions

| # | Decision |
|---|---|
| D1 | Pure flow logic in `lib/interview.ts`, tested with `node --test`. Node 24 strips TypeScript types natively, so no test framework is added. Plus a real-browser E2E (§7). |
| D2 | AI consent is explicit, per session and off by default. The checkbox is never pre-checked and reflects the session's stored value. It is never copied from another session. A disclosure explains what may be sent to the configured provider. |
| D3 | Feedback: one evaluation request per answer, in order, with visible progress. Then `POST .../report`. No bulk or client-side evaluation. |
| D4 | No automatic pause when the browser closes: a cross-origin unload request is unreliable. An abandoned interview keeps the backend's clock until the time limit. The UI says so. |
| D5 | An unsent answer lives in React state only. It survives a pause and a network failure, and is lost on reload. It is never written to localStorage, sessionStorage, IndexedDB, cookies or URLs. |
| D6 | A new route `/interview`, linked from the profile card once a profile exists. |

## 3. Files

| File | Role |
|---|---|
| `app/interview/page.tsx` | The route (static shell) |
| `components/interview/InterviewFlow.tsx` | Session discovery and recovery, the status → screen switch, discard, the in-memory draft |
| `components/interview/InterviewSetup.tsx` | `ProfileConfirm` (PROFILE_REVIEW), `PlanForm` (INTERVIEW_PLANNING), `ReadyScreen` (READY), `ConsentControl` |
| `components/interview/InterviewTurn.tsx` | Running and PAUSED states: question, answer kinds, display-only timer, pause/resume/end |
| `components/interview/InterviewFeedback.tsx` | REPORT_GENERATION: per-answer evaluation with progress, then the report |
| `components/interview/InterviewReport.tsx` | COMPLETED: every report section, plus retry |
| `lib/interview.ts` | Pure logic: status → screen, pending evaluations, time and length, error text, 409 detection, labels, all fixed copy |
| `lib/interview.test.ts` | `node --test` |
| `lib/candidateStorage.ts` | The existing candidate-id helpers, moved out of `CandidateProfile.tsx` so both pages share them |
| `lib/api.ts` | Session types (mirroring the backend schemas) and one function per existing endpoint |

## 4. Flow

Every screen is chosen from the server's `status` (`lib/interview.ts` `SCREEN`):

| Status | Screen | Server calls |
|---|---|---|
| no session | List: Resume/Discard for the unfinished one, or Start; View last report | `GET /candidates/{id}/interview-sessions`, `POST /interview-sessions`, `DELETE` |
| `PROFILE_REVIEW` | Approved facts and the pending count; Confirm. A `409` shows the server's message and a link to fact review. | `GET` resumes and facts, `POST .../actions CONFIRM_PROFILE` |
| `INTERVIEW_PLANNING` | Level, type, difficulty and length (the backend's value sets; the single role is shown as text); consent checkbox | `GET/PUT .../ai-consent`, `POST .../plan` |
| `READY` | Settings, planner source, topics, omitted groups; consent control; Start | `GET .../plan`, `START_INTERVIEW` |
| `ASKING`, `WAITING_FOR_ANSWER`, `ANSWER_*`, `NEXT_DECISION` | Question (server text verbatim, kind, topic n of N, "Worded with AI assistance" when the source is AI), answer box with code-point count, Submit / Ask to rephrase / I don't know / Skip, Pause, End | `POST .../questions/next`, `POST .../answers`, `PAUSE`, `END_INTERVIEW` |
| `PAUSED` | Resume, End | `RESUME`, `END_INTERVIEW` |
| `REPORT_GENERATION` | Finish reason, pending count, consent control (AI evaluation needs it before the report), "Evaluating answer i of n…" | `GET .../questions`, `POST .../evaluation` per answer, `POST .../report` |
| `COMPLETED` | The report; Retry when `retry.available` | `GET .../report`, `POST .../retry` |

The rules stay on the server:
- **Turns:** after an answer is saved, the next question is whatever `POST .../questions/next`
  returns. The client never advances on its own.
- **Timer:** the server's `time_remaining_seconds`, counted down locally for display only.
- **Answer length:** the 10,000-character limit is not enforced in the browser. A count and a
  warning are shown, and the server's `422` is displayed with the text kept and editable (no
  silent truncation).
- **Refusals:** a `409` (late answer, ended, not waiting…) keeps the unsent text visible and
  offers **Continue**, which re-reads the session and follows its status.
- **Retry:** the button only appears when the report says it is available. The new session
  comes from the server's response (READY). On a `409` the server's message is shown and the
  report stays.

## 5. Report

Every Phase 9 section is rendered as returned:
- Summary, Questions, Topics covered (and by competency), Shown clearly, To practise, Answer
  evidence, Communication observations (including the speech-metrics note), Topics to practise,
  Recommended practice, Retry, Score scale, Limitations.
- Each score shows as "n of 5 (meaning)" for one criterion of one answer.
- There are no bars, totals, averages, percentages, ranks or verdicts.
- Quotes, feedback and all server text are rendered as plain React text (no
  `dangerouslySetInnerHTML`).

## 6. Accessibility and layout

- **Structure:** semantic headings, a label on every control, native buttons, selects, checkbox
  and textarea.
- **Focus:** `:focus-visible` outlines. On each screen change, focus moves to the screen heading;
  on each new question, to the question text.
- **Announcements:** `aria-live` regions for the question, consent state and evaluation progress;
  errors use `role="alert"`.
- **Colour:** states are named in text, never by colour alone.
- **Layout:** the existing single 40rem column. At 390 px width there is no horizontal scrolling
  (verified).

## 7. Verification

- **`npm test`:** 10 tests (`node --test`). They cover status → screen for all 13 statuses,
  pending evaluations, time format, code-point length, retry availability, error and conflict
  handling, placeholders, and a wording check of every fixed UI string (no hiring, ranking,
  pass/fail, employability, percentage, overall or average language).
- **`npm run lint`, `npm run typecheck`, `npm run build`:** pass.
- **Real-browser E2E (32 checks, all passing):** headless Microsoft Edge driven over the Chrome
  DevTools Protocol by a scratch Node script. The Playwright MCP was unavailable (connection
  timeout). It ran against the production build and the real backend on PostgreSQL. Only the
  backend's model gateway was replaced by the backend tests' fake provider, so no provider was
  contacted and no credits were spent. Covered:
  - profile → `/interview`;
  - `409` on pending facts, then confirm;
  - consent unchecked by default and not carried over;
  - plan, READY, start;
  - focus on the question; Tab to the answer;
  - `422` (10,001 characters) with the text kept;
  - answer → next question;
  - offline submit keeps the text, then succeeds;
  - Ask to rephrase;
  - pause keeps the draft, resume;
  - I don't know, Skip;
  - End with confirmation;
  - per-answer progress ("Evaluating answer 1 of 2…" → "2 of 2…");
  - report sections and no combined score;
  - retry unavailable ("Nothing to retry.");
  - mobile width;
  - consent turned on at feedback → AI-scored report;
  - retry available; retry `409` with the report kept; retry → new READY session;
  - discard;
  - reload mid-interview → Resume shows the same open question, and the unsaved draft is gone;
  - browser storage holds only `candidateId`;
  - no console output with answers and no uncaught exceptions.

  With consent off, the gateway received **no** calls. It was called only for answer evaluation
  after consent was turned on.
- **Backend suite:** unchanged (§8 of the final report).

## 8. Known limitations

- **No authentication:** anyone holding a candidate or session id has full access. Local use only
  (the backend doesn't register these routes in production). The candidate id in localStorage is
  not authentication.
- **No rate limiting.**
- **Closing the browser does not pause** the interview (D4).
- **An unsent answer is lost on reload** (D5).
- **Feedback is sequential:** evaluation runs one answer at a time in the open page. Leaving the
  page mid-way stops it; returning and pressing the button continues with what is still pending.
- **Not included:** no voice, speech-to-text or speech metrics; no progress history across
  attempts; no candidate goals; no multilingual UI; no PDF export.
- **Topic choice:** a retry can't choose topics (Phase 10).
