# Styles: choose one, change one, make one

A **style** is a set of tokens (built-in: `slidegen/themes.json`; yours: `my_styles/styles.json`). Layout (grid, sizes, the 26 archetypes) never changes;
the style changes colour, fonts and the "skin" details that differ between the archive decks.

## Choose
| Where | How |
|---|---|
| Claude Desktop | "usa o estilo `teal_modern`" — Claude calls `list_styles` / `build_slide(style=...)` |
| Spec | `"theme": "lek_green"` |
| Command line | `py -3 build.py spec.json --theme lek_green` (list: `py -3 build.py --styles`) |
| One-off tweaks | `--primary 1F6FEB`, `--font Calibri`, `--heading-font Georgia` (or the same keys in the spec) |

Built in: `bain_red` (Team G/Team A), `lek_green` (Team D/Team F/Team L), `lek_report` (LEK report slides), `gold_serif` (Team E), `navy_cyan` (Team C), `lime_green` (Team I). Original styles made for this project: `orange_graphite` (Arial, orange + graphite), `teal_modern` (Calibri, rounded corners), `blue_slate` (Georgia titles with a rule), `plum_classic` (Cambria, bar headers), `indigo_clean` (Verdana, no footer rule). Archive mixes (`tools/mix_styles.py`, user ruling 2026-11-12: designs from the whole archive, mixed): 24 `mix_*` styles, about one per archive deck: reds `mix_crimson` `mix_brick` `mix_cherry` `mix_rust` `mix_wine` `mix_maroon` `mix_mulberry`, greens `mix_forest` `mix_emerald` `mix_pine` `mix_jade`, olive greens `mix_moss` `mix_olive` `mix_fern`, blues `mix_navy` `mix_ink` `mix_cobalt` `mix_steel`, golds `mix_ochre` `mix_amber` `mix_mustard` `mix_bronze`, greys `mix_graphite` `mix_slate`. Each is an original muted tone of an archive colour family and takes a different archive option for each trait (font family mapped to standard Office fonts, title size, weight and underline, header look, conclusion look, table header and row lines, badge, corners, bottom rule, one or two strong colours); none matches a single deck.
Preview all of them side by side: `out/style_gallery.pptx`.

## Make your own (your design: colours, fonts, logo)
Your styles live in `my_styles/styles.json` (logos in `my_styles/<name>/`). That folder is not in git, so `git pull`
never touches it, and its styles show up next to the built-in ones. One of them can be the **default**: every slide
that names no style uses it.

1. **From slides you already made** (.pptx or .pdf): `py -3 tools/style_from_deck.py deck.pptx --save clube --default`
   (Claude Desktop: "copia o design deste deck e salva como clube" -> `extract_style`). It measures the primary and
   series colours, the fonts, the title size/bold, rounded vs square shapes, and the **logo**: a picture repeated in a
   slide corner (top-right, bottom-left or bottom-right). It warns when a font is not installed or no logo was found.
2. **Say what you want**: `py -3 tools/style_from_deck.py --set clube primary=#1F6FEB heading_font=Georgia corners=rounded --logo logo.png --logo-position top-right`
   (Claude: "nossa cor é #1F6FEB, títulos em Georgia, logo no canto superior direito" -> `add_style`). Any token in
   the table below works as `key=value`; lists in JSON: `series=["0B2E6B","1F6FEB","7FA8F5","D6E4FC"]`.
3. **Check it** on a sample slide: `py -3 build.py examples/composite_coldchain.pt.json -o out/style_clube.pptx --theme clube`,
   look at it next to your slides, and adjust tokens with `--set` (header look, footer rule, title size, ...).

Default: `py -3 tools/style_from_deck.py --default clube` (back: `--default bain_red`). List: `--list`.
Built-in styles stay in `slidegen/themes.json`; edit that file only to change a built-in style for everyone.

## What can change (all tokens)
Tokens are grouped by what they touch. "Default" is the `_defaults` value; "—" means the code has a built-in fallback.

### Colour and font
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `primary` | hex | the brand colour: bars, rules, badges, highlights. Tints, pale fills and the dark colour derive from it | Bain CC0000 · LEK 00973A · lek_report 129B46 |
| `series` | list of hex (charts use up to 4) | chart series colours, dark → light. Default: primary + 3 tints | Team E E6AF00→FFECA9 · Team C 020E66→D5EAF3 · lek_report 3 greens |
| `dark` | hex | background of cover / agenda / key-insight slides. Default: primary darkened 55 % | Team D 00431E · Team E 1A1A1A · Team I 265701 |
| `title_color` | hex | action-title colour; default colour of panel headers and KPI figures | LEK green titles, Bain black |
| `on_primary` | hex | text on brand-colour fills. Automatic: white, or near-black when the brand colour is light (gold, lime) | automatic |
| `text_primary` | hex | text drawn in the brand colour on white (column headers, accent words). Automatic: brand colour darkened until it has 3:1 contrast on white (light gold/lime get darker) | automatic; can be set in a style |
| `heading_font`, `body_font` | font name | titles/headers vs everything else. Use fonts installed on the machine that opens the file. Default Arial | Georgia (Team I, Team C, Team E), Trebuchet MS (Team F) |
| `accent` | hex | colour of the `header_ends` dots and hairline | Team C 00ADEC |

