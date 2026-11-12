"""Composition recommender: content profile -> top 3 composite-slide options (layout, panels, links, spec skeleton, archive refs).

Run: py -3 tools/compose.py profile.json      (MCP: suggest_composition)
Profile: {"message", "lang", "items":[{id, kind, points, series, words, label, ...}], "relations":[{from,to,type}], "insights":N, "decisions":N}
Item kinds: bridge trend composition ranking comparison distribution correlation kpi geo process matrix lookup_table list text.
Optional item flags: br_states (geo has Brazilian UFs), qualitative (comparison is yes/no/ratings), share (composition as % of total),
numeric (lookup_table has numeric columns -> mini-bars), titled (list items have titles -> cards).
Composite-element shapes (added after the cold-chain case; old profiles unchanged):
  kind "breakdown" (parts that sum to a total, e.g. CAPEX = a+b+c; points = leaves, groups = [3,3] leaves per sub-total or a count) -> flow panel with "+" junctions
        (also kind composition + hierarchy:true or parts:[...]);
  kind "assumptions" (or lookup_table/list/comparison + sourced:true; points = rows, series = columns) -> table with pill cells + pill_legend (origin of each number);
  kind trend + phases:N (named phases of the time axis) -> chart `phases`; signed:true (negative then positive) -> column chart; payback:true -> `note` link on the chart.
Deterministic: rules below, no randomness. Numbers come from analysis/elements_labeled.jsonl (740 content slides, summarised in
docs/element-library.md); every approximation is marked "ponytail:".
"""
import itertools, json, math, random, re, sys, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from slidegen import composite      # noqa: E402
ARCHIVE = ROOT / "analysis" / "elements_labeled.jsonl"

# ---- archive facts (docs/element-library.md sec.3 and 4; medians re-computed from elements_labeled.jsonl) ----
LAYOUT_SHARE = {"1": .42, "2col": .16, "3col": .06, "T|B": .04, "L2|R": .02, "L|R2": .01, "2x2": .01,   # share of 740 content slides
                "4col": .026, "2x3": .01, "L|R3": .01, "T|B3": .01, "T2|B3": .01}   # 4col: 19 slides; ponytail: the other four have no archive count (5+col = 13 slides is their nearest family)
ARCH_WORDS = {"median": 174, "p25": 123, "p10": 65}      # words/slide over content slides
ARCH_COVER = {"median": .62, "p25": .54, "p10": .45}     # body area covered (density.area_covered)
ARCH_LAYOUT_ALIAS = {"L|R1": "2col"}                      # archive signature -> composite layout

# ---- element table: panel kind, chart kind, points range handled well, max series -----------------------
# ranges: composite limits (docs/archetypes.md: bullets 1-6, cards 2-5, kpis 1-4, process 2-5, matrix 2-8, table cols 2-6)
# and archive medians (native charts: 2 series x 5 categories; tables 6 rows x 5 cols; waterfall archive 12 slides).
# ponytail: chart point ranges are judgement calls from half-slide readability, not measured.
ELEMENTS = {  # name: (panel kind, chart kind, min points, max points, max series)
    "waterfall": ("chart", "waterfall", 3, 10, 1), "line": ("chart", "line", 4, 24, 4), "column": ("chart", "column", 2, 12, 3),
    "stacked": ("chart", "stacked", 3, 8, 5), "stacked100": ("chart", "stacked100", 3, 8, 5), "doughnut": ("chart", "doughnut", 2, 5, 1),
    "bar": ("chart", "bar", 3, 12, 1), "scatter": ("chart", "scatter", 4, 40, 3), "bubble": ("chart", "bubble", 4, 25, 3), "table": ("table", None, 2, 8, 6), "kpis": ("kpis", None, 1, 4, 1),
    "map_br": ("map_br", None, 3, 27, 1), "process": ("process", None, 2, 5, 1), "matrix": ("matrix", None, 2, 8, 1),
    "bullets": ("bullets", None, 1, 6, 1), "cards": ("cards", None, 2, 5, 1),
    "flow": ("flow", None, 3, 12, 1), "table_pills": ("table", None, 2, 8, 6),
}


def pick_element(it):
    """item -> element name (key of ELEMENTS)."""
    k, pts, ser = it["kind"], it.get("points", 0), it.get("series", 1)
    if k == "bridge": return "waterfall"
    if k == "breakdown" or (k == "composition" and (it.get("hierarchy") or it.get("parts"))): return "flow"     # parts -> total with "+" junctions
    if it.get("sourced") and k in ("lookup_table", "list", "comparison", "text"): return "table_pills"        # assumptions with their origin
    if k == "trend" and it.get("signed") and ser == 1 and pts <= 12: return "column"                          # negative then positive: columns, not a line
    if k == "trend": return "line" if pts > 8 or ser > 1 else "column"
    if k == "composition":
        if ser == 1 and 2 <= pts <= 5: return "doughnut"
        if pts > 8: return "bar"
        return "stacked100" if it.get("share") else "stacked"
    if k == "correlation" and it.get("dimensions", 2) >= 2 and pts >= 4: return "bubble" if it["dimensions"] >= 3 else "scatter"     # 2 numeric dimensions = x, y; a 3rd = bubble size (archive: 41 scatters)
    if k in ("ranking", "distribution", "correlation"): return "bar" if k == "ranking" and pts <= 12 else "column" if pts <= 12 else "table"     # correlation with < 2 dimensions or < 4 points: column of the ratio / table of the pairs
    if k == "comparison": return "table" if it.get("qualitative") or not ser else "column"
    if k == "lookup_table": return "table"
    if k == "kpi": return "kpis"
    if k == "geo": return "map_br" if it.get("br_states") else "bar" if pts <= 12 else "table"
    if k in ("process", "matrix"): return k
    if k == "cards": return "cards"
    return "cards" if it.get("titled") and 2 <= pts <= 5 else "bullets"          # list / text


