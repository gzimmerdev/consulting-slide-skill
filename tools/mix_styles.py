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


def pick(rng, w):
    w = {k: v for k, v in w.items() if v > 0}; r = rng.random() * sum(w.values())
    for k, v in w.items():
        r -= v
        if r <= 0: return k
    return k


def mix(name, decks, shares, rng):
    taken = {(fam(d["_hue"], d["_s"]), font_of(d["heading_font"]), d["title_size"]) for d in decks.values()}
    fonts = collections.Counter(font_of(d["heading_font"]) for d in decks.values())
    sizes = collections.Counter(d["title_size"] for d in decks.values()); bold = sum(d["title_bold"] for d in decks.values()) / len(decks)
    for _ in range(50):
        font, size = pick(rng, fonts), pick(rng, sizes)
        if (name, font, size) not in taken: break
    h, l, s = FAMILY[name]; h += rng.uniform(-6, 6)
    sh = lambda f: {k: v for k, v in shares.get(f, {}).items()}
    pal = pick(rng, sh("palette") or {"brand_grey": 1})
    series = [hexc(h, l * .62, s), hexc(h, l, s), hexc(h, .62, s * .55), hexc(h, .85, s * .45)]
    if pal == "two_brand": series[2] = "7F7F7F"      # second strong colour: graphite next to the brand
    return {"_src": f"archive mix (2026-11-12): {name} family as an original muted tone; font, title, headers, conclusion, tables and palette drawn from archive frequencies (tools/mix_styles.py)",
            "primary": hexc(h, l, s), "title_color": hexc(h, .16, s * .7), "dark": hexc(h, .16, s * .7), "kpi_color": hexc(h, l, s), "series": series,
            "heading_font": font, "body_font": "Segoe UI" if font in WIDE else font if rng.random() < .8 else "Arial", "title_size": max(18, min(22, size)), "title_bold": rng.random() < bold,
            "header_style": HEADER.get(pick(rng, {k: v for k, v in sh("header_look").items() if k in HEADER}), "rule"),
            "takeaway_style": CALLOUT.get(pick(rng, {k: v for k, v in sh("callout_look").items() if k in CALLOUT}), "dashed"),
            "table_header": TABLE.get(pick(rng, {k: v for k, v in sh("table_look").items() if k in TABLE}), "rule"),
            "badge": "square" if rng.random() < .35 else "circle"}


def main():
    decks = json.loads((ROOT / "private" / "archive_styles.json").read_text("utf8")); shares = json.loads((ROOT / "analysis" / "grammar.json").read_text("utf8")).get("style", {})
    p = ROOT / "slidegen" / "themes.json"; th = json.loads(p.read_text("utf8"))
    for name in FAMILY:
        th[f"mix_{name}"] = st = mix(name, decks, shares, random.Random(name))
        print(f"mix_{name}", st["primary"], st["heading_font"], st["title_size"], "bold" if st["title_bold"] else "reg", st["header_style"], st["takeaway_style"], st["table_header"], st["badge"])
    p.write_text(json.dumps(th, ensure_ascii=False, indent=1) + "\n", "utf8", newline="\n")


if __name__ == "__main__":
    main()
