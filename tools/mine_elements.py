"""Mine the pptx archive for element types, connector types and layouts (no vision, XML only).
usage: py -3 -I tools/mine_elements.py            -> analysis/elements.jsonl
       py -3 -I tools/mine_elements.py --selftest

One JSON line per slide: deck, slide, is_content, elements, exhibits, layout, links, density.
Conventions: inches (2 dp) everywhere; group transforms applied (nested too); rotation ignored.

is_content heuristic: the slide has an action-title-like text (a title placeholder, or the top-most
text in the top 25% of the slide that is >=5 words and >40% of slide width) with >=5 words, AND at
least one body element (chart/table/smartart/ole/cluster/picture>1% area/text with role body|label/
shape with text) besides title, source, page number, footer, connectors, dividers and backgrounds.
Covers, agendas, dividers and team pages have short titles ("Agenda", "Nossa equipe") -> false.

layout rule: exhibits whose centre lies in the body area (between title bottom and source top) are
grouped into rows (y-interval overlap) and columns (x-interval overlap):
 1 row -> "1" | "<n>col";  1 column -> "T|B" | "<n>row";  2 columns of (1,k) -> "L|R<k>" / "L<k>|R";
 2 rows of (1,k) -> "T|B<k>" / "T<k>|B"; equal-count rows -> "<r>x<c>"; else "other"; none -> "0".
"""
import sys, os, re, json, time, math, zipfile, statistics
from lxml import etree
from pptx import Presentation

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
C = '{http://schemas.openxmlformats.org/drawingml/2006/chart}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
MC = '{http://schemas.openxmlformats.org/markup-compatibility/2006}'
DGM = '{http://schemas.openxmlformats.org/drawingml/2006/diagram}'
EMU = 914400.0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
inch = lambda e: e / EMU
r2 = lambda v: round(v, 2)
SRC_RE = re.compile(r'^\W*(fonte|fontes|source|sources|nota|notas|note|notes)\b', re.I)
NAME_HINT = re.compile(r'(?P<map>mapa|\bmap\b)|(?P<logo>logo)|(?P<icon>icon|graphic\b|gr.fico\b)|(?P<chart_image>chart)', re.I)  # PT-BR PowerPoint names SVG icons 'Gráfico n'
ARROW_PRST = re.compile(r'arrow|chevron|homeplate', re.I)
PLOT_TAGS = ('barChart', 'bar3DChart', 'lineChart', 'line3DChart', 'pieChart', 'pie3DChart', 'ofPieChart',
             'doughnutChart', 'areaChart', 'area3DChart', 'scatterChart', 'bubbleChart', 'radarChart',
             'stockChart', 'surfaceChart', 'surface3DChart')



ADDIN = ("tclayout", "data - do not delete")      # chart add-in objects: their ProgID and data-stub name
def _addin(s): s = (s or "").lower(); return any(k in s for k in ADDIN)

def kids(el):
    """children of a shape tree, expanding mc:AlternateContent into its Choice (else Fallback)."""
    for c in el:
        if c.tag == MC + 'AlternateContent':
            ch = c.find(MC + 'Choice')
            if ch is None:
                ch = c.find(MC + 'Fallback')
            if ch is not None:
                yield from kids(ch)
        else:
            yield c


def get_xfrm(el):
    """-> (x,y,cx,cy,flipH,flipV,chOff,chExt) in EMU or None."""
    xf = None
    for c in el:
        if c.tag in (P + 'spPr', P + 'grpSpPr'):
            xf = c.find(A + 'xfrm')
        elif c.tag == P + 'xfrm':
            xf = c
        if xf is not None:
            break
    if xf is None:
        return None
    off, ext = xf.find(A + 'off'), xf.find(A + 'ext')
    if off is None or ext is None:
        return None
    co, ce = xf.find(A + 'chOff'), xf.find(A + 'chExt')
    g = lambda e, k: int(e.get(k))
    return (g(off, 'x'), g(off, 'y'), g(ext, 'cx'), g(ext, 'cy'), xf.get('flipH') in ('1', 'true'),
            xf.get('flipV') in ('1', 'true'),
            (g(co, 'x'), g(co, 'y')) if co is not None else None,
            (g(ce, 'cx'), g(ce, 'cy')) if ce is not None else None)


def tx_of(el):
    return el.find(P + 'txBody')


def para_info(tb):
    """text, words, [(size,chars)], n_paragraphs, bullets, bold_leadin, first run bold."""
    if tb is None:
        return '', 0, [], 0, False, False
    lst = tb.find(A + 'lstStyle')
    dsz = None
    if lst is not None:
        d = lst.find(f'{A}lvl1pPr/{A}defRPr')
        if d is not None and d.get('sz'):
            dsz = int(d.get('sz')) / 100
    texts, sizes, npar, bullets, lead = [], [], 0, False, False
    for p in tb.findall(A + 'p'):
        runs = [r for r in p if r.tag in (A + 'r', A + 'fld')]
        t = ''.join((r.findtext(A + 't') or '') for r in runs)
        if not t.strip():
            continue
        npar += 1
        texts.append(t)
        pp = p.find(A + 'pPr')
        if pp is not None:
            if pp.find(A + 'buChar') is not None or pp.find(A + 'buAutoNum') is not None:
                bullets = True
            elif pp.find(A + 'buNone') is None and pp.get('marL') and int(pp.get('indent') or 0) < 0:
                bullets = True
        for r in runs:
            rp = r.find(A + 'rPr')
            n = len((r.findtext(A + 't') or '').strip())
            if not n:
                continue
            s = int(rp.get('sz')) / 100 if rp is not None and rp.get('sz') else dsz
            if s:
                sizes.append((s, n))
        if len(runs) >= 2:
            r0, r1 = runs[0].find(A + 'rPr'), runs[1].find(A + 'rPr')
            b0 = r0 is not None and r0.get('b') in ('1', 'true')
            b1 = r1 is not None and r1.get('b') in ('1', 'true')
            if b0 and not b1 and (runs[1].findtext(A + 't') or '').strip():
                lead = True
    text = '\n'.join(texts)
    return text, len(text.split()), sizes, npar, bullets, lead


