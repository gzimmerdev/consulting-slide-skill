"""Your own slide design: derive a style from any deck (.pptx or .pdf), or set colours / fonts / a logo by hand.
Styles are saved in my_styles/styles.json (gitignored; logos in my_styles/<name>/) and merged with the built-in ones.

  py -3 tools/style_from_deck.py DECK --save NAME [--default]      style from a deck (colours, fonts, title, corners, repeated logo)
  py -3 tools/style_from_deck.py --set NAME key=value ... [--logo FILE [--logo-position footer-right|footer-left|top-right]] [--default]
  py -3 tools/style_from_deck.py --default NAME                     make NAME the style every slide without "theme" uses
  py -3 tools/style_from_deck.py --list                             styles (built-in + yours) and the default
  py -3 tools/style_from_deck.py DECK                               only print what would be derived

.pptx: reads the XML (fills, fonts, title runs, rounded vs square shapes, pictures repeated on most slides or on the layouts).
.pdf : reads the PDF text layer + vector drawings + images with PyMuPDF.
Only measurable tokens are set; the rest stay default (docs/styles.md lists every token). Preview a style on a sample slide:
  py -3 build.py examples/composite_coldchain.pt.json -o out/style_NAME.pptx --theme NAME
"""
import sys, json, re, colorsys, collections, zipfile, pathlib, posixpath, shutil
from lxml import etree

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P_ = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R_ = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from slidegen import core      # noqa: E402


def saturated(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    _, l, s = colorsys.rgb_to_hls(r, g, b)
    return s > 0.35 and 0.15 < l < 0.85


def pick_primary(weights):
    cands = [(w, c) for c, w in weights.items() if saturated(c)]
    return max(cands)[1] if cands else "404040"


def series_from(weights, primary):
    """Other frequent saturated colours close in hue to the primary, ordered dark -> light (archive rule)."""
    def hls(h): return colorsys.rgb_to_hls(*(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)))
    ph = hls(primary)[0]
    near = [c for c, w in sorted(weights.items(), key=lambda kv: -kv[1])
            if saturated(c) and min(abs(hls(c)[0] - ph), 1 - abs(hls(c)[0] - ph)) < 0.06][:4]
    return sorted(set(near) | {primary}, key=lambda c: hls(c)[1])[:4] if len(near) >= 3 else None


def from_pptx(path):
    z = zipfile.ZipFile(path); names = z.namelist()
    th = etree.fromstring(z.read(sorted(n for n in names if re.match(r"ppt/theme/theme\d+\.xml$", n))[0]))
    major = th.find(f".//{A}majorFont/{A}latin").get("typeface"); minor = th.find(f".//{A}minorFont/{A}latin").get("typeface")
    fills, fonts, shapes = collections.Counter(), collections.Counter(), collections.Counter()
    titles = []
    for n in names:
        if not re.match(r"ppt/slides/slide\d+\.xml$", n): continue
        x = etree.fromstring(z.read(n))
        for sp in x.iter("{http://schemas.openxmlformats.org/presentationml/2006/main}sp"):
            g = sp.find(f".//{A}prstGeom")
            if g is not None and g.get("prst") in ("rect", "roundRect"): shapes[g.get("prst")] += 1
            f = sp.find(f"{{http://schemas.openxmlformats.org/presentationml/2006/main}}spPr/{A}solidFill/{A}srgbClr")
            if f is not None: fills[f.get("val").upper()] += 1
            off = sp.find(f".//{A}off")
            runs = list(sp.iter(f"{A}r"))
            for r in runs:
                rp = r.find(f"{A}rPr"); t = (r.find(f"{A}t").text or "")
                if rp is None: continue
                lf = rp.find(f"{A}latin")
                if lf is not None:
                    tf = {"+mj-lt": major, "+mn-lt": minor}.get(lf.get("typeface"), lf.get("typeface")); fonts[tf] += len(t)
            if off is not None and int(off.get("y")) < 0.15 * 6858000 and runs:
                txt = "".join((r.find(f"{A}t").text or "") for r in runs)
                rp = runs[0].find(f"{A}rPr")
                if len(txt) > 30 and rp is not None and rp.get("sz"):
                    c = rp.find(f"{A}solidFill/{A}srgbClr")
                    titles.append((int(rp.get("sz")) / 100, rp.get("b") == "1", c.get("val").upper() if c is not None else "1A1A1A"))
    return fills, fonts, titles, shapes


