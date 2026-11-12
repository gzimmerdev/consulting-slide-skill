"""Native, editable charts styled like the archive. One entry point: add_chart(slide, c, theme, x, y, w, h).

c = {kind, categories, series:[{name, values}], number_format?, highlight?, gridlines?, min?, max?, legend?, percent?}
kinds: column | stacked | stacked100 | bar | line | pie | doughnut | waterfall | scatter | bubble (XY, see add_scatter)
Rules (docs/design-system.md §5 + chart add-in / Bain "Chart it up" training): gap 80, overlap 100 when stacked,
value axis hidden, bold direct data labels, series dark->light of the primary, single-series "story colouring"
via highlight (rest grey), no gridlines by default.
"""
from pptx.oxml.ns import qn
from pptx.chart.data import CategoryChartData, XyChartData, BubbleChartData
from pptx.enum.chart import XL_MARKER_STYLE, XL_CHART_TYPE, XL_LABEL_POSITION, XL_LEGEND_POSITION, XL_TICK_MARK, XL_TICK_LABEL_POSITION
from pptx.util import Pt, Inches
import re
import copy, math
from lxml import etree
from .core import rgb, tint, shade, fmt, hline, text

KINDS = {"column": XL_CHART_TYPE.COLUMN_CLUSTERED, "stacked": XL_CHART_TYPE.COLUMN_STACKED,
         "stacked100": XL_CHART_TYPE.COLUMN_STACKED_100, "bar": XL_CHART_TYPE.BAR_CLUSTERED,
         "line": XL_CHART_TYPE.LINE_MARKERS, "pie": XL_CHART_TYPE.PIE, "doughnut": XL_CHART_TYPE.DOUGHNUT,
         "waterfall": XL_CHART_TYPE.COLUMN_STACKED, "scatter": XL_CHART_TYPE.XY_SCATTER, "bubble": XL_CHART_TYPE.BUBBLE}
GREY_BAR, AXIS, LABEL = "D9D9D9", "BFBFBF", "404040"
C_NS = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def waterfall_parts(values, total_last=True):
    """Bridge = stacked column with an invisible base. values: start total, deltas (+/-), end total."""
    base, up, down, run = [], [], [], 0.0
    for i, x in enumerate(values):
        if i == 0 or (total_last and i == len(values) - 1):
            base.append(0); up.append(x); down.append(0); run = x
        elif x >= 0:
            base.append(run); up.append(x); down.append(0); run += x
        else:
            run += x; base.append(run); up.append(0); down.append(-x)
    return base, up, down


def _parts_values(c):
    """Waterfall values as drawn. total_first: first = total, the rest hang down from it (magnitudes)."""
    v = c["series"][0]["values"]
    return [v[0]] + [-abs(x) for x in v[1:]] if c.get("total_first") else v


def tops(c):
    """Value at the top of each category's bars (stack total for stacked/waterfall, max otherwise)."""
    ser = [s["values"] for s in c["series"]]; n = len(c["categories"]); k = c["kind"]
    if k == "waterfall":
        b, u, d = waterfall_parts(_parts_values(c), False if c.get("total_first") else c.get("total_last", True))
        return [b[i] + u[i] + d[i] for i in range(n)]
    if k == "stacked100": return [1.0] * n
    if k == "stacked": return [sum(s[i] for s in ser) for i in range(n)]
    return [max(s[i] for s in ser) for i in range(n)]


def scale_max(c):
    """Value-axis maximum. Fixed (not auto) so annotation geometry is computable; c['head'] = headroom factor."""
    if c.get("max") is not None: return c["max"]
    return 1.0 if c["kind"] == "stacked100" else max(tops(c)) * c.get("head", 1.12)


SMALL_FRAC = 0.06    # ponytail: "too small for its label" = under 6% of the axis maximum (10pt label needs ~0.17in); tune here


def small_limit(c, ph):
    """Value under which a stacked segment is too small for an inside label: 6% of the axis, and on a short plot (ph = plot height in in) also anything under 0.17in."""
    return max(SMALL_FRAC * scale_max(c), 0.17 / ph * scale_max(c))


