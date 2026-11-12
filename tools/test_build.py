"""Smoke test: every archetype builds, stays native/editable, and bad specs are rejected. Run: py -3 -I tools/test_build.py"""
import json, subprocess, sys, pathlib
from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.enum.shapes import MSO_SHAPE
root = pathlib.Path(__file__).parent.parent; out = root / "out"; out.mkdir(exist_ok=True)
run = lambda *a: subprocess.run([sys.executable, str(root / "build.py"), *map(str, a)], capture_output=True, text=True)

cat = json.loads((root / "examples" / "catalog.json").read_text("utf8"))
r = run(root / "examples" / "catalog.json", "-o", out / "catalog.pptx"); assert r.returncode == 0, r.stdout + r.stderr
slides = Presentation(out / "catalog.pptx").slides
assert len(slides) == len(cat) == 26, len(slides)
CHARTS = {"chart_takeaway": 1, "multi_chart": 3, "waterfall": 1, "composite": 1}
TABLES = {"comparison_table", "scorecard", "data_table"}
for (name, spec), s in zip(cat.items(), slides):
    shapes = list(s.shapes)
    assert sum(sh.has_chart for sh in shapes) == CHARTS.get(name, 0), f"{name}: native chart count"
    assert sum(sh.has_table for sh in shapes) == (1 if name in TABLES else 0), f"{name}: native table"
    icons = json.dumps(spec).count('"icon"')               # icons are the only pictures we add ourselves
    assert sum(sh.shape_type == 13 for sh in shapes) == icons, f"{name}: pictures only for icons"
    assert any(sh.has_text_frame and sh.text_frame.text.strip() for sh in shapes), f"{name}: real text"
print("ok catalog: 26 archetypes, native charts/tables, pictures only for icons")

for lang in ("pt", "en"):
    r = run(root / "examples" / f"chart_takeaway.{lang}.json", "-o", out / f"chart_takeaway.{lang}.pptx")
    assert r.returncode == 0, r.stdout
print("ok chart_takeaway pt/en")

# scorecard totals are computed by the tool, not typed: Milho = (5*30+5*25+4*20+4*15+3*10)/100 = 4.45 -> "4,5"
cells = [sh for sh in slides[list(cat).index("scorecard")].shapes if sh.has_table][0].table
assert cells.cell(1, 6).text == "4,5", cells.cell(1, 6).text

# composite: native chart/table frames, highlight box inside its chart frame, bad specs rejected
orb = json.loads((root / "examples" / "composite_orbital.pt.json").read_text("utf8"))
r = run(root / "examples" / "composite_orbital.pt.json", "-o", out / "composite_orbital.pptx"); assert r.returncode == 0, r.stdout + r.stderr
shapes = list(Presentation(out / "composite_orbital.pptx").slides[0].shapes)
charts = [sh for sh in shapes if sh.has_chart]
assert len(charts) == 2 and sum(sh.has_table for sh in shapes) == 1, "composite: native charts + table"
hl = [sh for sh in shapes if sh.name.startswith("highlight:")]; assert len(hl) == 1, "composite: highlight box"
c0, h0 = charts[0], hl[0]
assert c0.left <= h0.left and c0.top <= h0.top and h0.left + h0.width <= c0.left + c0.width     and h0.top + h0.height <= c0.top + c0.height, "composite: highlight lies within its chart frame"
print("ok composite builds natively, highlight inside chart")

bad = out / "bad.json"
def mutate(f):
    s = json.loads(json.dumps(orb)); f(s); return s
for spec, needle in [
    (mutate(lambda s: s["links"][0].update({"to": "zz"})), "unknown panel id"),
    (mutate(lambda s: s["panels"].pop()), "slots but 2 panels"),
    (mutate(lambda s: s["panels"][2].update({"bullets": ["x" * 170] * 4})), "characters too long"),
    (mutate(lambda s: s["links"].append({"kind": "highlight", "panel": "p2", "categories": [0]})), "not a chart"),
    (mutate(lambda s: s["links"].append({"kind": "highlight", "panel": "p1", "categories": [9]})), "outside 0..5"),
]:
    bad.write_text(json.dumps(spec)); r = run(bad)
    assert r.returncode == 1 and needle in r.stdout, (needle, r.stdout)
print("ok composite rejects bad specs")

