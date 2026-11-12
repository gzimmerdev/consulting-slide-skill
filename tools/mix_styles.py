"""Mixed styles from the whole archive (user ruling 2026-11-12: designs come from studying all decks, mixed, not from one team's look).

24 styles, about one per archive deck. Each takes a colour family the archive uses (reds, wines, greens, moss/olive, navy/blue, golds,
greys), rebuilt as an original muted tone (never a deck's hex), and a different archive option for every other trait: font family
(mapped to fonts every Office install has; the map of archive fonts is in private/font_map.json), title size, weight and underline,
header look, conclusion look (dashed / filled / rule / grey box), big numbers (plain / boxed / tiles), grey panels or white, bar
thickness, table header and row lines, badge, corners, bottom rule, one or two strong colours. Options are spread
evenly over the styles and, of 300 seeded shuffles, the one where two styles share the fewest traits wins (user, 2026-11-12: "it seems
there is no variety" when traits were drawn by frequency). A style whose colour family + font + title size equals one deck's is
re-assigned, so none copies a deck.
Input (local): private/archive_styles.json (per-deck traits from style_from_deck.derive). Writes slidegen/themes.json (mix_* entries).
Run: py -3 -I tools/mix_styles.py
"""
import colorsys, json, random, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# name: (hue, lightness, saturation, archive family) - muted tones of the archive's colour families
FAMILY = {"crimson": (356, .38, .62, "red"), "brick": (8, .37, .55, "red"), "cherry": (350, .33, .68, "red"), "rust": (14, .41, .60, "red"),
          "wine": (352, .29, .45, "red"), "maroon": (0, .25, .50, "red"), "mulberry": (338, .30, .42, "red"),
          "forest": (150, .27, .55, "green"), "emerald": (155, .32, .60, "green"), "pine": (166, .22, .50, "green"), "jade": (160, .36, .45, "green"),
          "moss": (95, .30, .50, "moss"), "olive": (72, .30, .45, "moss"), "fern": (110, .33, .45, "moss"),
          "navy": (218, .25, .55, "navy"), "ink": (226, .20, .45, "navy"), "cobalt": (212, .33, .55, "navy"), "steel": (205, .35, .30, "navy"),
          "ochre": (40, .40, .75, "gold"), "amber": (34, .44, .78, "gold"), "mustard": (46, .40, .65, "gold"), "bronze": (28, .34, .55, "gold"),
          "graphite": (210, .26, .08, "grey"), "slate": (215, .32, .14, "grey")}
STANDARD = ("Arial", "Trebuchet MS", "Verdana", "Calibri", "Segoe UI", "Century Gothic", "Franklin Gothic Book", "Georgia", "Cambria", "Tahoma")
_FM = ROOT / "private" / "font_map.json"      # archive font -> the closest standard Office font (local only: rare fonts can point to a deck)
FONT = json.loads(_FM.read_text("utf8")) if _FM.exists() else {}
font_of = lambda f: f if f in STANDARD else FONT.get(f, "Segoe UI")
WIDE = ("Century Gothic", "Verdana")      # wide fonts stay in headings: the text-height estimates assume an average-width body font
# Trait options the archive shows (vision labels + per-deck traits); common options are listed twice so they come up more often.
TRAITS = {"header_style": ["rule", "rule", "bar", "dotline", "vbar"],      # label over a line / filled bar / centred line / side bar
          "takeaway_style": ["dashed", "dashed", "solid", "rule", "grey"], "kpi_style": ["plain", "plain", "boxed", "tiles"],
          "panels": ["none", "none", "none", "grey"], "bar_gap": [80, 80, 50, 140], "table_header": ["rule", "rule", "fill", "plain"], "badge": ["circle", "square"],
          "title_bold": [True, False], "title_rule": [False, False, True], "footer_rule": [True, False], "table_row_rules": [False, True],
          "corners": ["square", "square", "rounded"], "source_italic": [True, False], "palette": ["brand_grey", "brand_grey", "two_brand"],
          "title_size": [18, 19, 20, 20, 21, 22, 24]}


