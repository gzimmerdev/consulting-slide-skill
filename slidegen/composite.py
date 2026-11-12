"""composite archetype: several ELEMENTS (chart, table, bullets, cards, kpis, map, process, matrix) on one slide, joined by
LINKS (arrow, bracket, highlight, callout, xref). Layouts split the body into slots; panels fill the slots in reading order.
Everything is built from the existing helpers (add_chart, _table/_cell, draw_tiles, draw_matrix, bullets, number_badge).
"""
import math, re
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.dml import MSO_LINE
from pptx.oxml.ns import qn
from lxml import etree
from pptx.util import Inches, Pt
from .core import (MX, W, CW, BODY_TOP, text, box, hline, number_badge, pill, bullets, takeaway_bar, title_and_footer,
                   rect_shape, FOOTER_RULE_Y, set_text, rgb, tint, load_theme, image, ICONS, TITLE_H)
from .charts import add_chart, category_rects, tops, small_segments, _num, _is_dark, waterfall_parts, _parts_values
from .table_slides import _table, _cell, _border
from .diagram_slides import draw_tiles, draw_matrix, draw_tree, _arrow_end

G = 0.22                     # gutter between panels (tighter: ruling 2026-11-08)
MIN_CHART = 1.6               # min chart frame (in): ~1.0in of plot after legend and axis labels, the shortest readable archive stack; smallest approved frame after its own title rows is ~1.7 (1.05 with a scale bar); _need ignores title rows and gaps, so charts could get ~1.4
HEAD = 0.32                  # panel sub-header height
BAR_Y = 6.1
PILL_H = 0.34                # row of legend pills at the bottom of a panel (panel option pill_legend)
ICON_D = 0.4                 # icon disc diameter in bullets / cards rows
ICON_W = 0.42                # icon in a table cell
SIDE_W = 0.3                 # vertical side-label strip (panel option side_label)
SC_H = 0.75                  # gradient scale bar add-on (panel option scale)
SLOTS = {"1": 1, "2col": 2, "3col": 3, "4col": 4, "T|B": 2, "L|R2": 3, "L2|R": 3, "2x2": 4, "2x3": 6, "L|R3": 4, "T|B3": 4, "T2|B3": 5, "cols": 0}     # cols: free columns, each split into rows (spec "cols"); slot count = total rows
NWEIGHTS = {"1": 0, "2col": 2, "3col": 3, "4col": 4, "T|B": 2, "L|R2": 2, "L2|R": 2, "2x2": 2, "2x3": 3, "L|R3": 2, "T|B3": 2, "T2|B3": 2, "cols": 0}
NRIGHT = {"L|R2": 2, "L|R3": 3, "T|B3": 3, "T2|B3": 3}     # right_weights: slots of the right column (L|R*) or of the bottom row (T|B3, T2|B3)
CPE = 0.47                   # ponytail: average glyph width = 0.47 em (Arial mixed text measures ~0.46): text-capacity estimate
WRAP = 0.95                  # ponytail: word wrap wastes ~8% of every line; real PowerPoint metrics are not available here


# ---------------------------------------------------------------- geometry
def _split(x, y, w, h, n, wts, horizontal=True):
    tot = sum(wts) if wts else n; wts = wts or [1] * n
    span = (w if horizontal else h) - G * (n - 1); pos = x if horizontal else y; out = []
    for k in range(n):
        s = span * wts[k] / tot
        out.append((pos, y, s, h) if horizontal else (x, pos, w, s)); pos += s + G
    return out


def _cols(cols, x, y, w, h):
    """layout "cols": [(column rect, header height, [row slots], header width)]; a column with a title / intro reserves HEAD + the intro text height above its rows.
    A column with "span": n carries its header across the next n-1 columns, which then reserve the same header height."""
    out = []; carry = 0; hh0 = 0
    for k, ((cx, cy, cw, ch), c) in enumerate(zip(_split(x, y, w, h, len(cols), [c["w"] for c in cols]), cols)):
        if carry: carry -= 1; hh = hh0; hw = 0
        else:
            hh = (HEAD if c.get("title") else 0) + (_lines(c["intro"], cw, c.get("intro_size", 11))[0] * c.get("intro_size", 11) * 1.2 / 72 + 0.12 if c.get("intro") else 0)
            carry = c.get("span", 1) - 1; hh0 = hh; hw = cw
            for q in range(1, c.get("span", 1)): hw += G + _split(x, y, w, h, len(cols), [c_["w"] for c_ in cols])[k + q][2]
        rs = _split(cx, cy + hh, cw, ch - hh, len(c["rows"]), c["rows"], horizontal=False); rt = c.get("row_titles") or []
        rs = [(a, b + HEAD, d, e - HEAD) if i < len(rt) and rt[i] else (a, b, d, e) for i, (a, b, d, e) in enumerate(rs)]      # row_titles: stacked sections, each row under its own header
        out.append(((cx, cy, cw, ch), hh, rs, hw))
    return out


def _nslots(spec): return sum(len(c["rows"]) for c in spec.get("cols") or []) + bool(spec.get("band")) if spec["layout"] == "cols" else SLOTS[spec["layout"]]


def _slots(spec):
    s_ = slots(spec["layout"], spec.get("cols") if spec["layout"] == "cols" else spec.get("weights"), *_body(spec), spec.get("right_weights"))
    if _hasband(spec): (x, y, w, h), hh = _band(spec); s_ = [(x, y + hh, w, h - hh), *s_]      # band panel = first panel, full width above the columns
    return s_


def slots(layout, weights, x, y, w, h, wr=None):
    if layout == "1": return [(x, y, w, h)]
    if layout == "cols": return [s_ for _, _, ss, _ in _cols(weights, x, y, w, h) for s_ in ss]
    if layout in ("2col", "3col", "4col"): return _split(x, y, w, h, SLOTS[layout], weights)
    if layout == "T|B": return _split(x, y, w, h, 2, weights, horizontal=False)
    if layout in ("T|B3", "T2|B3"):                                                  # top row (1 or 2 slots), bottom row of 3
        r = _split(x, y, w, h, 2, weights, horizontal=False)
        return [*([r[0]] if layout == "T|B3" else _split(*r[0], 2, None)), *_split(*r[1], 3, wr)]
    if layout == "2x3":                                                              # 2 rows x 3 cols, reading order row by row
        cols = [_split(*c_, 2, None, horizontal=False) for c_ in _split(x, y, w, h, 3, weights)]
        return [cols[0][0], cols[1][0], cols[2][0], cols[0][1], cols[1][1], cols[2][1]]
    c = _split(x, y, w, h, 2, weights)
    if layout in ("L|R2", "L|R3"): return [c[0], *_split(*c[1], NRIGHT[layout], wr, horizontal=False)]
    if layout == "L2|R": return [*_split(*c[0], 2, None, horizontal=False), c[1]]
    cols = [_split(*r, 2, None, horizontal=False) for r in c]                      # 2x2, reading order
    return [cols[0][0], cols[1][0], cols[0][1], cols[1][1]]


def _full(spec):
    return (MX, BODY_TOP, CW, (BAR_Y - 0.1 if spec.get("takeaway") else 6.75) - BODY_TOP)


BAND_GAP = 0.25
def _hasband(spec): return spec["layout"] == "cols" and bool(spec.get("band"))


def _band(spec):
    """cols option "band" (user ruling 2026-11-12, archive grid ~23%): the first panel runs across the full width on top (exhibit band or KPI strip),
    the columns fill the rest. Returns (band rect incl. its header, header height)."""
    x, y, w, h = _full(spec); return (x, y, w, h * spec["band"]["h"]), (HEAD if spec["band"].get("title") else 0)


def _body(spec):      # area the columns / layout slots fill (below the band, if any)
    x, y, w, h = _full(spec)
    if not _hasband(spec): return x, y, w, h
    bh = h * spec["band"]["h"]; return x, y + bh + BAND_GAP, w, h - bh - BAND_GAP


def _lines(s, w, size=12):
    cpl = max(1, int(w / (size * CPE / 72) * WRAP))
    return max(1, math.ceil(len(s.replace("**", "").replace("==", "")) / cpl)), cpl


def _tw(s, size=12, bold=False):      # estimated one-line text width (in)
    return len(s.replace("**", "").replace("==", "")) * size * CPE * (1.04 if bold else 1) / 72      # bold 0.49 em: calibrated on rendered headers (fit at >= 0.495 em per character of room, spilled at <= 0.482)


def _text_h(items, w, size=12, spacing=6, indent=0.25):
    """Estimated height (in) of a bullet list."""
    return sum(_lines(t, w - indent, size)[0] * size * 1.2 / 72 + spacing / 72 for t in items)


def _bars(v):
    """Mini-bar cell {"bars": [...]} -> list of bars, else None."""
    return v["bars"] if isinstance(v, dict) and "bars" in v else None


def _pill(v):
    """Pill cell {"pill": text, "color": theme key or hex} -> the dict, else None."""
    return v if isinstance(v, dict) and "pill" in v else None


def _pill_fill(c, theme):
    """Pill colour: a theme key (primary, dark, accent, pale...) or a hex."""
    c = (c or "primary").lstrip("#")
    return c.upper() if re.fullmatch(r"[0-9A-Fa-f]{6}", c) else theme[c]


GREYS = {"grey": "F2F2F2", "grey_dark": "D9D9D9", "grey_mid": "A6A6A6"}      # neutral tokens for emphasis shapes; "pale"/"primary"/... come from the theme


def _tone(c, theme):
    """Emphasis fill: grey / grey_dark, a theme key (pale, primary, dark...) or a hex."""
    return GREYS.get(c) or _pill_fill(c, theme)


def _ci(v):
    """Icon cell {"icon": lucide name, "text": ..., "pos": "top" (default) | "left"} -> the dict, else None."""
    return v if isinstance(v, dict) and "icon" in v else None


def _sc(v):
    """Styled text cell {"text", "fill", "bold", "box"} -> the dict, else None."""
    return v if isinstance(v, dict) and "text" in v and "icon" not in v else None


def _ct(v):
    """Text of a cell for width/line estimates (a mini-bar cell holds no text; a pill cell is drawn over an empty cell)."""
    return "" if _bars(v) is not None else v["pill"] if _pill(v) else v["text"] if _ci(v) or _sc(v) else " ".join(v) if isinstance(v, list) else str(v)


def _rcells(r, n):
    """Table row -> list of n cells. A row may be a list, {"group": label} (band) or {"total": [cells]}."""
    if isinstance(r, dict): return [r["group"], *[""] * (n - 1)] if "group" in r else list(r["total"])
    return r


def _row_lines(row, widths, size=11):
    if isinstance(row, dict) and "group" in row: return 1      # merged across the full width
    row = _rcells(row, len(widths))
    return max(sum(_lines(s, wd - 0.16 - (0.12 if isinstance(v, list) else 0) - (ICON_W + 0.08 if _ci(v) and v.get('pos') == 'left' else 0), size)[0] for s in (v if isinstance(v, list) else [_ct(v)])) for v, wd in zip(row, widths))


def _col_widths(p, w):
    n = len(p["columns"]); cwt = p.get("col_weights")
    if cwt and len(cwt) == n: return [w * v / sum(cwt) for v in cwt]
    body = [r for r in p["rows"] if not (isinstance(r, dict) and "group" in r)]
    L = [max(len(_ct(_rcells(r, n)[j])) if _bars(_rcells(r, n)[j]) is None else 20 for r in [p["columns"], *body]) for j in range(n)]   # bar cells count as 20 characters
    L = [min(max(v, 13), 36 if any(isinstance(_rcells(r, n)[j], list) for r in body) else 28) for j, v in enumerate(L)]   # list (bulleted) cells may claim a wider column    # ponytail: min 13 (was 6): a bold 12pt header like "Nordeste" wrapped mid-word in a narrow column
    if p.get("first_col") == "heading": L[0] = max(L[0], 22)     # 15pt heading-font labels need room ("Amônia" wrapped at 13)
    return [w * v / sum(L) for v in L]


def _need(p, w, tsz=None):
    """Minimum element height (in) the panel kind needs at width w. # ponytail: estimates, not measured text."""
    k = p["kind"]
    if k == "chart": # a chart with a scale bar under it may be compact
        return 1.5 if p.get("scale") else 1.8
    if k == "bullets" and p.get("icons"): return sum(max(ICON_D, _lines(t, w - 0.55, p.get("bullet_size", 12))[0] * p.get("bullet_size", 12) * 1.2 / 72) + 0.1 for t in p["items"])
    if k == "bullets": return _text_h(p["items"], w, p.get("bullet_size", 12))     # measured at the size it is drawn
    if k == "flow": return _flow_need(p)
    if k == "cards" and p.get("text_size"):
        iw = w - _lead(p) - 0.15; f = p["text_size"] / 12
        return sum(0.2 + (_lines(i["title"], iw, p["text_size"])[0] + _lines(i["text"], iw, p["text_size"])[0]) * 0.2 * f for i in p["items"]) + 0.08 * (len(p["items"]) - 1)
    if k == "table":
        cw = _col_widths(p, w); sz = p.get("size") or tsz or 11
        return sum(max((0.09 if p.get("tight") else 0.14) + _row_lines(r, cw, sz) * sz * 1.2 / 72, _bar_h(r, cw, sz)) for r in [p["columns"], *p["rows"]])
    if k == "cards":
        iw = w - _lead(p) - 0.15
        return sum(0.2 + (_lines(i["title"], iw)[0] + _lines(i["text"], iw)[0]) * 0.2 for i in p["items"]) + 0.08 * (len(p["items"]) - 1)
    if k == "kpis": return 1.0 + (0.6 if any(i.get("icon") for i in p["items"]) and w / len(p["items"]) >= 1.9 else 0)
    if k == "map_br": return 1.8      # map and matrix scale to their box, like charts
    if k == "process": return 0.6 * len(p["steps"]) if w < 7 else 1.3
    return 1.8            # matrix


def _lead(p):
    """Left inset (in) of card text: icon disc 0.75, number badge 0.55, plain 0.25."""
    return 0.75 if any(i.get("icon") for i in p["items"]) else 0.55 if p.get("numbered") else 0.25


