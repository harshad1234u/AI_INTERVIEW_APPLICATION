"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, type Candidate, getMe } from "@/lib/api";

type Auth = {
  /** undefined while loading; null when nobody is signed in. Never read from browser storage. */
  candidate: Candidate | null | undefined;
  /** Set after login, registration, a profile edit, or (null) logout and deletion. */
  setCandidate: (candidate: Candidate | null) => void;
  error: string | null;
  reload: () => void;
};

const AuthContext = createContext<Auth | null>(null);

/** Asks the server who is signed in (GET /api/auth/me) once, when the app starts. */
export default function AuthProvider({ children }: { children: ReactNode }) {
  const [candidate, setCandidate] = useState<Candidate | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setError(null);
    setCandidate(undefined);
    try {
      setCandidate(await getMe(signal));
    } catch (err) {
      if (signal?.aborted) return;
      if (err instanceof ApiError && err.status === 401) setCandidate(null); // and redirected
      else setError(err instanceof ApiError ? err.message : "Could not check your sign-in.");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- fetch-on-mount
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  return (
    <AuthContext.Provider value={{ candidate, setCandidate, error, reload: () => load() }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): Auth {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside <AuthProvider>");
  return auth;
}

/** Renders children only for a signed-in candidate; otherwise a loading, error or redirect note. */
export function SignedIn({ children }: { children: (candidate: Candidate) => ReactNode }) {
  const { candidate, error, reload } = useAuth();
  if (error) {
    return (
      <section className="card">
        <p className="form-error" role="alert">{error}</p>
        <div className="actions"><button type="button" onClick={reload}>Retry</button></div>
      </section>
    );
  }
  if (candidate === undefined) return <p>Loading…</p>;
  if (candidate === null) return <p>Taking you to the login page…</p>;
  return <>{children(candidate)}</>;
}
