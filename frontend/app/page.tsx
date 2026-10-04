import BackendStatus from "@/components/BackendStatus";
import CandidateProfile from "@/components/CandidateProfile";
import Core3D from "@/components/Core3D";

const STEPS = [
  { n: 1, title: "Build your profile", text: "Type your skills and projects or upload a resume, then approve what we found." },
  { n: 2, title: "Plan an interview", text: "Pick the type, difficulty and length. Optionally turn on AI help." },
  { n: 3, title: "Talk or type", text: "Hear each question and answer by voice, or type. Pause any time." },
  { n: 4, title: "Get clear feedback", text: "Quotes from your answers, what to practise, then retry those topics." },
];

export default function Home() {
  return (
    <main id="content">
      <section className="hero">
        <div className="hero-text">
          <p className="eyebrow">Practice · not a test</p>
          <h1>AI Interview Coach</h1>
          <p className="lead">
            Practice realistic, role-specific interviews and understand exactly how to improve.
          </p>
        </div>
        <Core3D className="core3d-hero" />
        <ol className="journey" aria-label="How it works">
          {STEPS.map((s) => (
            <li key={s.n} data-tilt>
              <span className="journey-n" aria-hidden="true">{s.n}</span>
              <strong>{s.title}</strong>
              <span className="hint">{s.text}</span>
            </li>
          ))}
        </ol>
      </section>
      <BackendStatus />
      <CandidateProfile />
    </main>
  );
}
