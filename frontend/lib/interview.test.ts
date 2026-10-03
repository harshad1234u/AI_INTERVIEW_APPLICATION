// Run with `npm test` (node --test; Node strips the TypeScript types).
import { test } from "node:test";
import assert from "node:assert/strict";
import type { InterviewStatus, QuestionView } from "./api";
import {
  ANSWER_KIND_LABEL,
  COMPETENCY_LABEL,
  COPY,
  CRITERION_LABEL,
  DIFFICULTY_LABEL,
  EVALUATION_STATUS_LABEL,
  FINISH_LABEL,
  LEVEL_LABEL,
  MODE_LABEL,
  QUESTION_KIND_LABEL,
  QUESTION_TYPE_LABEL,
  SCREEN,
  RULES_REASON_TEXT,
  attemptNumbers,
  attemptState,
  answerLength,
  canRetry,
  errorText,
  fill,
  formatRemaining,
  isConflict,
  isNetworkError,
  isUnfinished,
  pendingEvaluations,
  screenFor,
  seqById,
} from "./interview.ts";

const STATUSES: InterviewStatus[] = [
  "CREATED", "PROFILE_PROCESSING", "PROFILE_REVIEW", "INTERVIEW_PLANNING", "READY", "ASKING",
  "WAITING_FOR_ANSWER", "PAUSED", "ANSWER_PROCESSING", "ANSWER_EVALUATION", "NEXT_DECISION",
  "REPORT_GENERATION", "COMPLETED",
];

test("every backend status maps to a screen", () => {
  assert.deepEqual(Object.keys(SCREEN).sort(), [...STATUSES].sort());
  assert.deepEqual(
    STATUSES.map((s) => [s, screenFor(s)]),
    [
      ["CREATED", "confirm"], ["PROFILE_PROCESSING", "confirm"], ["PROFILE_REVIEW", "confirm"],
      ["INTERVIEW_PLANNING", "plan"], ["READY", "ready"], ["ASKING", "turn"],
      ["WAITING_FOR_ANSWER", "turn"], ["PAUSED", "paused"], ["ANSWER_PROCESSING", "turn"],
      ["ANSWER_EVALUATION", "turn"], ["NEXT_DECISION", "turn"], ["REPORT_GENERATION", "feedback"],
      ["COMPLETED", "report"],
    ],
  );
});

test("only COMPLETED is finished", () => {
  assert.deepEqual(STATUSES.filter((s) => !isUnfinished(s)), ["COMPLETED"]);
});

function q(seq: number, kind: string | null, status = "NOT_EVALUATED"): QuestionView {
  return {
    id: `q${seq}`, seq, topic_position: 1, topic: "t", competency: "behavioral",
    question_type: "BEHAVIORAL", difficulty: "MEDIUM", basis: "GENERIC", kind: "TOPIC",
    followup_index: 0, rephrase_index: 0, text: "?", source: "RULES", rules_reason: null,
    asked_at: "",
    answer: kind === null ? null : {
      kind: kind as "ANSWER", text: kind === "ANSWER" ? "x" : null, answered_at: "",
      evaluation: { status: status as "NOT_EVALUATED" },
    },
  };
}

test("only unevaluated ANSWERs need an evaluation, in interview order", () => {
  const questions = [
    q(5, "ANSWER"), q(1, "ANSWER", "EVALUATED"), q(2, "SKIP"), q(3, "DONT_KNOW"), q(4, "CLARIFY"),
    q(6, "ANSWER", "OBSERVATIONS_ONLY"), q(7, null), q(0, "ANSWER"),
  ];
  assert.deepEqual(pendingEvaluations(questions).map((x) => x.seq), [0, 5]);
  assert.deepEqual(pendingEvaluations([]), []);
});

test("remaining time is m:ss, floored and never negative", () => {
  assert.equal(formatRemaining(900), "15:00");
  assert.equal(formatRemaining(61.9), "1:01");
  assert.equal(formatRemaining(59), "0:59");
  assert.equal(formatRemaining(0), "0:00");
  assert.equal(formatRemaining(-5), "0:00");
  assert.equal(formatRemaining(2700), "45:00");
});

test("answer length counts code points after trimming, like the backend", () => {
  assert.equal(answerLength("  abc  "), 3);
  assert.equal(answerLength("😀😀"), 2); // two code points, four UTF-16 units
});

test("retry availability is read from the report as it is", () => {
  assert.equal(canRetry({ available: true }), true);
  assert.equal(canRetry({ available: false }), false);
});

class FakeApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

