"""Generate self-hosted stats cards from the GitHub GraphQL API.

Replaces third-party stat services (rate limits, downtime) with SVGs that match
the profile's design. Runs daily in .github/workflows/profile-stats.yml.

  GH_TOKEN=... python scripts/stats_cards.py --user chethandvg --out dist
"""

import argparse
import json
import os
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from theme import MONO, REDUCED_MOTION, SANS, THEMES, accent_gradient, esc

# Languages that distort the picture (notebook output, generated scripts, …).
HIDE_LANGS = {"Jupyter Notebook", "PowerShell", "Dockerfile", "Makefile", "Batchfile"}
TOP_LANGS = 6

# ── Data ─────────────────────────────────────────────────────────────────────


def gql(token: str, query: str, **variables) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]


PROFILE_Q = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalPullRequestReviewContributions
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        isPrivate
        stargazerCount
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}"""

CALENDAR_Q = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar { weeks { contributionDays { date contributionCount } } }
    }
  }
}"""


def fetch(token: str, login: str) -> dict:
    repos, cursor, first = [], None, None
    while True:
        u = gql(token, PROFILE_Q, login=login, cursor=cursor)["user"]
        first = first or u
        repos += u["repositories"]["nodes"]
        page = u["repositories"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]

    # Full contribution history, one year per request, for accurate streaks.
    days: dict[str, int] = {}
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(first["createdAt"].replace("Z", "+00:00"))
    while start < now:
        end = min(start + timedelta(days=365), now)
        cal = gql(token, CALENDAR_Q, login=login, **{"from": start.isoformat(), "to": end.isoformat()})
        for w in cal["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
        start = end

    langs: dict[str, list] = defaultdict(lambda: [0, "#888888"])
    for r in repos:
        for e in r["languages"]["edges"]:
            name = e["node"]["name"]
            if name in HIDE_LANGS:
                continue
            langs[name][0] += e["size"]
            langs[name][1] = e["node"]["color"] or "#888888"

    cc = first["contributionsCollection"]
    return {
        "days": dict(sorted(days.items())),
        "year_total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "repos": first["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos if not r["isPrivate"]),
        "followers": first["followers"]["totalCount"],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1][0]),
    }


def streaks(days: dict[str, int]) -> tuple[int, int]:
    today = date.today().isoformat()
    ordered = [(d, c) for d, c in days.items() if d <= today]
    longest = run = 0
    for _, c in ordered:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)
    current = 0
    for i, (d, c) in enumerate(reversed(ordered)):
        if c > 0:
            current += 1
        elif i == 0:  # today without contributions doesn't break the streak yet
            continue
        else:
            break
    return current, longest


# ── Rendering ────────────────────────────────────────────────────────────────


def fmt(n: int) -> str:
    return f"{n / 1000:.1f}k" if n >= 10_000 else f"{n:,}"


def overview_card(s: dict, t: dict) -> str:
    W, H = 1200, 300
    current, longest = streaks(s["days"])

    # Last 52 weeks as weekly bars.
    recent = list(s["days"].items())[-364:]
    weeks = [sum(c for _, c in recent[i:i + 7]) for i in range(0, len(recent), 7)]
    peak = max(weeks + [1])
    bx, by, bh = 560, 92, 150
    step = (W - 40 - bx) / max(len(weeks), 1)
    bw = step * 0.72
    bars = []
    for i, v in enumerate(weeks):
        h = max(3, v / peak * bh)
        x = bx + i * step
        fill = "url(#barG)" if v else t["empty_cell"]
        bars.append(
            f'<rect class="bar" style="animation-delay:{i * 0.012:.3f}s" x="{x:.1f}" y="{by + bh - h:.1f}" '
            f'width="{bw:.1f}" height="{h:.1f}" rx="2.5" fill="{fill}"/>'
        )
    first_label = datetime.fromisoformat(recent[0][0]).strftime("%b %Y") if recent else ""

    stats = [
        ("Current streak", f"{current}", "days"),
        ("Longest streak", f"{longest}", "days"),
        ("Commits", fmt(s["commits"]), "this year"),
        ("Pull requests", fmt(s["prs"]), "this year"),
        ("Repositories", fmt(s["repos"]), "owned"),
        ("Stars earned", fmt(s["stars"]), "public"),
    ]
    tiles = []
    for i, (label, value, unit) in enumerate(stats):
        col, row = i % 3, i // 3
        x, y = 40 + col * 160, 160 + row * 64
        tiles.append(
            f'<g class="fade" style="animation-delay:{0.15 + i * 0.06:.2f}s">'
            f'<text x="{x}" y="{y}" class="mono" font-size="11" letter-spacing="1" fill="{t["faint"]}">{esc(label.upper())}</text>'
            f'<text x="{x}" y="{y + 32}" class="sans"><tspan font-size="26" font-weight="700" fill="{t["text"]}">{esc(value)}</tspan>'
            f'<tspan dx="6" font-size="13" fill="{t["muted"]}">{esc(unit)}</tspan></text></g>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="GitHub activity overview">
<title>GitHub activity: {s["year_total"]} contributions in the last year</title>
<defs>
  {accent_gradient(t)}
  {accent_gradient(t, "barG", vertical=True)}
  <radialGradient id="glow" cx="1" cy="0" r="1"><stop offset="0" stop-color="{t["accent_b"]}" stop-opacity="{t["orb_opacity"] * 0.35}"/><stop offset="1" stop-color="{t["accent_b"]}" stop-opacity="0"/></radialGradient>
  <clipPath id="c"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  <style>
    .sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}
    .bar{{transform-box:fill-box;transform-origin:bottom;animation:grow .9s cubic-bezier(.2,.7,.2,1) backwards}}
    @keyframes grow{{from{{transform:scaleY(0)}}}}
    .fade{{animation:fade .6s ease-out backwards}}
    @keyframes fade{{from{{opacity:0}}}}
    {REDUCED_MOTION}
  </style>