def _flow_need(p):
    """Height (in) of a flow panel: td = one box row per level + connector room; lr = one row per leaf."""
    par = {n["id"]: n.get("parent") for n in p["nodes"]}
    def depth(i): return 1 + depth(par[i]) if par.get(i) in par else 0
    if p.get("direction", "td") == "lr":
        leaves = [n["id"] for n in p["nodes"] if n["id"] not in set(par.values())]; return 0.6 * len(leaves)
    return 0.34 * (1 + max(depth(i) for i in par)) + 0.4 * max(depth(i) for i in par)      # dense originals: ~0.34in boxes, 0.4in connectors


def _icon_h(v, wd, size):
    """Minimum height (in) of an icon cell: icon above the text (default) or beside it ("pos": "left")."""
    left = v.get("pos") == "left"; th = _lines(v["text"], wd - 0.16 - (ICON_W + 0.08 if left else 0), size)[0] * size * 1.2 / 72
    return max(ICON_W + 0.1, th + 0.14) if left else ICON_W + 0.06 + th + 0.14


def _bar_h(row, cw=None, size=11):
    """Minimum height (in) of a table row holding mini bars (0.2 + 0.2 per stacked bar) or icon cells (needs the column widths cw)."""
    if isinstance(row, dict): return 0
    ih = [_icon_h(v, wd, size) for v, wd in zip(row, cw or []) if _ci(v)]
    return max([0.2 + 0.2 * len(b) for b in map(_bars, row) if b] + ih or [0])


def _extra_h(p, w):
    """(callout box height, footnotes height) in inches; 0 when absent."""
    co = p.get("callout"); ch = 0
    if co: ch = _lines(f"{co.get('lead', '')} {co['text']}", w - 0.3, 11)[0] * 0.19 + 0.16
    fn = sum(_lines(f, w, 9)[0] for f in p.get("footnotes") or []) * 0.15 + (0.04 if p.get("footnotes") else 0)
    return ch, fn + (PILL_H if p.get("pill_legend") else 0) + (SC_H if p.get("scale") else 0)


def _bul_h(p, w):
    return _text_h(p["bullets"], w, p.get("bullet_size", 12)) + 0.1 + (HEAD if p.get("legend_title") else 0) if p.get("bullets") else 0


def check(spec):
    """Cross-field rules for composite. Returns error strings."""
    try: th = load_theme(spec.get("theme")); tsz = th.get("table_size")
    except KeyError: th = {}; tsz = None      # unknown theme is reported by build.py
    e = []; P = spec["panels"]; ids = [p["id"] for p in P]; lay = spec["layout"]
    if len(set(ids)) != len(ids): e.append("panels: duplicate ids")
    if lay == "cols" and not spec.get("cols"): return ["layout 'cols' needs the 'cols' list"]
    if lay != "cols" and spec.get("cols"): e.append("'cols' only works with layout 'cols'")
    if lay != "cols" and spec.get("band"): e.append("'band' only works with layout 'cols' (its first panel runs across the top)")
    NS = _nslots(spec)
    if len(P) != NS: e.append(f"layout '{lay}' has {NS} slots but {len(P)} panels were given")
    wts = spec.get("weights")
    if wts and len(wts) != NWEIGHTS[lay]: e.append(f"weights: layout '{lay}' needs {NWEIGHTS[lay]} values, got {len(wts)}")
    rw = spec.get("right_weights")
    if rw and len(rw) != NRIGHT.get(lay, 0): e.append(f"right_weights: layout '{lay}' needs {NRIGHT.get(lay, 0)} values, got {len(rw)}")
    by = {p["id"]: p for p in P}
    if spec.get("title_size") and _lines(spec["headline"], CW, spec["title_size"])[0] * spec["title_size"] * 1.2 / 72 > TITLE_H + 0.05:      # big titles must fit the title zone (it does not grow)
        e.append(f"headline: about {_lines(spec['headline'], CW, spec['title_size'])[0]} lines at title_size {spec['title_size']} pt do not fit the title area; shorten the headline or lower title_size")
    if spec.get("frame"): e += [f"frame: unknown panel id '{i}' (panels: {ids})" for i in spec["frame"]["panels"] if i not in by]
    for i, p in enumerate(P):
        if p["kind"] == "table":
            e += [f"panels/{i} ({p['id']}): row {r} has {len(_rcells(row, len(p['columns'])))} cells but {len(p['columns'])} columns"
                  for r, row in enumerate(p["rows"]) if len(_rcells(row, len(p["columns"]))) != len(p["columns"])]
            e += [f"panels/{i} ({p['id']}): {k} has {len(p[k])} entries but {len(p['columns'])} columns" for k in ("head_fill", "col_fill", "align", "header_align", "col_weights")
                  if isinstance(p.get(k), list) and len(p[k]) != len(p["columns"])]
        pid = f"panel '{p['id']}'"
        if p["kind"] == "flow":
            ns = p["nodes"]; nid = [n["id"] for n in ns]; roots = [n for n in ns if not n.get("parent")]
            if len(set(nid)) != len(nid): e.append(f"{pid}: duplicate node ids")
            if len(roots) != 1: e.append(f"{pid}: nodes need exactly one root (no parent), found {len(roots)}")
            e += [f"{pid}: node '{n['id']}' has unknown parent '{n['parent']}'" for n in ns if n.get("parent") and n["parent"] not in nid]
            e += [f"{pid}: node '{n['id']}' has an op but no inputs (nothing names it as parent)" for n in ns if n.get("op") and n["id"] not in {m.get("parent") for m in ns}]
        cells = [c_ for r in p.get("rows", []) if not isinstance(r, dict) or "total" in r for c_ in _rcells(r, len(p["columns"]))]
        icons = [*(p.get("icons") or []), *(i["icon"] for i in p.get("items") or [] if isinstance(i, dict) and i.get("icon")), *(c_["icon"] for c_ in cells if _ci(c_))]
        e += [f"{pid}: unknown icon '{n}' (find_icons lists the Lucide names)" for n in icons if n and not (ICONS / f"{n}.svg").exists()]
        if p.get("icons") and len(p["icons"]) != len(p["items"]): e.append(f"{pid}: 'icons' has {len(p['icons'])} names but there are {len(p['items'])} items (use \"\" for none)")
        for q in [c_ for c_ in cells if _pill(c_)] + list((p.get("pill_legend") or {}).get("pills", [])):
            try: _pill_fill(q.get("color"), th)
            except KeyError: e.append(f"{pid}: pill colour '{q.get('color')}' is neither a theme key nor a 6-digit hex")
        for q in _side_items(p):
            nr = len(p["rows"]) if p["kind"] == "table" else len(p["items"]) if p["kind"] == "cards" else 0
            if q.get("rows") and (not nr or max(q["rows"]) >= nr or q["rows"][0] > q["rows"][1]): e.append(f"{pid}: side_label rows {q['rows']} need a table/cards panel and 0 <= first <= last < {nr}")
            if q.get("fill") not in (None, "none"):
                try: _pill_fill(q["fill"], th)
                except KeyError: e.append(f"{pid}: side_label fill '{q['fill']}' is neither a theme key nor a 6-digit hex")
        for q in (p.get("scale") or {}).get("colors", []):
            try: _pill_fill(q, th)
            except KeyError: e.append(f"{pid}: scale colour '{q}' is neither a theme key nor a 6-digit hex")
        if p["kind"] == "chart":
            c = p["chart"]; k = c["kind"]
            if k in ("scatter", "bubble"): continue
            if c.get("callouts") and k not in ("pie", "doughnut"): e.append(f"{pid}: 'callouts' only works on pie/doughnut")
            if c.get("phases"):
                st = [q["start"] for q in c["phases"]]
                if k not in ("column", "stacked", "stacked100", "line", "waterfall"): e.append(f"{pid}: 'phases' only works on column/stacked/stacked100/line/waterfall charts")
                elif st != sorted(set(st)) or st[-1] >= len(c["categories"]): e.append(f"{pid}: phases 'start' must increase and stay inside 0..{len(c['categories']) - 1}")
            if c.get("totals") and k != "stacked": e.append(f"panel '{p['id']}': 'totals' only works on kind 'stacked'")
            if c.get("total_first") and k != "waterfall": e.append(f"panel '{p['id']}': 'total_first' only works on kind 'waterfall'")
            if k == "waterfall" and len(c["series"]) != 1: e.append(f"panel '{p['id']}': waterfall needs exactly one series")
    for i, em in enumerate(spec.get("emphasis") or []):
        w = f"emphasis/{i} ({em['kind']})"; refs = em.get("panels") or [em[k] for k in ("panel", "from", "to") if k in em]
        bad = [r for r in refs if r not in by]
        if bad: e.append(f"{w}: unknown panel id {bad} (panels: {ids})"); continue
        try: _tone(em.get("fill", "primary"), th) if th else None
        except KeyError: e.append(f"{w}: fill '{em['fill']}' is none of grey, grey_dark, a theme key or a 6-digit hex")
        if em["kind"] == "backdrop" and em.get("y") and not 0 <= em["y"][0] < em["y"][1] <= 1: e.append(f"{w}: y must be [from, to] with 0 <= from < to <= 1")
        if em["kind"] == "pointer" and len(P) == NS and not (wts and len(wts) != NWEIGHTS[lay]):
            R_ = dict(zip(ids, _slots(spec))); (ax, ay, aw, ah), (bx, by_, bw, bh) = R_[em["from"]], R_[em["to"]]
            if (ax < bx + bw and bx < ax + aw) == (ay < by_ + bh and by_ < ay + ah): e.append(f"{w}: panels '{em['from']}' and '{em['to']}' are not side by side or stacked; point between neighbours only")
    e += [f"panel '{p['id']}': title_shape needs a panel title" for p in P if p.get("title_shape") and not p.get("title")]
    e += [f"panel '{p['id']}': kpi 'delta' only works on kpis panels" for p in P if p["kind"] != "kpis" and any(isinstance(k, dict) and k.get("delta") for k in p.get("items") or [])]
    n_el = lambda p: len(p.get("items") or p.get("bullets") or [])
    for i, l in enumerate(spec.get("links") or []):
        w = f"links/{i} ({l['kind']})"
        refs = [l["panel"]] if l["kind"] == "cagr" else [l[k] for k in ("from", "to", "panel") if k in l]
        refs = [r for ref in refs for r in (ref if isinstance(ref, list) else [ref])]
        bad = [r for r in refs if r not in by]
        if bad: e.append(f"{w}: unknown panel id {bad} (panels: {ids})"); continue
        if l["kind"] in ("highlight", "callout", "xref"):
            tgt = by[l["to"] if l["kind"] == "xref" else l["panel"]]
            if tgt["kind"] != "chart": e.append(f"{w}: panel '{tgt['id']}' is a {tgt['kind']}, not a chart"); continue
            c = tgt["chart"]
            if c["kind"] in ("scatter", "bubble"): e.append(f"{w}: not supported on {c['kind']} charts"); continue
            cn = len(c["categories"])
            if c["kind"] in ("pie", "doughnut", "line"): e.append(f"{w}: not supported on {c['kind']} charts")
            cats = l["categories"] if "categories" in l else [l["category"]] if "category" in l else [j for _, j in l["pairs"]]
            if any(j >= cn for j in cats): e.append(f"{w}: category index outside 0..{cn - 1}")
        if l["kind"] == "cagr":
            tgt = by[l["panel"]]
            if tgt["kind"] != "chart" or tgt["chart"]["kind"] not in ("column", "stacked", "waterfall"): e.append(f"{w}: panel '{tgt['id']}' must be a column/stacked/waterfall chart")
            elif max(l["from"], l["to"]) >= len(tgt["chart"]["categories"]): e.append(f"{w}: bar index outside 0..{len(tgt['chart']['categories']) - 1}")
        if l["kind"] == "xref":
            src = by[l["panel"]]
            if src["kind"] not in ("bullets", "cards", "chart", "table", "kpis", "map_br", "matrix", "process") or not n_el(src):
                e.append(f"{w}: panel '{src['id']}' has no items/bullets to number")
            elif src["kind"] == "cards" and not src.get("numbered"): e.append(f"{w}: cards panel '{src['id']}' must be numbered")
            elif any(k >= n_el(src) for k, _ in l["pairs"]): e.append(f"{w}: item index outside 0..{n_el(src) - 1} of panel '{src['id']}'")
        if l["kind"] == "connector":
            src, dst = by[l["from"]], by[l["to"]]; nrow = len(dst["rows"]) if dst["kind"] == "table" else len(dst["items"]) if dst["kind"] == "cards" else 0
            if src["kind"] != "chart" or src["chart"]["kind"] not in ("column", "stacked", "waterfall", "bar"): e.append(f"{w}: panel '{src['id']}' must be a column/stacked/waterfall/bar chart")
            elif l["category"] >= len(src["chart"]["categories"]): e.append(f"{w}: category index outside 0..{len(src['chart']['categories']) - 1}")
            if not nrow: e.append(f"{w}: panel '{dst['id']}' must be a table (or cards) panel")
            elif l["row"] >= nrow: e.append(f"{w}: row index outside 0..{nrow - 1}")
        if l["kind"] == "note":
            tgt = by[l["panel"]]; cats = [v for v in (l.get("at"), l.get("target")) if isinstance(v, int)]
            if cats and (tgt["kind"] != "chart" or tgt["chart"]["kind"] not in ("column", "stacked", "waterfall", "bar")): e.append(f"{w}: a category index needs a column/stacked/waterfall/bar chart panel, '{tgt['id']}' is not")
            elif cats and max(cats) >= len(tgt["chart"]["categories"]): e.append(f"{w}: category index outside 0..{len(tgt['chart']['categories']) - 1}")
        if l["kind"] == "bracket" and not isinstance(l["from"], list): e.append(f"{w}: 'from' must be a list of panel ids")
        if l["kind"] == "arrow" and len(P) == NS and not (wts and len(wts) != NWEIGHTS[lay]):
            R = dict(zip(ids, _slots(spec)))
            (ax, ay, aw, ah), (bx, by_, bw, bh) = R[l["from"]], R[l["to"]]
            xo = ax < bx + bw and bx < ax + aw; yo = ay < by_ + bh and by_ < ay + ah
            if xo == yo: e.append(f"{w}: panels '{l['from']}' and '{l['to']}' are not side by side or stacked (diagonal); link neighbours only")
    # text budget per panel
    if len(P) == NS and not (wts and len(wts) != NWEIGHTS[lay]):
        for p, r in zip(P, _slots(spec)):
            r = (r[0], r[1], r[2] - _side_w(p), r[3]); hh = HEAD if p.get("title") else 0; bh = _bul_h(p, r[2]); xc, xf = _extra_h(p, r[2])
            need = hh + _need(p, r[2], tsz) + bh + xc + xf
            if p["kind"] == "chart":      # the frame the renderer really gives the chart: slot minus header, bullets, callout, footnotes and the chart's own title/subtitle rows (_need alone ignores the gaps and those rows)
                fh = r[3] - hh - bh - (0.08 if bh else 0) - xc - (0.1 if xc else 0) - xf - (0.3 if p["chart"].get("title") else 0) - (0.24 if p["chart"].get("subtitle") else 0)
                mn = MIN_CHART - (0.6 if p.get("scale") else 0)      # a scale-bar panel may be more compact, like _need (an approved exemplar: ~1.05in)
                if fh < mn - 0.02 and need <= r[3] + 0.02:
                    e.append(f"panel '{p['id']}' (chart): the chart would get only {fh:.1f}in of height (minimum {mn:.1f}in, about 1in of plot): cut text under it, drop the callout/footnotes, or give the panel more weight")
            if need > r[3] + 0.02:
                over = need - r[3]; cpl = _lines("x", r[2])[1]
                what = "bullets" if p["kind"] == "bullets" else "content"
                e.append(f"panel '{p['id']}' ({p['kind']}): {what} needs ~{need:.1f}in but the slot is {r[3]:.1f}in high "
                         f"({over:.1f}in over, ~{int(over / 0.2 * cpl)} characters too long at 12pt): shorten the text, drop an item, or change layout/weights")
    return e


