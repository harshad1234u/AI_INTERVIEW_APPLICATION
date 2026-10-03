// Downloadable plan and report documents: one self-contained HTML file each, readable in any
// browser and printable to PDF. Pure functions (no fetch, React or storage), run by `node --test`.
//
// Every value from the server (topics, quotes, feedback, the candidate's facts) is untrusted text:
// it is HTML-escaped here, and the document also forbids scripts with its own CSP, so a mistake in
// escaping still cannot run code. No ids, prompts, provider names or call metadata are included.
import type { InterviewPlan, InterviewReport, PlannedTopic } from "./api";
import {
  COMPETENCY_LABEL,
  CRITERION_LABEL,
  DIFFICULTY_LABEL,
  EVALUATION_STATUS_LABEL,
  LEVEL_LABEL,
  MODE_LABEL,
  QUESTION_KIND_LABEL,
  QUESTION_TYPE_LABEL,
  ROLE_LABEL,
  RULES_REASON_TEXT,
  formatRemaining,
} from "./interview.ts";

const ENTITIES: Record<string, string> = {
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
};

export const escapeHtml = (text: string | number) =>
  String(text).replace(/[&<>"']/g, (c) => ENTITIES[c]);

/** Tagged template: every interpolated value is escaped unless it is already `Html`. */
class Html {
  readonly value: string;
  constructor(value: string) {
    this.value = value; // no parameter property: `node --test` strips types only
  }
  toString() { return this.value; }
}
function h(strings: TemplateStringsArray, ...values: unknown[]): Html {
  let out = strings[0];
  values.forEach((v, i) => {
    const part = Array.isArray(v) ? v.map(piece).join("") : piece(v);
    out += part + strings[i + 1];
  });
  return new Html(out);
}
const piece = (v: unknown) =>
  v instanceof Html ? v.value : v === null || v === undefined || v === false ? "" : escapeHtml(String(v));

const STYLE = `
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;color:#1a1a1a;
background:#fff;max-width:760px;margin:32px auto;padding:0 20px;line-height:1.5;font-size:15px}
h1{font-size:24px;margin:0 0 4px} h2{font-size:18px;margin:28px 0 8px;border-bottom:1px solid #ccc;
padding-bottom:4px} h3{font-size:15px;margin:16px 0 4px} .meta{color:#555;margin:0 0 16px}
dl{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;margin:0} dt{color:#555}
dd{margin:0} ol,ul{padding-left:22px} li{margin:6px 0} .hint{color:#555;font-size:13px}
.note{border-left:3px solid #b26b00;background:#fff8ec;padding:8px 12px;margin:12px 0}
q{font-style:italic} footer{margin-top:32px;color:#666;font-size:12px;border-top:1px solid #ddd;
padding-top:8px} @media print{body{margin:0;max-width:none} h2{break-after:avoid} li{break-inside:avoid}}`;

function document_(title: string, body: Html): string {
  return "<!doctype html>\n" + h`<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title><style>${new Html(STYLE)}</style></head>
<body>${body}
<footer>AI Interview Coach — practice feedback for learning. It is not an assessment of you and
is not a hiring decision.</footer></body></html>`;
}

export type DocMeta = { candidateName: string; date: Date; attempt?: number };

const when = (d: Date) => d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

function plannedBy(source: "AI" | "RULES", reason: keyof typeof RULES_REASON_TEXT | null): Html {
  return h`${source === "AI" ? "AI assistance, checked by rules" : "Fixed rules"}${
    source === "RULES" && reason && reason !== "NOT_REQUESTED" ? h` <span class="hint">(${RULES_REASON_TEXT[reason]})</span>` : ""}`;
}

/** What a topic is about, as the candidate sees it before the interview. */
export function topicDescription(t: PlannedTopic): string {
  const type = QUESTION_TYPE_LABEL[t.question_type];
  const competency = COMPETENCY_LABEL[t.competency];
  // "Behavioral · Behavioral" or a competency that is already the title says nothing new.
  const parts = [`${type} question`, competency !== type && competency !== t.topic ? competency : null,
                 `${DIFFICULTY_LABEL[t.difficulty]} difficulty`].filter(Boolean);
  const kind = parts.join(" · ");
  return t.facts.length > 0
    ? `${kind} · based on your ${t.facts.map((f) => `${f.category.toLowerCase()} “${f.fact}”`).join(", ")}`
    : `${kind} · general question`;
}

export function planDocument(plan: InterviewPlan, meta: DocMeta): string {
  const s = plan.settings;
  const title = `Interview plan${meta.attempt ? ` #${meta.attempt}` : ""}`;
  return document_(title, h`
<h1>${title}</h1>
<p class="meta">${meta.candidateName} · ${when(meta.date)}</p>
<dl>
<dt>Role</dt><dd>${ROLE_LABEL[s.target_role]}</dd>
<dt>Level</dt><dd>${LEVEL_LABEL[s.experience_level]}</dd>
<dt>Interview type</dt><dd>${MODE_LABEL[s.mode]}</dd>
<dt>Difficulty</dt><dd>${DIFFICULTY_LABEL[s.difficulty]}</dd>
<dt>Length</dt><dd>${s.duration_minutes} minutes</dd>
<dt>Topics</dt><dd>${plan.topics.length}</dd>
<dt>Planned by</dt><dd>${plannedBy(plan.source, plan.rules_reason)}</dd>
</dl>
<h2>Topics, in order</h2>
<ol>${plan.topics.map((t) => h`<li><strong>${t.topic}</strong><br><span class="hint">${topicDescription(t)}</span></li>`)}</ol>
${plan.omitted_groups.length > 0 ? h`<p class="note">Left out: ${plan.omitted_groups.map((g) => QUESTION_TYPE_LABEL[g]).join(", ")} (no approved profile details to base it on).</p>` : ""}
<h2>How the interview works</h2>
<ul>
<li>The questions themselves are not shown in advance, as in a real interview.</li>
<li>Each topic may have up to two follow-up questions. You can ask for a question to be put
another way, say you don't know, or skip it.</li>
<li>The clock runs only while the interview is running; pausing stops it.</li>
<li>Questions about you use only the profile details you approved.</li>
</ul>`);
}

const score = (n: number | null, meaning?: string) =>
  n === null ? "too little to judge" : `${n} of 5${meaning ? ` (${meaning})` : ""}`;
const quotes = (items: string[]) =>
  items.length ? h`<ul>${items.map((q) => h`<li><q>${q}</q></li>`)}</ul>` : "";
const nothing = h`<p class="hint">Nothing listed here.</p>`;

/** The report exactly as the report page shows it, section by section. */
export function reportDocument(r: InterviewReport, meta: DocMeta): string {
  const s = r.summary;
  const seq = new Map(r.questions.map((q) => [q.question_id, q.seq]));
  const title = `Interview report${meta.attempt ? ` #${meta.attempt}` : ""}`;
  return document_(title, h`
<h1>${title}</h1>
<p class="meta">${meta.candidateName} · ${when(meta.date)}</p>
<p>Practice feedback for each answer, with the quotes it is based on. Scores belong to one
criterion of one answer and are never combined.</p>
<h2>Summary</h2>
<dl>
<dt>Type</dt><dd>${MODE_LABEL[s.settings.mode]}, ${DIFFICULTY_LABEL[s.settings.difficulty]}, ${s.settings.duration_minutes} minutes (${LEVEL_LABEL[s.settings.experience_level]})</dd>
<dt>Planned by</dt><dd>${s.plan_source === "AI" ? "AI assistance (checked by rules)" : "Fixed rules"}</dd>
<dt>Ending</dt><dd>${s.finish_reason_text}</dd>
<dt>Active time</dt><dd>${formatRemaining(s.active_seconds)} (minutes:seconds)</dd>
<dt>Questions</dt><dd>${s.questions_asked}</dd>
<dt>Responses</dt><dd>${s.answers.answer} answered, ${s.answers.skip} skipped, ${s.answers.dont_know} “I don't know”, ${s.answers.clarify} rephrase requests, ${s.answers.unanswered} not answered</dd>
<dt>Evaluation</dt><dd>${s.evaluations.evaluated} with AI, ${s.evaluations.observations_only} observations only, ${s.evaluations.not_applicable} with nothing to evaluate</dd>
</dl>
<h2>Questions</h2>
<ol>${r.questions.map((q) => h`<li value="${q.seq}"><span class="hint">${QUESTION_KIND_LABEL[q.kind]}</span><br>${q.text}<br><span class="hint">${q.answer_note}${q.evaluation_status ? ` · ${EVALUATION_STATUS_LABEL[q.evaluation_status]}` : ""}</span></li>`)}</ol>
<h2>Topics covered</h2>
<ul>${r.coverage.topics.map((t) => h`<li>${t.topic} <span class="hint">(${COMPETENCY_LABEL[t.competency]}, ${QUESTION_TYPE_LABEL[t.question_type]}) · ${t.note ?? `${t.questions_asked} ${t.questions_asked === 1 ? "question" : "questions"}`}</span></li>`)}</ul>
<h3>By competency</h3>
<ul>${r.coverage.competencies.map((c) => h`<li>${COMPETENCY_LABEL[c.competency]}: ${c.asked_topics} of ${c.planned_topics} planned topics asked</li>`)}</ul>
<h2>Shown clearly</h2>
${r.shown_clearly.length ? h`<ul>${r.shown_clearly.map((i) => h`<li><strong>${CRITERION_LABEL[i.criterion]}</strong> in answer #${i.seq}: ${score(i.score, i.score_meaning)}${quotes(i.evidence)}</li>`)}</ul>` : nothing}
<h2>To practise</h2>
${r.to_practise.criteria.length + r.to_practise.missing_concepts.length ? h`<ul>${r.to_practise.criteria.map((i) => h`<li><strong>${CRITERION_LABEL[i.criterion]}</strong> in answer #${i.seq}: ${score(i.score, i.score_meaning)}<br>${i.practice}${quotes(i.evidence)}</li>`)}${r.to_practise.missing_concepts.map((m) => h`<li><strong>${m.concept}</strong> not covered in answer #${m.seq}<br>${m.practice}</li>`)}</ul>` : nothing}
<h2>Answer evidence</h2>
${r.answer_evidence.length ? r.answer_evidence.map((a) => h`<h3>Answer #${a.seq} <span class="hint">(${EVALUATION_STATUS_LABEL[a.status]})</span></h3>
${a.notice ? h`<p class="note">${a.notice}</p>` : ""}
${a.evaluation.criteria.length ? h`<ul>${a.evaluation.criteria.map((c) => h`<li>${CRITERION_LABEL[c.criterion]}: ${score(c.score)}${quotes(c.evidence)}</li>`)}</ul>` : ""}
${a.evaluation.missing_concepts.length ? h`<p>Planned concepts not covered: ${a.evaluation.missing_concepts.join(", ")}</p>` : ""}
${a.evaluation.claims_to_verify.map((c) => h`<p><q>${c.quote}</q> — needs verification</p>`)}
${a.evaluation.feedback ? h`<p>${a.evaluation.feedback}</p>` : ""}`) : h`<p class="hint">No evaluated answers.</p>`}
<h2>Communication observations</h2>
<ul>${r.communication_observations.answers.map((o) => h`<li>Answer #${o.seq}: ${o.word_count} words${o.concepts_mentioned.length ? `; planned concepts mentioned: ${o.concepts_mentioned.join(", ")}` : ""}</li>`)}</ul>
<p class="hint">${r.communication_observations.speech_metrics.note}</p>
<h2>Topics to practise</h2>
${r.topics_to_practise.length ? h`<ul>${r.topics_to_practise.map((t) => h`<li>${t.topic} <span class="hint">(${COMPETENCY_LABEL[t.competency]})${t.criteria.length + t.missing_concepts.length ? ` · ${[...t.criteria.map((c) => CRITERION_LABEL[c]), ...t.missing_concepts].join(", ")}` : ""}</span></li>`)}</ul>` : nothing}
<h2>Recommended practice</h2>
${r.recommended_practice.length ? h`<ul>${r.recommended_practice.map((p) => h`<li>${p.practice} <span class="hint">(from answer ${p.question_ids.map((id) => `#${seq.get(id)}`).join(", ")})</span></li>`)}</ul>` : nothing}
<h2>Retry</h2>
<p>${r.retry.note}</p>
<h2>Score scale</h2>
<ul>${Object.entries(r.score_scale).map(([k, v]) => h`<li>${k === "null" ? "No score" : k}: ${v}</li>`)}</ul>
<p class="note">${r.limitations}</p>`);
}

/** e.g. "interview-plan-1-2026-10-03.html": no name or id in the file name. */
export function exportFileName(kind: "plan" | "report", date: Date, attempt?: number): string {
  return `interview-${kind}${attempt ? `-${attempt}` : ""}-${date.toISOString().slice(0, 10)}.html`;
}
