// Run with `npm test` (node --test; Node strips the TypeScript types).
import { test } from "node:test";
import assert from "node:assert/strict";
import type { InterviewPlan, InterviewReport } from "./api";
import { escapeHtml, exportFileName, planDocument, reportDocument, topicDescription } from "./exportDoc.ts";

const EVIL = `<script>alert("x")</script><img src=x onerror=alert(1)>`;
const FACT_ID = "11111111-2222-3333-4444-555555555555";
const QUESTION_ID = "99999999-8888-7777-6666-555555555555";
const META = { candidateName: `Asha ${EVIL}`, date: new Date("2026-10-03T10:00:00Z"), attempt: 2 };

const PLAN: InterviewPlan = {
  version: 1,
  source: "RULES",
  rules_reason: "QUOTA_REACHED",
  settings: { target_role: "SOFTWARE_DEVELOPER_INTERN", experience_level: "STUDENT", mode: "MIXED",
              difficulty: "MEDIUM", duration_minutes: 15 },
  competencies: ["project_understanding", "behavioral"],
  omitted_groups: ["TECHNICAL"],
  topics: [
    { position: 1, competency: "project_understanding", question_type: "PROJECT", difficulty: "MEDIUM",
      basis: "CANDIDATE_FACT", topic: `Project: ${EVIL}`,
      question_templates: ["SECRET TEMPLATE QUESTION?"], expected_concepts: ["secret-concept"],
      facts: [{ fact_id: FACT_ID, category: "PROJECT", fact: `TrustLens ${EVIL}` }] },
    { position: 2, competency: "behavioral", question_type: "BEHAVIORAL", difficulty: "MEDIUM",
      basis: "GENERIC", topic: "Teamwork", question_templates: ["Describe a team."],
      expected_concepts: [], facts: [] },
  ],
};

const REF = { question_id: QUESTION_ID, seq: 1, topic_position: 1 };
const REPORT: InterviewReport = {
  summary: {
    settings: PLAN.settings, plan_source: "AI", finish_reason: "CANDIDATE_ENDED",
    finish_reason_text: "You ended the interview.", active_seconds: 125, questions_asked: 1,
    answers: { answer: 1, skip: 0, dont_know: 0, clarify: 0, unanswered: 0 },
    evaluations: { evaluated: 1, observations_only: 0, not_applicable: 0, not_evaluated: 0 },
  },
  questions: [{ ...REF, kind: "TOPIC", text: `Explain ${EVIL}`, answer_kind: "ANSWER",
                answer_note: "Answered", evaluation_status: "EVALUATED" }],
  coverage: {
    topics: [{ topic_position: 1, topic: "TrustLens", competency: "project_understanding",
               question_type: "PROJECT", questions_asked: 1, note: null }],
    competencies: [{ competency: "project_understanding", planned_topics: 1, asked_topics: 1 }],
  },
  shown_clearly: [{ ...REF, criterion: "relevance", score: 4, score_meaning: "Good",
                    evidence: [`I used ${EVIL}`] }],
  to_practise: {
    criteria: [{ ...REF, criterion: "reasoning", score: 2, score_meaning: "Partial",
                 practice: "Explain why.", evidence: ["because"] }],
    missing_concepts: [{ ...REF, concept: "caching", practice: "Mention caching." }],
  },
  answer_evidence: [{ ...REF, status: "EVALUATED", notice: null, evaluation: {
    rubric: "TECHNICAL_PROJECT", rubric_version: 1, source: "AI", rules_reason: null,
    criteria: [{ criterion: "relevance", score: 4, evidence: ["quote one"] }],
    missing_concepts: ["caching"], claims_to_verify: [{ quote: "It is O(1)", status: "NEEDS_VERIFICATION" }],
    feedback: `Feedback ${EVIL}`, observations: { word_count: 40, planned_concepts: [], concepts_mentioned: [] },
    created_at: "2026-10-03T10:00:00Z", updated_at: "2026-10-03T10:00:00Z" } }],
  communication_observations: {
    answers: [{ question_id: QUESTION_ID, seq: 1, word_count: 40, concepts_mentioned: ["state"] }],
    speech_metrics: { available: false, note: "Speech metrics need voice answers." },
  },
  topics_to_practise: [{ topic_position: 1, topic: "TrustLens", competency: "project_understanding",
                         criteria: ["reasoning"], missing_concepts: ["caching"] }],
  recommended_practice: [{ practice: "Explain why.", question_ids: [QUESTION_ID] }],
  retry: { available: true, note: "You can retry the topics to practise in a new interview." },
  score_scale: { "1": "Not shown", "5": "Strong", null: "Too little to judge" },
  limitations: "Practice feedback only.",
};

function assertInert(doc: string) {
  // The only tags are the document's own: candidate text never becomes markup.
  assert.ok(!/<script/i.test(doc));
  assert.ok(!/<img/i.test(doc));
  assert.ok(doc.includes("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"));
  assert.ok(doc.includes(`content="default-src 'none'; style-src 'unsafe-inline'"`)); // no scripts at all
}

test("escapeHtml escapes every markup character", () => {
  assert.equal(escapeHtml(`<a href="x">'&'</a>`), "&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;");
  assert.equal(escapeHtml(3), "3");
});

test("the plan document has the settings, ordered topics and their basis, escaped", () => {
  const doc = planDocument(PLAN, META);
  assertInert(doc);
  assert.ok(doc.startsWith("<!doctype html>"));
  for (const text of ["Interview plan #2", "Software Developer Intern", "Mixed placement", "Medium",
                      "15 minutes", "Teamwork", "Left out: Technical",
                      "The daily AI usage limit was reached, so fixed rules were used."]) {
    assert.ok(doc.includes(text), text);
  }
  assert.ok(doc.indexOf("Project: ") < doc.indexOf("Teamwork")); // plan order
});

test("the plan document never reveals ids, prepared questions or expected concepts", () => {
  const doc = planDocument(PLAN, META);
  for (const hidden of [FACT_ID, "SECRET TEMPLATE QUESTION", "secret-concept", "question_templates"]) {
    assert.ok(!doc.includes(hidden), hidden);
  }
});

test("a topic says what it is based on", () => {
  assert.equal(topicDescription(PLAN.topics[1]), "Behavioral · Behavioral · Medium · general question");
  assert.match(topicDescription(PLAN.topics[0]), /^Project · Project Understanding · Medium · based on your project “TrustLens /);
});

test("the report document has every section of the report page, escaped, without ids", () => {
  const doc = reportDocument(REPORT, META);
  assertInert(doc);
  for (const heading of ["Summary", "Questions", "Topics covered", "By competency", "Shown clearly",
                         "To practise", "Answer evidence", "Communication observations",
                         "Topics to practise", "Recommended practice", "Retry", "Score scale"]) {
    assert.ok(doc.includes(`>${heading}</h`), heading);
  }
  for (const text of ["2:05 (minutes:seconds)", "4 of 5 (Good)", "caching", "It is O(1)",
                      "(from answer #1)", "Practice feedback only.", "never combined"]) {
    assert.ok(doc.includes(text), text);
  }
  assert.ok(!doc.includes(QUESTION_ID));
});

test("file names carry no name or id", () => {
  assert.equal(exportFileName("plan", META.date, 2), "interview-plan-2-2026-10-03.html");
  assert.equal(exportFileName("report", META.date), "interview-report-2026-10-03.html");
});
