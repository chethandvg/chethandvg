"""Render the hand-designed profile assets (hero banner, project cards, divider).

Run locally after editing content below:  python scripts/static_assets.py
Output goes to assets/ and is committed.
"""

from pathlib import Path

from theme import MONO, REDUCED_MOTION, SANS, THEMES, accent_gradient, esc, text_width, wrap

OUT = Path(__file__).resolve().parent.parent / "assets"

# ── Content ──────────────────────────────────────────────────────────────────

NAME = "Chethan D V"
ROLE = "Software Engineer · Full-Stack · Applied AI"
TAGLINE = [
    "I build scalable .NET & cloud systems and",
    "ship ML-powered products. Based in Berlin.",
]
CHIPS = ["C# / .NET", "Blazor", "Azure", "Python", "ML / LLMs"]

# Each code line is a list of (token_class, text).
CODE = [
    [("kw", "var"), ("plain", " me = "), ("kw", "new"), ("plain", " "), ("type", "Engineer")],
    [("punct", "{")],
    [("plain", "    "), ("prop", "Name"), ("plain", "   = "), ("str", '"Chethan D V"'), ("punct", ",")],
    [("plain", "    "), ("prop", "Base"), ("plain", "   = "), ("str", '"Berlin, DE"'), ("punct", ",")],
    [("plain", "    "), ("prop", "Stack"), ("plain", "  = ["), ("str", '".NET"'), ("punct", ", "),
     ("str", '"Azure"'), ("punct", ", "), ("str", '"AI"'), ("plain", "]"), ("punct", ",")],
    [("plain", "    "), ("prop", "Focus"), ("plain", "  = "), ("str", '"Scalable systems"'), ("punct", ",")],
    [("plain", "    "), ("prop", "Remote"), ("plain", " = "), ("num", "true"), ("punct", ",")],
    [("punct", "};")],
    [("kw", "await"), ("plain", " me."), ("type", "ShipAsync"), ("plain", "();")],
]

PROJECTS = [
    {
        "slug": "sorting-barrier",
        "title": "Breaking the Sorting Barrier",
        "category": "ALGORITHMS · RESEARCH",
        "badge": "SSSP",
        "desc": "First C# implementation of the STOC 2025 algorithm that breaks "
                "Dijkstra's 50-year sorting barrier. 49× fewer heap operations, "
                "97 tests.",
        "lang": ("C#", "#7355DD"),
        "tags": ".NET · Graphs · STOC '25",
    },
    {
        "slug": "ollama-net",
        "title": "Ollama.Net",
        "category": "AI · LLM CLIENT",
        "badge": "NuGet",
        "desc": "Modern, async, AOT-friendly .NET client for the Ollama REST API, "
                "with streaming, tool calling, embeddings and OpenTelemetry.",
        "lang": ("C#", "#7355DD"),
        "tags": ".NET 8–10 · AOT · LLMs",
    },
    {
        "slug": "livestream",
        "title": "LiveStream App",
        "category": "REAL-TIME · CLOUD",
        "badge": "HLS",
        "desc": "Live video streaming with Blazor WebAssembly, SignalR chat, a custom "
                "FFmpeg → HLS pipeline and Azure Front Door for global delivery.",
        "lang": ("C#", "#7355DD"),
        "tags": "Blazor · SignalR · Azure",
    },
    {
        "slug": "tenant-management",
        "title": "Tenant Management",
        "category": "PROPTECH · FULL-STACK",
        "badge": "App",
        "desc": "An app that helps house owners manage their tenants' data in one "
                "place: simple, fast and built end-to-end on C# and .NET.",
        "lang": ("C#", "#7355DD"),
        "tags": ".NET · Full-stack",
    },
]

# ── Hero ─────────────────────────────────────────────────────────────────────