def small_segments(c, ph):
    """[(series idx, category idx, value)] of stacked segments too small for an inside label (small_callouts: written outside instead)."""
    lim = small_limit(c, ph)
    return [(si, i, v) for si, s in enumerate(c["series"]) for i, v in enumerate(s["values"]) if v < lim]


def _num(v, nf, lang):
    """Plain text of a number under a simple Excel code ('#,##0', '0.0', '0%').
    # ponytail: custom label text is static (not linked to the cell): retype it if the chart data is edited by hand."""
    lit = re.findall(r'"([^"]*)"', nf.split(";")[0]); core = re.sub(r'"[^"]*"', "", nf.split(";")[0])     # quoted text is literal: 0"%" shows 41%, it does not scale like 0%
    pct = "%" in core
    frac = core.split(".")[1].rstrip("%") if "." in core else ""
    dec = len(frac); v = v * 100 if pct else v
    while dec > frac.count("0") and round(v, dec - 1) == round(v, dec): dec -= 1   # '#' decimals drop trailing zeros (0.0# -> 44,8 / 13,44)
    return fmt(v, dec, lang) + ("%" if pct else "") + "".join(lit)


def _top_labels(ser, texts, size, color, bold=True):
    """Invisible pad series stacked on top; its labels (INSIDE_BASE) print a text above each column. Native + editable."""
    ser.format.fill.background(); ser.format.line.fill.background()
    for i, t in enumerate(texts):
        if not t: continue
        dl = ser.points[i].data_label; dl.position = XL_LABEL_POSITION.INSIDE_BASE
        dl.text_frame.text = t
        r = dl.text_frame.paragraphs[0].runs[0]
        r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = rgb(color)


def _hide_legend_entry(ch, idx):
    leg = ch._chartSpace.chart.find(C_NS + "legend")
    e = etree.Element(C_NS + "legendEntry")
    etree.SubElement(e, C_NS + "idx", val=str(idx)); etree.SubElement(e, C_NS + "delete", val="1")
    leg.find(C_NS + "legendPos").addnext(e)


def _inner_layout(ch, fr):
    """Manual INNER plot-area layout (fractions of the chart frame): makes plot geometry known to the caller."""
    pa = ch._chartSpace.chart.plotArea
    lay = pa.find(C_NS + "layout")
    if lay is None: lay = etree.Element(C_NS + "layout"); pa.insert(0, lay)
    for k in list(lay): lay.remove(k)
    ml = etree.SubElement(lay, C_NS + "manualLayout")
    etree.SubElement(ml, C_NS + "layoutTarget", val="inner")
    for tag in ("xMode", "yMode"): etree.SubElement(ml, C_NS + tag, val="edge")
    for tag, v in zip("xywh", fr): etree.SubElement(ml, C_NS + tag, val=f"{v:.4f}")


def category_rects(c, x, y, w, h):
    """Where each category sits (inches) on a chart added with c['inner'] at frame (x, y, w, h).
    column-like: x0/x1 = category slot, bx0/bx1 = bar group, top = y of the bar top, base = y of the axis.
    bar: y0/y1 = slot, end = x of the bar end. Matches add_chart exactly because both use inner + scale_max."""
    fx, fy, fw, fh = c["inner"]; px, py, pw, ph = x + fx * w, y + fy * h, fw * w, fh * h
    n = len(c["categories"]); mx = scale_max(c); tp = tops(c)
    gap = c.get("gap", 50 if c["kind"] == "waterfall" else 80); out = []
    for i in range(n):
        if c["kind"] == "bar":
            sl = ph / n; out.append(dict(y0=py + i * sl, y1=py + (i + 1) * sl, end=px + pw * tp[i] / mx, px=px, pw=pw))
        else:
            sl = pw / n; bw = sl / (1 + gap / 100)
            x0 = px + i * sl
            out.append(dict(x0=x0, x1=x0 + sl, bx0=x0 + (sl - bw) / 2, bx1=x0 + (sl + bw) / 2,
                            top=py + ph * (1 - tp[i] / mx), base=py + ph))
    return out


