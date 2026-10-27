# Phase 12 — Authentication and Candidate Isolation

Status: implemented (approved scope). Only the signed-in candidate can read or change their own
profile, resumes, facts, interview sessions, answers, evaluations, reports and retries. The
frontend no longer treats a stored UUID as the user's identity.

## Why

Before this phase, possession of a candidate, resume or session UUID was enough to read the
candidate's data, change their email, grant AI consent, or delete sessions. The routes were
kept out of production for that reason.

## Approved decisions

| # | Decision |
|---|---|
| A1 | Email + password, server-side sessions |
| A2 | Credentials stored on `candidates` |
| A3 | Candidates created before this phase have no password and cannot log in (or be claimed by registering their email: `409`) |
| A4 | Another candidate's resource answers `404`, exactly like a missing one (never `403`) |
| A5 | Session cookie `SameSite=Lax` + an Origin check on state-changing requests |
| A6 | 5 wrong passwords lock the account for 15 minutes |
| A7 | Production still serves `/api/health` only |

## Passwords

- `hashlib.scrypt`, N=2^14, r=8, p=5 (an OWASP-listed setting: 16 MiB, about 175 ms here), a
  16-byte random salt per hash, 32-byte key. Stored as `scrypt$n$r$p$salt$key`, so the cost can
  be raised later without locking out existing passwords.
- Verification is constant-time (`hmac.compare_digest`). A malformed stored hash verifies nothing
  and never raises.
- Policy: 8–128 characters, no composition rules (NIST SP 800-63B). The upper bound caps hashing
  work. Login applies only the upper bound.
- An unknown email, a candidate with no password and a wrong password all get the same
  `401 {"detail": "Email or password is incorrect."}`. The first two still run one scrypt
  against a dummy hash, so they take the same time.
- Passwords are never logged, returned, put in exception messages, prompts or provider payloads.
  On `/api/auth/*`, validation errors (`422`) leave out FastAPI's usual `input` echo.

## Sessions

- `secrets.token_urlsafe(32)` gives the raw token. It is sent only in the `coach_session` cookie:
  `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age=604800`, and `Secure` when
  `AUTH_COOKIE_SECURE=true`. It is never in a JSON body.
- `auth_sessions` stores `SHA-256(token)` (hex) as the primary key, with `candidate_id`,
  `created_at` and `expires_at`. The expiry is absolute (7 days): sessions are never extended.
- `current_candidate` (in `app/api/deps.py`) is the only source of identity: it looks up the
  cookie's hash with `expires_at > now`. An unknown, expired or logged-out session is `401`.
- Logout deletes the row and clears the cookie. It is idempotent (`204` even without a session)
  and ends only that browser's session.
- A new sign-in deletes that candidate's expired sessions. There is no background purge.
- Deleting a candidate deletes their sessions (`ON DELETE CASCADE`) and clears the cookie.

## Lockout

The login reads the candidate row `FOR UPDATE`, so parallel attempts are counted one at a time.
Each wrong password adds to `failed_logins`. The fifth sets `locked_until = now + 15 min` and
resets the count. While locked, every attempt (even with the right password) is `429` and is not
counted. A success resets both columns. Only the targeted candidate is affected.

## CSRF

`OriginCheck` (in `app/main.py`) refuses `POST`, `PUT`, `PATCH` and `DELETE` unless `Origin` is
one of `CORS_ORIGINS`. The response is `403 {"detail": "Request origin not allowed."}`. A
missing Origin is refused too: browsers send one on every such request, so only non-browser
clients omit it, and they can add it. `GET`, `HEAD` and `OPTIONS` are never checked, and CORS
handles preflights before the check runs. CORS now allows credentials.

## Authorization

