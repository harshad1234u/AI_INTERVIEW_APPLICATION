# Demo runbook

A 10-minute demonstration of the AI Interview System on a local or staging machine, with
synthetic data. Nothing here is used by the application itself.

| File | What it is |
|---|---|
| `resume-ananya-iyer.pdf` | Synthetic resume of a fictional student (education, custom-named skills, internship, projects, certifications, achievements). `.html` is its source; print it to PDF with any browser to regenerate it |
| `seed_demo.py` | Recreates the demo account `ananya.iyer.demo@example.com` with an empty profile and clears usage counters. Refuses to run when `ENVIRONMENT=production`; the password comes from `DEMO_PASSWORD`, never from code |

## 1. Before the demo (once)

1. **AI providers** (`backend/.env`, never committed):
   - `AI_PROVIDERS=groq,gemini` is the working order on this machine.
   - Free tiers are tight: Gemini allows 20 requests a day for `gemini-2.5-flash`, and Groq limits
     tokens per minute. A rehearsal plus the demo fit, but **don't run the rehearsal in the 10
     minutes before the demo**. A paid key on the first provider removes the risk.
   - NVIDIA's configured model is retired. To use NVIDIA again, set a current `NVIDIA_MODEL`
     (list: `GET https://integrate.api.nvidia.com/v1/models`), add `nvidia` to `AI_PROVIDERS`, and
     run `tests/test_live_providers.py`.
2. **Database:** `backend/.env`'s `DATABASE_URL` must reach the database, or export it in the
   shell. Then `cd backend && .venv/Scripts/alembic upgrade head` (head `c5d1a7e3b920`).
3. **Frontend:** `cd frontend && npm install && npm run build`.

## 2. Start (each demo)

```bash
# terminal 1: backend (live AI from backend/.env)
cd backend
DEMO_PASSWORD='pick-a-demo-password' .venv/Scripts/python ../demo/seed_demo.py
.venv/Scripts/python -m app.main                  # http://127.0.0.1:8000/api/health -> ok

# terminal 2: frontend
cd frontend
npm run start                                     # http://localhost:3000
```

Use a browser with a webcam (Chrome or Edge) at `http://localhost:3000`. The camera only works on
`localhost` or HTTPS.

## 3. The demo script

1. **Log in** as `ananya.iyer.demo@example.com`. The login page explains how it works.
2. **Profile → Resume:** upload `demo/resume-ananya-iyer.pdf`.
   - Point out: custom headings ("Technical Competencies", "Internship Experience", "Selected
     Projects") are understood, and every item shows the line it came from.
   - Nothing is used until it is approved. Click **Approve all**.
   - Optional: add a skill under "Your skills and projects" to show manual entry.
3. **Go to your interviews → Start a new interview → Confirm profile.**
4. **Plan:** keep Mixed / Medium / 15 minutes, tick **Use AI assistance**, then **Plan
   interview**. Show the topics built from the resume, then **Download plan** (it opens in any
   browser and prints to PDF).
5. **Camera (optional):** read the panel aloud. Off by default; runs on this device; images never
   leave the browser; only counts are saved; not a measurement of emotion; never affects
   feedback. Click **Enable camera** and show the preview and "Expression: Mostly …".
6. **Start interview.** Answer the first question in two or three sentences, using a phrase from
   the plan (for example the project's name).
   - A **follow-up** appears. Click **Ask to rephrase** to show rephrasing.
   - Answer, then show **Pause** and **Resume**.
   - Click **End interview** after 3–4 answers.
7. **Feedback:** **Get my feedback**. Each answer is evaluated against a rubric with quotes from
   the answer.
8. **Report:** show "Shown clearly", "To practise", "Observed expression signals" (with its
   disclaimer) and **Download report**.
9. **Retry the topics to practise** → interview #2. **Back to your interviews** shows the history:
   #2 is a retry of #1, and each keeps its own report.

**Say about the camera:** it is an experimental observation of visible expressions only. It is
never used in any score, feedback, ranking or decision, and it says nothing about how the person
felt, their confidence, honesty or suitability. It is an explicit product addition beyond the
original PRD.

## 4. If something goes wrong

| What you see | What it means | What to do |
|---|---|---|
| "The AI service could not be used just now, so fixed rules were used." | Provider down or rate-limited; the fallback worked | Continue: the interview works with fixed rules. Mention it as the fallback |
| "AI evaluation is temporarily unavailable…" / "observations only" | Same, at the feedback step | Continue; the report still builds. Retry needs AI scores, so it may not be offered |
| "Camera permission was denied…" | The browser blocked the camera | Allow the camera in the address bar, or continue without it |
| "Facial-expression analysis is unavailable…" | Model or camera failure | Continue: the interview is unaffected |
| "Too many sign-in attempts from your network…" | The sign-in limit (20 per 15 min) | Re-run `seed_demo.py` (it clears the counters) |
| Sent back to the login page | The session expired or was reset by `seed_demo.py` | Log in again; nothing is lost |

## 5. Rehearsal (optional, uses about ten live AI calls)

With both servers running and the account seeded:

```bash
DEMO_PASSWORD='pick-a-demo-password' node e2e/demo_rehearsal.mjs   # 19 checks; needs Pillow
```

It walks this script in headless Edge, with a fake webcam showing one face. Screenshots and
downloads go to `e2e/out/rehearsal/`.
