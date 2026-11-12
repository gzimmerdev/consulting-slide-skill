# Design system extracted from the archive

Source: 39 .pptx files (33 are 16:9 case-competition decks) from 16 competitions. Method: XML scan of every deck (`tools/scan.py`),
deep metrics on 8 representative decks (`tools/extract.py` → `analysis/*.json`), visual review of rendered contact sheets (`render/sheets/`).
Decks reviewed in depth: Team G (Bain 2025), Team A (2025), Team D (LEK 2026), Team E (2026),
Team C (Mirow 2025), Team L (2024), Team F (2025), Team I (2026).

## 0. The most important finding

**Structure is shared, skin is not.** Every team re-skins the *same* consulting layout to the sponsor's brand
(Bain red, LEK green, gold, bright green, Mirow navy). So the tool has two layers:
a fixed **grid + type scale + element styling** (below, identical across decks) and a swappable **theme** (one primary colour + two fonts).
Everything else (tints, series colours, pale fills) is derived from the primary colour.

## 1. Canvas, margins, grid

| Item | Value | Evidence |
|---|---|---|
| Slide size | 13.333 × 7.5 in (16:9) | 33/39 decks. Others: 10×5.625 (Accenture 2018, Stone 2020), 11.33×7.9 (Bain 2014-15 organiser prompts) |
| Side margins | 0.15–0.4 in (tool uses 0.4) | title x = 0.06–0.33, source x = 0.03–0.67 |
| Title box | x 0.15–0.33, y 0.12–0.47, w 12.7–13.0, one text box | Team G/Team F/Team L/Team C/Team I |
| Body area | y ≈ 1.2 → 6.9 | headers at y 1.0–1.3, takeaway/footers from 6.2 |
| Source line | x 0.4, y 7.0–7.14, h 0.2–0.4 | all decks that have sources |
| Page number | x 12.5–13.0, y 7.0–7.13 | Team C, Team L, Team A, Team G |
| Columns | 2 or 3 columns separated by a dashed `D0D0D0` 1.5 pt vertical line | Team G 6/11, Team E 7/8 |

## 2. Typography (character-weighted frequency)

| Role | Size | Weight / style | Colour |
|---|---|---|---|
| Action title | **20 pt** (24 pt in Team C) | bold in 4/8 decks, regular in Team G/Team I; ≤ 2 lines (median 100–170 chars) | brand colour in 4/8 (Team D, Team L, Team F, Team C), black in others |
| Column header | 14–16 pt (Team E 20 pt italic serif) | bold or regular, centred over a rule | primary |
| Body | **12 pt** (11 Team A; 14 Team F/Team L) | regular | near-black / `50575C` / `404040` |
| Bold lead-in inside bullets | 12 pt | bold | same as body |
| Chart labels, table cells | 10–11 pt | bold for values | `404040` |
| Subtitle (unit + period) | 11–12 pt | *italic* | `7F7F7F` |
| KPI number | 24–32 pt | bold | primary |
| Source / footnote | 8–10 pt | *italic* | `7F7F7F`/`979797` |
| Page number | 10 pt | regular | grey |

Fonts: Arial (Team G, Team A body, Team I body, chart add-in decks) · Trebuchet MS (Team L, Team F, Team D) · Bower-Bold + Nexa Light (Team C, Team A/Team E 2026 headings)
· Georgia (Team I titles) · Meta (LEK template) · Aptos (untouched Office default, 11 decks).
**Not installed by default on most machines:** Bower-Bold, Nexa Light, Meta, Lemon/Milk, Graphik. The tool lets you pick any font per run (`--font`, `--heading-font`, or `font`/`heading_font` in the spec). Default is Arial because it renders identically everywhere.

## 3. Colour (per team; hex from `solidFill` frequency)

| Theme (tool name) | Primary | Secondary / dark | Tints (series order) | Neutrals |
|---|---|---|---|---|
| `bain_red` (Team G, Team A) | `CC0000` (`BF0404`) | `A82040`, `8E1C54`, `78091C` | `DF6060`, `F5A290` | `F2F2F2` panels, `7F7F7F` text, `0C0C0C` dark slides |
| `lek_green` (Team D, Team F) | `00973A` | `076B3B`, `00431E` | `00B852`, `BAF0C0`, `B1D345` | `F2F2F2`, `50575C` |
| `gold_serif` (Team E) | `E6AF00` | `FAD419` | `FFE06D`, `FFECA9` | `F2F2F2`, `747474`, `A1A1A1` |
| `navy_cyan` (Team C) | `020E66` | `017FC5` | `00ADEC`, `AAD5E8`, `D5EAF3` | `F2F2F2`, `071C25` |
| `lime_green` (Team I) | `57CC02` | `265701`, `2E5E0E` | `89E119`, `BBDB44` | `4B4B4B`, `F4D03F` accent |
| (Team L, not a preset yet) | `29B974` | `187955`, `0E4631` | — | `F6F4F3`, `4B4F58` |

