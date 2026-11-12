"""Text archetypes: executive_summary, two_column, icon_columns, kpi_tiles, quote_interview, key_insight."""
from pptx.enum.shapes import MSO_SHAPE
from .core import (MX, W, H, CW, BODY_TOP, text, box, hline, number_badge, section_header, pill, bullets,
                   takeaway_bar, title_and_footer, image, set_text, tint, rect_shape)

BAR_Y = 6.1


def _bottom(spec): return BAR_Y - 0.15 if spec.get("takeaway") else 6.7


def executive_summary(slide, spec, theme, lang):
    """2-4 columns, filled header bar each, dense bullets, so-what bar (archive: Diagnóstico | Estratégia | Resultados)."""
    title_and_footer(slide, spec, theme, lang)
    cols = spec["columns"]; n = len(cols); gap = 0.25; cw = (CW - gap * (n - 1)) / n; b = _bottom(spec)
    for i, c in enumerate(cols):
        x = MX + i * (cw + gap)
        pill(slide, x, BODY_TOP, cw, 0.5, c["header"], theme, size=13)
        if c.get("kpi"):
            text(slide, x, BODY_TOP + 0.6, cw, 0.6, c["kpi"], size=24, bold=True, color=theme["text_primary"],
                 font=theme["heading_font"], align="c", anchor="m")
        top = BODY_TOP + (1.3 if c.get("kpi") else 0.7)
        bullets(slide, x + 0.05, top, cw - 0.1, b - top, c["bullets"], theme, size=11, spacing=6)
        if i < n - 1: hline(slide, x + cw + gap / 2, BODY_TOP + 0.6, x + cw + gap / 2, b, "D0D0D0", 1.0, dash=True)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def two_column(slide, spec, theme, lang):
    """Two rule-underlined columns of bullets, dashed divider."""
    title_and_footer(slide, spec, theme, lang)
    cw = (CW - 0.6) / 2; b = _bottom(spec)
    for i, side in enumerate((spec["left"], spec["right"])):
        x = MX + i * (cw + 0.6)
        section_header(slide, x, cw, BODY_TOP - 0.05, side["header"], theme)
        bullets(slide, x, BODY_TOP + 0.6, cw, b - BODY_TOP - 0.6, side["bullets"], theme, size=13, spacing=10)
    hline(slide, MX + cw + 0.3, BODY_TOP, MX + cw + 0.3, b, "D0D0D0", 1.5, dash=True)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def icon_columns(slide, spec, theme, lang):
    """3-5 equal cards: icon (or number badge) on top, bold header, bullets. `active` dims the others (gradual reveal)."""
    title_and_footer(slide, spec, theme, lang)
    cards = spec["cards"]; n = len(cards); gap = 0.25; cw = (CW - gap * (n - 1)) / n; b = _bottom(spec)
    act = spec.get("active")
    for i, c in enumerate(cards):
        x = MX + i * (cw + gap); dim = act is not None and i != act
        col = "BFBFBF" if dim else theme["primary"]
        box(slide, x, BODY_TOP, cw, b - BODY_TOP, fill="F7F7F7" if dim else theme["pale"],
            line=theme["primary"] if act == i else None, line_w=1.5, shape=rect_shape(theme))
        box(slide, x, BODY_TOP, cw, 0.07, fill=col)
        cx = x + cw / 2 - 0.4
        if c.get("icon"):
            image(slide, c["icon"], cx, BODY_TOP + 0.3, 0.8, 0.8, {**theme, "text_primary": theme["text_primary"] if col == theme["primary"] else col}, label="ícone")
        else:
            s = box(slide, cx, BODY_TOP + 0.3, 0.8, 0.8, fill=col, shape=MSO_SHAPE.OVAL)
            set_text(s, str(i + 1), theme, size=22, bold=True, color=theme["on_primary"] if not dim else "FFFFFF")
        text(slide, x + 0.15, BODY_TOP + 1.25, cw - 0.3, 0.6, c["header"], size=14, bold=True,
             color="A6A6A6" if dim else theme["text_primary"], font=theme["heading_font"], align="c", anchor="m")
        bullets(slide, x + 0.2, BODY_TOP + 1.95, cw - 0.4, b - BODY_TOP - 2.05, c["bullets"], theme, size=11,
                color="A6A6A6" if dim else "1A1A1A", marker_color=col, spacing=5)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def kpi_tiles(slide, spec, theme, lang):
    """3-5 big numbers (brand colour) with label + note; optional bullets band below."""
    title_and_footer(slide, spec, theme, lang)
    kpis = spec["kpis"]; n = len(kpis); gap = 0.3; tw = (CW - gap * (n - 1)) / n; b = _bottom(spec)
    th = (2.3 if spec.get("bullets") else min(3.2, b - BODY_TOP - 0.3)) + (0.5 if any(k.get("icon") for k in kpis) else 0)
    top = BODY_TOP + 0.15
    for i, k in enumerate(kpis):
        x = MX + i * (tw + gap)
        box(slide, x, top, tw, th, fill=theme["pale"], shape=rect_shape(theme))
        box(slide, x, top, tw, 0.07, fill=theme["primary"])
        dy = 0.0
        if k.get("icon"):
            image(slide, k["icon"], x + tw / 2 - 0.25, top + 0.22, 0.5, 0.5, theme, label="ícone"); dy = 0.5
        text(slide, x, top + 0.25 + dy, tw, 0.9, k["value"], size=36, bold=True, color=theme["text_primary"],
             font=theme["heading_font"], align="c", anchor="m")
        text(slide, x + 0.2, top + 1.2 + dy, tw - 0.4, 0.55, k["label"], size=13, bold=True, font=theme["body_font"], align="c")
        if k.get("note"):
            text(slide, x + 0.2, top + 1.75 + dy, tw - 0.4, max(0.3, th - 1.85 - dy), k["note"], size=10, color="7F7F7F",
                 font=theme["body_font"], align="c")
    if spec.get("bullets"):
        y = top + th + 0.35
        bullets(slide, MX, y, CW, b - y, spec["bullets"], theme, size=12, spacing=6)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def quote_interview(slide, spec, theme, lang):
    """Title = the quote. Left: round photo, name, role, big quote mark. Right: key factors | detail rows."""
    s = dict(spec); s["headline"] = "“" + spec["headline"].strip('“”"') + "”"
    title_and_footer(slide, s, theme, lang)
    p = spec["person"]; lw = 3.4
    image(slide, p.get("photo"), MX + lw / 2 - 0.9, BODY_TOP + 0.2, 1.8, 1.8, theme, label="foto", oval=True)
    text(slide, MX, BODY_TOP + 2.15, lw, 0.35, p["name"], size=15, bold=True, color=theme["text_primary"],
         font=theme["heading_font"], align="c")
    text(slide, MX, BODY_TOP + 2.5, lw, 0.8, p["role"], size=11, color="7F7F7F", font=theme["body_font"], align="c")
    text(slide, MX, BODY_TOP + 3.3, lw, 1.2, "“", size=96, bold=True, color=tint(theme["primary"], .5),
         font="Georgia", align="c")
    x0 = MX + lw + 0.5; fw = 3.0; dx = x0 + fw + 0.3; dw = W - MX - dx
    hline(slide, MX + lw + 0.25, BODY_TOP, MX + lw + 0.25, 6.7, "D0D0D0", 1.5, dash=True)
    head = ("Fatores-chave", "Detalhamento") if lang == "pt" else ("Key factors", "Detail")
    section_header(slide, x0, fw, BODY_TOP - 0.05, head[0], theme)
    section_header(slide, dx, dw, BODY_TOP - 0.05, head[1], theme)
    f = spec["factors"]; step = (6.7 - BODY_TOP - 0.6) / len(f)
    for i, fa in enumerate(f):
        y = BODY_TOP + 0.6 + i * step
        number_badge(slide, x0, y + 0.05, i + 1, theme)
        text(slide, x0 + 0.42, y, fw - 0.42, step - 0.1, fa["label"], size=13, bold=True, font=theme["body_font"])
        text(slide, dx, y, dw, step - 0.1, fa["detail"], size=11, font=theme["body_font"])
        if i: hline(slide, x0, y - 0.08, W - MX, y - 0.08, "E5E5E5", 0.75)


