"""Controlled REAL-provider smoke test. Spends provider credits: run it deliberately, not in CI.

Drives a real backend (uvicorn app.main:app, AI_PROVIDERS from backend/.env) over HTTP through
the whole AI path: resume extraction -> planning -> interview with model-worded follow-ups ->
evaluation -> report. At most MAX_ANSWERS answers, so roughly ten model requests in all. Then one
deliberate failure: the primary provider with an invalid key, to see the live fallback.

    cd backend && .venv/Scripts/python ../e2e/live_smoke.py http://127.0.0.1:8001

Prints call metadata only (provider, model, latency, tokens, outcome): never prompts, answers,
resume text or keys. The candidate it creates is deleted at the end.
"""

import asyncio
import json
import os
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

import httpx2 as httpx  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.ai.gateway import ModelUnavailableError  # noqa: E402
from app.ai.profile_agent import extract_profile  # noqa: E402
from app.ai.providers import build_gateway  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
MAX_ANSWERS = 4
ORIGIN = {"Origin": "http://localhost:3000"}
FIXTURE = Path(__file__).parent / "fixtures" / "resume-fresh-graduate.pdf"
# A realistic candidate answers the question asked: chosen by the question's subject.
ANSWERS = {
    "library": "I built the Library Management System with Flask and MySQL. The schema had six "
               "tables; the main trade-off was keeping it normalised while issue and return "
               "queries stayed fast, so I added an index on the book and member columns and "
               "measured the query time before and after.",
    "index": "I added the index after timing the slow query: lookups by member went from about "
             "300 ms to 20 ms, and inserts got slightly slower, which was fine for a library.",
    "recursion": "Recursion solves a problem by calling itself on a smaller input until it "
                 "reaches a base case. A loop is better when the depth could be large, because "
                 "each call uses stack space and Python limits the depth.",
    "hash": "A hash map gives average constant-time lookup by key, while an array gives "
            "constant-time access by index and is better for ordered, dense data. The cost of "
            "the hash map is extra memory and no ordering.",
    "team": "In the Smart India Hackathon our team of four split the work by component. When two "
            "of us disagreed on the database, we listed the requirements and chose SQLite for "
            "speed of setup; I owned the API layer and we finished on time.",
    "internship": "I want this internship to work on real backend services, learn how teams "
                  "review code, and improve how I design APIs.",
}
GENERIC = ("I would start from the requirements, compare two options and their trade-offs, then "
           "choose the simpler one and measure it.")


def answer_for(question: str) -> str:
    q = question.lower()
    for key in ("index", "library", "recursion", "hash", "team", "internship"):
        if key in q or (key == "team" and "disagree" in q) or (key == "internship" and "why" in q):
            return ANSWERS[key]
    return GENERIC

# Seconds to wait before each model-backed request: free tiers limit tokens per minute.
PACE = float(os.environ.get("LIVE_PACE_SECONDS", "0"))
MODEL_ROUTES = ("/ai-extraction", "/plan", "/questions/next", "/evaluation")


def pace(request: httpx.Request) -> None:
    if request.method == "POST" and request.url.path.endswith(MODEL_ROUTES):
        time.sleep(PACE)


started = datetime.now(UTC)
client = httpx.Client(base_url=f"{BASE}/api", headers=ORIGIN, timeout=180,
                      event_hooks={"request": [pace]})
steps: list[dict] = []


def step(name: str, res: httpx.Response, **extra: object) -> dict:
    body = res.json() if res.content else None
    steps.append({"step": name, "status": res.status_code, **extra})
    print(f"{res.status_code}  {name}  {json.dumps(extra) if extra else ''}", flush=True)
    if res.status_code >= 400:
        raise SystemExit(f"{name} failed: {res.status_code} {res.text[:300]}")
    return body


email = f"live-smoke-{int(time.time())}@example.com"
me = step("register", client.post("/auth/register", json={
    "name": "Live Smoke", "email": email, "password": "live smoke password"}))