**Rules shared by all themes**
- Series order is *dark → light* of one hue: primary, then progressively lighter tints (Team E `E6AF00→FAD419→FFE06D→FFECA9`; Team C `020E66→00ADEC→AAD5E8→D5EAF3`). Tool: primary, +35 %, +60 %, +80 % tint.
- "Story colouring": on a single series, everything is grey (`D9D9D9`/`DBDBDB`/`A1A1A1`) except the bar(s) the title is about, which use the primary (Team G 7, 10, 11).
- Panels / pale fills are a very light tint (`F2F2F2` neutral or ~92 % tint of primary).
- White text only on primary/dark fills.

## 4. Shape styling

| Element | Style |
|---|---|
| Rules under column headers | straight line, **1.5 pt** (all decks); Team E uses 4.5 pt gold accent rules |
| Dividers | dashed `D0D0D0`, 1.5 pt |
| Takeaway / key-message box | dashed brand outline (Team G "Main Takeaway") or pale fill with brand edge (Team E) |
| Number badges | filled ellipse in primary with white bold numeral (Team G pills use rounded-rect) |
| Corner radius | PowerPoint default roundRect (16.667 %) is the mode; `50000` (full pill) for tags (Team I 54×, Team F 5×) |
| Borders | 0.75–1.5 pt, brand or grey |
| Shadows | essentially none on shapes (the Team G count is picture effects) → tool uses no shadows |
| Section tag | small bold label + 0.05 in primary bar at the footer (Team G) |

## 5. Charts (all native `c:chart`)

- Types seen: clustered column (dominant), stacked column, horizontal bar, line with markers, pie/donut (Team L), combo bar+line (Team I), waterfall (stacked column with invisible base series plus connector shapes).
- **Gap width 80** (Team E 50, Team I 45); **overlap 100** on stacked.
- Value axis **deleted** in most (values shown as data labels); light or no gridlines; category axis line grey, no tick marks.
- Data labels: bold, 10–11 pt; outside end for clustered, centred for stacked (white on dark series).
- Legend: **manual** shapes in the archive (small squares + text). The tool uses the native chart legend instead (stays editable). *Deliberate deviation.*
- Chart header (14 pt, rule below) + italic unit/period subtitle sit above the chart.
- Callouts the archive adds as shapes, not chart features: CAGR bubble (ellipse + arrow), dashed outline around a highlighted bar group, delta pills.

## 6. Recurring elements

| Element | Where | Reproducible? |
|---|---|---|
| Action title | every content slide | ✔ |
| Source line ("Fonte:"/"Sources:") | 7/8 decks, bottom-left | ✔ |
| Page number | Team C, Team L, Team A, Team G | ✔ |
| Sponsor logo (Bain, LEK, …) bottom-right | every deck | ✘ image. Tool: optional text tag (`footer_tag`) |
| Team photos, background photos (dark agenda slides) | team, divider, interview slides | ✘ images. Tool: user-supplied path |
| Icons (SVG in 23 decks) | process, KPI, framework slides | ✘ per-deck artwork. Closest: numbered badges / native shapes |
| Numbered badges 1–n | process, insights, risks | ✔ |
| Takeaway box | Team G, Team E, Team C | ✔ |
| Section tag + red bar | Team G footer | ✔ (`footer_tag`, bar not yet) |

## 7. What cannot be reproduced exactly (and the closest equivalent)

| In the archive | Why | Closest equivalent |
|---|---|---|
| Photos / sponsor logos | raster images, licensed | image slot with path in spec; or text tag |
| chart add-in charts (34 decks have `ppt/tags`, 29 contain embedded objects; likely chart add-in and chart workbooks, not verified per deck) | proprietary objects that drive labels/connectors | native chart + invisible-series waterfall + shape connectors |
| SVG icons (23 decks) | per-deck artwork | native shapes (badge, chevron); you can supply your own SVG/PNG |
| Maps (Brazil regions) | picture | image slot |
| SmartArt | **none found in the 39 decks** | n/a |
| Bower-Bold, Nexa Light, Meta fonts | not installed by default | any font you choose; preview renders substitute |
