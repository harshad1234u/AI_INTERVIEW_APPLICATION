import type { Metadata } from "next";
import Link from "next/link";
import InterviewFlow from "@/components/interview/InterviewFlow";

export const metadata: Metadata = {
  title: "Interview — AI Interview Coach",
  description: "A practice interview you can type or speak: questions, answers, feedback and your report.",
};

export default function InterviewPage() {
  return (
    <main id="content">
      <p>
        <Link href="/" className="back-link">← Your profile</Link>
      </p>
      <h1>Practice interview</h1>
      <p className="lead">
        Practice feedback for learning, based on your answers. It is not an assessment of you.
      </p>
      <InterviewFlow />
    </main>
  );
}
