#!/usr/bin/env python3
"""
Garage card: an Aventador-style wedge rendered in binary like an 80s vector display.

The car is an implicit 3D model (sharp facets, like the real thing) raymarched with numpy.
Panel edges and silhouettes glow brightest; faces are dim phosphor. It spins on a static
turntable while the scissor doors open and close. Writes car_dark.svg.
Run: python car.py
"""
import math
import random

import numpy as np

from common import HEADER, PHOSPHOR, ROOT, THEMES, esc, window

COLS, ROWS = 140, 50
FONT = 7.4
CW, LH = FONT * 0.6, FONT * 1.1
FRAMES = 96
LOOP = 9.6                       # seconds per revolution
ELEV, DIST, FOV = math.radians(16), 7.4, 0.8
TARGET = np.array([0.0, 0, 0.12])
EDGE, LIT, DIM = 1.0, 0.5, 0.22  # opacity tiers


# ------------------------------------------------------------------ shape helpers
def box(p, c, h):
    q = np.abs(p - c) - h
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(q.max(-1), 0)


def cyl_y(p, c, r, hw):
    q = p - c
    d = np.stack([np.hypot(q[:, 0], q[:, 2]) - r, np.abs(q[:, 1]) - hw], -1)
    return np.minimum(d.max(-1), 0) + np.linalg.norm(np.maximum(d, 0), axis=-1)


def hex2d(qx, qz, r):
    """hexagon with flat top/bottom (Aventador wheel arches are hexagonal)."""
    k = (-0.8660254, 0.5, 0.57735)
    ax, az = np.abs(qz), np.abs(qx)          # rotate 90° so a flat edge sits on top
    dot = np.minimum(k[0] * ax + k[1] * az, 0)
    ax, az = ax - 2 * dot * k[0], az - 2 * dot * k[1]
    ax = ax - np.clip(ax, -k[2] * r, k[2] * r)
    az = az - r
    return np.hypot(ax, az) * np.sign(az)


def rot_xz(p, pivot, ang):
    q = p - pivot
    c, s = math.cos(ang), math.sin(ang)
    return np.stack([c * q[:, 0] - s * q[:, 2], q[:, 1], s * q[:, 0] + c * q[:, 2]], -1) + pivot


# ------------------------------------------------------------------ the car
# x: nose (-) -> tail (+), y: side, z: up. ~4.8 m long, 2.1 m wide, 1.13 m tall.
ROOF_X = [-2.42, -2.25, -1.05, 0.15, 0.55, 1.15, 1.95, 2.4]
ROOF_Z = [0.40, 0.48, 0.70, 1.13, 1.13, 1.02, 0.92, 0.86]     # one unbroken wedge line nose->roof
PLAN_X = [-2.42, -2.15, -1.55, 1.55, 2.4]
PLAN_W = [0.52, 0.84, 1.0, 1.04, 0.94]
WHEELS = [(-1.45, 0.86, 0.15), (1.42, 0.88, 0.19)]
WR = 0.36


def side_w(x, z):
    w = np.interp(x, PLAN_X, PLAN_W)
    return w - np.maximum(0, z - 0.6) * 1.05 - np.maximum(0, 0.3 - z) * 0.7   # tumblehome + undercut


