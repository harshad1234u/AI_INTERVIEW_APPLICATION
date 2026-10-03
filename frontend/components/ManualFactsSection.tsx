"use client";

import { type FormEvent, type MouseEvent, useCallback, useEffect, useState } from "react";
import {
  ApiError,
  type Fact,
  type FactCategory,
  createManualFact,
  deleteManualFact,
  editManualFact,
  listManualFacts,
} from "@/lib/api";
import {
  FACT_CATEGORIES,
  MANUAL_LABEL,
  categoryError,
  factTextError,
} from "@/lib/profile";

const TEXT_INPUT_ID = "manual-fact-text";

function errorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return "Something went wrong. Please try again.";
  return err.fieldErrors.fact ?? err.message; // 409 duplicate or cap: the server's message
}

/** For "Enter your information manually" links: shows the card and puts the cursor in its form.
 * The link's own fragment navigation would take focus away again, so it is done here instead. */
export function focusManualEntry(e: MouseEvent<HTMLAnchorElement>) {
  const input = document.getElementById(TEXT_INPUT_ID);
  if (!input) return; // fall back to the link's #manual-facts
  e.preventDefault();
  document.getElementById("manual-facts")?.scrollIntoView({ block: "start" });
  input.focus({ preventScroll: true });
}

/** The candidate's own skills, projects and so on: approved as soon as they are added. */
export default function ManualFactsSection({ candidateId }: { candidateId: string }) {
  const [facts, setFacts] = useState<Fact[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [category, setCategory] = useState<FactCategory>("SKILL");
  const [text, setText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadError(null);
    try {
      setFacts(await listManualFacts(candidateId, signal));
    } catch (err) {
      if (!signal?.aborted) setLoadError(errorMessage(err));
    }
  }, [candidateId]);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    const invalid = categoryError(category) ?? factTextError(text);
    if (invalid) return setError(invalid);
    setBusy(true);
    setError(null);
    try {
      await createManualFact(candidateId, category, text);
      setText("");
      await load(); // the server's order and normalized text
    } catch (err) {
      setError(errorMessage(err)); // the typed text stays, so nothing is lost
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card" id="manual-facts" aria-labelledby="manual-facts-heading">
      <h2 id="manual-facts-heading">Your skills and projects</h2>
      <p className="hint">
        Add anything your resume doesn&apos;t show, or if it couldn&apos;t be read. What you add
        here counts as confirmed and can be used in your practice interviews.
      </p>
      <form onSubmit={add} className="manual-add" noValidate>
        <div className="field">
          <label htmlFor="manual-fact-category">Category</label>
          <select id="manual-fact-category" value={category} disabled={busy}
                  onChange={(e) => setCategory(e.target.value as FactCategory)}>
            {FACT_CATEGORIES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={TEXT_INPUT_ID}>Skill, project or other detail</label>
          <input id={TEXT_INPUT_ID} value={text} disabled={busy}
                 onChange={(e) => setText(e.target.value)}
                 aria-invalid={Boolean(error)}
                 aria-describedby={error ? "manual-fact-error" : undefined} />
          {error && <span id="manual-fact-error" className="field-error">{error}</span>}
        </div>
        <div className="actions">
          <button type="submit" disabled={busy}>{busy ? "Adding…" : "Add"}</button>
        </div>
      </form>

      {loadError && (
        <p className="form-error" role="alert">
          {loadError}{" "}
          <button type="button" className="link" onClick={() => load()}>Retry</button>
        </p>
      )}
      {facts === null && !loadError && <p>Loading…</p>}
      {facts?.length === 0 && <p className="hint">Nothing added yet.</p>}
      {facts && facts.length > 0 && FACT_CATEGORIES.map(([value, label]) => {
        const items = facts.filter((f) => f.category === value);
        if (items.length === 0) return null;
        return (
          <div key={value} className="fact-group">
            <h3>{label}</h3>
            <ul>
              {items.map((f) => (
                <ManualFactItem
                  key={f.id}
                  fact={f}
                  onSaved={(updated) =>
                    setFacts((prev) => prev?.map((x) => (x.id === updated.id ? updated : x)) ?? null)}
                  onDeleted={() => setFacts((prev) => prev?.filter((x) => x.id !== f.id) ?? null)}
                />
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}

function ManualFactItem({ fact, onSaved, onDeleted }: {
  fact: Fact;
  onSaved: (fact: Fact) => void;
  onDeleted: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(fact.fact);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(e: FormEvent) {
    e.preventDefault();
    const invalid = factTextError(draft);
    if (invalid) return setError(invalid);
    setBusy(true);
    setError(null);
    try {
      onSaved(await editManualFact(fact.id, draft)); // only the text is sent
      setEditing(false);
    } catch (err) {
      setError(errorMessage(err)); // the draft stays in the input
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Delete “${fact.fact}” from your profile?`)) return;
    setBusy(true);
    setError(null);
    try {
      await deleteManualFact(fact.id);
      onDeleted(); // removed only after the server confirms
    } catch (err) {
      // 404: already gone, which is what was asked for.
      if (err instanceof ApiError && err.status === 404) return onDeleted();
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <li className="fact" data-status={fact.status}>
      {editing ? (
        <form className="fact-edit" onSubmit={save} noValidate>
          <label className="visually-hidden" htmlFor={`manual-${fact.id}`}>
            Edit “{fact.fact}”
          </label>
          <input id={`manual-${fact.id}`} value={draft}
                 onChange={(e) => setDraft(e.target.value)} disabled={busy}
                 aria-invalid={Boolean(error)} />
          <div className="actions">
            <button type="submit" disabled={busy}>{busy ? "Saving…" : "Save"}</button>
            <button type="button" disabled={busy} onClick={() => {
              setEditing(false);
              setDraft(fact.fact);
              setError(null);
            }}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <div className="fact-row">
          <span className="fact-value">{fact.fact}</span>
          <span className="badge">{MANUAL_LABEL}</span>
          <div className="actions">
            <button type="button" disabled={busy} aria-label={`Edit ${fact.fact}`}
                    onClick={() => {
                      setDraft(fact.fact);
                      setEditing(true);
                    }}>
              Edit
            </button>
            <button type="button" className="danger" disabled={busy}
                    aria-label={`Delete ${fact.fact}`} onClick={remove}>
              Delete
            </button>
          </div>
        </div>
      )}
      {error && <p className="field-error" role="alert">{error}</p>}
    </li>
  );
}
