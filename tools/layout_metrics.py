"""Structural layout metrics for a slide (generated .pptx or archive original) + distance generated-vs-original.
usage: py -3 -I tools/layout_metrics.py gen.pptx [--slide N] [--vs <deck.pptx>:<slide> | --vs-id s03]
       py -3 -I tools/layout_metrics.py --archive-stats      -> analysis/layout_stats.json (p10/p50/p90 over content slides)
Elements come from tools/mine_elements.mine_slide (groups flattened with transforms, inches). PDF originals: PyMuPDF
text blocks + drawings + images mapped to the same element dicts.
Distance = weighted mean over DIST of min(1, |gen-orig| / scale); weights/scales below. 0 = same structure, 1 = max different.
"""
import sys, os, json, importlib.util
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("mine_elements", os.path.join(ROOT, "tools", "mine_elements.py"))
me = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(me)

W0, H0 = 13.333, 7.5
SKIP_SUB = {"background", "divider"}


def _leaf(e):
    return e["kind"] not in ("cluster", "connector") and e.get("sub") not in SKIP_SUB and e["bbox"][2] > 0.1 and e["bbox"][3] > 0.1


def _inter(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return max(w, 0) * max(h, 0)


def _distinct(vals, tol=0.05):
    n, last = 0, None
    for v in sorted(vals):
        if last is None or v - last > tol:
            n += 1
        last = v
    return n


EDGES = (lambda b: b[0], lambda b: b[1], lambda b: b[0] + b[2])


def _al(bb, f, tol=0.05):
    if len(bb) < 2:
        return 0.0
    v = [f(b) for b in bb]
    return sum(any(j != i and abs(x - y) <= tol for j, y in enumerate(v)) for i, x in enumerate(v)) / len(v)


def metrics(els, W=W0, H=H0):
    els = [e for e in els if _leaf(e)]
    title = next((e for e in els if e["kind"] == "text" and e.get("role") == "title"), None)
    top = min(title["bbox"][1] + title["bbox"][3] + 0.1, 2.0) if title else 1.0
    # ponytail: fixed body zone, not the template's real one
    barea = (W - 0.8) * max(H - 0.45 - top, 1)
    ov = 0.0
    for i, a in enumerate(els):
        for b in els[i + 1:]:
            x = _inter(a["bbox"], b["bbox"])
            if x <= 0:
                continue
            small = min(a["bbox"][2] * a["bbox"][3], b["bbox"][2] * b["bbox"][3])
            ca = a["kind"] == "shape" and not a.get("has_text")
            cb = b["kind"] == "shape" and not b.get("has_text")
            # ponytail: overlap inside a text-less shape (panel/frame/card) or shape-on-shape >=80% contained = intended
            if (ca or cb) and x >= 0.8 * small:
                continue
            if a["kind"] == "shape" and b["kind"] == "shape" and x >= 0.8 * small:
                continue
            ov += x
    bb = [e["bbox"] for e in els]
    out = dict(n_boxes=len(els), overlap=round(ov / barea, 4))
    for nm, f in zip(("left", "top", "right"), EDGES):
        out["align_" + nm] = round(_al(bb, f), 3)
    out["align_any"] = round(sum(any(abs(f(a) - f(c)) <= 0.05 for j, c in enumerate(bb) if j != i for f in EDGES)
                                 for i, a in enumerate(bb)) / len(bb), 3) if len(bb) > 1 else 0.0
    nb = [e["bbox"] for e in els if e.get("role") != "title"] or bb
    out["margin_left"] = round(min(b[0] for b in bb), 2) if bb else 0
    out["margin_right"] = round(W - max(b[0] + b[2] for b in bb), 2) if bb else 0
    out["margin_conform"] = round(sum(0.3 <= b[0] and b[0] + b[2] <= W - 0.3 and b[1] >= 0.2 and b[1] + b[3] <= H - 0.2
                                      for b in bb) / len(bb), 3) if bb else 0
    out["x_starts"] = _distinct([b[0] for b in nb])
    words = sum(e.get("words", 0) for e in els if e["kind"] == "text" or e.get("has_text"))
    out["words"] = words
    out["words_per_sqin"] = round(words / barea, 3)
    sizes = [(s, max(e.get("words", 1), 1)) for e in els if e["kind"] == "text" and e.get("role") != "title"
             for s in e.get("font_sizes", [])]
    out["font_sizes_distinct"] = len({s for e in els for s in e.get("font_sizes", [])})
    out["font_min_body"] = min((s for s, _ in sizes), default=0)
    flat = sorted(s for s, w in sizes for _ in range(w))
    out["font_median_body"] = flat[len(flat) // 2] if flat else 0
    kinds = {}
    for e in els:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    out["kinds"] = kinds
    lr = sum(max(0, min(b[0] + b[2], W / 2) - b[0]) * b[3] for b in bb)
    rr = sum(max(0, b[0] + b[2] - max(b[0], W / 2)) * b[3] for b in bb)
    tr = sum(max(0, min(b[1] + b[3], H / 2) - b[1]) * b[2] for b in bb)
    br = sum(max(0, b[1] + b[3] - max(b[1], H / 2)) * b[2] for b in bb)
    out["balance_lr"] = round((lr - rr) / (lr + rr), 3) if lr + rr else 0   # -1 all ink left .. +1 all right
    out["balance_tb"] = round((tr - br) / (tr + br), 3) if tr + br else 0
    # ponytail: summed box area, overlaps double counted
    out["ink_cover"] = round(min(1, sum(b[2] * b[3] for b in bb) / (W * H)), 3)
    return out


def pptx_slide_els(path, n=1):
    from pptx import Presentation
    prs = Presentation(path)
    W, H = me.inch(prs.slide_width), me.inch(prs.slide_height)
    return me.mine_slide(prs.slides[n - 1], W, H)["elements"], W, H


def pdf_els(path, n):
    import fitz
    pg = fitz.open(path)[n - 1]
    s = W0 / pg.rect.width
    H = pg.rect.height * s
    els = []
    for b in pg.get_text("dict")["blocks"]:
        bx = [v * s for v in b["bbox"]]
        bb = [bx[0], bx[1], bx[2] - bx[0], bx[3] - bx[1]]
        if b["type"] == 1:
            els.append(dict(kind="picture", sub="picture", bbox=bb))
            continue
        sp = [(x["size"] * s * 72, len(x["text"].split())) for ln in b["lines"] for x in ln["spans"]]
        w = sum(x for _, x in sp)
        if w:
            els.append(dict(kind="text", sub="body", role="body", words=w, font_sizes=sorted({round(z, 1) for z, _ in sp}), bbox=bb))
    for d in pg.get_drawings():
        r = d["rect"]
        x0, y0 = max(r.x0 * s, 0), max(r.y0 * s, 0)   # clamp off-slide bleed
        bb = [x0, y0, min(r.x1 * s, W0) - x0, min(r.y1 * s, H) - y0]
        if bb[2] > 0.1 and bb[3] > 0.1 and len(d.get("items", [])) <= 4 and bb[2] * bb[3] < 0.9 * W0 * H:
            els.append(dict(kind="shape", sub="plain" if d.get("fill") else "frame", has_text=False, bbox=bb))
    # ponytail: title = top-most text block in the top 25% with >=5 words; PDF font sizes are scaled to a 13.33in slide
    t = [e for e in els if e["kind"] == "text" and e["bbox"][1] < 0.25 * H and e["words"] >= 5]
    if t:
        min(t, key=lambda e: e["bbox"][1])["role"] = "title"
    return els, W0, H


def load_orig(spec):
    deck, n = spec.rsplit(":", 1)
    n = int(n)
    if deck.lower().endswith(".pdf"):
        return pdf_els(deck, n)
    return pptx_slide_els(deck if os.path.isabs(deck) else os.path.join(ROOT, "archive", deck), n)


def orig_by_id(i):
    r = next(x for x in json.load(open(os.path.join(ROOT, "analysis", "ai_audit", "originals.json"), encoding="utf8")) if x["id"] == i)
    return load_orig(f'{r["deck"]}:{r["slide"]}')


# metric -> (weight, scale = delta that counts as "fully different"). ponytail: hand-set; refit from layout_stats.json spreads.
DIST = dict(overlap=(2, 0.05), align_any=(2, 0.5), margin_conform=(1, 0.5), margin_left=(1, 0.6), x_starts=(1.5, 6), words=(2, 150),
            words_per_sqin=(1, 2), font_sizes_distinct=(1, 4), font_min_body=(1.5, 6), font_median_body=(1.5, 6), n_boxes=(1.5, 30),
            balance_lr=(1, 0.5), balance_tb=(1, 0.5), ink_cover=(1, 0.3))


def distance(g, o):
    deltas = {k: round(g[k] - o[k], 3) for k in DIST}
    norm = {k: min(1.0, abs(v) / DIST[k][1]) for k, v in deltas.items()}
    d = sum(DIST[k][0] * norm[k] for k in DIST) / sum(w for w, _ in DIST.values())
    return dict(structure_distance=round(d, 3), deltas=deltas, normalized={k: round(v, 2) for k, v in norm.items()},
                kinds_gen=g["kinds"], kinds_orig=o["kinds"])


def archive_stats():
    rows = []
    for ln in open(os.path.join(ROOT, "analysis", "elements.jsonl"), encoding="utf8"):
        r = json.loads(ln)
        if r.get("is_content") and r["elements"]:
            rows.append(metrics(r["elements"]))   # ponytail: assumes 13.33x7.5 slides
    st = {}
    for k in DIST:
        v = sorted(r[k] for r in rows)
        q = lambda p: v[min(len(v) - 1, int(p * (len(v) - 1) + 0.5))]
        st[k] = dict(p10=q(.1), p50=q(.5), p90=q(.9))
    st["_n_slides"] = len(rows)
    json.dump(st, open(os.path.join(ROOT, "analysis", "layout_stats.json"), "w"), indent=1)
    return st


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--archive-stats" in a:
        print(json.dumps(archive_stats(), indent=1))
        sys.exit()
    n = int(a[a.index("--slide") + 1]) if "--slide" in a else 1
    g = metrics(*pptx_slide_els(a[0], n))
    res = dict(generated=g)
    o = None
    if "--vs" in a:
        o = metrics(*load_orig(a[a.index("--vs") + 1]))
    if "--vs-id" in a:
        o = metrics(*orig_by_id(a[a.index("--vs-id") + 1]))
    if o:
        res.update(original=o, distance=distance(g, o))
    print(json.dumps(res, indent=1, ensure_ascii=False))