def from_pdf(path):
    import fitz
    d = fitz.open(path); fills, fonts, titles = collections.Counter(), collections.Counter(), []
    for page in d:
        H = page.rect.height; scale = 7.5 / (H / 72)                      # pt on page -> pt on a 7.5in-tall slide
        for dr in page.get_drawings():
            if dr.get("fill") and dr["rect"].width * dr["rect"].height < 0.6 * page.rect.width * H:
                h = "".join(f"{round(v * 255):02X}" for v in dr["fill"][:3]); fills[h] += dr["rect"].width * dr["rect"].height
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                for s in ln["spans"]:
                    if not s["text"].strip(): continue
                    font = re.sub(r"^[A-Z]{6}\+", "", s["font"]); bold = "Bold" in font or bool(s["flags"] & 16)
                    base = re.sub(r"(PS)?MT$", "", re.split(r"[-,]", font)[0])   # ArialMT -> Arial
                    fonts[base] += len(s["text"])
                    if s["bbox"][1] < 0.15 * H and len(s["text"]) > 15:
                        titles.append((round(s["size"] * scale), bold, f"{s['color']:06X}"))
    return fills, fonts, titles, collections.Counter()


LOGO_EXT = (".png", ".jpg", ".jpeg", ".gif")      # formats PowerPoint pictures take reliably


def installed_fonts():
    """Font family names installed on this Windows machine (empty set elsewhere: not checked)."""
    if sys.platform != "win32": return set()
    import subprocess
    r = subprocess.run(["powershell", "-NoProfile", "-Command", "Add-Type -AssemblyName System.Drawing; (New-Object System.Drawing.Text.InstalledFontCollection).Families | % { $_.Name }"],
                       capture_output=True, text=True)
    return {x.strip() for x in r.stdout.splitlines() if x.strip()}


def missing_fonts(style):
    have = installed_fonts()
    return sorted({style.get(k) for k in ("heading_font", "body_font") if style.get(k)} - have) if have else []


def _corner(x, y, w, h, W, H):
    """Logos sit in a corner: centre in the outer 30% across and the top or bottom 20%."""
    cx, cy = (x + w / 2) / W, (y + h / 2) / H
    inside = x >= -0.01 * W and y >= -0.01 * H and x + w <= 1.01 * W and y + h <= 1.01 * H      # designers park colour palettes off the slide
    return inside and (cx < 0.3 or cx > 0.7) and (cy < 0.2 or cy > 0.8)


def _where(cx, cy, w, h, W, H):
    """Logo position token from the picture box (EMU or pt, same unit as the page W x H)."""
    if cy + h / 2 < 0.3 * H: return "top-right"
    return "footer-left" if cx + w / 2 < 0.5 * W else "footer-right"


