"use client";

import { useCallback, useEffect, useState } from "react";
import {
  type QuestionHistory,
  type ReportResult,
  evaluateAnswer,
  generateReport,
  getQuestions,
} from "@/lib/api";
import { COPY, FINISH_LABEL, errorText, fill, pendingEvaluations } from "@/lib/interview";
import { ConsentControl } from "@/components/interview/InterviewSetup";

type Props = { sessionId: string; onReport: (result: ReportResult) => void };

/** REPORT_GENERATION: each answer is evaluated by its own request (the server decides how), then
 * the report is requested. Nothing is evaluated in the browser. */
export default function InterviewFeedback({ sessionId, onReport }: Props) {
  const [history, setHistory] = useState<QuestionHistory | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [notices, setNotices] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setError(null);
    try {
      setHistory(await getQuestions(sessionId, signal));
    } catch (err) {
      if (!signal?.aborted) setError(errorText(err));
    }
  }, [sessionId]);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function run() {
    setError(null);
    try {
      // Re-read first: a retry after an error continues with what is still pending.
      const pending = pendingEvaluations((await getQuestions(sessionId)).questions);
      for (const [i, q] of pending.entries()) {
        setProgress(fill(COPY.evaluating, { i: i + 1, n: pending.length }));
        const result = await evaluateAnswer(sessionId, q.id);
        if (result.notice) setNotices((all) => (all.includes(result.notice!) ? all : [...all, result.notice!]));
      }
      setProgress(COPY.building);
      onReport(await generateReport(sessionId));
    } catch (err) {
      setError(errorText(err));
      setProgress(null);
      await load();
    }
  }

  const pending = history ? pendingEvaluations(history.questions).length : 0;

  return (
    <>
      <h2 tabIndex={-1} data-screen-heading>Your feedback</h2>
      {history?.finish_reason && <p>{FINISH_LABEL[history.finish_reason]}</p>}
      <p className="hint">{COPY.feedbackIntro}</p>
      {history && (
        <p>
          {pending === 0
            ? "No answers are waiting for evaluation."
            : `${pending} ${pending === 1 ? "answer is" : "answers are"} waiting for evaluation.`}
        </p>
      )}
      {!progress && <ConsentControl sessionId={sessionId} note={COPY.consentFeedback} />}
      {progress && <p role="status" aria-live="polite">{progress}</p>}
      {notices.map((n) => <p key={n} className="notice">{n}</p>)}
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="primary" onClick={run} disabled={!history || progress !== null}>
          {progress ? "Working…" : error ? "Try again" : pending ? "Get my feedback" : "Build my report"}
        </button>
      </div>
    </>
  );
}
