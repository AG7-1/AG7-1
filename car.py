#!/usr/bin/env python3
"""
Rotating 3D supercar rendered in binary, with scissor doors that swing open as it turns.

The car is a signed-distance-field model raymarched with numpy. Each frame becomes
rows of 0/1 characters, and CSS flips through the frames, so it animates on GitHub.
Writes car_dark.svg and car_light.svg.   Run: python car.py
"""
import math
import random

import numpy as np

from common import ROOT, THEMES, esc, window

COLS, ROWS = 116, 44
FONT = 8.6
CW, LH = FONT * 0.6, FONT * 1.1
FRAMES = 60
LOOP = 7.5          # seconds per revolution
LEVELS = [0.14, 0.28, 0.45, 0.65, 0.84, 1.0]


# ------------------------------------------------------------------ SDF helpers
def box(p, c, h):
    q = np.abs(p - c) - h
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0)


def rbox(p, c, h, r):
    return box(p, c, np.asarray(h) - r) - r


def plane(p, n, d):
    """distance to half-space n·p <= d (negative inside)."""
    n = np.asarray(n, float)
    return (p @ n - d) / np.linalg.norm(n)


def cyl_y(p, c, r, hw):
    """cylinder with its axis along y (wheels)."""
    q = p - c
    d = np.stack([np.hypot(q[:, 0], q[:, 2]) - r, np.abs(q[:, 1]) - hw], -1)
    return np.minimum(d.max(-1), 0) + np.linalg.norm(np.maximum(d, 0), axis=-1)


def smin(a, b, k=0.08):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b + (a - b) * h - k * h * (1 - h)


def rot_xz(p, pivot, ang):
    """rotate points around a y-parallel axis through pivot."""
    q = p - pivot
    c, s = math.cos(ang), math.sin(ang)
    x = c * q[:, 0] - s * q[:, 2]
    z = s * q[:, 0] + c * q[:, 2]
    return np.stack([x, q[:, 1], z], -1) + pivot


# ------------------------------------------------------------------ the car
# x: front(-) -> rear(+), y: left/right, z: up. Proportions follow a low wedge V12 supercar.
WHEELS = [(-1.45, 0.88), (1.4, 0.89)]
WR = 0.37


def cyl_x(p, c, r, hl):
    """cylinder with its axis along x (exhausts)."""
    q = p - c
    d = np.stack([np.hypot(q[:, 1], q[:, 2]) - r, np.abs(q[:, 0]) - hl], -1)
    return np.minimum(d.max(-1), 0) + np.linalg.norm(np.maximum(d, 0), axis=-1)


