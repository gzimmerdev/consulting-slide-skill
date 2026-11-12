"""Retrieve-and-edit helper: closest archive slides + closest ready-made specs for a profile or spec.
usage: py -3 tools/retrieve.py profile_or_spec.json [k]      (MCP: find_similar, save_exemplar)
Similarity = feature overlap (layout, panel element kinds, panel count, links); no ML. Archive side = analysis/elements_labeled.jsonl
(via compose.archive); spec side = examples/*.json (type composite) + exemplars/ (approved slides: <id>.json + <id>.png + index.json).
"""
import json, re, shutil, sys, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
import compose, make_crops                                  # noqa: E402

EXEMPLARS = ROOT / "exemplars"
PRIVATE = ROOT / "private"      # local only (gitignored): exemplars rebuilt from other teams' slides, real deck names
NAMES = json.loads((PRIVATE / "deck_names.json").read_text("utf8")) if (PRIVATE / "deck_names.json").exists() else {}
CHARTY = {"column", "stacked", "stacked100", "line", "waterfall"}
NORM = {"bar": "column", "scatter": "column", "bubble": "column", "pie": "doughnut", "bullets": "text_block", "kpis": "text_block"}


def features(spec):
    """spec (or compose option, which carries a spec) -> (layout, [element kinds], has_links)."""
    spec = spec.get("spec", spec)
    kinds = [NORM.get(k, k) for k in ((p["chart"]["kind"] if p["kind"] == "chart" else p["kind"]) for p in spec.get("panels", []))]
    return spec.get("layout", "1"), kinds, bool(spec.get("links"))


def _score(want, have, words=None):
    s = 3 * (want[0] == have[0]) + .5 * (want[2] and have[2]) - .5 * abs(len(want[1]) - len(have[1]))
    rest = list(have[1])
    for w in want[1]:
        if w in rest: s += 1.5; rest.remove(w)
        elif w in CHARTY and any(r in CHARTY for r in rest): s += .5
    return s - (abs(words - compose.ARCH_WORDS["median"]) / 300 if words else 0)


def _image(deck, slide):
    """Existing PNG of an archive slide (audit originals, then make_crops crops) or how to export one."""
    deck = NAMES.get(Path(deck).stem, deck); name = Path(deck).name      # anonymised deck code -> real path (private/deck_names.json, local only)
    orig = ROOT / "analysis/ai_audit/originals.json"
    for r in json.loads(orig.read_text("utf8")) if orig.exists() else []:
        if Path(r["deck"]).name == name and r["slide"] == slide and Path(r["png"]).exists(): return r["png"], None
    crop = ROOT / "analysis/crops/slides" / f"{make_crops.slug(deck)}_{slide:02d}.png"      # body-area crop only
    if crop.exists(): return str(crop), None
    if not (ROOT / "archive" / deck).exists(): return None, "not available in this copy (the archive decks are not shared): check density and styling against the nearest specs/exemplars instead"
    png = ROOT / "analysis/nearest" / f"{make_crops.slug(deck)}_{slide:02d}.png"
    job = [{"deck": str(ROOT / "archive" / deck), "slides": [{"n": slide, "png": str(png)}]}]
    return None, f"export: write {json.dumps(job)} to a jobs.json, run powershell -NoProfile -File tools/export_slides.ps1 jobs.json"


def _spec_files():
    for f in sorted((ROOT / "examples").glob("*.json")):
        try: s = json.loads(f.read_text("utf8"))
        except ValueError: continue
        if isinstance(s, dict) and s.get("type") == "composite": yield str(f), s, None
    for d in (EXEMPLARS, PRIVATE / "exemplars"):
        idx = d / "index.json"
        for e in json.loads(idx.read_text("utf8")) if idx.exists() else []:
            yield str(d / f"{e['id']}.json"), json.loads((d / f"{e['id']}.json").read_text("utf8")), e


def nearest(x, k=3):
    """x = content profile (has "items"), compose option or spec -> {"archive": [...], "specs": [...]} (k each, best first)."""
    if "items" in x: x = compose.suggest(x, nearest=False)["options"][0]
    want = features(x); out = {"archive": [], "specs": []}; seen = set()
    for a in sorted(compose.archive(), key=lambda a: -_score(want, (a["layout"], a["kinds"], a["links"]), a["words"])):
        if a["deck"] in seen: continue                     # one slide per deck
        seen.add(a["deck"]); png, how = _image(a["path"], a["slide"])
        out["archive"].append({"deck": a["path"], "slide": a["slide"], "layout": a["layout"], "exhibits": a["kinds"], "words": a["words"],
                               "summary": f"layout {a['layout']}, {len(a['kinds'])} exhibits ({', '.join(a['kinds']) or '-'}), {a['words']} words" + (", links" if a["links"] else ""),
                               "png": png, **({"how_to_get_image": how} if how else {})})
        if len(out["archive"]) == k: break
    sc = [(_score(want, features(s)), f, s, e) for f, s, e in _spec_files()]
    for s, f, spec, e in sorted(sc, key=lambda t: (-t[0], t[1]))[:k]:
        lay, kinds, links = features(spec); png = Path(f).with_suffix(".png")
        out["specs"].append({"path": f, "score": round(s, 1), "layout": lay, "panels": kinds, "links": links, "headline": spec.get("headline", ""),
                             "exemplar": bool(e), "note": e["note"] if e else "", "png": str(png) if png.exists() else None})
    return out


def save_exemplar(spec, png_path, note="", dir=EXEMPLARS):
    """Add an approved slide to exemplars/ (spec json + png + index.json). Returns its id."""
    dir = Path(dir); dir.mkdir(parents=True, exist_ok=True)
    idx = dir / "index.json"; ents = json.loads(idx.read_text("utf8")) if idx.exists() else []
    base = re.sub(r"[^a-z0-9]+", "-", spec.get("headline", "slide").lower()).strip("-")[:40] or "slide"
    taken = [e["id"] for d_ in {dir, PRIVATE / "exemplars"} if (d_ / "index.json").exists() for e in json.loads((d_ / "index.json").read_text("utf8"))]
    id_ = f"{base}-{max([int(i[-3:]) for i in taken if i[-3:].isdigit()] + [0]) + 1:03d}"      # next number after the highest, shared + private (ids stay unique when files move)
    (dir / f"{id_}.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), "utf8")
    if png_path and Path(png_path).exists(): shutil.copy(png_path, dir / f"{id_}.png")
    ents.append({"id": id_, "note": note, "date": datetime.date.today().isoformat()})
    idx.write_text(json.dumps(ents, ensure_ascii=False, indent=1), "utf8")
    return id_


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf8")
    print(json.dumps(nearest(json.loads(Path(sys.argv[1]).read_text("utf8")), int(sys.argv[2]) if len(sys.argv) > 2 else 3), ensure_ascii=False, indent=1))
