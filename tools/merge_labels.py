"""analysis/crops/labels_*.json + index.json + elements.jsonl -> analysis/elements_labeled.jsonl
usage: py -3 -I tools/merge_labels.py      (py -3 -I tools/merge_labels.py --selftest)
Element crops (A/B): element gets "vision": label. Body crops (C): slide gets "vision_body": [labels]."""
import os, sys, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND_SUB = {
    'chart': 'column stacked_column stacked100_column bar stacked_bar waterfall line area pie doughnut scatter bubble mekko gantt combo other',
    'map': 'world brazil region city other',
    'diagram': 'process flow tree matrix_2x2 funnel timeline venn cycle org pyramid other',
    'table': 'plain harvey_balls checkmarks heatmap',
}
KINDS = set(KIND_SUB) | set('photo icon logo screenshot text_block cards other'.split())
ANN = set('highlight_box cagr_arrow totals delta_label callout legend axis_labels data_labels connector_arrow numbered_badges'.split())


def check(l, known):
    """-> error string or None."""
    if not isinstance(l, dict) or l.get('crop_id') not in known:
        return 'unknown crop_id'
    if l.get('kind') not in KINDS:
        return 'bad kind'
    sub = l.get('sub')
    if sub is not None and sub not in KIND_SUB.get(l['kind'], '').split():
        return 'bad sub'
    if not isinstance(l.get('annotations', []), list) or not set(l.get('annotations', [])) <= ANN:
        return 'bad annotations'
    if l.get('confidence') not in ('high', 'med', 'low'):
        return 'bad confidence'
    return None


def merge(crops_dir, elements, out):
    index = {c['crop_id']: c for c in json.load(open(os.path.join(crops_dir, 'index.json'), encoding='utf8'))}
    good, bad = {}, 0
    for f in sorted(glob.glob(os.path.join(crops_dir, 'labels_*.json'))):
        for l in json.load(open(f, encoding='utf8')):
            err = check(l, index)
            if err:
                bad += 1
                print(f'skip {os.path.basename(f)} {l.get("crop_id") if isinstance(l, dict) else l!r}: {err}')
            else:
                good[l['crop_id']] = l
    el, body = {}, {}
    for cid, l in good.items():
        c = index[cid]
        if c['element_id']:
            el[(c['deck'], c['slide'], c['element_id'])] = l
        else:
            body.setdefault((c['deck'], c['slide']), []).append(l)
    with open(out, 'w', encoding='utf8') as o:
        for line in open(elements, encoding='utf8'):
            r = json.loads(line)
            for e in r['elements']:
                v = el.get((r['deck'], r['slide'], e['id']))
                if v:
                    e['vision'] = v
            if (r['deck'], r['slide']) in body:
                r['vision_body'] = body[(r['deck'], r['slide'])]
            o.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(f'merged {len(good)} labels, skipped {bad}, missing {len(index) - len(good)} of {len(index)} crops')
    return len(good), bad


def selftest():
    import tempfile
    d = tempfile.mkdtemp()
    json.dump([{'crop_id': 'c0001', 'deck': 'd', 'slide': 1, 'element_id': 'e2', 'reason': 'A'}], open(d + '/index.json', 'w'))
    ok = {'crop_id': 'c0001', 'kind': 'chart', 'sub': 'waterfall', 'annotations': ['totals'], 'confidence': 'high'}
    json.dump([ok, dict(ok, crop_id='c9999'), dict(ok, sub='bogus')], open(d + '/labels_x.json', 'w'))
    open(d + '/el.jsonl', 'w').write(json.dumps({'deck': 'd', 'slide': 1, 'elements': [{'id': 'e1'}, {'id': 'e2'}]}) + '\n')
    assert merge(d, d + '/el.jsonl', d + '/out.jsonl') == (1, 2)
    r = json.loads(open(d + '/out.jsonl').read())
    assert r['elements'][1]['vision']['sub'] == 'waterfall' and 'vision' not in r['elements'][0]
    print('selftest ok')


if __name__ == '__main__':
    if '--selftest' in sys.argv:
        selftest()
    else:
        c = os.path.join(ROOT, 'analysis', 'crops')
        merge(c, os.path.join(ROOT, 'analysis', 'elements.jsonl'), os.path.join(ROOT, 'analysis', 'elements_labeled.jsonl'))
