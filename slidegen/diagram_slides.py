"""Diagram archetypes: process_steps, timeline, matrix_2x2, flowchart, issue_tree, funnel, tile_map."""
from pptx.enum.shapes import MSO_SHAPE
from .core import (MX, W, CW, BODY_TOP, text, box, hline, number_badge, section_header, pill, bullets,
                   takeaway_bar, title_and_footer, set_text, tint, fmt)

BAR_Y = 6.1


def _bottom(spec): return BAR_Y - 0.15 if spec.get("takeaway") else 6.7


# ---------------------------------------------------------------- process / time
def process_steps(slide, spec, theme, lang):
    """Chevrons (or numbered circles on a line) with title + description per step. `active` dims the others."""
    title_and_footer(slide, spec, theme, lang)
    steps = spec["steps"]; n = len(steps); act = spec.get("active"); b = _bottom(spec)
    col = lambda i: "BFBFBF" if act is not None and i != act else theme["primary"]
    if spec.get("style", "chevrons") == "chevrons":
        ov = 0.15; sw = (CW + ov * (n - 1)) / n
        for i, s in enumerate(steps):
            x = MX + i * (sw - ov)
            sh = MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON
            pill(slide, x, BODY_TOP + 0.1, sw, 0.85, s["title"], theme, fill=col(i), size=13, shape=sh)
            if s.get("description"):
                text(slide, x + 0.2, BODY_TOP + 1.15, sw - 0.45, b - BODY_TOP - 1.2, s["description"], size=12,
                     color="A6A6A6" if col(i) == "BFBFBF" else "1A1A1A", font=theme["body_font"])
    else:
        cw = CW / n; cy = BODY_TOP + 0.55
        hline(slide, MX + cw / 2, cy, MX + CW - cw / 2, cy, "BFBFBF", 2)
        for i, s in enumerate(steps):
            x = MX + i * cw
            c = box(slide, x + cw / 2 - 0.4, cy - 0.4, 0.8, 0.8, fill=col(i), shape=MSO_SHAPE.OVAL)
            set_text(c, str(i + 1), theme, size=22, bold=True, color=theme["on_primary"] if col(i) == theme["primary"] else "FFFFFF")
            text(slide, x + 0.1, cy + 0.55, cw - 0.2, 0.6, s["title"], size=14, bold=True, color=col(i),
                 font=theme["heading_font"], align="c", anchor="m")
            if s.get("description"):
                text(slide, x + 0.15, cy + 1.2, cw - 0.3, b - cy - 1.25, s["description"], size=12, align="c",
                     color="A6A6A6" if col(i) == "BFBFBF" else "1A1A1A", font=theme["body_font"])
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def timeline(slide, spec, theme, lang):
    """Milestones on a line, or a Gantt (periods + bars) when `bars` is given."""
    title_and_footer(slide, spec, theme, lang); b = _bottom(spec)
    if spec.get("bars"):
        per = spec["periods"]; lw = 2.6; gw = CW - lw; pw = gw / len(per)
        for j, p in enumerate(per):
            pill(slide, MX + lw + j * pw + 0.02, BODY_TOP, pw - 0.04, 0.42, p, theme, size=12,
                 fill=theme["primary"] if j % 2 == 0 else tint(theme["primary"], .25))
        rh = min(0.6, (b - BODY_TOP - 0.55) / len(spec["bars"]))
        for i, bar in enumerate(spec["bars"]):
            y = BODY_TOP + 0.55 + i * rh
            if i % 2 == 0: box(slide, MX, y, CW, rh, fill="F7F7F7")
            text(slide, MX + 0.1, y, lw - 0.2, rh, bar["label"], size=12, bold=True, font=theme["body_font"], anchor="m")
            x0 = MX + lw + bar["start"] * pw; x1 = MX + lw + (bar["end"] + 1) * pw
            lvl = min(bar.get("level", 0), 3)
            pill(slide, x0 + 0.06, y + rh * 0.2, x1 - x0 - 0.12, rh * 0.6, bar.get("note", ""), theme, size=10,
                 fill=theme["series"][lvl], shape=MSO_SHAPE.ROUNDED_RECTANGLE,
                 color="FFFFFF" if lvl == 0 else "1A1A1A")
    else:
        ms = spec["milestones"]; n = len(ms); cw = CW / n; ly = BODY_TOP + 1.3
        hline(slide, MX, ly, MX + CW, ly, theme["primary"], 3)
        for i, m in enumerate(ms):
            cx = MX + i * cw + cw / 2
            text(slide, cx - cw / 2, ly - 0.95, cw, 0.6, m["when"], size=16, bold=True, color=theme["text_primary"],
                 font=theme["heading_font"], align="c", anchor="b")
            box(slide, cx - 0.14, ly - 0.14, 0.28, 0.28, fill="FFFFFF", line=theme["primary"], line_w=3, shape=MSO_SHAPE.OVAL)
            text(slide, cx - cw / 2 + 0.1, ly + 0.3, cw - 0.2, 0.55, m["title"], size=13, bold=True,
                 font=theme["body_font"], align="c")
            if m.get("description"):
                text(slide, cx - cw / 2 + 0.1, ly + 0.85, cw - 0.2, b - ly - 0.9, m["description"], size=11,
                     color="595959", font=theme["body_font"], align="c")
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