# ---------------------------------------------------------------- panel renderers (x, y, w, h = element area)
def _header(slide, x, y, w, title, theme, plain=False, serif=False, bg="FFFFFF", fill=None, force_plain=False):
    if theme.get("header_style") == "bar" and not (plain and force_plain):      # explicit title_plain under a bar column header: plain bold title, not a second bar
        f = fill or theme.get("header_fill")     # spec option header_fill: grey bar with dark label instead of brand colour
        pill(slide, x, y, w, 0.3, title, theme, size=12, align=theme.get("header_align", "l"), fill=f, color=("FFFFFF" if fill else theme.get("header_text", "1A1A1A")) if f else None); return
    if plain and serif and (theme.get("header_style") != "dotline" or force_plain):     # spec title_font "heading": regular heading-font title (serif originals, e.g. s01)
        text(slide, x, y, w, 0.28, title, size=12, bold=bool(theme.get("panel_title_bold")), color=theme["title_color"], font=theme["heading_font"], align="l", anchor="b")
        if theme.get("serif_title_rule"): hline(slide, x, y + 0.31, x + w, y + 0.31, "BFBFBF", 0.75)     # spec option: hairline under the serif title (s08)
        return
    if plain and not theme.get("header_ends") and (theme.get("header_style") != "dotline" or force_plain):       # left-hand chart titles: bold dark, no italic accent, no rule (original house style)
        text(slide, x, y, w, 0.28, title, size=12, bold=theme.get("chart_title_bold", True), color=theme.get("chart_title_color", theme["title_color"]), font=theme["body_font"], align="l", anchor="b")   # sans bold like the originals (s09, s10); dark title, not the red brand tint (one accent per slide)
        return
    if theme.get("header_style") == "italic_centre":    # bold italic grey centred title, no rule (LEK report originals)
        text(slide, x, y, w, 0.28, title, size=12, bold=True, italic=True, color="7F7F7F", font=theme["heading_font"], align="c", anchor="b"); return
    if theme.get("header_style") == "dotline":  # centred caps title on a primary hairline with a disc at each end (s05 original)
        lc = theme.get("header_line") or theme["primary"]       # theme token header_line: hairline/dot colour (navy_cyan: cyan)
        hline(slide, x, y + 0.14, x + w, y + 0.14, lc, 0.75)
        for dx in (x, x + w - 0.1): box(slide, dx, y + 0.09, 0.1, 0.1, fill=lc, shape=MSO_SHAPE.OVAL)
        tw = min(w - 0.4, 0.11 * len(title) + 0.3)
        box(slide, x + (w - tw) / 2, y, tw, 0.28, fill=bg)
        text(slide, x, y, w, 0.28, title.upper() if theme.get("header_caps", True) else title, size=12, bold=theme.get("header_bold", True), color=theme["title_color"], font=theme["heading_font"], align="c", anchor="m")
        return
    if theme.get("header_style") == "label":     # section style label (archive 36%): bold brand-colour text a size up, no rule
        text(slide, x, y, w, 0.3, title, size=14, bold=True, color=theme["title_color"], font=theme["heading_font"], align="l", anchor="b"); return
    if theme.get("header_style") == "centred_rule":     # section style centred_rule (archive 22%): centred bold title on a hairline, no discs
        hline(slide, x, y + 0.15, x + w, y + 0.15, theme.get("header_line") or theme["primary"], 0.75)
        tw = min(w, _tw(title, 12, True) + 0.3); box(slide, x + (w - tw) / 2, y, tw, 0.3, fill=bg)
        text(slide, x, y, w, 0.3, title, size=12, bold=True, color=theme["title_color"], font=theme["heading_font"], align="c", anchor="m"); return
    if theme.get("header_style") == "rule": force_plain = False      # section style rule: falls through to bold text on the grey hairline
    if theme.get("header_style") == "vbar":     # short brand-colour vertical bar at the left, no underline (archive originals)
        box(slide, x, y + 0.02, 0.06, 0.26, fill=theme["primary"])
        text(slide, x + 0.14, y, w - 0.14, 0.28, title, size=12, bold=True, color=theme["title_color"], font=theme["heading_font"],
             align="l", anchor="b", italic=theme.get("header_italic", False))
        return
    text(slide, x, y, w, 0.28, title, size=12, bold=True, color=theme["title_color"], font=theme["heading_font"],
         align="l", anchor="b", italic=theme.get("header_italic", False))
    if theme.get("header_ends") == "dot":       # accent hairline with a dot at each end (Team C originals)
        hline(slide, x, y + 0.31, x + w, y + 0.31, theme["accent"], 0.75)
        for dx in (x, x + w - 0.08): box(slide, dx, y + 0.27, 0.08, 0.08, fill=theme["accent"], shape=MSO_SHAPE.OVAL)
        return
    hline(slide, x, y + 0.31, x + w, y + 0.31, "BFBFBF", 0.75)     # neutral grey rule: no accent-coloured rule under every header

def _extra_gap(items, w, h, base, indent=0.25, cap=0.4):
    """Fill rule: extra spacing (in) per item so a list spreads over its slot; capped so it still reads as a list. # ponytail: text height is estimated"""
    if len(items) < 2 or not h: return 0
    return max(0, min(cap, 0.85 * (h - _text_h(items, w, 12, base * 72, indent)) / len(items)))


def _numbered(slide, x, y, w, items, ks, theme, h=0):
    """Bullet list as separate rows so xref badges (item k -> number k+1) can sit exactly at their item."""
    xg = _extra_gap(items, w, h, 0.1, 0.4)
    for k, it in enumerate(items):
        hgt = _lines(it, w - 0.4)[0] * 0.2
        if k in ks: number_badge(slide, x, y - 0.03, k + 1, theme)
        else: text(slide, x + 0.06, y, 0.2, 0.2, "•", size=12, color="1A1A1A", font=theme["body_font"])
        text(slide, x + 0.38, y, w - 0.38, hgt, it, size=12, font=theme["body_font"])
        y += hgt + 0.1 + xg


def _bul(slide, x, y, w, h, items, theme, ks=None, marker="•", fill=True, size=12):    # fill False (panel option bullet_fill): natural spacing, not spread over the slot
    if not fill: h = 0
    if ks: _numbered(slide, x, y, w, items, ks, theme, h)
    else:
        sp = theme.get("bullet_space", 6)
        bullets(slide, x, y, w, h, items, theme, size=size, spacing=sp + _extra_gap(items, w, h, sp / 72) * 72, marker=marker)