def car(p, door):
    """(distance-ish, material) material: 0 paint, 1 tyre, 2 glass, 3 rim, 4 light, 5 vent."""
    x, y, z = p[:, 0], np.abs(p[:, 1]), p[:, 2]
    ps = np.stack([x, y, z], -1)

    top = np.interp(x, ROOF_X, ROOF_Z)
    d = np.maximum.reduce([z - top, 0.14 - z, y - side_w(x, z), np.abs(x) - 2.42]) * 0.75

    for wx, _, _ in WHEELS:                                         # hexagonal arches
        d = np.maximum(d, -np.maximum(hex2d(x - wx, z - WR, WR + 0.12), 0.6 - y))
    intake = np.maximum(box(ps, [0.82, 1.08, 0.56], [0.36, 0.2, 0.2]),
                        0.3 * (x - 0.82) - (z - 0.56) - 0.05)          # wedge side intake
    d = np.maximum(d, -intake)
    d = np.maximum(d, -box(ps, [-2.3, 0.6, 0.27], [0.22, 0.26, 0.07]))  # front intakes
    if door > 0.05:                                                 # door aperture
        d = np.maximum(d, -box(ps, [-0.35, 1.05, 0.78], [0.62, 0.32, 0.26]))

    wing = np.minimum.reduce([box(ps, [2.2, 0, 1.08], [0.17, 0.95, 0.02]),    # SVJ wing
                              box(ps, [2.2, 0.95, 1.02], [0.18, 0.015, 0.08]),
                              box(ps, [2.12, 0.4, 0.98], [0.04, 0.02, 0.1])])
    d = np.minimum(d, wing)

    mat = np.zeros(len(p))
    hinge = np.array([-0.97, 0.98, 0.72])                          # scissor door
    pd = rot_xz(ps, hinge, -door * math.radians(72))
    panel = np.maximum.reduce([np.abs(pd[:, 1] - side_w(pd[:, 0], pd[:, 2]) + 0.02) - 0.03,
                               np.abs(pd[:, 0] + 0.35) - 0.62,
                               np.abs(pd[:, 2] - 0.78) - 0.27,
                               pd[:, 2] - np.interp(pd[:, 0], ROOF_X, ROOF_Z) + 0.02]) * 0.75
    is_door = panel < d
    d = np.minimum(d, panel)

    tyre = np.full(len(p), 9.0)
    rim = np.full(len(p), 9.0)
    for wx, wy, hw in WHEELS:
        tyre = np.minimum(tyre, cyl_y(ps, np.array([wx, wy, WR]), WR, hw))
        rim = np.minimum(rim, cyl_y(ps, np.array([wx, wy + 0.012, WR]), WR * 0.62, hw))
    mat = np.where(tyre < d, 1, mat)
    d = np.minimum(d, tyre)
    mat = np.where(rim <= d + 1e-3, 3, mat)
    d = np.minimum(d, rim)

    mat = np.where((z > 0.78) & (x > -1.0) & (x < 0.75) & ~is_door & (mat == 0), 2, mat)   # glass
    hx, hy = x + 2.05, y - 0.62
    head = (z > 0.4) & (z < 0.62) & (((hx < 0) & (hx > -0.35) & (np.abs(np.abs(hy) + hx * 0.6) < 0.05))
                                     | ((hx >= 0) & (hx < 0.22) & (np.abs(hy) < 0.045)))
    tx, ty = z - 0.68, y - 0.66
    tail = (x > 2.3) & (y > 0.4) & (((ty >= 0) & (np.abs(np.abs(tx) - ty * 0.55) < 0.04)) | ((ty < 0) & (np.abs(tx) < 0.035)))
    mat = np.where((mat == 0) & (head | tail), 4, mat)
    louvre = (x > 1.05) & (x < 1.9) & (y < 0.5) & (z > 0.85) & (np.abs(((x - 1.05) % 0.17) - 0.085) < 0.03)
    mat = np.where((mat == 0) & louvre, 5, mat)
    return d, mat


# ------------------------------------------------------------------ renderer
ASPECT = (ROWS * LH) / (COLS * CW)


def camera(angle):
    ro = TARGET + DIST * np.array([math.cos(angle) * math.cos(ELEV), math.sin(angle) * math.cos(ELEV), math.sin(ELEV)])
    fwd = (TARGET - ro) / np.linalg.norm(TARGET - ro)
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right)
    return ro, fwd, right, np.cross(right, fwd)


def project(pts, angle):
    """world points -> (col, row) cell coordinates (inverse of the ray setup)."""
    ro, fwd, right, up = camera(angle)
    v = pts - ro
    zc = v @ fwd
    gx = (v @ right) / zc / FOV
    gy = (v @ up) / zc / FOV
    return gx * COLS + COLS / 2 - 0.5, -gy / ASPECT * ROWS + ROWS / 2 - 0.5


