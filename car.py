#!/usr/bin/env python3
"""
Garage card: a Lamborghini Aventador (scissor doors up) rendered in amber binary.

Brightness picks how bright each 0/1 is and photo edges are boosted. The headlights glow
softly in the Aventador's Y-shaped daytime-running-light pattern: blurred light, not lines.
They switch on once after load, then the card is completely still. Writes car_dark.svg.
Run: python car.py   (car.png = background-removed photo, see tools/subject_cutout.swift)
"""
import math

import numpy as np
from PIL import Image, ImageFilter

from common import HEADER, PHOSPHOR, ROOT, THEMES, esc, window

COLS = 228
FONT = 5.0
CW, LH = FONT * 0.6, FONT * 1.1
LEVELS = [0.2, 0.34, 0.5, 0.68, 0.85, 1.0]

# Y-shaped DRL in car.png pixel coordinates: (stem start, junction, arm A end, arm B end)
DRL = [
    [(416, 314), (482, 335), (507, 347), (480, 354)],   # near headlight
    [(641, 283), (662, 301), (681, 316), (650, 310)],   # far headlight
]
LAMP_POLY = [   # headlight housings in car.png pixels (whole lens glows faintly)
    [(410, 311), (470, 326), (507, 338), (509, 349), (489, 357), (452, 349)],
    [(638, 279), (660, 292), (683, 312), (679, 321), (660, 312), (642, 292)],
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


def rows_svg(grid, x0, y0):
    """binary_svg, but one group per row so the car scans in once on load."""
    rows, cols = grid.shape
    out = []
    for r in range(rows):
        row = binary_svg(grid[r:r + 1], x0, y0 + r * LH, r0=r)
        if row:
            out.append(f'<g class="cr" style="animation-delay:{r * 0.022:.3f}s">{row}</g>')
    return "\n".join(out)


def binary_svg(grid, x0, y0, r0=0):
    rows, cols = grid.shape
    out = []
    for r in range(rows):
        lines = [[" "] * cols for _ in LEVELS]
        for c in range(cols):
            v = grid[r, c]
            if np.isnan(v):
                continue
            lvl = min(int(v * len(LEVELS)), len(LEVELS) - 1)
            lines[lvl][c] = "1" if ((r + r0) * 7919 + c * 104729) % 100 < 30 + 50 * v else "0"
        for lvl, chars in enumerate(lines):
            s = "".join(chars)
            if s.strip():
                lead = len(s) - len(s.lstrip())
                s = s.strip()
                out.append(f'<text x="{x0 + lead * CW:.1f}" y="{y0 + r * LH:.1f}" textLength="{len(s) * CW:.1f}" fill-opacity="{LEVELS[lvl]}">{s}</text>')
    return "".join(out)


def drl_svg(bbox, rows, x0, y0):
    """Y-shaped light strips as soft, blurred light over the binary car."""
    bx, by, bx1, by1 = bbox
    cols = COLS
    sx, sy = cols * CW / (bx1 - bx), rows * LH / (by1 - by)
    pt = lambda p: (x0 + (p[0] - bx) * sx, y0 + (p[1] - by) * sy - FONT * 0.6)
    halos, strokes = [], []
    for stem, j, a, b in DRL:
        s, j, a, b = map(pt, (stem, j, a, b))
        d = f"M{s[0]:.1f} {s[1]:.1f}L{j[0]:.1f} {j[1]:.1f}L{a[0]:.1f} {a[1]:.1f}M{j[0]:.1f} {j[1]:.1f}L{b[0]:.1f} {b[1]:.1f}"
        size = max(math.dist(s, a), 10)
        mx, my = (s[0] + a[0]) / 2, (s[1] + a[1]) / 2
        halos.append(f'<ellipse cx="{mx:.1f}" cy="{my:.1f}" rx="{size * 0.75:.1f}" ry="{size * 0.42:.1f}" fill="url(#drlglow)"/>')
        strokes.append((d, size))
    lenses = "".join('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in map(pt, poly)) + '"/>' for poly in LAMP_POLY)
    wide = "".join(f'<path d="{d}" stroke="#fff3dc" stroke-width="{max(8, z * 0.2):.1f}" stroke-opacity=".75"/>' for d, z in strokes)
    mid = "".join(f'<path d="{d}" stroke="#fffaf0" stroke-width="{max(3.6, z * 0.08):.1f}" stroke-opacity=".9"/>' for d, z in strokes)
    core = "".join(f'<path d="{d}" stroke="#ffffff" stroke-width="1.8" stroke-opacity=".95"/>' for d, z in strokes)
    common = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    return (f'<g class="lights">{"".join(halos)}'
            f'<g fill="#fff3dc" fill-opacity=".38" filter="url(#blurM)">{lenses}</g>'
            f'<g {common} filter="url(#blurW)">{wide}</g>'
            f'<g {common} filter="url(#blurM)">{mid}</g>'
            f'<g {common} filter="url(#blurC)">{core}</g></g>')


SPECS = [("MODEL", "Aventador LP 700-4"), ("ENGINE", "6.5L V12 · NA"), ("POWER", "700 CV"),
         ("0-100", "2.9 s"), ("VMAX", "350 km/h"), ("DOORS", "scissor ▲")]


def build():
    t = THEMES["dark"]
    amber = PHOSPHOR["car"]
    g0, g1, g2 = t["car"]
    grid, bbox = photo_grid("car.png", COLS)
    rows = grid.shape[0]
    pad, top = 26, HEADER + 14
    cw_px, ch_px = COLS * CW, rows * LH
    y0 = top + FONT
    px = pad + cw_px + 30
    width = round(px + 280 + 30)
    height = round(top + ch_px + 30)

    panel = [f'<text x="{px}" y="{top + 30}" class="hd">GARAGE.EXE</text>',
             f'<text x="{px}" y="{top + 50}" class="dim">dream_car = load("aventador.bin")</text>']
    y = top + 88
    for k, v in SPECS:
        panel.append(f'<text x="{px}" y="{y}" class="sk">{k}</text>'
                     f'<text x="{px + 280}" y="{y}" class="sv" text-anchor="end">{esc(v)}</text>'
                     f'<line x1="{px}" x2="{px + 280}" y1="{y + 9}" y2="{y + 9}" stroke="{t["rule"]}"/>')
        y += 30
    y += 16
    panel.append(f'<text x="{px}" y="{y}" class="sk">LIGHTS</text>'
                 f'<text x="{px + 280}" y="{y}" class="sv" text-anchor="end">Y-DRL · ON</text>')

    defs = (f'<linearGradient id="cg" gradientUnits="userSpaceOnUse" x1="{pad}" y1="{top}" x2="{pad + cw_px}" y2="{top + ch_px}">'
            f'<stop offset="0" stop-color="{g0}"/><stop offset=".55" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient>'
            f'<radialGradient id="floor"><stop offset="0" stop-color="{g1}" stop-opacity=".18"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="drlglow"><stop offset="0" stop-color="#fff3dc" stop-opacity=".5"/><stop offset=".45" stop-color="{g2}" stop-opacity=".2"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></radialGradient>'
            '<filter id="blurW" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6"/></filter>'
            '<filter id="blurM" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.4"/></filter>'
            '<filter id="blurC" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation=".9"/></filter>')
    style = f'''
  .cr {{ opacity: 0; animation: in .45s ease-out forwards; }}
  @keyframes in {{ to {{ opacity: 1; }} }}
  .lights {{ opacity: 0; animation: lightson .9s ease-out 2.2s forwards; }}
  @keyframes lightson {{ 0% {{ opacity: 0; }} 20% {{ opacity: .6; }} 30% {{ opacity: .25; }} 100% {{ opacity: 1; }} }}
  .hd {{ font-size: 20px; font-weight: 700; fill: {amber}; letter-spacing: 3px; }}
  .sk {{ font-size: 12px; fill: {t["muted"]}; letter-spacing: 2px; }}
  .sv {{ font-size: 13px; fill: {g2}; font-weight: 700; }}
  .dim {{ font-size: 11px; fill: {t["muted"]}; }}'''
    body = f'''
  <ellipse cx="{pad + cw_px * 0.5:.0f}" cy="{top + ch_px * 0.93:.0f}" rx="{cw_px * 0.55:.0f}" ry="{ch_px * 0.12:.0f}" fill="url(#floor)"/>
  <g font-size="{FONT}px" font-weight="700" fill="url(#cg)">
{rows_svg(grid, pad, y0)}
  </g>
  {drl_svg(bbox, rows, pad, y0)}
  {"".join(panel)}'''
    return window("dark", width, height, "GARAGE // AVENTADOR.BIN", body, defs, style,
                  accent=amber, tag="CRT-02 · P3 AMBER")


def main():
    path = ROOT / "car_dark.svg"
    path.write_text(build())
    print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
