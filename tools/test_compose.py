"""compose.py checks: orbital profile -> L|R2 waterfall + table + stacked + arrow; thin profile -> density thin. Run: py -3 -I tools/test_compose.py"""
import json, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(root), str(root / "tools")]
import compose, build
from jsonschema import Draft202012Validator
from slidegen import composite

load = lambda n: json.loads((root / "examples" / "profiles" / f"{n}.json").read_text("utf8"))
v = Draft202012Validator(build.SCHEMA)

def valid(opt):                                   # every skeleton must pass the schema and composite.check (section skeletons: within compose.fits' 0.3in estimate slack)
    errs = [e.message for e in v.iter_errors(opt["spec"])] or ([] if opt["strategy"] in ("sections", "wide", "band", "strip") and compose.fits(opt["spec"]) else composite.check(opt["spec"]))
    assert not errs, (opt["layout"], errs[:3])

r = compose.suggest(load("orbital")); top = r["options"][0]
assert r["density"] == "ok", r["density_message"]
assert top["layout"] == "L|R2", top["layout"]
assert [p["element"] for p in top["panels"]] == ["waterfall", "table", "stacked"], top["panels"]
assert {"kind": "arrow", "from": "p1", "to": "p2"} in top["links"], top["links"]
assert top["examples"] and top["examples"][0]["layout"] == "L|R2", top["examples"][:1]
assert len(r["options"]) == 3
for o in r["options"]: valid(o)

t = compose.suggest(load("thin"))
assert t["density"] == "thin" and "menos denso" in t["density_message"]["pt"], t["density_message"]
assert len(t["options"]) == 3 and all(len(o["panels"]) >= 2 for o in t["options"]), [o["layout"] for o in t["options"]]
for o in t["options"]: valid(o)

# decisions add a numbered-cards panel with an xref; 5 items keep 5 panels
p = load("orbital"); p["decisions"] = 3; p["items"].append({"id": "d", "kind": "kpi", "points": 3})
r = compose.suggest(p)
assert all(len(o["panels"]) == 5 for o in r["options"]); [valid(o) for o in r["options"]]     # 5 items now keep 5 panels (was trimmed to 4)

# AI-written profiles pass texts/values instead of counts (the MCP "'>=' list vs int" error): same result as counts
q = load("orbital"); q["insights"] = ["a", "b", "c"]; q["decisions"] = ["entrar", "ticket", "40 unidades"]
q["items"][0]["points"] = [251, 154, 68, 17, 7, 5]; q["items"][1]["series"] = "2"
rq = compose.suggest(q); [valid(o) for o in rq["options"]]
assert any(pp["element"] == "cards" for o in rq["options"] for pp in o["panels"]), "decisions list should add a cards panel"
print("ok compose: orbital ->", top["layout"], [p["element"] for p in top["panels"]], "| thin ->", t["options"][0]["strategy"], t["options"][0]["layout"])

