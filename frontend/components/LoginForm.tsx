"use client";

import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/components/AuthProvider";
import { ApiError, login, register } from "@/lib/api";
import {
  type AuthFieldErrors,
  type AuthForm,
  type AuthMode,
  PASSWORD_MAX_LENGTH,
  PASSWORD_MIN_LENGTH,
  validateAuthForm,
} from "@/lib/auth";

const EMPTY: AuthForm = { name: "", email: "", password: "" };

export default function LoginForm() {
  const { candidate, setCandidate } = useAuth();
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("login");
  const [form, setForm] = useState<AuthForm>(EMPTY);
  const [fieldErrors, setFieldErrors] = useState<AuthFieldErrors>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Already signed in (or just signed in): the profile page is where to be.
  useEffect(() => {
    if (candidate) router.replace("/");
  }, [candidate, router]);

  function switchMode(next: AuthMode) {
    setMode(next);
    setForm({ ...form, password: "" });
    setFieldErrors({});
    setError(null);
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const errors = validateAuthForm(mode, form);
    setFieldErrors(errors);
    setError(Object.keys(errors).length ? "Please fix the highlighted fields." : null);
    if (Object.keys(errors).length) return;
    setBusy(true);
    try {
      const email = form.email.trim();
      setCandidate(mode === "login"
        ? await login({ email, password: form.password })
        : await register({ name: form.name.trim(), email, password: form.password }));
    } catch (err) {
      setForm((f) => ({ ...f, password: "" }));
      if (!(err instanceof ApiError)) setError("Something went wrong. Please try again.");
      else if (err.status === 409) {
        setFieldErrors({ email: err.message });
        setError("Please fix the highlighted fields.");
      } else {
        // 401: the server's generic "Email or password is incorrect."; 429: locked for a while.
        setFieldErrors(err.fieldErrors as AuthFieldErrors);
        setError(err.message);
      }
    } finally {
      setBusy(false);
    }
  }

  const fields: { key: keyof AuthForm; label: string; type: string; autoComplete: string }[] = [
    ...(mode === "register"
      ? [{ key: "name" as const, label: "Name", type: "text", autoComplete: "name" }]
      : []),
    { key: "email", label: "Email", type: "email", autoComplete: "email" },
    {
      key: "password", label: "Password", type: "password",
      autoComplete: mode === "login" ? "current-password" : "new-password",
    },
  ];

  return (
    <section className="card" aria-labelledby="auth-heading">
      <h2 id="auth-heading">{mode === "login" ? "Log in" : "Create your account"}</h2>
      <form onSubmit={submit} noValidate>
        {mode === "register" && (
          <p className="hint">
            We store your name, email and a securely hashed password so you can come back to your
            practice. You can delete your profile at any time.
          </p>
        )}
        {fields.map(({ key, label, type, autoComplete }) => (
          <div className="field" key={key}>
            <label htmlFor={key}>{label}</label>
            <input
              id={key}
              name={key}
              type={type}
              autoComplete={autoComplete}
              required
              maxLength={key === "password" ? PASSWORD_MAX_LENGTH : key === "name" ? 200 : undefined}
              minLength={key === "password" && mode === "register" ? PASSWORD_MIN_LENGTH : undefined}
              value={form[key]}
              onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              aria-invalid={Boolean(fieldErrors[key])}
              aria-describedby={fieldErrors[key] ? `${key}-error` : undefined}
            />
            {key === "password" && mode === "register" && !fieldErrors.password && (
              <span className="hint">At least {PASSWORD_MIN_LENGTH} characters.</span>
            )}
            {fieldErrors[key] && (
              <span id={`${key}-error`} className="field-error">{fieldErrors[key]}</span>
            )}
          </div>
        ))}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="actions">
          <button type="submit" className="primary" disabled={busy}>
            {busy
              ? mode === "login" ? "Logging in…" : "Creating account…"
              : mode === "login" ? "Log in" : "Create account"}
          </button>
        </div>
      </form>
      <p>
        {mode === "login" ? "New here? " : "Already have an account? "}
        <button type="button" className="link" onClick={() => switchMode(
          mode === "login" ? "register" : "login")} disabled={busy}>
          {mode === "login" ? "Create an account" : "Log in instead"}
        </button>
      </p>
    </section>
  );
}
