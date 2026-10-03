import type { Metadata } from "next";
import Link from "next/link";
import AccountBar from "@/components/AccountBar";
import InterviewFlow from "@/components/interview/InterviewFlow";

export const metadata: Metadata = {
  title: "Interview — AI Interview Coach",
  description: "A text practice interview: questions, answers, feedback and your report.",
};

export default function InterviewPage() {
  return (
    <main>
      <AccountBar />
      <p>
        <Link href="/">← Your profile</Link>
      </p>
      <h1>Practice interview</h1>
      <p className="lead">
        Practice feedback for learning, based on your answers. It is not an assessment of you.
      </p>
      <InterviewFlow />
    </main>
  );
}
