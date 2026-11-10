"""Build the profile README and its SVGs from profile.json.

    python tools/build.py [--fonts DIR]

Brand: BI with Moiz (deep teal, paper, one orange element, Bricolage Grotesque / Instrument Sans / Geist Mono).
Fonts are subset to the characters each SVG uses and embedded as WOFF, because GitHub shows README images
through <img>, which cannot load outside fonts. Needs: fonttools. Optional: gh (for live PR counts).
"""
import argparse, base64, html, io, json, pathlib, subprocess
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

C = dict(paper="#F6F1E8", ink="#0A0F14", deep="#0F3D3E", teal="#2E6F73", mist="#7FB3B8", sand="#EADCC8",
         signal="#C6601F", soft="#C4CCC9")
THEME = {
    "light": dict(card="#FFFDF8", ink="#0A0F14", ink2="#3B4650", muted="#5E6A73", line="#D9CFBF",
                  teal="#2E6F73", chip="#EADCC8", rail="#0F3D3E"),
    "dark": dict(card="#132527", ink="#F1EADF", ink2="#C4CCC9", muted="#93A3A1", line="#2A3F41",
                 teal="#8CC2C6", chip="#162A2C", rail="#8CC2C6"),
}
FONT_FILES = {"BG": "BricolageGrotesque-Bold.ttf", "IS": "InstrumentSans-Regular.ttf",
              "ISB": "InstrumentSans-Bold.ttf", "GM": "GeistMono-Regular.ttf"}
STACK = {"BG": '"BG","Bricolage Grotesque","Trebuchet MS",sans-serif',
         "IS": '"IS","Instrument Sans","Segoe UI",sans-serif',
         "ISB": '"ISB","Instrument Sans","Segoe UI",sans-serif',
         "GM": '"GM","Geist Mono",Consolas,monospace'}


class Svg:
    """Collects text per font so each SVG embeds only the glyphs it uses."""

    def __init__(self, fonts_dir):
        self.fonts_dir, self.used = fonts_dir, {}

    def text(self, x, y, s, font, size, fill, anchor="start", extra=""):
        self.used.setdefault(font, set()).update(s)
        weight = ' font-weight="700"' if font in ("BG", "ISB") else ""
        return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family=\'{STACK[font]}\'{weight} '
                f'font-size="{size}" fill="{fill}"{extra}>{html.escape(s)}</text>')

    def font_css(self):
        out = []
        for font, chars in sorted(self.used.items()):
            tt = TTFont(self.fonts_dir / FONT_FILES[font])
            opts = subset.Options(); opts.flavor = "woff"; opts.layout_features = ["kern", "liga"]
            sub = subset.Subsetter(opts); sub.populate(text="".join(sorted(chars)) + " "); sub.subset(tt)
            buf = io.BytesIO(); tt.flavor = "woff"; tt.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            weight = 700 if font in ("BG", "ISB") else 400
            out.append(f'@font-face{{font-family:"{font}";src:url(data:font/woff;base64,{b64}) format("woff");font-weight:{weight}}}')
        return "".join(out)

    def wrap(self, w, h, body, title):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">'
                f'<title>{html.escape(title)}</title><style>{self.font_css()}</style>{body}</svg>\n')


def banner(cfg, fonts):
    b, s, W, H = cfg["banner"], Svg(fonts), 1200, 340
    vals = [38, 52, 46, 64, 58, 80, 72, 118]          # shape only: a rising series, the last bar is the point
    x0, bw, gap, base = 838, 30, 12, 250
    bars = "".join(
        f'<rect x="{x0 + i * (bw + gap)}" y="{base - v}" width="{bw}" height="{v}" rx="4" '
        + (f'fill="{C["signal"]}"/>' if i == len(vals) - 1 else f'fill="{C["mist"]}" fill-opacity="{.28 + i * .06:.2f}"/>')
        for i, v in enumerate(vals))
    body = (f'<rect width="{W}" height="{H}" rx="24" fill="{C["deep"]}"/>'
            f'<line x1="828" y1="{base + 1}" x2="1150" y2="{base + 1}" stroke="{C["mist"]}" stroke-opacity=".4"/>{bars}'
            + s.text(1150, 282, b["chart_note"], "GM", 13, C["mist"], "end")
            + s.text(64, 84, b["kicker"], "GM", 15, C["mist"], extra=' letter-spacing="1"')
            + s.text(64, 160, b["line1"], "BG", 58, C["paper"])
            + s.text(64, 222, b["line2"], "BG", 58, C["sand"])
            + s.text(64, 276, b["sub"], "IS", 20, C["soft"]))
    return s.wrap(W, H, body, f'{b["line1"]} {b["line2"]}')


