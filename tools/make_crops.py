"""Crop vision-needed items out of the archive decks and tile them 2x2 for labelling.
usage: py -3 -I tools/make_crops.py     (rerunnable; skips slides already exported)
A = cluster/composite (shape-drawn chart/diagram), B = picture >4% of slide, C = content slide with layout "0"
and no A/B item (body-area crop). Outputs: analysis/crops/slides/<slug>_<NN>.png, tiles/tile_NNN.png, index.json."""
import os, re, json, subprocess, hashlib, time, unicodedata
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CR = os.path.join(ROOT, 'analysis', 'crops')
SW, SH, PX = 13.333, 7.5, 1600 / 13.333
PAD, CELL = 0.1, (760, 420)


def slug(deck):
    base = unicodedata.normalize('NFKD', os.path.splitext(os.path.basename(deck))[0]).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', base).strip('-')[:30] + '-' + hashlib.md5(deck.encode('utf8')).hexdigest()[:4]


def body_bbox(r):
    top, bot = 1.3, 7.1
    for e in r['elements']:
        if e['kind'] != 'text':
            continue
        y, h = e['bbox'][1], e['bbox'][3]
        if e['sub'] == 'title' and y + h < 2.5:
            top = max(top, y + h)
        elif e['sub'] in ('source', 'footer', 'page_number') and y > 5.5:
            bot = min(bot, y)
    return [0, round(top, 2), SW, round(max(bot - top, 0.5), 2)]


_NF = os.path.join(ROOT, 'private', 'deck_names.json')
NAMES = json.load(open(_NF, encoding='utf8')) if os.path.exists(_NF) else {}


def collect():
    items = []
    for l in open(os.path.join(ROOT, 'analysis', 'elements.jsonl'), encoding='utf8'):
        r = json.loads(l); r['deck'] = NAMES.get(os.path.splitext(os.path.basename(r['deck']))[0], r['deck'])      # anonymised code -> real archive path (private/, local only)
        if not r['is_content']:
            continue
        ab = [(e, 'A') for e in r['elements'] if e['kind'] == 'cluster' and e['sub_of'] == 'composite']
        ab += [(e, 'B') for e in r['elements'] if e['kind'] == 'picture' and e['area_share'] > 0.04]
        for e, why in ab:
            items.append(dict(deck=r['deck'], slide=r['slide'], element_id=e['id'], reason=why, bbox=e['bbox']))
        if not ab and r['layout'] == '0':
            items.append(dict(deck=r['deck'], slide=r['slide'], element_id=None, reason='C', bbox=body_bbox(r)))
    items.sort(key=lambda i: (i['deck'], i['slide'], i['reason']))
    return items


def export(items):
    need = {}
    for i in items:
        png = os.path.join(CR, 'slides', f"{slug(i['deck'])}_{i['slide']:02d}.png")
        i['png'] = png
        if not os.path.exists(png):
            need.setdefault(i['deck'], {})[i['slide']] = png
    jobs = [dict(deck=os.path.normpath(os.path.join(ROOT, 'archive', d)), slides=[dict(n=n, png=p) for n, p in sorted(s.items())]) for d, s in need.items()]
    fails = []
    if jobs:
        jf = os.path.join(CR, 'jobs.json')
        json.dump(jobs, open(jf, 'w', encoding='utf-8-sig'), ensure_ascii=False)
        out = subprocess.run(['powershell', '-NoProfile', '-File', os.path.join(ROOT, 'tools', 'export_slides.ps1'), jf],
                             capture_output=True, text=True, encoding='utf8').stdout
        fails = [l for l in out.splitlines() if l.startswith('FAIL')]
    return fails


def font(sz):
    for f in ('arialbd.ttf', 'arial.ttf'):
        try:
            return ImageFont.truetype(f, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def main():
    t0 = time.time()
    os.makedirs(os.path.join(CR, 'slides'), exist_ok=True)
    os.makedirs(os.path.join(CR, 'tiles'), exist_ok=True)
    items = collect()
    fails = export(items)
    index, cells = [], []
    for n, i in enumerate(items, 1):
        if not os.path.exists(i['png']):
            continue
        x, y, w, h = i['bbox']
        im = Image.open(i['png']).convert('RGB')
        box = [max(0, (x - PAD) * PX), max(0, (y - PAD) * PX), min(im.width, (x + w + PAD) * PX), min(im.height, (y + h + PAD) * PX)]
        if box[2] - box[0] < 8 or box[3] - box[1] < 8:
            continue
        cells.append((i, im.crop(tuple(int(v) for v in box))))
    d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    f = font(28)
    for t in range(0, len(cells), 4):
        tile = Image.new('RGB', (CELL[0] * 2, CELL[1] * 2), (200, 200, 200))
        for k, (i, c) in enumerate(cells[t:t + 4]):
            cid = f'c{t + k + 1:04d}'
            s = min(CELL[0] / c.width, CELL[1] / c.height, 2.0)
            c = c.resize((max(1, int(c.width * s)), max(1, int(c.height * s))), Image.LANCZOS)
            ox, oy = (k % 2) * CELL[0], (k // 2) * CELL[1]
            tile.paste(c, (ox + (CELL[0] - c.width) // 2, oy + (CELL[1] - c.height) // 2))
            dr = ImageDraw.Draw(tile)
            dr.rectangle([ox + 2, oy + 2, ox + 2 + 110, oy + 2 + 38], fill='white', outline='black')
            dr.text((ox + 8, oy + 5), cid, fill='black', font=f)
            dr.rectangle([ox, oy, ox + CELL[0] - 1, oy + CELL[1] - 1], outline=(120, 120, 120))
            index.append(dict(crop_id=cid, tile=f'tile_{t // 4 + 1:03d}.png', cell=k, deck=i['deck'], slide=i['slide'],
                              element_id=i['element_id'], reason=i['reason'], bbox=i['bbox']))
        tile.save(os.path.join(CR, 'tiles', f'tile_{t // 4 + 1:03d}.png'))
    json.dump(index, open(os.path.join(CR, 'index.json'), 'w', encoding='utf8'), ensure_ascii=False, indent=1)
    from collections import Counter
    print('crops', Counter(i['reason'] for i in index), 'tiles', (len(index) + 3) // 4, f'{time.time() - t0:.0f}s')
    for fl in fails:
        print(fl)


if __name__ == '__main__':
    main()
