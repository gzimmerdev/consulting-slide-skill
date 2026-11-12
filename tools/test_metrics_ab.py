"""Self-check: py -3 -I tools/test_metrics_ab.py"""
import os, sys, json, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout_metrics as lm
import ab_judge as ab

# metrics on a built example
g = lm.metrics(*lm.pptx_slide_els(os.path.join(lm.ROOT, "out", "composite_orbital.pptx")))
assert g["n_boxes"] > 3 and 0 <= g["overlap"] < 1 and 0 <= g["align_any"] <= 1 and g["words"] > 10 and g["font_min_body"] > 0, g
assert -1 <= g["balance_lr"] <= 1
d = lm.distance(g, g)
assert d["structure_distance"] == 0, d
# synthetic: two overlapping text boxes -> overlap > 0, aligned pair -> align_left 1
t = lambda x, y: dict(kind="text", sub="body", role="body", words=5, font_sizes=[12.0], bbox=[x, y, 3, 1])
m = lm.metrics([t(1, 2), t(1, 2.5)])
assert m["overlap"] > 0 and m["align_left"] == 1.0, m

# AB round trip with fake answers into a temp dir
tmp = tempfile.mkdtemp()
ab.AB = tmp
ab.ORIG = os.path.join(tmp, "o")
ab.GEN = os.path.join(tmp, "g")
os.makedirs(ab.ORIG)
os.makedirs(ab.GEN)
from PIL import Image
for i in ("s01", "s02"):
    Image.new("RGB", (1600, 900), "white").save(os.path.join(ab.ORIG, i + ".png"))
    Image.new("RGB", (1600, 898), "grey").save(os.path.join(ab.GEN, i + ".png"))
ab.make()
key = json.load(open(os.path.join(tmp, "key.json")))
assert len(key) == 4 and len(os.listdir(tmp)) >= 6
sizes = {Image.open(os.path.join(tmp, p + ".png")).size for p in key}
assert len(sizes) == 1, sizes
# judge A finds 3 of 4 originals, always-A judge B -> 50%
ans_a = [dict(pair_id=p, pick=(k["original"] if i else ("A" if k["original"] == "B" else "B")), confidence=2, giveaway="x") for i, (p, k) in enumerate(key.items())]
ans_b = [dict(pair_id=p, pick="A", confidence=1, giveaway="") for p in key]
json.dump(ans_a, open(os.path.join(tmp, "answers_a.json"), "w"))
json.dump(ans_b, open(os.path.join(tmp, "answers_b.json"), "w"))
r = ab.score()
assert r["n"] == 8 and abs(r["overall"] - 5 / 8) < 1e-9, r
assert os.path.exists(os.path.join(tmp, "report.md"))
shutil.rmtree(tmp)
print("ok")