### Action title and footer
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `title_size` | pt, 16–28 (default 20) | action title size | Team C 20 · Team E 17 |
| `title_bold` | true/false (default true) | action title weight | bold in every style |
| `title_rule` | true/false (default false) | rule under the action title | off in every style |
| `subtitle_italic` | true/false (default true) | chart subtitles (grey 10 pt) italic or upright | Team G, Team C, Team I upright |
| `source_italic` | true/false (default true) | footer source line italic or upright | Team G, Team C upright |
| `source_font` | font name (default body font) | footer source-line font | Team E Georgia |
| `source_size` | pt (default 9) | footer source line and wordmark size | Team C 11 |
| `footer_rule` | true/false (default true) | the bottom "underline" above source/page number | off in Team E, LEK report, Team I (their originals have none) |
| `footer_rule_width` | pt (default 1.5) | thickness of that underline | Team C 2.5 |
| `footer_brand` | text | letter-spaced wordmark drawn in the footer row (not drawn when a `logo` is set) | Team C "M I R O W & CO." |
| `logo` | `{file, position, height}` | logo picture on every slide of the style; `position` `footer-right` (default) / `footer-left` / `top-right`, `height` in inches (default 0.3), aspect ratio kept; source/page number shift clear of it; a spec's own `logo` overrides it; missing file = build error | none yet |
| `page_number_align` | `left` (default: right) | page number bottom-left, bold | Team E, lek_report |
| `page_number_size` | pt (default 10) | page number size | lek_report 20 |
| `page_number_bold` | true/false (default: true when left) | page number weight | Team C bold · lek_report regular |
| `page_number_color` | hex (default 7F7F7F right, 1A1A1A left) | page number colour | lek_report 7F7F7F · Team C 1A1A1A |
| `tracker_active` | hex (default primary) | fill of the active section in the footer tracker | Team G 770306 |
| `tracker_serif` | true/false | tracker labels in the heading font | Team G |

### Column and panel headers
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `header_style` | `rule` (default) · `bar` · `dotline` · `vbar` · `italic_centre` | column headers. `rule`: label over a rule (Bain). `bar`: white text in a filled bar (LEK). `dotline`: centred caps on a hairline with a dot at each end (Team C). `vbar`: short brand bar at the left, no underline (Team E). `italic_centre`: bold italic grey centred title, no rule (lek_report). Composite slides can override it with the `header_style` option | Team G rule · LEK bar · Team C dotline · Team E vbar · lek_report italic_centre |
| `header_italic` | true/false (default false) | italic column headers | Team E true |
| `rule_width` | pt (default 1.5) | weight of the rule under column headers (`rule` style, non-composite slides) | Team E 4.5 |
| `header_align` | `l` / `c` / `r` (default l) | label alignment of `bar` headers | lime_green `c` (no visible effect: Team I uses `rule` headers) |
| `header_caps` | true/false (default true) | `dotline` headers in capitals | Team C false |
| `header_bold` | true/false (default true) | `dotline` headers bold | Team C false |
| `header_line` | hex (default primary) | colour of the `dotline` hairline and dots | Team C 00ADEC |
| `header_ends` | `dot` | `rule` headers on composite slides get an `accent` hairline with a dot at each end instead of the grey rule | Team C |
| `panel_title_font` | `body` (default) · `heading` | font of composite panel and chart titles; `heading` = serif | Team G heading |
| `panel_title_bold` | true/false (default false) | serif panel titles bold | Team G true |
| `table_title_rule` | true/false (default true) | table panel titles get the rule header; false = plain sentence-case title | Team G false |

### Takeaway, shapes and tags
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `takeaway_style` | `dashed` (default) · `solid` · `rule` · `grey` | so-what bar: `dashed` = pale fill + dashed outline; `solid` = brand strip with light text; `rule` = thin primary rule over plain text, no box; `grey` = grey box, no outline | Team G dashed · LEK/Team D solid · Team E rule |
| `bar_gap` | % of a bar width (default 80) | gap between bars in column/bar charts: 50 = thick bars, 140 = thin bars (waterfalls keep their own) | mix_* styles |
| `corners` | `square` (default) · `rounded` | cards, tiles, bars | Team I / Team E rounded |
| `badge` | `circle` (default) · `square` | numbered markers 1-2-3 | Team I square |
| `tag_style` | `plain` | the stamp (`tag`) becomes a small label top-left, no box | Team E, lek_report |
| `tag_serif` | true/false | the plain tag is in the heading font, dark | Team E |

