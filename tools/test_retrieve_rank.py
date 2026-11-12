"""retrieve + rank checks. Run: py -3 -I tools/test_retrieve_rank.py"""
import json, sys, pathlib, tempfile
root = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(root), str(root / "tools")]
import retrieve, rank, compose

load = lambda p: json.loads((root / p).read_text("utf8"))
r = retrieve.nearest(load("examples/profiles/orbital.json"), k=3)
assert len(r["archive"]) == 3 and len(r["specs"]) == 3, r
assert all(a["png"] or a["how_to_get_image"] for a in r["archive"]) and all("summary" in a for a in r["archive"])
assert any(s["layout"] == "L|R2" or {"waterfall", "table", "stacked"} <= set(s["panels"]) for s in r["specs"]), r["specs"]
assert compose.suggest(load("examples/profiles/orbital.json"))["nearest"]["specs"][0]["layout"] == "L|R2"

a, b = load("examples/composite_orbital.pt.json"), load("examples/composite_2x3.pt.json")
with tempfile.TemporaryDirectory() as d:
    r1, r2 = rank.rank([a, b], out_dir=d), rank.rank([b, a], ["B", "A"], out_dir=d)
    assert [x["score"] for x in r1] == [x["score"] for x in r2] and r1[0]["reason"] and r1[0]["score"] <= r1[1]["score"], (r1, r2)
    assert not rank.rank([{"type": "composite"}], out_dir=d)[0].get("pptx")            # invalid spec ranks last, no crash

    png = pathlib.Path(d, "x.png"); png.write_bytes(b"png")
    i = retrieve.save_exemplar(a, str(png), "approved", dir=d)
    assert json.loads(pathlib.Path(d, f"{i}.json").read_text("utf8")) == a and pathlib.Path(d, f"{i}.png").read_bytes() == b"png"
    assert json.loads(pathlib.Path(d, "index.json").read_text("utf8"))[0]["note"] == "approved"
    assert retrieve.save_exemplar(a, str(png), dir=d) != i
print("ok")