def fill_line(sp):
    """(filled, transparent, outlined, dashed) from spPr (+ style refs)."""
    spPr = sp.find(P + 'spPr')
    filled, transp = False, False
    if spPr is not None:
        if spPr.find(A + 'noFill') is not None:
            filled = False
        elif spPr.find(A + 'solidFill') is not None:
            filled = True
            al = spPr.find(f'{A}solidFill//{A}alpha')
            transp = al is not None and int(al.get('val')) < 60000
        elif spPr.find(A + 'gradFill') is not None or spPr.find(A + 'blipFill') is not None:
            filled = True
        else:
            st = sp.find(P + 'style')
            fr = st.find(A + 'fillRef') if st is not None else None
            filled = fr is not None and fr.get('idx') not in (None, '0')
    outlined, dashed = False, False
    ln = spPr.find(A + 'ln') if spPr is not None else None
    if ln is not None and ln.find(A + 'noFill') is not None:
        outlined = False
    elif ln is not None and (ln.find(A + 'solidFill') is not None or ln.find(A + 'gradFill') is not None):
        outlined = True
    else:
        st = sp.find(P + 'style')
        lr = st.find(A + 'lnRef') if st is not None else None
        outlined = lr is not None and lr.get('idx') not in (None, '0') and ln is None
    if ln is not None:
        pd = ln.find(A + 'prstDash')
        dashed = pd is not None and pd.get('val') not in ('solid',)
    return filled, transp, outlined, dashed


def chart_info(blob):
    x = etree.fromstring(blob)
    pa = x.find(f'.//{C}plotArea')
    plots = [e for e in pa if etree.QName(e).localname in PLOT_TAGS] if pa is not None else []
    if not plots:
        return dict(sub='unknown', n_series=0, n_categories=0, data_labels=False, point_color_overrides=False)
    subs = []
    for p in plots:
        n = etree.QName(p).localname.replace('3D', '')
        if n == 'barChart':
            d = p.find(C + 'barDir')
            g = p.find(C + 'grouping')
            subs.append(('column' if d is None or d.get('val') == 'col' else 'bar') + '_' +
                        (g.get('val') if g is not None else 'clustered'))
        elif n in ('lineChart', 'areaChart'):
            g = p.find(C + 'grouping')
            gv = g.get('val') if g is not None else 'standard'
            subs.append(n[:-5] + ('' if gv in ('standard', 'clustered') else '_' + gv))
        else:
            subs.append(n[:-5].lower().replace('ofpie', 'of_pie'))
    sub = subs[0] if len(set(subs)) == 1 else 'combo'
    sers = list(x.iter(C + 'ser'))
    ncat = 0
    if sers:
        for tag in ('cat', 'xVal', 'val', 'yVal'):
            c = sers[0].find(f'{C}{tag}//{C}ptCount')
            if c is not None:
                ncat = int(c.get('val'))
                break
    dl = any(d.get('val') in ('1', 'true') for d in x.iterfind(f'.//{C}dLbls/{C}showVal')) or \
        any(d.get('val') in ('1', 'true') for d in x.iterfind(f'.//{C}dLbls/{C}showPercent'))
    return dict(sub=sub, n_series=len(sers), n_categories=ncat, data_labels=dl,
                point_color_overrides=x.find(f'.//{C}ser/{C}dPt') is not None,
                **({'plot_types': sorted(set(subs))} if sub == 'combo' else {}))


class Ctx:
    """per-slide mining state."""

    def __init__(self, slide, W, H):
        self.slide, self.W, self.H = slide, W, H  # W,H inches
        self.els, self.n, self.idmap = [], 0, {}
        self.ph_xfrm = {}
        try:
            for ph in slide.slide_layout.placeholders:
                if ph.left is not None:
                    self.ph_xfrm[ph.placeholder_format.idx] = (ph.left, ph.top, ph.width, ph.height)
        except Exception:
            pass
        self.tc = False


