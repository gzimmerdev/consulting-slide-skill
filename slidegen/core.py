"""Shared design system: theme, grid, text/shape helpers, and the footer/title every slide has.

All numbers below come from the archive analysis (docs/design-system.md).
Canvas 13.333 x 7.5 in. Left/right margin 0.4. Title 20pt bold. Source 9pt italic grey. Body 12pt.
"""
import json, os, re
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE
from pptx.oxml.ns import qn
from lxml import etree

W, H = 13.333, 7.5
MX = 0.3                      # left/right margin (archive originals sit ~0.0-0.15 in from the edge; ruling 2026-11-08: tighter spacing)
CW = W - 2 * MX               # content width
TITLE_Y, TITLE_H = 0.2, 0.8
BODY_TOP, BODY_BOTTOM = 1.2, 6.75     # body ends above the footer rule
FOOTER_RULE_Y = 6.92                  # the bottom "underline": full-width rule above source / page number
SOURCE_Y = 7.02
LABELS = {  # default strings per language
    "pt": {"source": "Fonte", "insights": "Principais insights", "takeaway": "Conclusão"},
    "en": {"source": "Source", "insights": "Key insights", "takeaway": "Takeaway"},
}


# ---------- theme ----------
def _mix(hexc, other, f):
    a = [int(hexc[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(x + (other - x) * f):02X}" for x in a)

def tint(hexc, f):  return _mix(hexc, 255, f)   # toward white
def shade(hexc, f): return _mix(hexc, 0, f)     # toward black

def _lum(hexc):
    """WCAG relative luminance."""
    c = [int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

MY_STYLES = Path(os.environ.get("SLIDEGEN_MY_STYLES") or Path(__file__).parent.parent / "my_styles")      # the user's own styles + logos (gitignored)


def my_styles():
    """my_styles/styles.json: {"_default": name, name: {tokens}}; {} when there is none."""
    f = MY_STYLES / "styles.json"
    return json.loads(f.read_text(encoding="utf8")) if f.exists() else {}


def default_theme():
    """The style a spec without "theme" gets: the user's default (my_styles), else bain_red."""
    d = my_styles().get("_default"); return d if d in themes() else "bain_red"


def themes():
    """All styles: built-in themes.json plus the user's my_styles/styles.json (same name: the user's wins), each merged over `_defaults`."""
    raw = json.loads((Path(__file__).parent / "themes.json").read_text(encoding="utf8"))
    base = raw.pop("_defaults")
    raw.update({k: v for k, v in my_styles().items() if not k.startswith("_")})
    return {k: {**base, **v} for k, v in raw.items()}

def load_theme(name=None, primary=None, font=None, heading_font=None, **overrides):
    t = dict(themes()[name or default_theme()]); t.update({k: v for k, v in overrides.items() if v is not None})
    if primary: t["primary"] = primary.lstrip("#").upper()
    if font: t["body_font"] = font; t["heading_font"] = heading_font or font
    if heading_font: t["heading_font"] = heading_font
    p = t["primary"]
    t["series"] = t.get("series") or [p, tint(p, .35), tint(p, .6), tint(p, .8)]   # dark->light as in the archive
    t["pale"] = tint(p, .92)
    t["dark"] = t.get("dark") or shade(p, .55)          # dark slides (cover, divider, key insight)
    # text drawn IN the brand colour on white: darken light brand colours (gold, lime) until readable (>= 3:1)
    tp = p
    while 1.05 / (_lum(tp) + 0.05) < 3: tp = shade(tp, .12)
    t["text_primary"] = t.get("text_primary") or tp
    if not t.get("on_primary"):                          # text on primary fills: white unless contrast < 3:1
        t["on_primary"] = "FFFFFF" if 1.05 / (_lum(p) + 0.05) >= 3 else "1A1A1A"
    return t

def rect_shape(theme):
    return MSO_SHAPE.ROUNDED_RECTANGLE if theme.get("corners") == "rounded" else MSO_SHAPE.RECTANGLE

def rgb(h): return RGBColor.from_string(h.lstrip("#").upper())


# ---------- primitives ----------
def new_deck():
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    return prs

def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])

def add_runs(p, s, size, font, color, bold=False, italic=None, accent=None):
    """Inline markup: **bold** ==accent== and //italic// (bold in the accent colour; falls back to the text colour)."""
    for seg in filter(None, re.split(r"(\*\*.+?\*\*|==.+?==|//.+?//)", s)):
        kw = seg[:2] in ("**", "==", "//") and len(seg) > 4
        r = p.add_run(); r.text = seg[2:-2] if kw else seg; f = r.font
        f.size = Pt(size); f.name = font
        f.italic = True if kw and seg[0] == "/" else italic
        f.bold = bold or (kw and seg[0] != "/")
        f.color.rgb = rgb(accent if kw and seg[0] == "=" and accent else color)

def text(slide, x, y, w, h, content, size=12, bold=False, italic=False, color="1A1A1A",
         font="Arial", align="l", anchor="t", spacing=None, accent=None):
    """content: str or list of paragraphs. **bold** segments are supported inline."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    paras = content if isinstance(content, list) else [content]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        if spacing: p.space_after = Pt(spacing)
        add_runs(p, para, size, font, color, bold, italic, accent)
    return tb

def box(slide, x, y, w, h, fill=None, line=None, line_w=1.0, dash=False, shape=MSO_SHAPE.RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.shadow.inherit = False
    if fill: s.fill.solid(); s.fill.fore_color.rgb = rgb(fill)
    else: s.fill.background()
    if line:
        s.line.color.rgb = rgb(line); s.line.width = Pt(line_w)
        if dash: s.line.dash_style = MSO_LINE.DASH
    else: s.line.fill.background()
    return s

def hline(slide, x1, y1, x2, y2, color, width=1.5, dash=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color); c.line.width = Pt(width)
    if dash: c.line.dash_style = MSO_LINE.DASH
    sp = c._element.spPr                                    # no theme shadow under rules (empty effect list)
    if sp.find(qn("a:effectLst")) is None: sp.append(etree.Element(qn("a:effectLst")))
    return c

def number_badge(slide, x, y, n, theme, d=0.28):
    shp = MSO_SHAPE.OVAL if theme.get("badge", "circle") == "circle" else rect_shape(theme)
    s = box(slide, x, y, d, d, fill=theme["primary"], shape=shp)
    tf = s.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = str(n); r.font.size = Pt(11); r.font.bold = True
    r.font.name = theme["body_font"]; r.font.color.rgb = rgb(theme["on_primary"])
    return s

def section_header(slide, x, w, y, label, theme):
    """Column header. style 'rule': 14pt bold label over a brand-colour rule (Team G/Team E);
    style 'bar': label in a filled brand bar (LEK/Team D)."""
    if theme.get("header_style") == "bar":
        pill(slide, x, y, w, 0.38, label, theme, size=13)
        return
    text(slide, x, y, w, 0.3, label, size=14, bold=True, color=theme["text_primary"],
         font=theme["heading_font"], align="c", anchor="b", italic=theme.get("header_italic", False))
    hline(slide, x, y + 0.34, x + w, y + 0.34, theme["primary"], theme.get("rule_width", 1.5))


# ---------- elements every content slide has ----------
class LogoError(ValueError): pass


def logo_path(f):
    """Existing file for a logo path (as given, else relative to the project root), or None."""
    for q in (Path(f), Path(__file__).parent.parent / f):
        if q.is_file(): return q


def _logo(slide, spec, theme):
    """Draw the logo(s) (spec "logo" wins over theme token "logo": {file, position footer-right|footer-left|top-right, height in},
    or a list of them; logos sharing a position sit side by side, inward from the edge). Aspect ratio kept.
    Returns {position: width + gaps taken from the neighbouring text} ({} = no logo)."""
    lg = spec.get("logo") or theme.get("logo")
    if not lg: return {}
    from PIL import Image
    used = {}
    for one in (lg if isinstance(lg, list) else [lg]):
        f = logo_path(one["file"])
        if not f: raise LogoError(f"logo: file not found: {one['file']}")
        iw, ih = Image.open(f).size; h = one.get("height", 0.3); w = h * iw / ih; pos = one.get("position", "footer-right")
        if w > 2.5: w = 2.5; h = w * ih / iw                                    # ponytail: logos wider than 2.5in are scaled down
        off = used.get(pos, 0)
        x = MX + off if pos == "footer-left" else W - MX - off - w
        y = min(max(SOURCE_Y + 0.15 - h / 2, FOOTER_RULE_Y + 0.04), H - 0.04 - h) if pos != "top-right" else max(TITLE_Y + (TITLE_H - h) / 2, 0.3 if spec.get("tag") else 0.08)
        slide.shapes.add_picture(str(f), Inches(x), Inches(y), Inches(w), Inches(h)).name = "logo"
        used[pos] = off + w + 0.15
    return used


def title_and_footer(slide, spec, theme, lang):
    used = _logo(slide, spec, theme)          # width the logos take from the title (top-right) or the footer text (left / right)
    rt, rr, rl = (used.get(k, 0) for k in ("top-right", "footer-right", "footer-left")); pos = bool(used)
    tb = text(slide, MX, TITLE_Y, CW - rt, TITLE_H, spec["headline"], size=theme.get("title_size", 20),
         bold=theme.get("title_bold", True), color=theme["title_color"], font=theme["heading_font"], anchor="m")
    if spec.get("accent_words"):    # key phrases in the brand colour (same font/size); case-insensitive match
        p0 = tb.text_frame.paragraphs[0]; r0 = p0.runs[0]; f0 = r0.font
        words = list(spec["accent_words"]) + re.findall(r"==(.+?)==", spec["headline"])      # ==markup== in the headline counts too
        hl = re.sub(r"==|\*\*", "", spec["headline"])      # no raw markup in the title when accent_words takes over the runs
        parts = re.split("(" + "|".join(re.escape(w) for w in words) + ")", hl, flags=re.I)
        for r in list(p0.runs): r._r.getparent().remove(r._r)
        for seg in filter(None, parts):
            r = p0.add_run(); r.text = seg; f = r.font; f.size = f0.size; f.name = f0.name; f.bold = f0.bold
            hit = re.fullmatch("|".join(re.escape(w) for w in words), seg, re.I)
            if hit and spec.get("accent_bold"): f.bold = True      # spec option: bold keywords (s04 original)
            f.color.rgb = rgb(theme["primary"] if hit else theme["title_color"])
    if theme.get("title_rule"):     # optional rule under the action title
        hline(slide, MX, TITLE_Y + TITLE_H + 0.06, W - MX, TITLE_Y + TITLE_H + 0.06, theme["primary"], 1.0)
    if theme.get("footer_rule", True):
        hline(slide, MX, FOOTER_RULE_Y, W - MX, FOOTER_RULE_Y, theme["primary"], theme.get("footer_rule_width", 1.5))   # brand-colour underline (user ruling; archive refs)
    if spec.get("source"):
        sx = (0.5 if theme.get("page_number_align") == "left" and spec.get("page_number") else 0) + rl     # leave room for the left page number / logo
        if theme.get("footer_brand") and not pos:      # a logo image replaces the text wordmark     # theme token: letter-spaced wordmark + vertical rule before the source line
            text(slide, MX, SOURCE_Y, 1.5, 0.3, theme["footer_brand"], size=theme.get("source_size", 9), bold=True, color="7F7F7F", font=theme["body_font"], anchor="m")
            hline(slide, MX + 1.55, SOURCE_Y + 0.05, MX + 1.55, SOURCE_Y + 0.25, "BFBFBF", 1.0); sx += 1.7
        text(slide, MX + sx, SOURCE_Y, (spec["footer_bar"]["x"] - 0.1 - MX - sx if spec.get("footer_bar") else CW - 1.2 - sx - rr), 0.3, f"{spec.get('source_label') or LABELS[lang]['source']}: {spec['source']}",
             size=theme.get("source_size", 9), italic=theme.get("source_italic", True), color="7F7F7F", font=theme.get("source_font", theme["body_font"]), anchor="m")
    if spec.get("page_number"):
        left = theme.get("page_number_align") == "left"     # archive originals: bold page number bottom-left
        text(slide, MX + rl if left else W - MX - 0.8 - rr, SOURCE_Y, 0.8, 0.3, str(spec["page_number"]), size=theme.get("page_number_size", 10), bold=theme.get("page_number_bold", left),
             color=theme.get("page_number_color") or ("1A1A1A" if left else "7F7F7F"), font=theme["heading_font"] if theme.get("page_number_font") == "heading" else theme["body_font"], align="l" if left else "r", anchor="m")
    if spec.get("footer_tag"):
        text(slide, W - MX - 3.8 - rr, SOURCE_Y, 2.9, 0.3, spec["footer_tag"], size=10, bold=True,
             color=theme["text_primary"], font=theme["body_font"], align="r", anchor="m")
    if spec.get("footer_bar"):   # spec option: rounded progress-bar graphic in the footer, {x, w} in inches (s08 original: green bar left of the logo)
        fb = spec["footer_bar"]; b = box(slide, fb["x"], SOURCE_Y + 0.04, fb["w"], 0.26, fill=theme["primary"], shape=MSO_SHAPE.ROUNDED_RECTANGLE); b.adjustments[0] = 0.5
        hi = box(slide, fb["x"] + 0.1, SOURCE_Y + 0.08, fb["w"] - 0.2, 0.07, fill=tint(theme["primary"], .5), shape=MSO_SHAPE.ROUNDED_RECTANGLE); hi.adjustments[0] = 0.5
    if spec.get("tag"):          # "ILUSTRATIVO" / "PRELIMINARY" stamp, top-right (Bain "Chart it up")
        if theme.get("tag_style") == "plain":     # small-caps label top-left (archive originals), no box
            if theme.get("tag_serif"): text(slide, MX, 0.04, 3.0, 0.3, spec["tag"], size=12, color=theme["title_color"], font=theme["heading_font"], align="l")   # theme token (gold_serif): serif dark label as in the originals
            else: text(slide, MX, 0.04, 3.0, 0.22, spec["tag"].upper(), size=8, bold=True, color="7F7F7F", font=theme["body_font"], align="l")
        else:
            b = box(slide, W - MX - 1.6, 0.04, 1.6, 0.22, line="7F7F7F", line_w=0.75)
            set_text(b, spec["tag"].upper(), theme, size=8, bold=True, color="7F7F7F")
    if spec.get("tracker"):      # section tracker in the footer: active section bold in primary, others grey
        tr = spec["tracker"]; n = len(tr["sections"]); w = min(1.7, 6.0 / n); x0 = W / 2 - n * w / 2
        ty = SOURCE_Y; ta = theme.get("tracker_active", theme["primary"]); tf_ = theme["heading_font" if theme.get("tracker_serif") else "body_font"]     # theme tokens tracker_active (active fill) / tracker_serif (heading-font labels)
        if tr.get("position") in ("right", "footer"): x0 = W - MX - 0.9 - rr - n * w; ty = FOOTER_RULE_Y - 0.36 if tr["position"] == "right" else SOURCE_Y     # spec option: right-aligned above the footer rule (clear of the source line)
        if tr.get("style") == "nodes":      # spec option: line with circle nodes (active one filled), caps labels below (archive originals)
            w = min(1.9, 8.2 / n); x0 = W - MX - n * w - rr - (0 if theme.get("page_number_align") == "left" or not spec.get("page_number") else 0.9); ly = FOOTER_RULE_Y + 0.02
            hline(slide, x0 + w / 2, ly, x0 + n * w - w / 2, ly, tr.get("line", "1A1A1A"), 2.25)
            for i, name in enumerate(tr["sections"]):
                on = i == tr.get("active", 0); cx = x0 + (i + .5) * w
                box(slide, cx - .08, ly - .08, .16, .16, fill=ta if on else "FFFFFF", line=tr.get("line", "1A1A1A"), line_w=2.0, shape=MSO_SHAPE.OVAL)
                text(slide, x0 + i * w, ly + .1, w, .25, name.upper(), size=9, bold=True, color="1A1A1A" if on else "A6A6A6", font=tf_, align="c")
            tr = {"sections": []}
        for i, name in enumerate(tr["sections"]):
            on = i == tr.get("active", 0)
            if tr.get("style") == "boxes":      # spec option: dashed-outline rounded boxes, active one filled in the brand colour
                b = box(slide, x0 + i * w + 0.05, ty - 0.02, w - 0.1, 0.32, fill=ta if on else None, line=ta, line_w=0.75, dash=True, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
                set_text(b, name, theme, size=10, bold=on, color="FFFFFF" if on else theme["text_primary"], font=tf_); continue
            box(slide, x0 + i * w + 0.05, ty - 0.03, w - 0.1, 0.04, fill=ta if on else "D9D9D9")
            text(slide, x0 + i * w, ty + 0.03, w, 0.25, name, size=8, bold=on,
                 color=theme["text_primary"] if on else "A6A6A6", font=tf_, align="c")


# ---------- shared building blocks used by many archetypes ----------
def set_text(shape, content, theme, size=12, bold=False, color="FFFFFF", align="c", anchor="m", italic=False, font=None):
    """Write text inside an autoshape (bars, pills, cells drawn as shapes)."""
    tf = shape.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.08); tf.margin_top = tf.margin_bottom = Inches(0.03)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    paras = content if isinstance(content, list) else [content]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        add_runs(p, para, size, font or theme["body_font"], color, bold, italic, theme.get("text_primary"))
    return shape

def pill(slide, x, y, w, h, content, theme, fill=None, color=None, size=12, bold=True,
         shape=None, align="c", line=None, dash=False):
    """Filled bar/label. Text colour defaults to the style's on_primary when the fill is the primary."""
    fill = fill or theme["primary"]
    if color is None: color = theme["on_primary"] if fill == theme["primary"] else "FFFFFF"
    s = box(slide, x, y, w, h, fill=fill, line=line, dash=dash, shape=shape or rect_shape(theme))
    return set_text(s, content, theme, size=size, bold=bold, color=color, align=align)

def bullets(slide, x, y, w, h, items, theme, size=12, color="1A1A1A", marker="•", spacing=6, marker_color=None):
    """Bullet list: plain round marker in the text colour (no red squares), **bold** lead-ins supported."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(spacing)
        if marker:      # hanging indent: real a:buChar so wrapped lines align under the text
            pPr = p._p.get_or_add_pPr(); pPr.set("marL", str(Inches(0.2))); pPr.set("indent", str(-Inches(0.2)))
            for tag, attrs in (("a:buClr", None), ("a:buFont", {"typeface": theme["body_font"]}), ("a:buChar", {"char": marker})):
                e = etree.SubElement(pPr, qn(tag))
                if tag == "a:buClr": etree.SubElement(e, qn("a:srgbClr")).set("val", (marker_color or color).upper())
                else:
                    for k, v in attrs.items(): e.set(k, v)
        add_runs(p, item, size, theme["body_font"], color, accent=theme.get("text_primary"))
    return tb

def takeaway_bar(slide, content, theme, lang, y=6.1, h=0.6, label=None):
    """So-what bar. style 'dashed': pale fill, dashed brand outline, solid edge (Team G 'Main Takeaway');
    style 'solid': filled brand strip (Team E / Team D conclusion strip)."""
    lab = LABELS[lang]["takeaway"] if label is None else label
    body = [f"**{lab}:** {content}" if lab and not content.lstrip().startswith("**") else content]      # text with its own bold lead-in ("**Recomendação:** ...") keeps it alone
    if theme.get("takeaway_style") == "rule":    # thin primary rule over plain text: no filled strip, no bold lead-in (hand-made look)
        hline(slide, MX, y, MX + CW, y, theme["primary"], 1.5)
        text(slide, MX, y + 0.08, CW, h - 0.08, [content], size=13, color="1A1A1A", font=theme["body_font"], anchor="m")
        return
    if theme.get("takeaway_style") == "grey":      # grey box, no outline (archive conclusion look)
        box(slide, MX, y, CW, h, fill=theme.get("takeaway_fill", "F2F2F2"), shape=rect_shape(theme))      # theme takeaway_fill: own box colour (pale blue)
        text(slide, MX + 0.3, y, CW - 0.5, h, body, size=13, color="1A1A1A", font=theme["body_font"], anchor="m")
        return
    if theme.get("takeaway_style") == "solid":
        box(slide, MX, y, CW, h, fill=theme["primary"], shape=rect_shape(theme))
        text(slide, MX + 0.3, y, CW - 0.5, h, body, size=13, color=theme["on_primary"], font=theme["body_font"], anchor="m")
        return
    box(slide, MX, y, CW, h, fill=theme["pale"], line=theme["primary"], line_w=1, dash=True)
    box(slide, MX, y, 0.1, h, fill=theme["primary"])
    text(slide, MX + 0.3, y, CW - 0.5, h, body, size=13, color="1A1A1A", font=theme["body_font"], anchor="m")

def image(slide, path, x, y, w, h, theme, label="imagem", oval=False):
    """Picture cropped to fill the box; grey placeholder with a label when no file is given.
    Images can't be generated: this is the slot for the user's own photo / logo / map / screenshot."""
    from pathlib import Path as _P
    if path and re.fullmatch(r"[a-z0-9-]+", str(path)):      # a Lucide icon name, e.g. "rocket"
        path = icon_png(path, theme["text_primary"])
    if path and _P(path).exists():
        from PIL import Image as _I
        iw, ih = _I.open(path).size
        pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
        r_img, r_box = iw / ih, w / h
        if r_img > r_box:   # too wide: crop left/right
            c = (1 - r_box / r_img) / 2; pic.crop_left = pic.crop_right = c
        else:
            c = (1 - r_img / r_box) / 2; pic.crop_top = pic.crop_bottom = c
        if oval: pic.auto_shape_type = MSO_SHAPE.OVAL
        return pic
    s = box(slide, x, y, w, h, fill="E7E6E6", shape=MSO_SHAPE.OVAL if oval else MSO_SHAPE.RECTANGLE)
    return set_text(s, f"[{label}]", theme, size=10, italic=True, color="7F7F7F", bold=False)

ICONS = Path(__file__).parent.parent / "assets" / "icons" / "lucide"   # 2,300 line icons, ISC licence

def icon_png(name, color, px=512):
    """Recolour a Lucide SVG to the style colour and render it to a cached PNG (python-pptx can't embed SVG).
    Returns None for an unknown icon name (the caller then draws the grey placeholder)."""
    svg = ICONS / f"{name}.svg"
    if not svg.exists(): return None
    out = Path(__file__).parent.parent / "out" / ".icon_cache" / f"{name}_{color}.png"
    if not out.exists():
        import fitz
        out.parent.mkdir(parents=True, exist_ok=True)
        src = svg.read_text(encoding="utf8").replace("currentColor", f"#{color}")
        doc = fitz.open(stream=src.encode(), filetype="svg")
        doc[0].get_pixmap(matrix=fitz.Matrix(px / 24, px / 24), alpha=True).save(out)
    return str(out)

def find_icons(query, limit=20):
    """Icon names containing a word (for the AI layer / MCP: 'chart', 'money', 'users'...)."""
    return sorted(p.stem for p in ICONS.glob(f"*{query}*.svg"))[:limit]

def fmt(v, decimals=1, lang="pt"):
    """Number to text with the right separators (1.234,5 in pt / 1,234.5 in en)."""
    s = f"{v:,.{decimals}f}"
    return s.translate(str.maketrans(",.", ".,")) if lang == "pt" else s

def harvey(score, max_score=4):
    """Harvey ball glyph for a 0..max score (rendered as text, stays editable)."""
    glyphs = "○◔◑◕●"
    return glyphs[round(max(0, min(score, max_score)) / max_score * 4)]