# ---------------------------------------------------------------- matrix
def draw_matrix(slide, spec, theme, gx, gy, gw, gh, inline_labels=False, size=12):
    """2x2 grid at (gx, gy) size gw x gh with axis labels and numbered bubbles. Shared with composite panels
    (inline_labels: print each item's label next to its bubble instead of relying on a separate list)."""
    q = spec.get("quadrants", ["", "", "", ""])     # top-left, top-right, bottom-left, bottom-right
    fills = ["F2F2F2", tint(theme["primary"], .75), "F7F7F7", "F2F2F2"]
    for k, (qx, qy) in enumerate(((0, 0), (1, 0), (0, 1), (1, 1))):
        box(slide, gx + qx * gw / 2, gy + qy * gh / 2, gw / 2 - 0.03, gh / 2 - 0.03, fill=fills[k])
        if q[k]:
            text(slide, gx + qx * gw / 2 + 0.1, gy + qy * gh / 2 + 0.08, gw / 2 - 0.2, 0.3, q[k], size=10, bold=True,
                 color="7F7F7F", font=theme["body_font"], align="r" if qx else "l")
    text(slide, gx, gy + gh + 0.08, gw, 0.3, spec["x_label"] + "  →", size=12, bold=True, color="404040",
         font=theme["body_font"], align="c")
    yl = text(slide, gx - 0.55 - gh / 2 + 0.15, gy + gh / 2 - 0.15, gh, 0.3, spec["y_label"] + "  →", size=12,
              bold=True, color="404040", font=theme["body_font"], align="c")
    yl.rotation = -90
    for i, it in enumerate(spec["items"], 1):
        d = 0.32 + 0.04 * it.get("size", 3)
        cx = gx + it["x"] / 10 * gw; cy = gy + gh - it["y"] / 10 * gh
        c = box(slide, cx - d / 2, cy - d / 2, d, d, fill=theme["primary"], line="FFFFFF", line_w=1.5, shape=MSO_SHAPE.OVAL)
        set_text(c, str(i), theme, size=11, bold=True, color=theme["on_primary"])
        if inline_labels:
            right = cx + d / 2 + 0.05 + 1.3 <= gx + gw
            text(slide, cx + d / 2 + 0.05 if right else cx - d / 2 - 1.35, cy - 0.12, 1.3, 0.24, it["label"], size=10,
                 bold=True, font=theme["body_font"], align="l" if right else "r", anchor="m")


def matrix_2x2(slide, spec, theme, lang):
    """Grid left with numbered bubbles (0-10 axes, top-right quadrant tinted), numbered list right."""
    title_and_footer(slide, spec, theme, lang); b = _bottom(spec)
    gx, gy = MX + 0.55, BODY_TOP + 0.1; gw, gh = 5.2, b - BODY_TOP - 0.65
    draw_matrix(slide, spec, theme, gx, gy, gw, gh)
    lx = gx + gw + 0.5; lw = W - MX - lx
    section_header(slide, lx, lw, BODY_TOP - 0.05, spec.get("list_title", "Itens" if lang == "pt" else "Items"), theme)
    step = min(0.95, (b - BODY_TOP - 0.6) / len(spec["items"]))
    for i, it in enumerate(spec["items"], 1):
        y = BODY_TOP + 0.6 + (i - 1) * step
        number_badge(slide, lx, y + 0.02, i, theme)
        body = f"**{it['label']}**" + (f": {it['description']}" if it.get("description") else "")
        text(slide, lx + 0.42, y, lw - 0.42, step - 0.05, body, size=11, font=theme["body_font"])
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


