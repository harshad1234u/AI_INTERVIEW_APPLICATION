// Demo rehearsal: the demo script, end to end, in a real browser, against the REAL backend with
// the AI providers from backend/.env (live calls: roughly ten). A fake webcam shows one face.
//
//   cd backend && DEMO_PASSWORD=... .venv/Scripts/python ../demo/seed_demo.py
//   backend:  .venv/Scripts/python -m app.main         (DATABASE_URL exported)
//   frontend: npm run build && npm run start
//   root:     DEMO_PASSWORD=... node e2e/demo_rehearsal.mjs
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { launchEdge, sleep } from "./cdp.mjs";

const DIR = import.meta.dirname;
const OUT = join(DIR, "out", "rehearsal");
const DOWNLOADS = join(OUT, "downloads");
rmSync(OUT, { recursive: true, force: true });
mkdirSync(DOWNLOADS, { recursive: true });
execFileSync(process.env.E2E_FEED_PYTHON ?? "python", [join(DIR, "camera_feeds.py")]);
const PYTHON = process.env.E2E_PYTHON ?? join(DIR, "..", "backend", ".venv", "Scripts", "python.exe");
const APP = "http://localhost:3000";
const API = "http://localhost:8000/api";
const EMAIL = "ananya.iyer.demo@example.com";
const PASSWORD = process.env.DEMO_PASSWORD;
if (!PASSWORD) throw new Error("Set DEMO_PASSWORD (the one given to demo/seed_demo.py).");
const RESUME = join(DIR, "..", "demo", "resume-ananya-iyer.pdf");
const db = (...a) => execFileSync(PYTHON, [join(DIR, "db.py"), ...a], { encoding: "utf8" }).trim();

const b = await launchEdge({ port: 9224, profile: join(OUT, "profile"), shots: OUT, api: API, args: [
  "--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream",
  `--use-file-for-fake-video-capture=${join(DIR, "out", "face.mjpeg")}`] });
await b.send("Page.setDownloadBehavior", { behavior: "allow", downloadPath: DOWNLOADS });
await b.send("Page.addScriptToEvaluateOnNewDocument", { source: `
  window.__streams = [];
  const original = navigator.mediaDevices?.getUserMedia?.bind(navigator.mediaDevices);
  if (original) navigator.mediaDevices.getUserMedia = async (c) => {
    const s = await original(c); window.__streams.push(s); return s; };` });
const liveTracks = () => b.js("(window.__streams || []).flatMap(s => s.getTracks()).filter(t => t.readyState === 'live').length");

const results = [];
async function step(name, fn) {
  try {
    const detail = await fn();
    results.push({ ok: true, name, detail: detail ?? "" });
    console.log(`PASS  ${name}${detail ? `  — ${detail}` : ""}`);
  } catch (err) {
    results.push({ ok: false, name, detail: err.message });
    console.log(`FAIL  ${name}  — ${err.message}`);
    await b.shot(`FAIL-${results.length}`).catch(() => {});
  }
}
const question = () => b.js("document.querySelector('.question-text')?.textContent ?? null");
const kind = () => b.js("document.querySelector('.question .hint')?.textContent ?? ''");
async function next(previous) {
  await b.waitFor(`Boolean(document.querySelector('.question-text')) && document.querySelector('.question-text').textContent !== ${JSON.stringify(previous)}`, "next question", 60000);
  return question();
}
const answerFor = (q) =>
  `For "${q.slice(0, 60)}", I would start from the requirements, compare two approaches and their ` +
  "trade-offs, then pick the simpler one. In CampusBus Tracker I cached route lookups with " +
  "PostgreSQL indexes and FastAPI, which cut the median response time from 420 ms to 60 ms.";
async function downloaded(prefix) {
  for (let i = 0; i < 100; i++) {
    const f = readdirSync(DOWNLOADS).find((n) => n.startsWith(prefix) && n.endsWith(".html"));
    if (f) return readFileSync(join(DOWNLOADS, f), "utf8");
    await sleep(100);
  }
  throw new Error(`no ${prefix} download`);
}
let q;

