#!/usr/bin/env python3
"""Regenerate every file in assets/ from the portfolio checkout.

    python3 scripts/build.py /path/to/keitan-website

Python 3 standard library plus Pillow. Colours come from the site's
src/styles/palette.ts, pixel art from public/art and src/assets/svg, and the
fonts are the committed subsets in scripts/fonts (made by subset_fonts.py).
Every SVG is self-contained (fonts and images inlined) because GitHub shows
README images through <img>, where nothing external may load. All motion is CSS
and stops under prefers-reduced-motion, leaving a complete still frame.
"""
import base64
import io
import json
import random
import re
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"

# ---------------------------------------------------------------------------
# Content. Everything the images say is defined here (the ChutaTrip stats live in README.md, not in any SVG).
# ---------------------------------------------------------------------------
DATA = {
    "handle": "Keitan",
    "name": "Keith Daniel Tan",
    "title": "IT & Cybersecurity",
    "location": "Las Vegas, NV",
    "tagline": "CyberCorps SFS Scholar. Security+ certified. Homelab enjoyer.",
    "quests": [
        {
            "name": "ChutaTrip",
            "year": "2026",
            "status": "completed",
            "featured": "1.0 shipped \u00b7 my biggest build",
            "summary": "A Japan trip planner for one person or a whole group, in nine languages: "
            "every day in order, a live map, tickets that work offline, and a budget that settles itself. Installs like an app.",
            "stack": ["TypeScript", "React", "Next.js", "Supabase", "PostgreSQL", "Vercel",
                      "Tailwind CSS", "MapLibre", "Playwright"],
        },
        {
            "name": "Proxmox Cyber Lab",
            "year": "2025",
            "status": "completed",
            "summary": "A segmented homelab for defensive security practice, threat modeling, and monitoring.",
            "stack": ["Proxmox VE", "Kali Linux", "Ubuntu", "Windows", "Wireshark", "WireGuard", "n8n"],
        },
        {
            "name": "AI-Enabled Discord Bot",
            "year": "2025",
            "status": "completed",
            "summary": "A 24/7 AI chat bot running in a hardened Proxmox container.",
            "stack": ["Python", "PostgreSQL", "SQLAlchemy", "Alembic", "OpenAI API", "Proxmox"],
        },
        {
            "name": "This Portfolio",
            "year": "2026",
            "status": "in progress",
            "summary": "A portfolio styled after classic MMO interfaces, with an animated pixel-art world and a 3D pet.",
            "stack": ["TypeScript", "Next.js", "React", "Tailwind CSS", "three.js", "Vercel"],
        },
    ],
    "skills": [
        ("Security", [("Defense", "defense"), ("Offense", "offense"), ("Vuln Management", "vuln-management"),
                      ("Identity & Access", "identity-access"), ("Compliance", "compliance")]),
        ("Infrastructure", [("Networking", "networking"), ("Linux", "linux"),
                            ("Windows & macOS", "windows"), ("Virtualization", "virtualization")]),
        ("Engineering & Leadership", [("Scripting", "scripting"), ("AI & ML", "ai-ml"), ("Languages", "languages"),
                                      ("Hardware", "hardware"), ("Leadership", "leadership")]),
    ],
    "achievements": {
        "top": {"tag": "1st Place", "title": "BSides Las Vegas Pros vs Joes CTF", "sub": "2026"},
        "rows": [
            {"icon": "ui/star", "title": "NCAE Cyber Games 2025", "tag": "3rd Place",
             "sub": "Also named Most Improved Teammate"},
            {"icon": "skills/compliance", "title": "CompTIA Security+", "sub": "Earned June 2025"},
            {"icon": "skills/defense", "title": "CyberCorps: Scholarship for Service",
             "sub": "National Science Foundation"},
            {"icon": "map/log", "title": "B.S. Computer Science",
             "sub": "University of Nevada, Las Vegas, Spring 2026"},
            {"icon": "items/item-resume", "title": "Co-author",
             "sub": "Single-View Tomographic Reconstruction Using Learned Primal Dual. "
                    "Submitted to IEEE Transactions on Computational Imaging (2026)"},
        ],
    },
    "games": [
        {"game": "RuneScape", "rank": "First game", "tier": "bronze", "icon": "skills/game-sword"},
        {"game": "Team Fortress 2", "rank": "Demoman", "note": "Competitive UGC + ESEA Open",
         "tier": "orange", "icon": "skills/game-bomb"},
        {"game": "League of Legends", "rank": "Emerald 2", "tier": "green", "icon": "skills/game-gem"},
        {"game": "Valorant", "rank": "Immortal 2", "tier": "red", "icon": "skills/game-gem"},
        {"game": "Overwatch", "rank": "Grandmaster", "tier": "gold", "icon": "skills/game-gem"},
        {"game": "Marvel Rivals", "rank": "Celestial", "tier": "celestial", "icon": "skills/game-gem"},
    ],
    "chat": [
        ("system", "Welcome to Keitan's profile."),
        ("player", "Find me on Discord: @keithdanieltan"),
        ("player", "Or visit keithdanieltan.com"),
    ],
    "buttons": [
        ("website", "Website", "items/item-globe"),
        ("linkedin", "LinkedIn", "items/item-linkedin"),
        ("chutatrip", "ChutaTrip", "items/item-map"),
        ("paper", "Paper", "items/item-resume"),
    ],
}

# ---------------------------------------------------------------------------
# Setup: palette, fonts, textures, icons
# ---------------------------------------------------------------------------
SITE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
if SITE is None or not (SITE / "src/styles/palette.ts").exists():
    sys.exit("usage: python3 scripts/build.py /path/to/keitan-website")