def car(p, door):
    """returns (distance, material): 0 paint, 1 tyre, 2 glass, 3 rim, 4 lights (emissive), 5 vents."""
    y = np.abs(p[:, 1])
    ps = np.stack([p[:, 0], y, p[:, 2]], -1)     # mirror left/right
    x, z = ps[:, 0], ps[:, 2]

    # lower body: long, low, wide slab
    body = rbox(ps, [0.0, 0, 0.5], [2.38, 1.03, 0.34], 0.1)
    body = np.maximum(body, plane(ps, [-0.22, 0, 1], 0.98))          # long flat bonnet (nose tip ~0.45)
    body = np.maximum(body, plane(ps, [-0.42, 1, 0], 1.62))          # pointed arrow nose in plan view
    body = np.maximum(body, plane(ps, [0.25, 1, 0], 1.6))            # slight rear taper
    body = np.maximum(body, plane(ps, [0, 1, 0.42], 1.26))           # sharp tumblehome crease
    body = np.maximum(body, plane(ps, [0.04, 0, 1], 0.9))            # flat engine deck
    body = np.maximum(body, plane(ps, [-1, 0, -0.9], 2.02))          # aggressive chin splitter angle
    body = np.maximum(body, plane(ps, [1, 0, -0.5], 2.2))            # rear diffuser kick

    # cabin: very raked windscreen running almost from the nose, short roof
    cab = rbox(ps, [0.3, 0, 0.88], [1.3, 0.72, 0.24], 0.08)
    cab = np.maximum(cab, plane(ps, [-0.42, 0, 1], 1.21))            # windscreen
    cab = np.maximum(cab, plane(ps, [0.13, 0, 1], 1.16))             # roof -> louvred engine cover
    cab = np.maximum(cab, plane(ps, [0, 1, 0.7], 1.3))               # narrow canopy
    d = smin(body, cab, 0.1)

    # big angular side intakes ahead of the rear wheels + roof-side scoops
    d = np.maximum(d, -np.maximum(box(ps, [0.82, 1.06, 0.58], [0.42, 0.16, 0.17]),
                                  plane(ps, [-0.6, 0, -1], -0.15)))   # wedge-shaped mouth
    d = np.maximum(d, -box(ps, [0.9, 0.8, 0.98], [0.25, 0.08, 0.06]))
    # front bumper intakes
    d = np.maximum(d, -box(ps, [-2.3, 0.62, 0.34], [0.2, 0.26, 0.08]))
    # engine cover louvres (shallow grooves)
    louv = np.abs(((x - 1.0) % 0.22) - 0.11) < 0.035
    d = np.where(louv & (x > 1.0) & (x < 2.0) & (y < 0.45) & (z > 0.84), np.maximum(d, -(d + 0.02)), d)

    # wheel arches (squared off a little)
    for wx, _ in WHEELS:
        arch = np.minimum(cyl_y(ps, np.array([wx, 0.98, WR]), WR + 0.1, 0.3),
                          box(ps, [wx, 0.98, WR - 0.2], [WR + 0.1, 0.3, 0.2]))
        d = np.maximum(d, -arch)

    # door openings revealed as the doors lift
    if door > 0.05:
        d = np.maximum(d, -box(ps, [-0.25, 1.02, 0.78], [0.6, 0.22, 0.22]))

    # rear wing (SVJ style) on two struts
    wing = box(ps, [2.12, 0, 1.1], [0.2, 0.98, 0.022])
    plate = box(ps, [2.12, 0.98, 1.04], [0.2, 0.02, 0.09])           # end plates
    strut = box(ps, [2.05, 0.42, 1.0], [0.05, 0.02, 0.1])
    d = np.minimum(d, np.minimum(np.minimum(wing, plate), strut))

    # twin hexagon-ish central exhausts, mounted high
    exh = cyl_x(ps, np.array([2.3, 0.13, 0.66]), 0.075, 0.08)
    d = np.maximum(d, -cyl_x(ps, np.array([2.4, 0.13, 0.66]), 0.055, 0.12))
    d = np.minimum(d, exh)

    mat = np.zeros(len(p))

    # scissor doors: hinge at the front of the door, swing up ~70°
    hinge = np.array([-0.85, 0.99, 0.76])
    pd = rot_xz(ps, hinge, -door * math.radians(70))
    dr = rbox(pd, [-0.25, 0.99, 0.76], [0.6, 0.035, 0.25], 0.03)
    dr = np.maximum(dr, plane(pd, [0.0, 0, 1], 1.0))                 # sloped top edge
    is_door = dr < d
    d = np.minimum(d, dr)

    # tyres + rims (rear tyres wider)
    tyre = np.full(len(p), 9.0)
    rim = np.full(len(p), 9.0)
    for (wx, wy), hw in zip(WHEELS, (0.15, 0.19)):
        tyre = np.minimum(tyre, cyl_y(ps, np.array([wx, wy, WR]), WR, hw) - 0.02)
        rim = np.minimum(rim, cyl_y(ps, np.array([wx, wy + 0.01, WR]), WR * 0.64, hw + 0.002))
    mat = np.where(tyre < d, 1, mat)
    d = np.minimum(d, tyre)
    mat = np.where(rim <= d + 1e-3, 3, mat)
    d = np.minimum(d, rim)

    # materials by region
    glass = (z > 0.84) & (x > -1.05) & (x < 0.95) & ~is_door
    mat = np.where((mat == 0) & glass, 2, mat)
    # Y-shaped headlights: two slanted strokes meeting near the nose corner
    hx, hy = x + 2.0, y - 0.66
    head = (z > 0.42) & (z < 0.64) & (
        ((hx < 0) & (hx > -0.38) & (np.abs(np.abs(hy) + hx * 0.55) < 0.045)) |      # two arms toward the nose
        ((hx >= 0) & (hx < 0.22) & (np.abs(hy) < 0.04)))                            # stem
    # Y-shaped tail lights across the rear face
    tx, ty = z - 0.7, y - 0.7
    tail = (x > 2.2) & (y > 0.42) & (y < 1.0) & (
        ((ty >= 0) & (np.abs(np.abs(tx) - ty * 0.55) < 0.035)) |                    # arms opening outward
        ((ty < 0) & (np.abs(tx) < 0.03)))                                           # stem toward centre
    mat = np.where((mat == 0) & (head | tail), 4, mat)
    vents = (mat == 0) & (x > 0.42) & (x < 1.24) & (y > 0.86) & (z > 0.42) & (z < 0.75)
    mat = np.where(vents, 5, mat)
    return d, mat


