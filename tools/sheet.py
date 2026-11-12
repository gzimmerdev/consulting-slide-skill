"""Contact sheets: sheet.py pdf outdir [cols=3] [per=12]"""
import sys, fitz, pathlib
from PIL import Image
pdf, out = sys.argv[1], pathlib.Path(sys.argv[2]); cols=int(sys.argv[3]) if len(sys.argv)>3 else 3; per=int(sys.argv[4]) if len(sys.argv)>4 else 12
out.mkdir(parents=True, exist_ok=True); d=fitz.open(pdf); W=560
ims=[]
for p in d:
    pm=p.get_pixmap(matrix=fitz.Matrix(W/p.rect.width, W/p.rect.width)); ims.append(Image.frombytes("RGB",(pm.width,pm.height),pm.samples))
for i in range(0,len(ims),per):
    ch=ims[i:i+per]; h=ch[0].height; rows=(len(ch)+cols-1)//cols
    s=Image.new("RGB",(cols*(W+6),rows*(h+6)),"#888")
    for j,im in enumerate(ch): s.paste(im,((j%cols)*(W+6),(j//cols)*(h+6)))
    s.save(out/f"sheet_{i//per+1:02d}.png")
print(pdf, len(ims),"pages")
