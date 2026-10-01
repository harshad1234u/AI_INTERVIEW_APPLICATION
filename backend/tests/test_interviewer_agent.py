"""InterviewerAgent through the real gateway with scripted fake providers. No real provider, no
credits."""

import json
import time

import pytest
from pydantic import ValidationError

from app.ai.gateway import ErrorKind, ModelCapability, ModelGateway
from app.ai.interviewer_agent import MAX_PROPOSALS, WordingRequest, propose_wording
from app.models.interview_question import AnswerKind as A
from app.models.interview_session import RulesReason
from app.schemas.interview_turn import FollowUpWording, RephraseWording
from app.services.interviewer import wording_codes
from tests.fakes import HANG, FakeProvider, make_gateway
from tests.test_interviewer import TOPICS, ctx, q

pytestmark = pytest.mark.anyio

ANSWER = "We used Kafka. I weighed the trade-offs carefully."
CLARIFICATION = "Sorry, what do you mean? My email is asha@example.com"
FOLLOW = WordingRequest(TOPICS[1], answer=ANSWER)
REPHRASE = WordingRequest(TOPICS[1], original_question=TOPICS[1].question_templates[0])
GOOD_FOLLOW_UP = {"question": "Which trade-offs mattered most in TrustLens?", "anchor": "trade-offs"}
GOOD_REPHRASE = {"question": "How is TrustLens put together, piece by piece?"}


def follow_ctx():
    return ctx(q(1, 2, said=ANSWER))


def rephrase_ctx():
    return ctx(q(1, 2, answer=A.CLARIFY))


def later(seconds: float = 30) -> float:
    return time.monotonic() + seconds


async def test_valid_follow_up_wording_is_accepted() -> None:  # G1
    provider = FakeProvider("groq", GOOD_FOLLOW_UP)
    out = await propose_wording(make_gateway(provider), FOLLOW,
                                lambda w: wording_codes(follow_ctx(), w), later())
    assert out.wording == FollowUpWording(**GOOD_FOLLOW_UP) and out.rules_reason is None
    [record] = out.records
    assert (record.capability, record.provider) == (ModelCapability.QUESTION_GENERATION, "groq")


async def test_prompt_layout_keeps_data_out_of_the_instructions() -> None:  # G2, §8.6
    provider = FakeProvider("groq", GOOD_FOLLOW_UP, GOOD_REPHRASE)
    gateway = make_gateway(provider)
    await propose_wording(gateway, FOLLOW, lambda w: set(), later())
    await propose_wording(gateway, REPHRASE, lambda w: set(), later())
    follow, rephrase = provider.calls
    for request in (follow, rephrase):
        for data in ("TrustLens", "Kafka", "trade-offs", "Explain the architecture"):
            assert data not in request.system_instruction  # closed-set values only
        assert "PROJECT" in request.system_instruction and "MEDIUM" in request.system_instruction
    tag_f = follow.user_content.split(">", 1)[0][1:]
    tag_r = rephrase.user_content.split(">", 1)[0][1:]
    assert tag_f != tag_r and tag_f.startswith("turn_data_")  # random per request
    assert f"<{tag_f}>" in follow.system_instruction
    data_f = json.loads(follow.user_content.split("\n")[1])
    data_r = json.loads(rephrase.user_content.split("\n")[1])
    assert data_f["answer"] == ANSWER and "original_question" not in data_f  # answer: FOLLOW_UP only
    assert "answer" not in data_r and data_r["original_question"] == TOPICS[1].question_templates[0]
    assert set(data_f) - {"answer"} == {"topic", "question_templates", "expected_concepts", "facts"}
    assert data_f["facts"] == [{"category": "PROJECT", "fact": "TrustLens"}]  # no ids
    for request in (follow, rephrase):
        assert CLARIFICATION not in request.system_instruction + request.user_content


@pytest.mark.parametrize("extra", ["action", "finish_reason", "topic", "difficulty", "score",
                                   "status", "competency", "event", "id"])
async def test_output_schema_has_no_control_fields(extra: str) -> None:  # G4
    with pytest.raises(ValidationError):
        FollowUpWording(**GOOD_FOLLOW_UP, **{extra: "FINISH"})
    with pytest.raises(ValidationError):
        RephraseWording(**GOOD_REPHRASE, **{extra: "FINISH"})
    provider = FakeProvider("groq", {**GOOD_FOLLOW_UP, "action": "FINISH"})
    out = await propose_wording(make_gateway(provider, retries=0), FOLLOW, lambda w: set(), later())
    assert out.wording is None and out.rules_reason == RulesReason.PROVIDERS_FAILED
    assert [r.error_type for r in out.records] == [ErrorKind.INVALID_OUTPUT] * 2