def render(angle, door):
    """grid of opacity tiers (NaN = empty). Edges get the brightest tier."""
    ro, fwd, right, up = camera(angle)
    xs = (np.arange(COLS) - COLS / 2 + 0.5) / COLS
    ys = (np.arange(ROWS) - ROWS / 2 + 0.5) / ROWS * ASPECT
    gx, gy = np.meshgrid(xs, -ys)
    rd = fwd + (gx[..., None] * right + gy[..., None] * up) * FOV
    rd = (rd / np.linalg.norm(rd, axis=-1, keepdims=True)).reshape(-1, 3)
    n_rays = len(rd)

    t = np.zeros(n_rays)
    hit = np.zeros(n_rays, bool)
    alive = np.ones(n_rays, bool)
    for _ in range(180):
        idx = np.where(alive)[0]
        if not len(idx):
            break
        dd, _ = car(ro + rd[idx] * t[idx, None], door)
        t[idx] += np.maximum(dd, 0.003)
        h = dd < 0.003
        hit[idx[h]] = True
        alive[idx[h | (t[idx] > 14)]] = False

    val = np.full(n_rays, np.nan)
    nrm = np.zeros((n_rays, 3))
    mats = np.full(n_rays, -1.0)
    if hit.any():
        p = ro + rd[hit] * t[hit, None]
        n = np.stack([car(p + v, door)[0] - car(p - v, door)[0] for v in np.eye(3) * 0.004], -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-9
        _, m = car(p, door)
        light = np.array([-0.35, 0.5, 0.8]); light /= np.linalg.norm(light)
        diff = np.clip(n @ light, 0, 1)
        b = np.where(diff > 0.55, LIT, DIM)
        b = np.where(m == 4, EDGE, b)                       # lights glow
        b = np.where((m == 1) | (m == 5), np.nan, b)        # tyres / louvres = negative space
        b = np.where(m == 2, DIM, b)
        val[hit], nrm[hit], mats[hit] = b, n, m

    H = hit.reshape(ROWS, COLS)
    T = np.where(hit, t, 1e6).reshape(ROWS, COLS)
    N = nrm.reshape(ROWS, COLS, 3)
    M = mats.reshape(ROWS, COLS)
    edge = np.zeros_like(H)
    for k, (dy, dx) in enumerate([(0, 1), (1, 0), (0, -1), (-1, 0)]):
        sh = lambda A: np.roll(np.roll(A, dy, 0), dx, 1)
        Hn, Tn, Nn, Mn = sh(H), sh(T), sh(N), sh(M)
        edge |= H & ~Hn                                            # silhouette (all sides)
        if k < 2:                                                  # interior lines: one-sided -> 1 char thick
            both = H & Hn
            depth = np.abs(np.where(both, T - Tn, 0)) > 0.35
            crease = (N * Nn).sum(-1) < 0.55
            edge |= both & (depth | crease | ((Mn != M) & (np.minimum(M, Mn) != 0) | ((M == 2) ^ (Mn == 2))))
    V = val.reshape(ROWS, COLS)
    return np.where(edge, EDGE, V)


# ------------------------------------------------------------------ SVG
def frame_svg(V, i, x0, y0, rng):
    out = []
    for r in range(ROWS):
        tiers = {EDGE: [" "] * COLS, LIT: [" "] * COLS, DIM: [" "] * COLS}
        for c in range(COLS):
            v = V[r, c]
            if np.isnan(v):
                continue
            if v == DIM:
                tiers[v][c] = "·" if (r + c) % 2 == 0 else " "       # faint dotted faces
            elif v == LIT:
                tiers[v][c] = "·"                                     # lit faces: solid dots
            else:
                tiers[v][c] = "1" if rng.random() < 0.7 else "0"
        y = y0 + r * LH
        for v, chars in tiers.items():
            s = "".join(chars)
            if s.strip():
                lead = len(s) - len(s.lstrip())
                s = s.strip()
                out.append(f'<text x="{x0 + lead * CW:.1f}" y="{y:.1f}" textLength="{len(s) * CW:.1f}" class="t{int(v * 100)}">{s}</text>')
    return f'<g class="f" style="animation-delay:{i * LOOP / FRAMES:.3f}s">{"".join(out)}</g>'


def to_screen(c, r, x0, y0):
    return x0 + (c + 0.5) * CW, y0 + (r + 0.5) * LH - FONT * 0.8


def turntable(x0, y0):
    """rotation-invariant floor rings: drawn once, not per frame."""
    th = np.linspace(0, 2 * math.pi, 120)
    parts = []
    sh = np.stack([2.6 * np.cos(th), 1.25 * np.sin(th), np.zeros_like(th)], -1)
    c, r = project(sh, 0.0)
    parts.append('<polygon points="' + " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(*to_screen(c, r, x0, y0)))
                 + '" fill="#000" fill-opacity=".5"/>')
    for rad, op, dash in [(3.25, 0.3, "1 7"), (2.95, 0.55, "3 5"), (2.7, 0.9, "")]:
        pts = np.stack([rad * np.cos(th), rad * np.sin(th), np.zeros_like(th)], -1)
        c, r = project(pts, 0.0)
        poly = " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(*to_screen(c, r, x0, y0)))
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        parts.append(f'<polygon{extra} points="{poly}" fill="none" stroke="url(#cg)" stroke-opacity="{op}" stroke-width="1.2"/>')
    return "".join(parts)


SPECS = [("MODEL", "Aventador SVJ"), ("ENGINE", "6.5L V12 · NA"), ("POWER", "770 CV"),
         ("0-100", "2.8 s"), ("VMAX", "350+ km/h"), ("DOORS", "scissor ▲")]


def build(frames):
    t = THEMES["dark"]
    amber = PHOSPHOR["car"]
    g0, g1, g2 = t["car"]
    pad, top = 22, HEADER + 6
    cw_px, ch_px = COLS * CW, ROWS * LH
    px = pad + cw_px + 18
    width = round(px + 290 + 30)
    height = round(top + ch_px + 18)
    rng = random.Random(5)
    y0 = top + FONT
    frames_svg = "\n".join(frame_svg(V, i, pad, y0, rng) for i, V in enumerate(frames))

    panel = [f'<text x="{px}" y="{top + 34}" class="hd">GARAGE.EXE</text>',
             f'<text x="{px}" y="{top + 54}" class="dim">dream_car = load("aventador.bin")</text>']
    y = top + 92
    for k, v in SPECS:
        panel.append(f'<text x="{px}" y="{y}" class="sk">{k}</text>'
                     f'<text x="{px + 290}" y="{y}" class="sv" text-anchor="end">{esc(v)}</text>'
                     f'<line x1="{px}" x2="{px + 290}" y1="{y + 9}" y2="{y + 9}" stroke="{t["rule"]}"/>')
        y += 30
    y += 14
    panel.append("".join(
        f'<rect class="tach" x="{px + j * 12}" y="{y}" width="8" height="16" rx="1" '
        f'fill="{amber if j < 19 else "#ff3b30"}" style="animation-delay:{j * 0.06:.2f}s"/>' for j in range(24)))
    panel.append(f'<text x="{px}" y="{y + 38}" class="dim">RPM ×1000 · {LOOP:.0f}s/rev · {FRAMES} frames</text>')

    defs = f'<linearGradient id="cg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{g0}"/><stop offset=".5" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient>'
    pct = 100 / FRAMES
    style = f'''
  .f {{ opacity: 0; animation: fr {LOOP}s step-end infinite; }}
  @keyframes fr {{ 0% {{ opacity: 1; }} {pct:.3f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
  .t100 {{ fill: {g2}; }} .t50 {{ fill: {g2}; fill-opacity: .55; }} .t22 {{ fill: {g1}; fill-opacity: .45; }}
  .tach {{ opacity: .15; animation: rev {LOOP}s steps(1) infinite; }}
  @keyframes rev {{ 0%, 100% {{ opacity: .15; }} 25%, 75% {{ opacity: 1; }} }}
  .hd {{ font-size: 20px; font-weight: 700; fill: {amber}; letter-spacing: 3px; }}
  .sk {{ font-size: 12px; fill: {t["muted"]}; letter-spacing: 2px; }}
  .sv {{ font-size: 13px; fill: {g2}; font-weight: 700; }}
  .dim {{ font-size: 11px; fill: {t["muted"]}; }}'''
    body = f'''
  {turntable(pad, y0)}
  <g font-size="{FONT}px" font-weight="700">
{frames_svg}
  </g>
  {"".join(panel)}'''
    return window("dark", width, height, "GARAGE // AVENTADOR.BIN", body, defs, style,
                  accent=amber, tag="CRT-02 · P3 AMBER")


def main():
    frames = []
    for i in range(FRAMES):
        ang = math.radians(210) + 2 * math.pi * i / FRAMES
        door = min(1, (0.5 - 0.5 * math.cos(2 * math.pi * i / FRAMES)) * 1.6)
        frames.append(render(ang, door))
        print(f"\rframe {i + 1}/{FRAMES}", end="", flush=True)
    print()
    path = ROOT / "car_dark.svg"
    path.write_text(build(frames))
    print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
