#!/usr/bin/env python3
"""
Static CRT cards for the rest of the profile: interests (about), projects and stack.
Edit the content in config.json under "about", "projects" and "stack".
Writes about_dark.svg, projects_dark.svg, stack_dark.svg.   Run: python extras.py
"""
import math

from common import CFG, HEADER, ROOT, THEMES, esc, window

W = 1000
T = THEMES["dark"]
BLUE, CYAN, VIOLET = "#89cff0", "#67e8f9", "#c4b5fd"

BASE_STYLE = f'''
  .fade {{ opacity: 0; animation: fade .5s ease-out forwards; }}
  @keyframes fade {{ to {{ opacity: 1; }} }}
  .lbl {{ font-size: 10.5px; fill: {T["muted"]}; letter-spacing: 1.8px; }}
  .txt {{ font-size: 14px; fill: {T["text"]}; }}
  .dim {{ font-size: 12px; fill: {T["muted"]}; }}'''


# ------------------------------------------------------------------ about / interests
def about():
    a = CFG["about"]
    lines = a["bio"]
    out = [f'<text x="40" y="{HEADER + 34}" class="prompt">❯ whoami</text>']
    y = HEADER + 66
    for i, ln in enumerate(lines):
        out.append(f'<text x="40" y="{y}" class="txt fade" style="animation-delay:{0.2 + i * 0.15:.2f}s">{esc(ln)}</text>')
        y += 24
    y += 10
    out.append(f'<text x="40" y="{y}" class="dim fade" style="animation-delay:.9s">{esc(a["tagline"])}</text>')

    # interest graph: four nodes feeding a central BUILD node
    cx, cy = 768, HEADER + 128
    nodes = a["interests"]
    pos = [(cx - 134, cy - 72), (cx + 134, cy - 72), (cx - 134, cy + 72), (cx + 134, cy + 72)]
    g = []
    for (nx, ny), node in zip(pos, nodes):
        g.append(f'<path d="M{nx} {ny} L{cx} {cy}" stroke="{BLUE}" stroke-opacity=".35" stroke-dasharray="3 4"/>')
        for k in (0.33, 0.66):
            g.append(f'<circle cx="{nx + (cx - nx) * k:.1f}" cy="{ny + (cy - ny) * k:.1f}" r="1.8" fill="{BLUE}" fill-opacity=".7"/>')
    for i, ((nx, ny), node) in enumerate(zip(pos, nodes)):
        g.append(f'''<g class="fade" style="animation-delay:{0.4 + i * 0.12:.2f}s">
    <rect x="{nx - 70}" y="{ny - 26}" width="140" height="52" rx="8" fill="{T["bg"]}" stroke="{BLUE}" stroke-opacity=".45"/>
    <text x="{nx}" y="{ny - 3}" class="node" text-anchor="middle">{esc(node[0])}</text>
    <text x="{nx}" y="{ny + 15}" class="nsub" text-anchor="middle">{esc(node[1])}</text></g>''')
    g.append(f'''<g class="fade" style="animation-delay:1s">
    <circle cx="{cx}" cy="{cy}" r="46" fill="{BLUE}" fill-opacity=".07" stroke="{BLUE}" stroke-opacity=".8"/>
    <circle cx="{cx}" cy="{cy}" r="54" fill="none" stroke="{BLUE}" stroke-opacity=".25" stroke-dasharray="2 4"/>
    <text x="{cx}" y="{cy + 2}" class="core" text-anchor="middle">BUILD</text>
    <text x="{cx}" y="{cy + 18}" class="nsub" text-anchor="middle">where they meet</text></g>''')

    H = HEADER + 270
    style = BASE_STYLE + f'''
  .prompt {{ font-size: 15px; font-weight: 700; fill: {BLUE}; }}
  .node {{ font-size: 13px; font-weight: 700; fill: #eef7ff; letter-spacing: 2px; }}
  .nsub {{ font-size: 10.5px; fill: {T["muted"]}; }}
  .core {{ font-size: 15px; font-weight: 700; fill: {BLUE}; letter-spacing: 3px; }}'''
    return window("dark", W, H, "ABOUT // INTERESTS.SYS", "".join(out) + "".join(g), "", style,
                  accent=BLUE, tag="CRT-04 · P4 BLUE")


# ------------------------------------------------------------------ projects
def waveform(x, y, w, h, color):
    bars = []
    n = 34
    for i in range(n):
        v = 0.25 + 0.75 * abs(math.sin(i * 0.55) * math.cos(i * 0.21))
        bh = v * h
        bars.append(f'<rect x="{x + i * w / n:.1f}" y="{y + (h - bh) / 2:.1f}" width="{w / n * 0.55:.1f}" height="{bh:.1f}" rx="1" fill="{color}" fill-opacity="{0.35 + 0.65 * v:.2f}"/>')
    return "".join(bars)


