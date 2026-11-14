#!/usr/bin/env python3
"""
Progress card: the contribution year as a retro LED matrix, plus a level-up XP bar.

Each day is a round LED (brighter = more contributions). Total contributions are XP
toward the next developer level. It lights up once on load, then stays still.
Writes progress_dark.svg.   Run: python progress.py
"""
from collections import defaultdict
from datetime import date, timedelta

from common import CFG, HEADER, PHOSPHOR, ROOT, THEMES, esc, github_data, window

W = 1000
PITCH, R = 15.6, 5.0           # LED spacing and radius
LEVELS = [(0, ""), (25, ""), (100, ""), (250, ""), (500, ""), (1000, ""), (2500, "")]   # XP thresholds


def stats(cal):
    counts = [c for _, c in cal]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    months = defaultdict(int)
    for d, c in cal:
        months[d[:7]] += c
    best = max(cal, key=lambda x: x[1]) if cal else ("", 0)
    bm = max(months, key=months.get) if months else ""
    return {"total": sum(counts), "active": sum(1 for c in counts if c), "longest": longest,
            "best": best, "best_month": (bm, months.get(bm, 0))}


def level(xp):
    idx = max(i for i, (th, _) in enumerate(LEVELS) if xp >= th)
    lo, name = LEVELS[idx]
    hi, nxt = LEVELS[min(idx + 1, len(LEVELS) - 1)]
    frac = 1.0 if hi == lo else (xp - lo) / (hi - lo)
    return idx + 1, name, hi, nxt, frac


def led_matrix(cal, g, t, x0, y0):
    if not cal:
        return ""
    start = date.fromisoformat(cal[0][0])
    start -= timedelta(days=(start.weekday() + 1) % 7)            # weeks start on Sunday
    mx = max(c for _, c in cal) or 1
    cols = defaultdict(list)
    month_at = {}
    for d, c in cal:
        dd = date.fromisoformat(d)
        w, wd = (dd - start).days // 7, (dd.weekday() + 1) % 7
        cols[w].append((wd, c))
        if dd.day <= 7 and wd == 0:
            month_at[w] = dd.strftime("%b").upper()
    out = []
    for w, label in month_at.items():
        out.append(f'<text x="{x0 + w * PITCH - R:.1f}" y="{y0 - 14}" class="ml">{label}</text>')
    for i, wd in enumerate(("MON", "WED", "FRI")):
        out.append(f'<text x="{x0 - 16}" y="{y0 + (1 + 2 * i) * PITCH + 3.5:.1f}" class="ml" text-anchor="end">{wd}</text>')
    for w in sorted(cols):
        leds = []
        for wd, c in cols[w]:
            cx, cy = x0 + w * PITCH, y0 + wd * PITCH
            if c == 0:
                leds.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R}" fill="{t["dots"]}" fill-opacity=".9"/>')
                continue
            k = (c / mx) ** 0.5
            col = g[2] if k > 0.7 else g[1] if k > 0.35 else g[0]
            leds.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R + 4}" fill="{col}" fill-opacity="{0.12 + 0.18 * k:.2f}"/>'
                        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{R}" fill="{col}"/>'
                        f'<circle cx="{cx - 1.5:.1f}" cy="{cy - 1.6:.1f}" r="1.4" fill="#fff" fill-opacity=".55"/>')
        out.append(f'<g class="col" style="animation-delay:{0.15 + w * 0.018:.3f}s">{"".join(leds)}</g>')
    return "\n".join(out)