def hero(t: dict) -> str:
    W, H = 1200, 400
    chips, x = [], 60
    for i, c in enumerate(CHIPS):
        w = text_width(c, 13, mono=True) + 28
        chips.append(
            f'<g class="up" style="animation-delay:{0.55 + i * 0.07:.2f}s">'
            f'<rect x="{x}" y="318" width="{w:.0f}" height="30" rx="15" fill="{t["chip_bg"]}" '
            f'stroke="{t["border"]}"/>'
            f'<text x="{x + w / 2:.0f}" y="338" text-anchor="middle" class="mono" font-size="13" '
            f'fill="{t["text"]}">{esc(c)}</text></g>'
        )
        x += w + 10

    code_lines = []
    for i, line in enumerate(CODE):
        spans = "".join(
            f'<tspan fill="{t["text"] if cls == "plain" else t[cls]}">{esc(txt)}</tspan>'
            for cls, txt in line
        )
        code_lines.append(
            f'<text x="726" y="{130 + i * 24}" class="mono" font-size="14.5" xml:space="preserve">{spans}</text>'
        )
    last_w = sum(len(txt) for _, txt in CODE[-1]) * 14.5 * 0.6
    cursor_y = 130 + (len(CODE) - 1) * 24 - 13

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(NAME)} — {esc(ROLE)}">
<title>{esc(NAME)} — {esc(ROLE)}</title>
<defs>
  {accent_gradient(t)}
  <radialGradient id="orbA"><stop offset="0" stop-color="{t["accent_a"]}" stop-opacity="{t["orb_opacity"]}"/><stop offset="1" stop-color="{t["accent_a"]}" stop-opacity="0"/></radialGradient>
  <radialGradient id="orbB"><stop offset="0" stop-color="{t["accent_b"]}" stop-opacity="{t["orb_opacity"]}"/><stop offset="1" stop-color="{t["accent_b"]}" stop-opacity="0"/></radialGradient>
  <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="{t["grid"]}" stroke-opacity="{t["grid_opacity"]}"/></pattern>
  <radialGradient id="gridFade" cx="0.3" cy="0.35" r="0.85"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
  <mask id="gridMask"><rect width="{W}" height="{H}" fill="url(#gridFade)"/></mask>
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="24"/></clipPath>
  <style>
    .sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}
    .orbA{{animation:driftA 16s ease-in-out infinite alternate}}
    .orbB{{animation:driftB 19s ease-in-out infinite alternate}}
    @keyframes driftA{{to{{transform:translate(140px,50px)}}}}
    @keyframes driftB{{to{{transform:translate(-160px,-40px)}}}}
    .up{{animation:up .7s cubic-bezier(.2,.7,.2,1) backwards}}
    @keyframes up{{from{{opacity:0;transform:translateY(10px)}}}}
    .cursor{{animation:blink 1.1s steps(1) infinite}}
    @keyframes blink{{50%{{opacity:0}}}}
    .scan{{animation:scan 6s ease-in-out infinite}}
    @keyframes scan{{0%,100%{{opacity:.0}}50%{{opacity:.9}}}}
    {REDUCED_MOTION}
  </style>
</defs>
<g clip-path="url(#frame)">
  <rect width="{W}" height="{H}" fill="{t["bg"]}"/>
  <rect width="{W}" height="{H}" fill="url(#grid)" mask="url(#gridMask)"/>
  <circle class="orbA" cx="180" cy="40" r="320" fill="url(#orbA)"/>
  <circle class="orbB" cx="1060" cy="380" r="340" fill="url(#orbB)"/>
  <rect class="scan" x="0" y="0" width="{W}" height="2" fill="url(#accent)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="24" fill="none" stroke="{t["border"]}"/>

<g class="up" style="animation-delay:.05s">
  <circle cx="66" cy="88" r="4" fill="#3FB950"><animate attributeName="opacity" values="1;.35;1" dur="2.4s" repeatCount="indefinite"/></circle>
  <text x="80" y="93" class="mono" font-size="14" fill="{t["muted"]}">open to remote opportunities · Berlin, DE</text>
</g>
<text class="sans up" style="animation-delay:.15s" x="58" y="178" font-size="76" font-weight="800" letter-spacing="-2.5" fill="url(#accent)">{esc(NAME)}</text>
<text class="sans up" style="animation-delay:.28s" x="60" y="226" font-size="25" font-weight="600" letter-spacing="-.3" fill="{t["text"]}">{esc(ROLE)}</text>
<g class="up" style="animation-delay:.4s">
  <text x="60" y="266" class="sans" font-size="17" fill="{t["muted"]}">{esc(TAGLINE[0])}</text>
  <text x="60" y="292" class="sans" font-size="17" fill="{t["muted"]}">{esc(TAGLINE[1])}</text>
</g>
{"".join(chips)}

<g class="up" style="animation-delay:.3s">
  <rect x="700" y="52" width="452" height="300" rx="16" fill="{t["panel"]}" fill-opacity=".82" stroke="{t["border"]}"/>
  <path d="M700 68a16 16 0 0 1 16-16h420a16 16 0 0 1 16 16v28H700z" fill="{t["panel_alt"]}" fill-opacity=".9"/>
  <circle cx="722" cy="74" r="5.5" fill="#FF5F57"/><circle cx="740" cy="74" r="5.5" fill="#FEBC2E"/><circle cx="758" cy="74" r="5.5" fill="#28C840"/>
  <text x="926" y="79" text-anchor="middle" class="mono" font-size="12.5" fill="{t["muted"]}">Program.cs</text>
  <line x1="700" y1="96" x2="1152" y2="96" stroke="{t["border"]}"/>
  {"".join(code_lines)}
  <rect class="cursor" x="{726 + last_w + 3:.0f}" y="{cursor_y}" width="9" height="17" rx="1" fill="{t["accent_b"]}"/>
