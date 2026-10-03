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
      <LoginForm />
    </main>
  );
}
