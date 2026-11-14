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

THEMES = {
    "dark": {
        "bg": "#0d1117", "bg2": "#161b22", "border": "#3a2a1f", "bar": "#16120f",
        "text": "#e6edf3", "muted": "#8b7d70", "dots": "#3d3128",
        "key": "#ffb347", "value": "#ffe8c7", "accent": "#ff8c1a", "title": "#ff5e1a",
        "grad": ["#ff4d00", "#ff9500", "#ffd23f"],      # Arancio Argos -> gold
        "car": ["#7fff00", "#c6ff4d", "#3ddc84"],       # Verde Mantis
        "portrait": ["#89cff0", "#bfe6fa", "#ffffff"],  # baby blue -> white
        "progress": ["#7c5cff", "#b49cff", "#f0b8ff"],  # lavender -> violet
        "grid": "#ff6a00", "tile": "#1f1813",
    },
    "light": {
        "bg": "#fffaf5", "bg2": "#fff1e3", "border": "#f0d9c2", "bar": "#fff1e3",
        "text": "#24292f", "muted": "#8c7361", "dots": "#ecd6c1",
        "key": "#b45309", "value": "#3b2412", "accent": "#d9480f", "title": "#c2410c",
        "grad": ["#c2410c", "#ea580c", "#d97706"],
        "car": ["#3f8f00", "#5fa800", "#2f7a3a"],
        "portrait": ["#2f7fb8", "#5aa9de", "#8cc8ec"],
        "progress": ["#5b3fd9", "#8257e6", "#b04fd6"],
        "grid": "#ea580c", "tile": "#f5e6d8",
    },
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def window(theme, width, height, title, body, defs="", style=""):
    """Wrap content in a macOS-style terminal window."""
    t = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="{FONT}">
<defs>
  <clipPath id="win"><rect width="{width}" height="{height}" rx="12"/></clipPath>
  <pattern id="scan" width="4" height="3" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="{t["text"]}" opacity="0.035"/></pattern>
  {defs}
</defs>
<style>
  text {{ white-space: pre; }}
  @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; opacity: 1 !important; }} }}
  {style}
</style>
<g clip-path="url(#win)">
  <rect width="{width}" height="{height}" fill="{t["bg"]}"/>
  <rect width="{width}" height="34" fill="{t["bar"]}"/>
  <line x1="0" y1="34" x2="{width}" y2="34" stroke="{t["border"]}"/>
  <circle cx="20" cy="17" r="6" fill="#ff5f57"/><circle cx="40" cy="17" r="6" fill="#febc2e"/><circle cx="60" cy="17" r="6" fill="#28c840"/>
  <text x="{width / 2}" y="22" text-anchor="middle" font-size="13" fill="{t["muted"]}">{esc(title)}</text>
  {body}
  <rect y="34" width="{width}" height="{height - 34}" fill="url(#scan)" pointer-events="none"/>
</g>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="none" stroke="{t["border"]}"/>
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