</g>
</svg>
'''


# ── Project card ─────────────────────────────────────────────────────────────


def project_card(p: dict, t: dict) -> str:
    W, H = 400, 200
    lines = wrap(p["desc"], 50, 3)
    desc = "".join(
        f'<text x="24" y="{104 + i * 21}" class="sans" font-size="13.5" fill="{t["muted"]}">{esc(l)}</text>'
        for i, l in enumerate(lines)
    )
    lang, color = p["lang"]
    lang_w = text_width(lang, 12.5, mono=True)
    bw = text_width(p["badge"], 11, mono=True) + 18
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{esc(p["title"])}">
<title>{esc(p["title"])}</title>
<defs>
  {accent_gradient(t)}
  <radialGradient id="glow" cx="0" cy="0" r="1"><stop offset="0" stop-color="{t["accent_a"]}" stop-opacity="{t["orb_opacity"] * 0.45}"/><stop offset="1" stop-color="{t["accent_a"]}" stop-opacity="0"/></radialGradient>
  <clipPath id="c"><rect width="{W}" height="{H}" rx="16"/></clipPath>
  <style>.sans{{font-family:{SANS}}} .mono{{font-family:{MONO}}}</style>
</defs>
<g clip-path="url(#c)">
  <rect width="{W}" height="{H}" fill="{t["panel"]}"/>
  <rect width="{W}" height="{H}" fill="url(#glow)"/>
  <rect width="{W}" height="3" fill="url(#accent)"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" stroke="{t["border"]}"/>
<text x="24" y="40" class="mono" font-size="11" letter-spacing="1.4" fill="{t["accent_b"]}">{esc(p["category"])}</text>
<rect x="{W - 24 - bw:.0f}" y="25" width="{bw:.0f}" height="22" rx="11" fill="{t["chip_bg"]}" stroke="{t["border"]}"/>
<text x="{W - 24 - bw / 2:.0f}" y="40" text-anchor="middle" class="mono" font-size="11" fill="{t["muted"]}">{esc(p["badge"])}</text>
<text x="24" y="72" class="sans" font-size="20" font-weight="700" letter-spacing="-.3" fill="{t["text"]}">{esc(p["title"])}</text>
{desc}
<line x1="24" y1="164" x2="{W - 24}" y2="164" stroke="{t["border"]}"/>
<circle cx="30" cy="182" r="6" fill="{color}"/>
<text x="44" y="186.5" class="mono" font-size="12.5" fill="{t["text"]}">{esc(lang)}</text>
<text x="{44 + lang_w + 14:.0f}" y="186.5" class="mono" font-size="12.5" fill="{t["faint"]}">{esc(p["tags"])}</text>
<text x="{W - 24}" y="187" text-anchor="end" class="sans" font-size="15" fill="{t["muted"]}">↗</text>
</svg>
'''


# ── Divider ──────────────────────────────────────────────────────────────────


def divider(t: dict) -> str:
    W, H = 1200, 24
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" aria-hidden="true">
<defs>
  <linearGradient id="d" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="{t["accent_a"]}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{t["accent_a"]}"/>
    <stop offset="1" stop-color="{t["accent_b"]}" stop-opacity="0"/>
  </linearGradient>
  <style>.p{{animation:p 5s ease-in-out infinite alternate}}@keyframes p{{from{{transform:translateX(-420px)}}to{{transform:translateX(420px)}}}}{REDUCED_MOTION}</style>
</defs>
<rect x="0" y="11.5" width="{W}" height="1" fill="url(#d)" opacity=".55"/>
<circle class="p" cx="600" cy="12" r="3" fill="{t["accent_b"]}"/>
</svg>
'''


def main():
    OUT.mkdir(exist_ok=True)
    for mode, t in THEMES.items():
        (OUT / f"hero-{mode}.svg").write_text(hero(t), encoding="utf-8")
        (OUT / f"divider-{mode}.svg").write_text(divider(t), encoding="utf-8")
        for p in PROJECTS:
            (OUT / f"project-{p['slug']}-{mode}.svg").write_text(project_card(p, t), encoding="utf-8")
    print(f"wrote assets to {OUT}")


if __name__ == "__main__":
    main()