def walk(ctx, parent, T):
    sx, ox, sy, oy = T
    top = parent.getparent() is not None and parent.tag == P + 'spTree' and parent.getparent().tag == P + 'cSld'
    for el in kids(parent):
        tag = el.tag
        if tag in (P + 'nvGrpSpPr', P + 'grpSpPr', P + 'extLst'):
            continue
        nv = el.find(f'{P}nvSpPr/{P}cNvPr')
        for t in ('nvCxnSpPr', 'nvPicPr', 'nvGraphicFramePr', 'nvGrpSpPr'):
            if nv is None:
                nv = el.find(f'{P}{t}/{P}cNvPr')
        name = (nv.get('name') if nv is not None else '') or ''
        xid = nv.get('id') if nv is not None else None
        xf = get_xfrm(el)
        if tag == P + 'grpSp':
            if _addin(name):
                ctx.tc = True
            if xf is None:
                walk(ctx, el, T)
                continue
            x, y, cx, cy, _, _, co, ce = xf
            co = co or (x, y)
            ce = ce or (cx, cy)
            kx = cx / ce[0] if ce[0] else 1
            ky = cy / ce[1] if ce[1] else 1
            T2 = (sx * kx, sx * (x - co[0] * kx) + ox, sy * ky, sy * (y - co[1] * ky) + oy)
            walk(ctx, el, T2)
            continue
        if tag not in (P + 'sp', P + 'cxnSp', P + 'pic', P + 'graphicFrame'):
            continue
        if xf is None:
            ph = el.find(f'{P}nvSpPr/{P}nvPr/{P}ph')
            if ph is not None and int(ph.get('idx') or 0) in ctx.ph_xfrm and sx == 1:
                x, y, cx, cy = ctx.ph_xfrm[int(ph.get('idx') or 0)]
                xf = (x, y, cx, cy, False, False, None, None)
            else:
                continue
        x, y, cx, cy, fh, fv, _, _ = xf
        X0, Y0 = sx * x + ox, sy * y + oy
        X1, Y1 = sx * (x + cx) + ox, sy * (y + cy) + oy
        bb = [inch(min(X0, X1)), inch(min(Y0, Y1)), inch(abs(X1 - X0)), inch(abs(Y1 - Y0))]
        # flips: group scale may be negative, combine with own flip
        flipx = fh ^ (X1 < X0)
        flipy = fv ^ (Y1 < Y0)
        if not (0 <= bb[0] + bb[2] / 2 <= ctx.W and 0 <= bb[1] + bb[3] / 2 <= ctx.H):
            continue  # parked off-slide
        e = make_element(ctx, el, tag, name, bb, flipx, flipy)
        if e is None:
            continue
        ctx.n += 1
        e['id'] = f'e{ctx.n}'
        e['bbox'] = [r2(v) for v in bb]
        e['_xid'] = xid
        if ctx.tc:
            pass
        ctx.els.append(e)
        if xid:
            ctx.idmap[xid] = e['id']
        if el.get('_in_group'):
            e['in_group'] = True


