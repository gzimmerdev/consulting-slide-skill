"""Chart archetypes: chart_takeaway, multi_chart, waterfall, scenarios."""
from pptx.enum.shapes import MSO_SHAPE
from .core import (MX, W, CW, BODY_TOP, LABELS, text, box, hline, number_badge, section_header, pill,
                   bullets, takeaway_bar, title_and_footer, rect_shape)
from .charts import add_chart

BAR_Y = 6.1                      # takeaway bar; ends 6.7, above the footer rule


def _callout(slide, x, y, label, theme):
    """CAGR / delta bubble at the top-right of a chart area (archive: ellipse + arrow)."""
    pill(slide, x, y, 1.5, 0.42, label, theme, size=12, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
         fill="FFFFFF", color=theme["text_primary"], line=theme["primary"], dash=True)


def _insights(slide, items, x, w, top, bottom, theme):
    n = len(items); step = min((bottom - top) / n, 1.1)
    for i, t in enumerate(items, 1):
        y = top + (i - 1) * step
        number_badge(slide, x, y + 0.02, i, theme)
        text(slide, x + 0.42, y, w - 0.42, step - 0.1, t, size=12, font=theme["body_font"])


def chart_takeaway(slide, spec, theme, lang):
    """Chart left (~62%), dashed divider, numbered insights right, takeaway bar."""
    L = LABELS[lang]; c = spec["chart"]
    title_and_footer(slide, spec, theme, lang)
    cw = 8.15; ix = 8.95; iw = W - MX - ix
    section_header(slide, MX, cw, BODY_TOP - 0.05, c["title"], theme)
    if c.get("subtitle"):
        text(slide, MX, BODY_TOP + 0.4, cw, 0.28, c["subtitle"], size=11, italic=True, color="7F7F7F", font=theme["body_font"])
    bottom = BAR_Y - 0.1 if spec.get("takeaway") else 6.7
    co = 0.45 if c.get("callout") else 0
    add_chart(slide, c, theme, MX, BODY_TOP + 0.75 + co, cw, bottom - (BODY_TOP + 0.75 + co))
    if co: _callout(slide, MX + cw - 1.6, BODY_TOP + 0.75, c["callout"], theme)
    hline(slide, 8.75, BODY_TOP, 8.75, bottom - 0.05, "D0D0D0", 1.5, dash=True)
    section_header(slide, ix, iw, BODY_TOP - 0.05, spec.get("insights_title") or L["insights"], theme)
    _insights(slide, spec["insights"], ix, iw, BODY_TOP + 0.65, bottom - 0.15, theme)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def multi_chart(slide, spec, theme, lang):
    """2-3 panels side by side; each has a filled banner stating its own claim, unit subtitle, chart, note."""
    title_and_footer(slide, spec, theme, lang)
    panels = spec["panels"]; n = len(panels); gap = 0.3
    pw = (CW - gap * (n - 1)) / n
    bottom = BAR_Y - 0.1 if spec.get("takeaway") else 6.7
    for i, p in enumerate(panels):
        x = MX + i * (pw + gap)
        pill(slide, x, BODY_TOP, pw, 0.55, p["claim"], theme, size=12, fill=theme["primary"])
        y = BODY_TOP + 0.62
        if p["chart"].get("subtitle"):
            text(slide, x, y, pw, 0.25, p["chart"]["subtitle"], size=10, italic=theme.get("subtitle_italic", True), color="7F7F7F", font=theme["body_font"])
        note_h = 0.5 if p.get("note") else 0
        co = 0.5 if p["chart"].get("callout") else 0        # callout gets its own band above the plot (it covered the tallest bars)
        add_chart(slide, p["chart"], theme, x, y + 0.3 + co, pw, bottom - (y + 0.3 + co) - note_h, font_size=10)
        if co: _callout(slide, x + pw - 1.55, y + 0.3, p["chart"]["callout"], theme)
        if p.get("note"):
            text(slide, x, bottom - note_h + 0.05, pw, note_h, p["note"], size=11, font=theme["body_font"])
        if i < n - 1:
            hline(slide, x + pw + gap / 2, BODY_TOP + 0.65, x + pw + gap / 2, bottom, "D0D0D0", 1.0, dash=True)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def waterfall(slide, spec, theme, lang):
    """Bridge chart: steps[0] = start total, middle = deltas, last = end total. Reuses the chart_takeaway layout."""
    s = dict(spec)
    s["chart"] = {"kind": "waterfall", "title": spec["chart_title"], "subtitle": spec.get("subtitle"),
                  "categories": [x["label"] for x in spec["steps"]],
                  "series": [{"name": "valor", "values": [x["value"] for x in spec["steps"]]}],
                  "number_format": spec.get("number_format", "#,##0"), "callout": spec.get("callout"),
                  "total_last": spec.get("total_last", True)}
    chart_takeaway(slide, s, theme, lang)


def scenarios(slide, spec, theme, lang):
    """Bear / base / bull cards: header, big value, metric rows, assumptions. Recommended card dashed + tinted."""
    title_and_footer(slide, spec, theme, lang)
    cards = spec["scenarios"]; n = len(cards); gap = 0.35
    cw = (CW - gap * (n - 1)) / n; rec = spec.get("recommended", n // 2)
    bottom = BAR_Y - 0.15 if spec.get("takeaway") else 6.7
    for i, c in enumerate(cards):
        x = MX + i * (cw + gap); on = i == rec
        box(slide, x, BODY_TOP, cw, bottom - BODY_TOP, fill=theme["pale"] if on else "FFFFFF",
            line=theme["primary"] if on else "D9D9D9", line_w=1.5 if on else 0.75, dash=on, shape=rect_shape(theme))
        pill(slide, x, BODY_TOP, cw, 0.5, c["name"], theme, size=14, fill=theme["primary"] if on else "7F7F7F")
        text(slide, x, BODY_TOP + 0.65, cw, 0.7, c["value"], size=30, bold=True,
             color=theme["text_primary"] if on else "404040", font=theme["heading_font"], align="c", anchor="m")
        text(slide, x, BODY_TOP + 1.35, cw, 0.3, c.get("value_label", ""), size=11, color="7F7F7F",
             font=theme["body_font"], align="c")
        y = BODY_TOP + 1.8
        for m in c.get("metrics", []):
            hline(slide, x + 0.2, y, x + cw - 0.2, y, "D9D9D9", 0.75)
            text(slide, x + 0.25, y + 0.05, cw * 0.6, 0.32, m["label"], size=11, color="404040", font=theme["body_font"], anchor="m")
            text(slide, x + cw * 0.55, y + 0.05, cw * 0.45 - 0.25, 0.32, m["value"], size=12, bold=True,
                 font=theme["body_font"], align="r", anchor="m")
            y += 0.4
        if c.get("assumptions"):
            bullets(slide, x + 0.25, y + 0.15, cw - 0.5, bottom - y - 0.25, c["assumptions"], theme, size=10, spacing=3)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


BUILDERS = {"chart_takeaway": chart_takeaway, "multi_chart": multi_chart, "waterfall": waterfall, "scenarios": scenarios}
