"""analysis/elements.jsonl -> docs/element-library.md (content slides only).
usage: py -3 -I tools/summarize_elements.py"""
import os, json, statistics as st
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAB = os.path.join(ROOT, 'analysis', 'elements_labeled.jsonl')  # written by tools/merge_labels.py
HAS_VISION = os.path.exists(LAB)
R = [json.loads(l) for l in open(LAB if HAS_VISION else os.path.join(ROOT, 'analysis', 'elements.jsonl'), encoding='utf8')]
ALL = R
R = [r for r in R if r['is_content']]
short = lambda d: os.path.splitext(os.path.basename(d))[0][:26]
CL = {'card': 'cards', 'arrow_shape': 'steps', 'badge': 'badges', 'composite': 'shapechart'}


def lab(e):
    k = e['kind']
    if k == 'cluster':
        return CL[e['sub_of']]
    if k == 'picture':
        return e.get('name_hint') if e.get('name_hint') in ('map', 'logo', 'chart_image') else 'picture'
    return k


def table(head, rows):
    return '| ' + ' | '.join(head) + ' |\n|' + '---|' * len(head) + '\n' + '\n'.join('| ' + ' | '.join(str(c) for c in r) + ' |' for r in rows) + '\n'


nd = len({r['deck'] for r in R})
out = [f'# Element library (mined from {nd} decks, {len(R)} content slides of {len(ALL)} slides)\n',
       'Source: `analysis/elements.jsonl` via `tools/mine_elements.py`. Content slides only. "decks" = breadth (of %d).\n' % nd]

# ---- element vocabulary
cnt, dk = Counter(), defaultdict(set)
for r in R:
    for e in r['elements']:
        v = e.get('vision')
        if v and v['kind'] == 'chart':  # vision-resolved shape/picture charts count as charts
            key = ('chart', f"{v['sub'] or 'other'} (drawn/image)")
        elif v:
            key = ('vision:' + v['kind'], v['sub'] or '-')
        elif e['kind'] == 'ole' and e.get('tiny'):
            key = ('ole', 'chart add-in data stub (invisible)')
        elif e['kind'] == 'shape':
            key = ('shape', f"{e['sub']} / {e['preset']}") if e['sub'] in ('card', 'badge', 'arrow_shape', 'highlight_box', 'divider') else ('shape', f"plain / {e['preset']}")
        elif e['kind'] == 'connector':
            key = ('connector', f"{e['arrow_at']}-arrow, {'dashed' if e['dashed'] else 'solid'}, {e['orientation']}")
        elif e['kind'] == 'cluster':
            key = ('cluster', f"{CL[e['sub_of']]} / {e['sub']}")
        else:
            key = (e['kind'], e['sub'])
        cnt[key] += 1
        dk[key].add(r['deck'])
out.append('## 1. Element vocabulary\n')
out.append('### By kind / sub (ranked by deck breadth, then count)\n')
sl_by = Counter()
for r in R:
    for k in {(e['kind']) for e in r['elements']}:
        sl_by[k] += 1
rows = [(k, s, c, len(dk[(k, s)])) for (k, s), c in cnt.items() if k not in ('shape', 'connector') and not (k == 'text')]
rows += [('text', s, c, len(dk[('text', s)])) for (k, s), c in cnt.items() if k == 'text']
rows.sort(key=lambda t: (-t[3], -t[2]))
out.append(table(['kind', 'sub', 'count', 'decks'], rows))
for kind, title, n in (('shape', 'Shapes (sub-role / preset)', 25), ('connector', 'Connectors (arrow, dash, orientation)', 15)):
    rows = sorted(((s, c, len(dk[(k, s)])) for (k, s), c in cnt.items() if k == kind), key=lambda t: (-t[2], -t[1]))[:n]
    out.append(f'\n### {title}\n')
    out.append(table(['type', 'count', 'decks'], rows))
