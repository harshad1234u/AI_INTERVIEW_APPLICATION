// Real-browser end-to-end journey of a new candidate, from registration to retry and history.
// Headless Microsoft Edge over the Chrome DevTools Protocol, Node built-ins only (Node >= 22).
// The UI talks to the real backend and PostgreSQL; only the model gateway is a deterministic fake
// (e2e/server.py), so no AI provider is contacted. See README "Browser end-to-end journey".
//
//   node e2e/journey.mjs        (frontend on :3000, e2e/server.py on :8000, both already running)
import { execFileSync, spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const DIR = import.meta.dirname;
const OUT = join(DIR, "out");
const DOWNLOADS = join(OUT, "downloads");
const SHOTS = join(OUT, "shots");
rmSync(OUT, { recursive: true, force: true });
mkdirSync(DOWNLOADS, { recursive: true });
mkdirSync(SHOTS, { recursive: true });
// A fake webcam showing one face (see e2e/camera_feeds.py; needs Pillow on E2E_FEED_PYTHON).
execFileSync(process.env.E2E_FEED_PYTHON ?? "python", [join(DIR, "camera_feeds.py")]);
const PYTHON = process.env.E2E_PYTHON ?? join(DIR, "..", "backend", ".venv", "Scripts", "python.exe");
const EDGE = process.env.E2E_EDGE ?? "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const APP = "http://localhost:3000";
const API = "http://localhost:8000/api";
const ORIGIN = APP;
const PHRASE = "trade-offs between speed and clarity"; // the fake evaluator quotes it
const ANSWER = `I would start from the requirements and weigh the ${PHRASE} before choosing.`;
const STAMP = Date.now();
const PREFIX = "e2e-journey-";
const A = { name: "Priya E2E", email: `${PREFIX}priya-${STAMP}@example.com`, password: "priya correct horse" };
const B = { name: "Bob E2E", email: `${PREFIX}bob-${STAMP}@example.com`, password: "bob correct horse" };

const results = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const db = (...args) => execFileSync(PYTHON, [join(DIR, "db.py"), ...args], { encoding: "utf8" }).trim();

// ---------- a second, scripted client: Node fetch with its own session cookie ----------
class ApiSession {
  cookie = null;
  async call(path, { method = "GET", body } = {}) {
    const headers = { Origin: ORIGIN };
    if (this.cookie) headers.Cookie = this.cookie;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const res = await fetch(`${API}${path}`, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
    const set = res.headers.get("set-cookie");
    if (set) this.cookie = set.split(";")[0];
    return { status: res.status, headers: res.headers, body: res.status === 204 ? null : await res.json().catch(() => null) };
  }
}

// ---------- browser ----------
const profile = join(OUT, "edge-profile");
const edge = spawn(EDGE, ["--headless=new", "--remote-debugging-port=9223", "--disable-gpu",
  "--no-first-run", `--user-data-dir=${profile}`, "--window-size=1280,900",
  "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
  `--use-file-for-fake-video-capture=${join(OUT, "face.mjpeg")}`, "about:blank"], { stdio: "ignore" });
let target;
for (let i = 0; i < 75 && !target; i++) {
  await sleep(200);
  try {
    target = (await (await fetch("http://127.0.0.1:9223/json/list")).json()).find((t) => t.type === "page");
  } catch { /* not up yet */ }
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let nextId = 0;
const pending = new Map();
const consoleLines = [];
const dialogs = [];
const requests = [];
const fetched = []; // every URL the page loads (to see what the camera feature downloads)
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { resolve, reject } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? reject(new Error(m.error.message)) : resolve(m.result);
  } else if (m.method === "Runtime.consoleAPICalled") {
    consoleLines.push(m.params.args.map((a) => a.value ?? a.description ?? "").join(" "));
  } else if (m.method === "Runtime.exceptionThrown") {
    consoleLines.push(`EXCEPTION ${m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text}`);
  } else if (m.method === "Page.javascriptDialogOpening") {
    dialogs.push(m.params.message);
    send("Page.handleJavaScriptDialog", { accept: true });
  } else if (m.method === "Network.requestWillBeSent" && (fetched.push(m.params.request.url), true)
             && m.params.request.url.startsWith(API)) {
    requests.push({ url: m.params.request.url, method: m.params.request.method, body: m.params.request.postData ?? "" });
  }
});
function send(method, params = {}) {
  const id = ++nextId;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}
