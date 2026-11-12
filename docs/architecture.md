# Architecture recommendation

## Decision

**A small Python library (python-pptx) with a JSON spec per archetype, a CLI, and a Claude Code skill on top as the AI front-end.**

```
 short brief ("5 numbers + data + slide type", PT or EN)
        │  AI layer: .claude/skills/slide/SKILL.md  (Claude picks the archetype, writes the headline,
        ▼                                            insights, takeaway; fills the JSON)
   spec.json ──► build.py ──► JSON Schema + fit rules ──► slidegen/{chart,text,table,diagram,structure}_slides.py + composite.py ──► native .pptx
                                   ▲                              ▲
                     schemas/archetypes.schema.json     slidegen/core.py + charts.py + themes.json (styles)
   Claude Desktop (subscription) ──► mcp_server.py ──► same build path   |   Excel ranges ──► build.resolve_excel
        verify: tools/preview.ps1 (real PowerPoint → PNG)  or  tools/preview.sh (LibreOffice)
```

The AI only ever produces *data* (the spec). Geometry, colours, fonts and chart styling live in code, so the output is identical every time and "looks like your deck" by construction. If the AI writes a bad spec, validation rejects it with a readable message and it retries.

## Options compared

| Option | Native charts | Reusable | Effort | Verdict |
|---|---|---|---|---|
| **python-pptx + JSON spec + CLI** | ✔ (+ raw XML access for gap width, label position, per-point colours) | ✔ | low | **Chosen core** |
| pptxgenjs (Node) | ✔ | ✔ | low | Equivalent, but python-pptx gives lxml access to fix chart details; you already have Python, Node is installed but unused |
| **Claude skill / Claude Code command** | via the core | ✔ | very low | **Chosen as the front-end**: turns a messy brief into a valid spec. Skills are cheap; do not let them draw geometry |
| Template .pptx with placeholders, filled by script | ✔ | medium | low | Rejected as the core: every archetype × every theme = one template to maintain; the theme (colour/font) can't be swapped |
| Web form | ✔ via the core | ✔ | medium–high | Only worth it if non-Claude users need it. A thin Flask/Streamlit form over `build.py` is a later add |
| Raw LLM → direct .pptx code each time | ✔ | ✘ | — | Rejected: non-deterministic styling; breaks "exactly the same look" |

## Why this shape
- **Theme = 1 colour + 2 fonts**; tints, series order and pale fills are derived (matches how the archive re-skins one structure per sponsor). Choosing "the colours I've chosen" is `--primary 1F6FEB` or `"primary"` in the spec.
- **Fonts**: you choose per run (`--font`, `--heading-font`). The file stores the font *name*; machines without it substitute. Default Arial renders everywhere.
- **Language**: `lang: pt|en` switches default labels (Fonte/Source, Principais insights/Key insights, Conclusão/Takeaway). Number separators follow the viewer's PowerPoint locale (format codes are locale-neutral).
- **Single slide focus**: one spec → one one-slide .pptx. A later `deck.json` (list of specs) is a 10-line loop; not built (YAGNI).
- **Verification loop**: build → render with real PowerPoint (COM; used here) → look. `tools/test_build.py` asserts native chart, no pictures, real text; `tools/check_examples.py` validates all 33 example specs (26 in `examples/catalog.json`, one per type, plus 7 example files) against the schema.

