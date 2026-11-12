"""Pixel comparison of an original slide vs a generated one (no judgement, just measurements).
usage: py -3 -I tools/compare_slides.py orig.png gen.png out_sidebyside.png  -> prints JSON metrics
side-by-side: original on top, generated below, both 1600x900."""
import sys, json
from PIL import Image, ImageFilter, ImageStat

def load(p): return Image.open(p).convert("RGB").resize((1600, 900))

def metrics(im):
    px = list(im.getdata()); n = len(px)
    white = sum(1 for r, g, b in px if r >= 250 and g >= 250 and b >= 250) / n          # pure white only
    light = sum(1 for r, g, b in px if 240 < min(r, g, b) and max(r, g, b) < 250) / n   # light-grey panels (F2F2F2 etc.) are NOT white
    dark = sum(1 for r, g, b in px if 0.3 * r + 0.59 * g + 0.11 * b < 80) / n
    hsv = list(im.convert("HSV").getdata())
    sat = sum(1 for h, s, v in hsv if s > 100 and v > 60) / n
    edges = ImageStat.Stat(im.convert("L").filter(ImageFilter.FIND_EDGES)).mean[0]
    q = im.quantize(8); pal = q.getpalette()[:24]; cnt = sorted(q.getcolors(), reverse=True)
    palette = [("%02X%02X%02X" % tuple(pal[i * 3:i * 3 + 3]), round(c / n, 3)) for c, i in cnt]
    grid = []                                            # ink share per cell, 4 rows x 6 cols
    for r in range(4):
        row = []
        for c in range(6):
            cell = im.crop((c * 266, r * 225, (c + 1) * 266, (r + 1) * 225)).convert("L")
            row.append(round(sum(1 for v in cell.getdata() if v < 250) / (266 * 225), 2))   # grey panels count as filled
        grid.append(row)
    return dict(white_share=round(white, 3), light_grey_share=round(light, 3), dark_share=round(dark, 3), saturated_share=round(sat, 3),
                edge_density=round(edges, 2), palette=palette, ink_grid_4x6=grid)

if __name__ == "__main__":
    a, b = load(sys.argv[1]), load(sys.argv[2])
    sbs = Image.new("RGB", (1600, 1810), "white"); sbs.paste(a, (0, 0)); sbs.paste(b, (0, 910)); sbs.save(sys.argv[3])
    ma, mb = metrics(a), metrics(b)
    diff = {k: round(mb[k] - ma[k], 3) for k in ("white_share", "light_grey_share", "dark_share", "saturated_share", "edge_density")}
    diff["ink_grid_diff"] = [[round(y - x, 2) for x, y in zip(ra, rb)] for ra, rb in zip(ma["ink_grid_4x6"], mb["ink_grid_4x6"])]
    print(json.dumps(dict(original=ma, generated=mb, generated_minus_original=diff), indent=1))