async function js(expression) {
  const r = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
  return r.result.value;
}
async function waitFor(expression, what, timeout = 15000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await js(expression).catch(() => false)) return;
    await sleep(100);
  }
  throw new Error(`timed out waiting for ${what}`);
}
const bodyText = () => js("document.body.innerText");
const waitText = (text, timeout) =>
  waitFor(`document.body.innerText.includes(${JSON.stringify(text)})`, `"${text}"`, timeout);
const waitPath = (p, timeout) => waitFor(`location.pathname === ${JSON.stringify(p)}`, `path ${p}`, timeout);
const buttonSel = (label) =>
  `[...document.querySelectorAll('button,a')].find(b => (b.textContent.trim() === ${JSON.stringify(label)} || b.getAttribute('aria-label') === ${JSON.stringify(label)}) && !b.disabled)`;
async function click(label, timeout) {
  await waitFor(`Boolean(${buttonSel(label)})`, `enabled "${label}"`, timeout);
  await js(`${buttonSel(label)}.click()`);
}
async function typeInto(selector, value) {
  await waitFor(`Boolean(document.querySelector(${JSON.stringify(selector)}))`, selector);
  await js(`(() => { const el = document.querySelector(${JSON.stringify(selector)});
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement : el.tagName === 'SELECT' ? HTMLSelectElement : HTMLInputElement;
    Object.getOwnPropertyDescriptor(proto.prototype, 'value').set.call(el, ${JSON.stringify(value)});
    el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); })()`);
}
const value = (selector) => js(`document.querySelector(${JSON.stringify(selector)})?.value`);
async function shot(name) {
  const { data } = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
  writeFileSync(join(SHOTS, `${name}.png`), Buffer.from(data, "base64"));
}
async function goto(url) {
  await send("Page.navigate", { url });
  await waitFor("document.readyState === 'complete'", `load ${url}`);
}
const questionText = () => js("document.querySelector('.question-text')?.textContent ?? null");
const questionKind = () => js("document.querySelector('.question .hint')?.textContent ?? ''");
async function nextQuestion(previous) {
  await waitFor(`(document.querySelector('.question-text')?.textContent ?? null) !== ${JSON.stringify(previous)}
    && Boolean(document.querySelector('.question-text'))`, "the next question", 20000);
  return questionText();
}
async function downloaded(prefix, timeout = 10000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    const file = readdirSync(DOWNLOADS).find((f) => f.startsWith(prefix) && f.endsWith(".html"));
    if (file) return join(DOWNLOADS, file);
    await sleep(100);
  }
  throw new Error(`no download starting with ${prefix}`);
}
/** Opens a downloaded document in the browser, checks it, prints it to PDF and reads the PDF. */
async function verifyDocument(file, expected, forbidden, pdfName) {
  const html = readFileSync(file, "utf8");
  for (const text of forbidden) if (html.includes(text)) throw new Error(`document contains ${text}`);
  if (/<script/i.test(html)) throw new Error("document contains a script tag");
  await goto(`file:///${file.replaceAll("\\", "/")}`);
  const shown = await bodyText();
  for (const text of expected) if (!shown.includes(text)) throw new Error(`opened document lacks "${text}"`);
  const { data } = await send("Page.printToPDF", { printBackground: true });
  const pdf = join(OUT, pdfName);
  writeFileSync(pdf, Buffer.from(data, "base64"));
  const text = execFileSync(PYTHON, ["-c",
    "import sys; from pypdf import PdfReader; r = PdfReader(sys.argv[1]); " +
    "print(len(r.pages)); print(' '.join((p.extract_text() or '') for p in r.pages))", pdf], { encoding: "utf8" });
  const [pages, ...rest] = text.split("\n");
  const flat = rest.join(" ").replace(/\s+/g, " ");
  for (const t of expected) if (!flat.includes(t.replace(/\s+/g, " "))) throw new Error(`PDF lacks "${t}"`);
  return `${Math.round(html.length / 1024)} KB HTML, PDF ${pages} page(s), ${expected.length} checks`;
}

