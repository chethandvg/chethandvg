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

from theme import MONO, REDUCED_MOTION, SANS, THEMES, accent_gradient, contrib_ramp, esc, shade

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
      commitContributionsByRepository(maxRepositories: 100) {
        contributions { totalCount }
        repository {
          name
          languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
            edges { size node { name color } }
          }
        }
      }
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

    # Languages weighted by my commits per repo over the last year, so the card
    # reflects what I actually work on rather than bytes sitting in repos
    # (vendored libraries, notebooks). This profile repo itself is excluded.
    cc = first["contributionsCollection"]
    langs: dict[str, list] = defaultdict(lambda: [0.0, "#888888"])
    committed = [r for r in cc["commitContributionsByRepository"] if r["repository"]["name"] != login]
    for r in committed:
        edges = [e for e in r["repository"]["languages"]["edges"] if e["node"]["name"] not in HIDE_LANGS]
        total = sum(e["size"] for e in edges) or 1
        for e in edges:
            langs[e["node"]["name"]][0] += r["contributions"]["totalCount"] * e["size"] / total
            langs[e["node"]["name"]][1] = e["node"]["color"] or "#888888"

    return {
        "days": dict(sorted(days.items())),
        "year_total": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "issues": cc["totalIssueContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "repos": sum(1 for r in repos if not r["isPrivate"]),
        "lang_repos": len(committed),
        "stars": sum(r["stargazerCount"] for r in repos if not r["isPrivate"]),
        "followers": first["followers"]["totalCount"],
        "created": first["createdAt"][:10],
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
        ("Current streak", f"{current}", "day" if current == 1 else "days"),
        ("Longest streak", f"{longest}", "day" if longest == 1 else "days"),
        ("Commits", fmt(s["commits"]), "this year"),
        ("All-time", fmt(sum(s["days"].values())), "total"),
        ("Best week", fmt(peak), "in 7 days"),
        ("On GitHub", f"{(date.today() - date.fromisoformat(s['created'])).days // 365}", "years"),
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
<text x="40" y="52" class="mono" font-size="12" letter-spacing="1.4" fill="{t["accent_b"]}">LANGUAGES · WEIGHTED BY MY COMMITS</text>
<text x="{W - 40}" y="52" text-anchor="end" class="mono" font-size="12" fill="{t["faint"]}">last 12 months · {s["lang_repos"]} repositories</text>
<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="14" rx="7" fill="{t["empty_cell"]}"/>
<g clip-path="url(#barClip)">{"".join(segs)}</g>
{"".join(legend)}
</svg>
'''


def landscape_card(s: dict, t: dict) -> str:
    """Isometric 3D contribution graph: height and colour both scale with daily work."""
    W, H = 1200, 640
    ramp = contrib_ramp(t)
    dark = t is THEMES["dark"]

    # Last 53 weeks, Sunday-aligned like GitHub's calendar.
    end = date.today()
    start = end - timedelta(days=(end.weekday() + 1) % 7) - timedelta(weeks=52)
    cells = []
    d = start
    while d <= end:
        off = (d - start).days
        cells.append((off // 7, off % 7, d, s["days"].get(d.isoformat(), 0)))
        d += timedelta(days=1)

    counts = sorted(c for *_, c in cells if c)
    peak = counts[-1] if counts else 1
    q = [counts[int(len(counts) * p)] for p in (0.25, 0.5, 0.75)] if counts else [1, 1, 1]

    def level(c):
        if not c:
            return 0
        return 1 if c <= q[0] else 2 if c <= q[1] else 3 if c <= q[2] else 4

    ox, oy, wv, dv, gap, max_h = 170, 236, (17, 5.5), (-9, 8), 0.1, 124

    def P(w, dd, h=0.0):
        return ox + w * wv[0] + dd * dv[0], oy + w * wv[1] + dd * dv[1] - h

    def poly(pts, fill):
        return f'<path d="M{"L".join(f"{x:.1f} {y:.1f}" for x, y in pts)}Z" fill="{fill}"/>'

    weeks: dict[int, list[str]] = defaultdict(list)
    for w, dd, _, c in cells:  # week-major order is a valid painter's order here
        a, b = (w + gap, dd + gap), (w + 1 - gap, dd + gap)
        cc, e = (w + 1 - gap, dd + 1 - gap), (w + gap, dd + 1 - gap)
        if not c:
            weeks[w].append(poly([P(*a), P(*b), P(*cc), P(*e)], ramp[0]))
            continue
        h = 3 + (max_h - 3) * (c / peak) ** 0.5
        top = ramp[level(c)]
        weeks[w].append(
            poly([P(*e), P(*cc), P(*cc, h), P(*e, h)], shade(top, 0.22 if dark else 0.12))
            + poly([P(*b), P(*cc), P(*cc, h), P(*b, h)], shade(top, 0.4 if dark else 0.24))
            + poly([P(*a, h), P(*b, h), P(*cc, h), P(*e, h)], top)
        )
    bars = "".join(
        f'<g class="wk" style="animation-delay:{w * 0.018:.3f}s">{"".join(parts)}</g>'
        for w, parts in sorted(weeks.items())
    )

    months, prev = [], None
    for w, dd, day, _ in cells:
        if dd == 0 and day.month != prev:
            if prev is not None:
                x, y = P(w + 0.5, 7.9)
                months.append(f'<text x="{x:.0f}" y="{y + 12:.0f}" text-anchor="middle" class="mono" '
                              f'font-size="11" fill="{t["faint"]}">{day.strftime("%b")}</text>')
            prev = day.month
    weekdays = "".join(
        f'<text x="{P(0, i + 0.5)[0] - 26:.0f}" y="{P(0, i + 0.5)[1] + 4:.0f}" text-anchor="end" class="mono" '
        f'font-size="10.5" fill="{t["faint"]}">{name}</text>'
        for i, name in ((1, "Mon"), (3, "Wed"), (5, "Fri"))
    )

    # Insights the other cards don't already show.
    by_day = max(cells, key=lambda x: x[3])
    by_wd, by_month = defaultdict(int), defaultdict(int)
    for _, dd, day, c in cells:
        by_wd[day.strftime("%A")] += c
        by_month[day.strftime("%b %Y")] += c
    top_wd = max(by_wd, key=by_wd.get)
    top_month = max(by_month, key=by_month.get)
    active = sum(1 for *_, c in cells if c)
    insights = [
        ("Best day", f"{by_day[3]}", by_day[2].strftime("%b %d, %Y")),
        ("Busiest month", top_month, f"{by_month[top_month]:,} contributions"),
        ("Favourite weekday", top_wd, f"{by_wd[top_wd]:,} contributions"),
        ("Active days", f"{active}", f"of {len(cells)} · {active / len(cells):.0%}"),
    ]
    info = []
    for i, (label, value, sub) in enumerate(insights):
        x, y = 780 + (i % 2) * 200, 64 + (i // 2) * 84
        info.append(
            f'<g class="fade" style="animation-delay:{0.2 + i * 0.08:.2f}s">'
            f'<text x="{x}" y="{y}" class="mono" font-size="11" letter-spacing="1" fill="{t["faint"]}">{esc(label.upper())}</text>'
            f'<text x="{x}" y="{y + 28}" class="sans" font-size="22" font-weight="700" fill="{t["text"]}">{esc(value)}</text>'
            f'<text x="{x}" y="{y + 48}" class="mono" font-size="11.5" fill="{t["muted"]}">{esc(sub)}</text></g>'
        )

    legend = "".join(
        f'<rect x="{82 + i * 22}" y="{H - 52}" width="16" height="16" rx="4" fill="{c}"/>' for i, c in enumerate(ramp)
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="3D contribution graph">
<title>3D contribution graph: {s["year_total"]} contributions in the last year</title>
<defs>
  <radialGradient id="glow" cx=".55" cy=".7" r=".7"><stop offset="0" stop-color="{t["accent_a"]}" stop-opacity="{t["orb_opacity"] * 0.3}"/><stop offset="1" stop-color="{t["accent_a"]}" stop-opacity="0"/></radialGradient>
  <clipPath id="c"><rect width="{W}" height="{H}" rx="20"/></clipPath>
  <style>
    .sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}
    .wk{{animation:rise .9s cubic-bezier(.2,.7,.2,1) backwards}}
    @keyframes rise{{from{{opacity:0;transform:translateY(26px)}}}}
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
<text x="40" y="56" class="mono" font-size="12" letter-spacing="1.4" fill="{t["accent_b"]}">CONTRIBUTION LANDSCAPE · LAST 12 MONTHS</text>
<text x="40" y="82" class="sans" font-size="14" fill="{t["muted"]}">Each bar is one day. Height and colour grow with the work done.</text>
{"".join(info)}
{weekdays}
{bars}
{"".join(months)}
<text x="40" y="{H - 39}" class="mono" font-size="11.5" fill="{t["faint"]}">Less</text>
{legend}
<text x="{82 + 5 * 22 + 4}" y="{H - 39}" class="mono" font-size="11.5" fill="{t["faint"]}">More<tspan dx="18">· peak {peak}/day · height ∝ √contributions</tspan></text>
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
        (out / f"landscape-{mode}.svg").write_text(landscape_card(s, t), encoding="utf-8")
    cur, lon = streaks(s["days"])
    print(f"{s['year_total']} contributions, streak {cur}/{lon}, {len(s['langs'])} languages -> {out}")


if __name__ == "__main__":
    main()
