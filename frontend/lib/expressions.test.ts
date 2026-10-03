// Run with `npm test` (node --test; Node strips the TypeScript types).
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  EXPRESSIONS,
  addSample,
  cameraErrorText,
  classify,
  emptyCounts,
  liveLabel,
  nextPace,
  toObservation,
} from "./expressions.ts";

test("a sample is one class, no face, or several faces (never analysed)", () => {
  assert.equal(classify([]), "no_face");
  assert.equal(classify([{ expressions: { happy: 0.9 } }, { expressions: { sad: 0.9 } }]), "multiple_faces");
  assert.equal(classify([{ expressions: { neutral: 0.2, happy: 0.7, surprised: 0.1 } }]), "happy");
  assert.equal(classify([{ expressions: {} }]), "neutral");
});

test("only counts are sent, and an unavailable question sends none", () => {
  let c = emptyCounts();
  for (const o of ["neutral", "neutral", "happy", "no_face", "multiple_faces"] as const) c = addSample(c, o);
  assert.deepEqual(toObservation(c, "ANALYZED"), {
    status: "ANALYZED", counts: { neutral: 2, happy: 1 }, no_face: 1, multiple_faces: 1 });
  assert.deepEqual(toObservation(c, "UNAVAILABLE"), { status: "UNAVAILABLE", counts: {}, no_face: 0, multiple_faces: 0 });
  assert.deepEqual(Object.keys(emptyCounts()).sort(), [...EXPRESSIONS, "multiple_faces", "no_face"].sort());
});

test("the live label is a look or a reason, never a number or a feeling", () => {
  assert.equal(liveLabel([]), "Waiting for the first sample…");
  assert.equal(liveLabel(["neutral", "neutral", "happy"]), "Mostly neutral");
  assert.equal(liveLabel(["angry", "disgusted", "neutral"]), "Mostly frowning");
  assert.equal(liveLabel(["happy", "neutral", "sad", "surprised"]), "Mixed");
  assert.equal(liveLabel(["happy", "no_face"]), "No face detected");
  assert.equal(liveLabel(["multiple_faces"]), "More than one face: not analysed");
  for (const l of [liveLabel(["fearful"]), liveLabel(["sad"])]) assert.doesNotMatch(l, /\d|nervous|anxious|confiden/i);
});

test("sampling slows on a slow device and stops when it cannot keep up", () => {
  assert.deepEqual(nextPace(120, 0), { delay: 1000, strikes: 0, stop: false });
  assert.deepEqual(nextPace(600, 0), { delay: 3000, strikes: 0, stop: false });
  assert.deepEqual(nextPace(2000, 1), { delay: 3000, strikes: 2, stop: false });
  assert.equal(nextPace(2000, 2).stop, true);
  assert.equal(nextPace(100, 2).strikes, 0); // one fast sample resets
});

test("camera errors: denied or missing is 'without analysis', anything else 'unavailable'", () => {
  assert.equal(cameraErrorText("NotAllowedError").denied, true);
  assert.match(cameraErrorText("NotAllowedError").text, /^Camera permission was denied/);
  assert.equal(cameraErrorText("NotFoundError").denied, true);
  assert.equal(cameraErrorText("AbortError").denied, false);
  assert.match(cameraErrorText("AbortError").text, /interview will continue normally/);
});