_pal_src = (SITE / "src/styles/palette.ts").read_text()
_pal_src = _pal_src[_pal_src.index("export const palette"):]
_pal_src = _pal_src[: _pal_src.index("} as const")] if "} as const" in _pal_src else _pal_src
P = dict(re.findall(r"^\s*(\w+):\s*'(#[0-9a-fA-F]{6})'", _pal_src, re.M))
OUT = P["outline"]

METRICS = json.loads((HERE / "fonts/metrics.json").read_text())
FONT_FILES = {"j": ("Jersey 10", "jersey10"), "v": ("VT323", "vt323")}
FONT_KEY = {"j": "jersey10", "v": "vt323"}



def tw(s, size, f="j"):
    """Width of a string in px at a font size, from the committed metrics."""
    m = METRICS[FONT_KEY[f]]
    return sum(m["adv"].get(c, m["adv"]["n"]) for c in s) / m["upem"] * size


def wrap(s, size, maxw, f="j"):
    lines, cur = [], ""
    for word in s.split(" "):
        t = (cur + " " + word).strip()
        if cur and tw(t, size, f) * 1.02 > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def b64(data):
    return base64.b64encode(data).decode()


_font_cache = {}


def font_face(f):
    if f not in _font_cache:
        fam, fn = FONT_FILES[f]
        data = (HERE / "fonts" / f"{fn}.woff2").read_bytes()
        _font_cache[f] = (
            f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64(data)}) format('woff2');}}"
        )
    return _font_cache[f]


def png_uri(im):
    """Palette PNG as a data URI. Transparent pixels use palette index 0."""
    im = im.convert("RGBA")
    px = [im.getpixel((x, y)) for y in range(im.height) for x in range(im.width)]
    colors = sorted({p[:3] for p in px if p[3] > 0})
    has_alpha = any(p[3] == 0 for p in px)
    off = 1 if has_alpha else 0
    index = {c: i + off for i, c in enumerate(colors)}
    out = Image.new("P", im.size, 0)
    out.putdata([0 if p[3] == 0 else index[p[:3]] for p in px])
    pal = [0, 0, 0] if has_alpha else []
    for c in colors:
        pal += list(c)
    out.putpalette(pal)
    buf = io.BytesIO()
    kw = {"transparency": 0} if has_alpha else {}
    out.save(buf, "PNG", optimize=True, **kw)
    return "data:image/png;base64," + b64(buf.getvalue())


def art(name, crop=None):
    im = Image.open(SITE / "public/art" / name).convert("RGBA")
    return im.crop(crop) if crop else im


ICON_RE = re.compile(r'<g style="fill:var\(--px-(\w+),(#[0-9a-fA-F]{6})\)">')


def icon_inner(name, tint=None):
    src = (SITE / "src/assets/svg" / f"{name}.svg").read_text()
    tint = tint or {}

    def sub(m):
        col = tint.get(m.group(1), P.get(m.group(1), m.group(2)))
        return f'<g fill="{col}">'

    inner = src[src.index(">") + 1: src.rindex("</svg>")]
    return ICON_RE.sub(sub, inner)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def n(v):
    """Compact number for attributes."""
    return f"{v:.2f}".rstrip("0").rstrip(".") if isinstance(v, float) else str(v)


# ---------------------------------------------------------------------------
# SVG document builder
# ---------------------------------------------------------------------------
BASE_CSS = (
    "text{font-family:'Jersey 10',monospace}.v{font-family:'VT323',monospace}"
    "image{image-rendering:pixelated}"
    "@keyframes rv{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
    "@keyframes show{from{opacity:0}to{opacity:1}}"
    "@keyframes blink{50%{opacity:0}}"
    ".rv{animation:rv .55s cubic-bezier(.2,.9,.3,1) both;animation-delay:var(--d,0s)}"
    ".sh{animation:show .01s steps(1,start) both;animation-delay:var(--d,0s)}"
    "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
)


class Doc:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.body, self.defs, self.css = [], [], []
        self.fonts = set()
        self.icons = {}
        self.pats = {}

    # -- primitives
    def add(self, s):
        self.body.append(s)

    def rect(self, x, y, w, h, fill, extra=""):
        self.add(f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{fill}"{extra}/>')

    def text(self, x, y, runs, size, fill=None, f="j", anchor="start", sh=1, shfill=None, extra=""):
        """Text with a hard drop shadow. runs: a string or [(string, colour)]."""
        self.fonts.add(f)
        if isinstance(runs, str):
            runs = [(runs, fill)]
        cls = ' class="v"' if f == "v" else ""
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""

        def one(dx, colour_of):
            spans = "".join(
                f'<tspan fill="{colour_of(c)}">{esc(t)}</tspan>' if len(runs) > 1 else esc(t) for t, c in runs
            )
            fl = "" if len(runs) > 1 else f' fill="{colour_of(runs[0][1])}"'
            return f'<text{cls} x="{n(x + dx)}" y="{n(y + dx)}" font-size="{size}"{fl}{a}>{spans}</text>'

        s = ""
        if sh:
            s += one(sh, lambda c: shfill or OUT)
        s += one(0, lambda c: c)
        if extra:
            s = f"<g {extra}>{s}</g>"
        self.add(s)

    def icon(self, name, x, y, size, tint=None, key=None, extra=""):
        key = key or name.replace("/", "-") + ("-" + key if key else "")
        if key not in self.icons:
            self.icons[key] = f'<symbol id="i-{key}" viewBox="0 0 16 16">{icon_inner(name, tint)}</symbol>'
        self.add(f'<use href="#i-{key}" x="{n(x)}" y="{n(y)}" width="{size}" height="{size}"{extra}/>')

    def pattern(self, name, src, w, h):
        if name not in self.pats:
            uri = png_uri(art(src))
            self.pats[name] = (
                f'<pattern id="{name}" width="{w}" height="{h}" patternUnits="userSpaceOnUse">'
                f'<image href="{uri}" width="{w}" height="{h}" preserveAspectRatio="none"/></pattern>'
            )
        return f"url(#{name})"

    def render(self):
        fonts = "".join(font_face(f) for f in sorted(self.fonts))
        css = fonts + BASE_CSS + "".join(self.css)
        defs = "".join(self.defs) + "".join(self.pats.values()) + "".join(self.icons[k] for k in sorted(self.icons))
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" '
            f'height="{self.h}" shape-rendering="crispEdges">'
            f"<style>{css}</style><defs>{defs}</defs>{''.join(self.body)}"
            f'</svg>\n'
        )