### Tables
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `table_header` | `rule` (default: bold dark label on a dark hairline) · `fill` (primary bar, white text, regular) · `plain` (regular, no rule) | table column headers | Team G fill · Team E plain |
| `table_size` | pt (default 11) | table body font size. Panel option `size` overrides | Team G 12 · Team E 10 · Team C 11 |
| `table_row_max` | inches (default 0.45) | max row height. Panel option `row_max` overrides | Team E 0.24 · Team C 0.44 |
| `table_row_rules` | true/false (default false) | light-grey hairline between body rows | Team C, Team I |

### Panels and dividers (composite)
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `panels` | `none` (default) · `grey` | `grey` puts an F2F2F2 panel behind every composite panel, title included, unless a panel sets `panel: none` | none |
| `dividers` | true/false (default false) | dashed grey line between vertically stacked slots. Spec option `dividers` overrides | Team G true |

### Charts
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `chart_font` | pt (default 10) | base chart text size (labels, axes) | Team G 12 |
| `chart_title_bold` | true/false (default true) | left-hand chart titles bold | lek_report false |
| `chart_title_color` | hex (default `title_color`) | left-hand chart titles colour | lek_report 129B46 |
| `label_color` | hex (default 404040) | value-label colour | Team E 000000 |
| `legend_size` | pt (default = chart font) | chart legend font | Team E 10 |
| `bullet_space` | pt (default 6) | space between bullets | Team G 14 |
| `stacked_label_font` | pt (default = chart font) | labels inside stacked segments | Team G 10 |
| `total_bold` | true/false (default true) | stack total labels bold | Team G false |
| `total_color` | hex | stack total label colour | Team G 1A1A1A |
| `total_bar` | hex (default shade of primary) | total bars of a waterfall without `total_first` | Team C 142143 |
| `waterfall_total` | hex (default 4D4D4D) | total bars of a `total_first` waterfall | Team E 000000 |
| `context_bar` | hex (default A6A6A6) | grey for the waterfall delta bars. A `total_first` waterfall keeps them primary unless `highlight` is set | Team C AAD5E8 |
| `backing_fill` | hex (default F6F6F6) | fill of the composite `backing` context panel | Team C F2F2F2 |
| `backing_line` | hex (default none) | outline of the `backing` context panel | Team C BFBFBF |

### KPIs, callouts and bullets (composite)
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `kpi_color` | hex (default `title_color`) | figure colour of `kpis` panels | lek_report 129B46 · Team I 265701 |
| `kpi_bold` | true/false (default true) | KPI figures bold | lek_report false |
| `kpi_style` | `bracket` · `boxed` · `tiles` | `bracket`: label above a [bracketed] figure; `boxed`: each KPI in an outlined card; `tiles`: each KPI on a brand-filled tile with light text (archive KPI looks) | lek_report bracket · mix_* styles |
| `kpi_row_max` | inches (default 1.1) | max KPI row height | lek_report 1.5 |
| `kpi_size` | pt (default auto) | fixed KPI figure size | lek_report 18 |
| `kpi_label_size` | pt (default 11) | KPI label size | lek_report 16 |
| `callout_style` | `bold_centre` | callout text bold, centred, no box | lek_report |
| `callout_fill` | hex (default F2F2F2) | callout box fill; FFFFFF = no visible box | Team G FFFFFF |
| `lead_in_plain` | true/false | bullets panels drop the bullet glyph (bold lead-ins read as plain text) | lek_report true |

### Numeral grids (composite `legend: numeral_grid`)
| Token | Values | What it changes | Used by |
|---|---|---|---|
| `grid_bullets` | true/false | grid item text gets a bullet dot | Team E true |
| `grid_numeral_font` | `body_font` (default) · `heading_font` | font of the numerals | Team E heading_font |
| `grid_numeral_size` | pt (default 28) | numeral size | Team E 24 |
| `grid_numeral_color` | hex (default 7F7F7F) | numeral colour | Team E A6A6A6 |
| `legend_text_size` | pt (default 12, or 10 in small cells) | grid item text size (the name is historical; it is not a chart legend) | Team E 10 |

## Still not tokens
- **Body text size has no single token.** Sizes come from per-element tokens (`table_size`, `chart_font`, `bullet_space`) and spec options (`bullet_size`, `text_size`, `size`).
- **Fonts not installed** (Bower-Bold, Nexa Light, Meta): the file stores the name; machines without the font substitute it.
