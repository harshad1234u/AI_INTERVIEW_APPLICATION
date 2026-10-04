"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { ApiError, logout } from "@/lib/api";
import { LOGIN_PATH } from "@/lib/auth";

const initials = (name: string) =>
  name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("") || "?";

/** Who is signed in, and the way out. Shown only while someone is signed in. */
export default function AccountBar() {
  const { candidate, setCandidate } = useAuth();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  if (!candidate) return null;

  async function signOut() {
    setBusy(true);
    setError(null);
    try {
      await logout(); // the server deletes the session and clears the cookie
      setCandidate(null);
      router.replace(LOGIN_PATH);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not log out. Please try again.");
      setBusy(false);
    }
  }

  return (
    <div className="account-bar">
      <span className="avatar" aria-hidden="true">{initials(candidate.name)}</span>
      <span className="account-name">Signed in as <strong>{candidate.name}</strong></span>
      <button type="button" onClick={signOut} disabled={busy}>
        {busy ? "Logging out…" : "Log out"}
      </button>
      {error && <span className="form-error" role="alert">{error}</span>}
    </div>
  );
}