def delay(i, step=0.12, base=0.1):
    return f' class="rv" style="--d:{base + i * step:.2f}s"'


# ---------------------------------------------------------------------------
# Window frame (stone, gold studs) and shared widgets
# ---------------------------------------------------------------------------
W = 840
CX, CW = 30, 780  # content column inside a window


def frame(d, w, h, body="rock", title=None, icon=None, tint=None):
    """Stone window: outline, stone band with bevel, gold studs, then the body.

    body=None draws only the ring (the hero and chat paint their own inside)."""
    stone = d.pattern("stone", "stone.webp", 128, 64)
    if body is None:
        parts = [(0, 0, w, 14), (0, h - 14, w, 14), (0, 0, 14, h), (w - 14, 0, 14, h)]
        for px, py, pw, ph in parts:
            d.rect(px, py, pw, ph, P["frame700"])
            d.rect(px, py, pw, ph, stone, ' opacity=".55"')
        d.rect(0, 0, w, 2, OUT)
        d.rect(0, h - 2, w, 2, OUT)
        d.rect(0, 0, 2, h, OUT)
        d.rect(w - 2, 0, 2, h, OUT)
        d.rect(2, 2, w - 4, 2, P["frame400"])
        d.rect(2, 2, 2, h - 4, P["frame400"])
        d.rect(2, h - 4, w - 4, 2, P["frame900"])
        d.rect(w - 4, 2, 2, h - 4, P["frame900"])
        d.rect(12, 12, w - 24, 2, OUT)
        d.rect(12, h - 14, w - 24, 2, OUT)
        d.rect(12, 12, 2, h - 24, OUT)
        d.rect(w - 14, 12, 2, h - 24, OUT)
    else:
        d.rect(0, 0, w, h, OUT)
        d.rect(2, 2, w - 4, h - 4, P["frame700"])
        d.rect(2, 2, w - 4, h - 4, stone, ' opacity=".55"')
        d.rect(2, 2, w - 4, 2, P["frame400"])
        d.rect(2, 2, 2, h - 4, P["frame400"])
        d.rect(2, h - 4, w - 4, 2, P["frame900"])
        d.rect(w - 4, 2, 2, h - 4, P["frame900"])
        d.rect(12, 12, w - 24, h - 24, OUT)
    if body == "rock":
        d.rect(14, 14, w - 28, h - 28, P["rock900"])
        d.rect(14, 14, w - 28, h - 28, d.pattern("rockd", "rock-dark.webp", 64, 64), ' opacity=".75"')
        d.rect(14, 14, w - 28, 2, P["rock950"])
        d.rect(14, 14, 2, h - 28, P["rock950"])
        d.rect(14, h - 16, w - 28, 2, P["rock700"])
        d.rect(w - 16, 14, 2, h - 28, P["rock700"])
    for sx, sy in ((3, 3), (w - 11, 3), (3, h - 11), (w - 11, h - 11)):
        d.rect(sx, sy, 8, 8, P["gold700"])
        d.rect(sx + 1, sy + 1, 6, 6, P["gold500"])
        d.rect(sx + 1, sy + 1, 3, 3, P["gold300"])
    if title:
        d.rect(14, 14, w - 28, 64, P["tabRed700"])
        d.rect(14, 14, w - 28, 2, P["tabRed300"])
        d.rect(14, 14, 2, 64, P["tabRed300"])
        d.rect(14, 76, w - 28, 2, P["tabRed900"])
        d.rect(w - 16, 14, 2, 64, P["tabRed900"])
        d.rect(14, 78, w - 28, 2, OUT)
        d.icon(icon, 28, 22, 48, tint)
        d.text(88, 58, title, 42, P["uiYellow"], sh=3)
        d.icon("ui/close", w - 58, 30, 32)
    return 96 if title else 28


def chip(d, x, y, label, size=24, h=36):
    w = tw(label, size) + 24
    d.rect(x, y, w, h, OUT)
    d.rect(x + 2, y + 2, w - 4, h - 4, P["rock700"])
    d.rect(x + 2, y + 2, w - 4, 2, P["rock500"])
    d.rect(x + 2, y + 2, 2, h - 4, P["rock500"])
    d.rect(x + 2, y + h - 4, w - 4, 2, P["rock900"])
    d.rect(x + w - 4, y + 2, 2, h - 4, P["rock900"])
    d.text(x + 12, y + h - 10, label, size, P["parch100"], sh=1)
    return w


def chips(d, x, y, labels, maxw, gap=8, size=24, h=36):
    """Flow chips into rows. Returns the y after the last row."""
    cx, cy = x, y
    for lab in labels:
        w = tw(lab, size) + 24
        if cx > x and cx + w > x + maxw:
            cx, cy = x, cy + h + gap
        chip(d, cx, cy, lab, size, h)
        cx += w + gap
    return cy + h


def slot(d, x, y, w, h, fill=None):
    d.rect(x, y, w, h, OUT)
    d.rect(x + 2, y + 2, w - 4, h - 4, fill or P["rock950"])
    d.rect(x + 2, y + 2, w - 4, 2, P["black"])
    d.rect(x + 2, y + 2, 2, h - 4, P["black"])
    d.rect(x + 2, y + h - 3, w - 4, 1, P["rock500"])
    d.rect(x + w - 3, y + 2, 1, h - 4, P["rock500"])


