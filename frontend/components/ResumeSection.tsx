"use client";

import { type FormEvent, useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  type Fact,
  type FactReview,
  type Resume,
  deleteResume,
  getResumeFacts,
  listResumes,
  reviewFact,
  runAiExtraction,
  uploadResume,
} from "@/lib/api";
import { FACT_CATEGORIES } from "@/lib/profile";
import { focusManualEntry } from "@/components/ManualFactsSection";
const STATUS_LABEL = { PENDING_REVIEW: "Needs review", APPROVED: "Approved", REJECTED: "Rejected" };
const RESUME_STATUS_LABEL = {
  PROCESSED: "Processed",
  FAILED: "Couldn't read",
  UNSUPPORTED: "Not supported",
};

function errorMessage(err: unknown): string {
  return err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
}

export default function ResumeSection({ candidateId }: { candidateId: string }) {
  const [resumes, setResumes] = useState<Resume[] | null>(null);
  const [facts, setFacts] = useState<Record<string, Fact[]>>({});
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const loadFacts = useCallback(async (list: Resume[], signal?: AbortSignal) => {
    const processed = list.filter((r) => r.status === "PROCESSED");
    const results = await Promise.all(processed.map((r) => getResumeFacts(r.id, signal)));
    setFacts((prev) => {
      const next = { ...prev };
      processed.forEach((r, i) => (next[r.id] = results[i]));
      return next;
    });
  }, []);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      setError(null);
      try {
        const list = await listResumes(candidateId, signal);
        await loadFacts(list, signal);
        setResumes(list);
      } catch (err) {
        if (!signal?.aborted) setError(errorMessage(err));
      }
    },
    [candidateId, loadFacts],
  );

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function upload(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const resume = await uploadResume(file);
      await loadFacts([resume]);
      setResumes((prev) => [resume, ...(prev ?? [])]);
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
    } catch (err) {
      // Keep the chosen file so the candidate can retry without picking it again.
      setError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function remove(resume: Resume) {
    const ok = window.confirm(
      "Delete this resume and everything extracted from it, including items you approved?",
    );
    if (!ok) return;
    setError(null);
    try {
      await deleteResume(resume.id);
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) return setError(errorMessage(err));
    }
    setResumes((prev) => prev?.filter((r) => r.id !== resume.id) ?? null);
  }

  function replaceFact(updated: Fact) {
    const resumeId = updated.resume_id; // always set here: these are the resumes' own facts
    if (!resumeId) return;
    setFacts((prev) => ({
      ...prev,
      [resumeId]: prev[resumeId].map((f) => (f.id === updated.id ? updated : f)),
    }));
  }

  return (
    <section className="card" aria-labelledby="resume-heading">
      <h2 id="resume-heading">Resume</h2>
      <p className="hint">
        Upload a text-based PDF (scanned resumes can&apos;t be read yet). We list what we find so you
        can check it: nothing is used for your practice interviews until you approve it. Uploads are
        read with simple text rules on our server; you can optionally ask an AI model to look again,
        which sends the resume text to an external AI provider.
      </p>

      <form onSubmit={upload} className="upload">
        <div className="field">
          <label htmlFor="resume-file">Resume (PDF)</label>
          <input
            id="resume-file"
            ref={fileInput}
            type="file"
            accept="application/pdf,.pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            disabled={uploading}
          />
        </div>
        <div className="actions">
          <button type="submit" disabled={!file || uploading}>
            {uploading ? "Reading resume…" : "Upload resume"}
          </button>
        </div>
      </form>
      <p className="hint" role="status" aria-live="polite">
        {uploading ? "Uploading and reading your resume…" : ""}
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}{" "}
          {resumes === null && (
            <button type="button" className="link" onClick={() => load()}>
              Retry
            </button>
          )}
        </p>
      )}

      {resumes === null && !error && <p>Loading resumes…</p>}
      {resumes?.length === 0 && <p className="hint">No resume uploaded yet.</p>}

      {resumes?.map((resume) => (
        <article key={resume.id} className="resume" aria-label="Uploaded resume">
          <header>
            <strong>{RESUME_STATUS_LABEL[resume.status]}</strong>
            <span className="hint">
              Uploaded {new Date(resume.created_at).toLocaleString()}
              {resume.page_count ? ` · ${resume.page_count} page(s)` : ""}
            </span>
            <button type="button" className="link danger" onClick={() => remove(resume)}>
              Delete
            </button>
          </header>
          {resume.message && <p className="notice">{resume.message}</p>}
          {resume.status !== "PROCESSED" && (
            <p>
              <a href="#manual-facts" onClick={focusManualEntry}>
                Enter your information manually
              </a>
            </p>
          )}
          {resume.status === "PROCESSED" && (
            <AiExtraction resumeId={resume.id} onDone={() => loadFacts([resume])} />
          )}
          {facts[resume.id] && <FactList facts={facts[resume.id]} onChange={replaceFact} />}
        </article>
      ))}
    </section>
  );
}

