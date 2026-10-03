"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  type InterviewSession,
  type InterviewStatus,
  type ReportResult,
  createInterviewSession,
  deleteInterviewSession,
  listInterviewSessions,
} from "@/lib/api";
import { SignedIn } from "@/components/AuthProvider";
import { COPY, errorText, isUnfinished, screenFor } from "@/lib/interview";
import InterviewFeedback from "@/components/interview/InterviewFeedback";
import InterviewReport from "@/components/interview/InterviewReport";
import { PlanForm, ProfileConfirm, ReadyScreen } from "@/components/interview/InterviewSetup";
import InterviewTurn from "@/components/interview/InterviewTurn";

/** The session on screen: its id and the status the server last reported. */
type Active = { id: string; status: InterviewStatus };

export default function InterviewFlow() {
  return <SignedIn>{(candidate) => <Flow candidateId={candidate.id} />}</SignedIn>;
}

/** The signed-in candidate's interviews. candidateId comes from GET /api/auth/me, never storage. */
function Flow({ candidateId }: { candidateId: string }) {
  const [sessions, setSessions] = useState<InterviewSession[] | null>(null);
  const [active, setActive] = useState<Active | null>(null);
  const [report, setReport] = useState<ReportResult | null>(null);
  // The unsent answer, in memory only (never browser storage): survives a pause, not a reload.
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const screenRef = useRef<HTMLElement>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setError(null);
    try {
      setSessions(await listInterviewSessions(candidateId, signal));
    } catch (err) {
      if (!signal?.aborted) setError(errorText(err));
    }
  }, [candidateId]);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const screen = active ? screenFor(active.status) : null;
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
      open(await createInterviewSession());
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

  const errorBox = error && <p className="form-error" role="alert">{error}</p>;

  if (!active) {
    const unfinished = sessions?.find((s) => isUnfinished(s.status));
    const lastCompleted = sessions?.find((s) => s.status === "COMPLETED");
    return (
      <section className="card" aria-labelledby="sessions-heading">
        <h2 id="sessions-heading">Your interview</h2>
        {errorBox}
        {sessions === null && !error && <p>Loading your interviews…</p>}
        {sessions === null && error && (
          <div className="actions"><button type="button" onClick={() => load()}>Retry</button></div>
        )}
        {sessions && unfinished && (
          <>
            <p>{COPY.resumePrompt} Started {new Date(unfinished.created_at).toLocaleString()}.</p>
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
              {lastCompleted && (
                <button type="button" onClick={() => open(lastCompleted)} disabled={busy}>
                  View your last report
                </button>
              )}
            </div>
          </>
        )}
      </section>
    );
  }

  return (
    <section className="card interview" ref={screenRef} aria-label="Interview">
      {screen === "confirm" && (
        <ProfileConfirm sessionId={active.id} candidateId={candidateId} onStatus={onStatus} />
      )}
      {screen === "plan" && <PlanForm sessionId={active.id} onStatus={onStatus} />}
      {screen === "ready" && <ReadyScreen sessionId={active.id} onStatus={onStatus} />}
      {(screen === "turn" || screen === "paused") && (
        <InterviewTurn sessionId={active.id} paused={screen === "paused"} onStatus={onStatus}
                       draft={draft} setDraft={setDraft} />
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
          onRetry={(view) => open({ id: view.session_id, status: view.status })}
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
