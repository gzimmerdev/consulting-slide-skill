"""Scan every .pptx in archive: slide size, theme colors/fonts, slide count, shape-type mix, chart count."""
import sys, zipfile, re, collections, pathlib, json
from lxml import etree
ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
root=pathlib.Path(sys.argv[1]); out=[]
for f in sorted(root.rglob('*.pptx')):
    try: z=zipfile.ZipFile(f)
    except Exception as e: print('BAD',f,e); continue
    n=z.namelist()
    pres=etree.fromstring(z.read('ppt/presentation.xml'))
    sz=pres.find('p:sldSz',ns); w,h=int(sz.get('cx')),int(sz.get('cy'))
    slides=[x for x in n if re.match(r'ppt/slides/slide\d+\.xml$',x)]
    charts=[x for x in n if re.match(r'ppt/charts/chart\d+\.xml$',x)]
    media=[x for x in n if x.startswith('ppt/media/')]
    # first theme
    th=sorted(x for x in n if re.match(r'ppt/theme/theme\d+\.xml$',x))
    cols={};fonts={}
    if th:
        t=etree.fromstring(z.read(th[0]))
        cs=t.find('.//a:clrScheme',ns)
        for c in cs:
            k=etree.QName(c).localname; ch=c[0]
            cols[k]=ch.get('val') or ch.get('lastClr')
        fs=t.find('.//a:fontScheme',ns)
        fonts={'major':fs.find('a:majorFont/a:latin',ns).get('typeface'),'minor':fs.find('a:minorFont/a:latin',ns).get('typeface')}
    # fonts actually used on slides
    used=collections.Counter(); srgb=collections.Counter(); native=0; pics=0; tables=0
    for s in slides:
        x=z.read(s).decode('utf8','ignore')
        used.update(re.findall(r'<a:latin typeface="([^"]+)"',x))
        srgb.update(re.findall(r'<a:srgbClr val="([0-9A-Fa-f]{6})"',x))
        pics+=x.count('<p:pic>'); tables+=x.count('<a:tbl>')
    out.append(dict(file=str(f.relative_to(root)),mb=round(f.stat().st_size/1e6,1),size_in=(round(w/914400,2),round(h/914400,2)),slides=len(slides),charts=len(charts),pics=pics,tables=tables,media=len(media),theme=cols,tfonts=fonts,used_fonts=used.most_common(4),top_rgb=srgb.most_common(6)))
json.dump(out,open(sys.argv[2],'w',encoding='utf8'),ensure_ascii=False,indent=1)
for o in out: print(f"{o['slides']:3d}sl {o['charts']:3d}ch {o['tables']:2d}tb {o['size_in']} {o['tfonts'].get('major')}/{o['tfonts'].get('minor')} acc1={o['theme'].get('accent1')} | {o['file'][-70:]}")
