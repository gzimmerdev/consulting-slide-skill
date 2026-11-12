"""List archive PDFs that look like slide decks (landscape ~16:9 or 4:3 pages). usage: pdf_scan.py archive_dir"""
import sys, pathlib, fitz
root = pathlib.Path(sys.argv[1])
for f in sorted(root.rglob('*.pdf')):
    try: d = fitz.open(f)
    except Exception as e: print('BAD', f.name, e); continue
    if not d.page_count: continue
    r = d[0].rect; ar = r.width / r.height
    kind = 'deck16:9' if 1.6 < ar < 1.9 else 'deck4:3' if 1.25 < ar < 1.45 else 'doc'
    print(f"{kind:8} {d.page_count:4d}p  {str(f.relative_to(root))[29:]}")
