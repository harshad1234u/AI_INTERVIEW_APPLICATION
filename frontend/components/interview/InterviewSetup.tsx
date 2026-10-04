"use client";

import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  type ClientAction,
  type Difficulty,
  type Duration,
  type ExperienceLevel,
  type Fact,
  type InterviewMode,
  type InterviewPlan,
  type InterviewStatus,
  type PlanSettings,
  actOnSession,
  getConsent,
  getInterviewPlan,
  getResumeFacts,
  listManualFacts,
  listResumes,
  planInterview,
  setConsent,
} from "@/lib/api";
import {
  COPY,
  DIFFICULTY_LABEL,
  LEVEL_LABEL,
  MODE_LABEL,
  QUESTION_TYPE_LABEL,
  ROLE_LABEL,
  RULES_REASON_TEXT,
  errorText,
} from "@/lib/interview";
import { MANUAL_LABEL } from "@/lib/profile";
import { exportFileName, planDocument, topicDescription } from "@/lib/exportDoc";
import ExportButtons from "@/components/interview/ExportButtons";
import CameraPanel from "@/components/interview/CameraPanel";
import type { Camera } from "@/components/interview/useExpressionCamera";
import type { Voice } from "@/components/interview/useVoice";
import { VoiceSetup } from "@/components/interview/VoicePanel";

type StepProps = { sessionId: string; onStatus: (status: InterviewStatus) => void };

