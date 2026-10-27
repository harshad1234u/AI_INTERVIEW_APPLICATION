// Pure logic for the optional voice mode. No React, no microphone, no speech engine: run by
// `node --test`. The browser side is components/interview/useVoice.ts.
//
// Voice is only a way to *enter and hear* text. The interviewer's questions are spoken by the
// browser's own voices; the candidate's speech becomes text in the answer box, where it is
// reviewed and edited before it is sent. The server only ever receives that text.

export const VOICE_LANGUAGES = [
  { code: "en-IN", label: "English (India)" },
  { code: "en-US", label: "English (US)" },
  { code: "en-GB", label: "English (UK)" },
] as const;
export type VoiceLang = (typeof VOICE_LANGUAGES)[number]["code"];
export const DEFAULT_LANG: VoiceLang = "en-IN";

export const isVoiceLang = (value: unknown): value is VoiceLang =>
  VOICE_LANGUAGES.some((l) => l.code === value);

export const RATES = [0.85, 1, 1.15] as const;
export const DEFAULT_RATE = 1;

/** Add recognised text to what is already in the answer box, with one space between. */
export function appendTranscript(base: string, recognised: string): string {
  const add = recognised.replace(/\s+/g, " ").trim();
  if (!add) return base;
  if (!base.trim()) return add;
  return `${base.replace(/\s+$/, "")} ${add}`;
}

/** The question as it is read aloud: markup characters dropped, whitespace collapsed. */
export function cleanForSpeech(text: string): string {
  return text
    .replace(/[`*_#>]/g, "")
    .replace(/https?:\/\/\S+/g, "a link")
    .replace(/\s+/g, " ")
    .trim();
}

/** Chunks of whole sentences, each at most `max` characters (a long sentence is cut at spaces).
 * Some engines stop reading a long utterance part-way, so the reader speaks chunk by chunk. */
export function splitForSpeech(text: string, max = 200): string[] {
  const clean = cleanForSpeech(text);
  if (!clean) return [];
  const sentences = clean.match(/[^.!?]+[.!?]+["')\]]*|[^.!?]+$/g) ?? [clean];
  const chunks: string[] = [];
  let current = "";
  const push = () => {
    if (current.trim()) chunks.push(current.trim());
    current = "";
  };
  for (const raw of sentences) {
    let sentence = raw.trim();
    while (sentence.length > max) {
      let cut = sentence.lastIndexOf(" ", max);
      if (cut <= 0) cut = max;
      push();
      chunks.push(sentence.slice(0, cut).trim());
      sentence = sentence.slice(cut).trim();
    }
    if (current && current.length + 1 + sentence.length > max) push();
    current = current ? `${current} ${sentence}` : sentence;
  }
  push();
  return chunks;
}

export type VoiceInfo = { name: string; lang: string; localService: boolean };

/** The best installed voice: the wanted language first (then other English), and a voice that
 * runs on this device before an online one, so the question text stays on the device. */
export function pickVoice<T extends VoiceInfo>(voices: T[], lang: VoiceLang): T | null {
  const norm = (l: string) => l.replace("_", "-").toLowerCase();
  const want = norm(lang);
  const score = (v: T) => {
    const l = norm(v.lang);
    let s = 0;
    if (l === want) s += 100;
    else if (l.startsWith("en-")) s += 50;
    else if (l.startsWith("en")) s += 40;
    else return -1;
    if (v.localService) s += 20;
    if (/natural|neural/i.test(v.name)) s += 5;
    return s;
  };
  let best: T | null = null;
  let bestScore = -1;
  for (const v of voices) {
    const s = score(v);
    if (s > bestScore) {
      best = v;
      bestScore = s;
    }
  }
  return best;
}

// ---------- speech observations (PRD section 21C): measured, never a judgement ----------

const FILLER_PATTERN = /\b(?:um+|uh+|erm|er|hmm+|you know|i mean)\b/gi;

export type SpeechMetrics = {
  words: number;
  seconds: number;
  /** Words per minute while the microphone was listening; null when too little was said. */
  wordsPerMinute: number | null;
  fillers: number;
  tooShort: boolean;
};

export const MIN_WORDS_FOR_METRICS = 8;
export const MIN_SECONDS_FOR_METRICS = 5;

export function countWords(text: string): number {
  const words = text.trim().match(/\S+/g);
  return words ? words.length : 0;
}

export function speechMetrics(text: string, listenedMs: number): SpeechMetrics {
  const words = countWords(text);
  const seconds = Math.max(0, Math.round(listenedMs / 1000));
  const tooShort = words < MIN_WORDS_FOR_METRICS || seconds < MIN_SECONDS_FOR_METRICS;
  return {
    words,
    seconds,
    wordsPerMinute: tooShort ? null : Math.round((words / listenedMs) * 60000),
    fillers: (text.match(FILLER_PATTERN) ?? []).length,
    tooShort,
  };
}

/** One neutral sentence about what was measured. Never says how the person felt or how well
 * they spoke. */
export function describeSpeech(m: SpeechMetrics): string {
  if (m.seconds === 0) return "";
  if (m.tooShort) return "This response is too short for meaningful speech measurements.";
  const filler = m.fillers === 0 ? "no filler sounds counted"
    : `${m.fillers} filler ${m.fillers === 1 ? "sound" : "sounds"} counted (like um or uh)`;
  return `Measured while speaking: ${m.words} words in ${m.seconds} seconds, about ` +
    `${m.wordsPerMinute} words a minute, ${filler}. This is a measurement of this answer, not a ` +
    `judgement; it stays on this page.`;
}

// ---------- failures, in the candidate's words ----------

/** Why speech input stopped, from the SpeechRecognition error name. `fatal`: do not restart. */
export function recognitionErrorText(code: string): { text: string; fatal: boolean } {
  switch (code) {
    case "not-allowed":
    case "service-not-allowed":
      return { fatal: true, text: "Microphone permission was denied (or speech input is blocked by this browser). Type your answer instead, or allow the microphone in the address bar and try again." };
    case "audio-capture":
      return { fatal: true, text: "No microphone was found. Type your answer instead." };
    case "network":
      return { fatal: true, text: "The browser's speech service could not be reached, so voice input stopped. Check your connection, or type your answer." };
    case "language-not-supported":
      return { fatal: true, text: "This browser cannot recognise speech in the chosen language. Pick another language, or type your answer." };
    case "no-speech":
      return { fatal: false, text: "We didn't hear anything. Check that the right microphone is selected, then try again. This is not a judgement of your answer." };
    default:
      return { fatal: true, text: "Voice input stopped working. You can type your answer instead." };
  }
}

export const VOICE_COPY = {
  title: "Voice mode (optional)",
  intro:
    "The interviewer reads each question aloud, and you can answer by speaking. Your speech is " +
    "turned into text in the answer box, where you can edit it before sending. You can always " +
    "type instead, and the interview works the same without voice.",
  micPrivacy:
    "Speech-to-text is done by your browser's speech service (Google for Chrome, Microsoft for " +
    "Edge): your voice is sent to that service to be turned into text. Audio is not recorded " +
    "and is never sent to this app's server; only the text you choose to send is. Accents and " +
    "mixing languages are not held against you.",
  voicePrivacy:
    "Questions are read by a voice installed on this device where one is available.",
  unsupportedSpeak: "This browser cannot read questions aloud. You can still read and type.",
  unsupportedListen:
    "This browser does not support speech input (try Chrome or Edge). You can still hear " +
    "questions and type your answers.",
} as const;