</defs>
<g clip-path="url(#c)">
  <rect width="{W}" height="{H}" fill="{t["panel"]}"/>
  <rect width="{W}" height="{H}" fill="url(#glow)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="{t["border"]}"/>

<text x="40" y="56" class="mono" font-size="12" letter-spacing="1.4" fill="{t["accent_b"]}">ACTIVITY · LAST 12 MONTHS</text>
<text x="40" y="118" class="sans"><tspan font-size="58" font-weight="800" letter-spacing="-2" fill="url(#accent)">{fmt(s["year_total"])}</tspan><tspan dx="12" font-size="18" fill="{t["muted"]}">contributions</tspan></text>
{"".join(tiles)}

<line x1="520" y1="40" x2="520" y2="{H - 40}" stroke="{t["border"]}"/>
<text x="{bx}" y="56" class="mono" font-size="12" letter-spacing="1.4" fill="{t["faint"]}">WEEKLY CONTRIBUTIONS</text>
<text x="{W - 40}" y="56" text-anchor="end" class="mono" font-size="12" fill="{t["faint"]}">peak {peak}/wk</text>
{"".join(bars)}
<text x="{bx}" y="{by + bh + 26}" class="mono" font-size="11.5" fill="{t["faint"]}">{esc(first_label)}</text>
<text x="{W - 40}" y="{by + bh + 26}" text-anchor="end" class="mono" font-size="11.5" fill="{t["faint"]}">now</text>
</svg>
'''


def languages_card(s: dict, t: dict) -> str:
    W, H = 1200, 196
    top = s["langs"][:TOP_LANGS]
    other = sum(v[0] for _, v in s["langs"][TOP_LANGS:])
    if other:
        top = top + [("Other", [other, t["faint"]])]
    total = sum(v[0] for _, v in top) or 1

    bar_x, bar_w, bar_y = 40, W - 80, 78
    segs, x = [], bar_x
    for i, (name, (size, color)) in enumerate(top):
        w = size / total * bar_w
        segs.append(
            f'<rect class="seg" style="animation-delay:{i * 0.08:.2f}s" x="{x:.1f}" y="{bar_y}" '
            f'width="{max(w - 3, 1):.1f}" height="14" rx="4" fill="{color}"/>'
        )
        x += w

    legend, cols = [], 4
    for i, (name, (size, color)) in enumerate(top):
        col, row = i % cols, i // cols
        lx, ly = 40 + col * 285, 132 + row * 34
        pct = f"{size / total * 100:.1f}%"
        legend.append(
            f'<circle cx="{lx + 6}" cy="{ly - 5}" r="6" fill="{color}"/>'
            f'<text x="{lx + 20}" y="{ly}"><tspan class="sans" font-size="15" font-weight="600" fill="{t["text"]}">{esc(name)}</tspan>'
            f'<tspan dx="8" class="mono" font-size="13" fill="{t["muted"]}">{pct}</tspan></text>'
        )
    H = 132 + ((len(top) - 1) // cols) * 34 + 34

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Most used languages">
<title>Most used languages</title>
<defs>
  <clipPath id="c"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  <clipPath id="barClip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="14" rx="7"/></clipPath>
  <style>
    .sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}
    .seg{{transform-box:fill-box;transform-origin:left;animation:grow .8s cubic-bezier(.2,.7,.2,1) backwards}}
    @keyframes grow{{from{{transform:scaleX(0)}}}}
    {REDUCED_MOTION}
  </style>
</defs>
<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{t["panel"]}"/></g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="none" stroke="{t["border"]}"/>
<text x="40" y="52" class="mono" font-size="12" letter-spacing="1.4" fill="{t["accent_b"]}">LANGUAGES · BY CODE VOLUME</text>
<text x="{W - 40}" y="52" text-anchor="end" class="mono" font-size="12" fill="{t["faint"]}">across {s["repos"]} repositories</text>
<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="14" rx="7" fill="{t["empty_cell"]}"/>
<g clip-path="url(#barClip)">{"".join(segs)}</g>
{"".join(legend)}
</svg>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="chethandvg")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]

    s = fetch(token, args.user)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for mode, t in THEMES.items():
        (out / f"overview-{mode}.svg").write_text(overview_card(s, t), encoding="utf-8")
        (out / f"languages-{mode}.svg").write_text(languages_card(s, t), encoding="utf-8")
    cur, lon = streaks(s["days"])
    print(f"{s['year_total']} contributions, streak {cur}/{lon}, {len(s['langs'])} languages -> {out}")


if __name__ == "__main__":
    main()