for spec, needle in [
    ({"type": "chart_takeaway", "headline": "x", "chart": {"kind": "column", "title": "t", "categories": ["a", "b"],
      "series": [{"name": "s", "values": [1, 2, 3]}]}, "insights": ["a", "b"], "takeaway": "t"}, "3 values but 2 categories"),
    ({"type": "issue_tree", "headline": "x", "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]}, "exactly one root"),
    ({"type": "kpi_tiles", "headline": "x", "kpis": [{"value": "1", "label": "a"}]}, "too short"),
]:
    bad.write_text(json.dumps(spec)); r = run(bad)
    assert r.returncode == 1 and needle in r.stdout, r.stdout
print("ok validation rejects bad specs"); bad.unlink()

# fill rule + density warning (composite): slots are filled, a deliberately sparse slide warns
sys.path.insert(0, str(root)); import build; from slidegen import composite
long = "Item de lista com texto suficientemente longo para ocupar tres linhas dentro da coluna estreita do painel, com detalhes extras de contexto e de numeros para o teste de preenchimento"
fill = {"type": "composite", "headline": "Teste de preenchimento", "layout": "2col", "source": "Dados ilustrativos", "panels": [
    {"id": "a", "kind": "chart", "title": "Grafico", "chart": {"kind": "column", "categories": ["a", "b", "c"], "series": [{"name": "s", "values": [1, 2, 3]}]},
     "bullets": ["Um ponto curto", "Outro ponto curto"]},
    {"id": "b", "kind": "bullets", "title": "Pontos", "items": [long] * 6}]}
warns = []; assert build.build_specs([fill], out / "fill.pptx", warnings=warns) == [], "fill spec builds"
sh = list(Presentation(out / "fill.pptx").slides[0].shapes); top, bot = composite._body(fill)[1], sum(composite._body(fill)[1::2])
ch = [x for x in sh if x.has_chart][0]; assert abs(bot - (ch.top + ch.height) / 914400 - 0.1 - (composite._bul_h(fill["panels"][0], 6.0))) < 0.35, "chart + its bullets fill the slot"
tb = [x for x in sh if x.shape_type == 17 and x.text_frame.text.startswith("Item")][0]
est = tb.top / 914400 + sum(composite._lines(p.text, tb.width / 914400 - 0.2)[0] * 0.2 + p.space_after.pt / 72 for p in tb.text_frame.paragraphs)
assert bot - est < 0.45, f"bullets spread over the slot (text ends {bot - est:.2f}in above the slot bottom)"
sparse = {"type": "composite", "headline": "Slide esparso", "layout": "1", "source": "Dados ilustrativos", "panels": [{"id": "a", "kind": "bullets", "items": ["Um unico ponto curto"]}]}
warns = []; build.build_specs([sparse], out / "sparse.pptx", warnings=warns); assert any("density" in w for w in warns) and any("sparse text" in w for w in warns), warns
warns = []; build.build_specs([orb], out / "composite_orbital.pptx", warnings=warns); assert not [w for w in warns if "density" in w], warns      # a well-filled example has no empty regions (its text is light: 107 words, it warns "sparse text")
print("ok composite fill rule + density warning")

# rich inline text: ==x== = bold in the accent colour; a list cell = one bulleted paragraph per item
from slidegen.core import load_theme
rich = {"type": "composite", "headline": "Teste rico", "layout": "1", "source": "x", "theme": "navy_cyan", "panels": [
    {"id": "t", "kind": "table", "columns": ["a", "b"], "rows": [["==destaque== normal", ["um", "dois", "tres"]]], "first_col": "heading", "chevrons": 1, "rules": "rows"}]}
assert build.build_specs([rich], out / "rich.pptx", warnings=[]) == [], "rich spec builds"
tbl = [x for x in Presentation(out / "rich.pptx").slides[0].shapes if x.has_table][0].table
r0 = [r for r in tbl.cell(1, 0).text_frame.paragraphs[0].runs if r.text == "destaque"][0]
assert r0.font.bold and str(r0.font.color.rgb) == load_theme("navy_cyan")["text_primary"], "==x== = bold accent run"
assert len(tbl.cell(1, 1).text_frame.paragraphs) == 3, "list cell = several paragraphs"
print("ok rich text + list cells")

# scatter / bubble are native XY charts; 2x3 builds 6 panels; the logo picture sits clear of the source text
from pptx.enum.chart import XL_CHART_TYPE
def build1(spec, name):
    f = out / f"{name}.pptx"; assert build.build_specs([spec], f, warnings=[]) == [], name; return list(Presentation(f).slides[0].shapes)
sc = json.loads((root / "examples" / "composite_scatter.pt.json").read_text("utf8"))
sh = build1(sc, "t_scatter"); ch = [x for x in sh if x.has_chart]
assert len(ch) == 1 and ch[0].chart.chart_type == XL_CHART_TYPE.XY_SCATTER, "scatter: native XY chart"
assert sum(x.shape_type == 9 or x.name.startswith("Connector") for x in sh) >= 2, "scatter: quadrant lines"
bub = json.loads(json.dumps(sc)); bub["panels"][0]["chart"].update(kind="bubble", highlight=[0])
for i, q in enumerate(bub["panels"][0]["chart"]["points"]): q["size"] = i + 1
assert [x.chart.chart_type for x in build1(bub, "t_bubble") if x.has_chart] == [XL_CHART_TYPE.BUBBLE], "bubble: native bubble chart"
nosize = json.loads(json.dumps(bub)); del nosize["panels"][0]["chart"]["points"][0]["size"]
assert any("no 'size'" in e for e in build.build_specs([nosize], out / "t_ns.pptx")), "bubble needs sizes"
g = json.loads((root / "examples" / "composite_2x3.pt.json").read_text("utf8")); assert g["layout"] == "2x3" and len(g["panels"]) == 6
sh = build1(g, "t_2x3"); txt = [x.text_frame.text for x in sh if x.has_text_frame]
assert all(any(p["title"] in t for t in txt) for p in g["panels"]), "2x3: six panel headers drawn"
assert len(composite.slots("2x3", None, 0, 0, 12, 5)) == 6
_c = [{"w": 1, "rows": [1, 1], "title": "A", "intro": "intro text", "span": 2}, {"w": 1, "rows": [1]}, {"w": 2, "rows": [1, 2, 1]}]      # layout cols: free columns split into rows, header + intro reserve space, span shares one header
_cs = composite.slots("cols", _c, 0, 0, 12, 6); assert len(_cs) == 6 and _cs[0][1] > 0.3 and abs(_cs[2][1] - _cs[0][1]) < 1e-6 and _cs[3][2] > 1.9 * _cs[0][2]
assert composite._nslots({"layout": "cols", "cols": _c}) == 6
for lay, n in (("4col", 4), ("L|R3", 4), ("T|B3", 4), ("T2|B3", 5)): assert len(composite.slots(lay, None, 0, 0, 12, 5)) == n == composite.SLOTS[lay], lay
lg = json.loads((root / "examples" / "composite_logo.pt.json").read_text("utf8")); sh = build1(lg, "t_logo")
pic = [x for x in sh if x.shape_type == 13 and x.name == "logo"]; src = [x for x in sh if x.has_text_frame and x.text_frame.text.startswith("Fonte")][0]
pn = [x for x in sh if x.has_text_frame and x.text_frame.text == str(lg["page_number"])][0]
assert len(pic) == 1, "logo picture present"
ov = lambda a, b: a.left < b.left + b.width and b.left < a.left + a.width and a.top < b.top + b.height and b.top < a.top + a.height
assert not ov(pic[0], src) and not ov(pic[0], pn), "logo clear of source and page number"
assert abs(pic[0].width / pic[0].height - 4) < 0.05, "logo keeps its aspect ratio (480x120)"
miss = json.loads(json.dumps(lg)); miss["logo"]["file"] = "examples/data/nope.png"
assert any("logo: file not found" in e for e in build.build_specs([miss], out / "t_miss.pptx")), "missing logo file -> build error"
print("ok scatter/bubble native XY, 2x3 six panels, logo placement + missing-file error")

# composite elements: flow panel, icons, pill cells, chart phases, doughnut callouts (all native; icons are the only pictures)
el = json.loads((root / "examples" / "composite_elements.pt.json").read_text("utf8")); sh = build1(el, "t_elements")
txt = lambda t: [x for x in sh if x.has_text_frame and x.text_frame.text == t]
assert sum(x.has_chart for x in sh) == 2 and sum(x.has_table for x in sh) == 1, "elements: native charts + table"
assert sum(x.shape_type == 13 for x in sh) == 3, "elements: pictures are the 3 kpi icons only"
assert len(txt("+")) == 2 and all(x.shape_type == 1 for x in txt("+")) and txt("OPEX") and txt("Custos fixos"), "flow: boxes + two operator circles as real shapes"
assert sum(x.name.startswith("Connector") or x.shape_type == 9 for x in sh) >= 12, "flow/phases/callouts: connector lines"
assert len(txt("Dado público")) == 2 and len(txt("Benchmark")) == 2, "pills: cell pill + legend pill carry real text"
assert all(txt(s_) for s_ in ("1", "2", "3")), "phases: three labels"
assert any(x.has_text_frame and x.text_frame.text.startswith("Equipamentos") and "34%" in x.text_frame.text for x in sh), "callouts: name + value outside the ring"
ic = {"type": "composite", "headline": "Icones", "layout": "2col", "source": "x", "panels": [
    {"id": "b", "kind": "bullets", "items": ["Primeiro ponto", "Segundo ponto"], "icons": ["rocket", ""]},
    {"id": "c", "kind": "cards", "items": [{"title": "A", "text": "texto a", "icon": "users"}, {"title": "B", "text": "texto b"}]}]}
assert sum(x.shape_type == 13 for x in build1(ic, "t_icons")) == 2, "bullets/cards icons: one picture each"
for f, needle in [
    (lambda s: s["panels"][4]["items"][0].update(icon="no-such-icon"), "unknown icon"),
    (lambda s: s["panels"][3]["rows"][0].__setitem__(2, {"pill": "x", "color": "nope"}), "pill colour"),
    (lambda s: s["panels"][2]["chart"].update(kind="bar"), "phases"),
    (lambda s: s["panels"][2]["chart"]["phases"].reverse(), "must increase"),
    (lambda s: s["panels"][2]["chart"].update(callouts=True), "callouts"),
    (lambda s: s["panels"][0]["nodes"][2].pop("parent"), "exactly one root"),
]:
    m = json.loads(json.dumps(el)); f(m); assert any(needle in e_ for e_ in build.build_specs([m], out / "t_bad.pptx")), needle
print("ok composite elements: flow, icons, pills, phases, callouts + their checks")

# composite elements 2: icon table cells, side labels, chart -> table connectors, gradient scale bar, dotted notes
e2 = json.loads((root / "examples" / "composite_elements2.pt.json").read_text("utf8")); sh = build1(e2, "t_elements2")
assert sum(x.shape_type == 13 for x in sh) == 3, "icon cells: three pictures"
tb = [x for x in sh if x.has_table][0]; ic = [x for x in sh if x.shape_type == 13]
assert all(tb.left <= x.left and x.left + x.width <= tb.left + tb.width and tb.top <= x.top <= tb.top + tb.height for x in ic), "icon cells: pictures lie inside the table"
assert tb.table.cell(1, 0).text == "Etanol hidratado" and tb.table.cell(1, 0).margin_top > 300000, "icon cell: text kept, room left for the icon"
sl = [x for x in sh if x.name == "side_label"]; assert [x.text_frame.text for x in sl] == ["CARROS", "CAMINHÕES", "ÔNIBUS", "MERCADO"], "side labels"
assert all(x.text_frame._txBody.find(qn("a:bodyPr")).get("vert") == "vert270" for x in sl), "side labels are rotated 270 degrees"
assert sl[0].top < sl[1].top < sl[2].top and sl[0].top + sl[0].height <= sl[1].top, "row strips follow the table rows without overlapping"
cn = [x for x in sh if x.name.startswith("connector:")]; assert len(cn) == 3 and all(c.shape_type == 9 or c.name.startswith("connector") for c in cn), "3 connectors"
assert all(c.left + c.width >= [x for x in sl if x.text_frame.text == "CARROS"][0].left - 20000 for c in cn), "connectors end at the table strips"
sc = [x for x in sh if x.name == "scale"]; assert len(sc) == 1 and sc[0]._element.spPr.find(qn("a:gradFill")) is not None and len(sc[0]._element.spPr.find(qn("a:gradFill")).find(qn("a:gsLst"))) == 3, "scale: native 3-stop gradient"
assert all(any(x.has_text_frame and x.text_frame.text == t for x in sh) for t in ("Fragmentado", "Consolidado", "Brasil")), "scale labels"
nt = [x for x in sh if x.name.startswith("note:")]; assert len(nt) == 2 and all(x.line.dash_style is not None for x in nt), "dotted notes"
for f, needle in [
    (lambda s: s["links"][0].update(category=9), "category index outside"),
    (lambda s: s["links"][0].update(row=5), "row index outside"),
    (lambda s: s["links"][0].update(to="s"), "table (or cards)"),
    (lambda s: s["links"][3].update(at=9), "category index outside"),
    (lambda s: s["links"][4].update(panel="t", target=0), "needs a column"),
    (lambda s: s["panels"][1]["side_label"][0].update(rows=[0, 7]), "side_label rows"),
    (lambda s: s["panels"][2]["scale"].update(colors=["zz", "FFFFFF"]), "scale colour"),
    (lambda s: s["panels"][1]["rows"][0].__setitem__(0, {"icon": "no-such-icon", "text": "x"}), "unknown icon"),
]:
    m = json.loads(json.dumps(e2)); f(m); assert any(needle in e_ for e_ in build.build_specs([m], out / "t_bad.pptx")), needle
tall = json.loads(json.dumps(e2)); r0 = tall["panels"][1]["rows"][0]; r0[0]["text"] = "Texto bem longo para a coluna estreita do icone " * 2
assert composite._bar_h(r0, [1.2, 2.0], 10) > composite._bar_h(e2["panels"][1]["rows"][0], [1.2, 2.0], 10) > 0.5, "row height estimate counts the icon + wrapped text"
print("ok composite elements 2: icon cells, side labels, connectors, scale, notes + their checks")

# fallback archetypes warn (front-end steers to composite)
mc = json.loads((root / "out" / "check" / "desktop_repro.json").read_text("utf8")) if (root / "out" / "check" / "desktop_repro.json").exists() else None
if mc:
    w = []; assert not build.build_specs([mc], out / "t_fb.pptx", warnings=w) and any("fallback archetype" in x for x in w), w
    print("ok fallback archetype warning")

# emphasis shapes: opt-in native shapes, no change without them
em = json.loads((root / "examples" / "composite_emphasis.pt.json").read_text("utf8")); sh = build1(em, "t_emphasis")
nm = lambda n: [x for x in sh if x.name == n]
assert len(nm("backdrop")) == 1 and len(nm("pointer")) == 2 and len(nm("accent_bar")) == 1 and len(nm("delta")) == 4, "emphasis: shapes by name"
assert {x.rotation for x in nm("delta")} == {0, 180}, "emphasis: down delta rotated"
assert sum(x.auto_shape_type == MSO_SHAPE.PENTAGON for x in sh if x.shape_type == 1 and x.name not in ("pointer", "delta")) == 2, "emphasis: pentagon headers"
bd = nm("backdrop")[0]; cf = [x for x in sh if x.has_chart][0]; assert bd.left <= cf.left and bd.top <= cf.top and bd.left + bd.width >= cf.left + cf.width, "emphasis: backdrop behind the chart"
assert sh.index(bd) < sh.index(cf), "emphasis: backdrop is drawn under the chart"
base = {k: v for k, v in em.items() if k != "emphasis"}; base["panels"] = [{k: v for k, v in p.items() if k != "title_shape"} for p in base["panels"]]
base["panels"][0]["items"] = [{k: v for k, v in i.items() if k != "delta"} for i in em["panels"][0]["items"]]
assert not [x for x in build1(base, "t_noemph") if x.name in ("backdrop", "pointer", "accent_bar", "delta")], "emphasis: nothing drawn unless used"
band = {**base, "emphasis": [{"kind": "backdrop", "panels": ["k", "b"], "y": [0.8, 1], "fill": "pale", "outline": "dashed"}]}
b0 = [x for x in build1(band, "t_band") if x.name == "backdrop"][0]; assert b0.height < 2.0 * 914400, "emphasis: y band is a slice of the panels"
bad = {**base, "emphasis": [{"kind": "pointer", "from": "k", "to": "zz"}, {"kind": "backdrop", "panels": ["k"], "fill": "nope"}, {"kind": "backdrop", "panels": ["k"], "y": [0.9, 0.2]}]}
errs = composite.check(bad); assert len(errs) == 3 and "unknown panel id" in errs[0], errs
assert any("title_shape needs" in e for e in composite.check({**base, "panels": [{**base["panels"][1], "title": "", "title_shape": "pentagon"}, *base["panels"][1:]]})), "title_shape needs a title"
print("ok emphasis shapes (backdrop/pointer/accent_bar/title_shape/delta)")
tb = json.loads((root / "examples" / "composite_tables.pt.json").read_text(encoding="utf-8"))
ts = [x for x in build1(tb, "t_tables") if x.has_table]; t1, t2 = ts[0].table, ts[1].table
assert (len(t1.columns), len(t2.columns)) == (8, 10), "tables: up to 10 columns"
assert str(t1.cell(0, 0).fill.fore_color.rgb) == "7F1D1D" and str(t1.cell(0, 1).fill.fore_color.rgb) == "D9D9D9", "tables: head_fill per column"
assert str(t1.cell(1, 7).fill.fore_color.rgb) == "FBE3D6", "tables: col_fill"
assert t2.cell(1, 1)._tc.tcPr.find(qn("a:lnL")) is not None and str(t2.cell(2, 1).fill.fore_color.rgb) == "F2F2F2", "tables: grid + bands"
e_ = composite.check({**tb, "panels": [{**tb["panels"][0], "head_fill": ["1A1A1A", None]}, tb["panels"][1]]}); assert any("head_fill has 2 entries" in x for x in e_), e_
wh = {**tb, "theme": "bain_red", "panels": [{k: v for k, v in tb["panels"][1].items() if k != "grid"} | {"head_fill": "FFFFFF"}, tb["panels"][0]]}
c0 = [x for x in build1(wh, "t_whitehead") if x.has_table][0].table.cell(0, 0)
assert c0._tc.tcPr.find(qn("a:lnB")) is not None and c0.text_frame.paragraphs[0].runs[0].font.bold, "tables: white head_fill without grid = bold header on a rule"
print("ok table styling (10 columns, head_fill, col_fill, bands, grid, styled cells)")
lg = {"file": "examples/data/logo_placeholder.png", "position": "footer-right", "height": 0.3}
assert any("title_size 30" in x for x in composite.check({**tb, "title_size": 30})), "title_size: long headline that cannot fit is an error"
kx = {**tb, "headline": "Avaliação das EPCs", "logo": [lg, lg, {**lg, "position": "top-right"}], "tag": "Anexos", "tag_style": "plain", "title_size": 30,
      "panels": [{**tb["panels"][0], "title_badge": 1}, tb["panels"][1]]}
sh = build1(kx, "t_kicker"); logos = sorted((x for x in sh if x.name == "logo"), key=lambda x: x.left)
assert len(logos) == 3 and logos[0].left + logos[0].width <= logos[1].left, "logo list: two footer-right logos side by side, no overlap"
assert any(x.has_text_frame and x.text_frame.text == "ANEXOS" and x.top < 914400 * 0.2 for x in sh), "tag_style plain: kicker above the title"
assert any(x.has_text_frame and x.text_frame.paragraphs[0].runs and x.text_frame.paragraphs[0].runs[0].font.size == 30 * 12700 for x in sh), "title_size override"
bd = [x for x in sh if x.has_text_frame and x.text_frame.text == "1" and x.width < 914400 * 0.4]; tt = [x for x in sh if x.has_table][0]
assert bd and bd[0].left <= tt.left + 914400 * 0.05, "title_badge: circle at the panel's left edge, table not shifted"
print("ok logo list, kicker (tag_style plain), title_size, title_badge")
ib = {**tb, "layout": "2col", "panels": [tb["panels"][0], {"id": "ib", "kind": "bullets", "title": "Recomendação", "items": ["**WEG:** melhor ==custo==", "**Fluence:** tecnologia"], "icons": ["award", "cpu"]}]}
th_ = composite.load_theme(ib["theme"]); runs = [r for x in build1(ib, "t_iconacc") if x.has_text_frame for q in x.text_frame.paragraphs for r in q.runs if r.text == "custo"]
assert runs and str(runs[0].font.color.rgb) == th_["text_primary"].upper(), "icon bullets: ==accent== drawn in the brand colour"
print("ok icon bullets keep the accent colour")
cb = {**ib, "panels": [tb["panels"][0], {"id": "cb", "kind": "cards", "title": "Alavancas", "items": [{"title": "WEG", "text": "melhor ==custo=="}, {"title": "Fluence", "text": "tecnologia"}]}]}
runs = [r for x in build1(cb, "t_cardacc") if x.has_text_frame for q in x.text_frame.paragraphs for r in q.runs if r.text == "custo"]
assert runs and str(runs[0].font.color.rgb) == th_["text_primary"].upper(), "cards: ==accent== drawn in the brand colour"
print("ok cards keep the accent colour")
cd_ = {**tb, "layout": "cols", "dividers": True, "cols": [{"w": 1, "rows": [0.5, 0.5], "title": "A"}, {"w": 1, "rows": [1], "title": "B"}],
       "panels": [{"id": "a1", "kind": "bullets", "items": ["um"]}, {"id": "a2", "kind": "bullets", "items": ["dois"]}, {"id": "b1", "kind": "bullets", "items": ["três"]}]}
hz = [x for x in build1(cd_, "t_coldiv") if x.shape_type == 9 and x.height == 0 and x.line.dash_style is not None]
assert len(hz) == 1, f"cols dividers: one dashed line between the two stacked slots of column A, got {len(hz)}"
print("ok cols dividers between stacked slots")
tp = {**cd_, "theme": "lek_green", "panels": [{"id": "a1", "kind": "bullets", "title": "Plano", "title_plain": True, "items": ["um"]}, *cd_["panels"][1:]]}
t_ = [x for x in build1(tp, "t_plainbar") if x.has_text_frame and x.text_frame.text == "Plano"][0]
assert t_.shape_type == 17, "title_plain under a bar column header: plain text box, not a second bar"
print("ok title_plain beats bar headers")
cg_ = {**cd_, "panels": [{"id": "a1", "kind": "chart", "chart": {"kind": "column", "categories": ["a", "b", "c"], "series": [{"name": "s", "values": [38, 45, 53]}], "labels": True}},
                         {"id": "a2", "kind": "bullets", "items": ["dois"]}, {"id": "b1", "kind": "bullets", "items": ["três"]}],
       "links": [{"kind": "cagr", "panel": "a1", "from": 0, "to": 2, "label": "+18%"}]}
mx_ = [x for x in build1(cg_, "t_cagrroom") if x.has_chart][0].chart.value_axis.maximum_scale
assert mx_ > 53 * 1.28 + 1, f"cagr on a short chart: extra headroom so the arrow clears the value label (axis max {mx_})"
print("ok cagr headroom on short charts")
big_ = {**tb, "layout": "cols", "cols": [{"w": 1, "rows": [1]}, {"w": 1, "rows": [1]}], "panels": [{"id": "a1", "kind": "chart", "chart": {"kind": "column", "categories": ["a", "b", "c"], "series": [{"name": "s", "values": [38, 45, 53]}], "title": "Receita", "subtitle": "R$ mi"}, "bullets": [f"ponto {i}" for i in range(12)]}, {"id": "b1", "kind": "bullets", "items": ["x"]}]}
assert any("panel 'a1' (chart)" in e for e in composite.check(big_)), "chart title + subtitle rows + bullets squeeze the chart frame under 1.6in (the slot check alone passes): check error"
big_["panels"][0]["bullets"] = big_["panels"][0]["bullets"][:11]; big_["panels"][0]["chart"].pop("title"); big_["panels"][0]["chart"].pop("subtitle")
assert composite.check(big_) == [], "a chart with room still passes"
print("ok chart minimum height guarded by check")
sk_ = {**cd_, "panels": [{"id": "a1", "kind": "chart", "chart": {"kind": "stacked", "categories": list("12345"), "series": [{"name": "Biometano", "values": [38, 52, 61, 63, 64]}, {"name": "CBIOs", "values": [6, 9, 11, 12, 12]},
       {"name": "Biofertilizante", "values": [4, 5, 6, 6, 6]}], "totals": True, "labels": True, "small_callouts": True}}, *cd_["panels"][1:]]}
lb_ = [x for x in build1(sk_, "t_smallcallouts") if x.has_text_frame and x.text_frame.text.isdigit() and x.text_frame.paragraphs[0].runs and x.text_frame.paragraphs[0].runs[0].font.size == 9 * 12700]
assert len(lb_) == 7, f"small_callouts: the 6-valued slivers (under 0.17in on this short plot) get outside labels too, not only values under 6% of the axis, got {len(lb_)}"
assert all(abs(a.top - b.top) >= 914400 * 0.16 for i, a in enumerate(lb_) for b in lb_[i + 1:] if a.left < b.left + b.width and b.left < a.left + a.width), "small_callouts: labels never overlap"
print("ok small_callouts labels on short plots")
from jsonschema import Draft202012Validator as _V
bad_ = json.loads((root / "examples" / "composite_orbital.pt.json").read_text(encoding="utf-8")); bad_["panels"].append({"id": "zz", "kind": "bullets", "bullets": ["a"]})
er_ = build.validate(bad_, _V(build.SCHEMA)); assert any("'bullets' was unexpected" in e and e.startswith("panels/") for e in er_), er_
from slidegen.charts import _num
assert (_num(41, '0"%"', "en"), _num(0.41, "0%", "en"), _num(3, '0" GW"', "pt")) == ("41%", "41%", "3 GW"), "quoted literals in number formats are text, not a percent scale"
print("ok schema errors name the field; quoted number-format literals")
wf_ = {**cd_, "panels": [{"id": "a1", "kind": "chart", "chart": {"kind": "waterfall", "total_first": True, "categories": ["T", "a", "b", "c", "E"], "series": [{"name": "s", "values": [100, -20, -10, -5, 65]}]}},
                         {"id": "a2", "kind": "bullets", "items": ["dois"]}, {"id": "b1", "kind": "bullets", "items": ["três"]}], "dividers": False}
ys_ = [x.top for x in build1(wf_, "t_wfneg") if x.shape_type == 9 and x.height == 0 and x.line.dash_style is not None and x.width < 914400]
assert len(ys_) == 4 and ys_ == sorted(ys_), f"total_first with negative deltas: level lines step down, not up ({ys_})"
print("ok total_first waterfall connectors with negative deltas")
# band (user ruling 2026-11-12): the first panel runs across the full width on top, the columns fill the rest
bd_ = {"type": "composite", "headline": "Band", "layout": "cols", "source": "x", "theme": "lek_green", "divider": True, "section_style": "centred_rule", "band": {"h": 0.45, "title": "Topo", "title_badge": 1},
       "cols": [{"w": 1, "rows": [1], "title": "A"}, {"w": 1, "rows": [1], "title": "B"}],
       "panels": [{"id": "w", "kind": "chart", "chart": {"kind": "column", "categories": ["a", "b"], "series": [{"name": "s", "values": [1, 2]}]}}, {"id": "x", "kind": "bullets", "items": ["um"]}, {"id": "y", "kind": "bullets", "items": ["dois"]}]}
assert composite._nslots(bd_) == 3 and not composite.check(bd_); S_ = composite._slots(bd_)
assert abs(S_[0][2] - composite._full(bd_)[2]) < 1e-6 and S_[1][1] > S_[0][1] + S_[0][3], "band slot spans the width, columns start below it"
build1(bd_, "t_band"); assert composite.check({**bd_, "layout": "2col", "cols": None}) and "band" in " ".join(composite.check({**{k: v for k, v in bd_.items() if k != "cols"}, "layout": "2col"}))
for st_ in ("label", "rule", "bar"): build1({**bd_, "section_style": st_}, "t_sec_" + st_)
# fit warnings (user ruling 2026-11-12: the build checks what instructions missed)
th_ = load_theme("lek_green")
fw = composite.fit({"layout": "cols", "cols": [{"w": 0.32, "rows": [1], "title": "Investimento segue na metade do necessário", "title_badge": 1}, {"w": 0.31, "rows": [1]}, {"w": 0.37, "rows": [1]}],
                    "panels": [{"id": "t", "kind": "table", "columns": ["Modelo", "Velocidade", "Atratividade", "Custo", "Risco", "Prazo", "Escala", "Pós-venda"], "rows": [["a"] * 8]}, {"id": "z", "kind": "bullets", "items": ["x"]},
                               {"id": "w", "kind": "chart", "chart": {"kind": "waterfall", "categories": ["2023", "Inflação de alimentos", "Salários", "Energia", "Perdas e quebras", "Marca própria", "2024"], "series": [{"name": "s", "values": [7.8, -1.4, -.9, -.6, -.4, .6, 5.1]}]}}]}, th_)
assert any("section header" in w for w in fw) and any("breaks mid-word" in w for w in fw), fw
fw2 = composite.fit({"layout": "cols", "cols": [{"w": 0.36, "rows": [1]}, {"w": 0.64, "rows": [1]}], "panels": [{"id": "w", "kind": "chart", "chart": {"kind": "waterfall", "categories": ["2023", "Inflação de alimentos", "Salários", "Energia", "Perdas e quebras", "Marca própria", "2024"], "series": [{"name": "s", "values": [7.8, -1.4, -.9, -.6, -.4, .6, 5.1]}]}}, {"id": "b", "kind": "bullets", "items": ["x"]}]}, th_)
assert any("category labels" in w for w in fw2), fw2
# row_titles: stacked sections with their own headers (L-shape / 2x2 sections, archive dispositions)
ch = lambda: {"kind": "chart", "chart": {"kind": "column", "categories": ["a", "b", "c"], "series": [{"name": "s", "values": [1, 2, 3]}]}}
Ls = {"type": "composite", "headline": "Forma em L com seções empilhadas", "layout": "cols", "source": "Dados ilustrativos", "section_style": "centred_rule", "divider": True, "dividers": True,
      "cols": [{"w": 0.5, "rows": [1], "title": "Seção alta"}, {"w": 0.5, "rows": [0.5, 0.5], "row_titles": ["Seção de cima", "Seção de baixo"], "row_badges": [2, 3]}],
      "panels": [{"id": "a", **ch()}, {"id": "b", **ch()}, {"id": "c", **ch()}]}
assert not build.build_specs([Ls], out / "L.pptx")
tx = [sh.text_frame.text for sh in Presentation(out / "L.pptx").slides[0].shapes if sh.has_text_frame]
assert "Seção de cima" in tx and "Seção de baixo" in tx and "Seção alta" in tx, tx
assert any("section header 'Uma seção de cima com um título longo demais" in w for w in composite.fit({**Ls, "cols": [Ls["cols"][0], {**Ls["cols"][1], "row_titles": ["Uma seção de cima com um título longo demais para meia largura do slide, que pede duas linhas inteiras", None]}]}, load_theme("bain_red")))
print("ok band layout, section styles, fit warnings (header, table header, category labels), row_titles (stacked sections)")
# own design (user request 2026-11-12): style from a deck incl. its corner logo, saved in my_styles/ (here a temp dir), as the default
import tempfile; sys.path.insert(0, str(root / "tools")); import style_from_deck as sfd
from slidegen import core as core_
_ms = core_.MY_STYLES; core_.MY_STYLES = pathlib.Path(tempfile.mkdtemp())
try:
    src_ = build1(json.loads((root / "examples" / "composite_logo.pt.json").read_text("utf8")), "t_logo_src")
    r_ = sfd.from_deck(str(out / "t_logo_src.pptx"), "Clube X", default=True)
    st_ = r_["clube_x"]; assert r_["_default"] == "clube_x" and st_["logo"]["position"] == "footer-right" and pathlib.Path(st_["logo"]["file"]).exists(), r_
    assert core_.default_theme() == "clube_x" and "clube_x" in build.themes(), "saved style is listed and is the default"
    sfd.save("clube_x", {"primary": "1F6FEB", "heading_font": "Georgia"})
    assert core_.load_theme()["primary"] == "1F6FEB" and core_.load_theme()["heading_font"] == "Georgia", "no theme -> the user's default style"
    try: sfd.save("clube_x", {"not_a_token": 1}); assert False, "unknown token must be refused"
    except ValueError: pass
    nt_ = {k: v for k, v in json.loads((root / "examples" / "composite_coldchain.pt.json").read_text("utf8")).items() if k != "theme"}
    pics_ = [x for x in build1(nt_, "t_default_style") if x.shape_type == 13]
    assert any(abs(x.height / 914400 - st_["logo"]["height"]) < 0.02 for x in pics_), "the default style's logo is drawn"
finally:
    core_.MY_STYLES = _ms
print("ok own design: style + logo from a deck, default style, tokens by hand")
# per-bar colours (user request 2026-11-12, GD slide): growth blue, falls red; a coloured negative bar must not turn white
pc_ = {"type": "composite", "lang": "pt", "headline": "Telhado cresce 8% e usinas remotas caem 32% a 65% em 2026, puxando o total para -10%", "layout": "1", "source": "Dados ilustrativos",
       "panels": [{"id": "a", "kind": "chart", "chart": {"kind": "bar", "categories": ["A", "B", "C"], "series": [{"name": "s", "values": [8, -32, -10]}], "point_colors": ["1F3A5F", "B5462B", ""]}}]}
ch_ = [x for x in build1(pc_, "t_point_colors") if x.has_chart][0].chart._chartSpace.xml
assert ch_.count("B5462B") == 1 and ch_.count('invertIfNegative val="0"') >= 3, "two coloured points + the series, all non-inverting"
print("ok point_colors")