def card(d, x, y, w, h, rim=None):
    d.rect(x, y, w, h, OUT)
    d.rect(x + 2, y + 2, w - 4, h - 4, P["rock800"])
    d.rect(x + 2, y + 2, w - 4, 2, P["rock600"])
    d.rect(x + 2, y + 2, 2, h - 4, P["rock600"])
    d.rect(x + 2, y + h - 4, w - 4, 2, P["rock950"])
    d.rect(x + w - 4, y + 2, 2, h - 4, P["rock950"])
    if rim:
        d.rect(x + 2, y + 2, w - 4, h - 4, "none", f' stroke="{rim}" stroke-width="2"')


STATUS = {
    "completed": ("status/completed", "uiGreen", "Completed"),
    "in progress": ("status/in-progress", "uiYellow", "In progress"),
}


# ---------------------------------------------------------------------------
# hero.svg
# ---------------------------------------------------------------------------
def build_hero():
    ART_X, ART_Y, AW, AH, S = 50, 40, 420, 200, 2
    HW, HH = AW * S, AH * S  # 840 x 400
    d = Doc(HW, HH)
    crop = (ART_X, ART_Y, ART_X + AW, ART_Y + AH)
    ax = lambda v: (v - ART_X) * S
    ay = lambda v: (v - ART_Y) * S
    rng = random.Random(20260)

    d.fonts.update({"j", "v"})
    d.defs.append(
        f'<radialGradient id="glow"><stop offset="0" stop-color="{P["sun"]}" stop-opacity=".75"/>'
        f'<stop offset=".45" stop-color="{P["dusk200"]}" stop-opacity=".3"/>'
        f'<stop offset="1" stop-color="{P["dusk200"]}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="moonglow"><stop offset="0" stop-color="{P["sun"]}" stop-opacity=".5"/>'
        f'<stop offset="1" stop-color="{P["sun"]}" stop-opacity="0"/></radialGradient>'
        f'<linearGradient id="scrim" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="{P["night950"]}" stop-opacity=".62"/>'
        f'<stop offset=".5" stop-color="{P["night950"]}" stop-opacity=".3"/>'
        f'<stop offset="1" stop-color="{P["night950"]}" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="gold" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="{P["parch050"]}"/>'
        f'<stop offset=".35" stop-color="{P["gold300"]}"/><stop offset="1" stop-color="{P["gold500"]}"/></linearGradient>'
    )
    d.css.append(
        "@keyframes tw{0%,100%{opacity:.15}50%{opacity:1}}"
        ".st{animation:tw var(--t,3s) ease-in-out infinite;animation-delay:var(--d,0s)}"
        "@keyframes dr{from{transform:translateX(var(--a))}to{transform:translateX(var(--b))}}"
        ".dr{animation:dr var(--t) linear infinite;animation-delay:var(--d)}"
        "@keyframes flut{to{transform:translateX(var(--f))}}"
        ".fl{animation:flut var(--t) steps(var(--n)) infinite;animation-delay:var(--d,0s)}"
        "@keyframes pulse{from{opacity:.55;transform:scale(.96)}to{opacity:1;transform:scale(1.06)}}"
        ".pu{animation:pulse 5s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:center}"
        "@keyframes ff{0%,100%{opacity:0;transform:translate(0,0)}20%{opacity:1}50%{opacity:.8;"
        "transform:translate(var(--x),var(--y))}80%{opacity:.6}}"
        ".ff{animation:ff var(--t) ease-in-out infinite;animation-delay:var(--d)}"
        "@keyframes sheen{from{transform:translateX(-420px)}to{transform:translateX(560px)}}"
        ".sw{animation:sheen 6.5s ease-in-out 2.5s infinite}"
        "@keyframes uncover{from{transform:scaleX(1)}to{transform:scaleX(0)}}"
        ".cv{transform:scaleX(0);transform-box:fill-box;transform-origin:100% 50%}"
    )

    def img(name, layer):
        uri = png_uri(art(f"landscape/{layer}.webp", crop))
        d.add(f'<image href="{uri}" x="0" y="0" width="{HW}" height="{HH}" preserveAspectRatio="none"/>')

    img("sky", "sky")

    # stars twinkling over the baked ones
    for i in range(30):
        x, y = rng.randrange(8, HW - 8, 2), rng.randrange(14, 160, 2)
        sz = 4 if rng.random() < 0.25 else 2
        d.add(
            f'<rect class="st" x="{x}" y="{y}" width="{sz}" height="{sz}" fill="{P["star"]}" '
            f'style="--t:{2 + rng.random() * 3:.1f}s;--d:-{rng.random() * 4:.1f}s"/>'
        )
    # moon
    mx, my = 746, 18
    d.add(f'<circle class="pu" cx="{mx + 15}" cy="{my + 15}" r="34" fill="url(#moonglow)"/>')
    d.add(
        f'<image href="{png_uri(art("landscape/moon.webp"))}" x="{mx}" y="{my}" width="30" height="30"/>'
    )
    # sun glow
    d.add(f'<circle class="pu" cx="{ax(328)}" cy="{ay(158)}" r="150" fill="url(#glow)"/>')

    # clouds: (file, w, h, row, start x, duration, delay)
    clouds = [("cloud-1", 80, 22, 44, 100, 140, -30), ("cloud-2", 56, 16, 70, 330, 100, -10),
              ("cloud-3", 68, 18, 58, 20, 170, -95)]
    for nm, cw, ch, row, x0, dur, dl in clouds:
        uri = png_uri(art(f"landscape/{nm}.webp"))
        a, b = -(x0 + cw * 2 + 10), HW - x0 + 10
        d.add(
            f'<g transform="translate({x0} {ay(row)})"><g class="dr" style="--a:{a}px;--b:{b}px;--t:{dur}s;--d:{dl}s">'
            f'<image href="{uri}" width="{cw * 2}" height="{ch * 2}" preserveAspectRatio="none"/></g></g>'
        )
    # birds (2 frames of 7x4)
    birds = [(92, 1.4, 520, 26, -4), (82, 1.15, 560, 26, -5), (102, 1.15, 250, 34, -16)]
    buri = png_uri(art("landscape/birds.webp"))
    for row, sc, x0, dur, dl in birds:
        bw, bh = 7 * sc * 2, 4 * sc * 2
        a, b = -(x0 + 40), HW - x0 + 40
        d.add(
            f'<g transform="translate({x0} {ay(row)})"><g class="dr" style="--a:{a}px;--b:{b}px;--t:{dur}s;--d:{dl}s">'
            f'<svg width="{bw:g}" height="{bh:g}" viewBox="0 0 7 4"><image class="fl" href="{buri}" width="14" height="4" '
            f'style="--f:-7px;--n:2;--t:.45s"/></svg></g></g>'
        )

    img("far", "far")
    img("mid", "mid")

    # sprites on the mid layer: flags (3 frames of 9x6), waterfall (3 of 7x26)
    furi = png_uri(art("landscape/flag.webp"))
    for fx, fy, dur, dl in [(365, 82, 0.9, -0.2), (341, 114, 1, -0.5), (389, 104, 0.85, -0.1), (412, 110, 0.95, -0.7)]:
        d.add(
            f'<svg x="{ax(fx)}" y="{ay(fy)}" width="18" height="12" viewBox="0 0 9 6"><image class="fl" href="{furi}" '
            f'width="27" height="6" style="--f:-27px;--n:3;--t:{dur}s;--d:{dl}s"/></svg>'
        )
    wuri = png_uri(art("landscape/waterfall.webp"))
    d.add(
        f'<svg x="{ax(340)}" y="{ay(171)}" width="14" height="52" viewBox="0 0 7 26"><image class="fl" href="{wuri}" '
        f'width="21" height="26" style="--f:-21px;--n:3;--t:.42s"/></svg>'
    )
    # glints on the sun's path across the lake
    for i in range(9):
        gx, gy = 300 + rng.random() * 16, 199 + rng.random() * 12
        gw = 2 if rng.random() < 0.5 else 3
        d.add(
            f'<rect class="st" x="{n(round(ax(gx)))}" y="{n(round(ay(gy)))}" width="{gw * 2}" height="2" fill="{P["sunCore"]}" '
            f'style="--t:{1.4 + rng.random() * 2:.1f}s;--d:-{rng.random() * 3:.1f}s"/>'
        )

    img("near", "near")

    # fireflies near the treeline
    for i in range(12):
        x, y = rng.randrange(20, HW - 20, 2), ay(176 + rng.random() * 52)
        y = round(y / 2) * 2
        d.add(
            f'<g class="ff" opacity=".8" style="--x:{(rng.random() - .5) * 90:.0f}px;--y:-{20 + rng.random() * 50:.0f}px;'
            f'--t:{6 + rng.random() * 7:.1f}s;--d:-{rng.random() * 10:.1f}s">'
            f'<rect x="{x - 2}" y="{y - 2}" width="8" height="8" fill="{P["firefly"]}" opacity=".25"/>'
            f'<rect x="{x}" y="{y}" width="4" height="4" fill="{P["firefly"]}"/></g>'
        )

    # legibility scrim behind the title
    d.rect(0, 0, 560, HH, "url(#scrim)")

    # title block
    d.add('<g class="rv" style="--d:.05s">')
    d.fonts.add("j")
    title = DATA["handle"]
    d.add(f'<clipPath id="tclip"><text x="40" y="146" font-size="168">{esc(title)}</text></clipPath>')
    d.add(f'<text x="45" y="151" font-size="168" fill="{OUT}">{esc(title)}</text>')
    d.add(f'<text x="43" y="149" font-size="168" fill="{P["gold700"]}">{esc(title)}</text>')
    d.add(f'<text x="40" y="146" font-size="168" fill="url(#gold)">{esc(title)}</text>')
    d.add(
        f'<g clip-path="url(#tclip)"><rect class="sw" x="0" y="40" width="46" height="130" fill="{P["white"]}" '
        f'opacity=".38" transform="skewX(-20)"/></g>'
    )
    d.add("</g>")
    d.add('<g class="rv" style="--d:.3s">')
    d.text(44, 196, DATA["name"], 48, P["parch100"], sh=3)
    d.text(44, 236, [(DATA["title"], P["uiOrange"]), (" · ", P["parch300"]),
                     (DATA["location"], P["parch100"])], 32, sh=2)
    d.add("</g>")

    # chat line at the bottom: the tagline, typed out once
    sx, sy, sw_, sh_ = 28, 350, 784, 44
    d.rect(sx, sy, sw_, sh_, OUT)
    d.rect(sx + 2, sy + 2, sw_ - 4, sh_ - 4, P["night950"])
    d.rect(sx + 2, sy + 2, sw_ - 4, 2, P["night700"])
    d.rect(sx + 2, sy + 2, 2, sh_ - 4, P["night700"])
    size = 30
    tx0, ty = sx + 18, sy + 32
    name_run, msg = DATA["handle"] + ": ", DATA["tagline"]
    full = tw(name_run + msg, size)
    steps = len(name_run + msg)
    d.text(tx0, ty, [(name_run, P["uiYellow"]), (msg, P["white"])], size, sh=2)
    tdur, tdel = 2.6, 1.2
    d.add(
        f'<rect class="cv" x="{tx0 - 2}" y="{sy + 4}" width="{n(round(full + 12))}" height="{sh_ - 8}" fill="{P["night950"]}" '
        f'style="animation:uncover {tdur}s steps({steps}) {tdel}s both"/>'
    )
    d.add(
        f'<rect x="{n(round(tx0 + full + 3))}" y="{ty - 22}" width="12" height="26" fill="{P["uiYellow"]}" '
        f'style="--L:{n(round(full))}px;animation:cur {tdur}s steps({steps}) {tdel}s both,blink 1s steps(1) {tdel + tdur}s infinite"/>'
    )
    d.css.append("@keyframes cur{from{transform:translateX(calc(var(--L) * -1))}to{transform:none}}")

    # frame on top
    frame(d, HW, HH, body=None)
    return d