try {
  await step("open the app and sign in with the demo account", async () => {
    await b.goto(APP);
    await b.waitPath("/login");
    await b.typeInto("#email", EMAIL);
    await b.typeInto("#password", PASSWORD);
    await b.js("document.querySelector('form').requestSubmit()");
    await b.waitPath("/");
    await b.waitText("Signed in as Ananya Iyer");
  });
  await step("an invalid resume gets a clear message", async () => {
    const fake = join(OUT, "not-a-resume.pdf");
    writeFileSync(fake, "This is a text file with a .pdf name.");
    await b.setFile("#resume-file", fake);
    await b.click("Upload resume");
    await b.waitText("The file is not a valid PDF.");
  });
  await step("upload the demo resume → facts from every section, with provenance", async () => {
    await b.setFile("#resume-file", RESUME);
    await b.click("Upload resume");
    await b.waitText("CampusBus Tracker", 20000);
    await b.waitText("Backend Engineering Intern, Northwind Software");
    await b.waitText("Sections found:");
    return (await b.text()).match(/\d+ need review · \d+ approved · \d+ rejected/)?.[0];
  });
  await step("approve all pending facts", async () => {
    await b.js("[...document.querySelectorAll('button')].find(e => e.textContent.startsWith('Approve all')).click()");
    await b.waitText("0 need review");
  });
  await step("configure the interview with AI consent → plan (live AI)", async () => {
    await b.click("Go to your interviews");
    await b.click("Start a new interview");
    await b.click("Confirm profile");
    await b.waitFor("document.querySelector('#plan-consent') && !document.querySelector('#plan-consent').disabled", "consent");
    await b.typeInto("#plan-mode", "MIXED");
    await b.typeInto("#plan-duration_minutes", "15");
    await b.js("document.querySelector('#plan-consent').click()");
    await b.click("Plan interview");
    await b.waitText("Ready to start", 90000);
    const plannedBy = await b.js("[...document.querySelectorAll('dt')].find(d => d.textContent === 'Planned by').nextElementSibling.textContent");
    const topics = await b.js("[...document.querySelectorAll('ol.numbered li strong')].map(e => e.textContent)");
    await b.shot("01-plan");
    return `${plannedBy}: ${topics.join(" | ")}`;
  });
  await step("export the plan → readable, no ids or prepared questions", async () => {
    await b.click("Download plan");
    const html = await downloaded("interview-plan-");
    if (!html.includes("Topics, in order") || /<script/i.test(html)) throw new Error("bad plan document");
    if (/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-/.test(html)) throw new Error("an id in the plan export");
    return `${Math.round(html.length / 1024)} KB`;
  });
  await step("enable the camera → preview, on-device model, expression status", async () => {
    await b.waitText("Camera: Off");
    await b.click("Enable camera");
    await b.waitText("Expression analysis: Active", 60000);
    await b.waitFor("document.querySelector('.camera-status')?.innerText.includes('Expression: Mostly')", "live expression", 30000);
    await b.shot("02-camera");
    return await b.js("document.querySelector('.camera-status').innerText");
  });
  await step("start → first question (live AI wording where available)", async () => {
    await b.click("Start interview");
    q = await next(null);
    return q;
  });
  await step("phone-sized screen during the interview: camera never covers the question or controls", async () => {
    await b.send("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
    await sleep(500);
    const layout = await b.js(`(() => {
      const r = (s) => document.querySelector(s).getBoundingClientRect();
      const submit = [...document.querySelectorAll('button')].find(e => e.textContent.trim() === 'Submit answer').getBoundingClientRect();
      return { width: document.documentElement.scrollWidth, camTop: r('.camera').top + scrollY,
               lowest: Math.max(r('.question-text').bottom, r('#answer').bottom, submit.bottom, r('.timer').bottom) + scrollY };
    })()`);
    await b.shot("03-mobile-interview");
    await b.send("Emulation.clearDeviceMetricsOverride");
    if (layout.width > 390 || layout.camTop < layout.lowest) throw new Error(JSON.stringify(layout));
    return `no sideways scroll; camera panel starts below the controls (${Math.round(layout.camTop)} > ${Math.round(layout.lowest)})`;
  });
  await step("answer → follow-up", async () => {
    await sleep(15000); // about the time a person spends typing; the camera observes it
    await b.typeInto("#answer", answerFor(q));
    await b.click("Submit answer");
    q = await next(q);
    if (!(await kind()).startsWith("Follow-up question")) throw new Error(await kind());
    return `${q} [${(await b.text()).includes("Worded with AI assistance") ? "AI-worded" : "fixed wording"}]`;
  });
  await step("ask to rephrase → the same question in other words", async () => {
    await b.click("Ask to rephrase");
    q = await next(q);
    if (!(await kind()).startsWith("The question, put another way")) throw new Error(await kind());
    return q;
  });
  await step("network drop while submitting → answer kept → retry", async () => {
    await b.typeInto("#answer", answerFor(q));
    await b.send("Network.emulateNetworkConditions", { offline: true, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await b.click("Submit answer");
    await b.waitText("Your answer is kept on this page but was not saved yet.");
    await b.send("Network.emulateNetworkConditions", { offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1 });
    await b.click("Submit answer");
    q = await next(q);
    return q;
  });
  await step("one more answer, then end the interview", async () => {
    await sleep(15000);
    await b.typeInto("#answer", answerFor(q));
    await b.click("Submit answer");
    q = await next(q);
    await b.click("End interview");
    await b.waitText("Your feedback");
    if (await liveTracks()) throw new Error("the camera is still on after the interview");
    return "camera released when the interview ended";
  });
  await step("live AI evaluation → report with observed expression signals", async () => {
    await b.click("Get my feedback");
    await b.waitText("Your interview report", 180000);
    await b.waitText("Observed expression signals");
    await b.waitText("They are not measurements of emotion, personality, confidence, honesty or suitability");
    const summary = await b.js("[...document.querySelectorAll('dt')].find(d => d.textContent === 'Evaluation').nextElementSibling.textContent");
    const signals = await b.js("[...document.querySelector('#r-expressions').parentElement.querySelectorAll('li')].map(l => l.textContent)");
    await b.shot("04-report");
    if (signals.length < 4) throw new Error(`${signals.length} questions with signals`);
    if (!signals.some((s) => /Mostly|Mixed/.test(s))) throw new Error("no observed signal");
    return `${summary}; ${signals.join(" | ")}`;
  });
  await step("export the report → evaluation, expression signals and disclaimer, no ids", async () => {
    await b.click("Download report");
    const html = await downloaded("interview-report-");
    for (const t of ["Answer evidence", "Observed expression signals", "never used in any score"]) {
      if (!html.includes(t)) throw new Error(`missing ${t}`);
    }
    if (/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-/.test(html) || /<script/i.test(html)) throw new Error("id or script in export");
    return `${Math.round(html.length / 1024)} KB`;
  });
  await step("retry the topics to practise → interview #2; history shows both", async () => {
    await b.click("Retry the topics to practise");
    await b.waitText("Ready to start");
    await b.click("Back to your interviews");
    await b.waitText("Your interview history");
    const items = await b.js("[...document.querySelectorAll('.history-item')].map(li => li.innerText.replace(/\\s+/g, ' '))");
    if (items.length !== 2 || !items[0].includes("retry of interview #1")) throw new Error(JSON.stringify(items));
    return items.join(" | ");
  });
  await step("leaving the interview with the camera on releases it", async () => {
    await b.click("Continue interview #2");
    await b.click("Enable camera");
    await b.waitText("Expression analysis: Active", 60000);
    await b.click("← Your profile");
    await b.waitPath("/");
    await sleep(500);
    if (await liveTracks()) throw new Error("camera still live after leaving");
  });
  await step("camera frames never left the browser", async () => {
    const big = b.requests.filter((r) => r.body.length > 20000 || /data:image|base64/.test(r.body));
    const sent = b.requests.filter((r) => r.method === "PUT" && r.url.endsWith("/expressions"));
    const thirdParty = b.fetched.filter((u) => !u.startsWith(APP) && !u.startsWith(API) && !u.startsWith("data:") && !u.startsWith("blob:") && !u.startsWith("file:") && u !== "about:blank");
    if (big.length || thirdParty.length) throw new Error(JSON.stringify({ big: big.length, thirdParty }));
    return `${sent.length} count-only observations sent; no other host contacted`;
  });
  await step("session expiry → back to the login page", async () => {
    db("expire-sessions", EMAIL);
    await b.click("Go to your interviews");
    await b.waitPath("/login", 15000);
  });
} finally {
  b.close();
  const passed = results.filter((r) => r.ok).length;
  writeFileSync(join(OUT, "results.json"), JSON.stringify({ passed, total: results.length, results }, null, 2));
  console.log(`\n${passed}/${results.length} passed`);
  process.exitCode = passed === results.length ? 0 : 1;
}
