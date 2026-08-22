#!/usr/bin/env python3
"""LIE TO ME v2 — ambience/music REFERENCE stems + desk dressing (D7, D8).

Stems: rain-on-glass bed, bass walk loop, brushed drums loop (music lane may replace).
Dressing: polaroid frame, ledger page (with coffee ring), elevator log strip.
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.io import wavfile

SR = 22050
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "assets", "v2")
AUDIO = os.path.join(BASE, "audio")
DRESS = os.path.join(BASE, "dressing")

PAPER = (236, 229, 211)
PAPER_DK = (216, 206, 184)
INK = (44, 40, 36)
COFFEE = (122, 82, 48)
GOLD = (226, 185, 59)


def pink_noise(n, seed=1):
    rng = np.random.RandomState(seed)
    white = rng.standard_normal(n + 1)
    # simple IIR pink filter
    b = [0.049922035, -0.095993537, 0.050612699, -0.004408786]
    a = [1, -2.494956002, 2.017265875, -0.522189400]
    from scipy.signal import lfilter
    return lfilter(b, a, white)[:n]


def wobble(n, rate=0.13, depth=0.25, seed=3):
    t = np.arange(n) / SR
    rng = np.random.RandomState(seed)
    ph0, ph1 = rng.uniform(0, 6.28, 2)
    return 1 - depth * (np.sin(2 * math.pi * rate * t + ph0) * 0.7 +
                        np.sin(2 * math.pi * rate * 1.7 * t + ph1) * 0.3)


def write_wav(path, sig, peak=0.5):
    m = np.max(np.abs(sig)) or 1.0
    data = (sig / m * peak * 32767).astype("<i2")
    wavfile.write(path, SR, data)
    print("wrote", path, f"{len(sig)/SR:.1f}s")


def make_audio():
    os.makedirs(AUDIO, exist_ok=True)
    n = SR * 16  # 16 s loops
    rain = pink_noise(n) * wobble(n)
    lp = np.exp(-np.arange(24) / 4.0); lp /= lp.sum()
    rain = np.convolve(rain, lp, mode="same")
    write_wav(os.path.join(AUDIO, "amb-rain.wav"), rain, peak=0.30)

    rt = pink_noise(SR * 16, seed=9) * 0.02
    hum = 0.05 * np.sin(2 * math.pi * 50 * np.arange(SR * 16) / SR)
    write_wav(os.path.join(AUDIO, "amb-room-tone.wav"), rt + hum, peak=0.10)

    # bass walk: 70 BPM swing eighths, D minor walk with ii-V-i turnarounds
    bpm = 70.0; beat = 60.0 / bpm; bar = 4 * beat
    bars = 16; total = int(bars * bar * SR)
    out = np.zeros(total)
    rng = np.random.RandomState(5)
    root = [73.42, 65.41, 58.27, 55.0]   # D2 C2 A#1? keep simple descending roots
    for b in range(bars):
        f0 = root[b % len(root)]
        for e in range(8):               # walking eighths
            t0 = (b * bar + e * beat / 2)
            idx = int(t0 * SR)
            dur = int(beat * 0.45 * SR)
            if idx + dur >= total:
                break
            step = rng.choice([0, 2, 3, 5, 7])
            f = f0 * 2 ** (step / 12) * (2 if e == 7 and b % 2 else 1)
            tt = np.arange(dur) / SR
            tone = (np.sin(2 * math.pi * f * tt) +
                    0.4 * np.sin(4 * math.pi * f * tt)) * np.exp(-tt * 3.5)
            out[idx:idx + dur] += tone
    write_wav(os.path.join(AUDIO, "stem-bass-walk.wav"), out, peak=0.45)

    # brushed drums: rim clicks + brush swishes at 70BPM swing
    out = np.zeros(total)
    for b in range(bars):
        for beat_i in range(4):
            for off, kind in ((0.0, "rim"), (2/3, "rim"), (0.5, "brush")):
                t0 = (b * bar + beat_i * beat + off * beat) % (total / SR)
                idx = int(t0 * SR); dur = int((0.06 if kind == "rim" else 0.22) * SR)
                if idx + dur >= total:
                    continue
                nz = rng.uniform(-1, 1, dur)
                env = np.exp(-np.arange(dur) / (dur / (3 if kind == "rim" else 8)))
                out[idx:idx + dur] += nz * env * (0.8 if kind == "rim" else 0.35)
    write_wav(os.path.join(AUDIO, "stem-brushed-drums.wav"), out, peak=0.28)


def _paper(w, h, ruled=True, seed=1):
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    rnd = np.random.RandomState(seed)
    # paper grain
    for _ in range(w * h // 60):
        x, y = rnd.randint(w), rnd.randint(h)
        g = int(rnd.randint(-8, 8))
        px = img.getpixel((x, y))
        img.putpixel((x, y), tuple(max(0, min(255, c + g)) for c in px))
    if ruled:
        for y in range(int(h*0.18), int(h*0.94), int(h*0.076)):
            d.line([(int(w*0.08), y), (int(w*0.92), y)], fill=PAPER_DK, width=2)
    return img, d


def coffee_ring(img, cx, cy, r, seed=2):
    """ring stain: two arcs of varying darkness"""
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    rnd = np.random.RandomState(seed)
    for i in range(14):
        rr = r + rnd.randint(-4, 5)
        a0 = rnd.uniform(0, 360); a1 = a0 + rnd.uniform(120, 300)
        alpha = rnd.randint(50, 110)
        od.arc([cx-rr, cy-rr, cx+rr, cy+rr], a0, a1,
               fill=(*COFFEE, alpha), width=rnd.randint(3, 7))
    ov = ov.filter(ImageFilter.GaussianBlur(2))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def make_dressing():
    os.makedirs(DRESS, exist_ok=True)

    # polaroid frame (portrait window 4:5)
    pw, ph = 420, 500
    pol = Image.new("RGB", (pw, ph), PAPER)
    d = ImageDraw.Draw(pol)
    d.rectangle([24, 24, pw-24, ph-96], outline=(190, 182, 164), width=2)
    d.rectangle([26, 26, pw-26, ph-98], fill=(20, 20, 26))     # photo well (dark)
    # caption line drawn as squiggle (font-free)
    pts = [(70 + i*38, ph - 62 + int(6*math.sin(i)))for i in range(8)]
    d.line(pts, fill=(70, 64, 58), width=3)
    grain(pol, seed=11)
    pol.save(os.path.join(DRESS, "polaroid-frame.png"), optimize=True)
    print("wrote polaroid-frame.png")

    # ledger page w/ coffee ring
    led, d = _paper(560, 720, ruled=True, seed=4)
    led = coffee_ring(led, 430, 600, 66, seed=6)
    # faux entries: short ink strokes on rules
    dd = ImageDraw.Draw(led)
    rnd = np.random.RandomState(8)
    row = 0
    for y in range(int(720*0.19), int(720*0.93), int(720*0.076)):
        x = 56 + rnd.randint(0, 30)
        for k in range(rnd.randint(2, 5)):
            ln = rnd.randint(30, 90)
            yy = y - 8
            dd.line([(x, yy), (x+ln, yy+rnd.randint(-2, 2))], fill=INK, width=3)
            x += ln + 18
        row += 1
    # header stroke
    dd.line([(56, 92), (300, 92)], fill=INK, width=4)
    led.save(os.path.join(DRESS, "ledger-page.png"), optimize=True)
    print("wrote ledger-page.png")

    # elevator log strip (narrow ticket)
    st = Image.new("RGB", (520, 150), PAPER)
    d = ImageDraw.Draw(st)
    for i in range(4):
        y = 26 + i * 32
        d.line([(24, y), (140, y)], fill=INK, width=3)
        d.line([(170, y), (330, y)], fill=PAPER_DK, width=2)
        d.line([(360, y), (430, y)], fill=INK, width=3)
        d.line([(450, y), (480, y)], fill=PAPER_DK, width=2)
    grain(st, seed=21)
    st.save(os.path.join(DRESS, "elevator-log-strip.png"), optimize=True)
    print("wrote elevator-log-strip.png")


def grain(img, seed=1):
    d = ImageDraw.Draw(img)
    rnd = np.random.RandomState(seed)
    w, h = img.size
    for _ in range(w * h // 80):
        x, y = rnd.randint(w), rnd.randint(h)
        px = img.getpixel((x, y))
        g = rnd.randint(-7, 7)
        img.putpixel((x, y), tuple(max(0, min(255, c + g)) for c in px))


if __name__ == "__main__":
    make_audio()
    make_dressing()
