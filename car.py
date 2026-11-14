#!/usr/bin/env python3
"""
Garage card: a Lamborghini Aventador rendered in amber binary from two photos.

Doors-down and doors-up shots from nearly the same angle are rendered like the portrait
(brightness -> how bright each 0/1 is, edges boosted). The card cuts between them like a
CRT channel switch, so the doors appear to open and close. In the doors-down view the
headlights glow in the Aventador's Y-shaped daytime-running-light pattern.
Only a few instant switches per cycle, so the image is not redrawn constantly.
Writes car_dark.svg.   Run: python car.py
(car_closed.png / car.png = background-removed photos, see tools/subject_cutout.swift)
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from common import HEADER, PHOSPHOR, ROOT, THEMES, esc, window

COLS = 228
FONT = 5.0
CW, LH = FONT * 0.6, FONT * 1.1
LEVELS = [0.2, 0.34, 0.5, 0.68, 0.85, 1.0]
LOOP = 12.0                     # seconds: doors down, then doors up
T_OPEN = 6.5                    # when the cut to doors-up happens

# Y-shaped DRL in car_closed.png pixel coordinates: (stem start, junction, arm A end, arm B end)
DRL = [
    [(1000, 693), (1150, 729), (1255, 757), (1196, 794)],   # near headlight
    [(1833, 666), (1859, 710), (1906, 758), (1815, 722)],   # far headlight
]


def photo_grid(name, cols):
    img = Image.open(ROOT / name).convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    img = img.crop(bbox)
    rows = round(cols * img.height / img.width * CW / LH)
    img = img.filter(ImageFilter.UnsharpMask(radius=max(2, img.width // 180), percent=160, threshold=0))
    a = np.asarray(img.resize((cols, rows), Image.LANCZOS), dtype=float) / 255
    lum = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    fg = a[..., 3] > 0.45
    tone = np.clip((lum - 0.04) / 0.72, 0, 1) ** 1.25
    gx = np.zeros_like(lum); gy = np.zeros_like(lum)
    gx[:, 1:-1] = lum[:, 2:] - lum[:, :-2]
    gy[1:-1, :] = lum[2:, :] - lum[:-2, :]
    mag = np.hypot(gx, gy)
    edge = mag > np.percentile(mag[fg], 90)
    sil = fg & ~(np.roll(fg, 1, 0) & np.roll(fg, -1, 0) & np.roll(fg, 1, 1) & np.roll(fg, -1, 1))
    v = 0.08 + 0.8 * tone
    v = np.where(edge | sil, 1.0, v)
    v = np.where((tone < 0.06) & ~(edge | sil), np.nan, v)
    return np.where(fg, v, np.nan), bbox


def binary_svg(grid, x0, y0):
    rows, cols = grid.shape
    out = []
    for r in range(rows):
        lines = [[" "] * cols for _ in LEVELS]
        for c in range(cols):
            v = grid[r, c]
            if np.isnan(v):
                continue
            lvl = min(int(v * len(LEVELS)), len(LEVELS) - 1)
            lines[lvl][c] = "1" if (r * 7919 + c * 104729) % 100 < 30 + 50 * v else "0"
        for lvl, chars in enumerate(lines):
            s = "".join(chars)
            if s.strip():
                lead = len(s) - len(s.lstrip())
                s = s.strip()
                out.append(f'<text x="{x0 + lead * CW:.1f}" y="{y0 + r * LH:.1f}" textLength="{len(s) * CW:.1f}" fill-opacity="{LEVELS[lvl]}">{s}</text>')
    return "".join(out)


def drl_svg(bbox, rows, x0, y0):
    """Y-shaped light strips drawn as glowing vector strokes over the binary car."""
    bx, by, bx1, by1 = bbox
    sx, sy = COLS * CW / (bx1 - bx), rows * LH / (by1 - by)
    pt = lambda p: (x0 + (p[0] - bx) * sx, y0 + (p[1] - by) * sy - FONT * 0.6)
    paths, glows = [], []
    for stem, j, a, b in DRL:
        s, j, a, b = map(pt, (stem, j, a, b))
        d = f"M{s[0]:.1f} {s[1]:.1f}L{j[0]:.1f} {j[1]:.1f}L{a[0]:.1f} {a[1]:.1f}M{j[0]:.1f} {j[1]:.1f}L{b[0]:.1f} {b[1]:.1f}"
        length = math.dist(s, j) + math.dist(j, a) + math.dist(j, b)
        size = max(math.dist(s, a), 8)
        glows.append(f'<ellipse cx="{j[0]:.1f}" cy="{j[1]:.1f}" rx="{size * 0.75:.1f}" ry="{size * 0.4:.1f}" fill="url(#drlglow)"/>')
        for w, op in [(7, .22), (3.4, .55), (1.4, 1)]:
            paths.append(f'<path class="drl" d="{d}" stroke="#fff7e8" stroke-opacity="{op}" stroke-width="{w}" '
                         f'stroke-linecap="round" stroke-linejoin="round" fill="none" style="stroke-dasharray:{length:.0f};stroke-dashoffset:{length:.0f}"/>')
    return f'<g class="drlg">{"".join(glows)}</g>{"".join(paths)}'


SPECS = [("MODEL", "Aventador LP 700-4"), ("ENGINE", "6.5L V12 · NA"), ("POWER", "700 CV"),
         ("0-100", "2.9 s"), ("VMAX", "350 km/h"), ("DOORS", "scissor ▲▼")]


def build():
    t = THEMES["dark"]
    amber = PHOSPHOR["car"]
    g0, g1, g2 = t["car"]
    closed, cbox = photo_grid("car_closed.png", COLS)
    opened, _ = photo_grid("car.png", round(COLS * 0.86))
    pad, top = 26, HEADER + 14
    cw_px = COLS * CW
    ch_px = max(closed.shape[0], opened.shape[0]) * LH
    base = top + FONT + ch_px                               # shared floor line
    yc = base - closed.shape[0] * LH
    yo = base - opened.shape[0] * LH
    xo = pad + (cw_px - opened.shape[1] * CW) / 2
    px = pad + cw_px + 30
    width = round(px + 280 + 30)
    height = round(top + ch_px + 34)

    panel = [f'<text x="{px}" y="{top + 30}" class="hd">GARAGE.EXE</text>',
             f'<text x="{px}" y="{top + 50}" class="dim">dream_car = load("aventador.bin")</text>']
    y = top + 88
    for k, v in SPECS:
        panel.append(f'<text x="{px}" y="{y}" class="sk">{k}</text>'
                     f'<text x="{px + 280}" y="{y}" class="sv" text-anchor="end">{esc(v)}</text>'
                     f'<line x1="{px}" x2="{px + 280}" y1="{y + 9}" y2="{y + 9}" stroke="{t["rule"]}"/>')
        y += 30
    y += 16
    panel.append(f'<text x="{px}" y="{y}" class="sk">CAM</text>'
                 f'<text x="{px + 280}" y="{y}" class="sv vd" text-anchor="end">DOORS DOWN · DRL ON</text>'
                 f'<text x="{px + 280}" y="{y}" class="sv vu" text-anchor="end">DOORS UP</text>')

    p_open = 100 * T_OPEN / LOOP
    glitch = 0.18 / LOOP * 100
    defs = (f'<linearGradient id="cg" gradientUnits="userSpaceOnUse" x1="{pad}" y1="{top}" x2="{pad + cw_px}" y2="{top + ch_px}">'
            f'<stop offset="0" stop-color="{g0}"/><stop offset=".55" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient>'
            f'<radialGradient id="floor"><stop offset="0" stop-color="{g1}" stop-opacity=".18"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="drlglow"><stop offset="0" stop-color="#fff7e8" stop-opacity=".55"/><stop offset=".5" stop-color="{g2}" stop-opacity=".18"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></radialGradient>'
            f'<pattern id="static" width="6" height="4" patternUnits="userSpaceOnUse"><rect width="3" height="1" fill="{g2}" opacity=".5"/><rect x="3" y="2" width="2" height="1" fill="{g1}" opacity=".35"/></pattern>')
    style = f'''
  .vdown {{ animation: vdown {LOOP}s step-end infinite; }}
  .vup {{ opacity: 0; animation: vup {LOOP}s step-end infinite; }}
  @keyframes vdown {{ 0% {{ opacity: 1; }} {p_open:.3f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
  @keyframes vup {{ 0% {{ opacity: 0; }} {p_open:.3f}% {{ opacity: 1; }} 100% {{ opacity: 1; }} }}
  .vd {{ animation: vdown {LOOP}s step-end infinite; }} .vu {{ opacity: 0; animation: vup {LOOP}s step-end infinite; }}
  .cut {{ opacity: 0; animation: cut {LOOP}s step-end infinite; }}
  @keyframes cut {{ 0% {{ opacity: .9; }} {glitch:.3f}% {{ opacity: 0; }} {p_open:.3f}% {{ opacity: .9; }} {p_open + glitch:.3f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
  .drl {{ animation: drl {LOOP}s linear infinite; }}
  @keyframes drl {{ 0%, 6% {{ stroke-dashoffset: var(--l, 999); }} 14%, 100% {{ stroke-dashoffset: 0; }} }}
  .drlg {{ opacity: 0; animation: drlg {LOOP}s step-end infinite; }}
  @keyframes drlg {{ 0% {{ opacity: 0; }} 14% {{ opacity: 1; }} 100% {{ opacity: 1; }} }}
  .hd {{ font-size: 20px; font-weight: 700; fill: {amber}; letter-spacing: 3px; }}
  .sk {{ font-size: 12px; fill: {t["muted"]}; letter-spacing: 2px; }}
  .sv {{ font-size: 13px; fill: {g2}; font-weight: 700; }}
  .dim {{ font-size: 11px; fill: {t["muted"]}; }}'''
    body = f'''
  <ellipse cx="{pad + cw_px * 0.5:.0f}" cy="{base - 6:.0f}" rx="{cw_px * 0.55:.0f}" ry="{ch_px * 0.13:.0f}" fill="url(#floor)"/>
  <g font-size="{FONT}px" font-weight="700" fill="url(#cg)">
    <g class="vdown">{binary_svg(closed, pad, yc)}{drl_svg(cbox, closed.shape[0], pad, yc)}</g>
    <g class="vup">{binary_svg(opened, xo, yo)}</g>
  </g>
  <rect class="cut" x="{pad - 10}" y="{top - 6}" width="{cw_px + 20:.0f}" height="{ch_px + 20:.0f}" fill="url(#static)"/>
  {"".join(panel)}'''
    return window("dark", width, height, "GARAGE // AVENTADOR.BIN", body, defs, style,
                  accent=amber, tag="CRT-02 · P3 AMBER")


def main():
    svg = build()
    # each DRL path animates from its own length to 0
    import re
    svg = re.sub(r'style="stroke-dasharray:(\d+);stroke-dashoffset:\1"', r'style="stroke-dasharray:\1;--l:\1"', svg)
    path = ROOT / "car_dark.svg"
    path.write_text(svg)
    print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
