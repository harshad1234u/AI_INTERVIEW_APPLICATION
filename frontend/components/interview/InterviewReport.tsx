"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  type InterviewPlanView,
  type InterviewReport as Report,
  type ReportResult,
  getReport,
  retryInterview,
} from "@/lib/api";
import {
  COMPETENCY_LABEL,
  COPY,
  CRITERION_LABEL,
  DIFFICULTY_LABEL,
  EVALUATION_STATUS_LABEL,
  LEVEL_LABEL,
  MODE_LABEL,
  QUESTION_KIND_LABEL,
  QUESTION_TYPE_LABEL,
  canRetry,
  errorText,
  formatRemaining,
  seqById,
} from "@/lib/interview";
import { exportFileName, reportDocument } from "@/lib/exportDoc";
import ExportButtons from "@/components/interview/ExportButtons";

type Props = {
  sessionId: string;
  initial: ReportResult | null;
  onRetry: (view: InterviewPlanView) => void;
  candidateName: string;
  attempt?: number;
  /** The attempt this one retries, when known: "Retry of interview #n". */
  retryOf?: number;
};

/** Quotes are the candidate's own words, rendered as plain text. */
function Quotes({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <ul className="quotes">
      {items.map((quote, i) => <li key={i}><q>{quote}</q></li>)}
    </ul>
  );
}

/** One criterion of one answer, exactly as stored: never combined with any other score. */
function Score({ score, meaning }: { score: number | null; meaning?: string }) {
  if (score === null) return <span className="hint">too little to judge</span>;
  return <span>{score} of 5{meaning && ` (${meaning})`}</span>;
}

