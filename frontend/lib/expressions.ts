// Pure logic for the optional camera expression observation. No React, no camera, no model:
// run by `node --test`. The browser side is components/interview/useExpressionCamera.ts.
//
// Only counts ever leave the browser: how many samples of one question fell into each class of
// the face-expression model. Frames are read from the <video> element and never kept.

export const EXPRESSIONS = ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"] as const;
export type Expression = (typeof EXPRESSIONS)[number];

export type Counts = Record<Expression, number> & { no_face: number; multiple_faces: number };
export type Observation = {
  status: "ANALYZED" | "UNAVAILABLE";
  counts: Partial<Record<Expression, number>>;
  no_face: number;
  multiple_faces: number;
};

/** What a class looks like (the backend's wording), never what someone feels. */
export const LOOKS: Record<Expression, string> = {
  neutral: "neutral",
  happy: "smiling",
  surprised: "surprised-looking",
  sad: "downcast-looking",
  angry: "frowning",
  disgusted: "frowning",
  fearful: "tense-looking",
};

export const emptyCounts = (): Counts =>
  ({ ...Object.fromEntries(EXPRESSIONS.map((e) => [e, 0])), no_face: 0, multiple_faces: 0 }) as Counts;

/** One sample: the faces the model found, each with a probability per class. */
export type Detection = { expressions: Partial<Record<string, number>> };

/** The sample's outcome: one class, or why there is none. More than one face is never analysed. */
export function classify(detections: Detection[]): Expression | "no_face" | "multiple_faces" {
  if (detections.length === 0) return "no_face";
  if (detections.length > 1) return "multiple_faces";
  let best: Expression = "neutral";
  for (const e of EXPRESSIONS) {
    if ((detections[0].expressions[e] ?? 0) > (detections[0].expressions[best] ?? 0)) best = e;
  }
  return best;
}

export function addSample(counts: Counts, outcome: ReturnType<typeof classify>): Counts {
  return { ...counts, [outcome]: counts[outcome] + 1 };
}

/** What is sent for one question: counts only. */
export function toObservation(counts: Counts, status: Observation["status"]): Observation {
  if (status === "UNAVAILABLE") return { status, counts: {}, no_face: 0, multiple_faces: 0 };
  const nonzero = Object.fromEntries(EXPRESSIONS.filter((e) => counts[e] > 0).map((e) => [e, counts[e]]));
  return { status, counts: nonzero, no_face: counts.no_face, multiple_faces: counts.multiple_faces };
}

/** A short live label from the latest samples: a look, or why there is none. No numbers. */
export function liveLabel(recent: ReturnType<typeof classify>[]): string {
  if (recent.length === 0) return "Waiting for the first sample…";
  const last = recent[recent.length - 1];
  if (last === "no_face") return "No face detected";
  if (last === "multiple_faces") return "More than one face: not analysed";
  const looks = recent.filter((r) => r !== "no_face" && r !== "multiple_faces")
    .map((r) => LOOKS[r as Expression]);
  const tally = new Map<string, number>();
  looks.forEach((l) => tally.set(l, (tally.get(l) ?? 0) + 1));
  const [top, n] = [...tally.entries()].sort((a, b) => b[1] - a[1] || (a[0] < b[0] ? -1 : 1))[0];
  return n / looks.length >= 0.6 ? `Mostly ${top}` : "Mixed";
}

// Sampling pace: about one sample a second, slower on a slow device, and off when the device
// cannot keep up, so the interview itself never waits for the camera.
export const BASE_INTERVAL_MS = 1000;
export const SLOW_INTERVAL_MS = 3000;
export const SLOW_INFERENCE_MS = 400;
export const TOO_SLOW_INFERENCE_MS = 1500;
export const TOO_SLOW_STRIKES = 3;

export function nextPace(inferenceMs: number, strikes: number): { delay: number; strikes: number; stop: boolean } {
  const s = inferenceMs > TOO_SLOW_INFERENCE_MS ? strikes + 1 : 0;
  return {
    delay: inferenceMs > SLOW_INFERENCE_MS ? SLOW_INTERVAL_MS : BASE_INTERVAL_MS,
    strikes: s,
    stop: s >= TOO_SLOW_STRIKES,
  };
}

/** Why the camera could not start, in the candidate's words (getUserMedia error names). */
export function cameraErrorText(name: string): { text: string; denied: boolean } {
  if (name === "NotAllowedError" || name === "SecurityError") {
    return { denied: true, text: "Camera permission was denied. You can continue the interview without facial-expression analysis." };
  }
  if (name === "NotFoundError" || name === "OverconstrainedError") {
    return { denied: true, text: "No camera was found. You can continue the interview without facial-expression analysis." };
  }
  if (name === "NotReadableError") {
    return { denied: false, text: "The camera is in use by another application. Facial-expression analysis is unavailable; the interview continues normally." };
  }
  return { denied: false, text: "Facial-expression analysis is unavailable. The interview will continue normally." };
}
