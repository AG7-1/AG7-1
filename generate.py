#!/usr/bin/env python3
"""
Main profile card: your photo rendered in binary next to a neofetch-style info panel.
Writes dark_mode.svg and light_mode.svg.   Run: python generate.py
"""
import math
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
LEVELS = [0.26, 0.38, 0.5, 0.64, 0.82, 1.0]


# ---------------------------------------------------------------- portrait
def portrait_grid():
    """rows x cols array of brightness 0..1, NaN = background."""
    img = Image.open(ROOT / CFG["photo"]).convert("RGBA")
    if P.get("crop"):
        img = img.crop(tuple(P["crop"]))
    cols = P.get("cols", 92)
    rows = round(cols * img.height / img.width * P_CW / P_LH)
    img = img.filter(ImageFilter.UnsharpMask(radius=img.width // 40, percent=int(P.get("local_contrast", 220)), threshold=0))
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
            v = 0.12 + 0.88 * v
            lvl = min(int(v * len(LEVELS)), len(LEVELS) - 1)
            lines[lvl][c] = "1" if rng.random() < 0.3 + 0.5 * v else "0"
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



# ---------------------------------------------------------------- hologram background
def head_box(grid, x0, y0):
    """centre and width of the head, from the top 40% of the silhouette."""
    rows = grid.shape[0]
    ys, xs = np.nonzero(~np.isnan(grid[: int(rows * 0.42)]))
    cx = x0 + (xs.min() + xs.max() + 1) / 2 * P_CW
    cy = y0 + (ys.mean() + 1) * P_LH
    return cx, cy, (xs.max() - xs.min() + 1) * P_CW


def rain_svg(grid, x0, y0):
    """static falling-binary columns behind the portrait, kept off the silhouette."""
    rng = random.Random(11)
    fs, cw, lh = 9, 9 * 0.6, 9 * 1.15
    rows, cols = grid.shape
    n_r, n_c = int(rows * P_LH / lh), int(cols * P_CW / cw)
    tiers = [[[" "] * n_c for _ in range(n_r)] for _ in range(3)]
    for c in range(0, n_c, 2):
        for _ in range(rng.choice([0, 1, 1, 2])):
            length, head = rng.randint(4, 14), rng.randint(0, n_r - 1)
            for k in range(length):
                r = head - k
                if r < 0:
                    break
                gr = min(int(r * lh / P_LH), rows - 1)
                gc = min(int(c * cw / P_CW), cols - 1)
                if not np.isnan(grid[gr, gc]):
                    continue
                tier = 2 if k == 0 else (1 if k < length / 2 else 0)
                tiers[tier][r][c] = rng.choice("01")
    out = []
    for tier, op in zip(tiers, (0.07, 0.13, 0.32)):
        for r, chars in enumerate(tier):
            s = "".join(chars)
            if s.strip():
                lead = len(s) - len(s.lstrip())
                s = s.strip()
                out.append(f'<text x="{x0 + lead * cw:.1f}" y="{y0 + fs + r * lh:.1f}" '
                           f'textLength="{len(s) * cw:.1f}" fill-opacity="{op}">{s}</text>')
    return f'<g class="rain" font-size="{fs}px">{"".join(out)}</g>'


def hud_svg(cx, cy, fw):
    """face-scan reticle around the head."""
    r = fw * 0.56
    ticks = []
    for i, deg in enumerate(range(0, 360, 10)):
        a = math.radians(deg)
        r2 = r + (11 if i % 6 == 0 else 7)
        ticks.append(f'<line x1="{cx + (r + 4) * math.cos(a):.1f}" y1="{cy + (r + 4) * math.sin(a):.1f}" '
                     f'x2="{cx + r2 * math.cos(a):.1f}" y2="{cy + r2 * math.sin(a):.1f}" class="hud" stroke-opacity=".45"/>')
    b, s = r * 0.85, 14
    brackets = "".join(
        f'<path d="M{cx + sx * b:.1f} {cy + sy * b - sy * s:.1f}V{cy + sy * b:.1f}H{cx + sx * b - sx * s:.1f}" '
        f'class="hud" stroke-opacity=".8" stroke-width="1.5"/>' for sx in (-1, 1) for sy in (-1, 1))
    return (f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="hud" stroke-opacity=".28" stroke-dasharray="3 5"/>'
            + "".join(ticks) + brackets
            + f'<text x="{cx + r + 16:.1f}" y="{cy - r * 0.55:.1f}" class="hudt">FACE_ID</text>'
            + f'<text x="{cx + r + 16:.1f}" y="{cy - r * 0.55 + 14:.1f}" class="hudt" fill-opacity=".6">AG7-1 · 100%</text>')


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

    hx, hy, fw = head_box(grid, PAD, py)
    g0, g1, g2 = t["portrait"]
    defs = f'''
  <linearGradient id="pg" gradientUnits="userSpaceOnUse" x1="0" y1="{py}" x2="{PAD + pw}" y2="{py + ph}">
    <stop offset="0" stop-color="{g0}"/><stop offset="0.55" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/>
  </linearGradient>
  <radialGradient id="halo" gradientUnits="userSpaceOnUse" cx="{hx:.0f}" cy="{hy:.0f}" r="{pw * 0.55:.0f}">
    <stop offset="0" stop-color="{g0}" stop-opacity=".22"/><stop offset=".5" stop-color="{g0}" stop-opacity=".07"/><stop offset="1" stop-color="{g0}" stop-opacity="0"/>
  </radialGradient>'''
    style = f'''
  .pr {{ opacity: 0; animation: up .5s ease-out forwards; }}
  .in {{ opacity: 0; animation: fade .35s ease-out forwards; font-size: {I_FONT}px; }}
  .k {{ fill: {t["key"]}; }} .v {{ fill: {t["value"]}; }} .t {{ fill: {t["text"]}; }} .d {{ fill: {t["dots"]}; }}
  .a {{ fill: {t["accent"]}; font-weight: 700; }} .h {{ fill: {t["title"]}; font-weight: 700; }}
  .cur {{ fill: {t["accent"]}; }}
  .rain {{ fill: {g0}; }} .hud {{ stroke: {g0}; fill: none; }} .hudt {{ fill: {g0}; font-size: 10px; letter-spacing: 1.5px; }}
  @keyframes up {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  @keyframes fade {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes blink {{ 50% {{ fill-opacity: 0; }} }}'''
    body = f'''
  <rect x="{PAD - 20}" y="{py - 10}" width="{pw + 40}" height="{ph + 20}" fill="url(#halo)"/>
  {rain_svg(grid, PAD, py)}
  {hud_svg(hx, hy, fw)}
  <g font-size="{P_FONT}px" font-weight="700" fill="url(#pg)">
{portrait_svg(grid, theme, PAD, py + P_FONT)}
  </g>
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
