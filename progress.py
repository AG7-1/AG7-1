#!/usr/bin/env python3
"""
progress.log: a 3D isometric version of your contribution graph, plus streaks and a
cumulative growth line. Writes progress_dark.svg and progress_light.svg.
Run: python progress.py
"""
import math
from collections import defaultdict
from datetime import date, timedelta

from common import CFG, ROOT, THEMES, esc, github_data, window

S = 9.5                       # tile size
A, B = S * 0.866, S * 0.5     # isometric axes
MAXH = 110


def hexmix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def shade(c, k):
    return hexmix(c, "#000000", 1 - k)


def color_for(t, theme):
    g0, g1, g2 = THEMES[theme]["progress"]
    return hexmix(g0, g1, t * 2) if t < 0.5 else hexmix(g1, g2, (t - 0.5) * 2)


def stats(cal):
    counts = [c for _, c in cal]
    total = sum(counts)
    longest = cur = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    # current streak counts back from today (or yesterday if today is still empty)
    i = len(counts) - 1
    if i >= 0 and counts[i] == 0:
        i -= 1
    while i >= 0 and counts[i]:
        cur += 1
        i -= 1
    best_d, best_c = max(cal, key=lambda x: x[1]) if cal else ("-", 0)
    wd = defaultdict(int)
    months = defaultdict(int)
    for d, c in cal:
        wd[date.fromisoformat(d).strftime("%A")] += c
        months[d[:7]] += c
    active = sum(1 for c in counts if c)
    return {
        "total": total, "longest": longest, "current": cur, "active": active,
        "best": (best_d, best_c), "weekday": max(wd, key=wd.get) if total else "-",
        "months": sorted(months.items())[-12:],
    }


def city(cal, theme, ox, oy):
    """isometric bars, painted back to front."""
    t = dict(THEMES[theme], tile="#1c1a26" if theme == "dark" else "#ece8f5")
    if not cal:
        return ""
    start = date.fromisoformat(cal[0][0])
    start -= timedelta(days=(start.weekday() + 1) % 7)       # align to Sunday
    mx = max(c for _, c in cal) or 1
    cells = []
    for d, c in cal:
        dd = date.fromisoformat(d)
        w, wd = (dd - start).days // 7, (dd.weekday() + 1) % 7
        cells.append((w, wd, c))
    cells.sort(key=lambda x: (x[0] + x[1], x[0]))
    U, V = (9.4, 2.4), (-6.6, 4.8)          # week axis, weekday axis
    out = []
    for w, d, c in cells:
        bx, by = ox + w * U[0] + d * V[0], oy + w * U[1] + d * V[1]
        if c == 0:
            col, h = t["tile"], 1.5
        else:
            k = math.sqrt(c / mx)
            col, h = color_for(k, theme), 8 + k * MAXH
        p0 = (bx, by); p1 = (bx + U[0], by + U[1]); p3 = (bx + V[0], by + V[1]); p2 = (p1[0] + V[0], p1[1] + V[1])
        pts = lambda *ps: " ".join(f"{x:.1f},{y:.1f}" for x, y in ps)
        up = lambda p: (p[0], p[1] - h)
        top = pts(up(p0), up(p1), up(p2), up(p3))
        front = pts(up(p3), up(p2), p2, p3)
        side = pts(up(p1), up(p2), p2, p1)
        anim = f' class="bar" style="animation-delay:{0.3 + w * 0.025:.2f}s"' if c else ""
        out.append(f'<g{anim}><polygon points="{front}" fill="{shade(col, 0.72)}"/>'
                   f'<polygon points="{side}" fill="{shade(col, 0.5)}"/>'
                   f'<polygon points="{top}" fill="{col}"/></g>')
    return "\n".join(out)