# chart details
ch = [e for r in R for e in r['elements'] if e['kind'] == 'chart']
tx = [e for r in R for e in r['elements'] if e['kind'] == 'text' and e['role'] in ('body', 'label')]
tb = [e for r in R for e in r['elements'] if e['kind'] == 'table']
pic = [e for r in R for e in r['elements'] if e['kind'] == 'picture']
out.append('\n### Detail stats\n')
pc = lambda a, b: f'{100 * a / b:.0f}%' if b else '-'
out.append(table(['item', 'value'], [
    ('native charts', f"{len(ch)} (median {st.median([e['n_series'] for e in ch]) if ch else 0} series, {st.median([e['n_categories'] for e in ch]) if ch else 0} categories)"),
    ('charts with data labels', pc(sum(e['data_labels'] for e in ch), len(ch))),
    ('charts with point-colour overrides (highlight)', pc(sum(e['point_color_overrides'] for e in ch), len(ch))),
    ('tables (median rows x cols)', f"{len(tb)} ({st.median([e['rows'] for e in tb]) if tb else 0} x {st.median([e['cols'] for e in tb]) if tb else 0})"),
    ('text boxes with bullets', pc(sum(e['bullets'] for e in tx if e['role'] == 'body'), sum(1 for e in tx if e['role'] == 'body'))),
    ('body text with bold lead-in', pc(sum(e['bold_leadin'] for e in tx if e['role'] == 'body'), sum(1 for e in tx if e['role'] == 'body'))),
    ('pictures total / >4% of slide', f"{len(pic)} / {sum(e['area_share'] > 0.04 for e in pic)}"),
    ('pictures named map / logo / chart_image / icon ("Gráfico n"/"Graphic n" = SVG icons)', ' / '.join(str(sum(e.get('name_hint') == h for e in pic)) for h in ('map', 'logo', 'chart_image', 'icon'))),
    ('...of which >4% of slide: map / logo / chart_image / icon', ' / '.join(str(sum(e.get('name_hint') == h and e['area_share'] > 0.04 for e in pic)) for h in ('map', 'logo', 'chart_image', 'icon'))),
]))

# ---- connector vocabulary
out.append('\n## 2. Connector vocabulary (links between elements)\n')
lk, ld, lex = Counter(), defaultdict(set), defaultdict(list)
for r in R:
    for l in r['links']:
        p = l['pattern']
        lk[p] += 1
        ld[p].add(r['deck'])
        if len(lex[p]) < 3 and (short(r['deck']), r['slide']) not in lex[p]:
            lex[p].append((short(r['deck']), r['slide']))
rows = [(f'`{p}`', c, len(ld[p]), '; '.join(f'{d} #{s}' for d, s in lex[p])) for p, c in sorted(lk.items(), key=lambda t: (-len(ld[t[0]]), -t[1]))[:40]]
out.append(table(['pattern', 'count', 'decks', 'examples (deck #slide)'], rows))
out.append('\nLink types: `connector` = cxnSp/line with arrowhead (or glued both ends); `arrow_between` = arrow_shape lying between two exhibits; '
           '`highlight` = unfilled outlined box over an exhibit; `badge_xref` = same 1-2 char badge in two places.\n')
tl = Counter(l['type'] for r in R for l in r['links'])
out.append(table(['link type', 'count', 'slides'], [(t, c, sum(any(l['type'] == t for l in r['links']) for r in R)) for t, c in tl.most_common()]))

# ---- layouts
out.append('\n## 3. Arrangements (layout signature of exhibits)\n')
lay = Counter(r['layout'] for r in R)
ld2 = defaultdict(set)
for r in R:
    ld2[r['layout']].add(r['deck'])
out.append(table(['layout', 'slides', 'share', 'decks'], [(l, c, pc(c, len(R)), len(ld2[l])) for l, c in lay.most_common(15)]))
out.append('\nTypical exhibit kind per position (ordered left-to-right, then top-to-bottom; most common kind and its share):\n')
rows = []
for l, c in lay.most_common(8):
    if l in ('0',):
        continue
    pos = defaultdict(Counter)
    for r in R:
        if r['layout'] != l:
            continue
        by = {e['id']: e for e in r['elements']}
        ex = sorted((by[i] for i in r['exhibits'] if i in by), key=lambda e: (round(e['bbox'][0] / 1.5), e['bbox'][1]))
        # keep only exhibits that are in the layout (centre in body) - approximated by count match
        for i, e in enumerate(ex):
            pos[i][lab(e)] += 1
    desc = ' ; '.join(f"{i + 1}: " + ', '.join(f'{k} {pc(v, sum(cn.values()))}' for k, v in cn.most_common(2)) for i, cn in sorted(pos.items())[:5])
    rows.append((l, c, desc))