def make_element(ctx, el, tag, name, bb, flipx, flipy):
    W, H = ctx.W, ctx.H
    tl = name.lower()
    tcn = _addin(tl)
    if tag == P + 'pic':
        area = bb[2] * bb[3] / (W * H)
        d = dict(kind='picture', sub='picture', aspect=r2(bb[2] / bb[3]) if bb[3] else None,
                 area_share=round(area, 3), name=name)
        m = NAME_HINT.search(name)
        if m:
            d['name_hint'] = m.lastgroup  # map | logo | chart_image (e.g. "Gráfico 3") | icon (e.g. "Graphic 5")
        return d
    if tag == P + 'graphicFrame':
        gd = el.find(f'{A}graphic/{A}graphicData')
        uri = (gd.get('uri') if gd is not None else '') or ''
        if uri.endswith('/chart'):
            rid = gd.find(C + 'chart').get(R + 'id')
            try:
                d = chart_info(ctx.slide.part.related_part(rid).blob)
            except Exception:
                d = dict(sub='unreadable', n_series=0, n_categories=0, data_labels=False, point_color_overrides=False)
            return dict(kind='chart', **d)
        if 'chartex' in uri:
            return dict(kind='chart', sub='chartex', n_series=0, n_categories=0, data_labels=False,
                        point_color_overrides=False)
        if uri.endswith('/table'):
            tbl = gd.find(A + 'tbl')
            sizes = [(int(r.get('sz')) / 100, 1) for r in tbl.iter(A + 'rPr') if r.get('sz')]
            words = sum(len(''.join(t.text or '' for t in tc.iter(A + 't')).split()) for tc in tbl.iter(A + 'tc'))
            return dict(kind='table', sub='table', rows=len(tbl.findall(A + 'tr')),
                        cols=len(tbl.findall(f'{A}tblGrid/{A}gridCol')), words=words, _sizes=sizes)
        if 'diagram' in uri:
            n = None
            try:
                dm = gd.find(f'{DGM}relIds').get(R + 'dm')
                n = sum(1 for p in etree.fromstring(ctx.slide.part.related_part(dm).blob).iter(DGM + 'pt')
                        if p.get('type') in (None, 'node'))
            except Exception:
                pass
            return dict(kind='smartart', sub='smartart', n_nodes=n)
        ole = gd.find(f'.//{P}oleObj') if gd is not None else None
        if ole is not None or 'ole' in uri:
            prog = (ole.get('progId') if ole is not None else '') or ''
            tc = _addin(prog + tl) or _addin(etree.tostring(el).decode('utf8', 'ignore')[:4000])
            if tc:
                ctx.tc = True
            return dict(kind='ole', sub='chart_addin' if tc else 'ole', prog_id=prog, name=name,
                        tiny=bb[2] * bb[3] < 0.05)
        return dict(kind='ole', sub='graphicframe:' + uri.rsplit('/', 1)[-1], name=name, tiny=False)
    # sp / cxnSp
    spPr = el.find(P + 'spPr')
    geom = spPr.find(A + 'prstGeom') if spPr is not None else None
    prst = geom.get('prst') if geom is not None else ('custom' if spPr is not None and spPr.find(A + 'custGeom') is not None else None)
    is_line = tag == P + 'cxnSp' or (prst and re.match(r'(line|straightConnector|bentConnector|curvedConnector)', prst))
    if is_line:
        ln = spPr.find(A + 'ln') if spPr is not None else None
        he = ln.find(A + 'headEnd') if ln is not None else None
        te = ln.find(A + 'tailEnd') if ln is not None else None
        hs = he.get('type', 'none') if he is not None else 'none'
        ts = te.get('type', 'none') if te is not None else 'none'
        fl, _, _, dashed = fill_line(el)
        w, h = bb[2], bb[3]
        orient = 'horizontal' if h < 0.15 * max(w, 0.01) or h < 0.03 else 'vertical' if w < 0.15 * max(h, 0.01) or w < 0.03 else 'diagonal'
        x0, y0, x1, y1 = bb[0], bb[1], bb[0] + w, bb[1] + h
        bx, ex = (x1, x0) if flipx else (x0, x1)
        by, ey = (y1, y0) if flipy else (y0, y1)
        arrow_at = 'both' if hs != 'none' and ts != 'none' else 'start' if hs != 'none' else 'end' if ts != 'none' else 'none'
        cn = el.find(f'{P}nvCxnSpPr/{P}cNvCxnSpPr')
        st = cn.find(A + 'stCxn') if cn is not None else None
        en = cn.find(A + 'endCxn') if cn is not None else None
        return dict(kind='connector', sub=(prst or 'line'), head_end=hs, tail_end=ts, arrow_at=arrow_at, dashed=dashed,
                    orientation=orient, _begin=(bx, by), _end=(ex, ey),
                    _st=st.get('id') if st is not None else None, _en=en.get('id') if en is not None else None,
                    **({'tc': True} if ctx.tc else {}))
    tb = tx_of(el)
    text, words, sizes, npar, bullets, lead = para_info(tb)
    filled, transp, outlined, dashed = fill_line(el)
    ph = el.find(f'{P}nvSpPr/{P}nvPr/{P}ph')
    pht = (ph.get('type') or 'body') if ph is not None else None
    if ph is not None or (words and not filled and not outlined and prst in (None, 'rect', 'custom') and
                          (el.find(f'{P}nvSpPr/{P}cNvSpPr') is not None)):
        if not words:
            return None
        role = 'body'
        if pht in ('title', 'ctrTitle'):
            role = 'title'
        elif pht == 'sldNum':
            role = 'page_number'
        elif pht in ('ftr', 'dt'):
            role = 'footer'
        elif SRC_RE.match(text) and bb[1] > 0.75 * H:
            role = 'source'
        elif re.fullmatch(r'\s*\d{1,3}\s*', text) and bb[1] > 0.88 * H:
            role = 'page_number'
        elif words <= 4:
            role = 'label'
        return dict(kind='text', sub=role, role=role, words=words, font_sizes=sorted({s for s, _ in sizes}),
                    n_paragraphs=npar, bullets=bullets, bold_leadin=lead, _sizes=sizes)
    if prst is None and not words and not filled and not outlined:
        return None
    d = dict(kind='shape', preset=prst or 'none', has_text=bool(words), words=words, filled=filled,
             transparent=transp, outlined=outlined, dashed=dashed, _sizes=sizes, _text=text.strip()[:12])
    if text:
        d['font_sizes'] = sorted({s for s, _ in sizes})
    w, h = bb[2], bb[3]
    short = d['_text']
    area_frac = w * h / (W * H)
    if area_frac > 0.8 and not words:
        d['sub'] = 'background'
    elif prst in ('ellipse', 'rect', 'roundRect', 'flowChartConnector') and w <= 0.6 and h <= 0.6 and 1 <= len(short) <= 2 and '\n' not in short:
        d['sub'] = 'badge'
    elif prst and ARROW_PRST.search(prst):
        d['sub'] = 'arrow_shape'
    elif prst in ('rect', 'line') and min(w, h) <= 0.03 and max(w, h) >= 0.5:
        d['sub'] = 'divider'
    elif not filled and (outlined or transp) and prst in ('rect', 'roundRect') and not words:
        d['sub'] = 'highlight_candidate'  # confirmed later (needs overlap with an exhibit)
    elif filled and prst in ('rect', 'roundRect', 'round2SameRect', 'snip1Rect') and words:
        d['sub'] = 'card'
    else:
        d['sub'] = 'plain'
    if tcn or ctx.tc:
        d['tc'] = True
    return d


def inter(a, b):
    w = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    h = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def gap(a, b):
    dx = max(a[0] - (b[0] + b[2]), b[0] - (a[0] + a[2]), 0)
    dy = max(a[1] - (b[1] + b[3]), b[1] - (a[1] + a[3]), 0)
    return math.hypot(dx, dy)


