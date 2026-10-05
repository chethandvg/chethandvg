"""Shared design tokens and SVG helpers for the profile assets.

Every asset is rendered twice (dark + light) so the README can swap them with
<picture> to follow the viewer's GitHub theme.
"""

from html import escape

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Inter',Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'JetBrains Mono','Cascadia Code',Consolas,Menlo,monospace"

THEMES = {
    "dark": {
        "bg": "#0B0D14",
        "panel": "#11141D",
        "panel_alt": "#161A26",
        "border": "#232838",
        "grid": "#FFFFFF",
        "grid_opacity": 0.045,
        "text": "#E6E8F0",
        "muted": "#8B93A7",
        "faint": "#5A6178",
        "accent_a": "#8B7CFF",
        "accent_b": "#3EC6E0",
        "orb_opacity": 0.55,
        "chip_bg": "#171B28",
        # code syntax
        "kw": "#C792EA",
        "type": "#7FDBCA",
        "str": "#C3E88D",
        "prop": "#82AAFF",
        "num": "#F78C6C",
        "punct": "#89DDFF",
        "comment": "#5A6178",
        "empty_cell": "#1A1F2C",
    },
    "light": {
        "bg": "#FBFBFE",
        "panel": "#FFFFFF",
        "panel_alt": "#F4F5FA",
        "border": "#E3E6EF",
        "grid": "#0F172A",
        "grid_opacity": 0.05,
        "text": "#0F172A",
        "muted": "#525B70",
        "faint": "#8A92A6",
        "accent_a": "#5B4BFF",
        "accent_b": "#0E9DB8",
        "orb_opacity": 0.28,
        "chip_bg": "#F1F2F8",
        "kw": "#8E44C9",
        "type": "#0B8A7A",
        "str": "#4E8A12",
        "prop": "#2F5FD0",
        "num": "#C2541E",
        "punct": "#0E7FA0",
        "comment": "#8A92A6",
        "empty_cell": "#EDEFF5",
    },
}


def esc(s) -> str:
    return escape(str(s), quote=True)


def text_width(s: str, size: float, mono: bool = False, weight: int = 400) -> float:
    """Rough rendered width estimate; good enough for layout of short labels."""
    if mono:
        return len(s) * size * 0.6
    factor = 0.53 if weight < 600 else 0.57
    narrow = sum(1 for ch in s if ch in "iljtfr.,:;'|!I ")
    wide = sum(1 for ch in s if ch in "mwMW@")
    return (len(s) - narrow * 0.45 + wide * 0.35) * size * factor


def wrap(s: str, max_chars: int, max_lines: int) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;") + "…"
    return lines


def accent_gradient(t: dict, gid: str = "accent", vertical: bool = False) -> str:
    x2, y2 = ("0", "1") if vertical else ("1", "0")
    return (
        f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">'
        f'<stop offset="0" stop-color="{t["accent_a"]}"/>'
        f'<stop offset="1" stop-color="{t["accent_b"]}"/></linearGradient>'
    )


def _rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def mix(a: str, b: str, k: float) -> str:
    """Blend hex colour a toward b by k (0..1)."""
    ra, rb = _rgb(a), _rgb(b)
    return "#" + "".join(f"{round(x + (y - x) * k):02X}" for x, y in zip(ra, rb))


def shade(c: str, k: float) -> str:
    return mix(c, "#000000", k)


def contrib_ramp(t: dict) -> list[str]:
    """Five contribution levels (none → busiest), violet rising into cyan.

    Shared by every contribution visual so colour always means "how much".
    """
    peak = mix(t["accent_b"], "#FFFFFF", 0.35) if t is THEMES["dark"] else shade(t["accent_b"], 0.15)
    return [
        t["empty_cell"],
        mix(t["empty_cell"], t["accent_a"], 0.45),
        t["accent_a"],
        mix(t["accent_a"], t["accent_b"], 0.6),
        peak,
    ]


REDUCED_MOTION ="@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
