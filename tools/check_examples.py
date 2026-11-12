"""Validate every examples/*.json (incl. examples/catalog.json = {type: spec}) against the schema."""
import json, pathlib, sys
from jsonschema import Draft202012Validator
root=pathlib.Path(__file__).parent.parent; v=Draft202012Validator(json.loads((root/"schemas/archetypes.schema.json").read_text("utf8")))
sys.path.insert(0, str(root)); from build import resolve_excel   # validate what build.py validates (excel ranges resolved)
bad=0; seen=set()
for f in sorted((root/"examples").glob("*.json")):
    d=json.loads(f.read_text("utf8")); specs=d.values() if f.name=="catalog.json" else [d]
    for s in specs:
        s=resolve_excel(s, f.parent)
        errs=[e.message for e in v.iter_errors(s)]; seen.add(s["type"])
        print(("FAIL " if errs else "ok   ")+f.name+" "+s["type"], errs[:2]); bad+=bool(errs)
print(len(seen),"archetypes covered"); sys.exit(bad)