def alpha(shape, opacity_pct):
    """Fill opacity on a solid-filled shape (python-pptx has no API for it)."""
    from lxml import etree
    clr = shape.fill._xPr.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr")
    etree.SubElement(clr, "{http://schemas.openxmlformats.org/drawingml/2006/main}alpha").set("val", str(int(opacity_pct * 1000)))


def key_insight(slide, spec, theme, lang):
    """Dark full-bleed slide with one centred statement (punchline / closing insight)."""
    if spec.get("image"):
        image(slide, spec["image"], 0, 0, W, H, theme)
        alpha(box(slide, 0, 0, W, H, fill="000000"), 60)
    else:
        box(slide, 0, 0, W, H, fill=theme["dark"])
    if spec.get("label"):
        text(slide, 1.5, 2.2, W - 3, 0.4, spec["label"].upper(), size=14, bold=True, color=tint(theme["primary"], .4),
             font=theme["heading_font"], align="c")
    box(slide, W / 2 - 0.6, 2.75, 1.2, 0.06, fill=theme["primary"])
    text(slide, 1.5, 3.0, W - 3, 2.3, spec["statement"], size=26, italic=True, color="FFFFFF",
         font=theme["heading_font"], align="c", anchor="t")


BUILDERS = {"executive_summary": executive_summary, "two_column": two_column, "icon_columns": icon_columns,
            "kpi_tiles": kpi_tiles, "quote_interview": quote_interview, "key_insight": key_insight}