function AiExtraction({ resumeId, onDone }: { resumeId: string; onDone: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [summary, setSummary] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    // The click is the consent: resume text only leaves our server when the candidate asks.
    const ok = window.confirm(
      "This sends the text of this resume to an external AI provider to look for more skills, " +
        "projects and other items. Anything it suggests still needs your approval. Continue?",
    );
    if (!ok) return;
    setBusy(true);
    setError(null);
    setSummary(null);
    try {
      const r = await runAiExtraction(resumeId);
      await onDone();
      const who = r.fallback_used
        ? `${r.provider} (${r.model}), used because ${r.requested_provider} was unavailable`
        : `${r.provider} (${r.model})`;
      setSummary(
        `AI via ${who}: ${r.facts_added} new item(s) to review, ${r.facts_already_listed} ` +
          `already listed, ${r.facts_rejected} discarded because they didn't match your resume.`,
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-extraction">
      <div className="actions">
        <button type="button" onClick={run} disabled={busy}>
          {busy ? "Asking AI…" : "Find more with AI"}
        </button>
      </div>
      <p className="hint" role="status" aria-live="polite">
        {summary}
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

function FactList({ facts, onChange }: { facts: Fact[]; onChange: (f: Fact) => void }) {
  const counts = { PENDING_REVIEW: 0, APPROVED: 0, REJECTED: 0 };
  facts.forEach((f) => counts[f.status]++);
  if (facts.length === 0) return null;
  return (
    <>
      <p className="hint">
        {counts.PENDING_REVIEW} need review · {counts.APPROVED} approved · {counts.REJECTED}{" "}
        rejected
      </p>
      {FACT_CATEGORIES.map(([category, label]) => {
        const items = facts.filter((f) => f.category === category);
        if (items.length === 0) return null;
        return (
          <div key={category} className="fact-group">
            <h3>{label}</h3>
            <ul>
              {items.map((f) => (
                <FactItem key={f.id} fact={f} onChange={onChange} />
              ))}
            </ul>
          </div>
        );
      })}
    </>
  );
}

function FactItem({ fact, onChange }: { fact: Fact; onChange: (f: Fact) => void }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(fact.fact);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(review: FactReview) {
    if (!fact.resume_id) return; // only resume facts are listed here
    setBusy(true);
    setError(null);
    try {
      onChange(await reviewFact(fact.resume_id, fact.id, review));
      setEditing(false);
    } catch (err) {
      // The draft stays in the input so nothing typed is lost.
      setError(err instanceof ApiError && err.fieldErrors.fact ? err.fieldErrors.fact : errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const edited = fact.fact !== fact.extracted_fact;
  const showSource = fact.category !== "SKILL" && fact.source_text !== fact.extracted_fact;

  return (
    <li className="fact" data-status={fact.status}>
      {editing ? (
        <form
          className="fact-edit"
          onSubmit={(e) => {
            e.preventDefault();
            send({ fact: draft, status: "APPROVED" });
          }}
        >
          <label className="visually-hidden" htmlFor={`fact-${fact.id}`}>
            Edit “{fact.fact}”
          </label>
          <input
            id={`fact-${fact.id}`}
            value={draft}
            maxLength={200}
            required
            onChange={(e) => setDraft(e.target.value)}
            aria-invalid={Boolean(error)}
          />
          <div className="actions">
            <button type="submit" disabled={busy}>
              Save &amp; approve
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setEditing(false);
                setDraft(fact.fact);
                setError(null);
              }}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="fact-row">
          <span className="fact-value">{fact.fact}</span>
          <span className="badge">{STATUS_LABEL[fact.status]}</span>
          <div className="actions">
            {fact.status !== "APPROVED" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => send({ status: "APPROVED" })}
                aria-label={`Approve ${fact.fact}`}
              >
                Approve
              </button>
            )}
            {fact.status !== "REJECTED" && (
              <button
                type="button"
                disabled={busy}
                onClick={() => send({ status: "REJECTED" })}
                aria-label={`Reject ${fact.fact}`}
              >
                Reject
              </button>
            )}
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setDraft(fact.fact);
                setEditing(true);
              }}
              aria-label={`Edit ${fact.fact}`}
            >
              Edit
            </button>
          </div>
        </div>
      )}
      <small className="provenance">
        {fact.extracted_by === "AI" ? "Found by AI in your resume" : "From your resume"} ·{" "}
        {fact.source_section}
        {showSource && <> · “{fact.source_text}”</>}
        {edited && <> · edited by you (resume said “{fact.extracted_fact}”)</>}
      </small>
      {error && (
        <span className="field-error" role="alert">
          {error}
        </span>
      )}
    </li>
  );
}