# 5-6 items are no longer trimmed: 5 -> a 5-panel layout, 6 -> 2x3; correlation with 2 numeric dimensions -> scatter panel, 3 -> bubble
five = {"message": "m", "items": [{"id": f"i{k}", "kind": "trend", "points": 5, "series": 1, "label": f"T{k}"} for k in range(4)] + [{"id": "c", "kind": "correlation", "points": 8, "dimensions": 2}], "insights": 0}
r5 = compose.suggest(five); [valid(o) for o in r5["options"]]
assert r5["options"] and all(len(o["panels"]) == 5 for o in r5["options"]) and r5["options"][0]["layout"] == "cols" and "T2|B3" in [o["layout"] for o in r5["options"]], [(o["layout"], len(o["panels"])) for o in r5["options"]]
assert sorted(len(c["rows"]) for c in r5["options"][0]["spec"]["cols"]) == [1, 2, 2], "5 exhibits -> 3 sections of 1+2+2 (user ruling 2026-11-12)"
assert any(pp["element"] == "scatter" for pp in r5["options"][0]["panels"]), r5["options"][0]["panels"]
six = dict(five, items=five["items"] + [{"id": "b", "kind": "correlation", "points": 6, "dimensions": 3}])
r6 = compose.suggest(six); [valid(o) for o in r6["options"]]
o6 = next(o for o in r6["options"] if o["layout"] == "2x3"); assert r6["options"][0]["layout"] == "cols" and len(o6["panels"]) == 6 and {"scatter", "bubble"} <= {pp["element"] for pp in o6["panels"]}
assert compose.pick_element({"kind": "correlation", "points": 8, "dimensions": 1}) == "column"
sec = compose.suggest({"message": "m", "items": [{"id": "m", "kind": "trend", "points": 5}, {"id": "f", "kind": "breakdown", "points": 4}, {"id": "c", "kind": "ranking", "points": 4}, {"id": "k", "kind": "kpi", "points": 3}, {"id": "r", "kind": "list", "points": 2, "words": 16}],
                       "relations": [{"from": "m", "to": "c", "type": "leads_to"}], "insights": 2, "decisions": 1})["options"]
assert sec[0]["strategy"] == "strip", "KPIs that relate to nothing -> KPI strip first (user ruling 2026-11-12)"
sec = next(o for o in sec if o["strategy"] == "sections"); valid(sec)
assert sec["layout"] == "cols" and [pp["item"] for pp in sec["panels"]] == ["m", "c", "f", "k", "r"] and sec["spec"]["frame"]["panels"] == ["p4", "p5"], sec["panels"]
assert "callout" in sec["spec"]["panels"][-1] and "takeaway" not in sec["spec"] and not any(pp.get("bullets") for pp in sec["spec"]["panels"]), "decision -> conclusion callout; insights -> intros"
tb_ = compose.suggest({"message": "m", "items": [{"id": "t", "kind": "lookup_table", "points": 6, "series": 6}, {"id": "c", "kind": "trend", "points": 5}, {"id": "k", "kind": "kpi", "points": 3}, {"id": "r", "kind": "list", "points": 2, "words": 14}],
                        "relations": [{"from": "c", "to": "t", "type": "zooms_into"}], "insights": 1})["options"]; tb_, tb2 = [o for o in tb_ if o["strategy"] == "sections"][:2]; valid(tb_); valid(tb2)
lay = lambda o: [(c["w"], len(c["rows"])) for c in o["spec"]["cols"]]
assert lay(tb_) != lay(sec) and {len(tb_["spec"]["cols"]), len(tb2["spec"]["cols"])} == {2, 3} and tb_["score"] >= tb2["score"], ("layout follows the content: 2- and 3-section variants ranked by archive share (user ruling 2026-11-12)", lay(tb_), lay(tb2), lay(sec))
assert tb_["spec"]["cols"][0]["w"] >= max(c["w"] for c in tb_["spec"]["cols"]) - 1e-9, "a table section runs wider (grammar rel_width)"
g1 = compose.sections([{"id": "c", "kind": "trend"}, {"id": "f", "kind": "breakdown"}, {"id": "t", "kind": "comparison"}, {"id": "k", "kind": "kpi"}],
                      ["column", "flow", "table", "kpis"], [{"from": "k", "to": "f", "type": "explains"}], 3)
assert g1 == [[0], [1, 3], [2]], ("a single KPI block is a support under its related exhibit, not its own section", g1)
print("ok compose: 5 items ->", r5["options"][0]["layout"], "| 6 items ->", r6["options"][0]["layout"], "| sections: related pair together, results framed")