function useAction(sessionId: string, onStatus: (status: InterviewStatus) => void) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = async (action: ClientAction) => {
    setBusy(true);
    setError(null);
    try {
      onStatus((await actOnSession(sessionId, action)).status);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  return { busy, error, run };
}

// ---------- PROFILE_REVIEW ----------

export function ProfileConfirm({ sessionId, candidateId, onStatus }: StepProps & { candidateId: string }) {
  const [facts, setFacts] = useState<Fact[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { busy, error, run } = useAction(sessionId, onStatus);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadError(null);
    try {
      const [resumes, manual] = await Promise.all(
        [listResumes(candidateId, signal), listManualFacts(candidateId, signal)]);
      const lists = await Promise.all(resumes.map((r) => getResumeFacts(r.id, signal)));
      setFacts([...lists.flat(), ...manual]); // resume facts, then the ones the candidate added
    } catch (err) {
      if (!signal?.aborted) setLoadError(errorText(err));
    }
  }, [candidateId]);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const approved = facts?.filter((f) => f.status === "APPROVED") ?? [];
  const pending = facts?.filter((f) => f.status === "PENDING_REVIEW").length ?? 0;

  return (
    <>
      <h2 tabIndex={-1} data-screen-heading>Confirm your profile</h2>
      <p className="hint">{COPY.confirmIntro}</p>
      {loadError && <p className="form-error" role="alert">{loadError}</p>}
      {facts === null && !loadError && <p>Loading your facts…</p>}
      {facts && (
        <>
          <p>
            {approved.length} approved {approved.length === 1 ? "fact" : "facts"}
            {pending > 0 && `, ${pending} still pending review`}.
          </p>
          {approved.length > 0 && (
            <ul className="plain-list">
              {approved.map((f) => (
                <li key={f.id}>
                  <span className="badge">{f.category.toLowerCase()}</span> {f.fact}
                  {f.source === "MANUAL" && <span className="hint"> · {MANUAL_LABEL}</span>}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      {error && (
        <div role="alert">
          <p className="form-error">{error}</p>
          <p className="hint">
            {COPY.pendingFacts} <Link href="/">Go to your profile</Link>
          </p>
        </div>
      )}
      <div className="actions">
        <button type="button" className="primary" onClick={() => run("CONFIRM_PROFILE")} disabled={busy}>
          {busy ? "Confirming…" : "Confirm profile"}
        </button>
      </div>
    </>
  );
}

// ---------- AI consent (per session, default off) ----------

export function ConsentControl({ sessionId, note }: { sessionId: string; note?: string }) {
  const [granted, setGranted] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getConsent(sessionId, controller.signal)
      .then((c) => setGranted(c.granted))
      .catch((err) => {
        if (!controller.signal.aborted) setError(errorText(err));
      });
    return () => controller.abort();
  }, [sessionId]);

  async function change(next: boolean) {
    setBusy(true);
    setError(null);
    try {
      setGranted((await setConsent(sessionId, next)).granted);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="consent" aria-live="polite">
      {granted !== null && <p><strong>{granted ? COPY.consentOn : COPY.consentOff}</strong></p>}
      {note && <p className="hint">{note}</p>}
      {granted === false && <p className="hint">{COPY.consentDisclosure}</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
      {granted !== null && (
        <div className="actions">
          <button type="button" onClick={() => change(!granted)} disabled={busy}>
            {busy ? "Saving…" : granted ? "Turn off AI assistance" : "Turn on AI assistance"}
          </button>
        </div>
      )}
    </div>
  );
}

// ---------- INTERVIEW_PLANNING ----------

const LEVELS = Object.keys(LEVEL_LABEL) as ExperienceLevel[];
const MODES = Object.keys(MODE_LABEL) as InterviewMode[];
const DIFFICULTIES = Object.keys(DIFFICULTY_LABEL) as Difficulty[];
const DURATIONS: Duration[] = [15, 30, 45];
const DEFAULTS: PlanSettings = {
  target_role: "SOFTWARE_DEVELOPER_INTERN", // the only role the backend defines
  experience_level: "STUDENT",
  mode: "MIXED",
  difficulty: "MEDIUM",
  duration_minutes: 15,
};

export function PlanForm({ sessionId, onStatus }: StepProps) {
  const [settings, setSettings] = useState<PlanSettings>(DEFAULTS);
  const [consent, setConsentChoice] = useState(false);
  const [serverConsent, setServerConsent] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    // Reflect the session's stored choice (off for a new session); never copied from elsewhere.
    getConsent(sessionId, controller.signal)
      .then((c) => {
        setServerConsent(c.granted);
        setConsentChoice(c.granted);
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(errorText(err));
      });
    return () => controller.abort();
  }, [sessionId]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (serverConsent !== consent) {
        setServerConsent((await setConsent(sessionId, consent)).granted);
      }
      onStatus((await planInterview(sessionId, settings)).status);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  }

  const select = <K extends keyof PlanSettings>(key: K, label: string, values: PlanSettings[K][],
                                                 text: (v: PlanSettings[K]) => string) => (
    <div className="field">
      <label htmlFor={`plan-${key}`}>{label}</label>
      <select
        id={`plan-${key}`}
        value={String(settings[key])}
        onChange={(e) => {
          const raw = e.target.value;
          const value = (key === "duration_minutes" ? Number(raw) : raw) as PlanSettings[K];
          setSettings({ ...settings, [key]: value });
        }}
      >
        {values.map((v) => (
          <option key={String(v)} value={String(v)}>{text(v)}</option>
        ))}
      </select>
    </div>
  );

  return (
    <form onSubmit={submit}>
      <h2 tabIndex={-1} data-screen-heading>Plan your interview</h2>
      <p>
        <span className="hint">Role:</span> {ROLE_LABEL[settings.target_role]}
      </p>
      {select("experience_level", "Experience level", LEVELS, (v) => LEVEL_LABEL[v])}
      {select("mode", "Interview type", MODES, (v) => MODE_LABEL[v])}
      {select("difficulty", "Difficulty", DIFFICULTIES, (v) => DIFFICULTY_LABEL[v])}
      {select("duration_minutes", "Length", DURATIONS, (v) => `${v} minutes`)}
      <div className="field checkbox">
        <input
          id="plan-consent"
          type="checkbox"
          checked={consent}
          disabled={serverConsent === null}
          onChange={(e) => setConsentChoice(e.target.checked)}
          aria-describedby="plan-consent-help"
        />
        <label htmlFor="plan-consent">{COPY.consentLabel}</label>
      </div>
      <p id="plan-consent-help" className="hint">{COPY.consentDisclosure}</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="actions">
        <button type="submit" disabled={busy || serverConsent === null}>
          {busy ? "Planning…" : "Plan interview"}
        </button>
      </div>
    </form>
  );
}

// ---------- READY ----------

export function ReadyScreen({ sessionId, onStatus, candidateName, attempt, camera, voice }: StepProps & {
  candidateName: string;
  attempt?: number;
  camera: Camera;
  voice: Voice;
}) {
  const [plan, setPlan] = useState<InterviewPlan | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const { busy, error, run } = useAction(sessionId, onStatus);

  useEffect(() => {
    const controller = new AbortController();
    getInterviewPlan(sessionId, controller.signal)
      .then((view) => setPlan(view.plan))
      .catch((err) => {
        if (!controller.signal.aborted) setLoadError(errorText(err));
      });
    return () => controller.abort();
  }, [sessionId]);

  return (
    <>
      <h2 tabIndex={-1} data-screen-heading>Ready to start</h2>
      <p className="hint">{COPY.readyIntro}</p>
      {loadError && <p className="form-error" role="alert">{loadError}</p>}
      {plan && (
        <>
          <dl>
            <dt>Role</dt>
            <dd>{ROLE_LABEL[plan.settings.target_role]}</dd>
            <dt>Level</dt>
            <dd>{LEVEL_LABEL[plan.settings.experience_level]}</dd>
            <dt>Type</dt>
            <dd>{MODE_LABEL[plan.settings.mode]}</dd>
            <dt>Difficulty</dt>
            <dd>{DIFFICULTY_LABEL[plan.settings.difficulty]}</dd>
            <dt>Length</dt>
            <dd>{plan.settings.duration_minutes} minutes</dd>
            <dt>Planned by</dt>
            <dd>{plan.source === "AI" ? "AI assistance (checked by rules)" : "Fixed rules"}</dd>
          </dl>
          {plan.source === "RULES" && plan.rules_reason && plan.rules_reason !== "NOT_REQUESTED" && (
            <p className="notice">{RULES_REASON_TEXT[plan.rules_reason]}</p>
          )}
          <h3>Topics, in order</h3>
          <ol className="plain-list numbered">
            {plan.topics.map((t) => (
              <li key={t.position}>
                <strong>{t.topic}</strong>
                <br />
                <span className="hint">{topicDescription(t)}</span>
              </li>
            ))}
          </ol>
          <p className="hint">
            The questions are not shown in advance. Each topic can have up to two follow-up
            questions.
          </p>
          <ExportButtons
            what="plan"
            fileName={exportFileName("plan", new Date(), attempt)}
            build={() => planDocument(plan, { candidateName, date: new Date(), attempt })}
          />
          {plan.omitted_groups.length > 0 && (
            <p className="hint">
              Left out: {plan.omitted_groups.map((g) => QUESTION_TYPE_LABEL[g]).join(", ")} (no
              approved details to base it on).
            </p>
          )}
        </>
      )}
      <ConsentControl sessionId={sessionId} />
      <VoiceSetup voice={voice} />
      <CameraPanel camera={camera} intro />
      <p className="hint">{COPY.browserClose}</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      <div className="actions">
        <button type="button" className="primary" onClick={() => run("START_INTERVIEW")} disabled={busy || !plan}>
          {busy ? "Starting…" : camera.state === "off" ? "Start interview without camera" : "Start interview"}
        </button>
      </div>
    </>
  );
}
