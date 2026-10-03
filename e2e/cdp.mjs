// Headless Microsoft Edge over the Chrome DevTools Protocol, Node built-ins only (Node >= 22).
// Used by demo_rehearsal.mjs; journey.mjs keeps its own copy of the same helpers.
import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { join } from "node:path";

const EDGE = process.env.E2E_EDGE ?? "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function launchEdge({ port, profile, shots, api, args = [] }) {
  const edge = spawn(EDGE, ["--headless=new", `--remote-debugging-port=${port}`, "--disable-gpu",
    "--no-first-run", `--user-data-dir=${profile}`, "--window-size=1280,900", ...args, "about:blank"],
  { stdio: "ignore" });
  let target;
  for (let i = 0; i < 75 && !target; i++) {
    await sleep(200);
    try {
      target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page");
    } catch { /* not up yet */ }
  }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let nextId = 0;
  const pending = new Map();
  const b = { requests: [], fetched: [], consoleLines: [], dialogs: [] };
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const { resolve, reject } = pending.get(m.id);
      pending.delete(m.id);
      m.error ? reject(new Error(m.error.message)) : resolve(m.result);
    } else if (m.method === "Runtime.consoleAPICalled") {
      b.consoleLines.push(m.params.args.map((a) => a.value ?? a.description ?? "").join(" "));
    } else if (m.method === "Runtime.exceptionThrown") {
      b.consoleLines.push(`EXCEPTION ${m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text}`);
    } else if (m.method === "Page.javascriptDialogOpening") {
      b.dialogs.push(m.params.message);
      b.send("Page.handleJavaScriptDialog", { accept: true });
    } else if (m.method === "Network.requestWillBeSent") {
      const r = m.params.request;
      b.fetched.push(r.url);
      if (r.url.startsWith(api)) b.requests.push({ url: r.url, method: r.method, body: r.postData ?? "" });
    }
  });
  b.send = (method, params = {}) => {
    const id = ++nextId;
    ws.send(JSON.stringify({ id, method, params }));
    return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
  };
  b.js = async (expression) => {
    const r = await b.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
    return r.result.value;
  };
  b.waitFor = async (expression, what, timeout = 15000) => {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      if (await b.js(expression).catch(() => false)) return;
      await sleep(150);
    }
    throw new Error(`timed out waiting for ${what}`);
  };
  b.text = () => b.js("document.body.innerText");
  b.waitText = (text, timeout) =>
    b.waitFor(`document.body.innerText.includes(${JSON.stringify(text)})`, `"${text}"`, timeout);
  b.waitPath = (p, timeout) => b.waitFor(`location.pathname === ${JSON.stringify(p)}`, `path ${p}`, timeout);
  const sel = (label) => `[...document.querySelectorAll('button,a')].find(e => (e.textContent.trim() === ${JSON.stringify(label)} || e.getAttribute('aria-label') === ${JSON.stringify(label)}) && !e.disabled)`;
  b.click = async (label, timeout) => {
    await b.waitFor(`Boolean(${sel(label)})`, `enabled "${label}"`, timeout);
    await b.js(`${sel(label)}.click()`);
  };
  b.typeInto = async (selector, value) => {
    await b.waitFor(`Boolean(document.querySelector(${JSON.stringify(selector)}))`, selector);
    await b.js(`(() => { const el = document.querySelector(${JSON.stringify(selector)});
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement : el.tagName === 'SELECT' ? HTMLSelectElement : HTMLInputElement;
      Object.getOwnPropertyDescriptor(proto.prototype, 'value').set.call(el, ${JSON.stringify(value)});
      el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true })); })()`);
  };
  b.goto = async (url) => {
    await b.send("Page.navigate", { url });
    await b.waitFor("document.readyState === 'complete'", `load ${url}`);
  };
  b.shot = async (name) => {
    const { data } = await b.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    writeFileSync(join(shots, `${name}.png`), Buffer.from(data, "base64"));
  };
  b.setFile = async (selector, file) => {
    const { root } = await b.send("DOM.getDocument");
    const { nodeId } = await b.send("DOM.querySelector", { nodeId: root.nodeId, selector });
    await b.send("DOM.setFileInputFiles", { nodeId, files: [file] });
  };
  b.close = () => { ws.close(); edge.kill(); };
  await b.send("Page.enable");
  await b.send("Runtime.enable");
  await b.send("Network.enable");
  return b;
}
