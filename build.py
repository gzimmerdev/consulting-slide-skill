"""CLI: py -3 build.py spec.json -o out.pptx [--theme bain_red] [--primary HEX] [--font NAME] [--heading-font NAME]

spec.json = one spec (one slide), a list of specs, or {name: spec} (one slide each, in order).
Validates every spec (JSON Schema + cross-field rules), then builds native, editable slides.
"""
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator
from slidegen.core import new_deck, blank, load_theme, themes, LogoError
from slidegen import chart_slides, text_slides, table_slides, diagram_slides, structure_slides, composite

ROOT = Path(__file__).parent
BUILDERS = {**structure_slides.BUILDERS, **text_slides.BUILDERS, **chart_slides.BUILDERS,
            **table_slides.BUILDERS, **diagram_slides.BUILDERS, **composite.BUILDERS}


def _chart_errs(c, where):
    e = []
    if c["kind"] in ("scatter", "bubble"):        # XY charts: points instead of categories/values
        from slidegen.charts import xy_series
        if not c.get("series") and not c.get("points"): return [f"{where}: {c['kind']} needs 'points' or 'series'"]
        ser = xy_series(c)
        if c["kind"] == "bubble": e += [f"{where}: bubble point {j} in '{n}' has no 'size'" for n, pts in ser for j, q in enumerate(pts) if "size" not in q]
        if c.get("highlight") and len(ser) > 1: e.append(f"{where}: 'highlight' only works with a single series")
        if any(k >= len(ser[0][1]) for k in c.get("highlight") or []): e.append(f"{where}: 'highlight' index outside points")
        qd = c.get("quadrants") or {}
        if qd.get("labels") and len(qd["labels"]) != 4: e.append(f"{where}: quadrants.labels needs 4 texts (top-left, top-right, bottom-left, bottom-right)")
        return e
    for s in c["series"]:
        if len(s["values"]) != len(c["categories"]):
            e.append(f"{where}: series '{s['name']}' has {len(s['values'])} values but {len(c['categories'])} categories")
    if c.get("highlight") and len(c["series"]) > 1: e.append(f"{where}: 'highlight' only works with a single series")
    if any(k >= len(c["categories"]) for k in c.get("highlight") or []): e.append(f"{where}: 'highlight' index outside categories")
    return e


def check(spec):
    """Rules JSON Schema can't express. Returns a list of error strings."""
    t, e = spec["type"], []
    if t == "chart_takeaway": e += _chart_errs(spec["chart"], "chart")
    if t == "multi_chart":
        for i, p in enumerate(spec["panels"]): e += _chart_errs(p["chart"], f"panels/{i}/chart")
    if t == "composite":
        for p in spec["panels"]:
            if p["kind"] == "chart": e += _chart_errs(p["chart"], f"panel '{p['id']}' chart")
        e += composite.check(spec)
    if t == "comparison_table":
        e += [f"rows/{i}: {len(r['cells'])} cells but {len(spec['columns'])} columns"
              for i, r in enumerate(spec["rows"]) if len(r["cells"]) != len(spec["columns"])]
        if spec.get("highlight_row", 0) >= len(spec["rows"]): e.append("highlight_row outside rows")
    if t == "scorecard":
        e += [f"options/{i}: {len(o['scores'])} scores but {len(spec['criteria'])} criteria"
              for i, o in enumerate(spec["options"]) if len(o["scores"]) != len(spec["criteria"])]
        mx = spec.get("max_score", 5)
        if any(not 0 <= s <= mx for o in spec["options"] for s in o["scores"]): e.append(f"scores must be within 0..{mx}")
    if t == "data_table":
        e += [f"rows/{i}: {len(r['values'])} values but {len(spec['columns'])} columns"
              for i, r in enumerate(spec["rows"]) if len(r["values"]) != len(spec["columns"])]
    if t == "timeline":
        if not spec.get("milestones") and not (spec.get("periods") and spec.get("bars")):
            e.append("timeline needs 'milestones', or 'periods' + 'bars'")
        for i, b in enumerate(spec.get("bars") or []):
            if not b["start"] <= b["end"] < len(spec.get("periods") or []): e.append(f"bars/{i}: start/end outside periods")
    if t in ("flowchart", "issue_tree"):
        ids = [n["id"] for n in spec["nodes"]]
        roots = [n for n in spec["nodes"] if not n.get("parent")]
        if len(roots) != 1: e.append(f"nodes: need exactly one root (no parent), found {len(roots)}")
        e += [f"node '{n['id']}': unknown parent '{n['parent']}'" for n in spec["nodes"] if n.get("parent") and n["parent"] not in ids]
        if len(set(ids)) != len(ids): e.append("nodes: duplicate ids")
    if spec.get("logo"):
        from slidegen.core import logo_path
        e += [f"logo: file not found: {g['file']}" for g in (spec["logo"] if isinstance(spec["logo"], list) else [spec["logo"]]) if not logo_path(g["file"])]
    if spec.get("theme") and spec["theme"] not in themes(): e.append(f"unknown theme '{spec['theme']}'. Styles: {', '.join(themes())}")
    if t == "scenarios" and spec.get("recommended", 0) >= len(spec["scenarios"]): e.append("recommended outside scenarios")
    for coll in ("steps", "cards", "sections"):
        if coll in spec and spec.get("active") is not None and spec["active"] >= len(spec[coll]): e.append(f"'active' outside {coll}")
    if spec.get("tracker") and spec["tracker"].get("active", 0) >= len(spec["tracker"]["sections"]):
        e.append("tracker.active outside sections")
    return e


