#!/usr/bin/env python3
"""
Terminal-style SVG dashboard for GitHub profile README.
Runs on a schedule via GitHub Actions — commits dashboard.svg back to repo.
"""

import os
import json
import datetime
import urllib.request

USERNAME = os.environ.get("GH_USERNAME", "kisalegacy")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUTPUT = "dashboard.svg"

# ── PALETTE ──────────────────────────────────────────────────────────────────
BG       = "#0d1117"
BG2      = "#161b22"
BORDER   = "#21262d"
BORDER2  = "#30363d"
GREEN    = "#3fb950"
CYAN     = "#58a6ff"
YELLOW   = "#d29922"
WHITE    = "#e6edf3"
GRAY     = "#8b949e"
RED      = "#f85149"
PURPLE   = "#bc8cff"
ORANGE   = "#ffa657"

W, H = 860, 460

LANG_COLORS = {
    "Python":     "#3572A5",
    "Go":         "#00ADD8",
    "Rust":       "#dea584",
    "C":          "#555555",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Shell":      "#89e051",
    "C++":        "#f34b7d",
    "HTML":       "#e34c26",
    "CSS":        "#563d7c",
}

# ── GITHUB API ────────────────────────────────────────────────────────────────
def gh_get(url):
    if not GITHUB_TOKEN:
        return None
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {GITHUB_TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "profile-dashboard/1.0")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  API error ({url}): {e}")
        return None


