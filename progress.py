#!/usr/bin/env python3
"""
Progress card: your contribution year as a radar dial.

Every day of the last year is a spike around the dial (oldest at 12 o'clock, clockwise to
today); a radar beam sweeps over it. Next to it: digital readouts and an oscilloscope trace
of weekly activity. Writes progress_dark.svg.   Run: python progress.py
"""
import math
from collections import defaultdict
from datetime import date

from common import CFG, HEADER, PHOSPHOR, ROOT, THEMES, esc, github_data, window

W, H = 1000, 500
CX, CY = 250, 290            # dial centre
R0, R1 = 74, 182             # inner ring, max spike radius


def stats(cal):
    counts = [c for _, c in cal]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    cur, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i]:
        cur, i = cur + 1, i - 1
    wd = defaultdict(int)
    for d, c in cal:
        wd[date.fromisoformat(d).strftime("%a").upper()] += c
    best = max(cal, key=lambda x: x[1]) if cal else ("", 0)
    return {"total": sum(counts), "active": sum(1 for c in counts if c), "current": cur,
            "longest": longest, "best": best, "weekday": max(wd, key=wd.get) if sum(counts) else "—"}


def polar(r, a):
    return CX + r * math.sin(a), CY - r * math.cos(a)


def dial(cal, g):
    n = len(cal)
    mx = max((c for _, c in cal), default=0) or 1
    out = []
    # guide rings + crosshair
    for r, op in [(R0, .5), (R0 + 36, .18), (R0 + 72, .18), (R1, .3)]:
        out.append(f'<circle cx="{CX}" cy="{CY}" r="{r}" fill="none" stroke="{g[1]}" stroke-opacity="{op}" stroke-dasharray="{"" if op > .4 else "2 4"}"/>')
    out.append(f'<path d="M{CX - R1 - 8} {CY}H{CX + R1 + 8}M{CX} {CY - R1 - 8}V{CY + R1 + 8}" stroke="{g[1]}" stroke-opacity=".12"/>')
    # month ticks + labels
    seen = set()
    for i, (d, _) in enumerate(cal):
        m = d[:7]
        if d[8:] == "01" and i > 3:
            seen.add(m)
            a = 2 * math.pi * i / n
            x1, y1 = polar(R1 + 2, a)
            x2, y2 = polar(R1 + 9, a)
            lx, ly = polar(R1 + 22, a)
            out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{g[1]}" stroke-opacity=".6"/>')
            out.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" class="ml" text-anchor="middle">{date.fromisoformat(d).strftime("%b").upper()}</text>')
    # day spikes
    for i, (d, c) in enumerate(cal):
        a = 2 * math.pi * (i + 0.5) / n
        if c == 0:
            x, y = polar(R0 + 3, a)
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r=".9" fill="{g[0]}" fill-opacity=".35"/>')
            continue
        k = math.sqrt(c / mx)
        x1, y1 = polar(R0 + 2, a)
        x2, y2 = polar(R0 + 8 + k * (R1 - R0 - 10), a)
        col = g[2] if k > 0.66 else g[1]
        out.append(f'<line class="sp" x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{col}" '
                   f'stroke-width="2.4" stroke-linecap="round" style="animation-delay:{0.2 + i / n * 1.6:.2f}s"/>')
        out.append(f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="2.4" fill="{g[2]}"/>')
    # radar sweep: a fan of thin sectors fading behind the beam
    fan = []
    for j in range(14):
        a0, a1 = -math.radians(j * 3 + 3), -math.radians(j * 3)
        p0, p1 = polar(R1, a0), polar(R1, a1)
        fan.append(f'<path d="M{CX} {CY}L{p0[0]:.1f} {p0[1]:.1f}A{R1} {R1} 0 0 1 {p1[0]:.1f} {p1[1]:.1f}Z" fill="{g[1]}" fill-opacity="{0.22 * (1 - j / 14):.3f}"/>')
    tip = polar(R1, 0)
    fan.append(f'<line x1="{CX}" y1="{CY}" x2="{tip[0]:.1f}" y2="{tip[1]:.1f}" stroke="{g[2]}" stroke-width="1.6"/>')
    out.append(f'<g transform="rotate({360 * (n - 0.5) / n:.1f} {CX} {CY})">{"".join(fan)}</g>')   # beam parked on today
    # today marker
    tx, ty = polar(R0, 2 * math.pi * (n - 0.5) / n)
    out.append(f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="7" fill="{g[2]}" fill-opacity=".18"/><circle cx="{tx:.1f}" cy="{ty:.1f}" r="3.5" fill="{g[2]}"/>')
    return "\n".join(out)


def scope(cal, g, x, y, w, h):
    """oscilloscope trace of weekly totals."""
    weeks = [sum(c for _, c in cal[i:i + 7]) for i in range(0, len(cal), 7)]
    mx = max(weeks, default=0) or 1
    grid = "".join(f'<line x1="{x + i * w / 10:.1f}" y1="{y}" x2="{x + i * w / 10:.1f}" y2="{y + h}" stroke="{g[1]}" stroke-opacity="{.25 if i % 5 == 0 else .08}"/>' for i in range(11))
    grid += "".join(f'<line x1="{x}" y1="{y + i * h / 4:.1f}" x2="{x + w}" y2="{y + i * h / 4:.1f}" stroke="{g[1]}" stroke-opacity="{.25 if i == 2 else .08}"/>' for i in range(5))
    n = len(weeks)
    pts = []
    for i, v in enumerate(weeks):          # square-ish pulses read like a logic analyser
        px0, px1 = x + i * w / n, x + (i + 1) * w / n
        py = y + h - 4 - (v / mx) * (h - 10)
        pts += [(px0, py), (px1, py)]
    d = "M" + " L".join(f"{a:.1f} {b:.1f}" for a, b in pts)
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    return f'''{grid}
  <path d="{d}" fill="none" stroke="{g[0]}" stroke-opacity=".35" stroke-width="5" stroke-linejoin="round"/>
  <path class="trace" d="{d}" fill="none" stroke="{g[2]}" stroke-width="1.6" stroke-linejoin="round" style="stroke-dasharray:{length:.0f};stroke-dashoffset:{length:.0f}"/>'''


def build(gh):
    t = THEMES["dark"]
    g = t["progress"]
    green = PHOSPHOR["progress"]
    cal = gh["calendar"]
    st = stats(cal)
    best_d, best_c = st["best"]
    best = f"{best_c}" if best_c else "0"
    best_when = date.fromisoformat(best_d).strftime("%b %d").upper() if best_c else "—"

    centre = f'''
  <text x="{CX}" y="{CY + 8}" class="big" text-anchor="middle">{st["total"]}</text>
  <text x="{CX}" y="{CY + 30}" class="lbl" text-anchor="middle">COMMITS · 1 YR</text>'''

    rx, ry = 520, HEADER + 56
    tiles = [("ACTIVE DAYS", st["active"], ""), ("STREAK", st["current"], "d"),
             ("LONGEST", st["longest"], "d"), ("PEAK DAY", best, best_when),
             ("HOT DAY", st["weekday"], ""), ("REPOS", gh["profile"]["repos"], "")]
    readouts = []
    for i, (label, val, unit) in enumerate(tiles):
        x = rx + (i % 3) * 152
        y = ry + (i // 3) * 82
        readouts.append(f'''<g class="ro" style="animation-delay:{0.4 + i * 0.12:.2f}s">
    <rect x="{x}" y="{y}" width="140" height="68" rx="6" fill="{g[0]}" fill-opacity=".05" stroke="{g[1]}" stroke-opacity=".25"/>
    <text x="{x + 12}" y="{y + 20}" class="lbl">{label}</text>
    <text x="{x + 12}" y="{y + 54}" class="num">{esc(val)}<tspan class="unit"> {esc(unit)}</tspan></text></g>''')

    sx, sy, sw, sh = rx, ry + 186, 444, 116
    first = date.fromisoformat(cal[0][0]).strftime("%b %Y").upper() if cal else ""
    defs = ""
    style = f'''
  .sp {{ opacity: 0; animation: grow .5s ease-out forwards; }}
  @keyframes grow {{ to {{ opacity: 1; }} }}
  .ro {{ opacity: 0; animation: grow .4s ease-out forwards; }}
  .trace {{ animation: draw 2.4s ease-out .8s forwards; }}
  @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
  .big {{ font-size: 46px; font-weight: 700; fill: {g[2]}; }}
  .num {{ font-size: 26px; font-weight: 700; fill: {g[2]}; }}
  .unit {{ font-size: 12px; fill: {g[1]}; font-weight: 400; }}
  .lbl {{ font-size: 10.5px; fill: {t["muted"]}; letter-spacing: 1.8px; }}
  .ml {{ font-size: 10px; fill: {g[1]}; fill-opacity: .7; letter-spacing: 1px; }}'''
    body = f'''
  <text x="28" y="{HEADER + 20}" class="lbl">SIGNAL: {esc(CFG["username"])}.commits · SINCE {first} · each spike = one day</text>
  {dial(cal, g)}
  {centre}
  {"".join(readouts)}
  <text x="{sx}" y="{sy - 10}" class="lbl">WEEKLY SIGNAL · 52 WK</text>
  <text x="{sx + sw}" y="{sy - 10}" class="lbl" text-anchor="end">UPDATED {esc(gh.get("fetched", ""))}</text>
  {scope(cal, g, sx, sy, sw, sh)}'''
    return window("dark", W, H, "PROGRESS // RADAR.LOG", body, defs, style, accent=green, tag="CRT-03 · P1 GREEN")


def main():
    gh = github_data()
    (ROOT / "progress_dark.svg").write_text(build(gh))
    print("wrote progress_dark.svg")


if __name__ == "__main__":
    main()
