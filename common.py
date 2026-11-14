"""Shared theme, window chrome and GitHub data helpers for all profile cards."""
import json
import os
import re
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text())
CACHE = ROOT / ".cache.json"

FONT = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, 'DejaVu Sans Mono', 'Courier New', monospace"

# One always-dark CRT theme: it looks right on GitHub's light AND dark pages.
# Each card is a "monitor" with its own classic phosphor colour.
THEMES = {
    "dark": {
        "bg": "#0a0e14", "bezel": "#05070a", "border": "#1c2633",
        "text": "#c9d6e3", "muted": "#566475", "dots": "#1f2b38", "rule": "#16202b",
        "key": "#7dd3fc", "value": "#eef7ff", "accent": "#bae6fd", "title": "#ffffff",
        "portrait": ["#89cff0", "#bfe6fa", "#ffffff"],   # P4-style baby blue -> white
        "car": ["#ff7a00", "#ffb000", "#ffd27a"],        # P3 amber
        "progress": ["#22c55e", "#4ade80", "#d9ffe6"],   # P1 phosphor green
    },
}
PHOSPHOR = {"portrait": "#89cff0", "car": "#ffb000", "progress": "#4ade80"}
HEADER = 44   # y where card content may start


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def window(theme, width, height, title, body, defs="", style="", accent="#89cff0", tag="CRT-01"):
    """Wrap content in a retro CRT monitor: bezel, scanlines, vignette, HUD corners."""
    t = THEMES["dark"]
    i = 6                                   # bezel thickness
    sw, sh = width - 2 * i, height - 2 * i
    corners = "".join(
        f'<path d="M{x + dx * 14} {y} H{x} V{y + dy * 14}" fill="none" stroke="{accent}" stroke-opacity=".55" stroke-width="1.5"/>'
        for x, y, dx, dy in [(i + 10, i + 38, 1, 1), (width - i - 10, i + 38, -1, 1),
                             (i + 10, height - i - 10, 1, -1), (width - i - 10, height - i - 10, -1, -1)])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{FONT}">
<defs>
  <clipPath id="scr"><rect x="{i}" y="{i}" width="{sw}" height="{sh}" rx="10"/></clipPath>
  <pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1.2" fill="#000" opacity=".28"/></pattern>
  <radialGradient id="vig" cx="50%" cy="50%" r="75%"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>
  <radialGradient id="glowbg" cx="50%" cy="45%" r="70%"><stop offset="0" stop-color="{accent}" stop-opacity=".07"/><stop offset="1" stop-color="{accent}" stop-opacity="0"/></radialGradient>
  {defs}
</defs>
<style>
  text {{ white-space: pre; }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; opacity: 1 !important; }} }}
  {style}
</style>
<rect width="{width}" height="{height}" rx="14" fill="{t["bezel"]}" stroke="{t["border"]}"/>
<g clip-path="url(#scr)">
  <rect x="{i}" y="{i}" width="{sw}" height="{sh}" fill="{t["bg"]}"/>
  <rect x="{i}" y="{i}" width="{sw}" height="{sh}" fill="url(#glowbg)"/>
  <text x="{i + 18}" y="{i + 22}" font-size="12" font-weight="700" fill="{accent}" letter-spacing="1.5">▚ {esc(title)}</text>
  <text x="{width - i - 34}" y="{i + 22}" font-size="11" fill="{t["muted"]}" text-anchor="end" letter-spacing="1.5">{esc(tag)}</text>
  <circle class="live" cx="{width - i - 22}" cy="{i + 18}" r="4" fill="{accent}"/>
  <line x1="{i + 18}" x2="{width - i - 18}" y1="{i + 32}" y2="{i + 32}" stroke="{t["rule"]}" stroke-dasharray="2 4"/>
  {body}
  {corners}
  <rect x="{i}" y="{i}" width="{sw}" height="{sh}" fill="url(#scan)"/>
  <rect x="{i}" y="{i}" width="{sw}" height="{sh}" fill="url(#vig)"/>
</g>
</svg>
'''


# ------------------------------------------------------------------ GitHub data
def _get(url, token=None, data=None):
    headers = {"User-Agent": "profile-cards"}
    if token:
        headers["Authorization"] = f"bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode()


def _calendar(user, token):
    """[(date, count)] for the last year, oldest first."""
    if token:
        q = {"query": f'{{user(login:"{user}"){{contributionsCollection{{contributionCalendar{{weeks{{contributionDays{{date contributionCount}}}}}}}}}}}}'}
        d = json.loads(_get("https://api.github.com/graphql", token, json.dumps(q).encode()))
        weeks = d["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        return [(x["date"], x["contributionCount"]) for w in weeks for x in w["contributionDays"]]
    # no token: the public contributions page has the same numbers
    h = _get(f"https://github.com/users/{user}/contributions")
    ids = {i: d for d, i in re.findall(r'data-date="([\d-]+)" id="(contribution-day-component-[\d-]+)"', h)}
    tips = dict(re.findall(r'for="(contribution-day-component-[\d-]+)"[^>]*>([^<]*)<', h))
    out = []
    for i, d in ids.items():
        m = re.match(r"(\d+) contribution", tips.get(i, ""))
        out.append((d, int(m.group(1)) if m else 0))
    return sorted(out)


def _profile(user, token):
    u = json.loads(_get(f"https://api.github.com/users/{user}", token))
    repos = json.loads(_get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner", token))
    return {
        "repos": u["public_repos"],
        "followers": u["followers"],
        "stars": sum(r["stargazers_count"] for r in repos if not r["fork"]),
    }


def github_data():
    """Live data, falling back to the last successful fetch so a flaky API never breaks a card."""
    user, token = CFG["username"], os.environ.get("GITHUB_TOKEN")
    try:
        data = {"profile": _profile(user, token), "calendar": _calendar(user, token),
                "fetched": date.today().isoformat()}
        CACHE.write_text(json.dumps(data))
        return data
    except Exception as e:
        print("GitHub fetch failed, using cache:", e)
        if CACHE.exists():
            return json.loads(CACHE.read_text())
        return {"profile": {"repos": "?", "followers": "?", "stars": "?"}, "calendar": [], "fetched": "never"}
