#!/usr/bin/env node
/* LIE TO ME v2 proof harness — extracts generator+prover from src/v2.template.html
   and machine-verifies: unique culprit, no innocent convictable, claim-truth
   coherence, full template coverage. Spec: proofs or the case doesn't ship. */
"use strict";
const fs = require("fs");
const html = fs.readFileSync("/root/lie-to-me/src/v2.template.html", "utf8");
const start = html.indexOf("function mulberry32");
const end = html.indexOf("const LTM_SFX");
if (start < 0 || end < 0) { console.error("EXTRACT FAIL"); process.exit(1); }
const core = html.slice(start, end);
const mod = new Function(core + `
  return {generateCase, proveCase, NAMES};`)();
const {generateCase, proveCase, NAMES} = mod;

let failures = 0;
const tplSeen = new Set();
const N = 2000;
for (let seed = 1; seed <= N; seed++) {
  for (const caseNum of [1, 2, 3]) {
  const cs = generateCase(seed, caseNum);
  tplSeen.add(cs.tpl);
  const p = proveCase(cs);
  if (!p.uniqueCulprit.holds) { failures++; console.log(`seed ${seed} case${caseNum} T${cs.tpl}: unique-culprit FAIL ${p.uniqueCulprit.detail}`); }
  if (!p.noInnocentConvicts.holds) { failures++; console.log(`seed ${seed} case${caseNum} T${cs.tpl}: no-innocent-convicts FAIL ${p.noInnocentConvicts.violations}`); }
  // claim truth coherence
  for (const c of cs.claims) {
    if (!["TRUE","FALSE","UNPROVEN"].includes(c.truth)) { failures++; console.log(`seed ${seed}: bad truth ${c.id}`); }
  }
  const culClaims = cs.claims.filter(c => c.who === cs.culprit);
  if (culClaims.some(c => c.truth !== "FALSE")) { failures++; console.log(`seed ${seed}: culprit has non-FALSE claim`); }
  const ids = new Set(cs.claims.map(c => c.id));
  if (ids.size !== cs.claims.length) { failures++; console.log(`seed ${seed}: duplicate claim ids`); }
  // ladder discipline: case number must draw from its own pool
  const lo = [1,5,9][caseNum-1], hi = [4,8,12][caseNum-1];
  if (cs.tpl < lo || cs.tpl > hi) { failures++; console.log(`seed ${seed} case${caseNum}: template ${cs.tpl} outside pool ${lo}-${hi}`); }
  }
}
// red-herring structure: templates 9-12 carry exactly one herring, never in excl
for (let seed = 1; seed <= N; seed++) {
  for (const caseNum of [2,3]) {
  const cs = generateCase(seed, caseNum);
  if (cs.tpl >= 9) {
    if (!cs.herring) { failures++; console.log(`seed ${seed} T${cs.tpl}: missing herring`); continue; }
    if (cs.excl[cs.herring.implicates].includes(cs.herring.record)) {
      failures++; console.log(`seed ${seed} T${cs.tpl}: herring entered exclusion math`);
    }
    if (cs.records.length !== 5) { failures++; console.log(`seed ${seed} T${cs.tpl}: expected 5 records`); }
  } else if (cs.records.length !== 4) {
    failures++; console.log(`seed ${seed} T${cs.tpl}: expected 4 records`);
  }
  if (cs.partial && cs.partial === cs.culprit) { failures++; console.log(`seed ${seed} T${cs.tpl}: partial-truth assigned to culprit`); }
  if (cs.liar && (cs.liar === cs.culprit || !cs.excl[cs.liar].length)) { failures++; console.log(`seed ${seed} T${cs.tpl}: liar invalid (${cs.liar})`); }
  }
}
console.log(`sweep: ${N} seeds x 3 cases, failures=${failures}`);
console.log(`template coverage: ${tplSeen.size}/12 -> {${[...tplSeen].sort((a,b)=>a-b).join(",")}}`);
if (tplSeen.size !== 12) { console.log("TEMPLATE COVERAGE INCOMPLETE"); process.exit(2); }
// per-template proof spot-checks with console proofs (the spec artifact)
let shown = 0;
for (let t = 1; t <= 12; t++) {
  for (let seed = 1; seed <= 5000; seed++) {
    const caseNum = Math.ceil(t / 4);
    const cs = generateCase(seed, caseNum);
    if (cs.tpl === t && shown < 6) {
      const p = proveCase(cs);
      console.log(`T${t} seed=${seed}: unique=${p.uniqueCulprit.holds} worlds={${p.uniqueCulprit.worlds}} noInnocentConvicts=${p.noInnocentConvicts.holds} records=[${cs.records.map(r=>r.id).join(",")}]`);
      shown++;
      break;
    }
  }
}
process.exit(failures ? 3 : 0);
