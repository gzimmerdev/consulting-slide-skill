"""Table archetypes (native, editable PowerPoint tables): comparison_table, scorecard, data_table."""
from lxml import etree
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from .core import (MX, CW, BODY_TOP, text, box, takeaway_bar, title_and_footer, rgb, fmt, harvey, add_runs)

BAR_Y = 6.1
NO_STYLE = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"   # "No Style, No Grid": we draw every fill/border ourselves


def _border(cell, side, color, w_pt):
    tcPr = cell._tc.get_or_add_tcPr()
    ln = etree.SubElement(tcPr, qn(f"a:ln{side}"), w=str(int(w_pt * 12700)))
    etree.SubElement(etree.SubElement(ln, qn("a:solidFill")), qn("a:srgbClr"), val=color)


def _cell(cell, value, theme, size=11, bold=False, color="1A1A1A", fill=None, align="c", bottom=("D9D9D9", 0.75), font=None, mv=0.03, grid=None):
    if grid:                                           # grid=(hex, pt): border on all four sides (schema order lnL, lnR, lnT, lnB)
        for s in "LRTB": _border(cell, s, *grid)
    elif bottom: _border(cell, "B", *bottom)            # borders before fill: schema order lnB < solidFill
    if fill: cell.fill.solid(); cell.fill.fore_color.rgb = rgb(fill)
    else: cell.fill.background()
    cell.margin_left = cell.margin_right = Inches(0.08); cell.margin_top = cell.margin_bottom = Inches(mv)
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf = cell.text_frame; tf.word_wrap = True
    p = tf.paragraphs[0]; p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
    font = font or theme["body_font"]; acc = theme.get("text_primary")
    if isinstance(value, list):     # list of strings: small bulleted lines inside the cell (• glyph, hanging indent)
        for k, it in enumerate(value):
            q = p if k == 0 else tf.add_paragraph(); q.alignment = p.alignment
            pPr = q._p.get_or_add_pPr(); pPr.set("marL", str(Inches(0.12))); pPr.set("indent", str(-Inches(0.12)))
            etree.SubElement(etree.SubElement(pPr, qn("a:buClr")), qn("a:srgbClr")).set("val", color.upper())
            etree.SubElement(pPr, qn("a:buFont")).set("typeface", font)
            etree.SubElement(pPr, qn("a:buChar")).set("char", "•")
            add_runs(q, str(it), size, font, color, bold, accent=acc)
    else: add_runs(p, str(value), size, font, color, bold, accent=acc)
    for q in tf.paragraphs: q._p.get_or_add_endParaRPr().set("sz", str(int(size * 100)))   # empty cells (pill cells) otherwise fall back to 18pt and inflate the row


def _table(slide, nrows, ncols, x, y, w, row_h, col_w):
    gf = slide.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(w), Inches(row_h * nrows))
    tbl = gf.table
    tblPr = tbl._tbl.tblPr
    for k in ("firstRow", "bandRow"): tblPr.set(k, "0")
    sid = tblPr.find(qn("a:tableStyleId"))
    if sid is None: sid = etree.SubElement(tblPr, qn("a:tableStyleId"))
    sid.text = NO_STYLE
    total = sum(col_w)
    for j, cw in enumerate(col_w): tbl.columns[j].width = Inches(w * cw / total)
    for i in range(nrows): tbl.rows[i].height = Inches(row_h)
    return tbl


def _symbol(v, theme):
    """Cell tokens: ✓ ✗ and 'harvey:N' (0-4) render as coloured glyphs; anything else is text."""
    s = str(v)
    if s.startswith("harvey:"): return harvey(float(s.split(":")[1])), theme["text_primary"], 16
    if s in ("✓", "v", "yes", "sim"): return "✓", theme["text_primary"], 16
    if s in ("✗", "x", "no", "não"): return "✗", "A6A6A6", 16
    return s, "1A1A1A", 11


def _highlight_row(slide, x, y, w, h, theme):
    box(slide, x - 0.04, y, w + 0.08, h, line=theme["primary"], line_w=2, dash=True)


