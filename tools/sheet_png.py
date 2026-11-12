"""Contact sheet from PNGs: sheet_png.py out_prefix cols per png1 png2 ...  -> out_prefix_sheetK.png"""
import sys
from PIL import Image
pre, cols, per, files = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4:]
W = 800
for k in range(0, len(files), per):
    ims = [Image.open(f).convert("RGB") for f in files[k:k + per]]
    ims = [im.resize((W, int(im.height * W / im.width))) for im in ims]; h = ims[0].height
    rows = (len(ims) + cols - 1) // cols; s = Image.new("RGB", (cols * (W + 6), rows * (h + 6)), "#666")
    for j, im in enumerate(ims): s.paste(im, ((j % cols) * (W + 6), (j // cols) * (h + 6)))
    s.save(f"{pre}_sheet{k // per + 1}.png"); print(f"{pre}_sheet{k // per + 1}.png")
