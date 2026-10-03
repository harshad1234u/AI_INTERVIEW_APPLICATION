"""Demo account for local / staging demonstrations only. Never part of the application.

    cd backend
    DEMO_PASSWORD='choose-one' .venv/Scripts/python ../demo/seed_demo.py

Deletes the previous demo account (and everything it owns), then creates a fresh one with a
synthetic name and email, signed up exactly as the app does it (hashed password, no data), so
every demo starts from an empty profile. Also clears usage counters, so earlier rehearsals don't
eat the demo's sign-in and AI quotas. Refuses to run when ENVIRONMENT=production.
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from sqlalchemy import delete, text  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.models import Candidate  # noqa: E402
from app.services.auth import new_candidate  # noqa: E402

DEMO_NAME = "Ananya Iyer"
DEMO_EMAIL = "ananya.iyer.demo@example.com"  # example.com: never a real mailbox

if get_settings().environment == "production":
    raise SystemExit("Refusing to seed demo data in production.")
password = os.environ.get("DEMO_PASSWORD", "")
if not 8 <= len(password) <= 128:
    raise SystemExit("Set DEMO_PASSWORD (8-128 characters) for the demo account.")

with SessionLocal() as db:
    db.execute(delete(Candidate).where(Candidate.email == DEMO_EMAIL))  # cascades to all its data
    db.execute(text("DELETE FROM usage_counters"))
    new_candidate(db, DEMO_EMAIL, DEMO_NAME, password)
    db.commit()
print(f"Demo account ready: {DEMO_EMAIL} (password from DEMO_PASSWORD). Resume: demo/resume-ananya-iyer.pdf")
