import type { Metadata } from "next";
import LoginForm from "@/components/LoginForm";

export const metadata: Metadata = {
  title: "Log in — AI Interview Coach",
  description: "Log in or create an account to practise interviews.",
};

export default function LoginPage() {
  return (
    <main>
      <h1>AI Interview Coach</h1>
      <p className="lead">
        Practice realistic, role-specific interviews and understand exactly how to improve.
      </p>
      <section className="card" aria-labelledby="how-heading">
        <h2 id="how-heading">How it works</h2>
        <ol className="plain-list numbered">
          <li>Add your skills and projects, or upload your resume and approve what we find.</li>
          <li>Plan a text interview for a software developer internship: type, difficulty, length.</li>
          <li>Answer the questions; follow-ups adapt to what you say. Pause whenever you need.</li>
          <li>Get feedback on each answer with quotes from it, then retry the topics to practise.</li>
        </ol>
        <p className="hint">
          Practice only: no hiring decisions, no scores across people. AI assistance is off unless
          you turn it on for an interview; fixed rules run the interview otherwise.
        </p>
      </section>
      <LoginForm />
    </main>
  );
}
