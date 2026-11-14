#!/usr/bin/env python3
"""
Garage card: a photo of a Lamborghini Aventador rendered in amber binary.

Same idea as the portrait: brightness picks how bright each 0/1 is, and edges in the
photo are boosted so panel lines, intakes and the scissor doors read crisply.
It scans in once on load, then stays completely still. Writes car_dark.svg.
Run: python car.py          (car.png = background-removed photo, see tools/subject_cutout.swift)
"""
import numpy as np
from PIL import Image, ImageFilter

from common import HEADER, PHOSPHOR, ROOT, THEMES, esc, window

COLS = 228
FONT = 5.0
CW, LH = FONT * 0.6, FONT * 1.1
LEVELS = [0.2, 0.34, 0.5, 0.68, 0.85, 1.0]
LAMPS = [(405, 305, 512, 360), (632, 275, 685, 322)]   # headlight boxes in car.png pixels
LIGHT_LOOP = 8.0                                         # seconds per lights on/off cycle


def car_grid():
    img = Image.open(ROOT / "car.png").convert("RGBA")
    bbox = img.getchannel("A").getbbox()
    img = img.crop(bbox)
    rows = round(COLS * img.height / img.width * CW / LH)
    img = img.filter(ImageFilter.UnsharpMask(radius=4, percent=160, threshold=0))
    small = img.resize((COLS, rows), Image.LANCZOS)
    a = np.asarray(small, dtype=float) / 255
    lum = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    fg = a[..., 3] > 0.45
    tone = np.clip((lum - 0.04) / 0.72, 0, 1) ** 1.25                # keep the photo's real contrast
    # edges: Sobel on luminance, so outlines glow brightest
    gx = np.zeros_like(lum); gy = np.zeros_like(lum)
    gx[:, 1:-1] = lum[:, 2:] - lum[:, :-2]
    gy[1:-1, :] = lum[2:, :] - lum[:-2, :]
    mag = np.hypot(gx, gy)
    edge = mag > np.percentile(mag[fg], 90)
    sil = fg & ~(np.roll(fg, 1, 0) & np.roll(fg, -1, 0) & np.roll(fg, 1, 1) & np.roll(fg, -1, 1))
    v = 0.08 + 0.8 * tone
    v = np.where(edge | sil, 1.0, v)
    v = np.where((tone < 0.06) & ~(edge | sil), np.nan, v)          # black tyres / intakes = negative space
    # lamp cells: inside a headlight box and pale (low saturation, fairly bright)
    sat = a[..., :3].max(-1) - a[..., :3].min(-1)
    lamp = np.zeros_like(fg)
    sx, sy = COLS / img.width, rows / img.height
    for x0, y0, x1, y1 in LAMPS:
        c0, c1 = int((x0 - bbox[0]) * sx), int((x1 - bbox[0]) * sx) + 1
        r0, r1 = int((y0 - bbox[1]) * sy), int((y1 - bbox[1]) * sy) + 1
        box = np.zeros_like(fg); box[r0:r1, c0:c1] = True
        lamp |= box & fg & (sat < 0.32) & (lum > 0.28)
    v = np.where(lamp, LEVELS[1], v)                   # lights "off" in the base layer
    return np.where(fg, v, np.nan), lamp


def car_svg(grid, x0, y0):
    rows, cols = grid.shape
    out = []
    for r in range(rows):
        lines = [[" "] * cols for _ in LEVELS]
        for c in range(cols):
            v = grid[r, c]
            if np.isnan(v):
                continue
            lvl = min(int(v * len(LEVELS)), len(LEVELS) - 1)
            h = (r * 7919 + c * 104729) % 100
            lines[lvl][c] = "1" if h < 30 + 50 * v else "0"
        parts = []
        for lvl, chars in enumerate(lines):
            s = "".join(chars)
            if s.strip():
                lead = len(s) - len(s.lstrip())
                s = s.strip()
                parts.append(f'<text x="{x0 + lead * CW:.1f}" textLength="{len(s) * CW:.1f}" fill-opacity="{LEVELS[lvl]}">{s}</text>')
        if parts:
            out.append(f'<g class="cr" style="animation-delay:{r * 0.022:.3f}s" transform="translate(0 {y0 + r * LH:.1f})">{"".join(parts)}</g>')
    return "\n".join(out)