# ---------------------------------------------------------------------------
# quests.svg
# ---------------------------------------------------------------------------
def build_quests():
    d = Doc(W, 100)
    y = 96
    qs = DATA["quests"]
    ops = []

    def feat(q, y0, i):
        pad = 24
        iw = CW - 2 * pad
        lines = wrap(q["summary"], 30, iw)
        stack_y = y0 + 168 + len(lines) * 38 + 8
        end = chips_height(q["stack"], iw, 24) + stack_y + pad
        h = end - y0
        ops.append(("feat", q, y0, h, lines, 0, stack_y, i))
        return h

    def chips_height(labels, maxw, size):
        cx, rows = 0, 1
        for lab in labels:
            w = tw(lab, size) + 24
            if cx > 0 and cx + w > maxw:
                cx, rows = 0, rows + 1
            cx += w + 8
        return rows * 36 + (rows - 1) * 8

    def row(q, y0, i):
        pad = 18
        iw = CW - 2 * pad
        lines = wrap(q["summary"], 26, iw)
        stack_y = y0 + 76 + len(lines) * 32 + 8
        end = stack_y + chips_height(q["stack"], iw, 24) + pad
        ops.append(("row", q, y0, end - y0, lines, stack_y, i))
        return end - y0

    y += feat(qs[0], y, 0) + 16
    for i, q in enumerate(qs[1:], 1):
        y += row(q, y, i) + 14
    H = y - 14 + 28
    d.h = H
    frame(d, W, H, title="Quest Log", icon="tabs/tab-quests")

    for op in ops:
        if op[0] == "feat":
            _, q, y0, h, lines, ty, sy, i = op
            icon, col, label = STATUS[q["status"]]
            d.add(f'<g{delay(1)}>')
            card(d, CX, y0, CW, h, rim=P["gold500"])
            d.rect(CX + 4, y0 + 4, CW - 8, 2, P["gold300"], ' opacity=".7"')
            px = CX + 24
            # ribbon
            d.rect(CX + 4, y0 + 4, CW - 8, 40, P["gold500"])
            d.rect(CX + 4, y0 + 4, CW - 8, 3, P["gold300"])
            d.rect(CX + 4, y0 + 41, CW - 8, 3, P["gold700"])
            d.text(px, y0 + 35, "Featured quest \u00b7 " + q["featured"], 30, OUT, sh=0)
            d.icon(icon, px, y0 + 62, 64)
            d.text(px + 80, y0 + 118, q["name"], 72, P[col], sh=4)
            d.text(CX + CW - 24, y0 + 106, f"{label} \u00b7 {q['year']}", 32, P["parch300"], anchor="end", sh=2)
            for k, ln in enumerate(lines):
                d.text(px, y0 + 170 + k * 38, ln, 30, P["parch100"], sh=1)
            chips(d, px, sy, q["stack"], CW - 48)
            d.add("</g>")
        else:
            _, q, y0, h, lines, sy, i = op
            icon, col, label = STATUS[q["status"]]
            d.add(f'<g{delay(i + 1, 0.15)}>')
            card(d, CX, y0, CW, h)
            px = CX + 18
            d.icon(icon, px, y0 + 18, 48)
            d.text(px + 60, y0 + 52, q["name"], 40, P[col], sh=2)
            d.text(CX + CW - 18, y0 + 50, f"{label} · {q['year']}", 28, P["parch300"], anchor="end", sh=2)
            for k, ln in enumerate(lines):
                d.text(px, y0 + 90 + k * 32, ln, 26, P["parch100"], sh=1)
            chips(d, px, sy, q["stack"], CW - 36)
            d.add("</g>")
    return d


