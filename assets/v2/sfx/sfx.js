// LIE TO ME v2 — SFX/music playback port (design-authored reference implementation).
// Engineering may inline this into the single-file HTML build. Contract:
//   LTM_SFX.init()                       — call once from first user gesture (autoplay policy)
//   LTM_SFX.play(name)                   — one-shot SFX by name (see sfx-params.json)
//   LTM_SFX.setMusicState({falseStamps}) — implements audio-spec.md §2 layering rules
"use strict";
const LTM_SFX = (() => {
  let ctx = null;
  const buffers = {};
  let bassSrc = null, drumSrc = null, rainSrc = null;
  let bassGain = null, state = { falseStamps: 0 };

  async function init() {
    if (ctx) return;
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    const names = ["stamp-thunk-1","stamp-thunk-2","stamp-thunk-3","string-twang",
                   "lamp-flicker-buzz","bass-drop","gavel-slam","typewriter-clatter",
                   "release-stamp"];
    for (const n of names) {
      const r = await fetch(`sfx/${n}.wav`);
      buffers[n] = await ctx.decodeAudioData(await r.arrayBuffer());
    }
    // ambience bed
    rainSrc = await _loopFrom("rain", -18); // optional; skip silently if absent
    _updateMusic();
  }

  async function _loopFrom(name, db) {
    try {
      const r = await fetch(`audio/${name}.wav`);
      const buf = await ctx.decodeAudioData(await r.arrayBuffer());
      const src = ctx.createBufferSource(); src.buffer = buf; src.loop = true;
      const g = ctx.createGain();
      g.gain.value = Math.pow(10, db / 20);
      src.connect(g).connect(ctx.destination); src.start();
      return { src, g };
    } catch (e) { return null; }
  }

  function play(name) {
    if (!ctx || !buffers[name]) return;
    const src = ctx.createBufferSource(); src.buffer = buffers[name];
    const g = ctx.createGain(); g.gain.value = 1;
    src.connect(g).connect(ctx.destination); src.start();
    // duck bed briefly on heavy hits
    if (name.startsWith("stamp-thunk") || name === "gavel-slam") _duck();
  }

  let duckTimer = null;
  function _duck() {
    if (!bassGain) return;
    const t = ctx.currentTime;
    bassGain.gain.cancelScheduledValues(t);
    bassGain.gain.setTargetAtTime(bassGain.gain.value * 0.4, t, 0.02);
    clearTimeout(duckTimer);
    duckTimer = setTimeout(_updateMusic, 600);
  }

  // spec §2: bass enters after 1st FALSE stamp (+6 dB each), pitch drops a whole
  // step per FALSE stamp floor D2; drums enter at 2nd FALSE stamp.
  const STEPS = [110.0, 98.0, 87.31, 73.42]; // A2 G2 F2 D2
  function setMusicState(s) { state = { ...state, ...s }; _updateMusic(); }

  async function _updateMusic() {
    if (!ctx || state.falseStamps < 1) return;
    const fs = Math.min(state.falseStamps, 3);
    if (!bassSrc) {
      try {
        const r = await fetch("audio/stem-bass-walk.wav");
        const buf = await ctx.decodeAudioData(await r.arrayBuffer());
        bassSrc = ctx.createBufferSource(); bassSrc.buffer = buf; bassSrc.loop = true;
        bassGain = ctx.createGain();
        bassSrc.playbackRate.value = STEPS[fs - 1] / 110.0;
        bassSrc.connect(bassGain).connect(ctx.destination); bassSrc.start();
      } catch (e) { return; }
    } else {
      bassSrc.playbackRate.setTargetAtTime(STEPS[fs - 1] / 110.0, ctx.currentTime, 0.15);
    }
    bassGain.gain.setTargetAtTime(
      Math.pow(10, (-20 + 6 * (fs - 1)) / 20), ctx.currentTime, 0.3);
  }

  function cutAll() { // wrong-conviction silence rule (spec §2.3)
    for (const s of [bassSrc]) if (s) try { s.stop(); } catch (e) {}
    bassSrc = null;
    if (rainSrc && rainSrc.g) {
      const t = ctx.currentTime;
      rainSrc.g.gain.setTargetAtTime(0.0001, t, 0.05);
      setTimeout(() => rainSrc && rainSrc.g &&
        rainSrc.g.gain.setTargetAtTime(Math.pow(10, -18 / 20), t + 0.9, 0.5), 900);
    }
  }

  return { init, play, setMusicState, cutAll };
})();