# ------------------------------------------------------------------ renderer
def normals(p, door):
    e = 0.004
    n = np.stack([car(p + v, door)[0] - car(p - v, door)[0]
                  for v in np.eye(3) * e], -1)
    return n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9)


def march(ro, rd, door, steps=110, far=16):
    t = np.zeros(len(rd))
    hit = np.zeros(len(rd), bool)
    alive = np.ones(len(rd), bool)
    for _ in range(steps):
        idx = np.where(alive)[0]
        if not len(idx):
            break
        d, _ = car(ro[idx] + rd[idx] * t[idx, None], door)
        t[idx] += d * 0.9
        h = d < 0.002
        hit[idx[h]] = True
        alive[idx[h | (t[idx] > far)]] = False
    return t, hit


def render(angle, door):
    """brightness grid (ROWS x COLS), NaN = empty; ground grid encoded as negative values."""
    elev = math.radians(17)
    dist = 7.1
    target = np.array([0.0, 0, 0.48])
    ro = target + dist * np.array([math.cos(angle) * math.cos(elev), math.sin(angle) * math.cos(elev), math.sin(elev)])
    fwd = (target - ro) / np.linalg.norm(target - ro)
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)

    xs = (np.arange(COLS) - COLS / 2 + 0.5) / COLS
    ys = (np.arange(ROWS) - ROWS / 2 + 0.5) / ROWS * (ROWS * LH) / (COLS * CW)
    gx, gy = np.meshgrid(xs, -ys)
    fov = 0.82
    rd = fwd + (gx[..., None] * right + gy[..., None] * up) * fov
    rd = (rd / np.linalg.norm(rd, axis=-1, keepdims=True)).reshape(-1, 3)
    ro_all = np.broadcast_to(ro, rd.shape)

    t, hit = march(ro_all, rd, door)
    out = np.full(len(rd), np.nan)
    light = np.array([-0.4, 0.55, 0.75]); light /= np.linalg.norm(light)

    if hit.any():
        p = ro_all[hit] + rd[hit] * t[hit, None]
        n = normals(p, door)
        _, mat = car(p, door)
        diff = np.clip(n @ light, 0, 1)
        h = light - rd[hit]; h /= np.linalg.norm(h, axis=-1, keepdims=True)
        spec = np.clip((n * h).sum(-1), 0, 1) ** 24
        rim = (1 - np.clip(-(n * rd[hit]).sum(-1), 0, 1)) ** 2.5
        b = 0.16 + 0.62 * diff + 0.55 * spec + 0.35 * rim
        b = np.where(mat == 1, 0.1 + 0.25 * diff + 0.3 * rim, b)        # tyres
        b = np.where(mat == 4, 1.0, b)                                       # lights glow
        b = np.where(mat == 5, 0.06 + 0.2 * diff, b)                         # dark intakes
        b = np.where(mat == 3, 0.3 + 0.5 * diff + 0.8 * spec, b)          # rims
        b = np.where(mat == 2, 0.12 + 0.3 * diff + 0.9 * spec + 0.2 * rim, b)  # glass
        out[hit] = np.clip(b, 0.02, 1)

    # synthwave ground grid with a soft car shadow
    miss = ~hit & (rd[:, 2] < -1e-3)
    tg = -ro_all[miss, 2] / rd[miss, 2]
    g = ro_all[miss] + rd[miss] * tg[:, None]
    r = np.hypot(g[:, 0], g[:, 1] * 1.3)
    line = (np.abs(((g[:, 0] + 0.5) % 1.0) - 0.5) < 0.05) | (np.abs(((g[:, 1] + 0.5) % 1.0) - 0.5) < 0.07)
    shadow = np.exp(-((g[:, 0] / 2.6) ** 2 + (g[:, 1] / 1.25) ** 2) ** 2)
    fade = np.clip(1 - r / 3.6, 0, 1)
    gv = np.where(line & (fade > 0.05), 0.55 * fade, np.nan)
    gv = np.where(shadow > 0.35, np.nan, gv)
    sh = np.where((shadow > 0.35) & (shadow < 0.9), -0.01, np.nan)       # shadow = dim dots
    val = np.where(np.isnan(gv), sh, -gv - 0.02)
    out_m = out[miss]
    out_m[~np.isnan(val)] = val[~np.isnan(val)]
    out[miss] = out_m
    return out.reshape(ROWS, COLS)