# ---------------------------------------------------------------------------
# skills.svg
# ---------------------------------------------------------------------------
def build_skills():
    groups = DATA["skills"]
    d = Doc(W, 100)
    y = 96
    TH = 128
    plan = []
    for gname, items in groups:
        plan.append((gname, items, y))
        y += 44 + TH + 22
    H = y - 22 + 28
    d.h = H
    frame(d, W, H, title="Skills", icon="tabs/tab-skills")
    d.css.append(
        "@keyframes shim{0%{opacity:0}5%{opacity:.14}14%,100%{opacity:0}}"
        ".shim{animation:shim 6s ease-in-out infinite;animation-delay:var(--d)}"
        "@keyframes hop{0%,100%{transform:none}5%{transform:translateY(-3px)}12%{transform:none}}"
        ".hop{animation:hop 6s steps(1) infinite;animation-delay:var(--d)}"
    )
    idx = 0
    for gi, (gname, items, y0) in enumerate(plan):
        d.add(f'<g{delay(gi, 0.25)}>')
        d.text(CX, y0 + 30, gname, 34, P["uiOrange"], sh=2)
        d.rect(CX + tw(gname, 34) + 14, y0 + 20, CW - tw(gname, 34) - 14, 2, P["rock600"])
        d.rect(CX + tw(gname, 34) + 14, y0 + 22, CW - tw(gname, 34) - 14, 2, OUT)
        cnt = len(items)
        gap = 12
        tw_ = (CW - gap * (cnt - 1)) / cnt
        for k, (label, ico) in enumerate(items):
            x = CX + k * (tw_ + gap)
            ty = y0 + 44
            slot(d, x, ty, tw_, TH)
            cxm = x + tw_ / 2
            dl = f"{idx * 0.22:.2f}s"
            d.add(f'<g class="hop" style="--d:{dl}">')
            d.icon(f"skills/{ico}", cxm - 24, ty + 18, 48)
            d.add("</g>")
            lines = wrap(label, 24, tw_ - 14)
            for m_, ln in enumerate(lines):
                d.text(cxm, ty + 92 + m_ * 24, ln, 24, P["parch100"], anchor="middle", sh=1)
            d.add(
                f'<rect class="shim" x="{n(x + 4)}" y="{ty + 4}" width="{n(tw_ - 8)}" height="{TH - 8}" '
                f'fill="{P["parch100"]}" opacity="0" style="--d:{dl}"/>'
            )
            idx += 1
        d.add("</g>")
    return d