def growth(months, theme, x, y, w, h):
    """cumulative contributions line with an area fill."""
    t = THEMES[theme]
    if not months:
        return ""
    cum, run = [], 0
    for _, c in months:
        run += c
        cum.append(run)
    top = max(cum) or 1
    n = len(cum)
    pts = [(x + i * w / max(n - 1, 1), y + h - cum[i] / top * h) for i in range(n)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{x},{y + h} {line} {x + w},{y + h}"
    labels = "".join(
        f'<text x="{px:.1f}" y="{y + h + 16}" class="ml" text-anchor="middle">{date.fromisoformat(m + "-01").strftime("%b")[0]}</text>'
        for (m, _), (px, _) in zip(months, pts))
    dots = "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="2.6" fill="{t["bg"]}" stroke="{THEMES[theme]["progress"][1]}" stroke-width="1.6"/>' for px, py in pts)
    length = sum(math.dist(pts[i], pts[i + 1]) for i in range(n - 1)) + 1
    return f'''
  <polygon points="{area}" fill="url(#ag)"/>
  <polyline class="ln" points="{line}" fill="none" stroke="url(#lg)" stroke-width="2.4" stroke-linejoin="round" stroke-linecap="round" style="stroke-dasharray:{length:.0f};stroke-dashoffset:{length:.0f}"/>
  {dots}{labels}'''


def build(theme, gh):
    t = THEMES[theme]
    cal = gh["calendar"]
    st = stats(cal)
    width, height = 1000, 470
    top = 34
    ox, oy = 90, top + 70
    g0, g1, g2 = t["progress"]

    px = 640
    best_d, best_c = st["best"]
    best_s = f"{best_c} on {date.fromisoformat(best_d).strftime('%b %d')}" if best_c else "-"
    rows = [
        ("contributions (1y)", st["total"]), ("active days", st["active"]),
        ("current streak", f"{st['current']} days"), ("longest streak", f"{st['longest']} days"),
        ("best day", best_s), ("most active", st["weekday"]),
    ]
    panel = [f'<text x="{px}" y="{top + 40}" class="hd">progress.log</text>',
             f'<text x="{px + 330}" y="{top + 40}" class="dim" text-anchor="end">updated {esc(gh.get("fetched", ""))}</text>']
    y = top + 74
    for i, (k, v) in enumerate(rows):
        panel.append(f'<g class="row" style="animation-delay:{0.5 + i * 0.1:.1f}s"><text x="{px}" y="{y}" class="k">{k}</text>'
                     f'<text x="{px + 330}" y="{y}" class="v" text-anchor="end">{esc(v)}</text></g>')
        y += 26
    y += 12
    panel.append(f'<text x="{px}" y="{y}" class="k">cumulative · last 12 months</text>')
    panel.append(growth(st["months"], theme, px + 6, y + 14, 318, 110))

    first = date.fromisoformat(cal[0][0]).strftime("%b %Y") if cal else ""
    last = date.fromisoformat(cal[-1][0]).strftime("%b %Y") if cal else ""
    legend_x, legend_y = 40, height - 28
    legend = "".join(f'<rect x="{legend_x + 70 + i * 16}" y="{legend_y - 10}" width="12" height="12" rx="2" fill="{c}"/>'
                     for i, c in enumerate([("#1c1a26" if theme == "dark" else "#ece8f5")] + [color_for(k, theme) for k in (0.2, 0.5, 0.8, 1.0)]))

    defs = f'''
  <linearGradient id="lg"><stop offset="0" stop-color="{g0}"/><stop offset=".6" stop-color="{g1}"/><stop offset="1" stop-color="{g2}"/></linearGradient>
  <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{g1}" stop-opacity=".28"/><stop offset="1" stop-color="{g1}" stop-opacity="0"/></linearGradient>'''
    style = f'''
  .bar {{ opacity: 0; animation: rise .6s cubic-bezier(.2,.8,.2,1) forwards; }}
  @keyframes rise {{ from {{ opacity: 0; transform: translateY(-18px); }} to {{ opacity: 1; transform: none; }} }}
  .row {{ opacity: 0; animation: fade .4s ease-out forwards; }}
  @keyframes fade {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
  .ln {{ animation: draw 2.2s ease-out 1s forwards; }}
  @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
  .hd {{ font-size: 18px; font-weight: 700; fill: {g1}; }}
  .k {{ font-size: 13px; fill: {g2}; }} .v {{ font-size: 13px; fill: {t["value"]}; font-weight: 700; }}
  .dim, .ml {{ font-size: 11px; fill: {t["muted"]}; }}'''
    body = f'''
  <text x="40" y="{top + 40}" class="hd">{esc(CFG["username"])} // a year of commits</text>
  <text x="40" y="{top + 60}" class="dim">{first} → {last} · each tower is a day, height = contributions</text>
{city(cal, theme, 90, oy + 150)}
  <text x="{legend_x}" y="{legend_y}" class="dim">less</text>{legend}<text x="{legend_x + 156}" y="{legend_y}" class="dim">more</text>
  {"".join(panel)}'''
    return window(theme, width, height, f"progress.log — {CFG['username']} — tail -f", body, defs, style)


def main():
    gh = github_data()
    for theme in THEMES:
        (ROOT / f"progress_{theme}.svg").write_text(build(theme, gh))
        print(f"wrote progress_{theme}.svg")


if __name__ == "__main__":
    main()
