import AccountBar from "@/components/AccountBar";
import BackendStatus from "@/components/BackendStatus";
import CandidateProfile from "@/components/CandidateProfile";

export default function Home() {
  return (
    <main>
      <AccountBar />
      <h1>AI Interview Coach</h1>
      <p className="lead">
        Practice realistic, role-specific interviews and understand exactly how to improve.
      </p>
      <BackendStatus />
      <CandidateProfile />
    </main>
  );
}