def projects():
    items = CFG["projects"]
    cards = []
    cw, gap, x = 448, 24, 28
    y0, ch = HEADER + 26, 196
    for i, p in enumerate(items):
        cx = x + i * (cw + gap)
        if p.get("placeholder"):
            cards.append(f'''<g class="fade" style="animation-delay:{0.2 + i * 0.15:.2f}s">
    <rect x="{cx}" y="{y0}" width="{cw}" height="{ch}" rx="10" fill="none" stroke="{T["muted"]}" stroke-opacity=".6" stroke-dasharray="5 6"/>
    <text x="{cx + cw / 2}" y="{y0 + 82}" class="ph" text-anchor="middle">{esc(p["name"])}</text>
    <text x="{cx + cw / 2}" y="{y0 + 108}" class="dim" text-anchor="middle">{esc(p["desc"])}</text>
    <text x="{cx + cw / 2}" y="{y0 + 132}" class="lbl" text-anchor="middle">STATUS · IN THE GARAGE</text></g>''')
            continue
        chips, chx = [], cx + 22
        for tag in p["tags"]:
            wpx = len(tag) * 7.4 + 18
            chips.append(f'<rect x="{chx:.1f}" y="{y0 + 150}" width="{wpx:.1f}" height="22" rx="11" fill="{CYAN}" fill-opacity=".08" stroke="{CYAN}" stroke-opacity=".4"/>'
                         f'<text x="{chx + wpx / 2:.1f}" y="{y0 + 165}" class="chip" text-anchor="middle">{esc(tag)}</text>')
            chx += wpx + 8
        desc = "".join(f'<text x="{cx + 22}" y="{y0 + 88 + k * 20}" class="txt">{esc(ln)}</text>' for k, ln in enumerate(p["desc"]))
        cards.append(f'''<g class="fade" style="animation-delay:{0.2 + i * 0.15:.2f}s">
    <rect x="{cx}" y="{y0}" width="{cw}" height="{ch}" rx="10" fill="{CYAN}" fill-opacity=".04" stroke="{CYAN}" stroke-opacity=".45"/>
    <text x="{cx + 22}" y="{y0 + 40}" class="pt">{esc(p["name"])}</text>
    <circle cx="{cx + cw - 76}" cy="{y0 + 34}" r="4" fill="#4ade80"/><text x="{cx + cw - 66}" y="{y0 + 38}" class="live">{esc(p["status"])}</text>
    {waveform(cx + 22, y0 + 50, 200, 16, CYAN)}
    {desc}
    {"".join(chips)}</g>''')
    H = y0 + ch + 30
    style = BASE_STYLE + f'''
  .pt {{ font-size: 22px; font-weight: 700; fill: #f0fbff; letter-spacing: 1px; }}
  .live {{ font-size: 11px; fill: #4ade80; letter-spacing: 1.5px; }}
  .chip {{ font-size: 11.5px; fill: {CYAN}; }}
  .ph {{ font-size: 17px; font-weight: 700; fill: {T["muted"]}; letter-spacing: 2px; }}'''
    return window("dark", W, H, "PROJECTS // LS ./BUILDS", "".join(cards), "", style, accent=CYAN, tag="CRT-05 · CYAN")


# ------------------------------------------------------------------ stack / loadout
def stack():
    rows = CFG["stack"]
    out = []
    y = HEADER + 34
    for i, (cat, items) in enumerate(rows.items()):
        out.append(f'<text x="40" y="{y + 15}" class="cat fade" style="animation-delay:{0.15 + i * 0.12:.2f}s">{esc(cat.upper())}</text>')
        x = 200
        for j, it in enumerate(items):
            wpx = len(it) * 7.8 + 26
            out.append(f'''<g class="fade" style="animation-delay:{0.2 + i * 0.12 + j * 0.04:.2f}s">
    <rect x="{x:.1f}" y="{y}" width="{wpx:.1f}" height="24" rx="4" fill="{VIOLET}" fill-opacity=".07" stroke="{VIOLET}" stroke-opacity=".38"/>
    <rect x="{x:.1f}" y="{y}" width="3" height="24" rx="1" fill="{VIOLET}"/>
    <text x="{x + wpx / 2 + 1:.1f}" y="{y + 16.5}" class="it" text-anchor="middle">{esc(it)}</text></g>''')
            x += wpx + 10
        y += 40
    H = y + 22
    style = BASE_STYLE + f'''
  .cat {{ font-size: 11px; fill: {T["muted"]}; letter-spacing: 2.4px; }}
  .it {{ font-size: 12.5px; fill: #ede9fe; }}'''
    return window("dark", W, H, "STACK // LOADOUT.CFG", "".join(out), "", style, accent=VIOLET, tag="CRT-06 · VIOLET")


def main():
    for name, fn in [("about", about), ("projects", projects), ("stack", stack)]:
        (ROOT / f"{name}_dark.svg").write_text(fn())
        print(f"wrote {name}_dark.svg")


if __name__ == "__main__":
    main()