async function check(name, fn) {
  try {
    const detail = await fn();
    results.push({ ok: true, name, detail: detail ?? "" });
    console.log(`PASS  ${name}${detail ? `  — ${detail}` : ""}`);
  } catch (err) {
    results.push({ ok: false, name, detail: err.message });
    console.log(`FAIL  ${name}  — ${err.message}`);
    await shot(`FAIL-${results.length}`).catch(() => {});
  }
}

await send("Page.enable");
await send("Runtime.enable");
await send("Network.enable");
await send("Page.setDownloadBehavior", { behavior: "allow", downloadPath: DOWNLOADS });
// Keep a handle on every camera stream the page opens (to check they are really stopped), and
// let a check choose what the camera does, exactly as a browser reports it: "deny" and
// "nocamera" reject like a refused prompt or a missing device; "blank" (no face) and "faces"
// (three faces) are canvas streams; "real" is Edge's fake webcam with one face.
const FACES = readFileSync(join(OUT, "faces.jpg")).toString("base64");
await send("Page.addScriptToEvaluateOnNewDocument", { source: `
  window.__streams = []; window.__cameraMode = "real";
  const original = navigator.mediaDevices?.getUserMedia?.bind(navigator.mediaDevices);
  if (original) navigator.mediaDevices.getUserMedia = async (c) => {
    const mode = window.__cameraMode;
    if (mode === "deny") throw new DOMException("Permission denied", "NotAllowedError");
    if (mode === "nocamera") throw new DOMException("Requested device not found", "NotFoundError");
    let stream;
    if (mode === "real") stream = await original(c);
    else {
      const canvas = Object.assign(document.createElement("canvas"), { width: 640, height: 480 });
      const ctx = canvas.getContext("2d");
      const draw = (img) => { ctx.fillStyle = "#777"; ctx.fillRect(0, 0, 640, 480); if (img) ctx.drawImage(img, 0, 0, 640, 480); };
      draw(null);
      if (mode === "faces") { const img = new Image(); img.onload = () => draw(img); img.src = "data:image/jpeg;base64,${FACES}"; }
      setInterval(() => ctx.fillRect(0, 0, 1, 1), 200); // keep frames coming
      stream = canvas.captureStream(5);
    }
    window.__streams.push(stream); return stream; };` });
const cameraMode = (mode) => js(`window.__cameraMode = ${JSON.stringify(mode)}`);
const liveTracks = () => js("window.__streams.flatMap(s => s.getTracks()).filter(t => t.readyState === 'live').length");
// Browser-level commands (camera permission) go to the browser target.
const browserWs = new WebSocket((await (await fetch("http://127.0.0.1:9223/json/version")).json()).webSocketDebuggerUrl);
await new Promise((r) => browserWs.addEventListener("open", r, { once: true }));
let browserId = 100000;
function browserSend(method, params) {
  const id = ++browserId;
  browserWs.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => browserWs.addEventListener("message", function on(e) {
    const m = JSON.parse(e.data);
    if (m.id !== id) return;
    browserWs.removeEventListener("message", on);
    m.error ? reject(new Error(m.error.message)) : resolve(m.result);
  }));
}

// Start clean: earlier runs (or other local testing) may have used this network's sign-up quota.
console.log(db("cleanup", PREFIX));
const priya = new ApiSession(); // Priya's second "browser", for checks only
const bob = new ApiSession();
let priyaId, firstSession, retrySession;

