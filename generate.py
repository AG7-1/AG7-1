#!/usr/bin/env python3
"""
Main profile card: your photo rendered in binary next to a neofetch-style info panel.
Writes dark_mode.svg and light_mode.svg.   Run: python generate.py
"""
import random

import numpy as np
from PIL import Image, ImageFilter

from common import CFG, HEADER, PHOSPHOR, ROOT, THEMES, esc, github_data, window

P = CFG["portrait"]
P_FONT = P.get("font_size", 8)          # small font = high-res portrait
P_CW, P_LH = P_FONT * 0.6, P_FONT * 1.12
I_FONT, I_CW, I_LH = 14, 8.4, 19
INFO_COLS = CFG.get("info_width", 56)
PAD, GAP, TOP = 34, 36, HEADER + 18
LEVELS = [0.16, 0.3, 0.46, 0.64, 0.82, 1.0]


# ---------------------------------------------------------------- portrait
def portrait_grid():
    """rows x cols array of brightness 0..1, NaN = background."""
    img = Image.open(ROOT / CFG["photo"]).convert("RGBA")
    if P.get("crop"):
        img = img.crop(tuple(P["crop"]))
    cols = P.get("cols", 92)
    rows = round(cols * img.height / img.width * P_CW / P_LH)
    img = img.filter(ImageFilter.UnsharpMask(radius=img.width // 40, percent=P.get("local_contrast", 220), threshold=0))
    img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=150)).resize((cols, rows), Image.LANCZOS)
    a = np.asarray(img, dtype=float) / 255
    lum = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    fg = a[..., 3] > 0.5
    # histogram-equalise only the person so the face gets the full tonal range
    vals = lum[fg]
    ranks = np.searchsorted(np.sort(vals), lum) / max(len(vals), 1)
    out = np.where(fg, ranks ** P.get("gamma", 1.0), np.nan)
    return out


def portrait_svg(grid, theme, x0, y0):
    rng = random.Random(7)
    rows, cols = grid.shape
    out = []
    for r in range(rows):
        lines = [[" "] * cols for _ in LEVELS]
        for c in range(cols):
            v = grid[r, c]
            if np.isnan(v):
                continue
            if theme == "light":
                v = 1 - v
            v = 0.08 + 0.92 * v
            lvl = min(int(v * len(LEVELS)), len(LEVELS) - 1)
            lines[lvl][c] = "." if lvl == 0 else ("1" if rng.random() < 0.3 + 0.5 * v else "0")
        parts = []
        for lvl, chars in enumerate(lines):
            s = "".join(chars)
            if not s.strip():
                continue
            lead = len(s) - len(s.lstrip())
            s = s.strip()
            parts.append(f'<text x="{x0 + lead * P_CW:.1f}" textLength="{len(s) * P_CW:.1f}" '
                         f'fill-opacity="{LEVELS[lvl]}">{s}</text>')
        if parts:
            out.append(f'<g class="pr" style="animation-delay:{r * 0.028:.3f}s" transform="translate(0 {y0 + r * P_LH:.1f})">'
                       + "".join(parts) + "</g>")
    return "\n".join(out)


# ---------------------------------------------------------------- info panel
def info_lines(gh):
    lines = []
    head = f"{CFG['username']}@github"
    lines.append([(head, "a"), (" " + "─" * (INFO_COLS - len(head) - 1), "d")])

    def kv(key, val):
        dots = INFO_COLS - len(key) - len(val) - 5
        return [("· ", "d"), (key, "k"), (":", "t"), (" " + "." * max(dots, 1) + " ", "d"), (val, "v")]

    def heading(t):
        t = f"── {t} "
        return [(t, "h"), ("─" * (INFO_COLS - len(t)), "d")]

    for sec in CFG["sections"]:
        if sec.get("title"):
            lines += [[], heading(sec["title"])]
        lines += [kv(k, v) for k, v in sec["items"]]

    cal = gh["calendar"]
    p = gh["profile"]
    lines += [[], heading("GitHub Stats")]
    lines.append(kv("Repos", f"{p['repos']}   Stars: {p['stars']}   Followers: {p['followers']}"))
    lines.append(kv("Contributions (1y)", str(sum(c for _, c in cal))))
    return lines


