"use client";

import { type FormEvent, useCallback, useEffect, useState } from "react";
import {
  ApiError,
  type Candidate,
  type CandidateInput,
  createCandidate,
  deleteCandidate,
  getCandidate,
  updateCandidate,
} from "@/lib/api";
import ResumeSection from "@/components/ResumeSection";

type Mode = "loading" | "create" | "view" | "edit";
type FieldErrors = Partial<Record<keyof CandidateInput, string>>;

// Remembers which profile this browser created. A convenience only — not authentication.
const STORAGE_KEY = "candidateId";
const NAME_MAX_LENGTH = 200;
const EMPTY: CandidateInput = { name: "", email: "" };

function readStoredId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeId(id: string | null): void {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage unavailable (private mode etc.): the profile just won't be remembered.
  }
}

export default function CandidateProfile() {
  const [mode, setMode] = useState<Mode>("loading");
  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [form, setForm] = useState<CandidateInput>(EMPTY);
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reset = useCallback((message: string | null = null) => {
    storeId(null);
    setCandidate(null);
    setForm(EMPTY);
    setFieldErrors({});
    setError(message);
    setMode("create");
  }, []);

  const load = useCallback(
    async (signal?: AbortSignal) => {
      const id = readStoredId();
      if (!id) return reset();
      setMode("loading");
      setError(null);
      try {
        setCandidate(await getCandidate(id, signal));
        setMode("view");
      } catch (err) {
        if (signal?.aborted) return;
        if (err instanceof ApiError && (err.status === 404 || err.status === 422)) return reset();
        setError(err instanceof ApiError ? err.message : "Could not load your profile.");
      }
    },
    [reset],
  );

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  function showError(err: unknown) {
    if (!(err instanceof ApiError)) {
      setError("Something went wrong. Please try again.");
      return;
    }
    if (err.status === 404) return reset("This profile no longer exists.");
    if (err.status === 409) {
      setFieldErrors({ email: err.message });
      setError("Please fix the highlighted fields.");
      return;
    }
    setFieldErrors(err.fieldErrors as FieldErrors);
    setError(err.message);
  }

  function cancelEdit() {
    setFieldErrors({});
    setError(null);
    setMode("view");
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      let saved: Candidate;
      if (mode === "edit" && candidate) {
        const changes: Partial<CandidateInput> = {};
        if (form.name !== candidate.name) changes.name = form.name;
        if (form.email !== candidate.email) changes.email = form.email;
        if (Object.keys(changes).length === 0) return setMode("view");
        saved = await updateCandidate(candidate.id, changes);
      } else {
        saved = await createCandidate(form);
      }
      storeId(saved.id);
      setCandidate(saved);
      setMode("view");
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!candidate) return;
    const warning =
      "Delete your profile? This permanently removes your name, email and uploaded resume data.";
    if (!window.confirm(warning)) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await deleteCandidate(candidate.id);
      reset();
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) reset();
      else showError(err);
    } finally {
      setBusy(false);
    }
  }

  function startEdit() {
    if (!candidate) return;
    setForm({ name: candidate.name, email: candidate.email });
    setFieldErrors({});
    setError(null);
    setMode("edit");
  }

  const errorBox = error && (
    <p className="form-error" role="alert">
      {error}
    </p>
  );

  return (
    <>
      <section className="card" aria-labelledby="profile-heading">
        <h2 id="profile-heading">Your profile</h2>

        {mode === "loading" && (
          <>
            {errorBox ?? <p>Loading profile…</p>}
            {error && (
              <button type="button" onClick={() => load()}>
                Retry
              </button>
            )}
          </>
        )}

        {mode === "view" && candidate && (
          <>
            <dl>
              <dt>Name</dt>
              <dd>{candidate.name}</dd>
              <dt>Email</dt>
              <dd>{candidate.email}</dd>
              <dt>Created</dt>
              <dd>{new Date(candidate.created_at).toLocaleDateString()}</dd>
            </dl>
            {errorBox}
            <div className="actions">
              <button type="button" onClick={startEdit} disabled={busy}>
                Edit
              </button>
              <button type="button" className="danger" onClick={remove} disabled={busy}>
                {busy ? "Deleting…" : "Delete profile"}
              </button>
            </div>
          </>
        )}

        {(mode === "create" || mode === "edit") && (
          <form onSubmit={submit}>
            {mode === "create" && (
              <p className="hint">
                We store your name and email so you can come back to your practice. You can delete
                them at any time.
              </p>
            )}
            {(["name", "email"] as const).map((field) => (
              <div className="field" key={field}>
                <label htmlFor={field}>{field === "name" ? "Name" : "Email"}</label>
                <input
                  id={field}
                  name={field}
                  type={field === "email" ? "email" : "text"}
                  autoComplete={field}
                  required
                  maxLength={field === "name" ? NAME_MAX_LENGTH : undefined}
                  value={form[field]}
                  onChange={(e) => setForm({ ...form, [field]: e.target.value })}
                  aria-invalid={Boolean(fieldErrors[field])}
                  aria-describedby={fieldErrors[field] ? `${field}-error` : undefined}
                />
                {fieldErrors[field] && (
                  <span id={`${field}-error`} className="field-error">
                    {fieldErrors[field]}
                  </span>
                )}
              </div>
            ))}
            {errorBox}
            <div className="actions">
              <button type="submit" disabled={busy}>
                {busy ? "Saving…" : mode === "create" ? "Create profile" : "Save changes"}
              </button>
              {mode === "edit" && (
                <button type="button" onClick={cancelEdit} disabled={busy}>
                  Cancel
                </button>
              )}
            </div>
          </form>
        )}
      </section>
      {candidate && (mode === "view" || mode === "edit") && (
        <ResumeSection key={candidate.id} candidateId={candidate.id} />
      )}
    </>
  );
}