# ------------------------------------------------------------------ SVG
def frame_svg(grid, i, x0, y0, rng, levels):
    car_rows, grid_rows = [], []
    for r in range(ROWS):
        lines = [[" "] * COLS for _ in LEVELS]
        gl = [" "] * COLS
        for c in range(COLS):
            v = grid[r, c]
            if np.isnan(v):
                continue
            if v < 0:                                       # ground
                gl[c] = "·" if v > -0.015 else ("+" if -v > 0.3 else "·")
                continue
            lvl = min(int(v * len(LEVELS)), len(LEVELS) - 1)
            lines[lvl][c] = "1" if rng.random() < 0.25 + 0.6 * v else "0"
        y = y0 + r * LH
        for lvl, chars in enumerate(lines):
            s = "".join(chars)
            if s.strip():
                lead = len(s) - len(s.lstrip())
                s = s.strip()
                car_rows.append(f'<text x="{x0 + lead * CW:.1f}" y="{y:.1f}" textLength="{len(s) * CW:.1f}" fill-opacity="{levels[lvl]}">{s}</text>')
        s = "".join(gl)
        if s.strip():
            lead = len(s) - len(s.lstrip())
            s = s.strip()
            grid_rows.append(f'<text x="{x0 + lead * CW:.1f}" y="{y:.1f}" textLength="{len(s) * CW:.1f}">{esc(s)}</text>')
    delay = i * LOOP / FRAMES
    return (f'<g class="f" style="animation-delay:{delay:.3f}s">'
            f'<g class="gr">{"".join(grid_rows)}</g><g fill="url(#cg)">{"".join(car_rows)}</g></g>')


SPECS = [
    ("MODEL", "Aventador SVJ"), ("ENGINE", "6.5L V12, NA"), ("POWER", "770 CV"),
    ("0-100", "2.8 s"), ("TOP", "350+ km/h"), ("DOORS", "scissor"),
]


