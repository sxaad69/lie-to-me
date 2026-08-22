#!/usr/bin/env python3
"""LIE TO ME v2 "The Breaking Point" — jsfxr-class SFX pack (decision D6).

Renders real WAVs (22050 Hz mono 16-bit) + JSON params + a JS playback port:
  - stamp-thunk x3 variants   : heavy rubber-stamp slam on paper
  - string-twang              : plucked double-bass twang (accusation sting)
  - lamp-flicker-buzz         : fluorescent flicker buzz (lamp juice)
  - bass-drop                 : pitch-diving sub drop (snap moment)
  - gavel-slam                : courtroom gavel crack
  - typewriter-clatter        : key clatter burst (records/ledger)
  - release-stamp             : lighter paper stamp (case closed)

Usage: .venv/bin/python tools/make_sfx.py
Output: assets/v2/sfx/*.wav + sfx-params.json + sfx.js
"""
import json
import math
import os

import numpy as np
from scipy.io import wavfile

SR = 22050
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "v2", "sfx")


def env_ad(n, a=0.005, d=0.15, curve=3.0):
    """attack-decay envelope"""
    n = int(n)
    t = np.arange(n) / SR
    ea = np.clip(t / max(a, 1e-9), 0, 1) ** (1 / curve)
    ed = np.clip((n / SR - t) / max(d, 1e-9), 0, 1) ** curve
    return ea * ed


def noise_sweep(n, f0=2200, f1=140, q=0.7, seed=3):
    """filtered noise sweep — the 'thud' body of a stamp/gavel"""
    rng = np.random.RandomState(seed)
    x = rng.uniform(-1, 1, int(n))
    # simple time-varying resonant lowpass via biquad coefficients swept f0->f1
    out = np.zeros_like(x)
    f = np.geomspace(f0, f1, len(x))
    y1 = np.zeros(2)
    for i in range(len(x)):
        w0 = 2 * math.pi * f[i] / SR
        alpha = math.sin(w0) / (2 * q)
        b0 = (1 - math.cos(w0)) / 2
        b1 = 1 - math.cos(w0)
        b2 = b0
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        xh0, xh1 = x[i], (x[i - 1] if i >= 1 else 0)
        yh1, yh2 = y1[0], y1[1]
        yv = (b0 / a0) * xh0 + (b1 / a0) * xh1 + (b2 / a0) * 0 \
             - (a1 / a0) * yh1 - (a2 / a0) * yh2
        out[i] = yv
        y1 = [yv, yh1]
    m = np.max(np.abs(out)) or 1.0
    return out / m


def tone_drop(n, f_start=180, f_end=38, curve=2.2):
    """exponential pitch dive sine — bass drop"""
    t = np.arange(int(n)) / SR
    f = np.geomspace(f_start, f_end, len(t))
    ph = 2 * math.pi * np.cumsum(f) / SR
    s = np.sin(ph)
    return s * env_ad(n, d=n / SR, curve=curve)


def karplus_strong(n, f0=98.0, decay=0.996, seed=7):
    """classic pluck — string twang at ~98Hz (G2-ish double bass)"""
    rng = np.random.RandomState(seed)
    period = max(2, int(SR / f0))
    buf = list(rng.uniform(-1, 1, period))
    out = np.zeros(int(n))
    for i in range(len(out)):
        v = buf[i % period]
        out[i] = v
        buf[i % period] = decay * 0.5 * (v + buf[(i + 1) % period])
    m = np.max(np.abs(out)) or 1.0
    return out / m


def square_buzz(n, f=118.0, depth=0.6, rate=13.0):
    """flickering fluorescent buzz: square wave with AM flutter"""
    t = np.arange(int(n)) / SR
    sq = np.sign(np.sin(2 * math.pi * f * t))
    am = 1 - depth * (np.sin(2 * math.pi * rate * t) > 0.55).astype(float)
    return sq * am * env_ad(n, a=0.02, d=n / SR, curve=1.5)


def click_train(n, hits=14, base_t=0.045, spread=0.28, seed=11):
    """typewriter clatter: short filtered-noise clicks on a loose grid"""
    rng = np.random.RandomState(seed)
    out = np.zeros(int(n))
    for k in range(hits):
        start = (base_t + rng.uniform(0, spread)) * SR
        ln = int(0.012 * SR)
        if start + ln < len(out):
            seg = rng.uniform(-1, 1, ln) * np.exp(-np.arange(ln) / (ln / 4))
            out[int(start):int(start) + ln] += seg
    m = np.max(np.abs(out)) or 1.0
    return out / m


def write(name, sig, params):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".wav")
    sig16 = (np.clip(sig, -1, 1) * 32767).astype("<i2")
    wavfile.write(path, SR, sig16)
    print("wrote", path, f"{len(sig)/SR:.2f}s")
    return {"file": name + ".wav", **params}


def main():
    meta = {}
    dur = lambda s: int(s * SR)

    for v in (1, 2, 3):
        n = dur(0.32)
        body = noise_sweep(n, f0=300 + 60 * v, f1=90, q=0.8, seed=20 + v)
        thump = body * env_ad(n, a=0.002, d=0.09, curve=2.4)
        knock = karplus_strong(dur(0.05), f0=240, decay=0.992, seed=40 + v) * 0.35
        mix = thump.copy()
        mix[: len(knock)] += knock[: len(mix)]
        m = np.max(np.abs(mix))
        meta[f"stamp-thunk-{v}"] = write(
            f"stamp-thunk-{v}", mix / m,
            {"kind": "stamp", "variant": v, "dur": len(mix) / SR})

    tw = karplus_strong(dur(1.4), f0=98.0, decay=0.9992, seed=7)
    tw *= env_ad(len(tw), a=0.003, d=1.1, curve=2.0)
    meta["string-twang"] = write("string-twang", tw,
                                 {"kind": "sting", "f": 98.0, "dur": len(tw) / SR})

    bz = square_buzz(dur(0.85), f=118.0, depth=0.65, rate=13.0)
    meta["lamp-flicker-buzz"] = write("lamp-flicker-buzz", bz,
                                      {"kind": "buzz", "f": 118.0, "dur": len(bz) / SR})

    bd = tone_drop(dur(1.25), f_start=170, f_end=36)
    meta["bass-drop"] = write("bass-drop", bd, {"kind": "drop", "dur": len(bd) / SR})

    gv = noise_sweep(dur(0.30), f0=900, f1=120, q=0.65, seed=5)
    gv *= env_ad(len(gv), a=0.001, d=0.075, curve=3.0)
    crack = karplus_strong(dur(0.06), f0=520, decay=0.988, seed=9) * 0.4
    gv[: len(crack)] += crack[: len(gv)]
    m = np.max(np.abs(gv))
    meta["gavel-slam"] = write("gavel-slam", gv / m, {"kind": "gavel", "dur": len(gv) / SR})

    tc = click_train(dur(0.75), hits=14)
    meta["typewriter-clatter"] = write("typewriter-clatter", tc,
                                       {"kind": "clatter", "dur": len(tc) / SR})

    rs = noise_sweep(dur(0.22), f0=420, f1=110, q=0.9, seed=31)
    rs *= env_ad(len(rs), a=0.0015, d=0.06, curve=2.2)
    meta["release-stamp"] = write("release-stamp", rs, {"kind": "stamp-light", "dur": len(rs) / SR})

    with open(os.path.join(OUT, "sfx-params.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print("wrote", os.path.join(OUT, "sfx-params.json"))


if __name__ == "__main__":
    main()
