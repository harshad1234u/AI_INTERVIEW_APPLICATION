"use client";

import { type FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { SignedIn, useAuth } from "@/components/AuthProvider";
import ManualFactsSection from "@/components/ManualFactsSection";
import ResumeSection from "@/components/ResumeSection";
import {
  ApiError,
  type Candidate,
  type CandidateInput,
  deleteCandidate,
  updateCandidate,
} from "@/lib/api";
import { LOGIN_PATH } from "@/lib/auth";

type FieldErrors = Partial<Record<keyof CandidateInput, string>>;

const NAME_MAX_LENGTH = 200;

/** The signed-in candidate's profile: who they are comes from the session, never the browser. */
export default function CandidateProfile() {
  return <SignedIn>{(candidate) => <Profile candidate={candidate} />}</SignedIn>;
}

function Profile({ candidate }: { candidate: Candidate }) {
  const { setCandidate } = useAuth();
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<CandidateInput>({ name: "", email: "" });
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function signedOut() {
    setCandidate(null);
    router.replace(LOGIN_PATH);
  }

  function showError(err: unknown) {
    if (!(err instanceof ApiError)) {
      setError("Something went wrong. Please try again.");
      return;
    }
    if (err.status === 404) return signedOut(); // the profile no longer exists
    if (err.status === 409) {
      setFieldErrors({ email: err.message });
      setError("Please fix the highlighted fields.");
      return;
    }
    setFieldErrors(err.fieldErrors as FieldErrors);
    setError(err.message);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const changes: Partial<CandidateInput> = {};
    if (form.name !== candidate.name) changes.name = form.name;
    if (form.email !== candidate.email) changes.email = form.email;
    if (Object.keys(changes).length === 0) return setEditing(false);
    setBusy(true);
    setError(null);
    setFieldErrors({});
    try {
      setCandidate(await updateCandidate(candidate.id, changes));
      setEditing(false);
    } catch (err) {
      showError(err);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    const warning =
      "Delete your profile? This permanently removes your account, your resume data and your " +
      "interviews, and logs you out.";
    if (!window.confirm(warning)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteCandidate(candidate.id); // the server also ends every session of this account
      signedOut();
    } catch (err) {
      showError(err);
      setBusy(false);
    }
  }

  function startEdit() {
    setForm({ name: candidate.name, email: candidate.email });
    setFieldErrors({});
    setError(null);
    setEditing(true);
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

        {!editing && (
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

        {editing && (
          <form onSubmit={submit}>
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
                {busy ? "Saving…" : "Save changes"}
              </button>
              <button type="button" onClick={() => setEditing(false)} disabled={busy}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>
      <ManualFactsSection key={`manual-${candidate.id}`} candidateId={candidate.id} />
      <ResumeSection key={candidate.id} candidateId={candidate.id} />
      <section className="card" aria-labelledby="interview-heading">
        <h2 id="interview-heading">Practice interviews</h2>
        <p className="hint">
          When your details above are ready (added by you, or approved from your resume), plan and
          take a text interview, then see your feedback and your past interviews.
        </p>
        <Link className="button-link" href="/interview">
          Go to your interviews
        </Link>
      </section>
    </>
  );
}