export default function InterviewReport({ sessionId, initial, onRetry, candidateName, attempt,
                                          retryOf }: Props) {
  const [result, setResult] = useState<ReportResult | null>(initial);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  useEffect(() => {
    if (initial) return;
    const controller = new AbortController();
    getReport(sessionId, controller.signal)
      .then(setResult)
      .catch((err) => {
        if (!controller.signal.aborted) setError(errorText(err));
      });
    return () => controller.abort();
  }, [sessionId, initial]);

  async function retry() {
    setRetrying(true);
    setRetryError(null);
    try {
      onRetry(await retryInterview(sessionId));
    } catch (err) {
      setRetryError(errorText(err)); // the report stays on screen
      setRetrying(false);
    }
  }

  if (error) return <p className="form-error" role="alert">{error}</p>;
  if (!result) return <p>Loading your report…</p>;
  const r: Report = result.report;
  const seq = seqById(r.questions);
  const refs = (ids: string[]) => ids.map((id) => `#${seq.get(id)}`).join(", ");
  const s = r.summary;

  return (
    <>
      <h2 tabIndex={-1} data-screen-heading>
        Your interview report{attempt ? ` (interview #${attempt})` : ""}
      </h2>
      {retryOf && <p className="hint">A retry of interview #{retryOf}.</p>}
      <p className="hint">{COPY.reportIntro}</p>
      <ExportButtons
        what="report"
        fileName={exportFileName("report", new Date(), attempt)}
        build={() => reportDocument(r, { candidateName, date: new Date(), attempt })}
      />

      <section aria-labelledby="r-summary">
        <h3 id="r-summary">Summary</h3>
        <dl>
          <dt>Type</dt>
          <dd>{MODE_LABEL[s.settings.mode]}, {DIFFICULTY_LABEL[s.settings.difficulty]},{" "}
            {s.settings.duration_minutes} minutes ({LEVEL_LABEL[s.settings.experience_level]})</dd>
          <dt>Planned by</dt>
          <dd>{s.plan_source === "AI" ? "AI assistance (checked by rules)" : "Fixed rules"}</dd>
          <dt>Ending</dt>
          <dd>{s.finish_reason_text}</dd>
          <dt>Active time</dt>
          <dd>{formatRemaining(s.active_seconds)} (minutes:seconds)</dd>
          <dt>Questions</dt>
          <dd>{s.questions_asked}</dd>
          <dt>Responses</dt>
          <dd>
            {s.answers.answer} answered, {s.answers.skip} skipped, {s.answers.dont_know} &ldquo;I
            don&apos;t know&rdquo;, {s.answers.clarify} rephrase requests, {s.answers.unanswered}{" "}
            not answered
          </dd>
          <dt>Evaluation</dt>
          <dd>
            {s.evaluations.evaluated} with AI, {s.evaluations.observations_only} observations only,{" "}
            {s.evaluations.not_applicable} with nothing to evaluate
          </dd>
        </dl>
      </section>

      <section aria-labelledby="r-questions">
        <h3 id="r-questions">Questions</h3>
        <ol className="plain-list">
          {r.questions.map((q) => (
            <li key={q.question_id}>
              <span className="hint">#{q.seq} · {QUESTION_KIND_LABEL[q.kind]}</span>
              <p>{q.text}</p>
              <p className="hint">
                {q.answer_note}
                {q.evaluation_status && ` · ${EVALUATION_STATUS_LABEL[q.evaluation_status]}`}
              </p>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="r-coverage">
        <h3 id="r-coverage">Topics covered</h3>
        <ul className="plain-list">
          {r.coverage.topics.map((t) => (
            <li key={t.topic_position}>
              {t.topic} <span className="hint">({COMPETENCY_LABEL[t.competency]},{" "}
                {QUESTION_TYPE_LABEL[t.question_type]})</span>
              <br />
              <span className="hint">
                {t.note ?? `${t.questions_asked} ${t.questions_asked === 1 ? "question" : "questions"}`}
              </span>
            </li>
          ))}
        </ul>
        <h4>By competency</h4>
        <ul className="plain-list">
          {r.coverage.competencies.map((c) => (
            <li key={c.competency}>
              {COMPETENCY_LABEL[c.competency]}: {c.asked_topics} of {c.planned_topics} planned
              topics asked
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="r-shown">
        <h3 id="r-shown">Shown clearly</h3>
        {r.shown_clearly.length === 0 && <p className="hint">Nothing listed here.</p>}
        <ul className="plain-list">
          {r.shown_clearly.map((i) => (
            <li key={`${i.question_id}-${i.criterion}`}>
              <strong>{CRITERION_LABEL[i.criterion]}</strong> in answer #{i.seq}:{" "}
              <Score score={i.score} meaning={i.score_meaning} />
              <Quotes items={i.evidence} />
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="r-practise">
        <h3 id="r-practise">To practise</h3>
        {r.to_practise.criteria.length + r.to_practise.missing_concepts.length === 0 && (
          <p className="hint">Nothing listed here.</p>
        )}
        <ul className="plain-list">
          {r.to_practise.criteria.map((i) => (
            <li key={`${i.question_id}-${i.criterion}`}>
              <strong>{CRITERION_LABEL[i.criterion]}</strong> in answer #{i.seq}:{" "}
              <Score score={i.score} meaning={i.score_meaning} />
              <p>{i.practice}</p>
              <Quotes items={i.evidence} />
            </li>
          ))}
          {r.to_practise.missing_concepts.map((m) => (
            <li key={`${m.question_id}-${m.concept}`}>
              <strong>{m.concept}</strong> not covered in answer #{m.seq}
              <p>{m.practice}</p>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="r-evidence">
        <h3 id="r-evidence">Answer evidence</h3>
        {r.answer_evidence.length === 0 && <p className="hint">No evaluated answers.</p>}
        {r.answer_evidence.map((a) => (
          <article key={a.question_id} className="evidence">
            <h4>Answer #{a.seq} <span className="hint">({EVALUATION_STATUS_LABEL[a.status]})</span></h4>
            {a.notice && <p className="notice">{a.notice}</p>}
            {a.evaluation.criteria.length > 0 && (
              <ul className="plain-list">
                {a.evaluation.criteria.map((c) => (
                  <li key={c.criterion}>
                    {CRITERION_LABEL[c.criterion]}: <Score score={c.score} />
                    <Quotes items={c.evidence} />
                  </li>
                ))}
              </ul>
            )}
            {a.evaluation.missing_concepts.length > 0 && (
              <p>Planned concepts not covered: {a.evaluation.missing_concepts.join(", ")}</p>
            )}
            {a.evaluation.claims_to_verify.map((c, i) => (
              <p key={i}><q>{c.quote}</q> <span className="badge">Needs verification</span></p>
            ))}
            {a.evaluation.feedback && <p>{a.evaluation.feedback}</p>}
          </article>
        ))}
      </section>

      <section aria-labelledby="r-observations">
        <h3 id="r-observations">Communication observations</h3>
        <ul className="plain-list">
          {r.communication_observations.answers.map((o) => (
            <li key={o.question_id}>
              Answer #{o.seq}: {o.word_count} words
              {o.concepts_mentioned.length > 0 && `; planned concepts mentioned: ${o.concepts_mentioned.join(", ")}`}
            </li>
          ))}
        </ul>
        <p className="hint">{r.communication_observations.speech_metrics.note}</p>
      </section>

      <section aria-labelledby="r-topics">
        <h3 id="r-topics">Topics to practise</h3>
        {r.topics_to_practise.length === 0 && <p className="hint">Nothing listed here.</p>}
        <ul className="plain-list">
          {r.topics_to_practise.map((t) => (
            <li key={t.topic_position}>
              {t.topic} <span className="hint">({COMPETENCY_LABEL[t.competency]})</span>
              {(t.criteria.length > 0 || t.missing_concepts.length > 0) && (
                <p className="hint">
                  {[...t.criteria.map((c) => CRITERION_LABEL[c]), ...t.missing_concepts].join(", ")}
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="r-recommended">
        <h3 id="r-recommended">Recommended practice</h3>
        {r.recommended_practice.length === 0 && <p className="hint">Nothing listed here.</p>}
        <ul className="plain-list">
          {r.recommended_practice.map((p) => (
            <li key={p.practice}>
              {p.practice} <span className="hint">(from answer {refs(p.question_ids)})</span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="r-retry">
        <h3 id="r-retry">Retry</h3>
        <p>{r.retry.note}</p>
        {retryError && <p className="form-error" role="alert">{retryError}</p>}
        {retrying && <p role="status">{COPY.retryWorking}</p>}
        {canRetry(r.retry) && (
          <div className="actions">
            <button type="button" className="primary" onClick={retry} disabled={retrying}>
              Retry the topics to practise
            </button>
          </div>
        )}
      </section>

      <section aria-labelledby="r-scale">
        <h3 id="r-scale">Score scale</h3>
        <ul className="plain-list">
          {Object.entries(r.score_scale).map(([k, v]) => (
            <li key={k}>{k === "null" ? "No score" : k}: {v}</li>
          ))}
        </ul>
        <p className="notice">{r.limitations}</p>
      </section>

      <p>
        <Link href="/">Back to your profile</Link>
      </p>
    </>
  );
}
