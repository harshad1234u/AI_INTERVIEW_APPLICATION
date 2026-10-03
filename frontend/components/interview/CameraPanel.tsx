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
export default function CameraPanel({ camera: { state, message, label, attach, enable, disable },
                                      intro = false }: { camera: Camera; intro?: boolean }) {
  const on = state === "starting" || state === "loading" || state === "active";
  return (
    <section className={`camera${intro ? " camera-intro" : ""}`} aria-labelledby="camera-heading">
      <h3 id="camera-heading">{COPY.cameraTitle}</h3>
      {(intro || !on) && <p className="hint">{COPY.cameraExplain}</p>}
      {on && (
        <video ref={attach} className="camera-preview" muted playsInline autoPlay
               aria-label="Your camera preview (stays on this device)" />
      )}
      <p className="camera-status" role="status" aria-live="polite">
        {STATUS[state]}
        {state === "active" && <> · Expression: <strong>{label}</strong></>}
      </p>
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
    </section>
  );
}
