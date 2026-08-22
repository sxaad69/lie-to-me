# AMBIENCE / MUSIC SPEC — LIE TO ME v2 "The Breaking Point"

Status: design-authored reference stems rendered (see `assets/v2/audio/`), spec binding
for engineering. Music lane may replace stems with better material, but the layering
contract below is the requirement (decision D7).

## 1. Ambience bed ("rain on glass", loop)

| Stem | Content | Level |
|---|---|---|
| `amb-rain.wav` | filtered pink-noise rain patter, low-pass ~1.4k, gentle amplitude wobble | -18 LUFS bed level |
| `amb-room-tone.wav` | near-quiet room tone: 50Hz hum + faint hiss | -30 LUFS |

Loop points: rain stem loops cleanly at bar boundary; crossfade 40 ms if re-cut.
Bed plays from case start, fades in over 1.2 s. Duck to -12 dB under dialogue/stamp
moments, recover with 1.5 s release.

## 2. Noir jazz 2-stem motif (layering in as accusations accumulate)

| Stem | Content | Entry rule |
|---|---|---|
| `stem-bass-walk.wav` | double-bass walking line, ~70 BPM, minor ii-V-i turnarounds, 98 Hz root | enters after FIRST FALSE stamp lands; volume +6 dB per additional FALSE stamp, max -8 LUFS |
| `stem-brushed-drums.wav` | brushed kit, swing eighths, rim-click pattern | enters after SECOND FALSE stamp or when any suspect portrait hits FRAYING; rides under bass at -10 LUFS |

Layering rules:
1. Stems are additive mono renders at -20 LUFS nominal; mix bus rides -14 LUFS.
2. Bass stem pitch-shifts DOWN a whole step per FALSE stamp (D minor descent:
   A2→G2→F2...), floor at D2 (73.4 Hz) — mirrors the "breaking point" visual.
3. On WRONG conviction lock: all stems cut instantly → 0.9 s silence → bass drop
   one-shot (`bass-drop.wav`) → records thud onto desk (`stamp-thunk-*` x N) as
   exculpatting evidence appears, one thud per record.
4. On CORRECT lock: gavel slam (`gavel-slam.wav`) → hit-stop 350 ms → lamp flicker
   (`lamp-flicker-buzz.wav`) → portrait break (crack SFX = string-twang pitched up)
   → typed confession over typewriter clatter.
5. Case closed: single release stamp (`release-stamp.wav`), music bed resolves to
   unison A and stops.

## 3. SFX map

| Moment | File | Trigger |
|---|---|---|
| Stamp TRUE/FALSE | `stamp-thunk-{1,2,3}.wav` | random variant per click |
| First contradiction found | `string-twang.wav` | once per suspect |
| Lamp flicker juice | `lamp-flicker-buzz.wav` | snap moment / idle >45 s |
| Snap moment payoff | `bass-drop.wav` | correct-lock chain reveal start |
| Wrong conviction | `gavel-slam.wav` (distant, lowpassed) then silence | wrong lock |
| Records reading | `typewriter-clatter.wav` | chain text typing |
| Case closed | `release-stamp.wav` | verdict stamp |

## 4. Delivery format for engineering

- All files 22050 Hz mono WAV 16-bit (drop-in for WebAudio without resampling).
- JS playback port: `assets/v2/sfx/sfx.js` exposes `LTM_SFX.play(name)` +
  `LTM_SFX.setMusicState({falseStamps:n})` implementing the layering rules above;
  params JSON in `sfx-params.json` carries durations/kinds so engineering never
  hard-codes timings.
- Total audio budget: < 400 KB decoded (< 250 KB encoded if opus later).
