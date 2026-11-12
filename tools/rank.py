"""Best-of-N ranking: build 2-3 candidate specs, measure, order them. Claude still picks visually from the renders.
usage: py -3 -I tools/rank.py a.json b.json [c.json]      (MCP: rank_candidates)
score (lower = better) = structure distance to the nearest archive slides (min over top 3) + .05 per metric outside archive p10-p90 + .1 per build warning.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import build, layout_metrics as lm, retrieve                  # noqa: E402

OUT = ROOT / "out" / "rank"


def _archive_els(wanted):
    """{(deck, slide): elements} for the wanted archive slides, from analysis/elements.jsonl."""
    got = {}
    for ln in open(ROOT / "analysis" / "elements.jsonl", encoding="utf8"):
        r = json.loads(ln)
        if (r["deck"], r["slide"]) in wanted: got[(r["deck"], r["slide"])] = r["elements"]
    return got


def rank(specs, names=None, out_dir=OUT):
    stats = json.loads((ROOT / "analysis" / "layout_stats.json").read_text("utf8"))
    names = names or [chr(65 + i) for i in range(len(specs))]; Path(out_dir).mkdir(parents=True, exist_ok=True)
    near = [retrieve.nearest(s, 3)["archive"] for s in specs]
    els = _archive_els({(a["deck"], a["slide"]) for n in near for a in n})
    res = []
    for s, n, nb in zip(specs, names, near):
        path = Path(out_dir) / f"cand_{n}.pptx"; warns = []
        errs = build.build_specs([build.resolve_excel(dict(s), ROOT)], str(path), warnings=warns)
        if errs: res.append({"name": n, "score": 99, "errors": errs, "reason": f"{n}: does not build: {errs[0][:120]}"}); continue
        g = lm.metrics(*lm.pptx_slide_els(str(path)))
        d = min(((lm.distance(g, lm.metrics(els[(a["deck"], a["slide"])]))["structure_distance"], a) for a in nb if (a["deck"], a["slide"]) in els), key=lambda t: t[0], default=(1, None))
        out = [k for k in lm.DIST if k in stats and not stats[k]["p10"] <= g[k] <= stats[k]["p90"]]
        sc = d[0] + .05 * len(out) + .1 * len(warns)
        ref = f"{Path(d[1]['deck']).stem} s{d[1]['slide']}" if d[1] else "none"
        res.append({"name": n, "pptx": str(path), "score": round(sc, 3), "structure_distance": d[0], "nearest_archive": ref, "metrics_outside_p10_p90": out,
                    "warnings": warns, "metrics": {k: g[k] for k in lm.DIST},
                    "reason": f"{n}: distance {d[0]:.2f} to {ref}; {len(out)} metrics outside archive p10-p90" + (f" ({', '.join(out)})" if out else "") + f"; {len(warns)} warnings"})
    return sorted(res, key=lambda r: (r["score"], r["name"]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    for r in rank([json.loads(Path(f).read_text("utf8")) for f in sys.argv[1:]], [Path(f).stem for f in sys.argv[1:]]): print(f"{r['score']:.3f}  {r['reason']}")
