# Tool gaps found by the 30-slide library rebuild (2026-11-08)

Source: `analysis/library/LNN/notes.md` (30 faithful rebuilds of archive slides, `manifest.json`), QA in `qa.json`.
Result: 17 rebuilds rated ok by their agents; 12 passed visual QA and are in `exemplars/` (ids 012-023). Failed QA: L04 (empty third), L07 (label over box), L14 ("Hardwar/e" mid-word break in a 6-leaf flow), L23 (waterfall labels overflow thin bars), L27 (matrix bubbles overlap).

Ranked by number of slides hurt:

1. **Emphasis shapes** (~13: L03 L05 L06 L07 L08 L10 L19 L21 L23 L25 L27 L28 L29): separate grey boxes per panel (grey backing merges adjacent panels), chevron / arrow-banner headers, V and block arrows, big outline numerals, funnel / trapezoid connector between chart and table, numbered circle badges. Being built (emphasis shapes agent).
2. **Table styling** (~10: L01 L02 L12 L13 L18 L27 L28 L29 L30). Built 2026-11-11: up to 10 columns, `head_fill` (one or per column), `col_fill`, `bands`, `grid`, styled cells `{text, fill, bold, box}` (example `examples/composite_tables.pt.json`). Still open: pill drift on wrapped rows (row-height estimates mis-sized rows; use `row_h`), sparkline cells (L12). Original gap: max 6 columns; header fill colour only from theme (custom `header_fill` only on bar style); no tinted / banded rows, full grid, per-cell fill or per-cell highlight box; pill cells drift off row centre when rows grow.
3. **No slot for user-supplied images** (~8: L02 L08 L09 L11 L13 L16 L17 L26): maps, photos, screenshots, code images leave empty areas; `cols` needs at least one panel per column. Maps stay external (user ruling); an image panel would only place the user's file.
4. **Layout** (~8): no full-width band inside `cols` (L08 L22); nested sub-bullets / sub-headings flattened (L03 L04 L18); chart beside its numbered insights inside one panel (L19); long `cols` intro overlaps the panel below (L05 L15); short bullet lists spread evenly over tall panels (L15 L17).
5. **Text limits** (~6): headline 170 chars (L03 L04 L19 L23), takeaway, card title 40 / text 170, bullet item ~200, `scale.left/right` 24, column headers 40.
6. **Charts** (~6): no line overlay on stacked (L24); % / decimal format on waterfall labels and locale separators (L07 L21 L23); rotated / truncated category labels in narrow charts (L23); line end labels overlap (L09); no sparkline-in-table cell (L12); KPI value with smaller unit, label above (L16).
7. **Rare** (2-3 each): funnel panel (L25), pull-quote style (L15), kicker line above the title (L02 L25), flow panels with 5-6 leaves get tiny / broken text (L14).

Doc vs code (to fix in docs): `source_label` must be given without the colon ("Fonte" not "Fonte:", else "Fonte::"); `chart_font` is spec-level only; `**bold //italic//**` nesting does not parse; flow `op` must be the × character, not x; `bullet_size` range is not stated in the schema error.

## A/B check of table styling (2026-11-11)
L01 L13 L18 L28 L30 rebuilt with the new table options (`analysis/library/LNN/spec_v2.json`), old and new rebuilds judged blind against the originals (4 Sonnet judges, both orders, neutral shuffled names; reports `analysis/ai_audit/ab_tables/{old,new}/report.md`).
Result: 100% detection for both old and new (40/40 each, confidence 3, no position bias), so this round cannot show the table effect: the decisive giveaways sit outside the tables. Logos (missing in every rebuild) are named in 32/40 picks of the new set; then pasted code image (L13), numbered circle badges on headings (L28), title size/font (L01 36pt caps, L30 light wide font), kicker tags ("ANEXOS", "APÊNDICE"). Judges still list the originals' table features (black headers, shaded cells) as evidence, even though the new rebuilds now have them.
Next gaps this exposed: logo in rebuilds (the `logo` slot exists; the archive logo files were not extracted), numbered circle badge on panel titles, kicker line above the title, title size option, image panel (code screenshot).

