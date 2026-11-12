#!/usr/bin/env py -3
"""Second brain, phase 0: generates brain/00-index (slides.tsv, decks.md, vocab.md) and brain/10-archive
(one note per deck) from analysis/elements_labeled.jsonl. Run from the project root: py -3 -I tools/build_brain.py
"""
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


def kebab(s: str) -> str:
    """Convert to kebab-case: lowercase, alphanum and hyphens only."""
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def deck_id_from_path(deck_path: str) -> str:
    """Extract competition, year, filename and kebab-case them."""
    parts = deck_path.split('/')
    competition = parts[1] if len(parts) > 1 else 'unknown'
    year = parts[2] if len(parts) > 2 else 'unknown'
    filename = parts[-1].replace('.pptx', '').replace('.ppt', '') if parts else 'unknown'
    return f"{kebab(competition)}-{kebab(year)}-{kebab(filename)}"


def parse_competition_year(deck_path: str) -> tuple[str, str]:
    parts = deck_path.split('/')
    competition = parts[1] if len(parts) > 1 else 'unknown'
    year = parts[2] if len(parts) > 2 else 'unknown'
    return competition, year


def main():
    input_path = Path('analysis/elements_labeled.jsonl')
    
    # Output directories
    brain_dir = Path('brain')
    idx_dir = brain_dir / '00-index'
    archive_dir = brain_dir / '10-archive'
    idx_dir.mkdir(parents=True, exist_ok=True)
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Accumulators
    slides_rows = []  # for slides.tsv
    deck_slides = defaultdict(list)  # deck_id -> list of slide dicts
    deck_meta = {}  # deck_id -> {competition, year, n_slides, n_content}
    exhibit_type_counts = Counter()
    layout_counts = Counter()
    competition_counts = Counter()
    year_counts = Counter()
    deck_paths = set()
    
    # Process JSONL line by line
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            slide_data = json.loads(line)
            
            deck_path = slide_data['deck']
            deck_paths.add(deck_path)
            did = deck_id_from_path(deck_path)
            competition, year = parse_competition_year(deck_path)
            
            slide_num = slide_data['slide']
            is_content = 1 if slide_data['is_content'] else 0
            layout = slide_data['layout']
            exhibits_ids = slide_data.get('exhibits', [])
            links = slide_data.get('links', [])
            density = slide_data.get('density', {})
            blind = slide_data.get('blind', {})
            elements = slide_data.get('elements', [])
            
            # Build element lookup
            elem_by_id = {e['id']: e for e in elements}
            
            # Get exhibit types
            exhibit_types = []
            for eid in exhibits_ids:
                elem = elem_by_id.get(eid)
                if elem:
                    etype = f"{elem['kind']}:{elem['sub']}"
                    exhibit_types.append(etype)
                    exhibit_type_counts[etype] += 1
            
            exhibits_str = '+'.join(exhibit_types) if exhibit_types else ''
            
            words = density.get('words', 0)
            median_font = density.get('median_font')
            area_covered = density.get('area_covered', 0.0)
            
            think_cell = 1 if blind.get('think_cell', False) else 0
            maps = blind.get('map_pictures', 0)
            
            # TSV row
            slides_rows.append([
                did, str(slide_num), str(is_content), layout, exhibits_str,
                str(len(links)), str(words),
                str(median_font) if median_font is not None else '',
                f"{area_covered:.3f}",
                str(think_cell), str(maps)
            ])
            
            # Deck slides for markdown
            slide_info = {
                'slide': slide_num,
                'content': is_content,
                'layout': layout,
                'exhibits': exhibits_str,
                'n_links': len(links),
                'words': words,
                'median_font': median_font,
                'area_covered': area_covered,
                'think_cell': think_cell,
                'maps': maps,
            }
            deck_slides[did].append(slide_info)
            
            # Update deck meta
            if did not in deck_meta:
                deck_meta[did] = {'deck_path': deck_path, 'competition': competition, 'year': year, 'n_slides': 0, 'n_content': 0}
            deck_meta[did]['n_slides'] += 1
            deck_meta[did]['n_content'] += is_content
            
            # Counters for vocab
            layout_counts[layout] += 1
            competition_counts[competition] += 1
            year_counts[year] += 1
    
    n_paths = len(deck_paths)
    assert len(deck_meta) == n_paths, f'deck_id collision: {n_paths} decks -> {len(deck_meta)} ids'

    # Sort slides within each deck by slide number
    for did in deck_slides:
        deck_slides[did].sort(key=lambda x: x['slide'])
    
    # 1. Write slides.tsv
    tsv_path = idx_dir / 'slides.tsv'
    with open(tsv_path, 'w', encoding='utf-8') as f:
        f.write("# Generated by tools/build_brain.py — do not edit by hand\n")
        f.write("deck_id\tslide\tcontent\tlayout\texhibits\tn_links\twords\tmedian_font\tarea_covered\tthink_cell\tmaps\n")
        for row in slides_rows:
            f.write('\t'.join(row) + '\n')
    
    # 2. Write brain/10-archive/<deck_id>.md
    for did, slides in deck_slides.items():
        meta = deck_meta[did]
        comp = meta['competition']
        year = meta['year']
        md_path = archive_dir / f"{did}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write("---\n")
            f.write("generated: true\n")
            f.write(f"deck: {meta['deck_path']}\n")
            f.write(f"competition: {comp}\n")
            f.write(f"year: {year}\n")
            f.write(f"n_slides: {meta['n_slides']}\n")
            f.write(f"n_content: {meta['n_content']}\n")
            f.write("---\n\n")
            f.write(f"This deck is from the **{comp}** competition, **{year}**, file **{Path(meta['deck_path']).name}**.\n\n")
            f.write("| slide | content | layout | exhibits | n_links | words | median_font | area_covered | think_cell | maps |\n")
            f.write("|-------|---------|--------|----------|---------|-------|-------------|--------------|------------|------|\n")
            for s in slides:
                med = str(s['median_font']) if s['median_font'] is not None else ''
                f.write(f"| {s['slide']} | {s['content']} | {s['layout']} | {s['exhibits']} | {s['n_links']} | {s['words']} | {med} | {s['area_covered']:.3f} | {s['think_cell']} | {s['maps']} |\n")
    
    # 3. Write brain/00-index/decks.md
    decks_md_path = idx_dir / 'decks.md'
    with open(decks_md_path, 'w', encoding='utf-8') as f:
        f.write("# Generated by tools/build_brain.py — do not edit by hand\n\n")
        f.write("# Decks Index\n\n")
        f.write("| deck_id | competition | year | slides | content |\n")
        f.write("|---------|-------------|------|--------|---------|\n")
        for did in sorted(deck_meta.keys()):
            meta = deck_meta[did]
            f.write(f"| [[{did}]] | {meta['competition']} | {meta['year']} | {meta['n_slides']} | {meta['n_content']} |\n")
    
    # 4. Write brain/00-index/vocab.md
    vocab_path = idx_dir / 'vocab.md'
    with open(vocab_path, 'w', encoding='utf-8') as f:
        f.write("# Generated by tools/build_brain.py — do not edit by hand\n\n")
        f.write("# Controlled Vocabulary\n\n")
        
        f.write("## Exhibit Types (kind:sub)\n\n")
        f.write("| type | count |\n")
        f.write("|------|-------|\n")
        for etype, count in sorted(exhibit_type_counts.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"| {etype} | {count} |\n")
        
        f.write("\n## Layouts\n\n")
        f.write("| layout | count |\n")
        f.write("|--------|-------|\n")
        for layout, count in sorted(layout_counts.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"| {layout} | {count} |\n")
        
        f.write("\n## Competitions\n\n")
        f.write("| competition | count |\n")
        f.write("|-------------|-------|\n")
        for comp, count in sorted(competition_counts.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"| {comp} | {count} |\n")
        
        f.write("\n## Years\n\n")
        f.write("| year | count |\n")
        f.write("|------|-------|\n")
        for year, count in sorted(year_counts.items(), key=lambda x: (-x[1], x[0])):
            f.write(f"| {year} | {count} |\n")
    
    # Report
    n_files = 1 + len(deck_slides) + 1 + 1  # slides.tsv + deck md files + decks.md + vocab.md
    print(f"Wrote {n_files} files:")
    print(f"  {tsv_path}")
    for did in sorted(deck_slides.keys()):
        print(f"  {archive_dir / f'{did}.md'}")
    print(f"  {decks_md_path}")
    print(f"  {vocab_path}")
    
    # Show first 5 lines of slides.tsv
    print("\nFirst 5 lines of slides.tsv:")
    with open(tsv_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i < 7:  # header + comment + 5 data lines
                print(line.rstrip())
            else:
                break


if __name__ == '__main__':
    main()