def fam(h, s):
    if s < .2: return "grey"
    return "red" if h < 20 or h > 340 else "gold" if h < 70 else "moss" if h < 120 else "green" if h < 180 else "navy"


def hexc(h, l, s): return "".join(f"{round(c * 255):02X}" for c in colorsys.hls_to_rgb(h / 360 % 1, l, s))


def assign(n):
    """{trait: [value for style 0..n-1]}: options spread evenly, the shuffle with the lowest max shared-trait count between two styles."""
    best = None
    for seed in range(300):
        rng = random.Random(seed); a = {}
        for k, v in TRAITS.items():
            col = (v * n)[:n]; rng.shuffle(col); a[k] = col
        score = max(sum(a[k][x] == a[k][y] for k in TRAITS) for x in range(n) for y in range(x + 1, n))
        if best is None or score < best[0]: best = (score, a)
    return best[1]


def mix(i, name, fonts, A, taken):
    h, l, s, f = FAMILY[name]; h += random.Random(name).uniform(-4, 4)
    t = {k: A[k][i] for k in TRAITS}; font = fonts[i % len(fonts)]
    k = 0
    while (f, font, t["title_size"]) in taken and k < len(fonts):      # never one deck's family + font + title size
        k += 1; font = fonts[(i + k) % len(fonts)]
    series = [hexc(h, l * .62, s), hexc(h, l, s), hexc(h, .62, s * .55), hexc(h, .85, s * .45)]
    if t.pop("palette") == "two_brand": series = [hexc(h, l, s), "595959", hexc(h, .62, s * .55), "BFBFBF"]      # brand + graphite
    dark = hexc(h, .16, min(s, .5) * .8)
    return {"_src": f"archive mix (2026-11-12): {name}, an original muted tone of the archive's {f} family; every other trait takes a different archive option per style (tools/mix_styles.py)",
            "primary": hexc(h, l, s), "title_color": dark, "dark": dark, "kpi_color": hexc(h, l, s), "series": series,
            "heading_font": font, "body_font": "Segoe UI" if font in WIDE else font, **t, **({"header_caps": False} if font in WIDE else {})}      # wide fonts: centred headers in sentence case


def main():
    decks = json.loads((ROOT / "private" / "archive_styles.json").read_text("utf8"))
    taken = {(fam(d["_hue"], d["_s"]), font_of(d["heading_font"]), d["title_size"]) for d in decks.values()}
    fonts = [f for f, _ in collections.Counter(font_of(d["heading_font"]) for d in decks.values()).most_common()]
    fonts += [f for f in ("Calibri",) if f not in fonts]      # only fonts the archive uses (mapped); Calibri as a second humanist sans next to Segoe UI
    p = ROOT / "slidegen" / "themes.json"; th = {k: v for k, v in json.loads(p.read_text("utf8")).items() if not k.startswith("mix_")}
    names = list(FAMILY); A = assign(len(names)); out = {}
    for i, name in enumerate(names): th[f"mix_{name}"] = out[name] = mix(i, name, fonts, A, taken)
    keys = [k for k in TRAITS if k != "palette"] + ["heading_font"]
    for a in out:
        same = max(sum(out[a][k] == out[b][k] for k in keys) for b in out if b != a)
        print(f"mix_{a:9}", out[a]["primary"], out[a]["heading_font"][:14].ljust(14), out[a]["title_size"], out[a]["header_style"].ljust(7), out[a]["takeaway_style"].ljust(6), out[a]["table_header"].ljust(5), f"| most shared: {same}/{len(keys)}")
    p.write_text(json.dumps(th, ensure_ascii=False, indent=1) + "\n", "utf8", newline="\n")


if __name__ == "__main__":
    main()