# ---------------------------------------------------------------- trees
def _tree(nodes):
    """nodes [{id,label,parent}] -> (children map, root id, depth map, leaf-order position map, leaf count)."""
    kids = {n["id"]: [] for n in nodes}; root = None
    for n in nodes:
        if n.get("parent") in kids: kids[n["parent"]].append(n["id"])
        else: root = n["id"]
    depth, pos, leaf = {}, {}, [0]
    def walk(i, d):
        depth[i] = d
        if not kids[i]:
            pos[i] = leaf[0]; leaf[0] += 1
        else:
            for k in kids[i]: walk(k, d + 1)
            pos[i] = (pos[kids[i][0]] + pos[kids[i][-1]]) / 2
    walk(root, 0)
    return kids, root, depth, pos, leaf[0]


NODE_STYLES = {"grey": ("BFBFBF", None, "FFFFFF", False), "outline": ("FFFFFF", "P", "T", True), "fill": ("P", None, "O", True), "plain": ("FFFFFF", "BFBFBF", "1A1A1A", False)}


def _node(slide, x, y, w, h, label, d, theme, style=None, size=None):
    """Tree box. style grey | outline | fill | plain (flow panels); default by depth (root filled, level 1 pale, rest outlined)."""
    if style:
        fill, line, col, bold = NODE_STYLES[style]
        k = {"P": theme["primary"], "T": theme["text_primary"], "O": theme["on_primary"]}
        fill, line, col = k.get(fill, fill), k.get(line, line), k.get(col, col); lw = 1.5
    else:
        lw = 1.25; bold = d < 2
        if d == 0: fill, line, col = theme["primary"], None, theme["on_primary"]
        elif d == 1: fill, line, col = theme["pale"], theme["primary"], "1A1A1A"
        else: fill, line, col = "FFFFFF", "BFBFBF", "1A1A1A"
    s = box(slide, x, y, w, h, fill=fill, line=line, line_w=lw)
    sz = size or (11 if d else 12); lw_ = max(len(t) for t in label.split())      # shrink so the longest word fits on one line (no "Funcionário/s" break)
    sz = max(6, min(sz, int((w - 0.16) * 72 / (lw_ * 0.52))))      # floor 6pt: a mid-word break ("Depreciaçã/o") is a worse giveaway than small text    # ponytail: char-width estimate, ~0.52 em per char (Arial)
    set_text(s, label, theme, size=sz, bold=bold, color=col)


def _arrow_end(conn):
    from pptx.oxml.ns import qn; from lxml import etree
    etree.SubElement(conn.line._get_or_add_ln(), qn("a:tailEnd"), type="triangle", w="med", len="med")