def info_svg(lines, x0, y0):
    out = []
    for i, chunks in enumerate(lines):
        if not chunks:
            continue
        n = sum(len(t) for t, _ in chunks)
        body = "".join(f'<tspan class="{c}">{esc(t)}</tspan>' for t, c in chunks)
        out.append(f'<text class="in" x="{x0}" y="{y0 + i * I_LH}" textLength="{n * I_CW:.1f}" '
                   f'style="animation-delay:{0.6 + i * 0.06:.2f}s">{body}</text>')
    y = y0 + (len(lines) + 1) * I_LH
    out.append(f'<text class="in" x="{x0}" y="{y}" style="animation-delay:{0.6 + len(lines) * 0.06:.2f}s">'
               f'<tspan class="a">❯</tspan><tspan class="t"> building something new</tspan><tspan class="cur">▋</tspan></text>')
    return "\n".join(out), len(lines) + 2


# ---------------------------------------------------------------- assemble
def build(theme, grid, gh):
    t = THEMES[theme]
    rows, cols = grid.shape
    pw, ph = cols * P_CW, rows * P_LH
    lines = info_lines(gh)
    info_h = (len(lines) + 2) * I_LH
    height = round(TOP + max(ph, info_h) + PAD - 6)
    ix = PAD + pw + GAP
    width = round(ix + INFO_COLS * I_CW + PAD)
    py = TOP + max(0, (info_h - ph) / 2)
    info, _ = info_svg(lines, ix, TOP + I_FONT + max(0, (ph - info_h) / 2))

    g0, g1, g2 = t["portrait"]
    defs = f'''
  <linearGradient id="pg" gradientUnits="userSpaceOnUse" x1="0" y1="{py}" x2="{PAD + pw}" y2="{py + ph}">
    <stop offset="0" stop-color="{g0}"/><stop offset="0.55" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/>
  </linearGradient>
  <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{g1}" stop-opacity="0"/><stop offset="0.5" stop-color="{g1}" stop-opacity="{0.16 if theme == 'dark' else 0.1}"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/>
  </linearGradient>
  <filter id="glow" x="-5%" y="-5%" width="110%" height="110%">
    <feGaussianBlur stdDeviation="1.6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>'''
    style = f'''
  .pr {{ opacity: 0; animation: up .5s ease-out forwards; }}
  .in {{ opacity: 0; animation: fade .35s ease-out forwards; font-size: {I_FONT}px; }}
  .k {{ fill: {t["key"]}; }} .v {{ fill: {t["value"]}; }} .t {{ fill: {t["text"]}; }} .d {{ fill: {t["dots"]}; }}
  .a {{ fill: {t["accent"]}; font-weight: 700; }} .h {{ fill: {t["title"]}; font-weight: 700; }}
  .cur {{ fill: {t["accent"]}; animation: blink 1.1s step-end infinite; }}
  .beam {{ animation: sweep 5s ease-in-out 2.2s infinite; opacity: 0; }}
  @keyframes up {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  @keyframes fade {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes blink {{ 50% {{ fill-opacity: 0; }} }}
  @keyframes sweep {{ 0% {{ opacity: 1; transform: translateY(-60px); }} 70% {{ opacity: 1; transform: translateY({ph}px); }} 71%, 100% {{ opacity: 0; }} }}'''
    body = f'''
  <g font-size="{P_FONT}px" font-weight="700" fill="url(#pg)">
{portrait_svg(grid, theme, PAD, py + P_FONT)}
  </g>
  <rect class="beam" x="{PAD - 6}" y="{py}" width="{pw + 12}" height="60" fill="url(#beam)"/>
{info}'''
    title = f"{CFG['username']} // PROFILE.SYS"
    return window(theme, width, height, title, body, defs, style, accent=PHOSPHOR["portrait"], tag="CRT-01 · P4 BLUE")


def main():
    grid = portrait_grid()
    gh = github_data()
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(build(theme, grid, gh))
        print(f"wrote {theme}_mode.svg")


if __name__ == "__main__":
    main()