out.append(table(['layout', 'slides', 'position: kind share'], rows))

# ---- density
out.append('\n## 4. Density (content slides)\n')
keys = [('words', 'words/slide'), ('exhibits', 'exhibits/slide'), ('min_font', 'min body font (pt)'), ('median_font', 'median body font (pt)'), ('area_covered', 'body area covered')]


def agg(rs, k):
    v = [r['density'][k] for r in rs if r['density'].get(k) is not None]
    return (round(st.mean(v), 2), round(st.median(v), 2)) if v else ('-', '-')


rows = [(n, *agg(R, k)) for k, n in keys]
out.append(table(['metric', 'mean', 'median'], rows))
out.append('\n### Per deck (mean)\n')
by = defaultdict(list)
for r in R:
    by[r['deck']].append(r)
rows = [(short(d), len(rs), *[agg(rs, k)[0] for k, _ in keys]) for d, rs in sorted(by.items())]
out.append(table(['deck', 'content slides'] + [n for _, n in keys], rows))

# ---- blind spots
tcs = sum(1 for r in ALL if r['blind'].get('chart_addin'))
out.append('\n## 5. Blind spots (need vision)\n')
out.append(table(['item', 'count'], [
    ('slides with chart add-in data stub (charts are drawn shapes, found as `shapechart`)', tcs),
    ('`shapechart` composites (shape-drawn charts/diagrams)', sum(1 for r in R for e in r['elements'] if e['kind'] == 'cluster' and e['sub_of'] == 'composite')),
    ('pictures >4% of slide (photo / map / chart image, unclassified)', sum(e['area_share'] > 0.04 for e in pic)),
    ('pictures named "chart" >4% of slide (chart images, not native)', sum(e.get('name_hint') == 'chart_image' and e['area_share'] > 0.04 for e in pic)),
    ('content slides with layout "0" (no exhibit found)', sum(r['layout'] == '0' for r in R)),
    ('decks skipped (not 16:9 or <3 slides)', 39 - len({r['deck'] for r in ALL})),
]))

# ---- vision labels
if HAS_VISION:
    out.append('\n## 6. Vision labels\n')
    VE = [(r, e) for r in R for e in r['elements'] if e.get('vision')]
    VB = [(r, v) for r in R for v in r.get('vision_body', [])]
    out.append(f'{len(VE)} labelled elements (shapechart / big picture) and {len(VB)} labelled body crops (slides with no exhibit found).\n')
    for title, items in (('Element crops', [(r['deck'], e['vision']) for r, e in VE]), ('Body crops (layout "0")', [(r['deck'], v) for r, v in VB])):
        if not items:
            continue
        kd, ann, adk, kdk = Counter(), Counter(), defaultdict(set), defaultdict(set)
        for d, v in items:
            k = (v['kind'], v['sub'] or '-')
            kd[k] += 1
            kdk[k].add(d)
            for a in v.get('annotations', []):
                ann[a] += 1
                adk[a].add(d)
        out.append(f'\n### {title}: kind / sub\n')
        out.append(table(['kind', 'sub', 'count', 'decks'], [(k, s, c, len(kdk[(k, s)])) for (k, s), c in sorted(kd.items(), key=lambda t: (-t[1], t[0]))]))
        out.append(f'\n### {title}: annotations\n')
        out.append(table(['annotation', 'count', 'share of crops', 'decks'], [(a, c, pc(c, len(items)), len(adk[a])) for a, c in ann.most_common()]))
        out.append(f"\nmulti-exhibit crops: {sum(bool(v.get('multi')) for _, v in items)}; confidence: " + ', '.join(f'{k} {n}' for k, n in Counter(v['confidence'] for _, v in items).most_common()) + '\n')
open(os.path.join(ROOT, 'docs', 'element-library.md'), 'w', encoding='utf8').write('\n'.join(out))
print('wrote docs/element-library.md', len(R), 'content slides')
