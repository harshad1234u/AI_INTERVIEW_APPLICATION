"use client";

import type { Camera } from "@/components/interview/useExpressionCamera";
import { COPY } from "@/lib/interview";

const STATUS: Record<Camera["state"], string> = {
  off: "Camera: Off",
  starting: "Camera: asking for permission…",
  loading: "Camera: On · loading the expression model…",
  active: "Camera: On · Expression analysis: Active",
  unavailable: "Camera: Off · Expression analysis: Unavailable",
};

/** The optional camera. `intro` shows the full explanation (before the interview starts). */
export default function CameraPanel({ camera: { state, message, label, breakdown, attach, enable, disable },
                                      intro = false }: { camera: Camera; intro?: boolean }) {
  const on = state === "starting" || state === "loading" || state === "active";
  return (
    <section className={`camera${intro ? " camera-intro" : ""}${on ? " camera-on" : ""}`}
             aria-labelledby="camera-heading">
      <h3 id="camera-heading">{COPY.cameraTitle}</h3>
      {(intro || !on) && <p className="hint">{COPY.cameraExplain}</p>}
      <div className="camera-row">
        {on && (
          <div className="camera-frame" data-live={state === "active"}>
            <video ref={attach} className="camera-preview" muted playsInline autoPlay
                   aria-label="Your camera preview (stays on this device)" />
            {state === "active" && <span className="camera-live">● Live</span>}
          </div>
        )}
        <div className="camera-info">
          <p className="camera-status" role="status" aria-live="polite">
            {STATUS[state]}
            {state === "active" && <> · Expression: <strong>{label}</strong></>}
          </p>
          {state === "active" && breakdown.length > 0 && (
            <ul className="look-bars" aria-label="What the last few samples looked like">
              {breakdown.map(({ look, percent }) => (
                <li key={look}>
                  <span className="look-name">{look}</span>
                  <span className="look-track" aria-hidden="true">
                    <span className="look-fill" style={{ width: `${percent}%` }} />
                  </span>
                  <span className="look-pct">{percent}%</span>
                </li>
              ))}
            </ul>
          )}
          {message && <p className="notice">{message}</p>}
          <div className="actions">
            {on ? (
              <button type="button" onClick={disable}>Disable camera</button>
            ) : (
              <button type="button" onClick={() => enable()}>
                {state === "unavailable" ? "Try the camera again" : "Enable camera"}
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