# ---------------------------------------------------------------------------
# achievements.svg
# ---------------------------------------------------------------------------
def build_achievements():
    A = DATA["achievements"]
    d = Doc(W, 100)
    y = 96
    # top card
    top_h = 150
    # rows
    rows = []
    ry = y + top_h + 16
    for r in A["rows"]:
        subs = wrap(r["sub"], 24, CW - 100 - 36)
        h = 22 + 34 + len(subs) * 28 + 14
        h = max(h, 92)
        rows.append((r, ry, h, subs))
        ry += h + 12
    H = ry - 12 + 28
    d.h = H
    frame(d, W, H, title="Achievements", icon="tabs/tab-achievements")
    d.css.append(
        "@keyframes spark{0%,100%{opacity:0}50%{opacity:1}}"
        ".spk{animation:spark 2.4s steps(1) infinite;animation-delay:var(--d)}"
        "@keyframes gsw{from{transform:translateX(-200px) skewX(-20deg)}to{transform:translateX(900px) skewX(-20deg)}}"
        ".gsw{animation:gsw 7s ease-in-out 2s infinite;transform-box:fill-box;transform-origin:center}"
    )
    # featured 1st place
    t = A["top"]
    d.add(f'<g{delay(0)}>')
    card(d, CX, y, CW, top_h, rim=P["gold300"])
    d.rect(CX + 4, y + 4, CW - 8, 3, P["gold500"])
    d.add(f'<clipPath id="topclip"><rect x="{CX + 4}" y="{y + 4}" width="{CW - 8}" height="{top_h - 8}"/></clipPath>')
    d.add(
        f'<g clip-path="url(#topclip)"><rect class="gsw" x="0" y="{y}" width="60" height="{top_h}" fill="{P["parch050"]}" opacity=".16"/></g>'
    )
    slot(d, CX + 22, y + 20, 110, 110, P["rock900"])
    d.icon("tabs/tab-achievements", CX + 22 + 7, y + 20 + 7, 96)
    for sx, sy_, dl in ((CX + 30, y + 30, "0s"), (CX + 112, y + 44, "0.8s"), (CX + 100, y + 112, "1.6s")):
        d.add(f'<rect class="spk" x="{sx}" y="{sy_}" width="6" height="6" fill="{P["white"]}" style="--d:{dl}"/>')
    d.text(CX + 156, y + 76, t["tag"], 72, P["gold300"], sh=4)
    d.text(CX + 156, y + 112, t["title"], 36, P["parch100"], sh=2)
    d.text(CX + CW - 22, y + 56, t["sub"], 36, P["parch300"], anchor="end", sh=2)
    d.add("</g>")
    for i, (r, y0, h, subs) in enumerate(rows):
        d.add(f'<g{delay(i + 1, 0.14)}>')
        card(d, CX, y0, CW, h)
        slot(d, CX + 14, y0 + (h - 68) / 2, 68, 68)
        d.icon(r["icon"], CX + 14 + 10, y0 + (h - 68) / 2 + 10, 48)
        tx = CX + 100
        d.text(tx, y0 + 40, r["title"], 34, P["parch100"], sh=2)
        if r.get("tag"):
            d.text(CX + CW - 20, y0 + 40, r["tag"], 34, P["uiOrange"], anchor="end", sh=2)
        for k, ln in enumerate(subs):
            d.text(tx, y0 + 70 + k * 28, ln, 24, P["parch300"], sh=1)
        d.add("</g>")
    return d


# ---------------------------------------------------------------------------
# gamelog.svg
# ---------------------------------------------------------------------------
TIERS = {
    "bronze": ("wood300", None),
    "orange": ("uiOrange", None),
    "green": ("uiGreen", ("moss300", "moss500", "moss700")),
    "red": ("uiRed", ("hp300", "hp500", "hp700")),
    "gold": ("gold300", ("gold300", "gold500", "gold700")),
    "celestial": ("uiCyan", ("uiCyan", "violet500", "violet700")),
}