try {
  // ---------- 1-3: open, register, log in ----------
  await check("open the app: signed out → /login with 'How it works'", async () => {
    await goto(APP);
    await waitPath("/login");
    await waitText("How it works");
    await shot("01-login");
  });
  await check("register a new candidate → profile page", async () => {
    await click("Create an account");
    await waitText("Create your account");
    await typeInto("#name", A.name);
    await typeInto("#email", A.email);
    await typeInto("#password", A.password);
    await click("Create account");
    await waitPath("/");
    await waitText(`Signed in as ${A.name}`);
    await priya.call("/auth/login", { method: "POST", body: { email: A.email, password: A.password } });
    priyaId = (await priya.call("/auth/me")).body.id;
  });

  // ---------- 4-8: profile, resume, review ----------
  await check("manual profile entry: a skill and a project, 'Added by you'", async () => {
    await typeInto("#manual-fact-category", "SKILL");
    await typeInto("#manual-fact-text", "Kotlin");
    await click("Add");
    await waitFor("document.querySelector('#manual-facts').innerText.includes('Kotlin')", "Kotlin");
    await typeInto("#manual-fact-category", "PROJECT");
    await typeInto("#manual-fact-text", "TrustLens");
    await click("Add");
    await waitFor("document.querySelector('#manual-facts').innerText.includes('TrustLens')", "TrustLens");
  });
  await check("upload a real (Edge-printed) resume → facts to review, sections found", async () => {
    const { root } = await send("DOM.getDocument");
    const { nodeId } = await send("DOM.querySelector", { nodeId: root.nodeId, selector: "#resume-file" });
    await send("DOM.setFileInputFiles", { nodeId, files: [join(DIR, "fixtures", "resume-fresh-graduate.pdf")] });
    await click("Upload resume");
    await waitText("Library Management System", 20000);
    await waitText("Sections found:");
    await waitText("Achievements (kept, no items taken from it)");
    await shot("02-resume-facts");
    const t = await bodyText();
    return t.match(/\d+ need review · \d+ approved · \d+ rejected/)?.[0];
  });
  await check("correct an extraction mistake, reject one item, approve all pending", async () => {
    await click("Edit Library Management System");
    await waitFor("[...document.querySelectorAll('.fact-edit input')].length === 1", "edit box");
    await typeInto(".fact-edit input", "Library Management System (Flask)");
    await click("Save & approve");
    await waitText("edited by you");
    await click("Reject Higher Secondary, Kendriya Vidyalaya, 2021 (92%)");
    await waitFor("document.body.innerText.includes('1 rejected')", "rejected");
    const approveAll = await js("[...document.querySelectorAll('button')].find(b => b.textContent.startsWith('Approve all'))?.textContent");
    if (!approveAll) throw new Error("no 'Approve all' button");
    await js("[...document.querySelectorAll('button')].find(b => b.textContent.startsWith('Approve all')).click()");
    await waitText("0 need review");
    if (!dialogs.at(-1)?.startsWith("Approve all")) throw new Error(`dialog: ${dialogs.at(-1)}`);
    return `${approveAll}; ${(await bodyText()).match(/0 need review · \d+ approved · 1 rejected/)?.[0]}`;
  });
  await check("AI extraction (opt-in click): grounded item added, invented one discarded", async () => {
    await click("Find more with AI");
    await waitText("1 discarded because they didn't match your resume", 20000);
    await waitText("Finalist, Smart India Hackathon 2024");
    await click("Approve Finalist, Smart India Hackathon 2024");
    await waitText("0 need review");
    return (await bodyText()).match(/AI via [^\n]+/)?.[0];
  });

  // ---------- 9-13: configure, consent, plan, inspect, export ----------
  await check("start an interview → confirm profile (manual + approved resume facts)", async () => {
    await click("Go to your interviews");
    await waitPath("/interview");
    await click("Start a new interview");
    await waitText("Confirm your profile");
    await waitText("TrustLens");
    await click("Confirm profile");
    await waitText("Plan your interview");
  });
  await check("configure the interview and give AI consent → plan with an honest fallback note", async () => {
    await waitFor("!document.querySelector('#plan-consent').disabled", "consent loaded");
    await typeInto("#plan-mode", "MIXED");
    await typeInto("#plan-difficulty", "MEDIUM");
    await typeInto("#plan-duration_minutes", "15");
    await js("document.querySelector('#plan-consent').click()");
    firstSession = (await priya.call(`/candidates/${priyaId}/interview-sessions`)).body[0].id;
    await click("Plan interview");
    await waitText("Ready to start", 20000);
    // The fake's planning output fails the schema: the gateway counts that as the provider failing.
    await waitText("The AI service could not be used just now, so fixed rules were used.");
    await waitText("based on your project");
    await shot("03-plan");
    return `${await js("document.querySelectorAll('ol.numbered li').length")} topics`;
  });
  await check("download the plan → readable document → prints to PDF", async () => {
    await click("Download plan");
    const file = await downloaded("interview-plan-1-");
    const plan = (await priya.call(`/interview-sessions/${firstSession}/plan`)).body.plan;
    const detail = await verifyDocument(file,
      ["Interview plan #1", A.name, "Software Developer Intern", "15 minutes", plan.topics[0].topic,
       "Topics, in order"],
      [firstSession, plan.topics[0].question_templates[0], "question_templates", priyaId], "plan.pdf");
    await goto(`${APP}/interview`);
    await click("Resume");
    await waitText("Ready to start");
    await click("Print or save as PDF");
    await waitFor("[...document.querySelectorAll('iframe')].some(f => f.srcdoc.includes('Interview plan #1'))", "print frame");
    return detail;
  });

  // ---------- camera: optional, local, lazy ----------
  await check("camera is optional and off: explained, nothing loaded until enabled", async () => {
    await waitText("Facial-expression observation (optional, experimental)");
    await waitText("images and video never leave your browser");
    await waitText("Camera: Off");
    await waitText("Start interview without camera");
    if (fetched.some((u) => u.includes("/models/face-api"))) throw new Error("model loaded before consent");
    if (await liveTracks()) throw new Error("camera open before consent");
  });
  await check("enable the camera → preview, local model, live expression", async () => {
    await click("Enable camera");
    await waitText("Expression analysis: Active", 60000);
    await waitFor("document.querySelector('.camera-status')?.innerText.includes('Expression: Mostly')", "a live expression", 30000);
    const models = fetched.filter((u) => u.includes("/models/face-api")).map((u) => u.split("/").pop());
    const apiCalls = requests.filter((r) => r.url.includes("expression")).length;
    await shot("08-camera-ready");
    return `${await js("document.querySelector('.camera-status').innerText")}; loaded ${models.join(", ")}; ${apiCalls} API calls`;
  });

  // ---------- 14-19: the interview ----------
  let q;
  await check("start the interview → first question and the server's timer", async () => {
    await click("Start interview");
    q = await nextQuestion(null);
    await waitText("Time left:");
    return q;
  });
  await check("answer → adaptive follow-up (fixed wording, the reason shown)", async () => {
    await sleep(8000); // let the camera sample this question
    await typeInto("#answer", ANSWER);
    await click("Submit answer");
    q = await nextQuestion(q);
    if (!(await questionKind()).startsWith("Follow-up question")) throw new Error(await questionKind());
    await waitText("The AI service could not be used just now");
    return q;
  });
  await check("ask to rephrase → the question put another way", async () => {
    await click("Ask to rephrase");
    q = await nextQuestion(q);
    if (!(await questionKind()).startsWith("The question, put another way")) throw new Error(await questionKind());
    return q;
  });
  await check("pause with a draft → clock stopped, draft kept → resume", async () => {
    await typeInto("#answer", "half-written draft");
    await click("Pause");
    await waitText("Interview paused");
    await waitText("Your unsent answer is kept on this page");
    await click("Resume");
    await nextQuestion(null);
    if ((await value("#answer")) !== "half-written draft") throw new Error("draft lost");
  });
  await check("submit, then 'I don't know' and 'Skip'", async () => {
    await typeInto("#answer", ANSWER);
    await click("Submit answer");
    q = await nextQuestion(q);
    await click("I don't know");
    q = await nextQuestion(q);
    await click("Skip");
    q = await nextQuestion(q);
    return q;
  });
  await check("camera sends counts only, per answered question", async () => {
    const sent = requests.filter((r) => r.method === "PUT" && r.url.endsWith("/expressions"));
    if (!sent.length) throw new Error("no observation sent");
    for (const r of sent) {
      const body = JSON.parse(r.body);
      const keys = Object.keys(body).sort().join(",");
      if (keys !== "counts,multiple_faces,no_face,status") throw new Error(keys);
      if (Object.values(body.counts).some((n) => !Number.isInteger(n))) throw new Error(r.body);
    }
    return `${sent.length} observations, e.g. ${sent[0].body}`;
  });
  await check("disable the camera mid-interview → camera released, interview continues", async () => {
    await shot("09-camera-in-interview");
    await click("Disable camera");
    await waitText("Camera: Off");
    if (await liveTracks()) throw new Error("a camera track is still live");
    await waitFor("Boolean(document.querySelector('.question-text'))", "question still there");
    return "0 live camera tracks";
  });
  await check("refresh mid-interview → offered Resume → the same open question", async () => {
    await send("Page.reload");
    await waitText("You have an unfinished interview.");
    await click("Resume");
    const again = await nextQuestion(null);
    if (again !== q) throw new Error(`${again} != ${q}`);
  });
  await check("network failure while submitting → answer kept → retry succeeds", async () => {
    await typeInto("#answer", ANSWER);
    await send("Network.emulateNetworkConditions", { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await click("Submit answer");
    await waitText("Your answer is kept on this page but was not saved yet.");
    if ((await value("#answer")) !== ANSWER) throw new Error("answer lost");
    await send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await click("Submit answer");
    q = await nextQuestion(q);
    return q;
  });
  await check("deadline passes while answering → late answer refused, kept on screen → feedback", async () => {
    db("deadline", firstSession, "-5");
    await typeInto("#answer", "an answer typed after time ran out");
    await click("Submit answer");
    await waitText("Continue");
    if ((await value("#answer")) !== "an answer typed after time ran out") throw new Error("draft lost");
    const shown = await bodyText();
    await click("Continue");
    await waitText("Your feedback");
    await waitText("The time limit was reached.");
    return shown.match(/[^\n]*(time|late)[^\n]*/i)?.[0];
  });

  // ---------- 20-24: evaluation, report, export ----------
  await check("evaluate each answer (consent on) → report", async () => {
    await click("Get my feedback");
    await waitText("Your interview report (interview #1)", 30000);
    await waitText("Observed expression signals");
    await waitText("They are not measurements of emotion, personality, confidence, honesty or suitability");
    await waitFor("/Question #1: (Mostly|Mixed)/.test(document.body.innerText)", "question 1's signal");
    for (const s of ["Summary", "Shown clearly", "To practise", "Answer evidence", "Topics to practise",
                     "Recommended practice", "never combined"]) await waitText(s);
    await shot("04-report");
    const report = (await priya.call(`/interview-sessions/${firstSession}/report`)).body.report;
    return `${report.summary.evaluations.evaluated} evaluated with AI; ${report.topics_to_practise.length} topics to practise`;
  });
  await check("download the report → readable document → prints to PDF", async () => {
    await click("Download report");
    const file = await downloaded("interview-report-1-");
    const detail = await verifyDocument(file,
      ["Interview report #1", "Summary", "Answer evidence", PHRASE, "Recommended practice",
       "Observed expression signals"],
      [firstSession, priyaId, "e2e-fake", "request_id"], "report.pdf");
    await goto(`${APP}/interview`);
    return detail;
  });

  // ---------- 25-27: retry and history ----------
  await check("retry the topics to practise → interview #2 is planned", async () => {
    await click("View report");
    await waitText("Your interview report (interview #1)");
    await click("Retry the topics to practise");
    await waitText("Ready to start");
    const sessions = (await priya.call(`/candidates/${priyaId}/interview-sessions`)).body;
    retrySession = sessions.find((s) => s.retry_of_id === firstSession)?.id;
    if (!retrySession) throw new Error(JSON.stringify(sessions));
  });
  await check("camera permission denied → clear message, camera stays off", async () => {
    await cameraMode("deny");
    await click("Enable camera");
    await waitText("Camera permission was denied. You can continue the interview without facial-expression analysis.");
    await waitText("Camera: Off");
    if (await liveTracks()) throw new Error("a camera track is live");
  });
  await check("no camera on the device → clear message", async () => {
    await cameraMode("nocamera");
    await click("Enable camera");
    await waitText("No camera was found. You can continue the interview without facial-expression analysis.");
  });
  await check("expression model cannot load → 'unavailable', camera released", async () => {
    await cameraMode("real");
    await send("Network.setCacheDisabled", { cacheDisabled: true });
    await send("Network.setBlockedURLs", { urls: ["*models/face-api*"] });
    await click("Enable camera");
    await waitText("Facial-expression analysis is unavailable (the model could not be loaded). The interview will continue normally.", 30000);
    await waitText("Expression analysis: Unavailable");
    if (await liveTracks()) throw new Error("a camera track is still live");
    await send("Network.setBlockedURLs", { urls: [] });
  });
  await check("several faces → not analysed", async () => {
    await cameraMode("faces");
    await click("Try the camera again");
    await waitFor("document.querySelector('.camera-status')?.innerText.includes('More than one face: not analysed')", "multiple faces", 60000);
    await click("Disable camera");
  });
  await check("no face in view → 'No face detected'; the interview runs normally", async () => {
    await cameraMode("blank");
    await click("Enable camera");
    await waitFor("document.querySelector('.camera-status')?.innerText.includes('No face detected')", "no face", 60000);
    await shot("10-camera-no-face");
  });
  await check("complete the retry (end early) → its own report, labelled as a retry", async () => {
    await click("Start interview");
    q = await nextQuestion(null);
    await sleep(8000); // the camera samples an empty view
    await typeInto("#answer", ANSWER);
    await click("Submit answer");
    await nextQuestion(q);
    await click("End interview");
    await waitText("Your feedback");
    await click("Turn on AI assistance");
    await waitText("AI assistance is on for this interview.");
    await click("Get my feedback");
    await waitText("Your interview report (interview #2)", 30000);
    await waitText("A retry of interview #1.");
    await waitText("Question #1: Insufficient visual data (the face was rarely visible).");
    await waitText("You ended the interview early, so this report is partial.");
  });
  await check("history lists both attempts separately", async () => {
    await click("Back to your interviews");
    await waitText("Your interview history");
    const items = await js("[...document.querySelectorAll('.history-item')].map(li => li.innerText.replace(/\\s+/g, ' '))");
    if (items.length !== 2 || !items[0].includes("Interview #2") || !items[0].includes("retry of interview #1")
        || !items[1].includes("Interview #1") || !items.every((i) => i.includes("Completed"))) {
      throw new Error(JSON.stringify(items));
    }
    await shot("05-history");
    await click("View the report of interview #1");
    await waitText("Your interview report (interview #1)");
    return items.join(" | ");
  });

  // ---------- 28-30: logout, login, persistence ----------
  await check("log out → log in again → the history is still there", async () => {
    await click("Log out");
    await waitPath("/login");
    if ((await priya.call("/auth/me")).status !== 200) throw new Error("other browser was logged out");
    await click("Log in instead").catch(() => {});
    await waitText("Log in");
    await typeInto("#email", A.email);
    await typeInto("#password", A.password);
    await js("document.querySelector('form').requestSubmit()");
    await waitPath("/");
    await goto(`${APP}/interview`);
    await waitText("Your interview history");
    const n = await js("document.querySelectorAll('.history-item').length");
    if (n !== 2) throw new Error(`${n} items`);
  });

  // ---------- security and quality ----------
  await check("another candidate gets 404 for every one of Priya's resources", async () => {
    const registered = await bob.call("/auth/register", { method: "POST", body: B });
    if (registered.status !== 201) throw new Error(`Bob's registration: ${registered.status}`);
    const probes = await Promise.all([
      bob.call(`/candidates/${priyaId}/interview-sessions`),
      bob.call(`/interview-sessions/${firstSession}/report`),
      bob.call(`/interview-sessions/${firstSession}/plan`),
      bob.call(`/interview-sessions/${retrySession}`, { method: "DELETE" }),
      bob.call(`/candidates/${priyaId}/manual-facts`),
    ]);
    if (probes.some((p) => p.status !== 404)) throw new Error(probes.map((p) => p.status).join(","));
    return "5 probes → 404";
  });
  await check("phone-sized screen: no sideways scrolling on the interview, report and profile", async () => {
    await send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
    const widths = [];
    for (const [url, text] of [[`${APP}/interview`, "Your interview history"], [`${APP}/`, "Your skills and projects"]]) {
      await goto(url);
      await waitText(text);
      widths.push(await js("document.documentElement.scrollWidth"));
      await shot(`06-mobile-${widths.length}`);
    }
    await click("Go to your interviews");
    await click("View the report of interview #1");
    await waitText("Your interview report (interview #1)");
    widths.push(await js("document.documentElement.scrollWidth"));
    await shot("06-mobile-report");
    await send("Emulation.clearDeviceMetricsOverride");
    if (widths.some((w) => w > 390)) throw new Error(`scroll widths ${widths}`);
    return `scroll widths ${widths.join(", ")} (viewport 390)`;
  });
  await check("keyboard: the screen heading takes focus when the screen changes", async () => {
    const focused = await js("document.activeElement?.matches('[data-screen-heading]') ? document.activeElement.textContent : null");
    if (!focused) throw new Error("focus not on the heading");
    return focused;
  });
  await check("sign-in flood from one network → the UI shows the throttle message", async () => {
    await click("Log out");
    await waitPath("/login");
    const stranger = new ApiSession();
    let status = 0;
    for (let i = 0; i < 25 && status !== 429; i++) {
      status = (await stranger.call("/auth/login", { method: "POST", body: { email: `${PREFIX}nobody@example.com`, password: "wrong password" } })).status;
    }
    await click("Log in instead").catch(() => {});
    await typeInto("#email", A.email);
    await typeInto("#password", A.password); // even the right password waits
    await js("document.querySelector('form').requestSubmit()");
    await waitText("Too many sign-in attempts from your network.");
    await shot("07-throttled");
    db("cleanup", "e2e-unused-prefix"); // reset the counters so later runs can sign in
  });
  await check("no identity in browser storage, no candidate_id sent, no page errors", async () => {
    const dump = await js("JSON.stringify({local: {...localStorage}, session: {...sessionStorage}})");
    if (dump !== '{"local":{},"session":{}}') throw new Error(dump);
    if (requests.some((r) => r.body.includes("candidate_id"))) throw new Error("candidate_id in a body");
    const bad = consoleLines.filter((l) => l.startsWith("EXCEPTION") || l.includes(A.password));
    if (bad.length) throw new Error(JSON.stringify(bad));
    return `${requests.length} API requests`;
  });
} finally {
  ws.close();
  browserWs.close();
  edge.kill();
  const cleanup = (() => { try { return db("cleanup", PREFIX); } catch (e) { return e.message; } })();
  const passed = results.filter((r) => r.ok).length;
  writeFileSync(join(OUT, "results.json"), JSON.stringify({ passed, total: results.length, results, dialogs }, null, 2));
  console.log(`\n${passed}/${results.length} passed. ${cleanup}`);
  if (existsSync(profile)) rmSync(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 300 });
  process.exitCode = passed === results.length ? 0 : 1;
}