def draw_tree(slide, nodes, theme, x, y, w, h, mode, flip=False, nh=None, gap=0.45, size=None):
    """Boxes + elbow connectors for a parent-linked node list inside the rect (x, y, w, h). mode 'td' (levels top to bottom) or 'lr'.
    flip: the root sits at the far end (bottom / right) and the connectors point to it (a flow of inputs feeding a result);
    a node with 'op' draws that operator in a circle on the junction of its inputs. Shared by flowchart, issue_tree and composite flow panels."""
    kids, root, depth, pos, nleaf = _tree(nodes); N = {n["id"]: n for n in nodes}
    levels = max(depth.values()) + 1; lv = {i: levels - 1 - d if flip else d for i, d in depth.items()}; td = mode == "td"
    if td: nh = nh or 0.65; nw = min(2.3, w / nleaf - 0.2); sz = nh; step = (h - nh) / max(levels - 1, 1); C = lambda i: x + (pos[i] + 0.5) * w / nleaf; L = lambda i: y + lv[i] * step
    else: nw = (w - gap * (levels - 1)) / levels; rh = h / nleaf; nh = nh or min(0.75, rh - 0.12); sz = nw; C = lambda i: y + (pos[i] + 0.5) * rh; L = lambda i: x + lv[i] * (nw + gap)
    P = lambda l, c: (c, l) if td else (l, c)          # (level coordinate, cross coordinate) -> (x, y)
    ln = lambda l1, c1, l2, c2: hline(slide, *P(l1, c1), *P(l2, c2), "7F7F7F", 1.25)
    M = {}
    for i, ks in kids.items():
        if not ks: continue
        pe = L(i) + (0 if flip else sz); ke = lambda k: L(k) + (sz if flip else 0); mid = M[i] = (pe + ke(ks[0])) / 2
        if flip: c = hline(slide, *P(mid, C(i)), *P(pe, C(i)), "7F7F7F", 1.25); _arrow_end(c)
        else: ln(pe, C(i), mid, C(i))
        ln(mid, C(ks[0]), mid, C(ks[-1]))
        for k in ks: ln(ke(k), C(k), mid, C(k))
    for i in depth:
        r = (C(i) - nw / 2, L(i), nw, nh) if td else (L(i), C(i) - nh / 2, nw, nh)
        _node(slide, *r, N[i].get("label") or N[i]["text"], depth[i], theme, N[i].get("style"), size)
    for i, ks in kids.items():           # operator circles last, on top of the connectors
        if ks and N[i].get("op"):
            cx, cy = P(M[i], C(i))
            o = box(slide, cx - 0.13, cy - 0.13, 0.26, 0.26, fill="FFFFFF", line=theme["primary"], line_w=1.25, shape=MSO_SHAPE.OVAL)
            set_text(o, N[i]["op"], theme, size=12, bold=True, color=theme["text_primary"]); tf = o.text_frame
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0


def flowchart(slide, spec, theme, lang):
    """Top-down org chart / hierarchy with elbow connectors."""
    title_and_footer(slide, spec, theme, lang); b = _bottom(spec)
    draw_tree(slide, spec["nodes"], theme, MX, BODY_TOP + 0.05, CW, b - 0.15 - BODY_TOP, "td")
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def issue_tree(slide, spec, theme, lang):
    """Left-to-right logic tree (MECE breakdown of a key question)."""
    title_and_footer(slide, spec, theme, lang); b = _bottom(spec)
    draw_tree(slide, spec["nodes"], theme, MX, BODY_TOP, CW, b - BODY_TOP, "lr")
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


def funnel(slide, spec, theme, lang):
    """Narrowing bars (e.g. 955 products -> 64 -> 5) with the filter criterion of each stage on the right."""
    title_and_footer(slide, spec, theme, lang); b = _bottom(spec)
    st = spec["stages"]; n = len(st); fw = 7.2; cx = MX + fw / 2
    rh = (b - BODY_TOP) / n
    for i, s in enumerate(st):
        w = fw * (1 - 0.55 * i / max(n - 1, 1)); y = BODY_TOP + i * rh
        col = theme["series"][min(i, 3)] if i < n - 1 else theme["primary"]
        pill(slide, cx - w / 2, y + 0.05, w, rh - 0.12, [f"**{s['value']}**  {s['label']}"], theme, fill=col,
             size=14, bold=False, color=theme["on_primary"] if i in (0, n - 1) else "1A1A1A")
        if s.get("criterion"):
            hline(slide, cx + w / 2 + 0.1, y + rh / 2, MX + fw + 0.45, y + rh / 2, "BFBFBF", 1, dash=True)
            text(slide, MX + fw + 0.55, y + 0.05, W - MX - (MX + fw + 0.55), rh - 0.1, s["criterion"], size=12,
                 font=theme["body_font"], anchor="m")
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


# ---------------------------------------------------------------- map
# Tile-grid map of Brazil (one tile per UF, approximate geography). Native, recolourable, no image needed.
BR_TILES = {"RR": (3, 0), "AP": (5, 0), "AM": (3, 1), "PA": (4, 1), "MA": (5, 1), "CE": (6, 1), "RN": (7, 1),
            "AC": (1, 2), "RO": (2, 2), "MT": (3, 2), "TO": (4, 2), "PI": (5, 2), "PE": (6, 2), "PB": (7, 2),
            "MS": (2, 3), "GO": (3, 3), "DF": (4, 3), "BA": (5, 3), "SE": (6, 3), "AL": (7, 3),
            "PR": (3, 4), "SP": (4, 4), "MG": (5, 4), "ES": (6, 4), "SC": (3, 5), "RJ": (5, 5), "RS": (3, 6)}