async def test_one_constrained_re_request_names_the_codes() -> None:  # G5, §30
    bad = {"question": "Why did you choose Kafka?", "anchor": "Kafka"}
    provider = FakeProvider("groq", bad, GOOD_FOLLOW_UP)
    out = await propose_wording(make_gateway(provider), FOLLOW,
                                lambda w: wording_codes(follow_ctx(), w), later())
    assert out.wording == FollowUpWording(**GOOD_FOLLOW_UP) and len(out.records) == 2
    assert "anchor_not_in_plan_vocabulary" in out.rejected[0]
    retry = provider.calls[1].system_instruction
    assert "anchor_not_in_plan_vocabulary" in retry and "Kafka" not in retry  # codes, not content


async def test_two_rejections_fall_back_with_output_rejected() -> None:  # G6
    bad = {"question": "Why did you choose Kafka?", "anchor": "Kafka"}
    provider = FakeProvider("groq", bad)
    out = await propose_wording(make_gateway(provider), FOLLOW,
                                lambda w: wording_codes(follow_ctx(), w), later())
    assert (out.wording, out.rules_reason, len(out.records)) == (
        None, RulesReason.OUTPUT_REJECTED, MAX_PROPOSALS)


async def test_provider_failures_are_recorded_and_bounded() -> None:  # G7
    gateway = make_gateway(FakeProvider("gemini", ErrorKind.AUTH),
                           FakeProvider("groq", ErrorKind.RATE_LIMITED))
    out = await propose_wording(gateway, FOLLOW, lambda w: set(), later())
    assert (out.wording, out.rules_reason) == (None, RulesReason.PROVIDERS_FAILED)
    assert [r.provider for r in out.records] == [None, None] and len(out.records) == MAX_PROPOSALS
    unconfigured = ModelGateway({}, timeout_seconds=1, max_retries=0, max_output_tokens=256)
    out = await propose_wording(unconfigured, FOLLOW, lambda w: set(), later())
    assert (out.rules_reason, out.records) == (RulesReason.NOT_CONFIGURED, [])


async def test_the_turn_deadline_is_honoured() -> None:  # G8, §6.5
    slow, spare = FakeProvider("groq", HANG), FakeProvider("gemini", GOOD_FOLLOW_UP)
    started = time.monotonic()
    out = await propose_wording(make_gateway(slow, spare, timeout=10), FOLLOW, lambda w: set(),
                                later(0.3))
    assert time.monotonic() - started < 2
    assert out.wording is None and spare.calls == []  # nothing runs past the deadline
    assert out.records[0].error_type == ErrorKind.TIMEOUT
    out = await propose_wording(make_gateway(spare), FOLLOW, lambda w: set(), later(-1))
    assert (out.records, spare.calls) == ([], [])  # already out of time: no call at all


async def test_a_duplicate_rephrase_gets_no_re_request() -> None:  # R7, P3, C7
    for same in (TOPICS[1].question_templates[0], "explain THE architecture of trustlens!"):
        provider = FakeProvider("groq", {"question": same}, GOOD_REPHRASE)
        out = await propose_wording(make_gateway(provider), REPHRASE,
                                    lambda w: wording_codes(rephrase_ctx(), w), later())
        assert out.duplicate and out.wording is None
        assert len(out.records) == len(provider.calls) == 1  # exactly one call


async def test_a_rephrase_after_provider_failures_falls_back(  # R12(a)
) -> None:
    provider = FakeProvider("groq", ErrorKind.TIMEOUT, ErrorKind.INVALID_OUTPUT)
    out = await propose_wording(make_gateway(provider, retries=0), REPHRASE, lambda w: set(),
                                later())
    assert (out.wording, out.duplicate, out.rules_reason) == (
        None, False, RulesReason.PROVIDERS_FAILED)
    assert [r.error_type for r in out.records] == [ErrorKind.TIMEOUT, ErrorKind.INVALID_OUTPUT]


async def test_other_rephrase_rejections_get_the_re_request() -> None:  # §8.4 step 1
    provider = FakeProvider("groq", {"question": "Is TrustLens a good answer?"}, GOOD_REPHRASE)
    out = await propose_wording(make_gateway(provider), REPHRASE,
                                lambda w: wording_codes(rephrase_ctx(), w), later())
    assert out.wording == RephraseWording(**GOOD_REPHRASE) and len(out.records) == 2