def build(gh):
    t = THEMES["dark"]
    g = t["progress"]
    green = PHOSPHOR["progress"]
    cal = gh["calendar"]
    st = stats(cal)
    lvl, name, nxt_xp, nxt_name, frac = level(st["total"])

    x0, y0 = 92, HEADER + 62
    mat_h = 7 * PITCH
    by = y0 + mat_h + 34                       # bottom section top
    H = round(by + 128)

    # legend
    lx = x0 + 52 * PITCH - 5 * 14 - 34
    legend = (f'<text x="{lx - 8}" y="{y0 + mat_h + 8}" class="ml" text-anchor="end">LESS</text>'
              + "".join(f'<circle cx="{lx + i * 14}" cy="{y0 + mat_h + 4}" r="4.2" fill="{c}"/>'
                        for i, c in enumerate([t["dots"], g[0], g[1], g[2]]))
              + f'<text x="{lx + 4 * 14}" y="{y0 + mat_h + 8}" class="ml">MORE</text>')

    # XP / level panel
    segs, sw = 34, 13.2
    lit = round(frac * segs)
    bar = "".join(f'<rect class="seg" x="{x0 - 24 + i * sw:.1f}" y="{by + 54}" width="{sw - 3.2:.1f}" height="16" rx="2" '
                  f'fill="{g[2] if i < lit else t["dots"]}" fill-opacity="{1 if i < lit else .9}" style="animation-delay:{0.9 + i * 0.03:.2f}s"/>'
                  for i in range(segs))
    xp_panel = f'''
  <text x="{x0 - 24}" y="{by + 18}" class="lbl">DEVELOPER LEVEL</text>
  <text x="{x0 - 24}" y="{by + 44}" class="lv">LEVEL {lvl:02d}<tspan class="lvn">  ▲ leveling up</tspan></text>
  {bar}
  <text x="{x0 - 24}" y="{by + 92}" class="xp">{st["total"]} / {nxt_xp} XP</text>
  <text x="{x0 - 24 + segs * sw - 3:.1f}" y="{by + 92}" class="xp" text-anchor="end">NEXT ▸ LEVEL {lvl + 1:02d}</text>
  <text x="{x0 - 24}" y="{by + 110}" class="ml">1 contribution = 1 XP · resets never</text>'''

    best_d, best_c = st["best"]
    bm, bmc = st["best_month"]
    tiles = [("ACTIVE DAYS", st["active"], "of 365"),
             ("LONGEST STREAK", st["longest"], "days"),
             ("PEAK DAY", best_c, date.fromisoformat(best_d).strftime("%b %d").upper() if best_c else "—"),
             ("BEST MONTH", bmc, date.fromisoformat(bm + "-01").strftime("%b %Y").upper() if bm else "—")]
    tx0 = 560
    tile_svg = []
    for i, (label, val, sub) in enumerate(tiles):
        x = tx0 + (i % 2) * 196
        y = by + (i // 2) * 58
        tile_svg.append(f'''<g class="tile" style="animation-delay:{0.6 + i * 0.1:.1f}s">
    <rect x="{x}" y="{y}" width="184" height="50" rx="6" fill="{g[0]}" fill-opacity=".05" stroke="{g[1]}" stroke-opacity=".22"/>
    <text x="{x + 12}" y="{y + 18}" class="lbl">{label}</text>
    <text x="{x + 12}" y="{y + 40}" class="num">{esc(val)}<tspan class="sub">  {esc(sub)}</tspan></text></g>''')

    first = date.fromisoformat(cal[0][0]).strftime("%b %Y").upper() if cal else ""
    style = f'''
  .col, .tile {{ opacity: 0; animation: on .35s ease-out forwards; }}
  .seg {{ opacity: 0; animation: on .2s ease-out forwards; }}
  @keyframes on {{ to {{ opacity: 1; }} }}
  .ml {{ font-size: 10px; fill: {t["muted"]}; letter-spacing: 1.2px; }}
  .lbl {{ font-size: 10.5px; fill: {t["muted"]}; letter-spacing: 1.8px; }}
  .lv {{ font-size: 22px; font-weight: 700; fill: {g[2]}; letter-spacing: 1px; }}
  .lvn {{ fill: {green}; font-size: 16px; letter-spacing: 2px; }}
  .xp {{ font-size: 12px; fill: {g[1]}; letter-spacing: 1px; }}
  .num {{ font-size: 20px; font-weight: 700; fill: {g[2]}; }}
  .sub {{ font-size: 11px; font-weight: 400; fill: {t["muted"]}; }}'''
    body = f'''
  <text x="28" y="{HEADER + 20}" class="lbl">BUILD.LOG · {esc(CFG["username"])} · SINCE {first} · {st["total"]} CONTRIBUTIONS</text>
  <text x="{W - 28}" y="{HEADER + 20}" class="lbl" text-anchor="end">UPDATED {esc(gh.get("fetched", ""))}</text>
  {led_matrix(cal, g, t, x0, y0)}
  {legend}
  <line x1="28" x2="{W - 28}" y1="{by - 12}" y2="{by - 12}" stroke="{t["rule"]}" stroke-dasharray="2 4"/>
  {xp_panel}
  {"".join(tile_svg)}'''
    return window("dark", W, H, "PROGRESS // BUILD.LOG", body, "", style, accent=green, tag="CRT-03 · P1 GREEN")


def main():
    gh = github_data()
    (ROOT / "progress_dark.svg").write_text(build(gh))
    print("wrote progress_dark.svg")


if __name__ == "__main__":
    main()
