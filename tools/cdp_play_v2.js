#!/usr/bin/env node
/* LIE TO ME v2 raw-CDP real-browser verification (smoke-playtest fallback path).
   Boots the game in dedicated headless chromium, plays case 1 through both lock
   outcomes, captures screenshots + console health. NO fun evaluation here. */
"use strict";
const fs = require("fs");
const http = require("http");

const BASE = process.argv[2] || "http://127.0.0.1:8791/index.html";
const OUTDIR = process.argv[3] || "/root/.hermes/kanban/boards/games/workspaces/t_32d7b061";
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
  if (!wsUrl) { console.error("NO WS URL ON PAGE TARGET"); process.exit(1); }
  const ws = new WebSocket(wsUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map(); const errors = []; const logs = []; const proofs = [];
  const send = (method, params = {}) => new Promise(res => {
    const mid = ++id; pending.set(mid, res); ws.send(JSON.stringify({ id: mid, method, params }));
  });
  ws.onmessage = ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result || {}); pending.delete(m.id); return; }
    if (m.method === "Runtime.consoleAPICalled") {
      const line = (m.params.args || []).map(a => a.value !== undefined ? String(a.value) : (a.description || "")).join(" ");
      if (m.params.type === "error") errors.push(line);
      else { logs.push(line); if (line.includes("PROOF")) proofs.push(line); }
    } else if (m.method === "Runtime.exceptionThrown") {
      errors.push("EXC: " + (m.params.exceptionDetails.text || "") + " " +
        ((m.params.exceptionDetails.exception || {}).description || ""));
    }
  };
  await send("Runtime.enable"); await send("Page.enable");

  /* 1. load */
  const t0 = Date.now();
  await send("Page.navigate", { url: BASE });
  await sleep(2500);
  const boot = await send("Runtime.evaluate", { returnByValue: true, expression: `JSON.stringify({
    ready: document.readyState,
    suspects: document.querySelectorAll(".suspect").length,
    claims: document.querySelectorAll(".claim").length,
    records: document.querySelectorAll(".rec").length,
    lockDisabled: document.getElementById("lockbtn").disabled,
    lockLabel: document.getElementById("lockbtn").textContent,
    caseLbl: document.getElementById("caselbl").textContent,
    title: document.title })` });
  const b = JSON.parse(boot.result.value);
  console.log("BOOT:", JSON.stringify(b), `(${((Date.now() - t0) / 1000).toFixed(1)}s)`);

  async function evalJson(expr) {
    const r = await send("Runtime.evaluate", { returnByValue: true, expression: expr });
    return JSON.parse(r.result.value);
  }
  async function clickEl(selector, idx = 0) {
    const r = await send("Runtime.evaluate", { returnByValue: true, expression: `(() => {
      const els = document.querySelectorAll("${selector}"); const el = els[${idx}];
      if (!el) return null; const q = el.getBoundingClientRect();
      return JSON.stringify({ x: q.x + q.width / 2, y: q.y + q.height / 2 }); })()` });
    if (!r.result || !r.result.value) throw new Error("no element for " + selector);
    const { x, y } = JSON.parse(r.result.value);
    for (const type of ["mousePressed", "mouseReleased"])
      await send("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: 1 });
    await sleep(150);
  }
  async function shot(name) {
    const s = await send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${OUTDIR}/${name}.png`, Buffer.from(s.data, "base64"));
    console.log("SHOT:", name);
  }

  /* 2. audio arm (first click anywhere = user gesture) */
  await clickEl("#brief");
  await sleep(800);
  console.log("AUDIO:", await evalJson(`JSON.stringify(LTM_SFX.context ? LTM_SFX.context.state : "null")`),
              "ready=" + await evalJson(`String(LTM_SFX.ready)`));

  /* 3. stamp every claim once -> TRUE (enables LOCK) */
  const nClaims = b.claims;
  for (let i = 0; i < nClaims; i++) { await clickEl(".claim", i); }
  console.log("LOCK AFTER STAMPS:", await evalJson(`JSON.stringify(document.getElementById("lockbtn").textContent)`));

  /* 4. wrong lock first (pick an innocent): silence + thud reveal + re-arm */
  const culprit = await evalJson(`JSON.stringify(CS.culprit)`);
  const innocent = NAMES_ORDER()[0] === culprit ? "Vega" : NAMES_ORDER()[0];
  function NAMES_ORDER() { return ["Marlowe", "Vega", "Ash"]; }
  await clickEl(`input[name="pick"][value="${innocent}"]`);
  await clickEl("#lockbtn");
  await sleep(1200);
  await shot("ltm-wronglock-silence");
  for (let i = 0; i < 12; i++) { await sleep(500);
    const armed = await evalJson(`document.getElementById("lockbtn").style.display !== "none" && document.getElementById("verdict").textContent.length > 10`);
    if (armed) break; }
  await shot("ltm-wronglock-reveal");
  console.log("WRONGLOCK:", await evalJson(`JSON.stringify({
    bad: document.getElementById("chain").classList.contains("bad"),
    rearmed: document.getElementById("lockbtn").textContent,
    locked: locked })`));
  /* un-stamp the FALSE-looking grades? not needed: stamps persist, lock re-arms */

  /* 5. now pick the culprit and lock -> snap chain */
  await clickEl(`#pickrow input[value="${culprit}"]`, 0);
  const selOk = await evalJson(`(document.querySelector('input[name="pick"]:checked')||{}).value`);
  if (selOk !== culprit) { // radio click may have missed; set programmatically as fallback
    await send("Runtime.evaluate", { expression: `document.querySelector('input[name="pick"][value="${culprit}"]').checked=true` });
  }
  await clickEl("#lockbtn");
  await sleep(1600); await shot("ltm-hitstop-lamp");
  let done = false;
  for (let i = 0; i < 30; i++) { await sleep(400);
    done = await evalJson(`document.getElementById("nextcase").style.display !== "none"`); if (done) break; }
  await shot("ltm-correct-chain");
  console.log("CORRECTLOCK:", await evalJson(`JSON.stringify({
    shatter: !!document.querySelector(".suspect.shatter"),
    brokenPortrait: (document.querySelector('.suspect[data-name="${culprit}"] .portrait').style.backgroundImage || "").includes("broken"),
    chainShown: document.getElementById("chain").style.display !== "none",
    verdict: document.getElementById("verdict").textContent,
    typed: document.getElementById("chain").textContent.length })`));

  /* 6. next case boots */
  await clickEl("#nextcase");
  await sleep(700);
  console.log("CASE2:", await evalJson(`document.getElementById("caselbl").textContent + " | claims=" + document.querySelectorAll(".claim").length`));
  await shot("ltm-case2-boot");

  console.log("CONSOLE_ERRORS:", errors.length, errors.slice(0, 3));
  console.log("GEN_PROOFS_CAPTURED:", proofs.length, "->", proofs.slice(0, 2));
  fs.writeFileSync(`${OUTDIR}/cdp-console.log`, [...proofs, ...logs].join("\n") + "\nERRORS:\n" + errors.join("\n"));
  process.exit(errors.length ? 4 : 0);
})().catch(e => { console.error("DRIVER FAIL:", e.message); process.exit(1); });