def build(theme, frames):
    t = THEMES[theme]
    pad, top = 26, 34 + 16
    cw_px, ch_px = COLS * CW, ROWS * LH
    panel_x = pad + cw_px + 20
    width = round(panel_x + 300 + pad)
    height = round(top + ch_px + pad)
    rng = random.Random(3)
    levels = LEVELS if theme == "dark" else [round(0.3 + 0.7 * v, 2) for v in LEVELS]
    frames_svg = "\n".join(frame_svg(g, i, pad, top + FONT, rng, levels) for i, g in enumerate(frames))
    pct = 100 / FRAMES
    g0, g1, g2 = t["car"]

    rows = []
    y = top + 30
    rows.append(f'<text x="{panel_x}" y="{y}" class="hd">garage.exe</text>')
    y += 14
    rows.append(f'<line x1="{panel_x}" x2="{panel_x + 290}" y1="{y}" y2="{y}" stroke="{t["border"]}"/>')
    y += 30
    for k, v in SPECS:
        rows.append(f'<text x="{panel_x}" y="{y}" class="sk">{k}</text><text x="{panel_x + 290}" y="{y}" class="sv" text-anchor="end">{esc(v)}</text>')
        y += 30
    y += 10
    rows.append(f'<text x="{panel_x}" y="{y}" class="sk">RENDER</text>'
                f'<text x="{panel_x + 290}" y="{y}" class="sv" text-anchor="end">{FRAMES} frames · raymarched</text>')
    y += 34
    # rev counter bar that sweeps with the rotation
    rows.append(f'<rect x="{panel_x}" y="{y}" width="290" height="8" rx="4" fill="{t["tile"]}"/>'
                f'<rect class="rev" x="{panel_x}" y="{y}" width="290" height="8" rx="4" fill="url(#cg2)"/>')
    y += 28
    rows.append(f'<text x="{panel_x}" y="{y}" class="dim">dream garage · loading…</text>')

    defs = f'''
  <linearGradient id="cg" gradientUnits="userSpaceOnUse" x1="{pad}" y1="{top}" x2="{pad + cw_px}" y2="{top + ch_px}">
    <stop offset="0" stop-color="{g0}"/><stop offset="0.5" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/>
  </linearGradient>
  <linearGradient id="cg2"><stop offset="0" stop-color="{g0}"/><stop offset="1" stop-color="{g2}"/></linearGradient>
  <filter id="glow" x="-5%" y="-5%" width="110%" height="110%">
    <feGaussianBlur stdDeviation="1.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>'''
    style = f'''
  .f {{ opacity: 0; animation: fr {LOOP}s step-end infinite; }}
  @keyframes fr {{ 0% {{ opacity: 1; }} {pct:.3f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
  .gr {{ fill: {t["grid"]}; fill-opacity: .45; }}
  .hd {{ font-size: 18px; font-weight: 700; fill: {t["accent"]}; }}
  .sk {{ font-size: 13px; fill: {t["key"]}; letter-spacing: 1px; }}
  .sv {{ font-size: 13px; fill: {t["value"]}; }}
  .dim {{ font-size: 12px; fill: {t["muted"]}; }}
  .rev {{ transform-box: fill-box; transform-origin: left; animation: rev {LOOP}s ease-in-out infinite; }}
  @keyframes rev {{ 0% {{ transform: scaleX(.05); }} 50% {{ transform: scaleX(1); }} 100% {{ transform: scaleX(.05); }} }}'''
    body = f'''
  <g font-size="{FONT}px" font-weight="700">
{frames_svg}
  </g>
  {"".join(rows)}'''
    return window(theme, width, height, "garage — aventador.bin — rotating", body, defs, style)


def main():
    frames = []
    for i in range(FRAMES):
        ang = math.radians(215) + 2 * math.pi * i / FRAMES
        door = 0.5 - 0.5 * math.cos(2 * math.pi * i / FRAMES)    # closed -> open -> closed
        door = min(1, door * 1.5)
        frames.append(render(ang, door))
        print(f"\rframe {i + 1}/{FRAMES}", end="", flush=True)
    print()
    for theme in THEMES:
        path = ROOT / f"car_{theme}.svg"
        path.write_text(build(theme, frames))
        print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
