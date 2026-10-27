"""E2E backend: the real FastAPI app on 127.0.0.1:8000, with the model gateway replaced by a
deterministic fake, exactly as backend/tests do it. No provider is contacted; no credits are spent.

    cd backend && .venv/Scripts/python ../e2e/server.py      (DATABASE_URL from backend/.env)

What the fake answers, per capability (every answer still goes through the real validators):
- PROFILE_EXTRACTION: one fact copied from the resume's "Achievements" section (accepted) and one
  invented fact (rejected by grounding), so the UI shows both outcomes.
- INTERVIEW_PLANNING and QUESTION_GENERATION: invalid output, so the planner and interviewer use
  their deterministic fallback and the UI explains why.
- ANSWER_EVALUATION: a valid technical-rubric evaluation quoting PHRASE (the E2E answers contain
  it), with low scores, so the report has topics to practise and a retry.
"""

import json
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)  # backend/.env
os.environ["AI_PROVIDERS"] = ""  # no real provider is even configured

import uvicorn  # noqa: E402

from app.ai.gateway import ModelCapability, RawCompletion  # noqa: E402
from app.ai.providers import get_model_gateway  # noqa: E402
from app.main import app  # noqa: E402
from tests.fakes import make_gateway  # noqa: E402

PHRASE = "trade-offs between speed and clarity"
EVALUATION = {
    "criteria": [{"criterion": c, "score": s, "evidence": [PHRASE]}
                 for c, s in (("relevance", 4), ("completeness", 2), ("reasoning", 2),
                              ("communication", 3))],
    "missing_concepts": [],
    "claims_to_verify": [],
    "feedback": "You name the trade-off. Say which option you chose and why, with an example.",
}


def extraction(user_content: str) -> dict:
    lines = [line.strip() for line in user_content.splitlines()]
    facts = [{"category": "SKILL", "fact": "Kubernetes", "source_section": "Skills",
              "source_text": "Expert in Kubernetes and Terraform"}]  # not in the resume
    if "Achievements" in lines:
        line = lines[lines.index("Achievements") + 1]
        facts.append({"category": "EXPERIENCE", "fact": re.sub(r"^[•\-]\s*", "", line),
                      "source_section": "Achievements", "source_text": line})
    return {"facts": facts}


class CapabilityFake:
    name, model = "e2e", "e2e-fake"  # never a real provider name: cleanup finds every row

    async def complete(self, request, json_schema, max_output_tokens):
        capability = request.capability
        print(f"[fake provider] {capability.value}", flush=True)
        if capability == ModelCapability.ANSWER_EVALUATION:
            text = json.dumps(EVALUATION)
        elif capability == ModelCapability.PROFILE_EXTRACTION:
            text = json.dumps(extraction(request.user_content))
        else:
            text = "{}"
        return RawCompletion(text=text, model=self.model, finish_reason="stop")


app.dependency_overrides[get_model_gateway] = lambda: make_gateway(CapabilityFake(), retries=0)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