test("server messages are shown verbatim; network errors are recognised", () => {
  const late = "The interview time limit was reached, so this answer was not saved.";
  assert.equal(errorText(new FakeApiError(409, late)), late);
  assert.equal(errorText(new FakeApiError(422, "Answer is too long: the limit is 10,000 characters.")),
               "Answer is too long: the limit is 10,000 characters.");
  assert.equal(errorText(new Error("boom")), COPY.unexpected); // not an API error
  assert.equal(errorText("text"), COPY.unexpected);
  assert.equal(isNetworkError(new FakeApiError(0, "offline")), true);
  assert.equal(isNetworkError(new FakeApiError(503, "down")), false);
  assert.equal(isNetworkError(null), false);
  // Only a 409 means the interview moved on; a 422 (e.g. too long) leaves the answer editable.
  assert.equal(isConflict(new FakeApiError(409, "late")), true);
  assert.equal(isConflict(new FakeApiError(422, "too long")), false);
  assert.equal(isConflict(new FakeApiError(0, "offline")), false);
});

test("question numbers by id", () => {
  assert.deepEqual([...seqById([{ question_id: "a", seq: 1 }, { question_id: "b", seq: 2 }])],
                   [["a", 1], ["b", 2]]);
});

test("placeholders are filled", () => {
  assert.equal(fill(COPY.evaluating, { i: 3, n: 8 }), "Evaluating answer 3 of 8…");
});

// No hiring, ranking, verdict or employability language in any fixed UI text.
const FORBIDDEN = [
  /\bhir(e|ed|es|ing)\b/i, /\brank/i, /\bpass(ed|es)?\b/i, /\bfail(ed|s|ure)?\b/i, /employab/i,
  /\b(un)?suitab/i, /\bpercent|%/i, /\boverall\b/i, /\baverage\b/i, /\btotal score\b/i,
  /\b(strong|weak) candidate\b/i, /\bcorrect\b/i, /\bincorrect\b/i, /\bcompeten(t|ce)\b/i,
  /\bconfiden(t|ce)\b/i, /\bpersonality\b/i,
];

test("fixed UI wording makes no judgment about the candidate", () => {
  const texts = [
    // The camera explanation names these words only to deny them (checked below).
    ...Object.values(COPY).filter((t) => t !== COPY.cameraExplain), ...Object.values(ANSWER_KIND_LABEL), ...Object.values(COMPETENCY_LABEL),
    ...Object.values(CRITERION_LABEL), ...Object.values(DIFFICULTY_LABEL),
    ...Object.values(EVALUATION_STATUS_LABEL), ...Object.values(FINISH_LABEL),
    ...Object.values(LEVEL_LABEL), ...Object.values(MODE_LABEL), ...Object.values(QUESTION_KIND_LABEL),
    ...Object.values(QUESTION_TYPE_LABEL),
  ];
  for (const text of texts) {
    for (const pattern of FORBIDDEN) assert.doesNotMatch(text, pattern, text);
  }
  const [before, denial] = COPY.cameraExplain.split("It is not a measurement of ");
  for (const pattern of FORBIDDEN) assert.doesNotMatch(before, pattern, before);
  assert.match(denial, /^emotion, confidence or honesty and never affects your feedback\./);
});

test("every rules reason has an explanation for the candidate", () => {
  const reasons = ["NOT_REQUESTED", "NOT_CONFIGURED", "PROVIDERS_FAILED", "OUTPUT_REJECTED",
                   "CONSENT_WITHDRAWN", "QUOTA_REACHED"] as const;
  assert.deepEqual(Object.keys(RULES_REASON_TEXT).sort(), [...reasons].sort());
  for (const r of reasons) assert.ok(RULES_REASON_TEXT[r].endsWith("."));
});

test("attempts are numbered oldest first, ties broken by id, whatever the list order", () => {
  const sessions = [
    { id: "c", created_at: "2026-10-03T10:00:02.5+00:00" },
    { id: "b", created_at: "2026-10-03T10:00:01Z" },
    { id: "a", created_at: "2026-10-03T10:00:01.000000Z" },
  ];
  assert.deepEqual([...attemptNumbers(sessions)], [["a", 1], ["b", 2], ["c", 3]]);
  assert.deepEqual([...attemptNumbers([])], []);
});

test("attempt states are plain words for every status", () => {
  for (const status of Object.keys(SCREEN) as InterviewStatus[]) {
    assert.ok(attemptState(status).length > 0, status);
  }
  assert.equal(attemptState("COMPLETED"), "Completed");
  assert.equal(attemptState("WAITING_FOR_ANSWER"), "In progress");
  assert.equal(attemptState("READY"), "Planned, not started");
});