cid = me["id"]
try:
    for category, fact in (("SKILL", "React"), ("PROJECT", "TrustLens")):
        step(f"manual fact {fact}", client.post(f"/candidates/{cid}/manual-facts",
                                                json={"category": category, "fact": fact}))
    resume = step("upload resume", client.post("/resumes", files={
        "file": ("resume.pdf", FIXTURE.read_bytes(), "application/pdf")}))
    ext = step("LIVE ai extraction", client.post(f"/resumes/{resume['id']}/ai-extraction"))
    steps[-1].update(provider=ext["provider"], model=ext["model"], latency_ms=ext["latency_ms"],
                     facts_added=ext["facts_added"], facts_rejected=ext["facts_rejected"],
                     facts_already_listed=ext["facts_already_listed"])
    print(f"      extraction: +{ext['facts_added']} added, {ext['facts_rejected']} rejected by "
          f"grounding, {ext['facts_already_listed']} already listed")
    step("approve all pending", client.post(f"/resumes/{resume['id']}/facts/review-pending",
                                            json={"status": "APPROVED"}))

    sid = step("create session", client.post("/interview-sessions", json={}))["id"]
    step("confirm profile", client.post(f"/interview-sessions/{sid}/actions",
                                        json={"action": "CONFIRM_PROFILE"}))
    step("grant AI consent", client.put(f"/interview-sessions/{sid}/ai-consent",
                                        json={"granted": True}))
    planned = step("LIVE plan", client.post(f"/interview-sessions/{sid}/plan", json={
        "target_role": "SOFTWARE_DEVELOPER_INTERN", "experience_level": "FRESH_GRADUATE",
        "mode": "MIXED", "difficulty": "MEDIUM", "duration_minutes": 15}))
    plan = planned["plan"]
    steps[-1].update(source=plan["source"], rules_reason=plan["rules_reason"],
                     topics=len(plan["topics"]),
                     fact_based_topics=sum(t["basis"] == "CANDIDATE_FACT" for t in plan["topics"]))
    print(f"      plan: {plan['source']} ({plan['rules_reason']}), {len(plan['topics'])} topics: "
          + "; ".join(t["topic"] for t in plan["topics"]))
    step("start", client.post(f"/interview-sessions/{sid}/actions",
                              json={"action": "START_INTERVIEW"}))

    asked = []
    for i in range(MAX_ANSWERS):
        turn = step(f"next question {i + 1}", client.post(f"/interview-sessions/{sid}/questions/next",
                                                          json={}))
        q = turn["question"]
        if q is None:
            break
        asked.append((q["kind"], q["source"], q["rules_reason"]))
        steps[-1].update(kind=q["kind"], source=q["source"], rules_reason=q["rules_reason"],
                         model_calls=len(turn["model_calls"]))
        print(f"      Q{q['seq']} [{q['kind']}, {q['source']}]: {q['text']}")
        step(f"answer {i + 1}", client.post(f"/interview-sessions/{sid}/answers", json={
            "question_id": q["id"], "kind": "ANSWER", "text": answer_for(q["text"])}))
    # One more decision after the last answer (may word a follow-up), then end.
    turn = step("next question (after last answer)",
                client.post(f"/interview-sessions/{sid}/questions/next", json={}))
    if turn["question"]:
        q = turn["question"]
        steps[-1].update(kind=q["kind"], source=q["source"], rules_reason=q["rules_reason"])
        print(f"      Q{q['seq']} [{q['kind']}, {q['source']}]: {q['text']}")
    step("end interview", client.post(f"/interview-sessions/{sid}/actions",
                                      json={"action": "END_INTERVIEW"}))

    history = step("questions", client.get(f"/interview-sessions/{sid}/questions"))
    for q in history["questions"]:
        if q["answer"] and q["answer"]["kind"] == "ANSWER":
            ev = step(f"LIVE evaluate Q{q['seq']}", client.post(
                f"/interview-sessions/{sid}/questions/{q['id']}/evaluation", json={}))
            detail = ev["evaluation"]
            steps[-1].update(status=ev["status"], source=detail["source"],
                             rules_reason=detail["rules_reason"],
                             scores={c["criterion"]: c["score"] for c in detail["criteria"]})
            print(f"      Q{q['seq']} {ev['status']} ({detail['source']}): "
                  + ", ".join(f"{c['criterion']}={c['score']}" for c in detail["criteria"]))
    report = step("report", client.post(f"/interview-sessions/{sid}/report", json={}))["report"]
    steps[-1].update(evaluated=report["summary"]["evaluations"]["evaluated"],
                     topics_to_practise=len(report["topics_to_practise"]),
                     retry=report["retry"]["available"])
    print(f"      report: {report['summary']['evaluations']}, "
          f"{len(report['topics_to_practise'])} topics to practise, retry {report['retry']}")
finally:
    client.delete(f"/candidates/{cid}")

# ---------- deliberate failure: the primary provider has an invalid key ----------
settings = get_settings()
broken = settings.model_copy(update={"ai_providers": "gemini,groq",
                                     "gemini_api_key": SecretStr("invalid-key-for-smoke-test")})
time.sleep(PACE)
try:
    fallback = asyncio.run(extract_profile(build_gateway(broken),
                                           "Skills\nPython, SQL\nProjects\nWeather Notifier"))
except ModelUnavailableError as exc:  # every provider failed: report it, never hide it
    fallback = type("Failed", (), {"record": exc.record, "facts": []})()
record = fallback.record
print(f"fallback: requested {record.requested_provider}, answered by {record.provider} "
      f"({record.model}), fallback_used={record.fallback_used}, attempts={record.attempts}, "
      f"error before fallback={record.error_type}, {record.latency_ms} ms, "
      f"{len(fallback.facts)} facts")
steps.append({"step": "LIVE fallback (invalid primary key)", "requested": record.requested_provider,
              "provider": record.provider, "model": record.model,
              "fallback_used": record.fallback_used, "attempts": record.attempts,
              "error_type": record.error_type, "latency_ms": record.latency_ms})

with SessionLocal() as db:
    calls = [dict(r._mapping) for r in db.execute(text(
        "SELECT capability, requested_provider, provider, model, succeeded, attempts, "
        "fallback_used, error_type, latency_ms, input_tokens, output_tokens, total_tokens "
        "FROM provider_calls WHERE created_at >= :t ORDER BY created_at"), {"t": started})]
print(f"\n{len(calls)} recorded gateway calls (the fallback call is not stored: it ran outside the app)")
for c in calls:
    print(f"  {c['capability']:20} {c['provider'] or '-':7} {c['model'] or '-':32} "
          f"ok={c['succeeded']} attempts={c['attempts']} fallback={c['fallback_used']} "
          f"err={c['error_type']} {c['latency_ms']} ms tokens={c['total_tokens']}")
totals = Counter()
for c in calls:
    totals["calls"] += 1
    totals["ok"] += bool(c["succeeded"])
    totals["tokens"] += c["total_tokens"] or 0
print(f"totals: {dict(totals)}")
out = Path(__file__).parent / "out"
out.mkdir(exist_ok=True)
(out / "live.json").write_text(json.dumps({"steps": steps, "calls": calls, "totals": totals},
                                          default=str, indent=2))