def _no_label(s, i):
    d = s.points[i].data_label._get_or_add_dLbl()
    for ch_ in list(d):
        if ch_.tag != C_NS + "idx": d.remove(ch_)
    etree.SubElement(d, C_NS + "delete", val="1")


def _is_dark(h):    # luma < 128 -> white label on that fill
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); return 0.299 * r + 0.587 * g + 0.114 * b < 128


def _labels(s, nf, size, color, pos, bold=False):   # ponytail: regular-weight value labels (hand-made look); bold only on key numbers
    dl = s.data_labels
    dl.show_value = True; dl.number_format = nf; dl.number_format_is_linked = False
    dl.font.size = Pt(size); dl.font.bold = bold; dl.font.color.rgb = rgb(color)
    if pos is not None: dl.position = pos
    return dl


def _connectors(slide, c, x, y, w, h):
    """Thin dashed grey line from each waterfall bar's end level to the next bar (spec option connectors). Needs c['inner']."""
    if not c.get("inner"): return
    b, u, d = waterfall_parts(_parts_values(c), False if c.get("total_first") else c.get("total_last", True))
    R = category_rects(c, x, y, w, h); T = tops(c)
    for i in range(len(R) - 1):
        lvl = b[i] + u[i] if u[i] else b[i]
        yy = R[i]["base"] - (R[i]["base"] - R[i]["top"]) * lvl / T[i] if T[i] else R[i]["base"]
        hline(slide, R[i]["bx1"], yy, R[i + 1]["bx0"], yy, "7F7F7F", 0.75, dash=True)


def xy_series(c):
    """[(name, points)] of a scatter/bubble chart: spec has "series":[{name, points}] or a flat "points" list (one series)."""
    return [(s["name"], s["points"]) for s in c["series"]] if c.get("series") else [(c.get("name", "Pontos"), c["points"])]


def _nice_range(vals, lo=None, hi=None):
    """(min, max, step) of an axis covering vals with ~12% padding on round numbers. # ponytail: ~5 ticks, 1/2/5 steps."""
    a, b = min(vals), max(vals); pad = (b - a or abs(b) or 1) * .12
    raw = (b - a + 2 * pad) / 5; mag = 10 ** math.floor(math.log10(raw)); step = next(m * mag for m in (1, 2, 5, 10) if m * mag >= raw)
    lo = math.floor((a - pad) / step) * step if lo is None else lo; hi = math.ceil((b + pad) / step) * step if hi is None else hi
    return lo, hi, step


