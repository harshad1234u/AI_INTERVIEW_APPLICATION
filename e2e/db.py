"""E2E database helper (test-only; never used by the app).

    python e2e/db.py deadline <session_id> <seconds_left>   # negative: the deadline has passed
    python e2e/db.py cleanup <email-prefix>        # delete E2E candidates, fake calls, counters
"""

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402

command, arg = sys.argv[1], sys.argv[2]
seconds_left = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
with SessionLocal() as db:
    if command == "deadline":
        # Stands in for minutes of answering: the clock is the server's, so it is moved there.
        db.execute(text(
            "UPDATE interview_sessions SET active_seconds = "
            "(plan->'settings'->>'duration_minutes')::int * 60 - :left - "
            "coalesce(extract(epoch FROM clock_timestamp() - active_since), 0) WHERE id = :s"),
            {"s": arg, "left": seconds_left})
    elif command == "cleanup":
        n = db.execute(text("DELETE FROM candidates WHERE email LIKE :p"), {"p": f"{arg}%"}).rowcount
        db.execute(text("DELETE FROM provider_calls WHERE requested_provider = 'e2e'"))
        db.execute(text("DELETE FROM usage_counters"))
        print(f"deleted {n} E2E candidate(s)")
    else:
        raise SystemExit(f"unknown command {command}")
    db.commit()
