"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  type AnswerKind,
  type ClientAction,
  type InterviewStatus,
  type TurnResult,
  actOnSession,
  getInterviewSession,
  nextQuestion,
  submitAnswer,
} from "@/lib/api";
import {
  ANSWER_KIND_LABEL,
  ANSWER_MAX_LENGTH,
  ANSWER_WARN_AT,
  COPY,
  QUESTION_KIND_LABEL,
  RULES_REASON_TEXT,
  answerLength,
  errorText,
  formatRemaining,
  isConflict,
  isNetworkError,
  screenFor,
} from "@/lib/interview";

type Props = {
  sessionId: string;
  paused: boolean;
  onStatus: (status: InterviewStatus) => void;
  // The unsent answer lives in the parent's memory only, so a pause doesn't lose it. Never stored.
  draft: string;
  setDraft: (text: string) => void;
};

const OTHER_KINDS: AnswerKind[] = ["CLARIFY", "DONT_KNOW", "SKIP"];

/** Seconds left as shown: the server's figure, counted down locally between requests. The
 * server alone decides whether an answer is in time. */
function useCountdown(turn: TurnResult | null, fetchedAt: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  if (!turn) return null;
  return turn.progress.time_remaining_seconds - Math.max(0, now - fetchedAt) / 1000;
}

export default function InterviewTurn({ sessionId, paused, onStatus, draft, setDraft }: Props) {
  const [turn, setTurn] = useState<TurnResult | null>(null);
  const [fetchedAt, setFetchedAt] = useState(0); // when the server's time figure arrived
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // After a refusal (e.g. the time limit) the page waits for the candidate before moving on, so
  // the unsent text stays visible next to the server's message.
  const [blocked, setBlocked] = useState(false);
  const questionRef = useRef<HTMLParagraphElement>(null);
  const remaining = useCountdown(turn, fetchedAt);

  const loadNext = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const result = await nextQuestion(sessionId);
      if (result.question === null) return onStatus(result.status); // finished: feedback next
      setFetchedAt(Date.now());
      setTurn(result);
    } catch (err) {
      setError(errorText(err));
      if (isConflict(err)) setBlocked(true);
    } finally {
      setBusy(false);
    }
  }, [sessionId, onStatus]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    if (!paused) loadNext();
  }, [paused, loadNext]);

  const questionId = turn?.question?.id;
  useEffect(() => {
    if (questionId) questionRef.current?.focus(); // a new question: move focus to it
  }, [questionId]);

  async function send(kind: AnswerKind) {
    if (!turn?.question) return;
    setBusy(true);
    setError(null);
    try {
      await submitAnswer(sessionId, turn.question.id, kind, kind === "ANSWER" ? draft : undefined);
    } catch (err) {
      setError(isNetworkError(err) ? COPY.networkKept : errorText(err));
      if (isConflict(err)) setBlocked(true);
      setBusy(false);
      return;
    }
    setDraft(""); // saved by the server: only now is the local copy dropped
    setTurn(null); // that question is answered; a failed fetch of the next one offers Try again
    await loadNext();
  }

  async function act(action: ClientAction, confirmText?: string) {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(true);
    setError(null);
    try {
      onStatus((await actOnSession(sessionId, action)).status);
    } catch (err) {
      setError(errorText(err));
      if (isConflict(err)) setBlocked(true);
    } finally {
      setBusy(false);
    }
  }

  /** Re-read the session after a refusal and go where the server says. */
  async function proceed() {
    setBusy(true);
    setError(null);
    try {
      const session = await getInterviewSession(sessionId);
      setBlocked(false);
      if (screenFor(session.status) === "turn") await loadNext();
      else onStatus(session.status);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const errorBox = error && (
    <div role="alert">
      <p className="form-error">{error}</p>
      {blocked ? (
        <div className="actions">
          <button type="button" onClick={proceed} disabled={busy}>Continue</button>
        </div>
      ) : (
        !turn?.question && !paused && (
          <div className="actions">
            <button type="button" onClick={loadNext} disabled={busy}>Try again</button>
          </div>
        )
      )}
    </div>
  );

  if (paused) {
    return (
      <>
        <h2 tabIndex={-1} data-screen-heading>Interview paused</h2>
        <p>{COPY.paused}</p>
        {draft && <p className="hint">Your unsent answer is kept on this page until you resume.</p>}
        {errorBox}
        <div className="actions">
          <button type="button" className="primary" onClick={() => act("RESUME")} disabled={busy}>
            {busy ? "Working…" : "Resume"}
          </button>
          <button type="button" onClick={() => act("END_INTERVIEW", COPY.endConfirm)} disabled={busy}>
            End interview
          </button>
        </div>
      </>
    );
  }

  const q = turn?.question;
  const length = answerLength(draft);
  const waiting = turn?.status === "WAITING_FOR_ANSWER";

  function submit(e: FormEvent) {
    e.preventDefault();
    send("ANSWER");
  }

  return (
    <>
      <h2 tabIndex={-1} data-screen-heading>Interview</h2>
      {turn && remaining !== null && (
        <p className="timer">
          <span>Time left: <strong>{formatRemaining(remaining)}</strong></span>
          <span className="hint">{COPY.timerNote}</span>
        </p>
      )}
      {!q && !error && <p aria-live="polite">Loading the next question…</p>}
      {q && turn && (
        <form onSubmit={submit}>
          <div className="question" aria-live="polite">
            <p className="hint">
              {QUESTION_KIND_LABEL[q.kind]} · Topic {q.topic_position} of {turn.progress.topics_total}:{" "}
              {q.topic}
            </p>
            <p className="question-text" ref={questionRef} tabIndex={-1}>{q.text}</p>
            {q.source === "AI" && <p className="hint">{COPY.aiWorded}</p>}
            {q.source === "RULES" && q.kind !== "TOPIC" && q.rules_reason &&
              q.rules_reason !== "NOT_REQUESTED" && q.rules_reason !== "NOT_CONFIGURED" && (
              <p className="hint">{RULES_REASON_TEXT[q.rules_reason]}</p>
            )}
          </div>
          <div className="field">
            <label htmlFor="answer">Your answer</label>
            <textarea
              id="answer"
              rows={8}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              disabled={blocked}
              aria-describedby="answer-count"
            />
            <span id="answer-count" className={length >= ANSWER_WARN_AT ? "field-error" : "hint"}>
              {length.toLocaleString()} / {ANSWER_MAX_LENGTH.toLocaleString()} characters
              {length >= ANSWER_WARN_AT && ` — ${COPY.lengthWarning}`}
            </span>
          </div>
          {errorBox}
          <div className="actions">
            <button type="submit" disabled={busy || blocked || !waiting || length === 0}>
              {busy ? "Sending…" : ANSWER_KIND_LABEL.ANSWER}
            </button>
            {OTHER_KINDS.map((kind) => (
              <button key={kind} type="button" onClick={() => send(kind)}
                      disabled={busy || blocked || !waiting}>
                {ANSWER_KIND_LABEL[kind]}
              </button>
            ))}
          </div>
        </form>
      )}
      {!q && errorBox}
      <div className="actions secondary">
        <button type="button" onClick={() => act("PAUSE")} disabled={busy || blocked || !waiting}>
          Pause
        </button>
        <button type="button" onClick={() => act("END_INTERVIEW", COPY.endConfirm)}
                disabled={busy || blocked || !waiting}>
          End interview
        </button>
      </div>
      <p className="hint">{COPY.browserClose}</p>
    </>
  );
}
