"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  type Candidate,
  type InterviewSession,
  type InterviewStatus,
  type ReportResult,
  createInterviewSession,
  deleteInterviewSession,
  listInterviewSessions,
} from "@/lib/api";
import { SignedIn } from "@/components/AuthProvider";
import {
  COPY,
  DIFFICULTY_LABEL,
  FINISH_LABEL,
  MODE_LABEL,
  attemptNumbers,
  attemptState,
  errorText,
  isUnfinished,
  screenFor,
} from "@/lib/interview";
import InterviewFeedback from "@/components/interview/InterviewFeedback";
import InterviewReport from "@/components/interview/InterviewReport";
import { PlanForm, ProfileConfirm, ReadyScreen } from "@/components/interview/InterviewSetup";
import InterviewTurn from "@/components/interview/InterviewTurn";
import { useExpressionCamera } from "@/components/interview/useExpressionCamera";
import { useVoice } from "@/components/interview/useVoice";

/** The session on screen: its id and the status the server last reported. */
type Active = { id: string; status: InterviewStatus };

export default function InterviewFlow() {
  return <SignedIn>{(candidate) => <Flow candidate={candidate} />}</SignedIn>;
}

/** The signed-in candidate's interviews. The candidate comes from GET /api/auth/me, never storage. */
function Flow({ candidate }: { candidate: Candidate }) {
  const [sessions, setSessions] = useState<InterviewSession[] | null>(null);
  const [active, setActive] = useState<Active | null>(null);
  const [report, setReport] = useState<ReportResult | null>(null);
  // The unsent answer, in memory only (never browser storage): survives a pause, not a reload.
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const screenRef = useRef<HTMLElement>(null);
  // Optional camera: lives here so a pause keeps it, and is released whenever it is not needed.
  const camera = useExpressionCamera();
  // Optional voice mode: also lives here so a pause keeps its settings; it never holds audio.
  const voice = useVoice();

  const load = useCallback(async (signal?: AbortSignal) => {
    setError(null);
    try {
      setSessions(await listInterviewSessions(candidate.id, signal));
    } catch (err) {
      if (!signal?.aborted) setError(errorText(err));
    }
  }, [candidate.id]);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const screen = active ? screenFor(active.status) : null;
  const cameraScreen = screen === "ready" || screen === "turn" || screen === "paused";
  const { disable: releaseCamera, state: cameraState } = camera;
  useEffect(() => {
    if (!cameraScreen && cameraState !== "off") releaseCamera();
  }, [cameraScreen, cameraState, releaseCamera]);
  const { silence: silenceVoice } = voice;
  useEffect(() => {
    if (!cameraScreen) silenceVoice(); // off the interview: no speaker, no microphone
  }, [cameraScreen, silenceVoice]);
  useEffect(() => {
    // A new screen: move focus to its heading so keyboard and screen-reader users follow along.
    screenRef.current?.querySelector<HTMLElement>("[data-screen-heading]")?.focus();
  }, [screen, active?.id]);

  const onStatus = useCallback((status: InterviewStatus) => {
    setActive((current) => (current ? { ...current, status } : current));
  }, []);

  function open(session: { id: string; status: InterviewStatus }) {
    setReport(null);
    setDraft("");
    setError(null);
    setActive({ id: session.id, status: session.status });
  }

  async function startNew() {
    setBusy(true);
    setError(null);
    try {
      const session = await createInterviewSession();
      open(session);
      load(); // the new attempt gets its number in the history
    } catch (err) {
      setError(errorText(err)); // e.g. 409: an unfinished session exists (the server's message)
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function discard(id: string) {
    if (!window.confirm(COPY.discardConfirm)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteInterviewSession(id);
    } catch (err) {
      // 404: already gone, which is what was asked for. Anything else is shown.
      if (!(err && typeof err === "object" && "status" in err && err.status === 404)) {
        setError(errorText(err));
        setBusy(false);
        return;
      }
    }
    setActive(null);
    setReport(null);
    setDraft("");
    setSessions(null);
    setBusy(false);
    await load();
  }

  function leave() {
    setActive(null);
    setReport(null);
    setDraft("");
    setSessions(null);
    load();
  }

  const numbers = attemptNumbers(sessions ?? []);
  const errorBox = error && <p className="form-error" role="alert">{error}</p>;

  if (!active) {
    const unfinished = sessions?.find((s) => isUnfinished(s.status));
    return (
      <>
        <section className="card" aria-labelledby="sessions-heading">
          <h2 id="sessions-heading">Your interview</h2>
          {errorBox}
          {sessions === null && !error && <p>Loading your interviews…</p>}
          {sessions === null && error && (
            <div className="actions"><button type="button" onClick={() => load()}>Retry</button></div>
          )}
          {sessions && unfinished && (
            <>
              <p>
                {COPY.resumePrompt} Interview #{numbers.get(unfinished.id)}, started{" "}
                {new Date(unfinished.created_at).toLocaleString()}.
              </p>
              <div className="actions">
                <button type="button" className="primary" onClick={() => open(unfinished)} disabled={busy}>
                  Resume
                </button>
                <button type="button" className="danger" onClick={() => discard(unfinished.id)} disabled={busy}>
                  Discard
                </button>
              </div>
            </>
          )}
          {sessions && !unfinished && (
            <>
              <p>{COPY.startNew}</p>
              <div className="actions">
                <button type="button" className="primary" onClick={startNew} disabled={busy}>
                  {busy ? "Starting…" : "Start a new interview"}
                </button>
              </div>
            </>
          )}
        </section>
        {sessions && sessions.length > 0 && (
          <History sessions={sessions} numbers={numbers} busy={busy} onOpen={open} onDelete={discard} />
        )}
      </>
    );
  }

  const attempt = numbers.get(active.id);
  const listed = sessions?.find((s) => s.id === active.id);
  const retryOf = listed?.retry_of_id ? numbers.get(listed.retry_of_id) : undefined;

  return (
    <section className="card interview" ref={screenRef} aria-label="Interview">
      {screen === "confirm" && (
        <ProfileConfirm sessionId={active.id} candidateId={candidate.id} onStatus={onStatus} />
      )}
      {screen === "plan" && <PlanForm sessionId={active.id} onStatus={onStatus} />}
      {screen === "ready" && (
        <ReadyScreen sessionId={active.id} onStatus={onStatus} candidateName={candidate.name}
                     attempt={attempt} camera={camera} voice={voice} />
      )}
      {(screen === "turn" || screen === "paused") && (
        <InterviewTurn sessionId={active.id} paused={screen === "paused"} onStatus={onStatus}
                       draft={draft} setDraft={setDraft} camera={camera} voice={voice} />
      )}
      {screen === "feedback" && (
        <InterviewFeedback
          sessionId={active.id}
          onReport={(result) => {
            setReport(result);
            onStatus(result.status);
          }}
        />
      )}
      {screen === "report" && (
        <InterviewReport
          key={active.id}
          sessionId={active.id}
          initial={report}
          candidateName={candidate.name}
          attempt={attempt}
          retryOf={retryOf}
          onRetry={(view) => {
            open({ id: view.session_id, status: view.status });
            load(); // the retry is a new attempt in the history
          }}
        />
      )}
      {errorBox}
      <div className="actions secondary">
        {screen !== "report" && (
          <button type="button" className="danger" onClick={() => discard(active.id)} disabled={busy}>
            {busy ? "Discarding…" : "Discard interview"}
          </button>
        )}
        <button type="button" onClick={leave} disabled={busy}>Back to your interviews</button>
      </div>
    </section>
  );
}

type HistoryProps = {
  sessions: InterviewSession[];
  numbers: Map<string, number>;
  busy: boolean;
  onOpen: (s: InterviewSession) => void;
  onDelete: (id: string) => void;
};

/** Every attempt, newest first. Each keeps its own report: attempts are never combined. */
function History({ sessions, numbers, busy, onOpen, onDelete }: HistoryProps) {
  return (
    <section className="card" aria-labelledby="history-heading">
      <h2 id="history-heading">Your interview history</h2>
      <p className="hint">
        Each interview keeps its own report. A retry practises the topics a report marked to
        practise; its results are never merged with the original&apos;s.
      </p>
      <ul className="history">
        {sessions.map((s) => {
          const n = numbers.get(s.id);
          const source = s.retry_of_id ? numbers.get(s.retry_of_id) : undefined;
          return (
            <li key={s.id} className="history-item">
              <div>
                <strong>Interview #{n}</strong>{" "}
                <span className="hint">{new Date(s.created_at).toLocaleString()}</span>
                <br />
                {s.settings
                  ? `${MODE_LABEL[s.settings.mode]}, ${DIFFICULTY_LABEL[s.settings.difficulty]}, ` +
                    `${s.settings.duration_minutes} minutes`
                  : "Not planned yet"}
                {" · "}
                <span className="badge">{attemptState(s.status)}</span>
                {source && <span className="hint"> · retry of interview #{source}</span>}
                {s.retry_of_id && !source && <span className="hint"> · a retry</span>}
                {s.finish_reason && <><br /><span className="hint">{FINISH_LABEL[s.finish_reason]}</span></>}
              </div>
              <div className="actions">
                <button type="button" onClick={() => onOpen(s)} disabled={busy}
                        aria-label={`${s.status === "COMPLETED" ? "View the report of" : "Continue"} interview #${n}`}>
                  {s.status === "COMPLETED" ? "View report" : "Continue"}
                </button>
                <button type="button" className="danger" onClick={() => onDelete(s.id)} disabled={busy}
                        aria-label={`Delete interview #${n}`}>
                  Delete
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
