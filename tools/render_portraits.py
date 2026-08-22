#!/usr/bin/env python3
"""LIE TO ME v2 "The Breaking Point" — procedural painterly noir portrait renderer.

Design decisions D1-D5 (DECISIONS.md):
  D1  Procedural PIL renderer, seeded + regenerable, style-lock by construction.
  D2  Style lock: hard key light from LEFT; near-black room; warm lamp glow;
      skin lit #e0b28a -> shadow #342320; paper cream #ece5d3; stamp red/green; brass gold.
  D3  3 suspects x 3 expressions: COMPOSED / FRAYING / BROKEN. 512x640 (4:5), shown ~180px.
  D4  Identity anchors: Marlowe (older M, receding grey-flecked hair, oxblood tie),
      Vega (F, hair pulled back w/ side mass, plum kerchief), Ash (younger M, flat cap, olive collar).
  D5  Readability at ~180px beats realism: brow angle, mouth state, gaze drift,
      sweat sheen are the fray carriers; head pose fixed.

Usage:
    .venv/bin/python tools/render_portraits.py            # renders all 9 into assets/v2/portraits/
    .venv/bin/python tools/render_portraits.py --sheet    # also builds contact sheet
"""
import argparse
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter

W, H = 512, 640

# ---- style locks (D2) -------------------------------------------------------
ROOM_TOP = (13, 14, 19)        # #0d0e13
ROOM_BOT = (16, 16, 23)        # #101017
LAMP_GLOW = (58, 45, 26)       # #3a2d1a
SKIN_LIT = (224, 178, 138)     # #e0b28a
SKIN_MID = (150, 106, 78)
SKIN_SHADOW = (52, 35, 32)     # #342320
HAIR_DARK = (24, 20, 18)
PAPER = (236, 229, 211)        # not used in portraits; kept for family reference
GOLD = (226, 185, 59)
OXBLOOD = (96, 30, 34)         # Marlowe tie
PLUM = (86, 48, 74)            # Vega kerchief
OLIVE = (92, 94, 56)           # Ash collar
GREY_FLECK = (168, 164, 158)   # Marlowe hair flecks

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "assets", "v2", "portraits")


def vgrad(w, h, top, bot):
    """Vertical gradient background."""
    base = Image.new("RGB", (1, h))
    px = base.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        px[0, y] = tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3))
    return base.resize((w, h))


def lamp_pool(img, cx, cy, r, strength=110):
    """Warm radial pool — the interrogation lamp."""
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for i in range(r, 0, -4):
        a = int(strength * (1 - i / r) ** 2)
        d.ellipse([cx - i, cy - i * 1.25, cx + i, cy + i * 1.25], fill=a)
    mask = mask.filter(ImageFilter.GaussianBlur(18))
    glow = Image.new("RGB", (w, h), LAMP_GLOW)
    return Image.composite(glow, img, mask)