def draw_tiles(slide, vals, theme, ox, oy, t, hl, dec, lang):
    """Tile-grid choropleth + legend. Grid origin (ox, oy), tile size t; returns (lo, hi). Shared with composite panels."""
    lo, hi = min(vals.values()), max(vals.values()); span = (hi - lo) or 1
    for uf, (c, r) in BR_TILES.items():
        v = vals.get(uf); x = ox + c * t; y = oy + r * t
        if v is None: fill, col = "F2F2F2", "A6A6A6"
        else:
            k = (v - lo) / span; fill = tint(theme["primary"], .85 - .85 * k); col = "FFFFFF" if k > .45 else "1A1A1A"
        s = box(slide, x + 0.03, y + 0.03, t - 0.06, t - 0.06, fill=fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE,
                line=theme["dark"] if uf in hl else None, line_w=2.25, dash=uf in hl)
        fs = min(9, max(5, round((t - 0.06) * 72 / 2.5)))       # two lines must fit small tiles (composite panels)
        set_text(s, [f"**{uf}**", fmt(v, dec, lang) if v is not None else "–"], theme, size=fs, color=col)
        tf = s.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    lx = ox + 4.4 * t; ly = oy + 6.35 * t; sw = min(0.45, t * 0.5)
    for i in range(5):
        box(slide, lx + i * sw, ly, sw, 0.16, fill=tint(theme["primary"], .85 - .85 * i / 4))
    text(slide, lx, ly + 0.18, max(2.25, 5 * sw), 0.25, f"{fmt(lo, dec, lang)}  →  {fmt(hi, dec, lang)}", size=9, color="7F7F7F",
         font=theme["body_font"])
    return lo, hi


def tile_map(slide, spec, theme, lang):
    """Choropleth on a tile grid of the 27 UFs + legend + ranked top-N list + insights."""
    title_and_footer(slide, spec, theme, lang); b = _bottom(spec)
    vals = spec["values"]; dec = spec.get("decimals", 0)
    t = min(6.2 / 7, (b - BODY_TOP - 0.2) / 7); ox = MX - 0.6 * t; oy = BODY_TOP + 0.1
    lo, hi = draw_tiles(slide, vals, theme, ox, oy, t, set(spec.get("highlight", [])), dec, lang)
    rx = MX + 6.9; rw = W - MX - rx
    section_header(slide, rx, rw, BODY_TOP - 0.05, spec.get("ranking_title", "Ranking"), theme)
    top = sorted(vals.items(), key=lambda kv: -kv[1])[:spec.get("top", 5)]
    for i, (uf, v) in enumerate(top):
        y = BODY_TOP + 0.55 + i * 0.36
        number_badge(slide, rx, y, i + 1, theme, d=0.26)
        text(slide, rx + 0.4, y, 1.2, 0.28, uf, size=12, bold=True, font=theme["body_font"], anchor="m")
        bw = (rw - 2.4) * v / hi
        box(slide, rx + 1.0, y + 0.05, bw, 0.18, fill=theme["primary"])
        text(slide, rx + 1.05 + bw, y, 1.3, 0.28, fmt(v, dec, lang) + ((spec["unit"] if spec["unit"] == "%" else " " + spec["unit"]) if spec.get("unit") else ""),
             size=11, color="404040", font=theme["body_font"], anchor="m")
    if spec.get("insights"):
        y = BODY_TOP + 0.75 + len(top) * 0.36
        bullets(slide, rx, y, rw, b - y, spec["insights"], theme, size=12, spacing=6)
    if spec.get("takeaway"): takeaway_bar(slide, spec["takeaway"], theme, lang, y=BAR_Y)


BUILDERS = {"process_steps": process_steps, "timeline": timeline, "matrix_2x2": matrix_2x2, "flowchart": flowchart,
            "issue_tree": issue_tree, "funnel": funnel, "tile_map": tile_map}
