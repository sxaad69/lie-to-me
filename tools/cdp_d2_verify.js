#!/usr/bin/env node
/* D2/t_cb5ef079 verification: music loop-source leak across cases.
   Instrumentation wraps AudioBufferSourceNode.start (via addScriptToEvaluateOnNewDocument)
   counting LIVE looping sources. Plays 3 full cases, each: double-stamp (spawns
   bass/drums stems) -> WRONG lock (assert live loops hit 0 during the 900ms silence)
   -> re-arm -> CORRECT lock -> close (assert exactly 1 live loop = fresh rain bed)
   -> next case (assert no carry-over). Exits non-zero on any failed assertion. */
"use strict";
const fs = require("fs");
const http = require("http");

const BASE = process.argv[2] || "https://sxaad69.github.io/lie-to-me/";
const OUTDIR = process.argv[3] || ".";
const PORT = process.env.CDP_PORT || "9333";

function jsonGet(path) {
  return new Promise((res, rej) => {
    http.get({ host: "127.0.0.1", port: PORT, path }, r => {
      let d = ""; r.on("data", c => d += c); r.on("end", () => { try { res(JSON.parse(d)); } catch (e) { rej(e); } });
    }).on("error", rej);
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const targets = await jsonGet("/json/list");
  const page = targets.find(t => t.type === "page");
  if (!page) { console.error("NO PAGE TARGET"); process.exit(1); }
  const wsUrl = page.webSocketDebuggerUrl || page.webSocketUrl;
  const ws = new WebSocket(wsUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map(); const errors = []; const logs = [];
  const send = (method, params = {}) => new Promise(res => {
    const mid = ++id; pending.set(mid, res); ws.send(JSON.stringify({ id: mid, method, params }));
  });
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result || {}); pending.delete(m.id); return; }
    if (m.method === "Runtime.consoleAPICalled") {
      const line = (m.params.args || []).map(a => a.value !== undefined ? String(a.value) : (a.description || "")).join(" ");
      if (m.params.type === "error") errors.push(line); else logs.push(line);
    } else if (m.method === "Runtime.exceptionThrown") {
      errors.push("EXC: " + (m.params.exceptionDetails.text || "") + " " +
        ((m.params.exceptionDetails.exception || {}).description || ""));
    }
  };
  await send("Runtime.enable"); await send("Page.enable");

  /* instrument BEFORE any page script runs */
  await send("Page.addScriptToEvaluateOnNewDocument", { source: `
    (() => {
      const live = new Set();
      window.__liveLoops = live;
      window.__loopsStarted = 0;
      const origStart = AudioBufferSourceNode.prototype.start;
      AudioBufferSourceNode.prototype.start = function (...a) {
        if (this.loop) {
          window.__loopsStarted++;
          live.add(this);
          this.addEventListener("ended", () => live.delete(this));
        }
        return origStart.apply(this, a);
      };
    })();` });

  await send("Page.navigate", { url: BASE });
  await sleep(3000);
  async function evalJson(expr) {
    const r = await send("Runtime.evaluate", { returnByValue: true, expression: expr });
    if (r.exceptionDetails) throw new Error("eval: " + (r.exceptionDetails.text || "?"));
    return JSON.parse(r.result.value);
  }
  async function clickEl(selector, idx = 0) {
    const r = await send("Runtime.evaluate", { returnByValue: true, expression: `(() => {
      const els = document.querySelectorAll(${JSON.stringify(selector)}); const el = els[${idx}];
      if (!el) return null; el.scrollIntoView({block:"center"});
      const q = el.getBoundingClientRect();
      return JSON.stringify({ x: q.x + q.width / 2, y: q.y + q.height / 2 }); })()` });
    if (!r.result || !r.result.value) throw new Error("no element for " + selector);
    const { x, y } = JSON.parse(r.result.value);
    for (const type of ["mousePressed", "mouseReleased"])
      await send("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 });
    await sleep(120);
  }
  async function shot(name) {
    const s = await send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${OUTDIR}/${name}.png`, Buffer.from(s.data, "base64"));
  }

  const boot = await evalJson(`JSON.stringify({
    title: document.title,
    secure: isSecureContext,
    caseLbl: document.getElementById("caselbl").textContent })`);
  console.log("BOOT:", JSON.stringify(boot));

  /* arm audio with a real gesture click */
  await clickEl("#brief");
  await sleep(1000);
  const ctxState = await evalJson(`JSON.stringify(LTM_SFX.context ? LTM_SFX.context.state : "null")`);
  console.log("AUDIO:", ctxState);

  const NAMES = ["Marlowe", "Vega", "Ash"];
  const results = { url: BASE, boot, audio: ctxState, cases: [], consoleErrors: [] };
  let failures = [];

  async function liveLoopInfo() {
    return evalJson(`JSON.stringify({ n: window.__liveLoops.size,
      started: window.__loopsStarted,
      kinds: [...window.__liveLoops].map(s => (s.buffer||{}).duration ? (s.buffer.duration>3?"long":"short")+":"+(s.playbackRate?s.playbackRate.value.toFixed(3):"?") : "?") })`);
  }
  async function stampAll(clicksPerClaim) {
    const n = await evalJson(`document.querySelectorAll(".claim").length`);
    for (let p = 0; p < clicksPerClaim; p++)
      for (let i = 0; i < n; i++) await clickEl(".claim", i);
    return n;
  }
  async function ensurePicked(name) {
    await clickEl(`#pickrow input[value="${name}"]`);
    let got = await evalJson(`JSON.stringify((document.querySelector('input[name="pick"]:checked')||{}).value||null)`);
    if (got !== name) {
      await send("Runtime.evaluate", { expression: `document.querySelector('input[name="pick"][value="${name}"]').checked=true` });
      got = await evalJson(`JSON.stringify((document.querySelector('input[name="pick"]:checked')||{}).value||null)`);
    }
    if (got !== name) throw new Error("radio unpickable: " + name);
  }
  async function clickLock(expectedRe) {
    await clickEl("#lockbtn");
    await sleep(500);
    let vw = await evalJson(`JSON.stringify(document.getElementById("verdict").textContent)`);
    if (!vw || !expectedRe.test(vw)) {
      await send("Runtime.evaluate", { expression: `document.getElementById("lockbtn").click()` });
      await sleep(500);
      vw = await evalJson(`JSON.stringify(document.getElementById("verdict").textContent)`);
    }
    return vw;
  }

  for (let caseNum = 1; caseNum <= 3; caseNum++) {
    const entry = { case: caseNum };
    const caseLbl = await evalJson(`JSON.stringify(document.getElementById("caselbl").textContent)`);
    entry.label = caseLbl;

    /* spawn stems: every claim TRUE then FALSE (false stamps raise the music) */
    const nClaims = await stampAll(2);
    entry.claims = nClaims;
    const before = await liveLoopInfo();
    entry.loopsAtLockTime = before.n;
    console.log(`CASE${caseNum} [${caseLbl}] claims=${nClaims} loops before lock:`, JSON.stringify(before));

    /* WRONG lock -> poll the 900ms silence window for the minimum live-loop count */
    const culprit = await evalJson(`JSON.stringify(CS.culprit)`);
    const innocent = NAMES.find(n => n !== culprit);
    await ensurePicked(innocent);
    const vw = await clickLock(/REJECTED/);
    entry.wrongVerdict = vw;
    let minLoops = Infinity;
    for (let i = 0; i < 24; i++) {           /* ~1.2s @ 50ms covers the 900ms window */
      const info = await liveLoopInfo();
      if (info.n < minLoops) { minLoops = info.n; entry.silenceKinds = info.kinds; }
      await sleep(50);
    }
    entry.silenceMinLoops = minLoops;
    console.log(`CASE${caseNum} WRONGLOCK silence min live loops: ${minLoops}`, JSON.stringify(entry.silenceKinds || []));
    if (minLoops !== 0) failures.push(`case${caseNum}: silence never reached 0 loops (min=${minLoops})`);
    await shot(`d2-case${caseNum}-wronglock`);

    await sleep(3200);                        /* thuds + typed tail + re-arm */
    entry.rearmed = await evalJson(`JSON.stringify(document.getElementById("lockbtn").textContent)`);
    entry.revealed = await evalJson(`document.querySelectorAll(".rec.reveal").length`);
    const afterRearm = await liveLoopInfo();  /* rebuilt bed should be back: rain only */
    entry.loopsAfterRearm = afterRearm.n;
    console.log(`CASE${caseNum} after re-arm: loops=${afterRearm.n}`, JSON.stringify(afterRearm.kinds));

    /* CORRECT lock -> snap chain -> close */
    await ensurePicked(culprit);
    const vw2 = await clickLock(/ACCEPTED/);
    entry.correctVerdict = vw2;
    let closed = false;
    for (let i = 0; i < 40; i++) { await sleep(400);
      closed = await evalJson(`document.getElementById("nextcase").style.display !== "none"`); if (closed) break; }
    entry.closed = closed;
    const atClose = await liveLoopInfo();
    entry.loopsAtClose = atClose.n;
    entry.closeKinds = atClose.kinds;
    console.log(`CASE${caseNum} CLOSE: loops=${atClose.n}`, JSON.stringify(atClose.kinds));
    if (atClose.n !== 1) failures.push(`case${caseNum}: ${atClose.n} live loops at close (want 1 = rain only)`);

    results.cases.push(entry);
    if (caseNum < 3) {
      await clickEl("#nextcase");
      await sleep(900);
      const carried = await liveLoopInfo();
      entry.carriedIntoNext = carried.n;
      console.log(`CASE${caseNum}->${caseNum + 1} carry-over loops right after newCase: ${carried.n}`, JSON.stringify(carried.kinds));
    }
  }
  await shot("d2-final");
  results.consoleErrors = errors;
  results.failures = failures;
  results.pass = failures.length === 0 && errors.length === 0;
  console.log("LOOPS_STARTED_TOTAL:", await evalJson(`window.__loopsStarted`));
  console.log("CONSOLE_ERRORS:", errors.length, errors.slice(0, 3));
  console.log(results.pass ? "D2 VERIFY: PASS \u2705" : "D2 VERIFY: FAIL \u274c " + JSON.stringify(failures));
  fs.writeFileSync(`${OUTDIR}/d2-results.json`, JSON.stringify(results, null, 1));
  fs.writeFileSync(`${OUTDIR}/d2-console.log`, logs.join("\n"));
  process.exit(results.pass ? 0 : 4);
})().catch(e => { console.error("DRIVER FAIL:", e.message); process.exit(1); });