# cold-chain profile (breakdown + assumptions with sources + phased signed series + KPIs): top option has flow + pills + phases + payback note
cc = compose.suggest(load("coldchain")); top = cc["options"][0]; valid(top)
assert {p["element"] for p in top["panels"]} >= {"flow", "table_pills", "column", "kpis"}, top["panels"]
sp = {p["id"]: p for p in top["spec"]["panels"]}
fl = next(p for p in sp.values() if p["kind"] == "flow"); tb = next(p for p in sp.values() if p["kind"] == "table")
ch = next(p for p in sp.values() if p["kind"] == "chart")
assert any(n.get("op") == "+" for n in fl["nodes"]), "flow needs a + junction"
assert tb["pill_legend"] and any(isinstance(c, dict) and "pill" in c for r in tb["rows"] for c in r), "table needs pill cells + legend"
assert len(ch["chart"]["phases"]) == 3 and min(ch["chart"]["series"][0]["values"]) < 0, ch["chart"]
assert any(l["kind"] == "note" for l in top["spec"]["links"]), "payback note"
for o in cc["options"]: valid(o)
# old-style spelling still works: composition + hierarchy -> flow, lookup_table + sourced -> pills
assert compose.pick_element({"kind": "composition", "hierarchy": True, "points": 6}) == "flow" and compose.pick_element({"kind": "lookup_table", "sourced": True, "points": 4}) == "table_pills"
print("ok compose: coldchain ->", top["layout"], [p["element"] for p in top["panels"]])
gm = compose.grammar(); assert gm.get("n_slides", 0) >= 100 and 0 < gm["header_rate"] <= 1 and gm["rel_width"] and gm["sections_by_blocks"], "analysis/grammar.json (tools/grammar.py) must be present"
print("ok compose: archive grammar loaded,", gm["n_slides"], "labelled slides")
# layout variety from the content (user ruling 2026-11-12): a bridge that most blocks explain -> its section wider, first; no hero -> equal sections first
bp = compose.suggest({"message": "margem caiu", "items": [{"id": "b", "kind": "bridge", "points": 7}, {"id": "l", "kind": "ranking", "points": 5}, {"id": "m", "kind": "comparison", "points": 3},
                      {"id": "a", "kind": "assumptions", "points": 3, "series": 3}, {"id": "k", "kind": "kpi", "points": 3}],
                      "relations": [{"from": "l", "to": "b", "type": "explains"}, {"from": "m", "to": "b", "type": "explains"}], "decisions": 1}, nearest=False)["options"]
st = [o["strategy"] for o in bp]; valid(bp[0])
assert st[0] == "wide" and len(set(st)) == len(st), ("hero bridge -> wide section first; options differ in structure", st)
c0 = bp[0]["spec"]["cols"]; assert c0[0]["w"] == max(c["w"] for c in c0) > 0.4 and bp[0]["spec"]["panels"][0]["chart"]["kind"] == "waterfall", c0
assert bp[0]["spec"]["section_style"] in compose.SECTION_STYLES and any(p.get("callout") for p in bp[0]["spec"]["panels"]), "section style from the archive mix; decision -> callout"
assert compose.section_style({"message": "x"}) == compose.section_style({"message": "x"}) and len({compose.section_style({"message": str(i)}) for i in range(40)}) >= 3, "section style: stable per slide, varies across slides"
sn = compose.suggest(json.loads((root / "examples" / "profiles" / "coldchain.json").read_text("utf8")), nearest=False)["options"]
eq = compose.suggest({"message": "m", "items": [{"id": "c", "kind": "trend", "points": 5}, {"id": "f", "kind": "breakdown", "points": 4}, {"id": "t", "kind": "comparison", "points": 4, "series": 4}, {"id": "k", "kind": "kpi", "points": 3}],
                      "relations": [{"from": "k", "to": "f", "type": "explains"}]}, nearest=False)["options"]
assert eq[0]["strategy"] == "sections" and "strip" in [o["strategy"] for o in eq], ("no hero -> equal sections first, KPI strip offered", [o["strategy"] for o in eq])
strip = next(o for o in eq if o["strategy"] == "strip"); valid(strip); assert strip["spec"]["band"]["h"] == 0.2 and strip["spec"]["panels"][0]["kind"] == "kpis"
print("ok compose: variants by content ->", st, "|", [o["strategy"] for o in eq])