def add_scatter(slide, c, theme, x, y, w, h, font_size=10):
    """Native XY chart (scatter) or bubble chart (third value = size). Points {x, y, label?, size?}; options: highlight (point indexes of the
    first series in primary, the rest grey), x_title / y_title, x_format / y_format, x_min x_max y_min y_max, bubble_scale, gridlines, legend, labels,
    quadrants {x: value|"mean", y: value|"mean", labels: [top-left, top-right, bottom-left, bottom-right]}: thin dashed grey lines + light
    corner labels, drawn as native shapes over the fixed plot area. Returns the chart."""
    kind = c["kind"]; bub = kind == "bubble"; ser = xy_series(c); p = theme["primary"]; LB = theme.get("label_color", LABEL)
    cd = BubbleChartData() if bub else XyChartData()
    for name, pts in ser:
        s = cd.add_series(name)
        for q in pts:
            if bub: s.add_data_point(q["x"], q["y"], q.get("size", 1))
            else: s.add_data_point(q["x"], q["y"])
    xs = [q["x"] for _, pts in ser for q in pts]; ys = [q["y"] for _, pts in ser for q in pts]
    ax = _nice_range(xs, c.get("x_min"), c.get("x_max")); ay = _nice_range(ys, c.get("y_min"), c.get("y_max"))   # ponytail: bubbles may clip at the edge: widen with x_min/x_max
    legend = c.get("legend", len(ser) > 1)
    lm = 0.12 if c.get("y_title") else 0.08; bm = (0.17 if c.get("x_title") else 0.10) + (0.08 if legend else 0)
    inner = (lm, 0.04, 0.97 - lm, 1 - 0.04 - bm)
    ch = slide.shapes.add_chart(KINDS[kind], Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.has_title = False; ch.font.size = Pt(font_size); ch.font.name = theme["body_font"]; ch.font.color.rgb = rgb(LB)
    ch.has_legend = legend
    if legend: ch.legend.position = XL_LEGEND_POSITION.BOTTOM; ch.legend.include_in_layout = False; ch.legend.font.size = Pt(theme.get("legend_size", font_size))
    for axis, (lo, hi, st), t, f in ((ch.category_axis, ax, c.get("x_title"), c.get("x_format")), (ch.value_axis, ay, c.get("y_title"), c.get("y_format"))):   # XY: category_axis = the X value axis
        axis.minimum_scale, axis.maximum_scale, axis.major_unit = lo, hi, st
        axis.visible = True; axis.has_major_gridlines = bool(c.get("gridlines", False))
        if axis.has_major_gridlines: axis.major_gridlines.format.line.color.rgb = rgb("E5E5E5"); axis.major_gridlines.format.line.width = Pt(.5)
        axis.format.line.color.rgb = rgb(AXIS); axis.major_tick_mark = XL_TICK_MARK.NONE
        axis.tick_labels.font.size = Pt(c.get("axis_size", 9)); axis.tick_labels.font.color.rgb = rgb(c.get("axis_color", "7F7F7F"))
        if f: axis.tick_labels.number_format = f; axis.tick_labels.number_format_is_linked = False
        if t:
            axis.has_title = True; tf = axis.axis_title.text_frame; tf.text = t
            r = tf.paragraphs[0].runs[0]; r.font.size = Pt(10); r.font.bold = False; r.font.color.rgb = rgb("595959")
    _inner_layout(ch, inner)
    plot = ch.plots[0]
    if not bub: plot.vary_by_categories = False
    else: plot.bubble_scale = c.get("bubble_scale", 50)
    hl = set(c.get("highlight") or []) if len(ser) == 1 else set()

    def paint(fm, color):
        fm.fill.solid(); fm.fill.fore_color.rgb = rgb(color)
        if bub: etree.SubElement(fm.fill._xPr.find(A_NS + "solidFill")[0], A_NS + "alpha", val="75000")      # translucent bubbles: overlaps stay readable

    for i, s in enumerate(list(plot.series)):
        col = p if len(ser) == 1 and not hl else theme["series"][i % len(theme["series"])]
        if c.get("colors") and i < len(c["colors"]): col = c["colors"][i]
        if hl: col = "A6A6A6"                                     # story colouring: highlighted points in primary, the rest grey
        if bub: paint(s.format, col)
        else:
            s.marker.style = XL_MARKER_STYLE.CIRCLE; s.marker.size = 9
            s.marker.format.fill.solid(); s.marker.format.fill.fore_color.rgb = rgb(col); s.marker.format.line.color.rgb = rgb("FFFFFF")
        for k in hl:
            if k >= len(ser[0][1]): continue
            if bub: paint(s.points[k].format, p)
            else:
                m = s.points[k].marker; m.style = XL_MARKER_STYLE.CIRCLE; m.size = 9
                m.format.fill.solid(); m.format.fill.fore_color.rgb = rgb(p); m.format.line.color.rgb = rgb("FFFFFF")
        for k, q in enumerate(ser[i][1] if c.get("labels", True) else []):
            if not q.get("label"): continue
            dl = s.points[k].data_label; dl.position = XL_LABEL_POSITION.RIGHT; dl.text_frame.text = q["label"]    # ponytail: static text, not linked to the cells
            r = dl.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(font_size); r.font.bold = k in hl; r.font.color.rgb = rgb("7F7F7F" if hl and k not in hl else "1A1A1A")
    qd = c.get("quadrants")
    if qd:
        qx = sum(xs) / len(xs) if qd.get("x") == "mean" else qd.get("x"); qy = sum(ys) / len(ys) if qd.get("y") == "mean" else qd.get("y")
        px, py, pw, ph = x + inner[0] * w, y + inner[1] * h, inner[2] * w, inner[3] * h
        if qx is not None and ax[0] < qx < ax[1]: xx = px + pw * (qx - ax[0]) / (ax[1] - ax[0]); hline(slide, xx, py, xx, py + ph, "7F7F7F", .75, dash=True)
        if qy is not None and ay[0] < qy < ay[1]: yy = py + ph * (1 - (qy - ay[0]) / (ay[1] - ay[0])); hline(slide, px, yy, px + pw, yy, "7F7F7F", .75, dash=True)
        for k, t in enumerate(qd.get("labels") or []):
            lw = min(pw / 2 - 0.1, 2.2); right = k % 2; low = k > 1
            text(slide, px + (pw - lw - 0.06 if right else 0.06), py + (ph - 0.26 if low else 0.04), lw, 0.22, t, size=9, italic=True, color="8C8C8C",
                 font=theme["body_font"], align="r" if right else "l", anchor="b" if low else "t")
    return ch


def add_chart(slide, c, theme, x, y, w, h, font_size=10):
    if c["kind"] in ("scatter", "bubble"): return add_scatter(slide, c, theme, x, y, w, h, font_size)
    kind = c["kind"]; nf = c.get("number_format", "General"); p = theme["primary"]; LB = theme.get("label_color", LABEL)
    cd = CategoryChartData(number_format=nf); cd.categories = c["categories"]
    tf_ = kind == "waterfall" and c.get("total_first")          # total bar, then the breakdown hanging down from it
    ab = tf_ or (kind == "waterfall" and c.get("labels_above"))     # delta labels above the bars (pad series)
    tot = kind == "stacked" and c.get("totals")                 # total labels above each stack
    lang = c.get("lang", "pt"); pad = 0.07 * max(tops(c))
    if kind == "waterfall":
        for name, vals in zip(("base", "up", "down"), waterfall_parts(_parts_values(c), False if tf_ else c.get("total_last", True))):
            cd.add_series(name, vals)
        if ab: cd.add_series("rótulo", [pad] * len(c["categories"]))
    else:
        for s in c["series"]:
            cd.add_series(s["name"], s["values"])
        if tot: cd.add_series("Total", [pad] * len(c["categories"]))
    ch = slide.shapes.add_chart(KINDS[kind], Inches(x), Inches(y), Inches(w), Inches(h), cd).chart
    ch.has_title = False
    ch.font.size = Pt(font_size); ch.font.name = theme["body_font"]; ch.font.color.rgb = rgb(LB)
    nser = len(c["series"]); pie = kind in ("pie", "doughnut")
    ch.has_legend = c.get("legend", pie or (nser > 1 and kind != "waterfall"))
    if ch.has_legend:
        ch.legend.position = XL_LEGEND_POSITION.RIGHT if pie else XL_LEGEND_POSITION.TOP if c.get("legend_pos") in ("top", "top_tight") else XL_LEGEND_POSITION.BOTTOM   # below the plot, as in the archive decks (top legend collided with the value labels)
        ch.legend.include_in_layout = False; ch.legend.font.size = Pt(theme.get("legend_size", font_size))
        if tot: _hide_legend_entry(ch, nser)
        if c.get("legend_pos") == "inside":      # spec legend_pos "inside": legend floats over the plot's bottom-right corner (s06 original)
            lg_ = ch._chartSpace.chart.find(C_NS + "legend"); ch.legend.include_in_layout = True
            lay = etree.fromstring('<c:layout xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:manualLayout><c:xMode val="edge"/><c:yMode val="edge"/><c:x val="0.3"/><c:y val="0.68"/><c:w val="0.68"/><c:h val="0.09"/></c:manualLayout></c:layout>')
            for old in lg_.findall(C_NS + "layout"): lg_.remove(old)
            lg_.find(C_NS + "legendPos").addnext(lay)
    plot = ch.plots[0]

    if pie:
        plot.vary_by_categories = True
        s = plot.series[0]
        cols = [p, tint(p, .35), tint(p, .6), tint(p, .8), "A6A6A6", "D9D9D9"]
        for i in range(len(c["categories"])):
            pt = s.points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(cols[i % len(cols)])
            pt.format.line.color.rgb = rgb("FFFFFF")
        if kind == "doughnut":
            hole = plot._element.find(C_NS + "holeSize")
            if hole is not None: hole.set("val", "60")
        if c.get("inner"): _inner_layout(ch, c["inner"])        # composite callouts: ring geometry known to the caller
        if c.get("callouts"): return ch                          # names + values are drawn outside the ring by composite._pie_callouts
        dl = _labels(s, "0%" if c.get("percent") else nf, font_size, "FFFFFF", None)
        if c.get("percent"): dl.show_value = False; dl.show_percentage = True
        if c.get("names"): dl.show_category_name = True   # spec option: category name beside the value (callout-style)
        vals = c["series"][0]["values"]; sd = s._element.find(C_NS + "dLbls")
        for i in range(len(vals)):                  # dark label on a light slice (white is illegible there): own dLbl = copy of the series label settings
            if _is_dark(cols[i % len(cols)]): continue
            d = s.points[i].data_label._get_or_add_dLbl()
            for k in list(d):
                if k.tag != C_NS + "idx": d.remove(k)
            for k in sd:
                if k.tag != C_NS + "dLbl": d.append(copy.deepcopy(k))
            for k in d.iter(A_NS + "srgbClr"): k.set("val", LB)
        for i, v in enumerate(vals):                # no labels on slivers under 6% (clipped at the ring edge)
            if v < 0.06 * sum(vals): _no_label(s, i)
        return ch

    va, ca = ch.value_axis, ch.category_axis
    va.visible = bool(c.get("value_axis", False))     # spec option; hidden by default (waterfall/stacked/column look)
    if va.visible: va.tick_labels.font.size = Pt(c.get("axis_size", 9)); va.tick_labels.font.color.rgb = rgb(c.get("axis_color", "7F7F7F"))     # chart options axis_size / axis_color
    if va.visible and c.get("axis_format"): va.tick_labels.number_format = c["axis_format"]; va.tick_labels.number_format_is_linked = False
    va.has_major_gridlines = bool(c.get("gridlines", False))
    if va.has_major_gridlines:
        va.major_gridlines.format.line.color.rgb = rgb("E5E5E5"); va.major_gridlines.format.line.width = Pt(.5)
    if kind != "stacked100":
        va.minimum_scale = 0 if c.get("min") is None else c["min"]
        if c.get("max") is not None: va.maximum_scale = c["max"]
        if c.get("major_unit"): va.major_unit = c["major_unit"]      # chart option: value-axis step
    if c.get("inner"):
        _inner_layout(ch, c["inner"])
        if kind != "stacked100": va.maximum_scale = scale_max(c)
    ca.has_major_gridlines = False; ca.major_tick_mark = XL_TICK_MARK.NONE
    ca.format.line.color.rgb = rgb(AXIS); ca.tick_labels.font.size = Pt(c.get("cat_size", font_size))     # chart option cat_size (pt): small category labels (s03)
    if kind == "bar": ca.reverse_order = True
    if kind != "waterfall" and any(v is not None and v < 0 for s in c["series"] for v in s["values"]):
        ca.tick_label_position = XL_TICK_LABEL_POSITION.LOW          # negative bars: category labels below the plot, not on the zero line
        if c.get("min") is None and kind != "stacked100": va.minimum_scale = None   # let the axis go below 0
        for s in plot.series:
            if hasattr(s, "invert_if_negative"): s.invert_if_negative = False   # PowerPoint default paints negative bars white (invisible)
    bold_axis = kind == "waterfall" and theme.get("waterfall_label_style") == "bold_axis"      # spec option: bold dark category labels, larger regular dark value labels (s03 original)
    if bold_axis: ca.tick_labels.font.bold = True; ca.tick_labels.font.color.rgb = rgb("1A1A1A")

    stacked = kind in ("stacked", "stacked100", "waterfall")
    if kind != "line":
        plot.gap_width = c.get("gap", 50 if kind == "waterfall" else theme.get("bar_gap", 80))      # theme bar_gap: 50 thick bars ... 150 thin bars
        plot.overlap = 100 if stacked else (-10 if nser > 1 else 0)
    plot.vary_by_categories = False

    if kind == "waterfall":
        b, u, d = list(plot.series)[:3]
        b.format.fill.background(); b.format.line.fill.background()
        u.format.fill.solid(); u.format.fill.fore_color.rgb = rgb(p)
        d.format.fill.solid(); d.format.fill.fore_color.rgb = rgb(p if tf_ and not c.get("highlight") else theme.get("context_bar", "A6A6A6"))
        v = c["series"][0]["values"]
        for i in range(len(v)):                     # totals in a dark shade of the primary
            if i == 0 or (not tf_ and c.get("total_last", True) and i == len(v) - 1):
                pt = u.points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(theme.get("waterfall_total", "4D4D4D") if tf_ else theme.get("total_bar") or shade(p, .45))   # total_first: dark grey total (user's reference); other waterfalls keep the dark primary shade
        if c.get("end_color") and len(v) > 1:     # spec option end_color: own colour for the last (end) bar, e.g. light context blue (s07)
            pt = (d if tf_ else u).points[len(v) - 1]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(c["end_color"])   # total_first (s05): the last hanging step
        hc = c.get("highlight_colors") or []          # spec option: own colour per highlighted step (s03: China red, USA maroon)
        for k, i in enumerate(c.get("highlight") or []):          # 'highlight' steps in primary, the other steps grey (context bars)
            pt = d.points[i]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(hc[k] if k < len(hc) else p)
        if c.get("connectors"): _connectors(slide, c, x, y, w, h)
        if ab:                                    # labels above every bar (pad series), none inside
            ins = set(c.get("inside_labels") or [])      # chart option inside_labels: category indices labelled white, centred inside the bar (s03)
            _top_labels(plot.series[3], [("" if i in ins else _num(abs(x), nf, lang)) for i, x in enumerate(v)], font_size + 2 if bold_axis else font_size, "1A1A1A" if bold_axis else LB, not bold_axis)
            for i in (c.get("bold_labels") or []):      # chart option bold_labels: category indices whose top value label is bold near-black (highlighted step)
                r = plot.series[3].points[i].data_label.text_frame.paragraphs[0].runs
                if r: r[0].font.bold = True; r[0].font.color.rgb = rgb("1A1A1A")
            for i in ins:
                dl = (d if (i if tf_ else i < len(v) - 1 or not c.get("total_last", True)) else u).points[i].data_label; dl.position = XL_LABEL_POSITION.CENTER; dl.text_frame.text = _num(abs(v[i]), nf, lang)
                r = dl.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(font_size + 2 if bold_axis else font_size); r.font.bold = not bold_axis; r.font.color.rgb = rgb(c.get("inside_color", "FFFFFF"))
            return ch
        hide0 = nf + ";-" + nf + ";;"               # hide zero labels of the empty segments
        _labels(u, hide0, font_size, "FFFFFF", XL_LABEL_POSITION.CENTER)
        _labels(d, nf + ";-" + nf + ";;", font_size, "FFFFFF", XL_LABEL_POSITION.CENTER)     # decrements: magnitude without the minus sign (as in the hand-made originals)
        return ch

    hl = set(c.get("highlight") or [])
    for i, s in enumerate(list(plot.series)[:nser]):
        col = theme["series"][i % len(theme["series"])]
        if nser == 1 and kind in ("column", "bar") and not hl: col = theme["dark"]   # one data series: dark tone of the brand, not the saturated primary on every bar
        if kind == "stacked" and nser > 1 and i == 0: col = theme["dark"]            # stacked: dark fixed-cost base, lighter tint on top (not one saturated colour per segment)
        if kind == "stacked" and nser > 2 and i == 1: col = p                        # stacked: brand red middle band (archive decks), pale tint only on top
        if c.get("colors") and i < len(c["colors"]): col = c["colors"][i]               # explicit per-series colours (spec option)
        if kind == "line":
            s.format.line.color.rgb = rgb(col); s.format.line.width = Pt(1.5); s.smooth = bool(c.get("smooth", False))   # thin line, small round dots as in the archive
            if c.get("markers", True):
                s.marker.format.fill.solid(); s.marker.format.fill.fore_color.rgb = rgb(col)
                s.marker.format.line.color.rgb = rgb(col)
                s.marker.style = XL_MARKER_STYLE.CIRCLE; s.marker.size = 5
            else: s.marker.style = XL_MARKER_STYLE.NONE
        else:
            s.format.fill.solid(); s.format.fill.fore_color.rgb = rgb(col)
            if hl and nser == 1:
                s.format.fill.fore_color.rgb = rgb(GREY_BAR)
                for k in hl:
                    pt = s.points[k]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(p)
            if nser == 1:
                for k, pc in enumerate((c.get("point_colors") or [])[:len(c["categories"])]):      # spec option: own colour per bar (growth blue, falls red, total grey)
                    if pc:
                        pt = s.points[k]; pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(pc)
                        dp = s._element.get_or_add_dPt_for_point(k)
                        if not dp.xpath("c:invertIfNegative"): dp.idx.addnext(dp.makeelement(qn("c:invertIfNegative"), {"val": "0"}))      # a coloured negative point turns white unless told not to
        lnf = "0%" if kind == "stacked100" and nf == "General" else nf
        if stacked:
            sz, lc = theme.get("stacked_label_font", font_size), "FFFFFF" if _is_dark(col) else LB
            _labels(s, lnf, sz, lc, XL_LABEL_POSITION.CENTER)
            if lang == "en" and kind == "stacked" and nf != "General":   # number_format follows the viewer's locale (comma in pt-BR), so en decks write the text: dots like the totals
                for k, v in enumerate(c["series"][i]["values"]):
                    dl = s.points[k].data_label; dl.position = XL_LABEL_POSITION.CENTER; dl.text_frame.text = _num(v, nf, lang)
                    r = dl.text_frame.paragraphs[0].runs[0]; r.font.size = Pt(sz); r.font.bold = False; r.font.color.rgb = rgb(lc)
        elif c.get("labels", True):
            _labels(s, lnf, font_size, LB,
                    XL_LABEL_POSITION.ABOVE if kind == "line" else XL_LABEL_POSITION.OUTSIDE_END)
            if (kind == "line" and nser > 1) or c.get("end_labels"):   # multi-series lines / spec end_labels: only first and last point labelled (labels collide)
                for k in range(1, len(c["categories"]) - 1): _no_label(s, k)
    if stacked and kind == "stacked":               # no labels inside slivers too small to read
        small = small_limit(c, c["inner"][3] * h) if c.get("small_callouts") else 0.09 * max(tops(c))
        for s, sd in zip(list(plot.series)[:nser], c["series"]):
            for i, v in enumerate(sd["values"]):
                if v < small:
                    d = s.points[i].data_label._get_or_add_dLbl()
                    for ch_ in list(d):
                        if ch_.tag != C_NS + "idx": d.remove(ch_)
                    etree.SubElement(d, C_NS + "delete", val="1")
    if tot:
        sums = [sum(s["values"][i] for s in c["series"]) for i in range(len(c["categories"]))]
        _top_labels(plot.series[nser], [_num(t, nf, lang) for t in sums], font_size, theme.get("total_color", LB), theme.get("total_bold", True))   # theme tokens (bain_red: regular black totals like the user reference)
    return ch
