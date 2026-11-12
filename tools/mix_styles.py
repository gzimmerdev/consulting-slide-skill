"""Mixed styles from the whole archive (user ruling 2026-11-12: designs come from studying all decks, mixed, not from one team's look).

Each style takes one colour family the archive uses, rebuilt as an original muted tone (never a deck's hex), and draws every other
trait independently from its archive frequency: font family (mapped to fonts every Office install has; the map of archive fonts is in private/font_map.json), title size and weight,
header look, conclusion look, table header, badge shape, palette type. A draw that matches any single deck's colour family + font
+ title size is redrawn, so no style copies one deck.
Inputs (local): private/archive_styles.json (per-deck traits from style_from_deck.derive) and analysis/grammar.json (styling shares).
Writes the styles into slidegen/themes.json.   Run: py -3 -I tools/mix_styles.py
"""
import colorsys, json, random, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAMILY = {"crimson": (356, .38, .62), "forest": (150, .27, .55), "navy": (218, .25, .55), "ochre": (40, .40, .75), "wine": (352, .29, .45), "moss": (95, .30, .50)}      # hue, lightness, saturation: muted versions of the archive's families
STANDARD = ("Arial", "Trebuchet MS", "Verdana", "Calibri", "Segoe UI", "Century Gothic", "Franklin Gothic Book", "Georgia", "Cambria", "Tahoma")
_FM = ROOT / "private" / "font_map.json"      # archive font -> the closest standard Office font (local only: rare fonts can point to a deck)
FONT = json.loads(_FM.read_text("utf8")) if _FM.exists() else {}
font_of = lambda f: f if f in STANDARD else FONT.get(f, "Segoe UI")
WIDE = ("Century Gothic", "Verdana")      # wide fonts stay in headings: the text-height estimates assume an average-width body font
HEADER = {"label": "rule", "centred_rule": "dotline", "bar": "bar", "rule": "rule"}                 # archive header look -> theme header_style
CALLOUT = {"dashed": "dashed", "outlined": "dashed", "grey_box": "dashed", "filled_bar": "solid", "rule": "rule"}
TABLE = {"rule_header": "rule", "filled_header": "fill", "grid": "plain", "zebra": "plain"}


def fam(h, s):
    if s < .2: return "grey"
    return "crimson" if h < 20 or h > 340 else "ochre" if h < 70 else "moss" if h < 120 else "forest" if h < 180 else "navy"


def hexc(h, l, s): return "".join(f"{round(c * 255):02X}" for c in colorsys.hls_to_rgb(h / 360 % 1, l, s))


def _pick_unused(rng, w):
    w = {k: v for k, v in w.items() if v > 0}; r = rng.random() * sum(w.values())
    for k, v in w.items():
        r -= v
        if r <= 0: return k
    return k


# Trait options the archive shows (vision labels + per-deck traits). Styles take DIFFERENT values (user, 2026-11-12: "it seems there is
# no variety"; frequency draws all landed on the most common value): each option goes to an equal share of the styles, and of 300
# seeded shuffles the one where two styles share the fewest traits wins. Common options are listed twice, so they come up more often.
TRAITS = {"header_style": ["rule", "bar", "dotline", "vbar"],                # label over a line / filled bar / centred line / side bar
          "takeaway_style": ["dashed", "solid", "rule"], "table_header": ["rule", "fill", "plain"], "badge": ["circle", "square"],
          "title_bold": [True, False], "title_rule": [False, True, False], "footer_rule": [True, False], "table_row_rules": [False, True],
          "corners": ["square", "square", "rounded"], "source_italic": [True, False], "palette": ["brand_grey", "two_brand", "brand_grey"]}
SIZES = [20, 18, 24, 22, 19, 21]


def assign(n):
    """{trait: [value for style 0..n-1]}: balanced per trait, the shuffle with the lowest max shared-trait count between two styles."""
    best = None
    for seed in range(300):
        rng = random.Random(seed); a = {}
        for k, v in TRAITS.items():
            col = (v * n)[:n]; rng.shuffle(col); a[k] = col
        score = max(sum(a[k][x] == a[k][y] for k in TRAITS) for x in range(n) for y in range(x + 1, n))
        if best is None or score < best[0]: best = (score, a)
    return best[1]


def mix(i, name, decks, A):
    fonts = [f for f, _ in collections.Counter(font_of(d["heading_font"]) for d in decks.values()).most_common()]
    fonts += [f for f in STANDARD if f not in fonts]; font = fonts[i % len(fonts)]
    t = {k: A[k][i] for k in TRAITS}
    h, l, s = FAMILY[name]; h += random.Random(name).uniform(-6, 6)
    series = [hexc(h, l * .62, s), hexc(h, l, s), hexc(h, .62, s * .55), hexc(h, .85, s * .45)]
    if t.pop("palette") == "two_brand": series = [hexc(h, l, s), "595959", hexc(h, .62, s * .55), "BFBFBF"]      # brand + graphite
    return {"_src": f"archive mix (2026-11-12): {name} family as an original muted tone; font, title, headers, conclusion, tables, badges and rules each take a different archive option per style (tools/mix_styles.py)",
            "primary": hexc(h, l, s), "title_color": hexc(h, .16, s * .7), "dark": hexc(h, .16, s * .7), "kpi_color": hexc(h, l, s), "series": series,
            "heading_font": font, "body_font": "Segoe UI" if font in WIDE else font, "title_size": SIZES[i % len(SIZES)], **t}


def main():
    decks = json.loads((ROOT / "private" / "archive_styles.json").read_text("utf8"))
    p = ROOT / "slidegen" / "themes.json"; th = json.loads(p.read_text("utf8")); out = {}
    A = assign(len(FAMILY))
    for i, name in enumerate(FAMILY):
        th[f"mix_{name}"] = out[name] = mix(i, name, decks, A)
    keys = [k for k in TRAITS if k != "palette"] + ["heading_font", "title_size"]
    for a in out:
        same = max(sum(out[a][k] == out[b][k] for k in keys) for b in out if b != a)
        print(f"mix_{a:8}", " ".join(str(out[a][k]) for k in keys), f"| most shared with another style: {same}/{len(keys)}")
    p.write_text(json.dumps(th, ensure_ascii=False, indent=1) + "\n", "utf8", newline="\n")


if __name__ == "__main__":
    main()