def comparison_table(slide, spec, theme, lang):
    """Header row in primary, first column as tinted label cells, ✓/✗/Harvey tokens, dashed outline on the pick."""
    title_and_footer(slide, spec, theme, lang)
    cols, rows = spec["columns"], spec["rows"]
    bottom = BAR_Y - 0.2 if spec.get("takeaway") else 6.7
    row_h = min(0.62, (bottom - BODY_TOP) / (len(rows) + 1))
    tbl = _table(slide, len(rows) + 1, len(cols) + 1, MX, BODY_TOP, CW, row_h, [1.3] + [1] * len(cols))
    _cell(tbl.cell(0, 0), spec.get("corner", ""), theme, fill=theme["primary"], color=theme["on_primary"], bold=True, bottom=None)
    for j, c in enumerate(cols, 1):
        _cell(tbl.cell(0, j), c, theme, size=12, bold=True, fill=theme["primary"], color=theme["on_primary"], bottom=None)
    for i, r in enumerate(rows, 1):
        _cell(tbl.cell(i, 0), r["label"], theme, size=12, bold=True, color=theme["text_primary"], fill=theme["pale"], align="l")
        for j, v in enumerate(r["cells"], 1):
            t, col, sz = _symbol(v, theme)
            _cell(tbl.cell(i, j), t, theme, size=sz, color=col)
    if spec.get("highlight_row") is not None:
        _highlight_row(slide, MX, BODY_TOP + row_h * (spec["highlight_row"] + 1), CW, row_h, theme)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def scorecard(slide, spec, theme, lang):
    """Options x weighted criteria, Harvey balls, weighted total computed here (never trust typed totals); winner outlined."""
    title_and_footer(slide, spec, theme, lang)
    crit, opts = spec["criteria"], spec["options"]; mx = spec.get("max_score", 5)
    wsum = sum(c["weight"] for c in crit)
    totals = [sum(c["weight"] * s for c, s in zip(crit, o["scores"])) / wsum for o in opts]
    win = max(range(len(opts)), key=totals.__getitem__)
    bottom = BAR_Y - 0.2 if spec.get("takeaway") else 6.7
    row_h = min(0.62, (bottom - BODY_TOP - 0.35) / (len(opts) + 1))
    tbl = _table(slide, len(opts) + 1, len(crit) + 2, MX, BODY_TOP, CW, row_h, [1.4] + [1] * len(crit) + [0.9])
    _cell(tbl.cell(0, 0), "Opção" if lang == "pt" else "Option", theme, size=12, bold=True, fill=theme["primary"],
          color=theme["on_primary"], bottom=None)
    for j, c in enumerate(crit, 1):
        _cell(tbl.cell(0, j), f"{c['name']} ({c['weight']:g}%)", theme, size=11, bold=True, fill=theme["primary"],
              color=theme["on_primary"], bottom=None)
    _cell(tbl.cell(0, len(crit) + 1), "Total", theme, size=12, bold=True, fill=theme["dark"], color="FFFFFF", bottom=None)
    for i, (o, t) in enumerate(zip(opts, totals), 1):
        _cell(tbl.cell(i, 0), o["name"], theme, size=12, bold=True, color=theme["text_primary"], fill=theme["pale"], align="l")
        for j, s in enumerate(o["scores"], 1):
            _cell(tbl.cell(i, j), f"{harvey(s / mx * 4)}  {fmt(s, 0, lang)}", theme, size=13, color=theme["text_primary"])
        on = i - 1 == win
        _cell(tbl.cell(i, len(crit) + 1), fmt(t, 1, lang), theme, size=14, bold=True,
              color=theme["on_primary"] if on else "1A1A1A", fill=theme["primary"] if on else None)
    _highlight_row(slide, MX, BODY_TOP + row_h * (win + 1), CW, row_h, theme)
    note = (f"Escala 0–{mx}; total = média ponderada pelos pesos" if lang == "pt"
            else f"Scale 0–{mx}; total = weighted average")
    text(slide, MX, BODY_TOP + row_h * (len(opts) + 1) + 0.08, CW, 0.25, note, size=9, italic=True, color="7F7F7F",
         font=theme["body_font"])
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def data_table(slide, spec, theme, lang):
    """Dense numeric table (DRE, cash flow, projections): years as columns, total rows bold on a tinted band."""
    title_and_footer(slide, spec, theme, lang)
    cols, rows = spec["columns"], spec["rows"]; dec = spec.get("decimals", 0)
    top = BODY_TOP
    if spec.get("unit"):
        text(slide, MX, top, CW, 0.28, spec["unit"], size=11, italic=True, color="7F7F7F", font=theme["body_font"]); top += 0.35
    bottom = BAR_Y - 0.2 if spec.get("takeaway") else 6.7
    row_h = min(0.4, (bottom - top) / (len(rows) + 1)); size = 11 if row_h >= 0.33 else 9
    tbl = _table(slide, len(rows) + 1, len(cols) + 1, MX, top, CW, row_h, [2.4] + [1] * len(cols))
    _cell(tbl.cell(0, 0), spec.get("corner", ""), theme, size=size, bold=True, fill=theme["primary"], color=theme["on_primary"], align="l", bottom=None)
    for j, c in enumerate(cols, 1):
        _cell(tbl.cell(0, j), c, theme, size=size, bold=True, fill=theme["primary"], color=theme["on_primary"], align="r", bottom=None)
    for i, r in enumerate(rows, 1):
        tot = r.get("style") == "total"; sub = r.get("style") == "sub"
        fill = theme["pale"] if tot else None
        line = (theme["primary"], 1.0) if tot else ("E5E5E5", 0.5)
        _cell(tbl.cell(i, 0), ("   " if sub else "") + r["label"], theme, size=size, bold=tot, fill=fill, align="l",
              color="595959" if sub else "1A1A1A", bottom=line)
        for j, v in enumerate(r["values"], 1):
            s = "–" if v is None else (f"({fmt(-v, dec, lang)})" if v < 0 else fmt(v, dec, lang))
            _cell(tbl.cell(i, j), s, theme, size=size, bold=tot, fill=fill, align="r",
                  color="C00000" if (v is not None and v < 0) else "1A1A1A", bottom=line)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


BUILDERS = {"comparison_table": comparison_table, "scorecard": scorecard, "data_table": data_table}