| Resource | How it is scoped |
|---|---|
| Profile, email, deletion (`/api/candidates/{id}`) | `get_candidate`: the id must be the signed-in candidate's |
| Resume list, interview session list | the same `get_candidate` |
| Resume, facts, fact review, AI extraction, resume deletion | `get_resume`: `resume.candidate_id` must match. A fact must also belong to that resume |
| Session reads (session, plan, questions, answers, evaluations, report, consent history), deletion | `get_interview_session`: `session.candidate_id` must match |
| Session writes (actions, plan, consent, next question, answer, evaluation, report, retry) | `owned_session_id`: reads only the owner column, then the service locks and loads the session itself. A session never changes owner |
| Question ids in answers and evaluations | already checked against the session by the services (`404 Question not found`) |
| Session creation, resume upload | the candidate comes from the session. A `candidate_id` in the JSON body is refused (`422`); in the upload form it is ignored |

`POST /api/candidates` was removed: registration is the only way to create a candidate.

## API

| Endpoint | Success | Errors |
|---|---|---|
| `POST /api/auth/register` `{name, email, password}` | `201` candidate + session cookie | `409` email taken · `422` |
| `POST /api/auth/login` `{email, password}` | `200` candidate + session cookie | `401` generic · `429` locked · `422` |
| `POST /api/auth/logout` | `204`, cookie cleared | — |
| `GET /api/auth/me` | `200` candidate | `401` |

Every other route except `GET /api/health` returns `401 {"detail": "Please log in."}` without a
valid session. Response shapes are unchanged.

## Database (migration `5c0e1d2f7a91`)

- `candidates`: `password_hash varchar(200) NULL`, `failed_logins smallint NOT NULL DEFAULT 0`
  with `CHECK (failed_logins >= 0)`, and `locked_until timestamptz NULL`.
- `auth_sessions`: `token_hash varchar(64)` PK, `candidate_id` FK → `candidates` `ON DELETE
  CASCADE` (indexed), `created_at`, `expires_at`, and `CHECK (expires_at > created_at)`.
- The downgrade refuses while any candidate has a password: the older schema can't hold it, and
  dropping it would silently lock those people out. Sessions are dropped.

## Frontend

- `/login` lets the candidate log in or create an account. It validates on the client, shows the
  server's messages, has loading states, and clears the password field after a failure.
- `AuthProvider` calls `GET /api/auth/me` once at startup. The profile and interview pages render
  only for a signed-in candidate. `AccountBar` shows who is signed in and has the logout button.
- `request()` sends `credentials: "include"`. A `401` from any API except login or register sends
  the browser to `/login`.
- `lib/candidateStorage.ts` was removed. Nothing is kept in `localStorage` or `sessionStorage`,
  and the token is never visible to JavaScript.
- The frontend and API must be on the same site (e.g. `localhost:3000` and `localhost:8000`), or
  the browser won't send the `SameSite=Lax` cookie.

## Verification

- Backend: `tests/test_auth.py` covers:
  - hashing, salts, malformed hashes, token storage, expiry and lockout;
  - register, login, logout and me, plus cookie flags, logs and `422` bodies;
  - the Origin check and preflights;
  - a structural and a behavioural `401` sweep over every served route;
  - a two-candidate IDOR matrix: 58 cross-owner requests, each `404` with the database unchanged;
  - real-connection races: duplicate registration, 8 parallel wrong passwords (exactly 5 counted,
    then `429`), and logout against concurrent requests.

  `tests/test_migrations.py` covers the schema, the cascade, the refused downgrade, and an
  upgrade → downgrade → upgrade round trip that keeps an existing candidate.
- Frontend: `lib/auth.test.ts` (redirect rule, form validation).
- Browser: headless Edge over CDP, against the real backend with a fake model gateway.

## Deferred (not in this phase)

Email verification, password reset, OAuth, magic links, OTP, general API rate limiting, an AI
quota system, production enablement, a retention policy, progress/history, voice/STT,
job-description grounding, learning mode, a multilingual UI, PDF export. Registration still
reveals whether an email is taken (`409`); fixing that needs email verification.