def lamp_svg(lamp, x0, y0):
    rows, cols = lamp.shape
    out, centres = [], []
    for r in range(rows):
        s = "".join(("1" if (r * 7919 + c * 104729) % 3 else "0") if lamp[r, c] else " " for c in range(cols))
        if s.strip():
            lead = len(s) - len(s.lstrip())
            s = s.strip()
            out.append(f'<text x="{x0 + lead * CW:.1f}" y="{y0 + r * LH:.1f}" textLength="{len(s) * CW:.1f}">{s}</text>')
    # glow + beam per lamp (connected blobs found by column split)
    ys, xs = np.nonzero(lamp)
    if len(xs):
        split = (xs.min() + xs.max()) / 2
        for side in (xs < split, xs >= split):
            if side.any():
                cx = x0 + xs[side].mean() * CW
                cy = y0 + ys[side].mean() * LH - FONT * 0.4
                w = (xs[side].max() - xs[side].min() + 1) * CW
                centres.append((cx, cy, w))
    glows = "".join(f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w * 0.9:.1f}" ry="{w * 0.45:.1f}" fill="url(#lampglow)"/>' for cx, cy, w in centres)
    beams = "".join(
        f'<polygon points="{cx:.1f},{cy - 3:.1f} {cx + w * 2.2:.1f},{cy - w * 0.55:.1f} {cx + w * 2.2:.1f},{cy + w * 0.9:.1f} {cx:.1f},{cy + 4:.1f}" fill="url(#beam)"/>'
        for cx, cy, w in centres)
    return f'<g class="lamp">{beams}{glows}<g class="lampc">{"".join(out)}</g></g>'


SPECS = [("MODEL", "Aventador LP 700-4"), ("ENGINE", "6.5L V12 · NA"), ("POWER", "700 CV"),
         ("0-100", "2.9 s"), ("VMAX", "350 km/h"), ("DOORS", "scissor ▲")]


def build(grid, lamp):
    t = THEMES["dark"]
    amber = PHOSPHOR["car"]
    g0, g1, g2 = t["car"]
    rows, cols = grid.shape
    pad, top = 26, HEADER + 14
    cw_px, ch_px = cols * CW, rows * LH
    px = pad + cw_px + 30
    width = round(px + 280 + 30)
    height = round(top + ch_px + 30)
    y0 = top + FONT

    panel = [f'<text x="{px}" y="{top + 30}" class="hd">GARAGE.EXE</text>',
             f'<text x="{px}" y="{top + 50}" class="dim">dream_car = load("aventador.bin")</text>']
    y = top + 88
    for k, v in SPECS:
        panel.append(f'<text x="{px}" y="{y}" class="sk">{k}</text>'
                     f'<text x="{px + 280}" y="{y}" class="sv" text-anchor="end">{esc(v)}</text>'
                     f'<line x1="{px}" x2="{px + 280}" y1="{y + 9}" y2="{y + 9}" stroke="{t["rule"]}"/>')
        y += 30
    y += 16
    panel.append("".join(f'<rect x="{px + j * 11.6:.1f}" y="{y}" width="7.6" height="14" rx="1" '
                         f'fill="{amber if j < 19 else "#ff3b30"}" fill-opacity="{1 if j < 15 else .15}"/>' for j in range(24)))
    panel.append(f'<text x="{px}" y="{y + 34}" class="dim">lights: auto · start-up flicker every {LIGHT_LOOP:.0f}s</text>')

    defs = (f'<linearGradient id="cg" gradientUnits="userSpaceOnUse" x1="{pad}" y1="{top}" x2="{pad + cw_px}" y2="{top + ch_px}">'
            f'<stop offset="0" stop-color="{g0}"/><stop offset=".55" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient>'
            f'<radialGradient id="lampglow"><stop offset="0" stop-color="#fff6dc" stop-opacity=".75"/><stop offset=".45" stop-color="{g2}" stop-opacity=".3"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="beam" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff6dc" stop-opacity=".2"/><stop offset="1" stop-color="{g2}" stop-opacity="0"/></linearGradient>'
            f'<radialGradient id="floor"><stop offset="0" stop-color="{g1}" stop-opacity=".18"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></radialGradient>')
    style = f'''
  .cr {{ opacity: 0; animation: in .45s ease-out forwards; }}
  @keyframes in {{ to {{ opacity: 1; }} }}
  .lamp {{ opacity: 0; animation: lights {LIGHT_LOOP}s step-end 2s infinite; }}
  .lampc {{ fill: #fff3cf; }}
  @keyframes lights {{ 0% {{ opacity: 0; }} 40% {{ opacity: 1; }} 41.5% {{ opacity: 0; }} 43% {{ opacity: 1; }} 44% {{ opacity: 0; }} 46% {{ opacity: 1; }} 85% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
  .hd {{ font-size: 20px; font-weight: 700; fill: {amber}; letter-spacing: 3px; }}
  .sk {{ font-size: 12px; fill: {t["muted"]}; letter-spacing: 2px; }}
  .sv {{ font-size: 13px; fill: {g2}; font-weight: 700; }}
  .dim {{ font-size: 11px; fill: {t["muted"]}; }}'''
    body = f'''
  <ellipse cx="{pad + cw_px * 0.5:.0f}" cy="{top + ch_px * 0.93:.0f}" rx="{cw_px * 0.55:.0f}" ry="{ch_px * 0.12:.0f}" fill="url(#floor)"/>
  <g font-size="{FONT}px" font-weight="700" fill="url(#cg)">
{car_svg(grid, pad, y0)}
  </g>
  <g font-size="{FONT}px" font-weight="700">{lamp_svg(lamp, pad, y0)}</g>
  {"".join(panel)}'''
    return window("dark", width, height, "GARAGE // AVENTADOR.BIN", body, defs, style,
                  accent=amber, tag="CRT-02 · P3 AMBER")


def main():
    path = ROOT / "car_dark.svg"
    path.write_text(build(*car_grid()))
    print(f"wrote {path.name} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