def logo_pptx(path):
    """(image bytes, extension, position, height in) of a picture on the slide layouts/master or on >= 40% of the slides; else None."""
    z = zipfile.ZipFile(path); names = set(z.namelist())
    pres = etree.fromstring(z.read("ppt/presentation.xml")); sz = pres.find(f"{P_}sldSz")
    W, H = int(sz.get("cx")), int(sz.get("cy"))
    slides = [n for n in names if re.match(r"ppt/slides/slide\d+\.xml$", n)]
    hits = collections.Counter(); box = {}; use = collections.Counter()      # slides using each layout (a layout's picture counts that often)
    for n in slides:
        rel = posixpath.join(posixpath.dirname(n), "_rels", posixpath.basename(n) + ".rels")
        for r in etree.fromstring(z.read(rel)) if rel in names else []:
            if r.get("Type", "").endswith("/slideLayout"): use[posixpath.normpath(posixpath.join(posixpath.dirname(n), r.get("Target")))] += 1
    for n in sorted(names):
        if not re.match(r"ppt/(slides/slide|slideLayouts/slideLayout|slideMasters/slideMaster)\d+\.xml$", n): continue
        rel = posixpath.join(posixpath.dirname(n), "_rels", posixpath.basename(n) + ".rels")
        if rel not in names: continue
        rels = {r.get("Id"): posixpath.normpath(posixpath.join(posixpath.dirname(n), r.get("Target"))) for r in etree.fromstring(z.read(rel))}
        for pic in etree.fromstring(z.read(n)).iter(f"{P_}pic"):
            b = pic.find(f".//{A}blip"); xf = pic.find(f"{P_}spPr/{A}xfrm"); off = xf.find(f"{A}off") if xf is not None else None; ext = xf.find(f"{A}ext") if xf is not None else None
            if b is None or off is None or ext is None or b.get(f"{R_}embed") not in rels: continue
            x, y, w, h = (int(v) for v in (off.get("x"), off.get("y"), ext.get("cx"), ext.get("cy")))
            if w * h > 0.06 * W * H or not _corner(x, y, w, h, W, H): continue    # a photo / chart / icon in the body, not a logo
            m = rels[b.get(f"{R_}embed")]
            if posixpath.splitext(m)[1].lower() not in LOGO_EXT or h < 0.15 * 914400 or m not in names or len(z.read(m)) < 2000: continue      # vector fragments / tiny marks are not logos
            hits[m] += 1 if "/slides/" in n else use[n] if "slideLayout" in n else len(slides)      # layout: as often as slides use it; master: every slide
            box.setdefault(m, (x, y, w, h))
    if not hits: return None
    m, c = hits.most_common(1)[0]
    if c < (1 if len(slides) < 3 else max(2, 0.4 * len(slides))) or m not in names: return None      # short decks: one small picture is enough
    x, y, w, h = box[m]
    return z.read(m), posixpath.splitext(m)[1].lower(), _where(x, y, w, h, W, H), round(max(0.2, min(0.7, h / 914400)), 2)


def logo_pdf(path):
    """Same for a PDF: an image drawn on >= 40% of the pages."""
    import fitz
    d = fitz.open(path); hits = collections.Counter(); box = {}
    for page in d:
        W, H = page.rect.width, page.rect.height
        for im in page.get_images(full=True):
            for r in page.get_image_rects(im[0])[:1]:
                if r.width * r.height > 0.06 * W * H or not _corner(r.x0, r.y0, r.width, r.height, W, H) or r.height / H * 7.5 < 0.15 or d.extract_image(im[0])["ext"] not in ("png", "jpeg", "jpg", "gif"): continue
                hits[im[0]] += 1; box.setdefault(im[0], (r.x0, r.y0, r.width, r.height, W, H))
    if not hits: return None
    xref, c = hits.most_common(1)[0]
    if c < (1 if len(d) < 3 else max(2, 0.4 * len(d))): return None
    x, y, w, h, W, H = box[xref]; img = d.extract_image(xref)
    return img["image"], "." + img["ext"], _where(x, y, w, h, W, H), round(max(0.2, min(0.7, h / H * 7.5)), 2)


def save(name, tokens, logo=None, logo_position=None, logo_height=None, default=False):
    """Create/update style NAME in my_styles/styles.json. logo = image file path or (bytes, ext). Returns the saved style."""
    key = re.sub(r"[^a-z0-9_]+", "_", name.lower()).strip("_") or "my_style"
    known = set().union(*(v.keys() for v in core.themes().values())) | {"logo", "_src"}
    bad = [k for k in tokens if k not in known]
    if bad: raise ValueError(f"unknown tokens {bad}; see docs/styles.md")
    core.MY_STYLES.mkdir(parents=True, exist_ok=True); st = core.my_styles()
    cur = {**st.get(key, {}), **tokens}
    if logo is not None:
        d = core.MY_STYLES / key; d.mkdir(exist_ok=True)
        if isinstance(logo, tuple): f = d / f"logo{logo[1]}"; f.write_bytes(logo[0])
        else: f = d / f"logo{pathlib.Path(logo).suffix.lower()}"; shutil.copy(logo, f)
        fp = f.resolve(); fp = fp.relative_to(ROOT).as_posix() if fp.is_relative_to(ROOT) else str(fp)
        cur["logo"] = {"file": fp, "position": logo_position or (cur.get("logo") or {}).get("position", "footer-right"),
                       "height": logo_height or (cur.get("logo") or {}).get("height", 0.35)}
    st[key] = cur
    if default: st["_default"] = key
    (core.MY_STYLES / "styles.json").write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf8")
    return {key: cur, "_default": st.get("_default")}