def _explain(x):
    """Error lines for one schema error; a vague oneOf/anyOf error (panel kinds, cell forms) is replaced by the errors of the
    branch that fits best: the one whose 'kind'/'type' matches, else the one with the fewest errors."""
    if x.validator in ("oneOf", "anyOf") and x.context:
        by = {}
        for c in x.context: by.setdefault(c.schema_path[0], []).append(c)
        ok = [v for v in by.values() if not any(c.validator == "const" and list(c.path)[-1:] in (["kind"], ["type"]) for c in v)]
        best = min(ok or by.values(), key=len)
        if len(ok) < len(by): return [l for c in best for l in _explain(c)]
    return [f"{'/'.join(map(str, x.absolute_path)) or '(root)'}: {x.message}"]


def validate(spec, validator):
    errs = [l for x in validator.iter_errors(spec) for l in _explain(x)]
    if errs and spec.get("type") in BUILDERS:          # oneOf errors are vague: re-validate against the matching branch
        branch = next(b for b in validator.schema["oneOf"] if b["properties"]["type"]["const"] == spec["type"])
        errs = [l for x in Draft202012Validator(branch).iter_errors(spec) for l in _explain(x)]
    return list(dict.fromkeys(errs)) or check(spec)


def _grid(x, base):
    """Values of an Excel range (cached formula results, so the file must have been saved by Excel)."""
    from openpyxl import load_workbook
    p = Path(x["file"]); p = p if p.is_absolute() else base / p
    if not p.exists(): raise ValueError(f"excel file not found: {p}")
    wb = load_workbook(p, data_only=True, read_only=True)
    ws = wb[x["sheet"]] if x.get("sheet") else wb.active
    return [[c.value for c in row] for row in ws[x["range"]]]


def resolve_excel(spec, base):
    """Replace every {"excel": {file, sheet?, range}} with the data it points to.
    Range layout: first row = header (series names / column labels), first column = categories / row labels."""
    def chart(c):
        if "excel" in c:
            g = _grid(c.pop("excel"), base)
            c["categories"] = [str(r[0]) for r in g[1:]]
            c["series"] = [{"name": str(g[0][j]), "values": [r[j] for r in g[1:]]} for j in range(1, len(g[0]))]
    if "chart" in spec: chart(spec["chart"])
    for p in spec.get("panels", []):
        if "chart" in p: chart(p["chart"])
    if "excel" in spec:
        g = _grid(spec.pop("excel"), base); t = spec["type"]
        if t == "data_table":
            spec["columns"] = [str(v) for v in g[0][1:]]
            spec["rows"] = [{"label": str(r[0]), "values": list(r[1:])} for r in g[1:]]
        elif t == "waterfall":
            spec["steps"] = [{"label": str(r[0]), "value": r[1]} for r in g[1:]]
        elif t == "tile_map":
            spec["values"] = {str(r[0]).strip().upper(): r[1] for r in g[1:] if r[1] is not None}
        else:
            raise ValueError(f"'excel' is not supported on {t} (charts, data_table, waterfall, tile_map)")
    return spec