def fit(it, el):
    _, _, lo, hi, smax = ELEMENTS[el]; pts, ser = it.get("points", 0), it.get("series", 1)
    if pts and pts > hi: return f"too many points ({pts} > {hi}): keep the top {hi} and group the rest as 'Outros'"
    if pts and pts < lo: return f"few points ({pts} < {lo}): pair it with a table or KPI strip"
    if ser > smax: return f"too many series ({ser} > {smax}): merge or split"
    return "ok"


# ---- layouts: slot rectangles (x, y, w, h in 0..1, composite reading order) and the relation shapes each suits ----
SLOTS = {"1": [(0, 0, 1, 1)], "2col": [(0, 0, .5, 1), (.5, 0, .5, 1)], "3col": [(i / 3, 0, 1 / 3, 1) for i in range(3)], "4col": [(i / 4, 0, .25, 1) for i in range(4)],
         "2x3": [(c / 3, r / 2, 1 / 3, .5) for r in range(2) for c in range(3)], "L|R3": [(0, 0, .5, 1), *[(.5, r / 3, .5, 1 / 3) for r in range(3)]],
         "T|B3": [(0, 0, 1, .5), *[(c / 3, .5, 1 / 3, .5) for c in range(3)]], "T2|B3": [(0, 0, .5, .5), (.5, 0, .5, .5), *[(c / 3, .5, 1 / 3, .5) for c in range(3)]],
         "T|B": [(0, 0, 1, .5), (0, .5, 1, .5)], "L|R2": [(0, 0, .5, 1), (.5, 0, .5, .5), (.5, .5, .5, .5)],
         "L2|R": [(0, 0, .5, .5), (0, .5, .5, .5), (.5, 0, .5, 1)], "2x2": [(0, 0, .5, .5), (.5, 0, .5, .5), (0, .5, .5, .5), (.5, .5, .5, .5)]}
# shape fit 0..5, hand-set from the layout/kind tables of element-library.md sec.3 and the user's reference slides
# (fan = 1 source -> 2 details: orbital; converge = 2 inputs -> 1 conclusion; chain = a->b->c; compare = same measure side by side).
SHAPE_FIT = {"1": {"single": 5}, "2col": {"chain": 4, "compare": 4, "converge": 3, "parallel": 3, "fan": 2},
             "T|B": {"chain": 3, "compare": 2, "parallel": 2, "fan": 2, "converge": 2},
             "3col": {"chain": 4, "compare": 4, "parallel": 3, "fan": 1.5, "converge": 1.5},
             "L|R2": {"fan": 5, "chain": 2, "parallel": 2}, "L2|R": {"converge": 5, "parallel": 2, "chain": 1.5},
             "2x2": {"parallel": 4, "compare": 3, "chain": 2, "fan": 2, "converge": 2},
             "4col": {"chain": 4, "compare": 4, "parallel": 3, "fan": 1.5, "converge": 1.5}, "2x3": {"parallel": 4, "compare": 3, "chain": 2, "fan": 2, "converge": 2},
             "L|R3": {"fan": 4, "parallel": 3, "chain": 2, "converge": 1.5}, "T|B3": {"converge": 3, "parallel": 3, "chain": 2, "fan": 2, "compare": 2},
             "T2|B3": {"parallel": 3, "chain": 2, "compare": 2, "fan": 2, "converge": 2}}   # ponytail: hand-set like the rows above, no archive count
FLOW = ("leads_to", "zooms_into", "explains", "located_in")
BIG = {"flow", "scatter", "bubble", "waterfall", "stacked", "stacked100", "line", "column", "bar", "map_br", "matrix"}   # exhibits that want a big slot


def adjacent(a, b):                       # same rule as composite.check for arrows: side by side or stacked, not diagonal
    xo = a[0] < b[0] + b[2] - 1e-9 and b[0] < a[0] + a[2] - 1e-9; yo = a[1] < b[1] + b[3] - 1e-9 and b[1] < a[1] + a[3] - 1e-9
    return xo != yo


def shape(n, rels):
    if n == 1: return "single"
    out, inn = {}, {}
    for r in rels:
        out.setdefault(r["from"], []).append(r); inn.setdefault(r["to"], []).append(r)
    if any(r["type"] == "compares" for r in rels): return "compare"
    if any(len(v) >= 2 and v[0]["type"] in FLOW for v in out.values()): return "fan"
    if any(len(v) >= 2 for v in inn.values()): return "converge"
    return "chain" if rels else "parallel"


def place(layout, items, els, rels):
    """Best assignment of items to slots (<= 24 permutations): relations adjacent+forward, big exhibits in big slots."""
    S, ids = SLOTS[layout], [i["id"] for i in items]
    srcs = [r["from"] for r in rels if r["type"] in FLOW]
    best, bs = None, -1e9
    for perm in itertools.permutations(range(len(items))):           # perm[slot] = item index
        pos = {ids[p]: s for s, p in enumerate(perm)}; sc = 0
        for r in rels:
            a, b = pos.get(r["from"]), pos.get(r["to"])
            if a is None or b is None: continue
            sc += 2 * adjacent(S[a], S[b]) + .5 * (a < b)
        for s, p in enumerate(perm):
            area = S[s][2] * S[s][3]
            sc += (area >= .5) * .6 * (els[p] in BIG) + (area <= .34) * .3 * (els[p] in ("table", "kpis", "bullets", "cards"))
            sc += 1.5 * (ids[p] in srcs and area == max(x[2] * x[3] for x in S))
        if sc > bs + 1e-9: best, bs = perm, sc
    return best, bs