def from_deck(path, name, default=False):
    """derive() + the repeated logo, saved as style NAME."""
    st = derive(path); lg = (logo_pdf if str(path).lower().endswith(".pdf") else logo_pptx)(path)
    return save(name, st, logo=(lg[0], lg[1]) if lg else None, logo_position=lg[2] if lg else None, logo_height=lg[3] if lg else None, default=default)


def _value(v):
    try: return json.loads(v)
    except ValueError: return v.lstrip("#").upper() if re.fullmatch(r"#?[0-9A-Fa-f]{6}", v) else v


def derive(path):
    p = str(path).lower()
    fills, fonts, titles, shapes = from_pdf(path) if p.endswith(".pdf") else from_pptx(path)
    primary = pick_primary(fills)
    tcount = collections.Counter(titles).most_common(1)
    size, bold, tcol = tcount[0][0] if tcount else (20, True, "1A1A1A")
    top_fonts = [f for f, _ in fonts.most_common(4) if f and not f.startswith("+")]
    style = {"_src": f"derived from {pathlib.Path(path).name}", "primary": primary,
             "title_color": tcol if (saturated(tcol) or tcol in ("000000", "1A1A1A")) else "1A1A1A",
             "title_size": max(16, min(28, round(size))), "title_bold": bool(bold),
             "heading_font": top_fonts[0] if top_fonts else "Arial", "body_font": top_fonts[0] if top_fonts else "Arial"}
    if shapes and shapes["roundRect"] > shapes["rect"]: style["corners"] = "rounded"
    ser = series_from(fills, primary)
    if ser: style["series"] = ser
    return style


if __name__ == "__main__":
    import argparse
    sys.stdout.reconfigure(encoding="utf8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("deck", nargs="?"); ap.add_argument("--save"); ap.add_argument("--set", nargs="+", metavar=("NAME", "KEY=VALUE"))
    ap.add_argument("--logo"); ap.add_argument("--logo-position", choices=["footer-right", "footer-left", "top-right"]); ap.add_argument("--logo-height", type=float)
    ap.add_argument("--default", nargs="?", const=True); ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for n, v in core.themes().items(): print(f"{n:18} {v['primary']}  {v['heading_font']}/{v['body_font']}" + ("  (yours)" if n in core.my_styles() else ""))
        print("default:", core.default_theme())
    elif a.set:
        toks = dict(kv.split("=", 1) for kv in a.set[1:]); toks = {k: _value(v) for k, v in toks.items()}
        print(json.dumps(save(a.set[0], toks, logo=a.logo, logo_position=a.logo_position, logo_height=a.logo_height, default=a.default is True), indent=1, ensure_ascii=False))
    elif a.deck and a.save:
        r = from_deck(a.deck, a.save, default=a.default is True); print(json.dumps(r, indent=1, ensure_ascii=False))
        st = next(v for k, v in r.items() if k != "_default")
        if "logo" not in st: print("no repeated logo found in the deck: add one with --set NAME --logo FILE")
        for f in missing_fonts(st): print(f"WARNING font '{f}' is not installed here: slides fall back to another font. Install it, or --set NAME heading_font=Arial body_font=Arial")
    elif a.deck:
        print(json.dumps(derive(a.deck), indent=1, ensure_ascii=False))
    elif isinstance(a.default, str):
        if a.default not in core.themes(): sys.exit(f"unknown style {a.default}")
        st = core.my_styles(); st["_default"] = a.default; core.MY_STYLES.mkdir(parents=True, exist_ok=True)
        (core.MY_STYLES / "styles.json").write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf8"); print("default style:", a.default)
    else: ap.print_help()