def merged_prs(repo):
    try:
        out = subprocess.run(["gh", "api", f"search/issues?q=repo:{repo}+is:pr+is:merged", "--jq", ".total_count"],
                             capture_output=True, text=True, timeout=30)
        return int(out.stdout.strip())
    except Exception:
        return None


def card(c, mode, fonts):
    t, s, W, H = THEME[mode], Svg(fonts), 580, 200
    stat = c.get("stat_text", "")
    if c.get("stat") == "merged_prs":
        n = merged_prs(c["repo"])
        stat = f"{n} merged PRs" if n else ""
    chips, cx = [], 28
    for ch in c["chips"]:
        w = 16 + len(ch) * 8.2
        chips.append(f'<rect x="{cx}" y="128" width="{w:.0f}" height="26" rx="13" fill="{t["chip"]}"/>'
                     + s.text(f"{cx + w / 2:.0f}", 146, ch, "GM", 12.5, t["teal"], "middle"))
        cx += w + 8
    body = (f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["card"]}" stroke="{t["line"]}"/>'
            f'<rect x="0" y="0" width="8" height="{H}" rx="4" fill="{t["rail"]}"/>'
            + s.text(28, 44, c["meta"], "GM", 12.5, t["muted"])
            + (s.text(W - 28, 44, stat, "GM", 12.5, t["teal"], "end") if stat else "")
            + s.text(28, 80, c["title"], "BG", 28, t["ink"])
            + s.text(28, 108, c["desc"], "IS", 15.5, t["ink2"])
            + "".join(chips)
            + s.text(28, 182, "Open the repo →", "ISB", 14, t["teal"]))
    return s.wrap(W, H, body, f'{c["title"]}: {c["desc"]}')


def picture(name, alt, width):
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">'
            f'<img alt="{html.escape(alt)}" src="assets/{name}-light.svg" width="{width}"></picture>')


def readme(cfg):
    links = [f'<a href="{cfg["site"]}">biwithmoiz.com</a>']
    if cfg.get("linkedin"):
        links.append(f'<a href="{cfg["linkedin"]}">LinkedIn</a>')
    links.append('<a href="https://github.com/MoizP-AI-Lab/power-bi-lab">power-bi-lab</a>')
    cards = "\n".join(f'<a href="{c["url"]}">{picture("card-" + c["slug"], c["title"] + ": " + c["desc"], "49%")}</a>'
                      for c in cfg["cards"])
    b = cfg["banner"]
    return f"""<a href="{cfg["site"]}"><img alt="BI with Moiz: {b["line1"]} {b["line2"]}" src="assets/banner.svg" width="100%"></a>

<p>{" · ".join(links)}</p>

### Projects

{cards}

<sub>Every project shows when it was built, the stack used and where its data comes from.</sub>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", default=str(ROOT.parent.parent / "brand" / "fonts"),
                    help="folder with the six brand TTFs")
    fonts = pathlib.Path(ap.parse_args().fonts)
    cfg = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "banner.svg").write_text(banner(cfg, fonts), encoding="utf-8")
    for c in cfg["cards"]:
        for mode in THEME:
            (ASSETS / f'card-{c["slug"]}-{mode}.svg').write_text(card(c, mode, fonts), encoding="utf-8")
    (ROOT / "README.md").write_text(readme(cfg), encoding="utf-8")
    for p in sorted(ASSETS.glob("*.svg")):
        print(f"{p.name:28} {p.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