def get_github_stats():
    repos = gh_get(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner") or []
    public_repos = len([r for r in repos if not r.get("private", False)])

    lang_bytes = {}
    for repo in repos:
        if repo.get("fork"):
            continue
        langs = gh_get(repo.get("languages_url", "")) or {}
        for lang, b in langs.items():
            lang_bytes[lang] = lang_bytes.get(lang, 0) + b

    total = sum(lang_bytes.values()) or 1
    top = sorted(lang_bytes.items(), key=lambda x: -x[1])[:5]
    top_langs = [(lang, round(b / total * 100, 1)) for lang, b in top]

    if not top_langs:
        top_langs = [("Python", 40.0), ("Go", 25.0), ("Rust", 18.0), ("C", 10.0), ("Shell", 7.0)]

    return {"repos": public_repos, "langs": top_langs}


# ── TIME ─────────────────────────────────────────────────────────────────────
def time_progress():
    now = datetime.datetime.utcnow()
    soy = datetime.datetime(now.year, 1, 1)
    eoy = datetime.datetime(now.year + 1, 1, 1)
    year_pct = (now - soy).total_seconds() / (eoy - soy).total_seconds() * 100
    day_pct  = (now.hour * 3600 + now.minute * 60 + now.second) / 86400 * 100
    hour_pct = (now.minute * 60 + now.second) / 3600 * 100
    min_pct  = now.second / 60 * 100
    return {
        "year":   round(year_pct, 1),
        "day":    round(day_pct, 1),
        "hour":   round(hour_pct, 1),
        "minute": round(min_pct, 1),
        "clock":  now.strftime("%H:%M:%S"),
        "date":   now.strftime("%Y-%m-%d"),
    }


# ── SVG BUILDER ───────────────────────────────────────────────────────────────
def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class SVG:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = []

    def rect(self, x, y, w, h, fill=BG, rx=3, stroke=None, sw=1):
        s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'
        if stroke:
            s += f' stroke="{stroke}" stroke-width="{sw}"'
        s += "/>"
        self.buf.append(s)

    def text(self, x, y, content, fill=WHITE, size=11, anchor="start",
             weight="normal", family="'Courier New',Courier,monospace"):
        self.buf.append(
            f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
            f'font-family="{family}" text-anchor="{anchor}" font-weight="{weight}">'
            f"{esc(content)}</text>"
        )

    def line(self, x1, y1, x2, y2, stroke=BORDER2, sw=1):
        self.buf.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def bar(self, x, y, w, h, pct, fg=GREEN, bg=BORDER):
        self.rect(x, y, w, h, fill=bg, rx=2)
        filled = max(0, int(w * min(pct, 100) / 100))
        if filled > 0:
            self.rect(x, y, filled, h, fill=fg, rx=2)

    def panel(self, x, y, w, h, title, title_color=CYAN):
        self.rect(x, y, w, h, fill=BG2, rx=4, stroke=BORDER2, sw=1)
        self.text(x + 10, y + 16, title, fill=title_color, size=10, weight="bold")
        self.line(x + 1, y + 22, x + w - 1, y + 22, stroke=BORDER)

    def render(self):
        return (
            f'<svg viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" '
            f'xmlns="http://www.w3.org/2000/svg">\n'
            + "\n".join(self.buf)
            + "\n</svg>"
        )


# ── LAYOUT ────────────────────────────────────────────────────────────────────
PAD  = 16
GAP  = 10
COL1 = 310
COL2 = W - 2 * PAD - COL1 - GAP
ROW1_Y = PAD + 40 + GAP
ROW2_Y = ROW1_Y + 120 + GAP
PH1    = 120
PH2    = 150


def generate(stats, tp):
    svg = SVG(W, H)

    # canvas
    svg.rect(0, 0, W, H, fill=BG, rx=8, stroke=BORDER2, sw=1)

    # ── HEADER ───────────────────────────────────────────────────────────────
    svg.rect(PAD, PAD, W - 2 * PAD, 36, fill=BG2, rx=4, stroke=BORDER2, sw=1)
    svg.text(PAD + 12, PAD + 24, "◢  KISALEGACY", fill=GREEN, size=13, weight="bold")
    svg.text(PAD + 135, PAD + 24, "·  SYSTEMS  ·  NETWORKS  ·  SECURITY", fill=GRAY, size=11)
    svg.text(W - PAD - 12, PAD + 24, "● ONLINE", fill=GREEN, size=11, anchor="end")

    cx = PAD + COL1 + GAP

    # ── ROW 1 LEFT: TIME PROGRESS ────────────────────────────────────────────
    svg.panel(PAD, ROW1_Y, COL1, PH1, "TIME PROGRESS")
    bars = [
        ("YEAR  ", tp["year"]),
        ("DAY   ", tp["day"]),
        ("HOUR  ", tp["hour"]),
        ("MIN   ", tp["minute"]),
    ]
    lw = 52
    bw = COL1 - lw - 62 - 20
    by = ROW1_Y + 32
    for label, pct in bars:
        svg.text(PAD + 10, by + 10, label, fill=GRAY, size=10)
        svg.bar(PAD + 10 + lw, by, bw, 11, pct)
        svg.text(PAD + 10 + lw + bw + 6, by + 10, f"{pct:5.1f}%", fill=WHITE, size=10)
        by += 20

    # ── ROW 1 RIGHT: CLOCK ───────────────────────────────────────────────────
    svg.panel(cx, ROW1_Y, COL2, PH1, "SYSTEM CLOCK")
    mid = cx + COL2 // 2
    svg.text(mid, ROW1_Y + 60, tp["clock"] + " UTC", fill=GREEN, size=28,
             anchor="middle", weight="bold")
    svg.text(mid, ROW1_Y + 84, tp["date"], fill=GRAY, size=12, anchor="middle")
    svg.text(mid, ROW1_Y + 108, f"public repos: {stats['repos']}", fill=GRAY,
             size=10, anchor="middle")

    # ── ROW 2 LEFT: LANGUAGES ────────────────────────────────────────────────
    svg.panel(PAD, ROW2_Y, COL1, PH2, "LANGUAGE BREAKDOWN")
    llw = 76
    lbw = COL1 - llw - 62 - 20
    ly  = ROW2_Y + 34
    for lang, pct in stats["langs"][:5]:
        color = LANG_COLORS.get(lang, CYAN)
        svg.text(PAD + 10, ly + 10, lang, fill=WHITE, size=10)
        svg.bar(PAD + 10 + llw, ly, lbw, 10, pct, fg=color)
        svg.text(PAD + 10 + llw + lbw + 6, ly + 10, f"{pct:.1f}%", fill=GRAY, size=10)
        ly += 24

    # ── ROW 2 RIGHT: PROJECTS ────────────────────────────────────────────────
    svg.panel(cx, ROW2_Y, COL2, PH2, "PROJECT STATUS")
    projects = [
        ("ASH CORE",      72, GREEN,  "ACTIVE DEV", "AI · Database Polymorph · 3D/VR Framework"),
        ("PHOENIX PROTO", 55, YELLOW, "ARCH PHASE",  "5-Layer Security Containment & Recovery"),
    ]
    py2 = ROW2_Y + 36
    pbw = COL2 - 20
    for name, pct, color, status, desc in projects:
        svg.text(cx + 10,        py2, name,           fill=WHITE, size=11, weight="bold")
        svg.text(cx + COL2 - 10, py2, f"[{status}]", fill=color, size=10, anchor="end")
        py2 += 16
        svg.bar(cx + 10, py2, pbw, 9, pct, fg=color)
        py2 += 14
        svg.text(cx + 10, py2, desc, fill=GRAY, size=9)
        py2 += 28

    # ── FOOTER ───────────────────────────────────────────────────────────────
    fy = H - PAD - 22
    svg.line(PAD, fy - 8, W - PAD, fy - 8, stroke=BORDER)
    svg.text(PAD + 4,     fy + 6,
             "Systems · Networks · Security  |  Go · Rust · C",
             fill=GRAY, size=10)
    svg.text(W - PAD - 4, fy + 6,
             f"auto-updated · {tp['date']}",
             fill=GRAY, size=10, anchor="end")

    return svg.render()


# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[dashboard] Fetching stats for {USERNAME}...")
    stats = get_github_stats()
    print(f"  repos={stats['repos']}  langs={stats['langs']}")
    tp = time_progress()
    print(f"  clock={tp['clock']}  year={tp['year']}%  day={tp['day']}%")
    svg_out = generate(stats, tp)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(svg_out)
    print(f"[dashboard] Written -> {OUTPUT}  ({len(svg_out)} bytes)")
