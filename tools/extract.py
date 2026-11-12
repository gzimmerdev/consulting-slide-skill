"""Per-deck design metrics via python-pptx + raw XML. usage: extract.py deck.pptx out.json"""
import sys, json, re, collections, zipfile
from pptx import Presentation
from pptx.util import Emu
from lxml import etree
A='{http://schemas.openxmlformats.org/drawingml/2006/main}'
C='{http://schemas.openxmlformats.org/drawingml/2006/chart}'
inch=lambda e: round(e/914400,2)
def rgb_of(run_el):
    s=run_el.find(f'{A}rPr/{A}solidFill/{A}srgbClr'); return s.get('val') if s is not None else None
p=Presentation(sys.argv[1]); W,H=p.slide_width,p.slide_height
if W<12e6: print('skip small'); sys.exit()
sz=collections.Counter(); fonts=collections.Counter(); cols=collections.Counter(); fills=collections.Counter()
titles=[]; foot=[]; pnum=[]; radii=collections.Counter(); shadows=0; lines=collections.Counter(); shp=collections.Counter()
for i,s in enumerate(p.slides,1):
    top=None
    for sh in s.shapes:
        shp[sh.shape_type.__str__().split('.')[-1].split(' ')[0] if sh.shape_type else 'none']+=1
        el=sh._element
        for g in el.iter(f'{A}prstGeom'):
            if g.get('prst')=='roundRect':
                gd=g.find(f'.//{A}gd'); radii[gd.get('fmla') if gd is not None else 'default16667']+=1
        if el.find('.//'+A+'outerShdw') is not None: shadows+=1
        sp=el.find('.//{http://schemas.openxmlformats.org/presentationml/2006/main}spPr')
        if sp is not None:
            f=sp.find(f'{A}solidFill/{A}srgbClr')
            if f is not None: fills[f.get('val')]+=1
            ln=sp.find(f'{A}ln')
            if ln is not None and ln.get('w'): lines[round(int(ln.get('w'))/12700,2)]+=1
        if not sh.has_text_frame: continue
        txt=sh.text_frame.text.strip()
        if not txt: continue
        for r in el.iter(f'{A}r'):
            rp=r.find(f'{A}rPr'); t=r.find(f'{A}t').text or ''
            if rp is None: continue
            n=len(t)
            if rp.get('sz'): sz[int(rp.get('sz'))/100]+=n
            lf=rp.find(f'{A}latin')
            if lf is not None: fonts[lf.get('typeface')]+=n
            c=rgb_of(r)
            if c: cols[c]+=n
        # candidates
        t0=sh.top if sh.top is not None else 0
        if t0<H*0.2 and sh.width>W*0.5 and len(txt)>25 and (top is None or t0<top[0]): top=(t0,sh,txt)
        low=txt.lower()
        if t0>H*0.85 and re.match(r'(fonte|source|sources|fontes|nota|note)',low): foot.append((i,inch(sh.left),inch(t0),inch(sh.width),inch(sh.height),[int(r.find(f"{A}rPr").get("sz"))/100 for r in el.iter(f"{A}r") if r.find(f"{A}rPr") is not None and r.find(f"{A}rPr").get("sz")][:1]))
        if re.fullmatch(r'\d{1,3}',txt) and t0>H*0.88 and sh.left>W*0.6: pnum.append((inch(sh.left),inch(t0),inch(sh.width)))
    if top:
        t0,sh,txt=top; r0=[r for r in sh._element.iter(f'{A}r')][0]; rp=r0.find(f'{A}rPr')
        titles.append(dict(slide=i,x=inch(sh.left),y=inch(sh.top),w=inch(sh.width),h=inch(sh.height),sz=int(rp.get('sz'))/100 if rp is not None and rp.get('sz') else None,b=rp.get('b') if rp is not None else None,col=rgb_of(r0),font=(rp.find(f'{A}latin').get('typeface') if rp is not None and rp.find(f'{A}latin') is not None else None),chars=len(txt),lines=txt.count('\n')+1,txt=txt[:110]))
# charts
z=zipfile.ZipFile(sys.argv[1]); charts=[]
for n in z.namelist():
    if re.match(r'ppt/charts/chart\d+\.xml$',n):
        x=etree.fromstring(z.read(n)); pa=x.find(f'.//{C}plotArea')
        kinds=[etree.QName(e).localname for e in pa if etree.QName(e).localname.endswith('Chart')]
        sc=[s.find(f'.//{A}srgbClr').get('val') if s.find(f'.//{C}spPr//{A}srgbClr') is not None else None for s in x.iter(f'{C}ser')]
        sc=[ (s.find(f'{C}spPr').find(f'.//{A}srgbClr').get('val') if s.find(f'{C}spPr') is not None and s.find(f'{C}spPr').find(f'.//{A}srgbClr') is not None else None) for s in x.iter(f'{C}ser')]
        dl=x.find(f'.//{C}dLblPos'); gw=x.find(f'.//{C}gapWidth'); ov=x.find(f'.//{C}overlap')
        charts.append(dict(kind=kinds,nser=len(sc),ser_colors=sc[:6],gridlines=x.find(f'.//{C}majorGridlines') is not None,dlblpos=dl.get('val') if dl is not None else None,gap=gw.get('val') if gw is not None else None,overlap=ov.get('val') if ov is not None else None,legend=x.find(f'.//{C}legend') is not None,legendpos=(x.find(f'.//{C}legendPos').get('val') if x.find(f'.//{C}legendPos') is not None else None),valax_deleted=(x.find(f'.//{C}valAx/{C}delete').get('val') if x.find(f'.//{C}valAx/{C}delete') is not None else None),fsz=[int(e.get('sz'))/100 for e in x.iter(f'{A}defRPr') if e.get('sz')][:3]))
out=dict(deck=sys.argv[1].split('/')[-1],slides=len(p.slides),size=(inch(W),inch(H)),sizes=sz.most_common(12),fonts=fonts.most_common(5),text_colors=cols.most_common(8),fills=fills.most_common(10),radii=radii.most_common(4),shadows=shadows,line_pt=lines.most_common(5),shapes=shp.most_common(8),titles=titles[:200],sources=foot[:6],pnum=pnum[:4],charts=charts)
json.dump(out,open(sys.argv[2],'w',encoding='utf8'),ensure_ascii=False,indent=1); print('ok',sys.argv[1][-40:],len(titles),'titles',len(charts),'charts')