def union(bs):
    x0, y0 = min(b[0] for b in bs), min(b[1] for b in bs)
    x1, y1 = max(b[0] + b[2] for b in bs), max(b[1] + b[3] for b in bs)
    return [r2(x0), r2(y0), r2(x1 - x0), r2(y1 - y0)]


def label(e, byid):
    k = e['kind']
    if k == 'cluster':
        return {'card': 'cards', 'arrow_shape': 'steps', 'badge': 'badges', 'composite': 'shapechart'}[e['sub_of']]
    if k == 'picture':
        return e.get('name_hint') if e.get('name_hint') in ('map', 'logo', 'chart_image') else 'picture'
    if k == 'shape':
        return e['sub'] if e['sub'] not in ('plain', 'highlight_candidate') else 'shape'
    return k


def clusters(ctx):
    """size-similar, adjacent cards/badges/arrow-shapes (>=3) -> kind=cluster."""
    out = []
    for cls in ('card', 'arrow_shape', 'badge'):
        cand = [e for e in ctx.els if e['kind'] == 'shape' and e['sub'] == cls and (cls != 'arrow_shape' or e['has_text'])]
        par = list(range(len(cand)))

        def f(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i
        for i in range(len(cand)):
            for j in range(i + 1, len(cand)):
                a, b = cand[i]['bbox'], cand[j]['bbox']
                sim = abs(a[2] - b[2]) <= 0.25 * max(a[2], b[2]) and abs(a[3] - b[3]) <= 0.25 * max(a[3], b[3])
                if sim and gap(a, b) <= 0.6:
                    par[f(i)] = f(j)
        groups = {}
        for i in range(len(cand)):
            groups.setdefault(f(i), []).append(cand[i])
        for g in groups.values():
            if len(g) < 3:
                continue
            bbs = [m['bbox'] for m in g]
            mh, mw = statistics.median(b[3] for b in bbs), statistics.median(b[2] for b in bbs)
            cy = [b[1] + b[3] / 2 for b in bbs]
            cx = [b[0] + b[2] / 2 for b in bbs]
            sub = 'row' if max(cy) - min(cy) <= 0.4 * mh else 'column' if max(cx) - min(cx) <= 0.4 * mw else 'grid'
            out.append(dict(kind='cluster', sub=sub, sub_of=cls, n=len(g), members=[m['id'] for m in g], bbox=union(bbs)))
    # composite: many small plain shapes + labels + lines glued together = a chart/diagram drawn from shapes
    # (chart add-in output, hand-built bars/maps). >=8 members, >=3 plain shapes, >=1.5 sq in.
    taken = {m for c in out for m in c['members']}
    cand = [e for e in ctx.els if e['id'] not in taken and (
        (e['kind'] == 'shape' and e['sub'] == 'plain') or (e['kind'] == 'text' and e['role'] == 'label') or
        (e['kind'] == 'connector' and e['arrow_at'] == 'none' and e['bbox'][2] * e['bbox'][3] < 25))]
    if len(cand) <= 700:
        par = list(range(len(cand)))

        def f2(i):
            while par[i] != i:
                par[i] = par[par[i]]
                i = par[i]
            return i
        for i in range(len(cand)):
            for j in range(i + 1, len(cand)):
                if gap(cand[i]['bbox'], cand[j]['bbox']) <= 0.12:
                    par[f2(i)] = f2(j)
        gr = {}
        for i in range(len(cand)):
            gr.setdefault(f2(i), []).append(cand[i])
        for g in gr.values():
            bbs = [m['bbox'] for m in g]
            u = union(bbs)
            if len(g) >= 8 and sum(1 for m in g if m['kind'] == 'shape') >= 3 and u[2] * u[3] >= 1.5:
                out.append(dict(kind='cluster', sub='composite', sub_of='composite', n=len(g), members=[m['id'] for m in g], bbox=u))
    # badge clusters beside a card cluster are annotations of that list, not an exhibit
    cards = [c for c in out if c['sub_of'] not in ('badge', 'composite')]
    for c in out:
        c['_annot'] = c['sub_of'] == 'badge' and any(
            inter([c['bbox'][0] - .5, c['bbox'][1] - .5, c['bbox'][2] + 1, c['bbox'][3] + 1], k['bbox']) > 0 for k in cards)
    for c in out:
        ctx.n += 1
        c['id'] = f'e{ctx.n}'
        ctx.els.append(c)


def groups_1d(items, lo, hi):
    """items: [(idx,start,end)] -> list of lists (merge when overlap >= 50% of item length)."""
    gs = []
    for it in sorted(items, key=lambda t: t[1]):
        for g in gs:
            ov = min(it[2], g['e']) - max(it[1], g['s'])
            if ov >= 0.5 * (it[2] - it[1]) and ov > 0:
                g['m'].append(it[0])
                g['s'], g['e'] = min(g['s'], it[1]), max(g['e'], it[2])
                break
        else:
            gs.append(dict(s=it[1], e=it[2], m=[it[0]]))
    return [g['m'] for g in gs]


def layout_sig(bbs):
    n = len(bbs)
    if n == 0:
        return '0'
    if n == 1:
        return '1'
    rows = groups_1d([(i, b[1], b[1] + b[3]) for i, b in enumerate(bbs)], 0, 0)
    cols = groups_1d([(i, b[0], b[0] + b[2]) for i, b in enumerate(bbs)], 0, 0)
    if len(rows) == 1:
        return f'{n}col' if n <= 4 else '5+col'
    if len(cols) == 1:
        return 'T|B' if n == 2 else f'{n}row' if n <= 4 else '5+row'
    cc = sorted(len(c) for c in cols)
    rc = sorted(len(r) for r in rows)
    if len(cols) == 2 and cc[0] == 1:
        left = min(cols, key=lambda c: min(bbs[i][0] for i in c))
        return f'L|R{cc[1]}' if len(left) == 1 else f'L{cc[1]}|R'
    if len(rows) == 2 and rc[0] == 1:
        topg = min(rows, key=lambda r: min(bbs[i][1] for i in r))
        return f'T|B{rc[1]}' if len(topg) == 1 else f'T{rc[1]}|B'
    if len(set(rc)) == 1 and rc[0] > 1:
        return f'{len(rows)}x{rc[0]}'
    return 'other'


def mine_slide(slide, W, H, deck='', idx=1):
    ctx = Ctx(slide, W, H)
    walk(ctx, slide.shapes._spTree, (1, 0, 1, 0))
    els = ctx.els
    # title: placeholder title, else top-most >=5-word text in top 25%
    if not any(e['kind'] == 'text' and e['role'] == 'title' for e in els):
        c = [e for e in els if e['kind'] == 'text' and e['role'] in ('body', 'label') and e['words'] >= 5
             and e['bbox'][1] < 0.25 * H and e['bbox'][2] > 0.4 * W]
        if c:
            t = min(c, key=lambda e: (e['bbox'][1], -max(e['font_sizes'] or [0])))
            t['role'] = t['sub'] = 'title'
    title = next((e for e in els if e['kind'] == 'text' and e['role'] == 'title'), None)
    # highlight boxes: unfilled/transparent outlined rect over a chart/table/picture/smartart
    big = [e for e in els if e['kind'] in ('chart', 'table', 'smartart', 'ole') or
           (e['kind'] == 'picture' and e['area_share'] > 0.04)]
    big = [e for e in big if not (e['kind'] == 'ole' and (e.get('tiny') or e['sub'] == 'chart_addin' and e['bbox'][2] * e['bbox'][3] < 0.05))]
    links = []
    for e in els:
        if e['kind'] == 'shape' and e['sub'] == 'highlight_candidate':
            ba = e['bbox'][2] * e['bbox'][3]
            best = max(big, key=lambda b: inter(e['bbox'], b['bbox']), default=None)
            if best and ba > 0 and inter(e['bbox'], best['bbox']) >= 0.5 * ba and ba <= 0.95 * best['bbox'][2] * best['bbox'][3]:
                e['sub'] = 'highlight_box'
                links.append(dict(type='highlight', box=e['id'], over=best['id'], pattern=f"{label(best, None)} + highlight_box"))
            else:
                e['sub'] = 'frame'
    clusters(ctx)
    mem2cl = {m: c['id'] for c in els if c['kind'] == 'cluster' for m in c['members']}
    byid = {e['id']: e for e in els}
    exh = list(big) + [e for e in els if e['kind'] == 'cluster' and not e['_annot']]
    exh_ids = [e['id'] for e in exh]
    # body area
    tb = title['bbox'][1] + title['bbox'][3] if title else 0.17 * H
    srcs = [e['bbox'][1] for e in els if e['kind'] == 'text' and e['role'] == 'source']
    bt, bb_ = min(tb, 0.4 * H), min(srcs) if srcs else 0.93 * H
    lay = layout_sig([e['bbox'] for e in exh if bt <= e['bbox'][1] + e['bbox'][3] / 2 <= bb_])
    # connector endpoints
    nonconn = [e for e in els if e['kind'] not in ('connector', 'cluster') and not (
        e['kind'] == 'text' and e['role'] in ('title', 'source', 'page_number', 'footer')) and
        not (e['kind'] == 'shape' and e['sub'] in ('background', 'divider', 'frame', 'highlight_box'))]

    def near(pt):
        best = None
        for e in nonconn:
            b = e['bbox']
            d = math.hypot(max(b[0] - pt[0], 0, pt[0] - b[0] - b[2]), max(b[1] - pt[1], 0, pt[1] - b[1] - b[3]))
            if d <= 0.3:
                k = (round(d, 2), b[2] * b[3])
                if best is None or k < best[0]:
                    best = (k, e['id'])
        return best[1] if best else None
    for e in els:
        if e['kind'] != 'connector':
            continue
        fr = ctx.idmap.get(e['_st']) if e['_st'] else None
        to = ctx.idmap.get(e['_en']) if e['_en'] else None
        fr = fr or near(e['_begin'])
        to = to or near(e['_end'])
        if e['arrow_at'] == 'start':
            fr, to = to, fr
        e['from'], e['to'] = fr, to
        if fr and to and fr != to:
            a, b = byid[mem2cl.get(fr, fr)], byid[mem2cl.get(to, to)]
            if a is not b:
                if e['arrow_at'] == 'none' and not (e['_st'] and e['_en']):
                    continue  # plain rules are decoration unless glued (stCxn+endCxn)
                links.append(dict(type='connector', **{'from': a['id'], 'to': b['id']}, arrow=e['arrow_at'] != 'none', dashed=e['dashed'],
                                  pattern=f"{label(a, byid)} -connector-> {label(b, byid)}" if e['arrow_at'] != 'none' else f"{label(a, byid)} -line- {label(b, byid)}"))
    # arrow shapes lying between two exhibits (not part of a steps cluster)
    for e in els:
        if e['kind'] == 'shape' and e['sub'] == 'arrow_shape' and e['id'] not in mem2cl:
            b = e['bbox']
            cx, cy = b[0] + b[2] / 2, b[1] + b[3] / 2
            pr = e['preset']
            vertical = 'down' in pr.lower() or 'up' in pr.lower()
            cand = [x for x in exh if x['kind'] != 'cluster' or True]
            if not vertical:
                L = [x for x in cand if x['bbox'][0] + x['bbox'][2] <= b[0] + 0.15 and x['bbox'][1] - .1 <= cy <= x['bbox'][1] + x['bbox'][3] + .1]
                Rr = [x for x in cand if x['bbox'][0] >= b[0] + b[2] - 0.15 and x['bbox'][1] - .1 <= cy <= x['bbox'][1] + x['bbox'][3] + .1]
                A_ = max(L, key=lambda x: x['bbox'][0] + x['bbox'][2], default=None)
                B_ = min(Rr, key=lambda x: x['bbox'][0], default=None)
            else:
                L = [x for x in cand if x['bbox'][1] + x['bbox'][3] <= b[1] + 0.15 and x['bbox'][0] - .1 <= cx <= x['bbox'][0] + x['bbox'][2] + .1]
                Rr = [x for x in cand if x['bbox'][1] >= b[1] + b[3] - 0.15 and x['bbox'][0] - .1 <= cx <= x['bbox'][0] + x['bbox'][2] + .1]
                A_ = max(L, key=lambda x: x['bbox'][1] + x['bbox'][3], default=None)
                B_ = min(Rr, key=lambda x: x['bbox'][1], default=None)
            if A_ and B_ and gap(A_['bbox'], b) <= 1.0 and gap(B_['bbox'], b) <= 1.0:
                if 'left' in pr.lower() or 'up' in pr.lower():
                    A_, B_ = B_, A_
                links.append(dict(type='arrow_between', arrow=e['id'], **{'from': A_['id'], 'to': B_['id']},
                                  pattern=f"{label(A_, byid)} -arrow-> {label(B_, byid)}"))
    for c in els:
        if c['kind'] == 'cluster' and c['sub_of'] == 'arrow_shape':
            pass
    # numbered cross references: same 1-2 char badge text in two places
    seen = {}
    for e in els:
        if e['kind'] == 'shape' and e['sub'] == 'badge':
            seen.setdefault(e['_text'], []).append(e)
    for t, es in seen.items():
        if len(es) >= 2 and any(gap(a['bbox'], b['bbox']) > 1.0 for a in es for b in es):
            links.append(dict(type='badge_xref', value=t, ids=[e['id'] for e in es], pattern='badge-xref'))
    # density
    skip = lambda e: e['kind'] == 'text' and e['role'] in ('title', 'source', 'page_number', 'footer')
    words = sum(e.get('words', 0) for e in els if e['kind'] in ('text', 'shape', 'table') and not (e['kind'] == 'text' and e['role'] == 'page_number'))
    sz = []
    for e in els:
        if e['kind'] in ('text', 'shape', 'table') and not skip(e):
            sz += e['_sizes']
    big_sz = sorted(s for s, n in sz for _ in range(1))
    mn = min((s for s, n in sz if n >= 3), default=None)
    med = None
    if sz:
        tot = sum(n for _, n in sz)
        acc = 0
        for s, n in sorted(sz):
            acc += n
            if acc >= tot / 2:
                med = s
                break
    gx, gy = 48, 27
    cov = tot_c = 0
    for i in range(gx):
        for j in range(gy):
            px, py = (i + .5) * W / gx, (j + .5) * H / gy
            if not bt <= py <= bb_:
                continue
            tot_c += 1
            for e in els:
                if e['kind'] in ('connector', 'cluster') or skip(e) or (e['kind'] == 'shape' and e['sub'] in ('background', 'divider', 'frame', 'highlight_box')):
                    continue
                b = e['bbox']
                if b[0] <= px <= b[0] + b[2] and b[1] <= py <= b[1] + b[3]:
                    cov += 1
                    break
    density = dict(words=words, exhibits=len(exh), min_font=mn, median_font=med, area_covered=round(cov / tot_c, 3) if tot_c else 0)
    # is_content
    tw = title.get('words', 0) if title else 0
    body = [e for e in els if (e['kind'] in ('chart', 'table', 'smartart', 'cluster')) or
            (e['kind'] == 'ole' and not e.get('tiny')) or
            (e['kind'] == 'picture' and e['area_share'] > 0.01) or
            (e['kind'] == 'text' and e['role'] in ('body', 'label')) or
            (e['kind'] == 'shape' and e['has_text'] and e['sub'] != 'background')]
    is_content = bool(title and tw >= 5 and title['bbox'][1] < 0.25 * H and body)
    # flags / cleanup
    blind = dict(chart_addin=ctx.tc or any(e['kind'] == 'ole' and e['sub'] == 'chart_addin' for e in els),
                 map_pictures=sum(1 for e in els if e['kind'] == 'picture' and e.get('name_hint') == 'map'),
                 big_pictures=sum(1 for e in els if e['kind'] == 'picture' and e['area_share'] > 0.04))
    for e in els:
        if e['kind'] == 'cluster':
            e['annotation'] = e['_annot']
        for k in [k for k in e if k.startswith('_')]:
            del e[k]
        if e['kind'] == 'shape' and e['sub'] == 'highlight_candidate':
            e['sub'] = 'frame'
    return dict(deck=deck, slide=idx, is_content=is_content, elements=els, exhibits=exh_ids, layout=lay,
                links=links, density=density, blind=blind)


def mine_deck(path, rel, out):
    prs = Presentation(path)
    if prs.slide_width < 12_000_000 or len(prs.slides) < 3:
        return None
    W, H = inch(prs.slide_width), inch(prs.slide_height)
    n = nc = err = 0
    for i, s in enumerate(prs.slides, 1):
        try:
            rec = mine_slide(s, W, H, rel, i)
        except Exception as ex:  # untrusted input: never abort the run
            err += 1
            rec = dict(deck=rel, slide=i, is_content=False, error=repr(ex)[:200], elements=[], exhibits=[], layout='0', links=[], density={}, blind={})
        n += 1
        nc += rec['is_content']
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return n, nc, err


def main():
    t0 = time.time()
    arch = os.path.join(ROOT, 'archive')
    os.makedirs(os.path.join(ROOT, 'analysis'), exist_ok=True)
    decks = sorted(os.path.join(d, f) for d, _, fs in os.walk(arch) for f in fs if f.lower().endswith('.pptx') and not f.startswith('~$'))
    tot = [0, 0, 0, 0]
    with open(os.path.join(ROOT, 'analysis', 'elements.jsonl'), 'w', encoding='utf8') as out:
        for p in decks:
            rel = os.path.relpath(p, arch).replace('\\', '/')
            t = time.time()
            try:
                r = mine_deck(p, rel, out)
            except Exception as ex:
                print(f'FAIL {rel}: {ex!r}')
                continue
            if r is None:
                print(f'skip {rel}')
                continue
            tot[0] += 1
            tot[1] += r[0]
            tot[2] += r[1]
            tot[3] += r[2]
            print(f'{rel[-60:]}: {r[0]} slides, {r[1]} content, {r[2]} errors, {time.time() - t:.1f}s', flush=True)
    print(f'decks={tot[0]} slides={tot[1]} content={tot[2]} errors={tot[3]} time={time.time() - t0:.0f}s')


def selftest():
    import tempfile
    from pptx.util import Inches
    from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    prs = Presentation()
    prs.slide_width, prs.slide_height = 12192000, 6858000
    s = prs.slides.add_slide(prs.slide_layouts[6])
    g = s.shapes.add_group_shape()
    g.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1), Inches(1), Inches(1), Inches(1))
    g.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(2), Inches(2), Inches(1), Inches(1))
    xf = g._element.grpSpPr.find(A + 'xfrm')  # group chOff=(1,1) chExt=(2,2) -> off (3,3) ext (4,4): scale 2
    xf.find(A + 'off').set('x', str(Inches(3))); xf.find(A + 'off').set('y', str(Inches(3)))
    xf.find(A + 'ext').set('cx', str(Inches(4))); xf.find(A + 'ext').set('cy', str(Inches(4)))
    a = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(5), Inches(1), Inches(1))
    b = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(4), Inches(5), Inches(1), Inches(1))
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(1.5), Inches(5.5), Inches(4), Inches(5.5))
    c.line._get_or_add_ln().append(etree.fromstring(f'<a:tailEnd xmlns:a="{A[1:-1]}" type="triangle"/>'))
    cd = CategoryChartData(); cd.categories = ['a', 'b']; cd.add_series('s1', (1, 2)); cd.add_series('s2', (3, 4))
    s.shapes.add_chart(XL_CHART_TYPE.COLUMN_STACKED, Inches(8), Inches(1), Inches(4), Inches(3), cd)
    path = os.path.join(tempfile.gettempdir(), 'mine_selftest.pptx')
    prs.save(path)
    rec = mine_slide(Presentation(path).slides[0], 13.333, 7.5)
    E = rec['elements']
    bbs = [e['bbox'] for e in E if e['kind'] == 'shape']
    assert [3.0, 3.0, 2.0, 2.0] in bbs and [5.0, 5.0, 2.0, 2.0] in bbs, bbs
    con = next(e for e in E if e['kind'] == 'connector')
    ra = next(e['id'] for e in E if e['bbox'] == [0.5, 5.0, 1.0, 1.0])
    rb = next(e['id'] for e in E if e['bbox'] == [4.0, 5.0, 1.0, 1.0])
    assert (con['from'], con['to']) == (ra, rb) and con['arrow_at'] == 'end', con
    ch = next(e for e in E if e['kind'] == 'chart')
    assert ch['sub'] == 'column_stacked' and ch['n_series'] == 2 and ch['n_categories'] == 2, ch
    assert ch['bbox'] == [8.0, 1.0, 4.0, 3.0]
    print('selftest ok')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        main()