# ---- skeleton builders ----------------------------------------------------------------------------------
def _panel(pid, it, el):
    pk, ck, _, _, _ = ELEMENTS[el]; n = max(it.get("points", 3), 1); ser = max(it.get("series", 1), 1); lab = it.get("label")
    p = {"id": pid, "kind": pk}
    if lab: p["title"] = lab[:70]
    cats = [f"TODO {i + 1}" for i in range(n)]
    if ck in ("scatter", "bubble"):       # points instead of categories; mean quadrants are the usual reading of a correlation
        p["chart"] = {"kind": ck, "x_title": "TODO x", "y_title": "TODO y", "quadrants": {"x": "mean", "y": "mean", "labels": ["TODO"] * 4},
                      "points": [{"x": i + 1, "y": (i * 3) % 5 + 1, "label": f"TODO {i + 1}", **({"size": i + 1} if ck == "bubble" else {})} for i in range(min(max(n, 4), 40))]}
    elif pk == "chart":
        ch = {"kind": ck, "categories": cats, "series": [{"name": f"Série {s + 1}", "values": [1] * n} for s in range(ser)], "number_format": "#,##0"}
        k = max(_count(it.get("phases")), 0)
        if k >= 2 and ck in ("column", "stacked", "stacked100", "line", "waterfall"): ch["phases"] = [{"start": i * n // k, "label": str(i + 1)} for i in range(k)]
        if it.get("signed"): ch["series"][0]["values"] = [-1] + [1] * (n - 1)
        if ck == "waterfall": ch.update(total_first=True, categories=["Total"] + cats[:-1], series=[{"name": lab or "TODO", "values": [n - 1] + [1] * (n - 1)}])
        if ck == "stacked": ch.update(totals=True, series_labels="left", small_callouts=True)   # user's reference: names beside the stack, small values pulled out
        p["chart"] = ch
    elif pk == "flow":
        g = it.get("groups"); g = g if isinstance(g, list) else [n // g + (i < n % g) for i in range(g)] if isinstance(g, int) and 1 < g <= n else []
        if sum(g) != n: g = []
        nodes = [{"id": "tot", "text": "TODO total", "style": "fill", "op": "+"}]
        for gi, size in enumerate(g or [0]):
            par = "tot"
            if g: par = f"g{gi}"; nodes.append({"id": par, "text": f"TODO grupo {gi + 1}", "style": "outline", "parent": "tot", "op": "+"})
            nodes += [{"id": f"{par}_{j}", "text": f"TODO parte {gi + 1}.{j + 1}", "style": "grey", "parent": par} for j in range(size or n)]
        p.update(direction="lr", nodes=nodes)
    elif pk == "table" and el == "table_pills":
        cols = min(max(it.get("series", 3), 3), 6); src = ["Dado público", "Benchmark", "Decisão", "Estimativa"]; col = ["primary", "C0701F", "FFC000", "4D4D4D"]
        p.update(columns=["TODO premissa"] + [f"TODO col {c}" for c in range(1, cols - 1)] + ["Origem"],
                 rows=[["TODO"] * (cols - 1) + [{"pill": src[r % 4], "color": col[r % 4]}] for r in range(min(n, 8))],
                 pill_legend={"label": "Origem:", "pills": [{"pill": a, "color": b} for a, b in zip(src, col)]})
    elif pk == "table":
        cols = min(max(ser if it["kind"] != "lookup_table" else it.get("series", 2), 2), 6)
        p.update(columns=[f"TODO col {c + 1}" for c in range(cols)], rows=[["TODO"] * cols for _ in range(min(n, 8))])
        if it.get("numeric"): p["note_mini_bars"] = "numeric pair columns can use {bars} cells"   # stripped below
        p.pop("note_mini_bars", None)
    elif pk == "kpis": p["items"] = [{"value": "TODO", "label": "TODO"} for _ in range(min(n, 4))]
    elif pk == "map_br": p["values"] = dict(zip(["SP", "RJ", "MG", "BA", "PR", "RS"], range(1, min(max(n, 3), 6) + 1)))
    elif pk == "process": p["steps"] = [{"title": f"TODO {i + 1}", "text": "TODO"} for i in range(min(max(n, 2), 5))]
    elif pk == "matrix":
        p.update(x_label="TODO x", y_label="TODO y", quadrants=["TODO"] * 4, items=[{"label": f"TODO {i + 1}", "x": 2 + i, "y": 3 + i, "size": 5} for i in range(min(max(n, 2), 8))])
    elif pk == "cards": p.update(numbered=True, items=[{"title": f"TODO {i + 1}", "text": "TODO"} for i in range(min(max(n, 2), 5))])
    else: p["items"] = ["**TODO:** frase"] * min(max(n, 1), 6)
    return p


_G = None
def grammar():
    """Archive slide grammar from vision labels (tools/grammar.py -> analysis/grammar.json); {} when absent."""
    global _G
    if _G is None:
        f = ROOT / "analysis" / "grammar.json"; _G = json.loads(f.read_text("utf8")) if f.exists() else {}
    return _G


GFAM = {"kpis": "big_numbers", "bullets": "bullets", "cards": "cards", "flow": "diagram", "process": "diagram", "matrix": "matrix", "map_br": "map", "table": "table", "table_pills": "table"}
def gfam(el):                             # compose element -> grammar block family (charts: everything ELEMENTS draws as a chart)
    return GFAM.get(el) or ("chart" if ELEMENTS[el][0] == "chart" else "other")


def sections(items, els, rels, k=3):
    """4-6 items -> k cols sections (user ruling 2026-11-12: one main exhibit + at most one support per section): up to 2 small
    result blocks (kpis / bullets / cards) share one section; the rest pair up, related items first, else the pair the archive
    most often puts in one section (grammar same_section). Returns lists of item indexes, or None when k does not fit."""
    ids = [i["id"] for i in items]; rel = {frozenset((r["from"], r["to"])) for r in rels}
    same = grammar().get("same_section", {}); co = lambda a, b: same.get(" + ".join(sorted((gfam(els[a]), gfam(els[b])))), 0)
    small = [j for j in range(len(items)) if els[j] in ("kpis", "bullets", "cards")][:2]
    groups = [[j] for j in range(len(items)) if j not in small]
    lone = small if len(small) == 1 else []; small = small if len(small) == 2 else []    # one small block is a support, not a section
    while len(groups) + bool(small) > k:     # ponytail: greedy pairing of singles; related first, then archive co-occurrence
        one = [a for a in range(len(groups)) if len(groups[a]) == 1]
        if len(one) < 2: return None
        cand = [(a, b) for x, a in enumerate(one) for b in one[x + 1:]]
        a, b = max(cand, key=lambda ab: (frozenset((ids[groups[ab[0]][0]], ids[groups[ab[1]][0]])) in rel, co(groups[ab[0]][0], groups[ab[1]][0]), ab[0]))
        groups[a] += groups.pop(b)
    if lone:                                 # under the single exhibit it relates to (else the archive's most frequent pairing)
        one = [a for a in range(len(groups)) if len(groups[a]) == 1]
        if not one: return None
        groups[max(one, key=lambda a: (frozenset((ids[groups[a][0]], ids[lone[0]])) in rel, co(groups[a][0], lone[0]), -a))] += lone
    g = groups + [small] * bool(small)
    return g if len(g) == k and all(len(x) <= 2 for x in g) else None


SECTION_STYLES = {"label": .358, "centred_rule": .223, "bar": .106, "rule": .097}      # archive header_styles without "none" (sections stay marked, ruling 2026-11-11)
def section_style(prof):
    """Section header look for this slide, drawn from the archive mix (user ruling 2026-11-12); seeded by the message so a slide keeps its look across runs."""
    G = grammar().get("header_styles") or {}; w = {k: G.get(k, v) for k, v in SECTION_STYLES.items()}
    r = random.Random(zlib.crc32((prof.get("message") or "").encode("utf8"))).random() * sum(w.values())
    for k, v in w.items():
        r -= v
        if r <= 0: return k
    return "label"


def hero(items, els, rels):
    """The exhibit that carries the message: most relations point to it (>= 2), else a bridge, else a chart with >= 8 points. None if no item stands out."""
    ind = {i["id"]: sum(r["to"] == i["id"] for r in rels) for i in items}
    big = [j for j in range(len(items)) if els[j] not in ("kpis", "bullets", "cards")]
    j = max(big, key=lambda j: (ind[items[j]["id"]], items[j]["kind"] == "bridge", items[j].get("points", 0)), default=None)
    if j is not None and ind[items[j]["id"]] >= 2: return j
    return next((j for j in big if items[j]["kind"] == "bridge"), next((j for j in big if ELEMENTS[els[j]][0] == "chart" and items[j].get("points", 0) >= 8), None))


SMALL = ("kpis", "bullets", "cards")


def stacked_option(items, els, rels, prof, g, shape, hero_j=None):
    """Stacked sections (archive dispositions, user ruling 2026-11-12: vary the disposition): shape "L" = one tall section beside two
    stacked ones (~10% of archive slides), "grid" = 2x2 sections (~5%). Stacked sections carry their own header (cols row_titles);
    each holds one exhibit + at most one small support. g = item-index groups from sections(); None when they do not stack."""
    if shape == "L":
        tall = lambda j: els[j] in ("flow", "process", "matrix", "table", "table_pills") and items[j].get("points", 0) > 3      # needs a full-height column
        ok = [c for c in range(len(g)) if all(len(x) == 1 for d, x in enumerate(g) if d != c)]      # the stacked sections hold one exhibit each
        if not ok: return None
        li = max(ok, key=lambda c: (any(tall(j) for j in g[c]), len(g[c]) > 1, hero_j in g[c], -c))
        cg = [[g[li]], [x for c, x in enumerate(g) if c != li]]
    else: cg = [g[:2], g[2:]]
    if any(len(x) > 1 for c, secs in enumerate(cg) for x in secs if shape == "grid" or c == 1): return None      # a stacked section is short: one exhibit, no support
    perm = [j for secs in cg for x in secs for j in x]; cols, S, x0 = [], [], 0
    for c, secs in enumerate(cg):
        rows, rt = [], []
        for x in secs:
            rows += [f / len(secs) for f in ([0.6, 0.4] if len(x) == 2 else [1])]; rt += ["S"] + [None] * (len(x) - 1)
        y0 = 0
        for r in rows: S.append((x0, y0, 0.5, r)); y0 += r
        col = {"w": 0.5, "rows": [round(r, 2) for r in rows]}
        if shape == "L" and c == 0: col["title"] = "TODO seção"
        else: col["row_titles"] = rt
        cols.append(col); x0 += 0.5
    n = len(items); share = grammar().get("dispositions_by_blocks", {}).get(str(min(n, 7)), {}).get("L" if shape == "L" else "grid2x2")
    why = ("uma seção alta + duas empilhadas ao lado (forma em L), cada uma com seu cabeçalho" if shape == "L" else "quatro seções em grade 2x2, cada uma com seu cabeçalho") + \
          (f"; no arquivo, {share:.0%} dos slides com {n} blocos usam essa disposição" if share else "")
    o = build_option("cols", items, els, perm, rels, {**prof, "insights": 0}, shape, why, slots=S); o["score"] = share or 0
    sp = o["spec"]; sp.pop("takeaway", None); sp["divider"] = True; sp["dividers"] = True; sp["section_style"] = section_style(prof); sp["cols"] = cols; k = 0
    for col in cols:
        for i in range(len(col["rows"])):
            q = sp["panels"][k + i]; q["title_plain"] = True
            if col.get("row_titles") and col["row_titles"][i]: lab = q.pop("title", ""); col["row_titles"][i] = f"TODO seção ({lab})" if lab else "TODO seção"      # the section header names the exhibit; no second title in a short row
        k += len(col["rows"])
    if prof.get("decisions") == 1:
        host = next((q for q in reversed(sp["panels"]) if q["kind"] != "chart"), None)
        if host: host["callout"] = {"lead": "Conclusão:", "text": "TODO decisão recomendada"}
        else: sp["takeaway"] = "TODO: decisão recomendada"
    o["notes"].append("seções empilhadas (row_titles): o cabeçalho da seção nomeia o exhibit e a unidade; a linha é curta, então no máximo 1 bullet sob o gráfico")
    return o


def sections_option(items, els, rels, prof, k=3, wide=None, band=None, shape="cols"):
    """cols sections (user rulings 2026-11-12): k sections of one exhibit + at most one support. Variants from the content:
    wide = item index whose section gets ~1.6x the width (the exhibit that carries the message);
    band = item index that runs across the top (an exhibit that needs width, or the KPIs as a strip), the rest in k sections below."""
    idx = [j for j in range(len(items)) if j != band]
    sub = sections([items[j] for j in idx], [els[j] for j in idx], rels, k)
    if not sub: return None
    g = [[idx[j] for j in s] for s in sub]; G = grammar()
    if shape != "cols": return stacked_option(items, els, rels, prof, g, shape, wide)
    if band is not None and els[band] != "kpis" and any(sum(els[j] not in ("kpis", "bullets", "cards") for j in s) > 1 for s in g): return None      # under a band the columns are short: no two exhibits stacked
    strip = band is not None and els[band] == "kpis"; bh = 0 if band is None else 0.2 if strip else 0.45
    perm = ([band] if band is not None else []) + [j for s in g for j in s]
    # widths from the archive (grammar rel_width: mostly equal; tables / matrices ~5-12% wider); the hero's section ~1.6x
    rw = G.get("rel_width", {}); raw = [max(rw.get(gfam(els[j]), 1.0) for j in s) * (1.6 if wide in s else 1) for s in g]; ws = [round(r / sum(raw), 2) for r in raw]
    S = [(0, 0, 1, bh)] if band is not None else []; x0 = 0
    for c, s in enumerate(g): S += [(x0, bh + (1 - bh) * r / len(s), ws[c], (1 - bh) / len(s)) for r in range(len(s))]; x0 += ws[c]
    ns = k + (band is not None and not strip)
    share = G.get("sections_by_blocks", {}).get(str(min(len(items), 7)), {}).get(str(ns))
    lab = items[wide if wide is not None else band].get("label") or items[wide if wide is not None else band]["id"] if (wide is not None or band is not None) else ""
    if strip: kind, why = "strip", f"faixa de KPIs no topo + {k} seções"
    elif band is not None: kind, why = "band", f"'{lab}' em faixa larga no topo (precisa de largura) + {k} seções abaixo; no arquivo ~23% dos slides têm faixa + colunas"
    elif wide is not None: kind, why = "wide", f"{k} seções, a de '{lab}' mais larga (é o exhibit que carrega a mensagem)"
    else: kind, why = "sections", f"{k} seções iguais (cabeçalho + 1 exhibit + no máximo 1 apoio)"
    o = build_option("cols", items, els, perm, rels, {**prof, "insights": 0}, kind,
                     why + (f"; no arquivo, {share:.0%} dos slides com {len(items)} blocos têm {ns} seções" if share else ""), slots=S)
    o["score"] = share or 0
    sp = o["spec"]; sp.pop("takeaway", None); sp["divider"] = True; sp["section_style"] = section_style(prof)
    for p in sp["panels"]: p["title_plain"] = True      # the section header marks the section; panel titles under it stay plain (exemplars 024/029)
    if band is not None: sp["band"] = {"h": bh} if strip else {"h": bh, "title": "TODO seção"}
    if strip: sp["panels"][0].pop("title", None)
    sp["cols"] = [{"w": ws[c], "rows": [0.55, 0.45][:len(s)] if len(s) > 1 else [1], "title": "TODO seção"} for c, s in enumerate(g)]
    # grey on ONE section: the one whose blocks the archive most often puts on grey (grammar grey_by_kind), if that rate is >= 20%
    gk = G.get("grey_by_kind", {}); pid = {j: f"p{perm.index(j) + 1}" for j in perm}
    rate = [sum(gk.get(gfam(els[j]), 0) for j in s) / len(s) for s in g]; c = max(range(len(g)), key=lambda x: (rate[x], x))
    if rate[c] >= .2 or not gk:
        if len(g[c]) == 2: sp["frame"] = {"panels": [pid[j] for j in g[c]], "style": "none"}
        else: next(p for p in sp["panels"] if p["id"] == pid[g[c][0]])["panel"] = "grey"
    if prof.get("decisions") == 1:      # the decision closes the last section as a conclusion callout (charts take none: then a takeaway)
        host = next((p for p in reversed([sp["panels"][perm.index(j)] for j in g[-1]]) if p["kind"] != "chart"), None)
        if host: host["callout"] = {"lead": "Conclusão:", "text": "TODO decisão recomendada"}
        else: sp["takeaway"] = "TODO: decisão recomendada"
    o["notes"].append("intro de seção é opcional (o arquivo usa em ~9% dos cabeçalhos): \"intro\" + \"intro_size\": 12 só quando o título + exhibit não dizem o ponto; insights vão no título da seção, num rótulo do gráfico ou no callout, não em bullets sob cada gráfico")
    return o


def fits(spec, slack=0.3):
    """composite.check on a TODO skeleton, tolerating text-budget overflows up to `slack` in (estimates on placeholder content; the built slide is checked strictly)."""
    return all((m := re.search(r"\(([\d.]+)in over", e)) and float(m.group(1)) <= slack for e in composite.check(spec))


def section_options(items, els, rels, prof):
    """Structurally different section layouts, ordered by the content (user ruling 2026-11-12): a hero that needs width (bridge, long series)
    -> band first; another clear hero -> wider section first; KPIs that relate to nothing -> KPI strip first; else equal sections.
    Within a kind the archive share decides; one option per kind, so the top options differ in structure."""
    n = len(items); h = hero(items, els, rels); kp = next((j for j in range(n) if els[j] == "kpis"), None)
    cand = [sections_option(items, els, rels, prof, k) for k in (2, 3, 4)] + [sections_option(items, els, rels, prof, 3, wide=h, shape="L"), sections_option(items, els, rels, prof, 4, shape="grid")]
    if h is not None: cand += [sections_option(items, els, rels, prof, k, wide=h) for k in (2, 3)] + [sections_option(items, els, rels, prof, k, band=h) for k in (2, 3)]
    if kp is not None: cand += [sections_option(items, els, rels, prof, k, band=kp) for k in (2, 3)]
    cand = [o for o in cand if o and fits(o["spec"])]
    needs_w = h is not None and (items[h]["kind"] == "bridge" or items[h].get("points", 0) >= 6)
    lone_k = kp is not None and not any(items[kp]["id"] in (r["from"], r["to"]) for r in rels)
    # order (user ruling 2026-11-12: vary the disposition): a draw weighted by how often the archive uses each disposition for this many
    # blocks (grammar dispositions_by_blocks), seeded by the message so a slide keeps its order; the content boosts what it needs
    # (a wide hero -> band, a clear hero -> wider section, KPIs related to nothing -> strip). One option per disposition first.
    D = grammar().get("dispositions_by_blocks", {}).get(str(min(n, 7)), {}); D0 = grammar().get("dispositions", {})
    def disp(o):
        k = len(o["spec"]["cols"]); return {"L": "L", "grid": "grid2x2", "band": f"band_top+cols{k}", "strip": f"band_top+cols{k}", "wide": f"cols{k}_uneq"}.get(o["strategy"], f"cols{k}")
    def weight(o):
        w = D.get(disp(o)) or D0.get(disp(o)) or 0.01
        return w * (5 if o["strategy"] == "band" and needs_w else 2 if o["strategy"] == "wide" else 3 if o["strategy"] == "strip" and lone_k else 1)
    rng = random.Random(zlib.crc32((prof.get("message") or "").encode("utf8")))
    key = {d: rng.random() ** (1 / weight(o)) for o in cand for d in [disp(o)]}      # weighted order without replacement (Efraimidis-Spirakis)
    cand = sorted(cand, key=lambda o: (-key[disp(o)], -o["score"]))
    first = list({disp(o): o for o in reversed(cand)}.values())[::-1]
    return first + [o for o in cand if o not in first]


def build_option(layout, items, els, perm, rels, prof, strategy, why, weights=None, slots=None):
    pan, byid, panels = [], {}, []
    for s, p in enumerate(perm):
        it, el = items[p], els[p]; pid = f"p{s + 1}"; byid[it["id"]] = pid
        pan.append(_panel(pid, it, el)); panels.append({"id": pid, "item": it["id"], "kind": ELEMENTS[el][0], "element": el, "fit": fit(it, el)})
    S = slots or SLOTS[layout]; pos ={byid[items[p]["id"]]: S[s] for s, p in enumerate(perm)}; pk = {p["id"]: p for p in pan}
    links, notes = [], []
    for r in rels:
        a, b = byid.get(r["from"]), byid.get(r["to"])
        if not a or not b: continue
        t = r["type"]; ca = pk[a]
        if t in ("leads_to", "located_in") or (t == "zooms_into" and not any(l["kind"] == "arrow" and l["from"] == a for l in links)):
            if adjacent(pos[a], pos[b]): links.append({"kind": "arrow", "from": a, "to": b})
        if t == "zooms_into" and ca["kind"] == "chart" and ca["chart"]["kind"] not in ("line", "pie", "doughnut") and not any(l["kind"] == "highlight" and l["panel"] == a for l in links):
            links.append({"kind": "highlight", "panel": a, "categories": [0], "label": "TODO"})
        if t == "explains":
            if ca["kind"] in ("bullets", "cards") and pk[b]["kind"] == "chart": links.append({"kind": "xref", "panel": a, "to": b, "pairs": [[0, 0]]})
            elif pk[b]["kind"] == "chart": links.append({"kind": "callout", "panel": b, "category": 0, "text": "TODO"})
            elif adjacent(pos[a], pos[b]): links.append({"kind": "arrow", "from": a, "to": b})
        if t == "compares": notes.append(f"{a} vs {b}: same unit and axis scale (set major_unit / max_height_in equal on both)")
    srcs = {}
    for r in rels:
        if r["type"] == "sums_to" and r["from"] in byid and r["to"] in byid: srcs.setdefault(byid[r["to"]], []).append(byid[r["from"]])
    for to, fr in srcs.items():
        links.append({"kind": "bracket", "from": fr[:3], "to": to, "label": "TODO"} if len(fr) > 1 else {"kind": "arrow", "from": fr[0], "to": to})
    # insights -> bullets under the main exhibit; decisions -> numbered cards (+xref) already added as an item by the caller
    n_ins = min(prof.get("insights", 0), 4)
    host = next((p for p in sorted(pan, key=lambda p: -pos[p["id"]][2] * pos[p["id"]][3]) if p["kind"] not in ("bullets", "cards")), None)
    if host and n_ins:                     # ponytail: bullet capacity by slot area (half slot ~2, quarter slot ~1), tuned to composite.check's text budget
        a = pos[host["id"]][2] * pos[host["id"]][3]; cap = 4 if a >= .5 else 2 if a >= .3 else 1
        if n_ins > cap: notes.append(f"só {cap} insight(s) cabem sob o gráfico neste layout; o resto vai em cartões/bullets de outro painel ou no takeaway")
        n_ins = min(n_ins, cap)
    if n_ins and host and host["kind"] == "flow": host["callout"] = {"lead": "TODO risco:", "text": "TODO insight + número"}   # flow panels take a callout, not bullets (schema)
    elif n_ins and host: host["bullets"] = [f"**TODO insight {i + 1}:** ==palavra-chave== + número" for i in range(n_ins)]
    for p in pan:       # payback on a negative-then-positive series: dotted note in the empty top-left corner (bars there are negative)
        it = next(x for x in items if byid[x["id"]] == p["id"])
        if it.get("payback") and p["kind"] == "chart": links.append({"kind": "note", "panel": p["id"], "text": "TODO: payback em X anos", "at": "top-left"})
    spec = {"type": "composite", "lang": prof.get("lang", "pt"), "headline": (prof.get("message") or "TODO: título de ação com número")[:170],
            "layout": layout, "panels": pan, "source": "TODO"}
    if weights: spec["weights"] = weights
    if links: spec["links"] = links
    if prof.get("decisions") == 1: spec["takeaway"] = "TODO: decisão recomendada"
    return {"layout": layout, "strategy": strategy, "panels": panels, "links": links, "notes": notes, "why": why, "spec": spec}


# ---- density -------------------------------------------------------------------------------------------
def est_words(it):
    # ponytail: words per element are rough label/cell counts (chart: 8 + 2.5/point + 2/series); text uses the given word count.
    p, s = it.get("points", 0), max(it.get("series", 1), 1); k = it["kind"]
    if it.get("words"): return it["words"]
    if k in ("list", "text"): return 18 * max(p, 1)
    if k in ("lookup_table", "comparison") and (it.get("qualitative") or k == "lookup_table"): return 2 * p * max(it.get("series", 2), 2)
    return {"kpi": 8 * p, "breakdown": 4 * p + 6, "assumptions": 6 * p, "process": 14 * p, "matrix": 40, "geo": 30}.get(k, 8 + p * (1 + .5 * s) + 2 * s)


def est_fill(it, el):                     # fraction of its slot an element fills (ponytail: heuristic, calibrated so a 6-point chart ~ .9)
    p = it.get("points", 3); w = it.get("words", 0)
    return min(1, {"table": .25 + .14 * p, "table_pills": .3 + .14 * p, "flow": .45 + .06 * p, "kpis": .4, "bullets": max(w, 18 * p) / 90, "cards": .3 + .2 * p, "process": .5 + .1 * p}.get(el, .4 + .08 * p))


def density(prof, items, els):
    words = 18 + 20 + sum(est_words(i) for i in items) + 25 * prof.get("insights", 0) + 30 * prof.get("decisions", 0)
    fills = [est_fill(i, e) for i, e in zip(items, els)] + [.5] * (prof.get("insights", 0) > 0)
    cov = .85 * sum(fills) / max(len(fills), 1)          # ponytail: .85 = body area ceiling seen in the archive (p90 of area_covered ~ .85)
    thin = words < ARCH_WORDS["p25"] or (cov < ARCH_COVER["p25"] and words < ARCH_WORDS["median"])     # low coverage alone is not thin: small extras (KPIs, a short list) pull the fill average down
    est = {"words": round(words), "coverage": round(cov, 2), "archive_median_words": ARCH_WORDS["median"], "archive_p25_words": ARCH_WORDS["p25"], "archive_p25_coverage": ARCH_COVER["p25"]}
    if thin:
        m = {"pt": f"Os dados podem deixar o slide menos denso que o normal para este tipo de caso (~{round(words)} palavras estimadas; mediana do arquivo {ARCH_WORDS['median']}, 25% dos slides ficam abaixo de {ARCH_WORDS['p25']}). Opções que cabem nesta quantidade de dados abaixo.",
             "en": f"The data may make this slide less dense than usual for this kind of case (~{round(words)} estimated words; archive median {ARCH_WORDS['median']}, 25% of slides are below {ARCH_WORDS['p25']}). Options that fit this amount of data below."}
    else:
        m = {"pt": f"Densidade ok (~{round(words)} palavras, mediana do arquivo {ARCH_WORDS['median']}).", "en": f"Density ok (~{round(words)} words, archive median {ARCH_WORDS['median']})."}
    return ("thin" if thin else "ok"), m, est


# ---- archive examples ----------------------------------------------------------------------------------
_ARCH = None


def _norm(e):
    v = e.get("vision") or {}
    k = f"{v['kind']}:{v.get('sub')}" if v else e["kind"] + ":" + str(e.get("sub", "")).replace(" (drawn/image)", "")
    if e["kind"] == "table" or k.startswith("table"): return "table"
    if k.startswith("chart:"):
        s = k[6:]
        return "stacked" if "stacked" in s and "100" not in s else "stacked100" if "100" in s else "line" if s.startswith("line") else "doughnut" if s in ("pie", "doughnut") else "waterfall" if s == "waterfall" else "column"
    if k.startswith("cards") or (e["kind"] == "cluster" and e.get("sub") in ("row", "column", "grid")): return "cards"
    if k.startswith("map"): return "map_br"
    if k.startswith("diagram:process") or k.startswith("diagram:flow"): return "process"
    if k.startswith("diagram:matrix"): return "matrix"
    return "text_block" if k.startswith("text_block") else "other"


def archive():
    global _ARCH
    if _ARCH is None:
        _ARCH = []
        if ARCHIVE.exists():
            for line in open(ARCHIVE, encoding="utf8"):
                x = json.loads(line)
                if not x["is_content"]: continue
                d = {e["id"]: e for e in x["elements"]}
                _ARCH.append({"deck": Path(x["deck"]).stem, "path": x["deck"], "slide": x["slide"], "layout": ARCH_LAYOUT_ALIAS.get(x["layout"], x["layout"]),
                              "kinds": [_norm(d[i]) for i in x["exhibits"] if i in d], "words": x["density"]["words"], "links": bool(x["links"]),
                              "cov": x["density"]["area_covered"]})
    return _ARCH


def examples(opt, k=3):
    want = ["table" if p["element"] == "table_pills" else "process" if p["element"] == "flow" else p["element"] if p["element"] in ("waterfall", "stacked", "stacked100", "line", "column", "doughnut", "table", "cards", "map_br", "process", "matrix") else "column" if p["element"] in ("bar", "scatter", "bubble") else "text_block" for p in opt["panels"]]
    sc = []
    for a in archive():
        s = 3 * (a["layout"] == opt["layout"]) + .5 * (a["links"] and bool(opt["links"])) - .5 * abs(len(a["kinds"]) - len(want)) - abs(a["words"] - ARCH_WORDS["median"]) / 300
        rest = list(a["kinds"])
        for w in want:
            if w in rest: s += 1.5; rest.remove(w)
            elif w in ("column", "stacked", "stacked100", "line", "waterfall") and any(r in ("column", "stacked", "stacked100", "line", "waterfall") for r in rest): s += .5
        sc.append((s, a))
    out, decks = [], set()
    for s, a in sorted(sc, key=lambda t: -t[0]):
        if a["deck"] in decks: continue
        decks.add(a["deck"]); out.append({"ref": f"slide {a['slide']} do deck {a['deck']}", "deck": a["deck"], "slide": a["slide"], "layout": a["layout"], "exhibits": a["kinds"], "words": a["words"], "score": round(s, 1)})
        if len(out) == k: break
    return out


# ---- main ----------------------------------------------------------------------------------------------
def _thin_options(prof, items, els, rels):
    """Options for little data: bigger single exhibit + KPI strip / exhibit + raw-numbers table / exhibit + insight cards."""
    cand = [(i, e) for i, e in zip(items, els) if e not in ("bullets", "cards")]
    if not cand: return []
    base, bel = max(cand, key=lambda t: t[0].get("points", 0) * max(t[0].get("series", 1), 1)); out = []
    pts, ser = base.get("points", 3), max(base.get("series", 1), 1)
    kp = {"id": "k", "kind": "kpi", "points": 3, "label": "Indicadores-chave"}
    tb = {"id": "t", "kind": "lookup_table", "points": pts, "series": ser + 1, "label": "Números de base"}
    cd = {"id": "c", "kind": "list", "titled": True, "points": max(2, min(prof.get("insights", 0) or 3, 5)), "label": "Leituras"}
    for name, other, lay, w, why in (
            ("kpi_strip", kp, "T|B", [.3, .7], "um exhibit grande com tira de 3 KPIs (último valor, variação, CAGR/média) em cima"),
            ("raw_table", tb, "2col", [.62, .38], "o exhibit mais a tabela dos números de base (mais denso, auditável)"),
            ("insight_cards", cd, "2col", [.6, .4], "o exhibit mais cartões com as leituras (xref numerado ao gráfico)")):
        its = [other, base] if name == "kpi_strip" else [base, other]; es = [pick_element(other), bel] if name == "kpi_strip" else [bel, pick_element(other)]
        opt = build_option(lay, its, es, (0, 1), [], dict(prof, insights=prof.get("insights", 0) if name != "insight_cards" else 0), name, why, w)
        if name == "insight_cards":
            sp = opt["spec"]; sp["panels"][1].update(numbered=True)
            if sp["panels"][0]["kind"] == "chart": opt["links"].append({"kind": "xref", "panel": "p2", "to": "p1", "pairs": [[i, min(i, pts - 1)] for i in range(min(len(sp["panels"][1]["items"]), pts))]}); sp["links"] = opt["links"]
        if name == "raw_table" and base.get("kind") != "bridge": opt["links"].append({"kind": "arrow", "from": "p1", "to": "p2"}); opt["spec"]["links"] = opt["links"]
        out.append(opt)
    return out


def _count(v, default=0):
    """Profiles written by an AI often pass the texts/values themselves instead of counts: list -> len, "3" -> 3."""
    if isinstance(v, (list, tuple, dict)): return len(v)
    try: return int(float(v))
    except (TypeError, ValueError): return default


def _normalize(prof):
    p = dict(prof)
    for k in ("insights", "decisions"): p[k] = _count(p.get(k, 0))
    items = []
    for it in p.get("items", []):
        it = dict(it)
        if it.get("kind") == "assumptions": it.update(kind="lookup_table", sourced=True)
        if isinstance(it.get("parts"), (list, tuple)) and "points" not in it: it["points"] = len(it["parts"])
        if "points" not in it and isinstance(it.get("values"), (list, tuple)): it["points"] = len(it["values"])
        for k, d in (("points", 0), ("series", 1), ("words", 0)):
            if k in it: it[k] = _count(it[k], d)
        items.append(it)
    p["items"] = items
    return p


def suggest(prof, nearest=True):
    prof = _normalize(prof)
    items = [dict(i) for i in prof["items"]]; rels = prof.get("relations", [])
    if prof.get("decisions", 0) >= 2:      # decisions -> numbered cards panel, xref'd to the main chart
        items.append({"id": "_dec", "kind": "cards", "points": min(prof["decisions"], 5), "label": "Decisões"})
        main = next((i for i in items if pick_element(i) in BIG), None)
        if main: rels = rels + [{"from": "_dec", "to": main["id"], "type": "explains"}]
    els = [pick_element(i) for i in items]
    dens, msg, est = density(prof, items, els)
    dropped = []
    if len(items) > 6:                      # ponytail: composite has max 6 slots (2x3); keep the 6 heaviest, the rest become insights/bullets
        w = sorted(range(len(items)), key=lambda j: -est_words(items[j]) - 10 * (els[j] in BIG))[:6]; keep = sorted(w)
        dropped = [items[j]["id"] for j in range(len(items)) if j not in keep]; items = [items[j] for j in keep]; els = [els[j] for j in keep]
        rels = [r for r in rels if r["from"] in {i["id"] for i in items} and r["to"] in {i["id"] for i in items}]
    n = len(items); sh = shape(n, rels); opts = []
    if dens == "thin": opts = _thin_options(prof, items, els, rels)
    if not opts:
        cands = []
        for lay, S in SLOTS.items():
            if len(S) != n: continue
            perm, rs = place(lay, items, els, rels)
            base = SHAPE_FIT.get(lay, {}).get(sh, 1)
            cands.append((base + 12 * LAYOUT_SHARE.get(lay, 0) + rs / 4, lay, perm))
        for sc, lay, perm in sorted(cands, key=lambda c: -c[0]):
            why = f"forma '{sh}' das relações cabe em {lay} (arquivo: {round(100 * LAYOUT_SHARE.get(lay, 0))}% dos slides usam este layout)"
            o = build_option(lay, items, els, perm, rels, prof, "standard", why); o["score"] = round(sc, 2); opts.append(o)
        if 4 <= n <= 6: opts[:0] = section_options(items, els, rels, prof)      # user rulings 2026-11-12: dense, not crammed; layout variety from the content
        ok = [o for o in opts if (fits(o["spec"]) if o["strategy"] in ("sections", "wide", "band", "strip") else not composite.check(o["spec"]))]      # drop layouts whose slots are too small for the panels (composite's own text-budget check)
        opts = (ok or opts)[:3]
    for r, o in enumerate(opts, 1):
        o["rank"] = r; o["examples"] = examples(o)
        if dropped: o["notes"].append(f"itens fora (máx. 6 painéis): {dropped} -> viram insights/bullets")
    res = {"message": prof.get("message"), "relation_shape": sh, "density": dens, "density_message": msg, "estimate": est, "options": opts}
    if nearest and opts:                    # retrieve-and-edit: closest archive slides + ready specs to the top option
        import retrieve; res["nearest"] = retrieve.nearest(opts[0])
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    print(json.dumps(suggest(json.loads(Path(sys.argv[1]).read_text(encoding="utf8"))), ensure_ascii=False, indent=1))