def load_specs(path):
    d = json.loads(Path(path).read_text(encoding="utf-8-sig"))   # tolerate BOM (Notepad/PowerShell)
    specs = d if isinstance(d, list) else [d] if "type" in d else list(d.values())
    return [resolve_excel(s, Path(path).resolve().parent) for s in specs]


SCHEMA = json.loads((ROOT / "schemas" / "archetypes.schema.json").read_text(encoding="utf8"))


def _words(v):
    """Words in all string values of a spec (keys such as type/theme/lang are not counted)."""
    if isinstance(v, str): return len(v.split())
    if isinstance(v, list): return sum(_words(x) for x in v)
    if isinstance(v, dict): return sum(_words(x) for k, x in v.items() if k not in ("type", "theme", "lang", "icon", "kind", "color"))
    return 0


def build_specs(specs, out, theme=None, primary=None, font=None, heading_font=None, warnings=None):
    """Validate then build. Returns a list of error strings (empty = written to `out`). Shared by CLI and MCP server.
    Non-fatal findings (density check) are appended to the `warnings` list when one is passed."""
    if theme and theme not in themes(): return [f"unknown style '{theme}'. Styles: {', '.join(themes())}"]
    v = Draft202012Validator(SCHEMA)
    errs = [f"#{i} {s.get('type')}: {e}" for i, s in enumerate(specs) for e in validate(s, v)]
    if errs: return errs
    prs = new_deck(); composite.WARNINGS.clear()
    for s in specs:
        th = load_theme(theme or s.get("theme"), primary or s.get("primary"),
                        font or s.get("font"), heading_font or s.get("heading_font"))
        try: BUILDERS[s["type"]](blank(prs), s, th, s.get("lang", "pt"))
        except LogoError as ex: return [str(ex)]          # theme-token logo with a missing file
    for s in specs:      # steer away from fallback archetypes (front-end rule: composite is the default for 2+ data blocks)
        if s["type"] in ("multi_chart", "chart_takeaway"): composite.WARNINGS.append(f"fallback archetype '{s['type']}': prefer composite for multi-block content (cost tree, assumptions with sources, phases, KPIs); every data block the user gave must appear on the slide")
        elif s["type"] != "composite" and _words(s) < 100: composite.WARNINGS.append(f"sparse fallback slide ({_words(s)} words < 100): the archive median is ~175; add the data blocks the user gave or use composite")
    Path(out).parent.mkdir(parents=True, exist_ok=True); prs.save(out)
    if warnings is not None: warnings.extend(composite.WARNINGS)
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?"); ap.add_argument("-o", "--out", default="slide.pptx")
    ap.add_argument("--styles", action="store_true", help="list available styles and exit")
    ap.add_argument("--theme"); ap.add_argument("--primary"); ap.add_argument("--font"); ap.add_argument("--heading-font")
    a = ap.parse_args()
    if a.styles or not a.spec:
        for k, v in themes().items(): print(f"{k:18} {v['primary']}  {v['heading_font']}/{v['body_font']}  {v.get('_src', '')}")
        return
    try:
        specs = load_specs(a.spec)
    except ValueError as e:
        print(f"Spec invalid: {e}"); sys.exit(1)
    warns = []; errs = build_specs(specs, a.out, a.theme, a.primary, a.font, a.heading_font, warns)
    if errs:
        print("Spec invalid:\n  " + "\n  ".join(errs)); sys.exit(1)
    for w in warns: print("WARNING", w)
    print("wrote", a.out, f"({len(specs)} slide{'s' * (len(specs) > 1)})")


if __name__ == "__main__":
    main()