## Status (2026-11-08)
- ✔ All 26 archetypes built (`docs/archetypes.md`): the 25 classified types plus `composite`, tested by `tools/test_build.py`.
- ✔ Composite (type 26): 1–6 panels in a layout grid (charts incl. scatter/bubble with phase markers and donut callouts, tables with pill cells, bullets, cards, KPIs (icons), map, process, matrix, flow trees with operator junctions) joined by arrow, bracket, highlight, callout, xref and CAGR links (`docs/archetypes.md`). Logo slot (`logo` in the spec or theme).
- ✔ Retrieve-and-edit: `tools/retrieve.py` (MCP `find_similar`) finds the nearest archive slides and specs; approved slides go to `exemplars/` (`save_exemplar`). `tools/rank.py` (MCP `rank_candidates`) ranks 2–3 candidate specs by structure distance to the archive (`tools/layout_metrics.py`, `analysis/layout_stats.json`). Tests: `tools/test_retrieve_rank.py`.
- ✔ Blind A/B test vs the originals: `tools/ab_judge.py` (pairs in `analysis/ai_audit/ab/`, report `ab/report.md`). Baseline 2026-11-08: originals spotted 16/20 (80%; 50% = indistinguishable). After retrieve-and-edit + logos + fuller content (`analysis/ai_audit/v5`, `ab_v5/report.md`): 20/20. The giveaways are now element types composite cannot draw (flowcharts with connectors, icons in panels, coloured tag pills, chart callouts/phase markers, gradient scales), not missing content. After adding flow panels, icons, pill cells, phase markers and donut callouts (`v6`, `ab_v6/report.md`): 13/20 = 65%. Still spotted by both judges: s02/s04 (chart add-in watermark, maps, gradient scales) and s05 (icons in table cells, vertical side labels, connector arrows). After tighter spacing + table-cell icons, side labels, chart→table connectors, gradient scales and dotted notes (`v7`, `ab_v7/report.md`): 16/20 = 80%; one judge picked A 9/10 (position bias), so v6 vs v7 is within noise at 20 picks. s02/s04 are still caught on the chart add-in watermark every time. v8 (per-style footer rule, node tracker, footer bar, faithful line data, inside legend; 4 judges told to ignore the chart add-in mark; `ab_v8/report.md`): 24/40 = 60%. s07/s09/s10 at or below chance; s02/s04 4/4 (map, rearranged layout, larger text). Main remaining giveaways: panel arrangement differs from the original, and text larger/looser than the original's dense small text. v9 (faithful panel arrangement via `layout: "cols"`, per-slide text sizes; judges also told to ignore maps; `ab_v9/report.md`): 25/40 = 62.5%, with strong A-position bias (77.5% A picks). Excluding s02/s04, whose giveaways were the map, chart add-in mark and the original's own typos/leftovers: 17/32 = 53% (chance). s06 was caught on mid-word breaks in narrow flow boxes; fixed after the run (flow text floor 6 pt).
- ✔ Archive mining: 26 decks, 740 content slides, elements extracted to `analysis/elements.jsonl` by `tools/mine_elements.py`; summary in `docs/element-library.md`.
- ✔ AI-elements audit: composite slides compared side by side with the archive originals (`analysis/ai_audit`; one line per tool change in `analysis/ai_audit/changelog.md`).
- ✔ Composition recommender (`tools/compose.py`, MCP `suggest_composition`): a content profile (data items + relations + insights/decisions) → top 3 composite options (layout, panels, links, spec skeleton, "like archive slide X"), with a thin-data warning and data-fitted alternatives. Rules and thresholds come from `analysis/elements_labeled.jsonl`; for 4-6 blocks it returns 2-/3-section `cols` variants ranked and sized by the archive grammar. Tests: `tools/test_compose.py`.
- ✔ Archive grammar (`tools/grammar.py`, MCP `slide_grammar`): vision labels of 120 archive slides (`analysis/grammar/`, form `SCHEMA.md`, Haiku labels checked against a Sonnet reference with `--agree`) -> `analysis/grammar.json` (numbers for compose.py) + `brain/30-patterns/` (notes the skill reads). Elements and how they combine, not layouts to copy (user ruling 2026-11-12).
- Retrieve-and-edit of whole specs is for explicit archive-slide rebuilds only (user ruling 2026-11-12).
- ✔ Styles as tokens (`docs/styles.md`), style extraction from any .pptx/.pdf (`tools/style_from_deck.py`).
- ✔ Icons (Lucide, ISC) by name; Excel ranges as data source.
- ✔ AI front-end on the subscription: MCP server for Claude Desktop (`docs/mcp.md`) + Claude Code skill.
- Next: flowchart/tree panel inside composite (A/B giveaway), learned pattern discovery over the archive (see `docs/research-vision-document-ai.md`), deck-level storyline.

## Known limits (honest list)
- Logos, photos, maps, SVG icons cannot be generated; slots accept your own files (`image` on cover, agenda_divider, key_insight, closing, exhibit_annotated; team photos). The Brazil map is native (`tile_map`, composite `map_br`).
- Waterfall (type 3, composite `waterfall`) and CAGR links (composite `cagr`) are built from native chart features and shapes; chart-add-in-style connectors are the waterfall `connectors` option.
- Text fit is validated by character limits, not by measuring rendered text; very long single words can still wrap. Verify visually.
- Legend is the native chart legend (editable) instead of the archive's hand-drawn squares.
