# Phase 13 — Manual Profile Entry

Status: implemented (approved scope). A signed-in candidate can add, edit and delete their own
skills, projects, experience, education and certifications without a resume. This closes the last
unmet MVP must-have in the PRD: "Manual skills/projects" (§66, §67), level 1 trust (§18), and
manual entry when a resume can't be read (§19).

## Why

Facts could only come from a resume (`FactSource` was `RESUME` only, and `resume_id` was
required). Yet the message for an unreadable resume told the candidate to "enter your information
manually", and there was no way to do that.

## Approved decisions

| # | Decision |
|---|---|
| M1 | A manual fact is `APPROVED` as soon as it is added. Typing it is the confirmation; there is no pending state |
| M2 | Stored in `candidate_facts`, so fact ids, plans and the interviewer work unchanged |
| M3 | At most 100 manual facts per candidate, enforced under the candidate row lock |
| M4 | An exact duplicate (same category, same text ignoring case) of a manual fact or a non-rejected resume fact is `409`. No merging, no automatic resolution, no similarity matching |
| M5 | Edited in place: same id, category, source and status. `extracted_fact` keeps the original text for audit. Delete removes; there is no reject state |
| M6 | The unreadable-resume message is unchanged (now true) and gains a link to manual entry |
| M7 | Scope: manual profile entry only |

## Database (migration `70b0b7891bc0`)

- `source` now allows `RESUME` and `MANUAL`.
- `resume_id`, `source_section`, `source_text` and `extracted_by` are now nullable. That is only
  so a manual fact can leave them empty; resume facts still need them, through
  `ck_candidate_facts_provenance_matches_source`:
  - **MANUAL:** `resume_id`, `source_section`, `source_text`, `extracted_by` and
    `provider_call_id` are all NULL, and `status = 'APPROVED'`.
  - **Any other source:** `resume_id`, `source_section`, `source_text` and `extracted_by` are all
    set.
- `uq_candidate_facts_manual_fact`: a unique index on `(candidate_id, category, lower(fact))`
  where `source = 'MANUAL'`. It is the database backstop against manual duplicates. Duplicates of
  resume facts can't be expressed as an index (resume facts may repeat each other), so the service
  checks them under the row lock.
- **Cascades:**
  - Deleting a candidate removes their manual facts (`candidate_id` FK, `ON DELETE CASCADE`).
  - Deleting a resume removes only that resume's facts. Manual facts have no resume.
- **Downgrade:** refuses while any manual fact exists (the repo's convention for lossy
  downgrades).

## API (signed in, owner only)

| Endpoint | Success | Errors |
|---|---|---|
| `GET /api/candidates/{id}/manual-facts` | `200` manual facts only, ordered by category, then original text ignoring case, then id (the resume-facts order) | `401` · `404` not yours |
| `POST /api/candidates/{id}/manual-facts` `{category, fact}` | `201`, `APPROVED`, no resume provenance | `401` · `404` not yours · `409` duplicate or cap · `422` |
| `PATCH /api/manual-facts/{fact_id}` `{fact}` | `200`, text changed only | `401` · `404` not yours, missing, or a resume fact · `409` duplicate · `422` (including any other field) |
| `DELETE /api/manual-facts/{fact_id}` | `204` | `401` · `404` |

- **Text rule:** the same `FactText` rule as resume-fact edits: trimmed, internal whitespace
  collapsed to one space, 1–200 characters after trimming.
- **Categories:** the existing `FactCategory` values.
- **Separation:** the resume-fact routes can't reach a manual fact, and the manual routes can't
  reach a resume fact.
- **CSRF and the sweep:** writes go through the Phase 12 Origin check, and the Phase 12 route
  sweep covers all four routes.

## Concurrency

Every create and edit first locks the candidate row (`SELECT … FOR UPDATE`). Then it counts the
manual facts (for the cap), checks for a duplicate, and writes, all in one transaction. Parallel
identical creates give one `201` and `409`s for the rest. A burst at the cap never goes past 100.
If the unique index ever fires, it also becomes `409`.

A resume upload doesn't take that lock. A resume can therefore add a fact equal to a manual one
(M4 governs manual entry only; resume facts are reviewed separately), and nothing is ever
resolved automatically.

## Planner and interviewer: no changes

- **Planner:** `approved_facts` reads approved facts by candidate and sorts them by category and
  text. A manual fact gets an `F` ref like any other, and the planner's existing validation
  applies to it (grounding, no invented topics).
- **Interviewer:** grounds questions and follow-ups on the plan's fact snapshots.
- **D8:** `valid_positions` compares each cited fact's (id, category, text) with the current
  approved fact. Editing or deleting a manual fact therefore makes its topics ineligible. An edit
  during planning is caught by the existing stale-plan check (`409 profile changed`).
- **Profile confirmation:** manual facts are never pending, so they never block it.
- **Trust:** manual text reaches a model only inside the delimited data, as edited resume facts
  already did. It is untrusted content; there are no keyword filters, because the structure is
  the defence.

## Frontend

- **"Your skills and projects" card** (`#manual-facts`) on the profile page: category picker
  (the backend's categories), text box, Add, a list by category with Edit (text only) and Delete
  (after confirmation, removed once the server answers), each item labelled "Added by you".
  Client checks mirror the server's (`lib/profile.ts`, `node --test`). The server's `409` and
  `422` messages are shown, and typed text is kept.
- **Unreadable resume:** a `FAILED` or `UNSUPPORTED` resume shows "Enter your information
  manually", which scrolls to the card and focuses its text box.
- **Profile confirmation** lists manual facts after the approved resume facts, marked "Added by
  you".

## Verification

- **`tests/test_manual_facts.py`:**
  - CRUD, text rules and categories;
  - duplicates (case, whitespace, other category, near-duplicates, approved, pending and rejected
    resume facts, edits), and the cap including edits and deletes at the cap;
  - ownership and CSRF, manual and resume route separation, profile confirmation, resume and
    candidate deletion, the unreadable-resume path;
  - rules and fake-AI plans citing manual facts, an invented AI topic still rejected, follow-up
    grounding, D8 after edit and after delete, an edit racing planning;
  - inert injection text, no fact text in logs;
  - real-connection races (duplicate creates; a 12-request burst from 95 facts ends at 100).
- **`tests/test_auth.py`:** the sweep and the IDOR matrix include manual facts.
- **`tests/test_migrations.py`:** the provenance CHECK, the index, cascades, the refused
  downgrade, and an upgrade → downgrade → upgrade round trip that keeps resume facts.
- **Browser** (headless Edge + CDP, fake model gateway): add, duplicate, edit, delete, reload,
  unreadable resume → manual entry, confirmation, a plan using the manual project, report, retry,
  second-account isolation, empty browser storage.

## Out of scope

New roles, proficiency levels, semantic duplicate detection, automatic conflict resolution, AI
clean-up of manual facts, job descriptions, voice/STT, learning mode, a multilingual UI, voice
output, PDF export, progress/history, a retention policy, general rate limiting, AI quotas,
production deployment, email verification, password reset, OAuth.