def ellipse_pts(cx, cy, rx, ry, n=64):
    return [(cx + rx * math.cos(2 * math.pi * k / n),
             cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def painterly_pass(img, seed=3, radius=2, passes=2):
    """Soft brush pass — kills vector edges, gives the oil-sketch feel."""
    out = img
    for _ in range(passes):
        blur = out.filter(ImageFilter.GaussianBlur(radius))
        out = Image.blend(out, blur, 0.55)
    # subtle canvas grain
    g = random.Random(seed)
    px = out.load()
    w, h = out.size
    for _ in range(w * h // 28):
        x, y = g.randrange(w), g.randrange(h)
        r, gg, b = px[x, y]
        dgr = g.randint(-9, 9)
        px[x, y] = (max(0, min(255, r + dgr)), max(0, min(255, gg + dgr)),
                    max(0, min(255, b + dgr)))
    return out


def vignette(img, strength=120):
    w, h = img.size
    m = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(m)
    steps = 40
    for i in range(steps, 0, -1):
        a = int(strength * (i / steps) ** 2.2)
        rw = w * 0.75 * (1 - i / steps) + w * 0.28
        rh = h * 0.72 * (1 - i / steps) + h * 0.30
        d.ellipse([w / 2 - rw, h / 2 - rh, w / 2 + rw, h / 2 + rh], fill=a)
    m = m.filter(ImageFilter.GaussianBlur(30))
    dark = Image.new("RGB", (w, h), (5, 5, 8))
    return Image.composite(dark, img, m)


def half_face_shadow(img, seed=11):
    """The accusation metaphor: right side of frame falls to near-black (D2 key-left)."""
    w, h = img.size
    grad = Image.new("L", (w, 1))
    gp = grad.load()
    for x in range(w):
        t = x / (w - 1)
        gp[x, 0] = int(min(135, max(0, (t - 0.66)) / 0.34 * 225))
    grad = grad.resize((w, h)).filter(ImageFilter.GaussianBlur(36))
    dark = Image.new("RGB", (w, h), (8, 8, 12))
    return Image.composite(dark, img, grad)


# ----------------------------- face geometry --------------------------------
def build_face(spec, expr):
    """spec: identity dict; expr in {COMPOSED, FRAYING, BROKEN}."""
    rnd = random.Random(f"{spec['name']}-{expr}")
    img = vgrad(W, H, ROOM_TOP, ROOM_BOT)
    img = lamp_pool(img, W * 0.36, H * 0.42, 330)

    d = ImageDraw.Draw(img)
    fraying = expr == "FRAYING"
    broken = expr == "BROKEN"

    # --- shoulders / torso -------------------------------------------------
    torso_y = int(H * 0.80)
    d.polygon([(int(W*0.06), H), (int(W*0.30), torso_y), (int(W*0.70), torso_y),
               (int(W*0.94), H)], fill=(28, 26, 30))
    # shirt collar wedge
    d.polygon([(int(W*0.40), torso_y+6), (int(W*0.50), torso_y+44),
               (int(W*0.60), torso_y+6)], fill=(196, 188, 172))
    # tie / kerchief / collar per identity
    if spec["name"] == "Marlowe":
        d.polygon([(int(W*0.47), torso_y+10), (int(W*0.53), torso_y+10),
                   (int(W*0.55), torso_y+90), (int(W*0.50), torso_y+108),
                   (int(W*0.45), torso_y+90)], fill=OXBLOOD)
    elif spec["name"] == "Vega":
        d.polygon([(int(W*0.38), torso_y-4), (int(W*0.62), torso_y-4),
                   (int(W*0.66), torso_y+34), (int(W*0.34), torso_y+34)], fill=PLUM)
    else:  # Ash
        d.polygon([(int(W*0.36), torso_y+2), (int(W*0.64), torso_y+2),
                   (int(W*0.68), torso_y+46), (int(W*0.32), torso_y+46)],
                  fill=(38, 40, 30))
        d.line([(int(W*0.36), torso_y+2), (int(W*0.64), torso_y+2)], fill=OLIVE, width=7)

    # --- head ----------------------------------------------------------------
    hx, hy = W * 0.47, H * 0.40          # slightly left-of-center: light side has air
    rx, ry = 118, 148                     # fixed pose (D5)
    head_pts = ellipse_pts(hx, hy, rx, ry, 72)
    jaw = [(hx - rx * 0.86, hy + ry * 0.30), (hx - rx * 0.62, hy + ry * 0.93),
           (hx, hy + ry * 1.04), (hx + rx * 0.62, hy + ry * 0.93),
           (hx + rx * 0.86, hy + ry * 0.30)]
    # head outline: ONE non-self-intersecting loop.
    # Upper arc traversed left->top->right (ang: pi..2pi), then jaw appended
    # right->left so the path never crosses itself. The v2 bowtie ordering
    # (ellipse starting at ang=0 + jaw left->right) self-intersected and its
    # zero-winding lens let background show through as a dark cheek patch.
    JAW_Y = hy + ry * 0.30
    head_all = []
    for k in range(36, 72):
        ang = 2 * math.pi * k / 72
        head_all.append((hx + rx * math.cos(ang), hy + ry * math.sin(ang)))
    n_jaw = 26
    for j in range(n_jaw, -1, -1):          # t: 1 -> 0  (right jaw -> left jaw)
        t = j / n_jaw
        jx = rx * 0.90 * -math.cos(math.pi * t)   # +0.9rx at t=1 ... -0.9rx at t=0
        jy = JAW_Y + (ry * 0.74) * math.sin(math.pi * t)  # dips to ry*1.04 mid-jaw
        head_all.append((hx + jx, jy))
    # neck
    d.polygon([(hx-44, hy+ry*0.82), (hx+44, hy+ry*0.82),
               (hx+52, torso_y+10), (hx-52, torso_y+10)], fill=SKIN_SHADOW)
    # ears: only the lit-side ear exists — the shadow-side ear lives inside the
    # silhouette now and reads as a dark cheek blotch; noir shadow swallows it.
    d.polygon(ellipse_pts(hx - rx*0.97, hy + 6, 16, 26, 20), fill=SKIN_MID)
    # face base — flat mid tone; noir lighting comes ENTIRELY from the
    # half_face_shadow post pass (key-left). Internal shading stays SOFT:
    # eye sockets, under-jaw, nose-side only. No geometric terminator split
    # (v1 of this renderer produced black wedge artifacts).
    face_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fd = ImageDraw.Draw(face_layer)
    fd.polygon(head_all, fill=SKIN_MID + (255,))
    # broad soft core light on the lit side of the face
    fd.ellipse([hx - rx*0.92, hy - ry*0.72, hx + rx*0.30, hy + ry*0.66],
               fill=(214, 168, 128, 150))
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, face_layer)
    face_soft = img_rgba.filter(ImageFilter.GaussianBlur(6))
    # keep the blurred version only INSIDE the head silhouette
    sil = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sil).polygon(head_all, fill=255)
    img = Image.composite(face_soft.convert("RGB"), img_rgba.convert("RGB"), sil)
    d = ImageDraw.Draw(img)
    sd = ImageDraw.Draw(img)
    EYEBROW_Y = hy - ry * 0.42
    EYE_Y = hy - ry * 0.22
    NOSE_Y = hy + ry * 0.16
    MOUTH_Y = hy + ry * 0.55
    lx = hx - rx * 0.42   # lit-side eye (left of frame)
    sx = hx + rx * 0.40   # shadow-side eye

    # soft anatomical shadows: eye sockets + under-jaw (drawn after eye
    # coords are known, before the features themselves)
    sock = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sod = ImageDraw.Draw(sock)
    sod.ellipse([lx - 40, EYE_Y - 22, lx + 40, EYE_Y + 20], fill=(96, 62, 48, 60))
    sod.ellipse([sx - 38, EYE_Y - 20, sx + 38, EYE_Y + 18], fill=(60, 40, 34, 80))
    # thin chin/jaw crescent ONLY — hugging the jaw outline, never the mouth
    sod.polygon([(hx - rx*0.50, hy + ry*0.94), (hx + rx*0.50, hy + ry*0.94),
                 (hx + rx*0.30, hy + ry*1.05), (hx - rx*0.30, hy + ry*1.05)],
                fill=(50, 34, 30, 70))
    sock = sock.filter(ImageFilter.GaussianBlur(9))
    img = Image.alpha_composite(img.convert("RGBA"), sock).convert("RGB")
    d = ImageDraw.Draw(img)

    def eye(ex, ey, lit_side):
        """Returns nothing; draws one eye. Gaze drift = fray carrier (D5)."""
        open_lid = 1.0 if not broken else 0.72
        w_eyelid = 30
        h_eye = 13 * open_lid
        # sclera barely reads in this light — mostly dark orbit + glint
        d.ellipse([ex - w_eyelid, ey - h_eye, ex + w_eyelid, ey + h_eye],
                  fill=(206, 200, 190) if lit_side else (120, 112, 104))
        iris_r = 9.5
        # gaze drift: composed centers, fraying darts outward, broken unfocused down-lid
        gx = (-6 if lit_side else 6) if fraying else (2 if lit_side else -2)
        gy = 3 if broken else 0
        ix, iy = ex + gx, ey + gy
        d.ellipse([ix - iris_r, iy - iris_r, ix + iris_r, iy + iris_r], fill=(38, 34, 30))
        d.ellipse([ix - 3.2, iy - 3.2, ix + 1.2, iy + 1.2], fill=(235, 228, 210))
        # upper lid line
        d.line([ex - w_eyelid, ey - h_eye - 2, ex + w_eyelid, ey - h_eye - 1],
               fill=(30, 24, 20), width=3)
        # under-eye bag deepens with fray
        bag = 3 if broken else (2 if fraying else 1)
        d.arc([ex - w_eyelid*0.8, ey + h_eye, ex + w_eyelid*0.8, ey + h_eye + 12],
              20, 160, fill=(70, 48, 40), width=bag)

    eye(lx, EYE_Y, True)
    eye(sx, EYE_Y + (2 if not broken else 5), False)

    # brows — the primary fray carrier (D5): inner-ends drop, angle steepens
    def brow(bx, lit_side):
        lift_out = 10
        inner_dx = -34 if lit_side else 30
        drop_inner = 0
        if fraying:
            drop_inner = 9
        if broken:
            drop_inner = 16
        tilt_out = -lift_out - (6 if broken else 0)
        p_in = (bx + inner_dx, EYEBROW_Y + drop_inner)
        p_out = (bx - inner_dx * 0.9, EYEBROW_Y - 6 + (tilt_out * 0.3))
        wd = 8 if not broken else 10
        col = HAIR_DARK if spec["name"] != "Marlowe" else (52, 48, 44)
        d.line([p_in, ((p_in[0]+p_out[0])/2, (p_in[1]+p_out[1])/2 - 4), p_out],
               fill=col, width=wd, joint="curve")

    brow(lx, True)
    brow(sx, False)

    # nose — minimal: nostril shade + bridge terminator
    d.line([hx - 8, EYE_Y + 8, hx - 14, NOSE_Y + 6], fill=(96, 66, 50), width=5)
    d.ellipse([hx - 22, NOSE_Y + 2, hx - 10, NOSE_Y + 10], fill=(84, 56, 42))
    d.ellipse([hx + 6, NOSE_Y + 3, hx + 18, NOSE_Y + 10], fill=(60, 40, 32))

    # mouth — state carrier: set -> dry-parted tremor -> slack open
    mw = 46
    if not fraying and not broken:
        d.line([hx - mw/2, MOUTH_Y, hx + mw/2, MOUTH_Y - 4], fill=(88, 52, 44), width=6)
    elif fraying:
        pts = [(hx - mw/2 + i*(mw/6), MOUTH_Y + (2 if i % 2 else -3)) for i in range(7)]
        d.line(pts, fill=(96, 56, 46), width=6, joint="curve")
        d.line([hx - mw/3, MOUTH_Y + 9, hx + mw/4, MOUTH_Y + 10],
               fill=(140, 96, 80), width=3)
    else:  # BROKEN: slack, open, breath caught
        d.ellipse([hx - mw/2.4, MOUTH_Y - 6, hx + mw/2.4, MOUTH_Y + 22],
                  fill=(40, 24, 22))
        d.line([hx - mw/2.4, MOUTH_Y - 6, hx + mw/2.4, MOUTH_Y - 6],
               fill=(120, 80, 66), width=4)

    # stubble shade on the broken state — FAINT, low-alpha, jawline only
    if broken and spec["name"] != "Vega":
        jpts = [(hx - rx*0.55, hy + ry*0.88), (hx, hy + ry*1.03), (hx + rx*0.52, hy + ry*0.86),
                (hx + rx*0.30, hy + ry*1.00), (hx - rx*0.32, hy + ry*1.01)]
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        od.polygon(jpts, fill=(30, 26, 24, 40))
        img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
        d = ImageDraw.Draw(img)

    # sweat drops — BROKEN gets visible beads on temple + brow
    if broken or fraying:
        beads = [(hx - rx*0.78, hy - ry*0.55, 5), (hx - rx*0.6, hy - ry*0.72, 4),
                 (hx - rx*0.88, hy - ry*0.2, 4)]
        if broken:
            beads += [(hx - rx*0.5, hy - ry*0.85, 5), (hx + rx*0.1, hy - ry*0.9, 3)]
        for bx, by, br in beads:
            d.ellipse([bx-br, by-br, bx+br, by+br], fill=(214, 222, 224))
            d.ellipse([bx-br*0.4, by-br*0.5, bx+br*0.1, by+br*0.1], fill=(245, 250, 250))

    # ---------------- hair per identity (fixed pose, D4/D5) ------------------
    if spec["name"] == "Marlowe":
        # receding grey-flecked hair: high forehead, thin strands over crown
        crown = [(hx-rx*1.02, hy-ry*0.30), (hx-rx*0.72, hy-ry*0.98),
                 (hx+rx*0.10, hy-ry*1.10), (hx+rx*0.78, hy-ry*0.86),
                 (hx+rx*1.00, hy-ry*0.22)]
        d.polygon(crown, fill=HAIR_DARK)
        rr = random.Random("marlowe-flecks")
        for _ in range(46):
            ang = rr.uniform(-math.pi*0.92, -math.pi*0.08)
            gr = rr.uniform(0.62, 1.0)
            fx = hx + math.cos(ang)*rx*gr
            fy = hy - abs(math.sin(ang))*ry*gr*1.02
            d.line([fx, fy, fx+rr.randint(-5, 5), fy+rr.randint(2, 6)],
                   fill=(*GREY_FLECK,), width=2)
    elif spec["name"] == "Vega":
        # hair pulled back into a side mass BEHIND the head + plum kerchief
        # tied at the crown (fabric knot visible, not a sports band).
        # side mass first, behind the head silhouette
        d.polygon(ellipse_pts(hx - rx*1.02, hy + ry*0.10, 44, 96, 24), fill=HAIR_DARK)
        # hairline: dark cap of hair over the top of the skull
        d.polygon([(hx-rx*1.04, hy-ry*0.22), (hx-rx*0.80, hy-ry*0.92),
                   (hx+rx*0.30, hy-ry*1.10), (hx+rx*0.95, hy-ry*0.72),
                   (hx+rx*1.02, hy-ry*0.30)], fill=HAIR_DARK)
        # kerchief: a band ACROSS THE CROWN ONLY, with a knot + trailing tails
        # on the lit side; sits ABOVE the brows, never over the ears.
        ky = hy - ry*0.62
        d.polygon([(hx-rx*1.02, ky), (hx+rx*0.98, ky-10),
                   (hx+rx*0.90, ky-34), (hx-rx*0.94, ky-26)], fill=PLUM)
        # band highlight (lit side)
        d.polygon([(hx-rx*1.02, ky), (hx+rx*0.20, ky-6),
                   (hx+rx*0.18, ky-16), (hx-rx*1.0, ky-12)],
                  fill=(118, 70, 104))
        # knot + tails on lit side
        d.polygon(ellipse_pts(hx - rx*0.98, ky - 6, 15, 12, 16), fill=(70, 38, 62))
        d.polygon([(hx - rx*1.05, ky - 4), (hx - rx*1.30, ky + 26),
                   (hx - rx*1.12, ky + 30), (hx - rx*0.92, ky + 6)], fill=PLUM)
        d.polygon([(hx - rx*0.95, ky - 8), (hx - rx*1.22, ky - 34),
                   (hx - rx*1.06, ky - 38), (hx - rx*0.84, ky - 14)],
                  fill=(78, 44, 68))
    else:  # Ash flat cap — sits HIGH so the brows and eyes stay readable (D5)
        cap = [(hx-rx*1.10, hy-ry*0.52), (hx-rx*0.66, hy-ry*1.16),
               (hx+rx*0.50, hy-ry*1.20), (hx+rx*1.02, hy-ry*0.62),
               (hx+rx*1.28, hy-ry*0.50), (hx+rx*1.00, hy-ry*0.38),
               (hx-rx*0.98, hy-ry*0.36)]
        d.polygon(cap, fill=(34, 32, 28))
        d.line([(hx-rx*1.10, hy-ry*0.52), (hx+rx*1.28, hy-ry*0.50)],
               fill=(58, 54, 46), width=5)
        # cap crown seam
        d.arc([hx - rx*0.5, hy - ry*1.34, hx + rx*0.6, hy - ry*0.86],
              200, 340, fill=(52, 48, 42), width=4)

    # ---------------- lamp rim light on lit EDGE only (style signature) ------
    # v1 stroked every head point left of center, which included the top arc
    # and drew a gold line down the middle of the face. Restrict to the true
    # left-edge band (near min-x) so it reads as an edge catch-light.
    rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    xs_all = [p[0] for p in head_all]
    x_left = min(xs_all)
    rim_pts = [p for p in head_all if p[0] < x_left + rx * 0.22 and p[1] > hy - ry * 0.5]
    if len(rim_pts) > 2:
        rd.line(rim_pts, fill=(232, 190, 128, 120), width=4, joint="curve")
    img = Image.alpha_composite(img.convert("RGBA"), rim).convert("RGB")

    # ---------------- post: painterly, shadow, vignette ----------------------
    if os.environ.get("LTM_DEBUG"):
        stem = f"/tmp/ltm-{spec['name'].lower()}-{expr.lower()}"
        img.save(stem + "-0-preramp.png")
    img = painterly_pass(img, seed=hash(spec["name"]) % 999)
    if os.environ.get("LTM_DEBUG"):
        img.save("/tmp/ltm-dbg-painterly.png")
    img = half_face_shadow(img)
    if os.environ.get("LTM_DEBUG"):
        img.save("/tmp/ltm-dbg-ramp.png")
    img = vignette(img)

    return img


SPECS = [
    {"name": "Marlowe"},
    {"name": "Vega"},
    {"name": "Ash"},
]
EXPRS = ["COMPOSED", "FRAYING", "BROKEN"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", action="store_true", help="also write contact sheet")
    ap.add_argument("--outdir", default=OUT_DIR)
    args = ap.parse_args()
    os.makedirs(args.outdir, exist_ok=True)
    written = []
    for spec in SPECS:
        for expr in EXPRS:
            img = build_face(spec, expr)
            path = os.path.join(args.outdir, f"{spec['name'].lower()}-{expr.lower()}.png")
            img.save(path, optimize=True)
            written.append(path)
            print("wrote", path)
    if args.sheet:
        sheet = Image.new("RGB", (W*3, H*3), (10, 10, 14))
        for i, spec in enumerate(SPECS):
            for j, expr in enumerate(EXPRS):
                tile = Image.open(os.path.join(
                    args.outdir, f"{spec['name'].lower()}-{expr.lower()}.png"))
                sheet.paste(tile, (j*W, i*H))
        sp = os.path.join(args.outdir, "_contact-sheet.png")
        sheet.save(sp, optimize=True)
        print("wrote", sp)
        # game-scale strip (~180px wide as engineering will display)
        gs = Image.new("RGB", (184*3 + 16, 230), (13, 14, 19))
        for i, spec in enumerate(SPECS):
            tile = Image.open(os.path.join(args.outdir,
                              f"{spec['name'].lower()}-broken.png")).resize((176, 220))
            gs.paste(tile, (8 + i*184, 5))
        gp = os.path.join(args.outdir, "_gamescale-strip.png")
        gs.save(gp, optimize=True)
        print("wrote", gp)


if __name__ == "__main__":
    main()
