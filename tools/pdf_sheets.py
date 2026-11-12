"""Contact sheets for every slide-deck PDF that is a team solution not already reviewed.
usage: pdf_sheets.py archive_dir out_dir   -> out_dir/<NN_slug>/sheet_KK.png (16 slides each) + index.txt"""
import sys, re, pathlib, fitz
from PIL import Image
root, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
_SK = pathlib.Path(__file__).resolve().parent.parent / "private" / "pdf_skip.txt"
SKIP = re.compile(_SK.read_text("utf8").strip() if _SK.exists() else r"(?!)", re.I)      # file names to skip (local list: names archive decks)
idx = []; W, COLS, PER = 420, 4, 16
for f in sorted(root.rglob('*.pdf')):
    if SKIP.search(str(f)): continue
    try: d = fitz.open(f)
    except Exception: continue
    r = d[0].rect
    if not (1.25 < r.width / r.height < 1.9) or d.page_count < 5: continue
    n = len(idx) + 1; slug = f"{n:02d}_" + re.sub(r"[^A-Za-z0-9]+", "_", f.stem)[:40]
    dd = out / slug; dd.mkdir(exist_ok=True)
    ims = []
    for p in d:
        z = W / p.rect.width; pm = p.get_pixmap(matrix=fitz.Matrix(z, z))
        ims.append(Image.frombytes("RGB", (pm.width, pm.height), pm.samples))
    for i in range(0, len(ims), PER):
        ch = ims[i:i + PER]; h = ch[0].height; rows = (len(ch) + COLS - 1) // COLS
        s = Image.new("RGB", (COLS * (W + 4), rows * (h + 4)), "#777")
        for j, im in enumerate(ch): s.paste(im.resize((W, h)), ((j % COLS) * (W + 4), (j // COLS) * (h + 4)))
        s.save(dd / f"sheet_{i // PER + 1:02d}.png")
    idx.append(f"{slug}\t{d.page_count}p\t{f.relative_to(root)}")
(out / "index.txt").write_text("\n".join(idx), encoding="utf8"); print(len(idx), "decks"); print("\n".join(idx))