def _chart(slide, p, x, y, w, h, theme, lang, head, room=0):
    c = dict(p["chart"]); k = c["kind"]
    h = min(h, c.get("max_height_in", h))      # spec option: compact chart, not stretched to the panel
    if c.get("title"):
        text(slide, x, y, w, 0.3, c["title"], size=12, font=theme["heading_font"]); y += 0.3; h -= 0.3
    if c.get("subtitle"):
        text(slide, x, y, w, 0.22, c["subtitle"], size=10, italic=theme.get("subtitle_italic", True), color="7F7F7F", font=theme["body_font"])
        y += 0.24; h -= 0.24
    legend = c.get("legend", len(c.get("series") or []) > 1 and k != "waterfall" and not c.get("series_labels")); top = 0.04
    fs = theme.get("legend_size", theme.get("chart_font", 10))    # legend band in inches, not a share of the frame (a tall panel left ~1 in empty above the legend)
    rows = -(-sum(len(str(s["name"])) * fs * 0.55 / 72 + 0.3 for s in c.get("series") or []) // (0.9 * w)) if legend else 0   # ponytail: char-width estimate of legend rows
    lg = min(0.4, (0.22 + 0.22 * rows) / h) if legend else 0
    if legend and c.get("legend_pos") in ("top", "top_tight"): top += 0.10 if c["legend_pos"] == "top_tight" else lg; lg = 0   # spec legend_pos "top": legend above the plot
    if c.get("phases"): top += 0.3 / h       # room above the plot for the phase labels
    if k in ("pie", "doughnut") and c.get("callouts"):      # ring in the middle, names + values outside it (no legend)
        d = max(1.2, min(h - 0.3, w - 3.0)); c["legend"] = False; c["inner"] = ((1 - d / w) / 2, (1 - d / h) / 2, d / w, d / h)
    if k == "bar":       # label column sized to the longest category: PowerPoint cuts names that don't fit ("Mato…")
        lw = max(0.18, min(0.45, (max(len(str(s)) for s in c["categories"]) * c.get("cat_size", theme.get("chart_font", 10)) * 0.55 / 72 + 0.12) / w))
        c["inner"] = (lw, top, 0.96 - lw, 1 - top - 0.03 - lg)
    elif k not in ("pie", "doughnut", "scatter", "bubble"):      # scatter/bubble set their own plot area (axis titles need room)
        lx = 0.17 if c.get("series_labels") == "left" else 0.03        # series names need room left of the first stack
        c["inner"] = (lx, top, 0.97 - lx, 1 - top - min(0.13, 0.40 / h) - lg)
    c["head"] = head; c["lang"] = lang
    if k == "bar": c["head"] = max(head, 1 + 0.45 / (c["inner"][2] * w))     # room for the value label after the longest bar, in inches
    elif room: ph = c["inner"][3] * h; c["head"] = max(head, 1 / (1 - min(room / ph, 0.45)))     # room (in) above the tallest bar: a cagr arrow on a short chart hit the value label
    add_chart(slide, c, theme, x, y, w, h, font_size=theme.get("chart_font", 10))
    _waterfall_connectors(slide, c, x, y, w, h)
    if k == "stacked": _stack_notes(slide, c, x, y, w, h, lang, theme)
    if c.get("phases"): _phases(slide, c, x, y, w, h, theme)
    if k in ("pie", "doughnut") and c.get("callouts"): _pie_callouts(slide, c, x, y, w, h, lang, theme)
    return c, (x, y, w, h)


def _seg_mid(c, R, i, si):
    """y (in) of the middle of series si in stack i, or None for an empty stack."""
    t = tops(c)[i]
    if not t: return None
    vals = [s["values"][i] for s in c["series"]]; unit = (R[i]["base"] - R[i]["top"]) / t
    return R[i]["base"] - (sum(vals[:si]) + vals[si] / 2) * unit


def _spread(ys, gap, up=False):
    """Push label y positions apart so no two are closer than gap (down from the top, or up from the bottom with up=True)."""
    out = {}; prev = None; sg = -1 if up else 1
    for k, y in sorted(ys.items(), key=lambda kv: sg * kv[1]):
        if prev is not None and sg * (y - prev) < gap: y = prev + sg * gap
        out[k] = prev = y
    return out


def _stack_notes(slide, c, x, y, w, h, lang, theme):
    """series_labels 'left': series names left of the first stack with grey leaders; small_callouts: too-small segment values outside
    right of their stack with leaders (archive look). Native text boxes + connectors. # ponytail: 9pt label, fixed 0.2in min spacing."""
    R = category_rects(c, x, y, w, h); nf = c.get("number_format", "General"); n = len(R); LG = "A6A6A6"
    if c.get("series_labels") == "left":
        ys = {si: _seg_mid(c, R, 0, si) for si, s in enumerate(c["series"]) if s["values"][0] > 0}
        ys = {k: v for k, v in ys.items() if v is not None}; ly = _spread(ys, 0.2); tx1 = R[0]["bx0"] - 0.3
        for si, yy in ly.items():
            text(slide, x, yy - 0.1, tx1 - x, 0.2, c["series"][si]["name"], size=9, font=theme["body_font"], align="r", anchor="m")
            hline(slide, tx1 + 0.04, yy, R[0]["bx0"], ys[si], LG, 0.5)
    if c.get("small_callouts"):
        for i in range(n):
            segs = {si: v for si, ci, v in small_segments(c, c["inner"][3] * h) if ci == i and v > 0}
            ys = {si: _seg_mid(c, R, i, si) for si in segs}; ly = _spread(ys, 0.17, up=True)
            if ly and (d := y + c["inner"][1] * h - min(ly.values())) > 0: ly = {si: v + d for si, v in ly.items()}      # never above the plot: shift the whole group down, gaps kept
            for si, yy in ly.items():
                bx = R[i]["bx1"]; text(slide, bx + 0.1, yy - 0.09, 0.5, 0.18, _num(segs[si], nf, lang), size=9, font=theme["body_font"], anchor="m")
                hline(slide, bx, ys[si], bx + 0.09, yy, LG, 0.5)


def _phases(slide, c, x, y, w, h, theme):
    """Phase markers: dashed vertical divider at the start of each phase after the first, label centred above its span of categories."""
    R = category_rects(c, x, y, w, h); ph = c["phases"]
    for q, s in enumerate(ph):
        a = s["start"]; b = ph[q + 1]["start"] if q + 1 < len(ph) else len(R)
        if a > 0: hline(slide, R[a]["x0"], y + 0.3, R[a]["x0"], R[0]["base"], "7F7F7F", 0.75, dash=True)
        sw_ = R[b - 1]["x1"] - R[a]["x0"]      # long label over a short span: shrink to fit, never wrap
        text(slide, R[a]["x0"], y + 0.02, sw_, 0.28, s["label"], size=min(14, max(9, 14 * sw_ / (0.115 * len(s["label"])))), color=theme["text_primary"], font=theme["heading_font"], align="c", anchor="m")


def _pie_callouts(slide, c, x, y, w, h, lang, theme):
    """Doughnut/pie callouts: bold category name + value outside the ring, thin leader from the middle of each slice. Native text + lines.
    # ponytail: slice angles assume the first slice starts at 12 o'clock clockwise (the chart default); labels only pushed apart vertically."""
    vals = c["series"][0]["values"]; tot = sum(vals); pct = c.get("percent"); nf = "0%" if pct else c.get("number_format", "0.#")
    nf = "0.#" if nf == "General" else nf
    r = c["inner"][2] * w / 2; cx, cy = x + w / 2, y + h / 2; a = 0; side = {"L": {}, "R": {}}; lw = (w - 2 * r) / 2 - 0.45
    for i, v in enumerate(vals):
        t = 2 * math.pi * (a + v / 2) / tot; a += v
        side["L" if math.sin(t) < 0 else "R"][i] = (cx + r * math.sin(t), cy - r * math.cos(t))
    for sd, pts in side.items():
        ys = _spread({i: pt[1] for i, pt in pts.items()}, 0.5); sg = -1 if sd == "L" else 1; lx = cx + sg * (r + 0.35)
        for i, (ex, ey) in pts.items():
            ly = min(max(ys[i], y + 0.25), y + h - 0.25)
            text(slide, lx if sg > 0 else lx - lw, ly - 0.22, lw, 0.44, [f"**{c['categories'][i]}**", _num(vals[i] / tot if pct else vals[i], nf, lang)], size=11, font=theme["body_font"], align="l" if sg > 0 else "r", anchor="m")
            hline(slide, ex, ey, lx - sg * 0.03, ly, "A6A6A6", 0.75)


def _waterfall_connectors(slide, c, x, y, w, h):
    """Thin dashed grey level lines between the bars of a total_first waterfall (hand-made look; no-op otherwise)."""
    if c["kind"] != "waterfall" or not c.get("total_first"): return
    R = category_rects(c, x, y, w, h); v = c["series"][0]["values"]; T = v[0]
    base, top0 = R[0]["base"], R[0]["top"]; lvl = T
    for i in range(len(v) - 1):
        if i >= 1: lvl -= abs(v[i])                                # level left after the bar i hangs down
        yy = base - (base - top0) * lvl / T
        hline(slide, R[i]["bx1"], yy, R[i + 1]["bx0"], yy, "7F7F7F", 0.75, dash=True)


def _table_panel(slide, p, x, y, w, h, theme, geo=None):
    """Returns the real table height (the arrow link aims at it). Rows: list, {"group": label} (grey band) or {"total": [cells]}.
    Cells: text, {"bars": [{"value", "label", "series"}]} (mini horizontal bars, scaled per column max) or {"icon", "text", "pos"}.
    geo (dict, optional) receives geo["rows"] = [(top, bottom)] in inches per body row."""
    if p.get("w"): w = min(w, p["w"])      # panel option w (in): table narrower than its slot, left-aligned
    cols, rows = p["columns"], p["rows"]; n = len(rows) + 1; nc = len(cols); cw = _col_widths(p, w)
    ts = p.get("size") or theme.get("table_size")     # theme token / panel option "size": fixed body size, rows grow to fill the slot
    size = ts or 11
    tall = any(_bar_h(r, cw, size) for r in rows); cap = 1.1 if tall else p.get("row_max", theme.get("table_row_max", 0.45))
    pad = 0.07 if p.get("tight") else 0.12      # panel option tight: compact rows (body cell margins 0.01in instead of 0.03in)
    if ts: row_h = min(cap, max(ts * 1.2 / 72 + pad, h / n))   # ponytail: rows grow up to the cap; wrapped rows are not individually sized
    else: row_h = min(cap, max(0.22, h / n)); size = 10 if row_h >= 0.3 else 9
    if p.get("row_h"): row_h = p["row_h"]      # panel option row_h (in): fixed row height, spare space becomes the centred offset
    hdr = min(row_h, 0.45); rh = row_h if not tall else min(cap, max(row_h, (h - hdr) / (n - 1)))
    if tall:      # tall rows (mini bars): split the slot by estimated wrapped height per row, so bulleted cells that wrap do not push the last row past the panel
        need = [max(0.14 + _row_lines(r_, cw, size) * size * 1.2 / 72, _bar_h(r_, cw, size)) for r_ in rows]
        rhs = [min(cap, v * (h - hdr - 0.05 * n) / sum(need)) for v in need]
    else: rhs = [rh] * (n - 1)
    mv = 0.01 if p.get("tight") else 0.03     # ponytail: pills / cell boxes / chevrons sit on the nominal row heights; a row PowerPoint wraps taller shifts them (text estimates were tried and mis-sized rows: set row_h or widen the column)
    tops = [sum(rhs[:i]) for i in range(n)]      # offset of body row i+1 below the header
    off = max(0, min(0.5, (h - (hdr + sum(rhs)) - 0.05 * n) / 2))     # fill rule: spare space beyond the row cap centres the table in its slot
    y += off
    tbl = _table(slide, n, nc, x, y, w, rh, cw); tbl.rows[0].height = Inches(hdr)
    for i, v in enumerate(rhs, 1): tbl.rows[i].height = Inches(v)
    m = p.get("matrix")     # spec option (s10): centred figures, grey band on group rows
    fill_hdr = theme.get("table_header", "rule") == "fill"
    A = p.get("align") or ["c" if m and j else "l" for j in range(nc)]      # panel option align: per-column l/c/r
    hs = p.get("header_size") or size; hf = theme["heading_font"] if p.get("header_font") == "heading" else None      # panel options header_size (pt) / header_font heading (serif originals)
    G = (_tone(p["grid"], theme), 0.75) if p.get("grid") else None      # panel option grid: full cell grid in that colour
    HF = p.get("head_fill"); HF = HF if isinstance(HF, list) else [HF] * nc      # panel option head_fill: header cell fill, one colour or one per column (null = style default)
    CF = p.get("col_fill") or [None] * nc; band = _tone(p["bands"], theme) if p.get("bands") else None      # col_fill: body fill per column; bands: tint every 2nd body row
    for j, c in enumerate(cols):
        al = (p.get("header_align") or A)[j]      # panel option header_align: per-column header alignment (default = body alignment)
        if HF[j] and _tone(HF[j], theme).upper() == "FFFFFF" and not G: _cell(tbl.cell(0, j), c, theme, size=hs, font=hf, bold=True, color="1A1A1A", align=al, bottom=("1A1A1A", 1.0))     # white header, no grid: the rule look, else nothing marks the header off (was plain text on a fill theme)
        elif HF[j]: f_ = _tone(HF[j], theme); _cell(tbl.cell(0, j), c, theme, size=hs, font=hf, bold=not fill_hdr and theme.get("table_header") != "plain", fill=f_, color="FFFFFF" if _is_dark(f_) else "1A1A1A", align=al, bottom=None, grid=G)
        elif fill_hdr: _cell(tbl.cell(0, j), c, theme, size=hs, font=hf, bold=False, fill=theme["primary"], color=theme["on_primary"], align=al, bottom=None, grid=G)   # filled brand header, regular weight (user's reference)
        elif theme.get("table_header") == "plain": _cell(tbl.cell(0, j), c, theme, size=hs, font=hf, bold=False, color="1A1A1A", align=al, bottom=None, grid=G)   # plain header (archive originals): regular weight, no rule
        else: _cell(tbl.cell(0, j), c, theme, size=hs, font=hf, bold=True, color="1A1A1A", align=al, bottom=None if p.get("header_rule") is False else ("1A1A1A", 1.0), grid=G)      # rule header: bold dark text on a dark hairline
    bi = 0      # body-row counter for bands (group rows restart nothing)
    for i, r in enumerate(rows, 1):
        if isinstance(r, dict) and "group" in r:
            _cell(tbl.cell(i, 0), r["group"], theme, size=size, bold=True, fill=theme.get("group_fill", "F2F2F2"), color=theme.get("group_color", "1A1A1A"), align="l", bottom=None, grid=G)
            for j in range(1, nc):
                if G:
                    for s_ in "LRTB": _border(tbl.cell(i, j), s_, *G)      # borders before the fill (schema order)
                if theme.get("group_fill", "F2F2F2"): tbl.cell(i, j).fill.solid(); tbl.cell(i, j).fill.fore_color.rgb = rgb(theme.get("group_fill", "F2F2F2"))
            tbl.cell(i, 0).merge(tbl.cell(i, nc - 1)); continue
        tot = isinstance(r, dict); cells = _rcells(r, nc)
        grp = m and not tot and not any(cells[1:])
        rule = ("BFBFBF", 0.5) if p.get("rules") == "rows" and i < n - 1 else ("D9D9D9", 0.5) if theme.get("table_row_rules") else None   # option "rules": rows = light-grey rule between body rows
        for j, v in enumerate(cells):
            hd = j == 0 and p.get("first_col") == "heading" and not tot      # option "first_col": heading = row label in the heading font, 15pt regular
            sc = _sc(v) or {}; own = sc.get("fill") or CF[j]
            _cell(tbl.cell(i, j), v if isinstance(v, list) else "" if _pill(v) else _ct(v), theme, size=15 if hd else size, bold=tot or (hd and bool(p.get("first_col_bold"))) or bool(sc.get("bold")), color="1A1A1A",   # plain body rows: no zebra tint, no bold key column
                  fill=theme["pale"] if tot else "F2F2F2" if grp else _tone(own, theme) if own else band if bi % 2 else None, align=A[j],
                  bottom=rule, font=theme["heading_font"] if hd else None, mv=mv, grid=G)
            if _ci(v):      # room for the icon: above the text (top margin; text is middle-anchored) or left of it
                if v.get("pos") == "left": tbl.cell(i, j).margin_left = Inches(ICON_W + 0.16)
                else: tbl.cell(i, j).margin_top = Inches(ICON_W + 0.06)     # hairlines only with theme token table_row_rules (s08); s03 original has none
        bi += 1
    tot_w = sum(cw); cx = [x + w * sum(cw[:j]) / tot_w for j in range(nc)]
    if p.get("chevrons") is not None:       # option "chevrons": column index; light-grey chevron in every body row just left of that column
        k = p["chevrons"]   # ponytail: uses the nominal row height, rows that wrap taller drift slightly off-centre
        for i, r in enumerate(rows, 1):
            if not isinstance(r, dict): box(slide, cx[k] - 0.22, y + hdr + tops[i - 1] + rhs[i - 1] / 2 - 0.2, 0.17, 0.4, fill="BFBFBF", shape=MSO_SHAPE.CHEVRON)
    for j in range(nc):         # mini bars: native rectangles over the (empty) cells, scaled to the column max
        col = [(i, _bars(_rcells(r, nc)[j])) for i, r in enumerate(rows, 1) if not isinstance(r, dict) and _bars(_rcells(r, nc)[j])]
        if not col: continue
        mx = max([b["value"] for _, bs in col for b in bs] + [1e-9]); cwj = w * cw[j] / tot_w; room = cwj - 0.2 - 0.5   # ponytail: per-column scale, so 2023 and 2024 bars are not comparable
        for i, bs in col:
            top = y + hdr + tops[i - 1]; rh = rhs[i - 1]; k = len(bs); bh = min(0.17, (rh - 0.2) / k); gap = 0.05
            by = top + (rh - (k * bh + (k - 1) * gap)) / 2
            hline(slide, cx[j] + 0.1, by - 0.03, cx[j] + 0.1, by + k * bh + (k - 1) * gap + 0.03, "1A1A1A", 0.75)
            for q, b in enumerate(bs):
                bw = max(0.02, room * b["value"] / mx); yy = by + q * (bh + gap)
                box(slide, cx[j] + 0.1, yy, bw, bh, fill=theme["series"][b.get("series", 0) % len(theme["series"])])
                text(slide, cx[j] + 0.14 + bw, yy - 0.03, 0.5, bh + 0.06, b["label"], size=p.get("bar_label_size") or min(size, 10), font=theme["body_font"], anchor="m")
    for i, r in enumerate(rows, 1):         # pill cells: small rounded filled rectangle with the text, centred in the (empty) cell
        if isinstance(r, dict): continue
        for j, v in enumerate(_rcells(r, nc)):
            if not _pill(v): continue
            f = _pill_fill(v.get("color"), theme); ps = p.get("pill_size", 9); k_ = ps / 9; ph = 0.22 * k_      # table option pill_size (pt): chip scales with its text
            pw = min(w * cw[j] / tot_w - 0.08, (0.075 * len(v["pill"]) + 0.25) * k_)
            _pill_shape(slide, cx[j] + (w * cw[j] / tot_w - pw) / 2, y + hdr + tops[i - 1] + (rhs[i - 1] - ph) / 2, pw, v["pill"], f, theme, h=ph, size=ps)
    for i, r in enumerate(rows, 1):         # cell option box: dashed outline inset in the cell (highlights one figure)
        if isinstance(r, dict): continue
        for j, v in enumerate(r):
            if (_sc(v) or {}).get("box"): box(slide, cx[j] + 0.03, y + hdr + tops[i - 1] + 0.03, w * cw[j] / tot_w - 0.06, rhs[i - 1] - 0.06, line=_tone(v["box"], theme), line_w=1.25, dash=True)
    for i, r in enumerate(rows, 1):         # icon cells: Lucide icon at the top of the cell (above the text) or at its left, centred with the text group
        if isinstance(r, dict): continue
        for j, v in enumerate(_rcells(r, nc)):
            if not _ci(v): continue
            cwj = w * cw[j] / tot_w; top = y + hdr + tops[i - 1]; rh_ = rhs[i - 1]; left = v.get("pos") == "left"
            ix = cx[j] + (cwj / 2 if A[j] == "c" and not left else cwj - 0.08 - ICON_W / 2 if A[j] == "r" and not left else 0.08 + ICON_W / 2)
            if left: iy = top + rh_ / 2
            else: th = _lines(v["text"], cwj - 0.16, size)[0] * size * 1.2 / 72; iy = top + max(0.02, (rh_ - (ICON_W + 0.06 + th)) / 2) + ICON_W / 2
            _icon(slide, v["icon"], ix, iy, ICON_W, theme, p.get("icon_style", "disc"))
    if geo is not None: geo["rows"] = [(y + hdr + tops[k], y + hdr + tops[k] + rhs[k]) for k in range(n - 1)]
    return off + hdr + sum(rhs) + (0 if (ts or tall) and not p.get("row_pad") else 0.05 * n)     # rendered rows run taller than row_h (cell margins): reserve 0.05in each so what sits below clears the table


def _pill_shape(slide, x, y, w, label, fill, theme, h=0.22, size=9):
    b = box(slide, x, y, w, h, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE); b.adjustments[0] = 0.25
    set_text(b, label, theme, size=size, bold=True, color="1A1A1A" if not _is_dark(fill) else "FFFFFF"); tf = b.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0


def _legend(slide, items, x, y, w, theme, layout=None):
    """Small series legend, right-aligned at the top of the panel (table option "legend": [names]; legend_layout "stack": one entry per line)."""
    xx = x + w
    for q, nm in reversed(list(enumerate(items))):
        if layout == "stack": xx = x + w; y0 = y + 0.28 * q
        else: y0 = y
        tw = 0.075 * len(nm) + 0.1; xx -= tw
        text(slide, xx, y0, tw, 0.2, nm, size=10, font=theme["body_font"], align="r", anchor="m")
        xx -= 0.28; box(slide, xx, y0 + 0.02, 0.2, 0.16, fill=theme["series"][q % len(theme["series"])]); xx -= 0.12


def _icon(slide, name, cx, cy, d, theme, style="disc"):
    """Lucide icon centred at (cx, cy): a brand-colour disc with a white line icon (default) or the plain line icon in the brand colour. Picture."""
    if style == "line": return image(slide, name, cx - d / 2, cy - d / 2, d, d, theme)
    box(slide, cx - d / 2, cy - d / 2, d, d, fill=theme["primary"], shape=MSO_SHAPE.OVAL)
    return image(slide, name, cx - d * 0.3, cy - d * 0.3, d * 0.6, d * 0.6, {**theme, "text_primary": theme["on_primary"]})


def _icon_rows(slide, p, x, y, w, h, theme):
    """Bullets panel with `icons` (one Lucide name per item, "" = none): one row per item, icon at the left, text at its right."""
    items, ic = p["items"], p["icons"]; sz = p.get("bullet_size", 12); st = p.get("icon_style", "disc")
    hs = [max(ICON_D, _lines(t, w - 0.55, sz)[0] * sz * 1.2 / 72) for t in items]
    gap = max(0.1, min(0.4, (h - sum(hs)) / max(len(items) - 1, 1))) if p.get("bullet_fill", True) else 0.1
    for k, t in enumerate(items):
        if k < len(ic) and ic[k]: _icon(slide, ic[k], x + ICON_D / 2, y + hs[k] / 2, ICON_D, theme, st)
        text(slide, x + 0.55, y, w - 0.55, hs[k], t, size=sz, font=theme["body_font"], anchor="m", accent=theme.get("text_primary"))     # ==accent== in brand colour, as on plain bullets
        y += hs[k] + gap


def _cards(slide, p, x, y, w, h, theme, geo=None):
    items = p["items"]; n = len(items); ch = min((h - 0.08 * (n - 1)) / n, 1.5)
    gp = 0.08 + (min(0.25, (h - n * ch - 0.08 * (n - 1)) / (n - 1)) if n > 1 else 0)     # fill rule: spare height widens the gaps
    for i, it in enumerate(items):
        cy = y + i * (ch + gp)
        if geo is not None: geo.setdefault("rows", []).append((cy, cy + ch))
        box(slide, x, cy, w, ch, fill=p.get("card_fill") or theme["pale"], shape=rect_shape(theme))   # panel option card_fill: own card fill hex (s02 grey)
        box(slide, x, cy, 0.06, ch, fill=theme["primary"])
        tx = x + 0.2
        if it.get("icon"): d = min(0.5, ch - 0.16); _icon(slide, it["icon"], x + 0.2 + d / 2, cy + ch / 2, d, theme, p.get("icon_style", "disc")); tx = x + 0.2 + d + 0.15
        elif p.get("numbered"): number_badge(slide, x + 0.18, cy + ch / 2 - 0.14, i + 1, theme); tx = x + 0.55
        text(slide, tx, cy, x + w - tx - 0.12, ch, [f"**{it['title']}**", it["text"]], size=p.get("text_size", 12), font=theme["body_font"], anchor="m", accent=theme.get("text_primary"))     # ==accent== in brand colour


def _kpis(slide, p, x, y, w, h, theme):
    items = p["items"]; n = len(items); f = theme["body_font"]; ic = any(i.get("icon") for i in items); st = p.get("icon_style", "disc")
    if w / n >= 1.9:                                  # side by side; an icon disc sits above the figure
        tw = (w - 0.15 * (n - 1)) / n; th = min(h - (0.6 if ic else 0), 2.4); y += 0.6 if ic else 0
        for i, k in enumerate(items):
            tx = x + i * (tw + 0.15)
            if k.get("icon"): _icon(slide, k["icon"], tx + 0.25, y - 0.3, 0.5, theme, st)
            # no tinted card or accent bar: a plain brand-coloured figure with its label beneath (as in the original)
            # left-aligned, dark figure (not a centred red pair): one accent per slide, reads as a hand-placed stat
            text(slide, tx, y + 0.12, tw, th * 0.5, k["value"], size=max(16, min(26, int(tw * 72 / (0.6 * max(len(k["value"]), 1))))), bold=theme.get("kpi_bold", True), color=theme.get("kpi_color") or theme.get("title_color") or "1A1A1A", font=theme["heading_font"], align="l", anchor="m")
            text(slide, tx, y + th * 0.6, tw - 0.1, th * 0.38, k["label"], size=11, font=f, align="l")
            if k.get("delta"): sz = max(16, min(26, int(tw * 72 / (0.6 * max(len(k["value"]), 1))))); _delta(slide, k, tx + min(tw - 0.25, 0.68 * sz / 72 * len(k["value"]) + 0.15), y + 0.12 + th * 0.25, theme)
    else:                                             # stacked rows: value | label
        rh = min((h - 0.1 * (n - 1)) / n, 1.4)
        if theme.get("kpi_style") == "bracket":       # theme token: green label above a [bracketed] figure (lek_report)
            rh = min((h - 0.1 * (n - 1)) / n, theme.get("kpi_row_max", 1.1)); fh = rh - 0.32; c = theme["primary"]
            for i, k in enumerate(items):
                ry = y + i * (rh + 0.1); fy = ry + 0.32; bx0, bx1 = x + 0.15, x + w - 0.15
                text(slide, bx0, ry, w - 0.3, 0.3, k["label"], size=theme.get("kpi_label_size", 11), color=c, font=f, align="c", anchor="m")
                text(slide, bx0 + 0.1, fy, w - 0.5, fh, k["value"], size=theme.get("kpi_size") or max(16, min(24, int((w - 0.5) * 72 / (0.6 * max(len(k["value"]), 1))))), bold=theme.get("kpi_bold", True), color=c, font=theme["heading_font"], align="c", anchor="m")
                for bx, d in ((bx0, 0.08), (bx1, -0.08)):
                    hline(slide, bx, fy, bx, fy + fh, c, 1); hline(slide, bx, fy, bx + d, fy, c, 1); hline(slide, bx, fy + fh, bx + d, fy + fh, c, 1)
            return
        ox = 0.65 if ic else 0; vw = min(1.9, w * (0.36 if ic else 0.42))
        for i, k in enumerate(items):
            ry = y + i * (rh + 0.1)
            if k.get("icon"): _icon(slide, k["icon"], x + 0.4, ry + rh / 2, 0.5, theme, st)
            text(slide, x + 0.15 + ox, ry, vw, rh, k["value"], size=max(16, min(24, int(vw * 72 / (0.6 * max(len(k["value"]), 1))))), bold=theme.get("kpi_bold", True), color=theme.get("kpi_color") or theme["primary"], font=theme["heading_font"], anchor="m")
            text(slide, x + 0.15 + ox + vw + 0.1, ry, w - ox - vw - (0.25 if ic else 0.4), rh, k["label"], size=12, font=f, anchor="m")
            if k.get("delta"): _delta(slide, k, x + 0.15 + ox + vw - 0.2, ry + rh / 2, theme)      # stacked rows: markers share one column at the right edge of the figure column


def _flow(slide, p, x, y, w, h, theme):
    """Boxes joined by connectors: each node's `parent` is the node it feeds, so the root is the result (bottom / right) and an `op` on a
    node draws that operator circle where its inputs join. Reuses diagram_slides.draw_tree."""
    lr = p.get("direction", "td") == "lr"
    draw_tree(slide, p["nodes"], theme, x, y, w, h, "lr" if lr else "td", flip=True, nh=0.55 if not lr else None, gap=0.7, size=p.get("node_size", 11))


def _map(slide, p, x, y, w, h, theme, lang):
    nf = p.get("number_format", "0"); dec = len(nf.split(".")[1]) if "." in nf else 0
    t = min(w / 7, (h - 0.55) / 7); ox = x + (w - 7 * t) / 2 - t
    draw_tiles(slide, p["values"], theme, ox, y, t, set(p.get("highlight", [])), dec, lang)


def _process(slide, p, x, y, w, h, theme):
    st = p["steps"]; n = len(st); f = theme["body_font"]
    if w >= 7:                                        # chevrons across, description under each
        ov = 0.12; sw = (w + ov * (n - 1)) / n
        for i, s in enumerate(st):
            sx = x + i * (sw - ov)
            pill(slide, sx, y, sw, 0.6, s["title"], theme, size=12, shape=MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON)
            if s.get("text"): text(slide, sx + 0.15, y + 0.7, sw - 0.4, h - 0.7, s["text"], size=12, font=f)
        return
    rh = min(h / n, 1.5)
    for i, s in enumerate(st):
        ry = y + i * rh
        if i < n - 1: hline(slide, x + 0.2, ry + 0.4, x + 0.2, ry + rh, "BFBFBF", 1.5)
        number_badge(slide, x + 0.06, ry + 0.02, i + 1, theme, d=0.28)
        text(slide, x + 0.5, ry, w - 0.5, rh - 0.05, [f"**{s['title']}**", *([s["text"]] if s.get("text") else [])], size=12, font=f)


def _numeral_grid(slide, items, x, y, w, h, theme, col_major=False):
    """2x2 legend (s09/s10 originals): large grey numeral, brand bar, text split on ';' into short lines. Items: '**1** a; b; c'."""
    cw, ch = w / 2, h / 2
    for i, it in enumerate(items[:4]):
        m = re.match(r"\*\*(.+?)\*\*\s*(.*)", it); num, body = (m.group(1), m.group(2)) if m else (str(i + 1), it)
        cx, cy = (x + (i // 2) * cw, y + (i % 2) * ch) if col_major else (x + (i % 2) * cw, y + (i // 2) * ch)
        text(slide, cx, cy, 0.45, ch, num, size=theme.get("grid_numeral_size", 28), bold=True, color=theme.get("grid_numeral_color", "7F7F7F"), font=theme[theme.get("grid_numeral_font", "body_font")], align="c", anchor="m")
        box(slide, cx + 0.5, cy + 0.08, 0.05, ch - 0.16, fill=theme["primary"])
        text(slide, cx + 0.62, cy, cw - 0.7, ch, [("• " if theme.get("grid_bullets") else "") + t.strip() for t in body.split(";")[:3]], size=theme.get("legend_text_size") or (12 if ch > 0.5 else 10), color="1A1A1A", font=theme["body_font"], anchor="m")


def _matrix(slide, p, x, y, w, h, theme):
    draw_matrix(slide, p, theme, x + 0.55, y + 0.05, w - 0.65, h - 0.45, inline_labels=True)


def _side_items(p):
    """Panel option side_label: "TEXT" (+ side_fill) or [{text, rows?: [first, last], fill?, level?}] -> list of dicts."""
    sl = p.get("side_label")
    return [] if not sl else [{"text": sl, "fill": p.get("side_fill")}] if isinstance(sl, str) else sl


def _side_w(p):
    """Width (in) the side-label strips take left of the panel content."""
    it = _side_items(p)
    return (max(s.get("level", 0) for s in it) + 1) * (SIDE_W + 0.04) + 0.04 if it else 0


def _side_strips(slide, p, x, y, h, geo, theme):
    """Vertical (270 degree) label strips at the left edge of the panel: whole panel height, or (table / cards) from row `first` to `last`.
    Level 0 = brand fill, level 1 = pale fill, right of level 0. Native text boxes with vert270 text."""
    for s_ in _side_items(p):
        lv = s_.get("level", 0); fill = s_.get("fill") or (theme["primary"] if lv == 0 else theme["pale"])
        a, b = (geo["rows"][s_["rows"][0]][0], geo["rows"][s_["rows"][1]][1]) if s_.get("rows") else (y, y + h)
        bx = box(slide, x + lv * (SIDE_W + 0.04), a + (0.02 if s_.get("rows") else 0), SIDE_W, b - a - (0.04 if s_.get("rows") else 0), fill=fill if fill != "none" else None)
        set_text(bx, s_["text"], theme, size=11, bold=True, color="FFFFFF" if fill != "none" and _is_dark(fill) else "1A1A1A")
        bx.text_frame._txBody.find(qn("a:bodyPr")).set("vert", "vert270"); bx.name = "side_label"


def _scale(slide, s, x, y, w, theme):
    """Gradient scale bar (native gradient fill) with end labels and arrow markers under it. s: {colors (2-4, default green-yellow-red),
    left, right (end labels), markers [{at 0..1, label?}], frame (dashed brand box round it)}. Height SC_H."""
    f = theme["body_font"]; bx, bw = x + 0.12, w - 0.24; by = y + 0.06; bh = 0.2; ly = by + bh + 0.2
    if s.get("frame"): box(slide, x, y, w, SC_H - 0.05, line=theme["primary"], line_w=1.75, dash=True)
    bar = box(slide, bx, by, bw, bh, fill="FFFFFF"); cols = [_pill_fill(c, theme) for c in s.get("colors") or ["3DAE2B", "F5D90A", "D9302C"]]
    bar.fill.gradient(); bar.fill.gradient_angle = 0
    gl = bar._element.spPr.find(qn("a:gradFill")).find(qn("a:gsLst"))
    for g in list(gl): gl.remove(g)
    for k, c in enumerate(cols): etree.SubElement(etree.SubElement(gl, qn("a:gs"), pos=str(round(100000 * k / (len(cols) - 1)))), qn("a:srgbClr"), val=c)
    bar.name = "scale"
    if s.get("left"): text(slide, bx, ly, 1.6, 0.22, s["left"], size=10, font=f, align="l", anchor="m")
    if s.get("right"): text(slide, bx + bw - 1.6, ly, 1.6, 0.22, s["right"], size=10, font=f, align="r", anchor="m")
    for m in s.get("markers") or []:
        mx = bx + m["at"] * bw; _arrow_end(hline(slide, mx, ly - 0.02, mx, by + bh + 0.02, "1A1A1A", 1.5))
        if m.get("label"):
            al = "l" if m["at"] < 0.15 else "r" if m["at"] > 0.85 else "c"
            text(slide, mx if al == "l" else mx - 1.6 if al == "r" else mx - 0.8, ly, 1.6, 0.22, m["label"], size=10, font=f, align=al, anchor="m")


# ---------------------------------------------------------------- links
def _rect_union(rs):
    x0 = min(r[0] for r in rs); y0 = min(r[1] for r in rs)
    return (x0, y0, max(r[0] + r[2] for r in rs) - x0, max(r[1] + r[3] for r in rs) - y0)


def _chevron(slide, cx, cy, rot, theme):
    # brand-colour disc with a white chevron (the user's reference slide); rot: 0 right, 90 down, 180 left, 270 up
    d = box(slide, cx - 0.16, cy - 0.16, 0.32, 0.32, fill=theme["primary"], shape=MSO_SHAPE.OVAL)
    ch = box(slide, cx - 0.05, cy - 0.08, 0.11, 0.16, fill="FFFFFF", shape=MSO_SHAPE.CHEVRON)
    ch.rotation = rot; d.name = "arrow"
    return d


def _link_arrow(slide, l, R, E, theme):
    a, b = R[l["from"]], R[l["to"]]; ea, eb = E[l["from"]], E[l["to"]]
    if a[0] + a[2] <= b[0] + 0.01 or b[0] + b[2] <= a[0] + 0.01:           # side by side
        right = a[0] + a[2] <= b[0] + 0.01
        gx = (a[0] + a[2] + b[0]) / 2 if right else (b[0] + b[2] + a[0]) / 2
        cy = ea[1] + ea[3] / 2
        if l.get("anchor") == "centre": cy = (min(a[1], b[1]) + max(a[1] + a[3], b[1] + b[3])) / 2
        elif b[3] < a[3] - 0.1 or not eb[1] <= cy <= eb[1] + eb[3]: cy = eb[1] + eb[3] / 2     # target is one of several stacked slots: aim at it
        _chevron(slide, gx, cy, 0 if right else 180, theme)
    else:                                                                   # stacked
        down = a[1] + a[3] <= b[1] + 0.01
        gy = (a[1] + a[3] + b[1]) / 2 if down else (b[1] + b[3] + a[1]) / 2
        cx = ea[0] + ea[2] / 2
        if b[2] < a[2] - 0.1 or not eb[0] <= cx <= eb[0] + eb[2]: cx = eb[0] + eb[2] / 2
        _chevron(slide, cx, gy, 90 if down else 270, theme)


def _link_bracket(slide, l, R, theme):
    U = _rect_union([R[i] for i in l["from"]]); T = R[l["to"]]
    if T[0] >= U[0] + U[2] - 0.01:                                          # target to the right: ] then arrow
        bx = U[0] + U[2] + 0.02; y0 = U[1] + HEAD; y1 = U[1] + U[3]; ym = (y0 + y1) / 2
        br = box(slide, bx, y0, 0.1, y1 - y0, line=theme["primary"], line_w=1.5, shape=MSO_SHAPE.RIGHT_BRACKET)
        c = hline(slide, bx + 0.1, ym, T[0] - 0.02, ym, theme["primary"], 1.5)
        lx, ly = (bx + 0.1 + T[0]) / 2, ym
    else:                                                                   # target below: ⎵ then arrow down
        by = U[1] + U[3] + 0.0; cx = U[0] + U[2] / 2; ln = U[2] - 0.3
        br = box(slide, cx - 0.05, by + 0.05 - ln / 2 + 0.05, 0.1, ln, line=theme["primary"], line_w=1.5, shape=MSO_SHAPE.RIGHT_BRACKET)
        br.rotation = 90
        c = hline(slide, cx, by + 0.15, cx, T[1] - 0.02, theme["primary"], 1.5)
        lx, ly = cx, by + 0.15 + (T[1] - by - 0.15) / 2
    _arrow_end(c); br.name = "bracket"
    if l.get("label"):
        lw = min(1.2, 0.075 * len(l["label"]) + 0.15)
        b = box(slide, lx - lw / 2, ly - 0.12, lw, 0.24, fill="FFFFFF", line=theme["primary"], line_w=0.75, shape=rect_shape(theme))
        set_text(b, l["label"], theme, size=9, color=theme["text_primary"], bold=True)


def _cat_rects(CG, pid):
    c, (x, y, w, h) = CG[pid]
    return c, (x, y, w, h), category_rects(c, x, y, w, h)


def _link_highlight(slide, l, CG, theme):
    c, (x, y, w, h), rs = _cat_rects(CG, l["panel"]); sel = [rs[i] for i in l["categories"]]
    lab = 0.30 if l.get("label") else 0
    if c["kind"] == "bar":
        x0, x1 = x + 0.02, min(max(r["end"] for r in sel) + 0.7, x + w - 0.02)
        y0, y1 = min(r["y0"] for r in sel) + 0.01, max(r["y1"] for r in sel) - 0.01
    else:
        x0, x1 = min(r["x0"] for r in sel) + 0.02, max(r["x1"] for r in sel) - 0.02
        y0 = max(min(r["top"] for r in sel) - 0.32, y + 0.02 + lab); y1 = min(sel[0]["base"] + 0.3, y + h - 0.02)
    b = box(slide, x0, y0, x1 - x0, y1 - y0, line=theme["primary"], line_w=1.75, dash=True, shape=rect_shape(theme))   # dashed brand box, as in the user's reference
    if theme.get("corners") == "rounded": b.adjustments[0] = 0.06
    b.name = f"highlight:{l['panel']}"
    if l.get("label"):
        text(slide, x0, y0 - lab, x1 - x0 + 0.6, 0.22, l["label"], size=10, bold=True, color=theme["text_primary"], font=theme["body_font"], anchor="b")


def _link_callout(slide, l, CG, theme):
    c, (x, y, w, h), rs = _cat_rects(CG, l["panel"]); r = rs[l["category"]]; f = theme["body_font"]
    if c["kind"] == "bar":
        tx = min(r["end"] + 0.75, x + w - 1.7); ty = (r["y0"] + r["y1"]) / 2 - 0.2
        text(slide, tx, ty, 1.7, 0.4, l["text"], size=10, italic=True, color="404040", font=f, anchor="m")
        hline(slide, r["end"] + 0.55 if tx > r["end"] + 0.6 else r["end"] + 0.1, ty + 0.2, tx - 0.04, ty + 0.2, theme["primary"], 0.75)
        return
    cx = (r["bx0"] + r["bx1"]) / 2; tx = min(cx + 0.3, x + w - 1.7); ty = max(r["top"] - 0.85, y + 0.02)
    text(slide, tx, ty, 1.7, 0.45, l["text"], size=10, italic=True, color="404040", font=f, anchor="b")
    hline(slide, tx + 0.02, ty + 0.5, cx, r["top"] - 0.27, theme["primary"], 0.75)


def _link_cagr(slide, l, CG, theme):
    """CAGR arrow: up from bar i, across, down onto bar j (arrow head), label in a small rounded box mid-way."""
    c, (x, y, w, h), rs = _cat_rects(CG, l["panel"]); i, j = l["from"], l["to"]; ri, rj = rs[i], rs[j]
    if l.get("style") == "diagonal":      # archive original: one slim brand arrow bar-top to bar-top, plain bold label above its midpoint
        xa, xb = (ri["bx0"] + ri["bx1"]) / 2, (rj["bx0"] + rj["bx1"]) / 2
        _arrow_end(hline(slide, xa, max(ri["top"] - 0.45, y + 0.05), xb, max(rj["top"] - 0.45, y + 0.05), theme["primary"], 1.25))   # above the value labels (0.3 ran through "771,8")
        if l.get("label"): text(slide, (xa + xb) / 2 - 0.8, (ri["top"] + rj["top"]) / 2 - 0.85, 1.6, 0.25, l["label"], size=10, bold=True, color=theme["primary"], font=theme["body_font"], align="c", anchor="b")
        return
    xi, xj = (ri["bx0"] + ri["bx1"]) / 2, (rj["bx0"] + rj["bx1"]) / 2
    si, sj = ri["top"] - 0.27, rj["top"] - 0.27           # clear of the value labels above the bars
    yh = max(min(si, sj) - 0.14, y + 0.12); col = "404040"       # ponytail: ignores bars between i and j that may be taller
    hline(slide, xi, si, xi, yh, col, 0.75); hline(slide, xi, yh, xj, yh, col, 0.75)
    _arrow_end(hline(slide, xj, yh, xj, sj, col, 0.75))
    if l.get("label"):
        lw = 0.085 * len(l["label"]) + 0.35; mx = (xi + xj) / 2
        b = box(slide, mx - lw / 2, yh - 0.11, lw, 0.22, fill="FFFFFF", line=col, line_w=0.75, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
        b.adjustments[0] = 0.5; set_text(b, l["label"], theme, size=9, color="1A1A1A", bold=True)


def _bar_mid(c, r, i):
    """(x where a line leaves bar i, y of its middle) for column-like and bar charts; waterfall bars hang between their two levels."""
    if c["kind"] == "bar": return r["end"] + 0.03, (r["y0"] + r["y1"]) / 2
    yb = r["base"]; tp = tops(c)[i]
    if c["kind"] == "waterfall" and tp: yb = r["base"] - (r["base"] - r["top"]) * waterfall_parts(_parts_values(c), False if c.get("total_first") else c.get("total_last", True))[0][i] / tp
    return r["bx1"] + 0.03, (r["top"] + yb) / 2


def _link_connector(slide, l, CG, TG, R, theme):
    """Elbow arrow from the middle of chart bar `category` (dot at the bar) to table row (or cards item) `row`, arriving at the table panel's left edge.
    `via` (0..1, default 0.5) = where the vertical leg sits between the two. Native elbow connector."""
    c, (x, y, w, h), rs = _cat_rects(CG, l["from"]); x0, y0 = _bar_mid(c, rs[l["category"]], l["category"])
    ra, rb = TG[l["to"]]["rows"][l["row"]]; tx, ty = R[l["to"]][0] - 0.02, (ra + rb) / 2
    cn = slide.shapes.add_connector(MSO_CONNECTOR.ELBOW, Inches(x0), Inches(y0), Inches(tx), Inches(ty))
    cn.line.color.rgb = rgb(theme["primary"]); cn.line.width = Pt(1.25); cn.name = f"connector:{l['from']}:{l['category']}"
    sp = cn._element.spPr; etree.SubElement(sp.find(qn("a:prstGeom")).find(qn("a:avLst")), qn("a:gd"), name="adj1", fmla=f"val {round(l.get('via', 0.5) * 100000)}")
    sp.append(etree.Element(qn("a:effectLst"))); _arrow_end(cn)
    box(slide, x0 - 0.04, y0 - 0.04, 0.08, 0.08, fill=theme["primary"], shape=MSO_SHAPE.OVAL)


def _link_note(slide, l, E, CG, theme):
    """Small free-floating dotted-outline box with text: in a corner of the panel (`at` top-left/top-right/bottom-left/bottom-right, default top-right)
    or, with `at` = a chart category index, above that bar. A thin arrow leads to the bar when `at` is an index or `target` (category) is given."""
    x, y, w, h = E[l["panel"]]; t = l["text"]; at = l.get("at", "top-right"); tgt = at if isinstance(at, int) else l.get("target")
    sz = l.get("size", 9); bw = l.get("w") or min(2.2 * sz / 9, 0.07 * sz / 9 * len(t.replace("**", "")) + 0.3); bh = _lines(t, bw - 0.16, sz)[0] * 0.0167 * sz + 0.12
    if tgt is not None: c, _, rs = _cat_rects(CG, l["panel"]); r = rs[tgt]; cx = (r["bx0"] + r["bx1"]) / 2 if "bx0" in r else r["end"]
    if isinstance(at, int):
        px = min(max(cx - bw / 2, x), x + w - bw); py = max(r["top"] - 0.55 - bh, y + 0.02) if "top" in r else (r["y0"] + r["y1"]) / 2 - bh / 2
        if "top" not in r: px = min(r["end"] + 0.6, x + w - bw)
    else:
        px = x + w - bw - 0.04 if at.endswith("right") else x + 0.04; py = y + 0.02 if at.startswith("top") else y + h - bh - 0.02
    b = box(slide, px, py, bw, bh, fill="FFFFFF", line="404040", line_w=1.0); b.line.dash_style = MSO_LINE.ROUND_DOT; b.name = f"note:{l['panel']}"
    set_text(b, t, theme, size=sz, color="1A1A1A", bold=False)
    if tgt is not None:
        if "top" in r: _arrow_end(hline(slide, px + bw / 2, py + bh, cx, r["top"] - 0.32, "404040", 0.75))
        elif isinstance(at, int): _arrow_end(hline(slide, px, py + bh / 2, r["end"] + 0.4, (r["y0"] + r["y1"]) / 2, "404040", 0.75))
        else:      # corner box, bar chart: from the box edge facing the bar to the bar's near edge, just inside its end
            up = py + bh <= r["y0"]; _arrow_end(hline(slide, px + bw / 2, py + bh if up else py, min(r["end"] - 0.15, px + bw), r["y0"] if up else r["y1"], "404040", 0.75))


def _xref_chart_side(slide, l, CG, theme):
    c, (x, y, w, h), rs = _cat_rects(CG, l["to"])
    for k, j in l["pairs"]:
        r = rs[j]
        if c["kind"] == "bar": number_badge(slide, min(r["end"] + 0.6, x + w - 0.3), (r["y0"] + r["y1"]) / 2 - 0.14, k + 1, theme)
        else: number_badge(slide, (r["bx0"] + r["bx1"]) / 2 - 0.14, max(r["top"] - 0.55, y + 0.01), k + 1, theme)


# ---------------------------------------------------------------- the archetype
def _backdrop(slide, em, R, theme):
    """Emphasis 'backdrop': grey/pale box behind one or more panels (optionally only the vertical band y=[from, to] of their union), under all content."""
    bx, by, bw, bh = _rect_union([R[i] for i in em["panels"]]); y0, y1 = em.get("y", [0, 1]); ln = em.get("outline", "none")
    b = box(slide, bx - 0.1, by + y0 * bh - 0.05, bw + 0.2, (y1 - y0) * bh + 0.1, fill=_tone(em.get("fill", "grey"), theme), line=None if ln == "none" else "A6A6A6", line_w=0.75, dash=ln == "dashed")
    b.name = "backdrop"


def _pointer(slide, em, R, theme):
    """Emphasis 'pointer': small triangle (or block arrow) centred in the gutter between two neighbouring slots, pointing from -> to."""
    (ax, ay, aw, ah), (bx, by, bw, bh) = R[em["from"]], R[em["to"]]; blk = em.get("shape") == "block"
    if ax < bx + bw and bx < ax + aw:       # stacked: down or up
        cx = (max(ax, bx) + min(ax + aw, bx + bw)) / 2; down = ay < by; cy = (ay + ah + by) / 2 if down else (by + bh + ay) / 2; rot = (90 if down else 270) if blk else (180 if down else 0)
    else:                                   # side by side: right or left
        cy = (max(ay, by) + min(ay + ah, by + bh)) / 2; right = ax < bx; cx = (ax + aw + bx) / 2 if right else (bx + bw + ax) / 2; rot = (0 if right else 180) if blk else (90 if right else 270)
    w, h = (0.3, 0.26) if blk else (0.3, 0.22)
    s = box(slide, cx - w / 2, cy - h / 2, w, h, fill=_tone(em.get("fill", "grey_mid"), theme), shape=MSO_SHAPE.RIGHT_ARROW if blk else MSO_SHAPE.ISOSCELES_TRIANGLE)
    s.rotation = rot; s.name = "pointer"


def _accent_bar(slide, em, R, theme, top=0):
    """Emphasis 'accent_bar': thin brand bar in the gutter left of a panel's slot, from under its title (top) to the slot bottom."""
    x, y, w, h = R[em["panel"]]; box(slide, x - 0.11, y + top, 0.05, h - top, fill=_tone(em.get("fill", "primary"), theme)).name = "accent_bar"


def _delta(slide, k, x, cy, theme):
    """KPI item option delta 'up'/'down': small filled triangle right of the figure (x = end of the estimated text)."""
    s = box(slide, x, cy - 0.09, 0.2, 0.17, fill=_tone(k.get("delta_color", "4D4D4D"), theme), shape=MSO_SHAPE.ISOSCELES_TRIANGLE)
    s.name = "delta"
    if k["delta"] == "down": s.rotation = 180


def composite(slide, spec, theme, lang):
    theme = {**theme, **{k: spec[k] for k in ("header_style", "header_italic", "header_caps", "header_bold", "header_fill", "header_text", "title_bold", "chart_font", "source_italic", "corners", "waterfall_label_style", "serif_title_rule", "subtitle_italic", "title_rule", "panel_title_bold", "page_number_font", "page_number_size", "page_number_bold", "source_font", "table_header", "group_fill", "group_color", "title_size", "tag_style") if k in spec}}     # per-slide look (s05: dotline, upright, regular title)
    title_and_footer(slide, spec, theme, lang)
    P = spec["panels"]; links = spec.get("links") or []
    raw = _slots(spec)      # raw slot rects: dividers and arrows sit on these
    rects = [(r[0] + p.get("x_inset", 0), r[1], r[2] - p.get("x_inset", 0), r[3]) for p, r in zip(P, raw)]     # panel option x_inset (in): content starts right of the slot edge (s03 right column)
    R = {p["id"]: r for p, r in zip(P, rects)}
    E = {}; CG = {}; TG = {}
    ks = {}; head = {}; room = {}                             # head: value-axis headroom per chart panel (room for boxes / badges / notes)
    def _bkr(p):    # compact chart (max_height_in): backing stops just under the chart, not at the slot bottom
        x, y, w, h = R[p["id"]]; m = p["kind"] == "chart" and p["chart"].get("max_height_in")
        return (x, y, w, min(h, HEAD + (0.24 if p["chart"].get("subtitle") else 0) + m)) if m else (x, y, w, h)
    # grey backgrounds, drawn first (under everything): "backing" (legacy flag, all flagged panels share one panel with the theme's backing line),
    # frame {"panels": [ids], "style"} (one panel round a group of slots) and panel "grey" (own panel; theme token "panels": "grey" = default for all)
    fr = spec.get("frame"); framed = set(fr["panels"]) if fr else set(); bg = {}; groups = []
    bk = [p for p in P if p.get("backing")]
    if bk: groups.append(([_bkr(p) for p in bk], theme.get("backing_fill", "F6F6F6"), theme.get("backing_line"), bool(theme.get("backing_line")), [p["id"] for p in bk]))
    if fr:
        st = fr.get("style", "dashed")
        groups.append(([R[i] for i in fr["panels"]], "F2F2F2", None if st == "none" else "A6A6A6", st == "dashed", list(fr["panels"])))
    fo = bool(fr and fr.get("title_outside"))      # frame option: panel titles stay above the frame
    for p in P:
        if p.get("backing") or p["id"] in framed: continue
        if p.get("panel", theme.get("panels", "none")) == "grey": groups.append(([R[p["id"]]], "F2F2F2", None, False, [p["id"]]))
    tops = set()      # cols: first slot right under a column title with no intro; a grey box there must not climb into the header rule
    if spec["layout"] == "cols" and (spec.get("section_style") or theme.get("header_style")) != "bar":      # bar headers: the grey box tucks under the bar on purpose (one block)
        k_ = int(_hasband(spec))
        if k_ and spec["band"].get("title"): tops.add(P[0]["id"])
        for c_ in spec["cols"]:
            if c_.get("title") and not c_.get("intro") and k_ < len(P): tops.add(P[k_]["id"])
            k_ += len(c_["rows"])
    for rs, fill, line, dash, ids in groups:
        bx, by, bw, bhh = _rect_union(rs); t0 = 0.32 + 0.1 if fo and ids == list(fr["panels"]) else 0.1 if tops & set(ids) else 0     # t0: frame top moves below the title (0.28 + gap) / below a cols header
        box(slide, bx - 0.12, by - 0.1 + t0, bw + 0.24, bhh + 0.2 - t0, fill=fill, line=line, line_w=0.75, dash=dash)     # bleeds 0.12in past the content, as in the archive
        bg.update({i: "FFFFFF" if t0 else fill for i in ids})      # title_outside: the header sits on white
    for em in spec.get("emphasis") or []:      # spec "emphasis" (opt-in): grey backdrops go under everything
        if em["kind"] == "backdrop":
            _backdrop(slide, em, R, theme)
            if em.get("y", [0])[0] == 0: bg.update({i: _tone(em.get("fill", "grey"), theme) for i in em["panels"]})
    if spec["layout"] == "cols":      # column headers (title on the header style, intro text under it) over the column's rows; the band's header first
        hd = list(zip(spec["cols"], _cols(spec["cols"], *_body(spec))))
        if _hasband(spec): (bx_, by_, bw_, bh_), _ = _band(spec); hd.insert(0, (spec["band"], ((bx_, by_, bw_, bh_), 0, None, bw_)))
        for c, ((cx, cy, cw, ch), hh, _, hw) in hd:
            if not hw: continue
            cw = hw
            bx = 0.36 if c.get("title") and c.get("title_badge") is not None else 0      # column option title_badge: numbered circle before the column title
            if bx: number_badge(slide, cx, cy + 0.01, c["title_badge"], theme)
            if c.get("title"): _header(slide, cx + bx, cy, cw - bx, c["title"], {**theme, "header_style": spec.get("section_style") or theme.get("header_style")}, serif=c.get("title_font") == "heading", fill=c.get("header_fill"), force_plain=c.get("title_plain", False))
            if c.get("intro"): set_text(box(slide, cx, cy + (HEAD if c.get("title") else 0), cw, hh - (HEAD if c.get("title") else 0)), c["intro"], theme, size=c.get("intro_size", 11), color="1A1A1A", align="l", anchor="t")
        for c, (_r, _hh, rs, _hw) in zip(spec["cols"], _cols(spec["cols"], *_body(spec))):      # row_titles: a section header above each titled row
            for i, (rx, ry, rw, _rh) in enumerate(rs):
                t = (c.get("row_titles") or [None] * 99)[i] if i < len(c.get("row_titles") or []) else None
                if not t: continue
                b = (c.get("row_badges") or [None] * 99)[i] if i < len(c.get("row_badges") or []) else None
                if b is not None: number_badge(slide, rx, ry - HEAD + 0.01, b, theme)
                _header(slide, rx + (0.36 if b is not None else 0), ry - HEAD, rw - (0.36 if b is not None else 0), t, {**theme, "header_style": spec.get("section_style") or theme.get("header_style")})
    for l in links:
        if l["kind"] == "xref": ks.setdefault(l["panel"], set()).update(k for k, _ in l["pairs"]); head[l["to"]] = 1.32
        if l["kind"] == "callout": head[l["panel"]] = 1.32
        if l["kind"] == "cagr": head[l["panel"]] = max(head.get(l["panel"], 0), 1.28); room[l["panel"]] = 0.5 if l.get("style") != "diagonal" else 0     # bracket arrow + label box above the value labels (diagonal style keeps its own clearance)
        if l["kind"] == "highlight":
            head.setdefault(l["panel"], 1.22)      # room above the tallest bar for its value label + the box label (1.14 put the box edge through "154")
            # ponytail: highlight link also greys the other bars (charts.py rule), not just a box around them
            next(p for p in P if p["id"] == l["panel"])["chart"].setdefault("highlight", l["categories"])
    for p, (x, y, w, h) in zip(P, rects):
        if p.get("title") and p.get("title_badge") is not None:      # panel option title_badge: numbered circle left of the title (archive section numbers); the title shifts right
            number_badge(slide, x, y + 0.01, p["title_badge"], theme); x += 0.36; w -= 0.36
        if p.get("title") and p.get("title_shape"):      # panel option title_shape pentagon/chevron: arrow-shaped header banner (archive step headers)
            pill(slide, x, y, w, 0.3, p["title"], theme, size=12, align="l", fill=p.get("header_fill"), shape=MSO_SHAPE.PENTAGON if p["title_shape"] == "pentagon" else MSO_SHAPE.CHEVRON)
        elif p.get("title"): _header(slide, x, y, w, p["title"], theme, plain=(p["kind"] == "chart" or p.get("title_plain", False) or (p["kind"] == "table" and not theme.get("table_title_rule", True))), serif=p.get("title_font") == "heading" or theme.get("panel_title_font") == "heading", bg=bg.get(p["id"], "FFFFFF"), fill=p.get("header_fill"), force_plain=p.get("title_plain", False))
        if p.get("title") and p.get("title_badge") is not None: x -= 0.36; w += 0.36      # only the title moved for the badge; the content keeps the full slot
        x0s, sw = x, _side_w(p); x += sw; w -= sw      # side-label strips take their width left of the content (header stays full width)
        ey = y + (HEAD + (0.1 if fo and p["id"] in framed else 0) if p.get("title") else 0); bh = _bul_h(p, w); xc, xf = _extra_h(p, w)
        eh = h - (ey - y) - bh - (0.08 if bh else 0) - xc - (0.1 if xc else 0) - xf
        if p.get("subtitle"):   # panel option "subtitle"/"subtitle_note": bold heading-font title + grey note inside the panel, above tag/legend (s07 original)
            text(slide, x + 0.1, ey, w - 0.2, 0.28, p["subtitle"], size=13, bold=True, color=p.get("subtitle_color") or theme["title_color"], font=theme["body_font"] if p.get("subtitle_font") == "body" else theme["heading_font"], anchor="b")
            if p.get("subtitle_note"): text(slide, x + 0.1, ey + 0.28, w - 0.2, 0.22, p["subtitle_note"], size=10, color="7F7F7F", font=theme["body_font"])
            d = 0.58 if p.get("subtitle_note") else 0.36; ey += d; eh -= d
        if p.get("tag"):    # panel option "tag": small rounded light-grey outlined tag at the element's top-left (drawn over the first header cell)
            tg = box(slide, x + 0.02, ey + 0.04, 0.09 * len(p["tag"]) + 0.2, 0.22, line="BFBFBF", line_w=0.75, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
            tg.adjustments[0] = 0.3; set_text(tg, p["tag"], theme, size=8, color="BFBFBF", bold=False, font=theme["heading_font"])
        k = p["kind"]
        if bh and p.get("bullets_position") == "top" and k != "bullets" and p.get("legend") != "numeral_grid":    # panel option: lead-in bullets above the element
            _bul(slide, x, ey, w, bh, p["bullets"], theme, ks.get(p["id"]), "" if p.get("footnote") or theme.get("lead_in_plain") else "•", size=p.get("bullet_size", 12)); ey += bh + 0.08; bh = 0
        tn = _lines(p["table_note"], w, 9)[0] * 0.15 + 0.1 + p.get("note_gap", 0) if p.get("table_note") else 0; eh -= tn      # spec table_note: 9pt italic note under the table
        if isinstance(p.get("legend"), list): _legend(slide, p["legend"], x, ey, w, theme, p.get("legend_layout")); d = 0.28 * (len(p["legend"]) if p.get("legend_layout") == "stack" else 1); ey += d; eh -= d     # table option "legend": mini-bar series names
        if k == "chart":
            c, fr = _chart(slide, p, x, ey, w, eh, theme, lang, head.get(p["id"], 1.12), room.get(p["id"], 0)); CG[p["id"]] = (c, fr)
        elif k == "table":
            TG[p["id"]] = {}; eh = _table_panel(slide, p, x, ey, w, eh, theme, TG[p["id"]])
            if tn: text(slide, x, ey + eh + 0.2, w, 0.4, p["table_note"], size=9, italic=p.get("table_note_italic", True), color="595959", font=theme["body_font"]); eh += tn
        elif k == "flow": _flow(slide, p, x, ey, w, eh, theme)
        elif k == "bullets" and p.get("icons"): _icon_rows(slide, p, x, ey, w, eh, theme)
        elif k == "bullets": _bul(slide, x, ey, w, eh, p["items"], theme, ks.get(p["id"]), fill=p.get("bullet_fill", True), size=p.get("bullet_size", 12))
        elif k == "cards": TG[p["id"]] = {}; _cards(slide, p, x, ey, w, eh, theme, TG[p["id"]])
        elif k == "kpis": _kpis(slide, p, x, ey, w, eh, theme)
        elif k == "map_br": _map(slide, p, x, ey, w, eh, theme, lang)
        elif k == "process": _process(slide, p, x, ey, w, eh, theme)
        elif k == "matrix": _matrix(slide, p, x, ey, w, eh, theme)
        if bh and p.get("legend") == "numeral_grid":
            gy, gh = ey + eh + 0.08, bh
            if p.get("legend_title"): _header(slide, x, gy, w, p["legend_title"], theme, serif=True); gy += HEAD; gh -= HEAD   # heading above the grid (s10 'Descricao dos Scores')
            gh = min(gh, y + h - gy)      # grid never runs past the panel bottom (footer rule)
            _numeral_grid(slide, p["bullets"], x, gy, w, gh, theme, p.get("numeral_order") == "column")
        elif bh: _bul(slide, x, ey + eh + 0.08, w, bh, p["bullets"], theme, ks.get(p["id"]) if k != "bullets" else None, "" if p.get("footnote") else "•", size=p.get("bullet_size", 12))
        if xc or xf:       # callout box under the element (and its bullets), footnotes at the panel bottom
            cy = ey + eh + (0.08 + bh if bh else 0) + 0.1
            if xc:
                co = p["callout"]; ld = co.get("lead", ""); ct = (ld if "==" in ld else f"**{ld}**") + f" {co['text']}" if ld else co["text"]   # lead with ==accent== keeps its own markup
                if theme.get("callout_style") == "bold_centre": text(slide, x, cy, w, xc, ct.replace("**", ""), size=11, bold=True, color="1A1A1A", font=theme["body_font"], align="c", anchor="m")   # theme token (lek_report): bold centred text on the backdrop, no inner box
                else: set_text(box(slide, x, cy, w, xc, fill="FFFFFF" if p["id"] in bg else p.get("callout_fill", theme.get("callout_fill", "F2F2F2")), shape=rect_shape(theme)), ct, theme, size=11, color="1A1A1A", align="l")
            pl = PILL_H if p.get("pill_legend") else 0; sc = SC_H if p.get("scale") else 0
            if sc: _scale(slide, p["scale"], x, y + h - xf, w, theme)      # gradient scale bar: top of the bottom block, above pills and footnotes
            if pl:       # legend row of pills ("Input source: [Public data] [Benchmark]"), above the footnotes
                lg = p["pill_legend"]; px = x; py = y + h - xf + sc + 0.05
                if lg.get("label"): lw = 0.085 * len(lg["label"]) + 0.1; text(slide, px, py, lw, 0.24, lg["label"], size=10, bold=True, font=theme["body_font"], anchor="m"); px += lw + 0.05
                nch = sum(len(q["pill"]) for q in lg["pills"]); cc, pad, gap = (0.075, 0.3, 0.1) if px - x + 0.075 * nch + (0.3 + 0.1) * len(lg["pills"]) <= w else (0.062, 0.2, 0.06)   # narrow panel: compact pills so the legend never runs off the panel
                for q in lg["pills"]: pw = cc * len(q["pill"]) + pad; _pill_shape(slide, px, py, pw, q["pill"], _pill_fill(q.get("color"), theme), theme, h=0.24); px += pw + gap
            if xf - pl - sc > 0: text(slide, x, y + h - xf + sc + pl, w, xf - pl - sc, p["footnotes"], size=9, color="7F7F7F", font=theme["body_font"], anchor="b")
        if sw: _side_strips(slide, p, x0s, y + (HEAD if p.get("title") else 0), h - (HEAD if p.get("title") else 0), TG.get(p["id"]), theme)
        E[p["id"]] = (x, ey, w, eh)
    # dividers are opt-in (spec "divider"): s09/s10 originals have one, other archive slides use the gutter alone
    if spec.get("divider") and spec["layout"] in ("2col", "L2|R", "L|R2", "L|R3", "3col", "4col", "cols"):
        for r_ in (raw[1:] if spec["layout"] in ("3col", "4col") else [c_[0] for c_ in _cols(spec["cols"], *_body(spec)) if c_[3]][1:] if spec["layout"] == "cols" else raw[-1:]):      # 3col: a line at both gutters
            dx = r_[0] - G / 2; hline(slide, dx, _body(spec)[1] if _hasband(spec) else BODY_TOP, dx, BAR_Y - 0.1 if spec.get("takeaway") else FOOTER_RULE_Y - 0.05, "A6A6A6", 1.0, dash=True)      # stop above a takeaway bar
        if _hasband(spec): x_, y_, w_, _h = _body(spec); hline(slide, x_, y_ - BAND_GAP / 2, x_ + w_, y_ - BAND_GAP / 2, "A6A6A6", 1.0, dash=True)      # band | columns
    if spec.get("dividers", theme.get("dividers")):      # horizontal dashed light-grey line between vertically stacked slots
        pr = {"L|R2": [(1, 2)], "L2|R": [(0, 1)], "T|B": [(0, 1)], "2x2": [(0, 2), (1, 3)],
              "L|R3": [(1, 2), (2, 3)], "2x3": [(0, 3), (1, 4), (2, 5)], "T|B3": [(0, 1)]}.get(spec["layout"], [])
        if spec["layout"] == "cols" and spec.get("dividers"):      # cols (opt-in per spec, not the theme token): between consecutive slots of each column (panels run column by column)
            k_ = int(_hasband(spec))
            for c_ in spec["cols"]: pr += [(k_ + i, k_ + i + 1) for i in range(len(c_["rows"]) - 1)]; k_ += len(c_["rows"])
        for a_, b_ in pr:
            ra, rb = raw[a_], raw[b_]; hy = (ra[1] + ra[3] + rb[1] - (HEAD if spec["layout"] == "cols" and rb[1] - (ra[1] + ra[3]) > HEAD else 0)) / 2
            hline(slide, ra[0], hy, ra[0] + ra[2], hy, "BFBFBF", 0.75, dash=True)
    for l in links:
        if l["kind"] == "arrow": _link_arrow(slide, l, {p["id"]: r for p, r in zip(P, raw)}, E, theme)   # arrows sit on the raw slot edges (x_inset moves content only)
        elif l["kind"] == "bracket": _link_bracket(slide, l, R, theme)
        elif l["kind"] == "highlight": _link_highlight(slide, l, CG, theme)
        elif l["kind"] == "callout": _link_callout(slide, l, CG, theme)
        elif l["kind"] == "xref": _xref_chart_side(slide, l, CG, theme)
        elif l["kind"] == "cagr": _link_cagr(slide, l, CG, theme)
        elif l["kind"] == "connector": _link_connector(slide, l, CG, TG, R, theme)
        elif l["kind"] == "note": _link_note(slide, l, E, CG, theme)
    for em in spec.get("emphasis") or []:
        if em["kind"] == "pointer": _pointer(slide, em, {p["id"]: r for p, r in zip(P, raw)}, theme)
        elif em["kind"] == "accent_bar": _accent_bar(slide, em, R, theme, HEAD if next(p for p in P if p["id"] == em["panel"]).get("title") else 0)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)
    WARNINGS.extend(density(slide, spec)); WARNINGS.extend(fit(spec, theme))


FONT_W = {"Trebuchet MS": 1.0, "Arial": 1.03, "Helvetica": 1.03, "Calibri": 0.93, "Segoe UI": 1.02, "Tahoma": 1.03, "Verdana": 1.18,
          "Georgia": 1.10, "Times New Roman": 0.95, "Cambria": 1.0, "Garamond": 0.9}      # ponytail: rough width relative to Trebuchet MS; unknown fonts = 1.0


def fit(spec, theme):
    """Text that will not fit where it is drawn (user ruling 2026-11-12: checked by the build, not left to instructions):
    a header longer than one line of its bar/column, a table header word wider than its column, chart category words wider than
    their bar slot. # ponytail: character-count estimates (CPE), not PowerPoint metrics."""
    w_ = []; P = spec["panels"]; hst = theme.get("header_style")
    fh, fb = FONT_W.get(theme.get("heading_font"), 1.0), FONT_W.get(theme.get("body_font"), 1.0)      # widths calibrated on Trebuchet MS renders
    if spec["layout"] == "cols":
        hd = list(zip(spec["cols"], _cols(spec["cols"], *_body(spec))))
        if _hasband(spec): hd.insert(0, (spec["band"], (None, 0, None, _full(spec)[2])))
        for c, (_r, hh, _, hw) in hd:
            if not (hw and c.get("title")): continue
            st = spec.get("section_style") or hst; sz = 14 if st == "label" else 12
            room = hw - (0.36 if c.get("title_badge") is not None else 0) - (0.2 if st == "bar" else 0.05)
            if _tw(c["title"], sz, True) * fh > room:
                w_.append(f"section header '{c['title']}' needs 2 lines but its column fits one (~{int(len(c['title']) * room / (_tw(c['title'], sz, True) * fh))} characters): shorten it")
    for c, (_r, _hh, rs, _hw) in (zip(spec["cols"], _cols(spec["cols"], *_body(spec))) if spec["layout"] == "cols" else []):
        for i, t in enumerate(c.get("row_titles") or []):
            st = spec.get("section_style") or hst; sz = 14 if st == "label" else 12; bd = (c.get("row_badges") or [None] * 99)[i] if i < len(c.get("row_badges") or []) else None
            if t and i < len(rs) and _tw(t, sz, True) * fh > rs[i][2] - (0.36 if bd is not None else 0) - (0.2 if st == "bar" else 0.05):
                w_.append(f"section header '{t}' needs 2 lines but its section fits one: shorten it")
    for p, r in zip(P, _slots(spec)):
        pw = r[2] - _side_w(p)
        if p.get("title") and _tw(p["title"], 12, True) * fb > (pw - (0.2 if hst == "bar" and not p.get("title_plain") else 0) - (0.36 if p.get("title_badge") is not None else 0)):
            w_.append(f"panel '{p['id']}': title '{p['title']}' needs 2 lines in a {pw:.1f}in panel: shorten it")
        if p["kind"] == "table":
            ws = _col_widths(p, p.get("w") or pw); hs = p.get("header_size") or p.get("size") or theme.get("table_size") or 10
            for c, cw in zip(p["columns"], ws):
                long = max(str(c).split() or [""], key=len)
                if _tw(long, hs, True) * fb > cw - 0.12:
                    w_.append(f"panel '{p['id']}': table header '{c}' breaks mid-word ('{long}' in a {cw:.2f}in column): shorter header, col_weights, or header_size")
        if p["kind"] == "chart" and p["chart"]["kind"] in ("column", "stacked", "stacked100", "waterfall"):
            ch = p["chart"]; n = len(ch["categories"]); sz = ch.get("cat_size") or spec.get("chart_font") or theme.get("chart_font") or 10
            slot = (pw - 0.35) / max(n, 1)      # plot width (frame minus the value axis) per category
            bad = [k for k in ch["categories"] if _tw(str(k), sz) * fb > slot and (slot < 0.7 or _tw(max(str(k).split(), key=len), sz) * fb > slot)]      # ponytail: PowerPoint wrapped "Granéis Líquidos" in 0.83in slots (exemplar 007) but not "Perdas e quebras" in ~0.6in (Desktop bom_preco): 0.7in is a guess between them
            if bad:
                w_.append(f"panel '{p['id']}': category labels {bad[:3]} are too long for {slot:.2f}in bars and will overlap: shorter names, cat_size, more panel width, or a bar chart")
    return w_


WARNINGS = []      # filled by composite(); build.build_specs drains it
ROWS = ["top", "upper", "lower", "bottom"]; COLS = ["far-left", "left", "centre-left", "centre-right", "right", "far-right"]


def density(slide, spec):
    """Geometric density check on the 4x6 grid of the body (no rendering). Text boxes count by their estimated text height, lines are ignored.
    Returns warning strings: > 2 empty cells or coverage < 0.55. # ponytail: text height uses the same CPE estimate as the fit check."""
    bx, by, bw, bh = _full(spec); N = 0.05; nx, ny = round(bw / N), round(bh / N); cov = [[False] * nx for _ in range(ny)]
    for sh in slide.shapes:
        x, y, w, h = (sh.left or 0) / 914400, (sh.top or 0) / 914400, (sh.width or 0) / 914400, (sh.height or 0) / 914400
        if min(w, h) < 0.03 or sh.shape_type == 9 or sh.name.startswith("Connector"): continue       # hairlines / connectors do not fill a region
        if sh.has_text_frame and sh.shape_type == 17 and sh.text_frame.text.strip():                  # plain text box: shrink to the text
            sz = max((r.font.size.pt for pp in sh.text_frame.paragraphs for r in pp.runs if r.font.size), default=12)
            h = min(h, sum(_lines(pp.text, w, sz)[0] * sz * 1.2 / 72 for pp in sh.text_frame.paragraphs))
        elif sh.shape_type == 17: continue                                                               # empty text box
        elif sh.shape_type == 1 and not (sh.has_text_frame and sh.text_frame.text.strip()): continue   # empty autoshape (grey panel backing, bars) is not content
        for j in range(max(0, int((y - by) / N)), min(ny, int((y + h - by) / N) + 1)):
            for i in range(max(0, int((x - bx) / N)), min(nx, int((x + w - bx) / N) + 1)): cov[j][i] = True
    cells = []
    for r in range(4):
        for c in range(6):
            js = range(r * ny // 4, (r + 1) * ny // 4); is_ = range(c * nx // 6, (c + 1) * nx // 6)
            cells.append((r, c, sum(cov[j][i] for j in js for i in is_) / (len(js) * len(is_))))
    empty = [f"{ROWS[r]}-{COLS[c]}" for r, c, f in cells if f < 0.15]; total = sum(f for *_, f in cells) / 24; out = []
    if len(empty) > 2 or total < 0.55:
        out.append(f"density: {len(empty)} empty regions ({', '.join(empty) or 'none'}), coverage {total:.2f} - consider fill/panels/more content")
    return out


BUILDERS = {"composite": composite}
