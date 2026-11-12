"""Replace archive deck paths and team names with codes in the shared (git-tracked) files, so the repo does not leak
other teams' competition material. The real names live only in private/ (gitignored):
  private/deck_names.json  {"D01": "<archive path of the deck>.pptx", ...}
  private/team_names.json  [["Team A", ["<team name>", ...]], ...]
Run after regenerating archive-derived files (mine_elements, merge_labels, grammar.py, summarize_elements, ...):
  py -3 -I tools/anonymize.py            (tracked + new non-ignored text files)   py -3 -I tools/anonymize.py FILE ...
Idempotent; prints the files it changed. Without private/ it does nothing (a shared copy has nothing to anonymise).
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "private"
TEXT = {".py", ".md", ".json", ".jsonl", ".ps1", ".txt", ".tsv"}


def rules():
    if not (P / "deck_names.json").exists(): return []
    decks = json.loads((P / "deck_names.json").read_text("utf8"))
    out = []
    for code, path in decks.items():      # full path, then file name, then file name without extension
        for s in (path, Path(path).name, Path(path).stem): out.append((s, f"{code}.pptx" if s != Path(path).stem else code))
    for code, names in json.loads((P / "team_names.json").read_text("utf8")) if (P / "team_names.json").exists() else []:
        out += [(n, code) for n in names]
    return sorted(out, key=lambda r: -len(r[0]))      # longest first: a deck path before the team name inside it


def anonymise(text, R):
    for a, b in R: text = re.sub(r"(?<![A-Za-z])" + re.escape(a) + r"(?![a-z])", lambda _: b, text)
    return text


def main(files):
    R = rules()
    if not R: print("no private/deck_names.json: nothing to anonymise"); return
    files = files or [f for f in subprocess.run(["git", "-C", str(ROOT), "ls-files", "--cached", "--others", "--exclude-standard"], capture_output=True, text=True).stdout.splitlines()
                      if Path(f).suffix in TEXT and not f.startswith(("private/", "assets/"))]
    for f in files:
        p = ROOT / f; s = p.read_text("utf8"); t = anonymise(s, R)
        if t != s: p.write_text(t, "utf8"); print("anonymised", f)


if __name__ == "__main__":
    main(sys.argv[1:])