def build_gamelog():
    d = Doc(W, 100)
    games = DATA["games"]
    gap = 12
    tw_ = (CW - gap) / 2
    TH = 118
    rows = (len(games) + 1) // 2
    H = 96 + rows * TH + (rows - 1) * gap + 28
    d.h = H
    frame(d, W, H, title="Game Log", icon="skills/game-controller")
    d.defs.append(
        f'<linearGradient id="cel" x1="0" x2="1"><stop offset="0" stop-color="{P["uiCyan"]}"/>'
        f'<stop offset="1" stop-color="{P["violet300"]}"/></linearGradient>'
    )
    d.css.append(
        "@keyframes spk{0%,100%{opacity:0}50%{opacity:1}}"
        ".spk{animation:spk 3.2s steps(1) infinite;animation-delay:var(--d)}"
    )
    for i, g in enumerate(games):
        col, tint = TIERS[g["tier"]]
        x = CX + (i % 2) * (tw_ + gap)
        y = 96 + (i // 2) * (TH + gap)
        d.add(f'<g{delay(i, 0.13)}>')
        card(d, x, y, tw_, TH)
        slot(d, x + 14, y + 16, 86, 86)
        tmap = None
        key = None
        if tint:
            tmap = {"spec300": P[tint[0]], "spec500": P[tint[1]], "spec700": P[tint[2]]}
            key = "gem-" + g["tier"]
        d.icon(g["icon"], x + 14 + 19, y + 16 + 19, 48, tmap, key=key)
        d.add(
            f'<rect class="spk" x="{x + 14 + 56}" y="{y + 16 + 18}" width="4" height="4" fill="{P["white"]}" '
            f'style="--d:{i * 0.5:.1f}s"/>'
        )
        tx = x + 118
        d.text(tx, y + 40, g["game"], 30, P["parch100"], sh=2)
        fill = "url(#cel)" if g["tier"] == "celestial" else P[col]
        d.text(tx, y + 80, g["rank"], 40, fill, sh=3)
        if g.get("note"):
            d.text(tx, y + 106, g["note"], 24, P["parch300"], sh=1)
        d.add("</g>")
    return d


# ---------------------------------------------------------------------------
# chat.svg
# ---------------------------------------------------------------------------
def build_chat():
    d = Doc(W, 100)
    lines = DATA["chat"]
    LH = 46
    H = 28 + 34 + len(lines) * LH + 20 + 28
    d.h = H
    frame(d, W, H, body=None)
    par = d.pattern("parch", "parchment.webp", 64, 64)
    d.rect(14, 14, W - 28, H - 28, P["parch200"])
    d.rect(14, 14, W - 28, H - 28, par)
    d.rect(14, 14, W - 28, H - 28, P["parch100"], ' opacity=".45"')
    d.rect(14, 14, W - 28, 2, P["parch400"])
    d.rect(14, 14, 2, H - 28, P["parch400"])
    d.rect(14, H - 16, W - 28, 2, P["parch050"])
    d.rect(W - 16, 14, 2, H - 28, P["parch050"])
    d.fonts.add("v")
    size = 38
    y = 28 + 42
    for i, (kind, msg) in enumerate(lines):
        dl = 0.7 + i * 1.1
        d.add(f'<g class="sh" style="--d:{dl:.1f}s">')
        if kind == "system":
            d.text(CX, y, msg, size, P["chatRed"], f="v", sh=0)
        else:
            nm = DATA["handle"] + ":"
            d.text(CX, y, nm, size, P["chatBlue"], f="v", sh=0)
            d.text(CX + tw(nm + " ", size, "v"), y, msg, size, P["ink"], f="v", sh=0)
        d.add("</g>")
        last = (CX + tw(DATA["handle"] + ": " + msg, size, "v"), y)
        y += LH
    # blinking cursor after the last line
    d.add(
        f'<rect x="{n(round(last[0] + 6))}" y="{last[1] - 26}" width="14" height="28" fill="{P["ink"]}" '
        f'style="animation:show .01s steps(1,start) {0.7 + (len(lines) - 1) * 1.1:.1f}s both,blink 1s steps(1) {0.7 + (len(lines) - 1) * 1.1 + 0.4:.1f}s infinite"/>'
    )
    return d


# ---------------------------------------------------------------------------
# buttons
# ---------------------------------------------------------------------------
def build_button(label, icon):
    w, h = 168, 48
    d = Doc(w, h)
    d.rect(0, 0, w, h, OUT)
    d.rect(2, 2, w - 4, h - 4, P["rock700"])
    d.rect(2, 2, w - 4, 3, P["rock400"])
    d.rect(2, 2, 3, h - 4, P["rock400"])
    d.rect(2, h - 5, w - 4, 3, P["rock900"])
    d.rect(w - 5, 2, 3, h - 4, P["rock900"])
    d.rect(5, 5, w - 10, h - 10, P["rock600"], ' opacity=".6"')
    d.add(f'<clipPath id="bc"><rect x="5" y="5" width="{w - 10}" height="{h - 10}"/></clipPath>')
    d.css.append(
        "@keyframes bs{0%{transform:translateX(-60px) skewX(-20deg)}30%,100%{transform:translateX(240px) skewX(-20deg)}}"
        ".bs{animation:bs 6s ease-in-out infinite;transform-box:fill-box;transform-origin:center}"
    )
    d.add(f'<g clip-path="url(#bc)"><rect class="bs" x="0" y="0" width="14" height="{h}" fill="{P["parch100"]}" opacity=".25"/></g>')
    x0 = round((w - (32 + 10 + tw(label, 30))) / 2)
    d.icon(icon, x0, 8, 32)
    d.text(x0 + 42, 34, label, 30, P["uiYellow"], sh=2)
    return d


# ---------------------------------------------------------------------------
def main():
    ASSETS.mkdir(exist_ok=True)
    out = {
        "hero.svg": build_hero(),
        "quests.svg": build_quests(),
        "skills.svg": build_skills(),
        "achievements.svg": build_achievements(),
        "gamelog.svg": build_gamelog(),
        "chat.svg": build_chat(),
    }
    for key, label, icon in DATA["buttons"]:
        out[f"btn-{key}.svg"] = build_button(label, icon)
    for name, doc in sorted(out.items()):
        data = doc.render()
        (ASSETS / name).write_text(data, encoding="utf-8")
        print(f"{name:20s} {len(data.encode()):7d} bytes")


if __name__ == "__main__":
    main()