## Second A/B round: logos, kickers, badges, title size (2026-11-11)
v3 rebuilds (`spec_v3.json`: archive logos via the `logo` list, `tag_style: plain` kickers, `title_badge` on L28 columns, L01 `title_size` 36) judged against the originals with v2 as a control (4 fresh Sonnet judges, both orders; reports `analysis/ai_audit/ab_tables_v3/{v2,v3}/report.md`).
Result: still 100% for both (40/40 each). The giveaways moved: typography now leads (14/40 name the font: originals use Century Gothic / rounded light fonts, rebuilds use the theme's Arial or Trebuchet; the spec-level `font` / `heading_font` fields exist but the rebuilds never set the deck's fonts), then "uniform / clean template" spacing (11), title wrapping (L01 original is a two-line condensed title, 9), the pasted code image (L13, 8), italic serif panel headers (L13, 8), oversized page numbers (L28, L30, 4). Logos are still named (14), now as "hand-placed" positions.
Next for these annex slides: set each deck's real fonts in the rebuild specs (no code needed), then image panel (code screenshot), page-number size per slide is already a token (`page_number_size`).

## Third A/B round: the decks' own fonts (2026-11-11)
v4 (`spec_v4.json`) = v3 + each deck's installed fonts (L18 Nexa Light/Bold, L30 Eurostile with smaller title/table sizes to fit, L13 Arial body; L01 Graphik and L13 Meta are not installed, L28 was already Trebuchet MS). v3 as control, 4 fresh Sonnet judges. Result: still 100% for both (40/40 each); fonts are no longer named. The giveaways are now the originals' human irregularities: uneven bullet/heading spacing, overflowing tables (L28), a stray chevron arrow (L28), tall multi-line headers and "* *" footnote markers (L30), the pasted code image (L13), the two-line title (L01). Judges pick the messier slide as the human one.
Conclusion: stop tuning these five annex slides (decided with the user beforehand: stop if still 100% after fonts). Their remaining tells are deliberate polish differences and pasted images, not missing table features. Reports: `analysis/ai_audit/ab_tables_v4/{v3,v4}/report.md`.

## End-to-end skill test after the archive grammar (2026-11-12)
Three fresh Sonnet agents got only a brief + the `/slide` skill (solar / navy_cyan, food delivery / lime_green EN, hospital / bain_red); outputs in `out/e2e/` (local). All three took the `sections` option, built 3 numbered sections with intros, one grey block and dividers, every number from the brief, no overflow. Fixed the same night: schema errors now name the panel and field (`build._explain`), quoted literals in number formats (`0"%"`) no longer scale as percent, `total_first` waterfall level lines with negative deltas no longer float upward, skill gotchas (decisions vs list items, `items` vs `bullets`, cols panel order, links are suggestions).
Still open (ranked): (1) doughnut `callouts` labels overlap on adjacent small slices (solar RS/PR), no warning; (2) a scored options x criteria `comparison` item maps to a column chart, a table is the better default; (3) compose.py `why`/notes/TODO text is Portuguese for `lang: en`; (4) waterfall category labels truncate/rotate without a warning (hospital, fixed by hand with `cat_size`); (5) process panel leaves large vertical gaps when a column is tall (hospital section 3); (6) rank.py gave no real signal between two close variants (0.350 vs 0.343); (7) [fixed 2026-11-12: footer wordmark removed from navy_cyan] the navy_cyan footer wordmark appeared on every slide in that style.

## Test 2026-11-12: saneamento (4 blocks: trend, breakdown, comparison table, KPIs + 1 decision)
- Fixed: a single small block (KPIs) became its own section, so compose returned only a 4col option (3-section variant stacked chart + tree and failed the fit check; 2-section was None). Now it joins the exhibit it relates to.
- Open: no reference line on column charts (the R$ 46 bi/ano need was drawn as a stacked "lacuna" series).
- Open: table header cells break words mid-word ("Velocidad e") when a column is narrow; check() does not warn. Fixed by hand with col_weights.
- Open: section header bars do not grow or warn when the title needs 2 lines (text spills out of the bar).

## Test 2026-11-12: Bom Preço + Claude Desktop comparison (same skeleton on two prompts)
- Fixed (user rulings 2026-11-12): compose offers band / wide / strip / equal sections ordered by the content, one per kind first; section_style per slide from the archive mix; build fit() warnings for headers needing 2 lines, table headers breaking mid-word, chart category labels too long (PowerPoint wrapped them at 0.83in slots, not at ~0.6in).
- Open: waterfall value labels inside very thin bars (0,4 / 0,6 in a short wide band) are unreadable; they should move above the bar.
- Open: a kpis panel only goes side by side at >= 1.9in per item, so 3 KPIs in a 5.5in column stack with a wide gap between figure and label.

