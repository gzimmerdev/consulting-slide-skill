# Element library (mined from 26 decks, 740 content slides of 874 slides)

Source: `analysis/elements.jsonl` via `tools/mine_elements.py`. Content slides only. "decks" = breadth (of 26).

## 1. Element vocabulary

### By kind / sub (ranked by deck breadth, then count)

| kind | sub | count | decks |
|---|---|---|---|
| text | title | 740 | 26 |
| text | label | 9824 | 25 |
| text | body | 5541 | 25 |
| picture | picture | 1834 | 25 |
| text | source | 519 | 25 |
| text | page_number | 598 | 21 |
| ole | chart add-in data stub (invisible) | 531 | 21 |
| chart | column_stacked | 92 | 21 |
| vision:table | plain | 84 | 21 |
| vision:cards | - | 61 | 21 |
| table | table | 152 | 20 |
| vision:photo | - | 59 | 18 |
| vision:text_block | - | 47 | 18 |
| chart | column_clustered | 29 | 15 |
| vision:screenshot | - | 80 | 14 |
| cluster | cards / column | 35 | 13 |
| vision:diagram | process | 22 | 13 |
| vision:diagram | matrix_2x2 | 18 | 13 |
| chart | bar_stacked | 61 | 11 |
| chart | scatter | 41 | 10 |
| cluster | cards / row | 29 | 10 |
| chart | line | 26 | 10 |
| cluster | badges / column | 19 | 10 |
| chart | waterfall (drawn/image) | 12 | 10 |
| cluster | cards / grid | 28 | 9 |
| chart | line (drawn/image) | 18 | 9 |
| vision:other | - | 15 | 9 |
| chart | stacked_column (drawn/image) | 10 | 9 |
| vision:map | brazil | 22 | 8 |
| chart | column (drawn/image) | 21 | 8 |
| chart | gantt (drawn/image) | 8 | 8 |
| chart | combo | 8 | 5 |
| chart | bubble | 5 | 5 |
| vision:diagram | tree | 12 | 4 |
| vision:map | city | 12 | 4 |
| chart | combo (drawn/image) | 6 | 4 |
| chart | scatter (drawn/image) | 5 | 4 |
| vision:diagram | flow | 5 | 4 |
| vision:map | world | 4 | 4 |
| chart | doughnut | 4 | 4 |
| vision:table | heatmap | 7 | 3 |
| chart | pie | 4 | 3 |
| chart | chartex | 3 | 3 |
| cluster | steps / column | 3 | 3 |
| vision:diagram | timeline | 3 | 3 |
| vision:diagram | funnel | 4 | 2 |
| chart | doughnut (drawn/image) | 3 | 2 |
| vision:logo | - | 2 | 2 |
| chart | line_stacked | 2 | 2 |
| chart | radar | 2 | 2 |
| chart | bubble (drawn/image) | 2 | 2 |
| chart | bar (drawn/image) | 2 | 2 |
| chart | bar_clustered | 2 | 2 |
| cluster | steps / grid | 2 | 2 |
| vision:table | harvey_balls | 2 | 1 |
| vision:icon | - | 2 | 1 |
| text | footer | 2 | 1 |
| vision:diagram | org | 1 | 1 |
| chart | pie (drawn/image) | 1 | 1 |
| vision:diagram | cycle | 1 | 1 |
| chart | stacked100_column (drawn/image) | 1 | 1 |
| vision:diagram | pyramid | 1 | 1 |
| cluster | badges / grid | 1 | 1 |
| vision:table | checkmarks | 1 | 1 |
| vision:map | region | 1 | 1 |
| cluster | steps / row | 1 | 1 |
| chart | stacked_bar (drawn/image) | 1 | 1 |


### Shapes (sub-role / preset)

| type | count | decks |
|---|---|---|
| plain / rect | 3003 | 25 |
| plain / ellipse | 1778 | 25 |
| card / rect | 1221 | 25 |
| plain / custom | 1212 | 23 |
| arrow_shape / chevron | 479 | 23 |
| plain / triangle | 142 | 20 |
| plain / roundRect | 369 | 19 |
| arrow_shape / homePlate | 185 | 18 |
| highlight_box / rect | 50 | 16 |
| badge / ellipse | 284 | 14 |
| badge / rect | 99 | 13 |
| plain / rtTriangle | 21 | 11 |
| card / roundRect | 119 | 9 |
| plain / arc | 55 | 8 |
| plain / mathPlus | 12 | 7 |
| plain / round2SameRect | 42 | 6 |
| plain / rightBrace | 13 | 6 |
| plain / plus | 9 | 5 |
| plain / mathMultiply | 5 | 5 |
| plain / diamond | 7 | 3 |
| plain / wedgeRectCallout | 6 | 3 |
| plain / trapezoid | 3 | 3 |
| plain / flowChartConnector | 188 | 2 |
| plain / hexagon | 8 | 2 |
| arrow_shape / rightArrow | 7 | 2 |


### Connectors (arrow, dash, orientation)

| type | count | decks |
|---|---|---|
| none-arrow, solid, vertical | 1575 | 25 |
| none-arrow, solid, horizontal | 1297 | 25 |
| none-arrow, dashed, horizontal | 617 | 22 |
| end-arrow, solid, horizontal | 146 | 22 |
| end-arrow, solid, vertical | 79 | 22 |
| none-arrow, dashed, vertical | 545 | 21 |
| none-arrow, solid, diagonal | 208 | 18 |
| end-arrow, solid, diagonal | 73 | 14 |
| both-arrow, solid, horizontal | 289 | 13 |
| none-arrow, dashed, diagonal | 46 | 6 |
| end-arrow, dashed, diagonal | 13 | 6 |
| end-arrow, dashed, horizontal | 10 | 5 |
| start-arrow, solid, horizontal | 107 | 4 |
| both-arrow, solid, vertical | 6 | 4 |
| end-arrow, dashed, vertical | 5 | 4 |


### Detail stats

| item | value |
|---|---|
| native charts | 279 (median 2 series, 5 categories) |
| charts with data labels | 3% |
| charts with point-colour overrides (highlight) | 45% |
| tables (median rows x cols) | 152 (6.0 x 5.0) |
| text boxes with bullets | 37% |
| body text with bold lead-in | 8% |
| pictures total / >4% of slide | 2055 / 221 |
| pictures named map / logo / chart_image / icon ("Gráfico n"/"Graphic n" = SVG icons) | 0 / 0 / 0 / 816 |
| ...of which >4% of slide: map / logo / chart_image / icon | 0 / 0 / 0 / 15 |


## 2. Connector vocabulary (links between elements)

| pattern | count | decks | examples (deck #slide) |
|---|---|---|---|
| `text -connector-> text` | 64 | 15 | D03 #38; D06 #3; D06 #31 |
| `chart + highlight_box` | 24 | 11 | D05 #23; D06 #31; D07 #25 |
| `badge-xref` | 61 | 10 | D04 #39; D05 #36; D07 #3 |
| `table + highlight_box` | 18 | 8 | D04 #30; D04 #41; D05 #32 |
| `shape -connector-> text` | 13 | 6 | D06 #29; D09 #12; D10 #5 |
| `text -connector-> shapechart` | 11 | 6 | D10 #4; D10 #11; D14 #25 |
| `text -connector-> shape` | 12 | 5 | D13 #18; D13 #19; D13 #22 |
| `shapechart -connector-> text` | 7 | 5 | D04 #2; D07 #24; D08 #7 |
| `chart -arrow-> chart` | 7 | 5 | D07 #24; D10 #4; D15 #12 |
| `picture -connector-> text` | 6 | 5 | D10 #5; D11 #12; D12 #19 |
| `chart -connector-> shapechart` | 5 | 4 | D15 #17; D16 #3; D19 #3 |
| `shapechart -arrow-> shapechart` | 4 | 4 | D04 #19; D09 #4; D15 #13 |
| `text -connector-> chart` | 4 | 4 | D06 #3; D13 #19; D14 #76 |
| `text -connector-> picture` | 17 | 3 | D13 #18; D13 #19; D14 #75 |
| `picture -connector-> picture` | 9 | 3 | D06 #15; D09 #11; D09 #18 |
| `shape -connector-> shape` | 8 | 3 | D07 #12; D15 #7; D18 #7 |
| `picture + highlight_box` | 8 | 3 | D11 #7; D11 #9; D14 #11 |
| `shapechart -connector-> card` | 7 | 3 | D06 #3; D15 #8; D26 #12 |
| `shapechart -connector-> cards` | 7 | 3 | D15 #8; D16 #6; D25 #12 |
| `shape -connector-> picture` | 5 | 3 | D10 #5; D12 #19; D18 #7 |
| `shapechart -connector-> shape` | 4 | 3 | D04 #2; D04 #4; D06 #7 |
| `table -arrow-> table` | 4 | 3 | D04 #32; D07 #20; D19 #16 |
| `chart -connector-> text` | 4 | 3 | D14 #13; D15 #4; D15 #6 |
| `chart -arrow-> table` | 3 | 3 | D04 #29; D05 #31; D10 #4 |
| `card -connector-> text` | 5 | 2 | D08 #17; D15 #29; D15 #38 |
| `cards -line- shapechart` | 5 | 2 | D10 #10; D15 #8 |
| `text -line- shapechart` | 4 | 2 | D15 #21; D16 #16 |
| `frame -line- frame` | 2 | 2 | D04 #38; D05 #35 |
| `picture -connector-> shapechart` | 2 | 2 | D06 #7; D19 #7 |
| `card -connector-> shapechart` | 2 | 2 | D08 #15; D15 #67 |
| `frame -line- text` | 2 | 2 | D15 #21; D16 #16 |
| `shapechart -connector-> chart` | 2 | 2 | D23 #9; D24 #10 |
| `cards -connector-> card` | 6 | 1 | D14 #15; D14 #16; D14 #22 |
| `card -line- cards` | 4 | 1 | D14 #15; D14 #22 |
| `cards -arrow-> chart` | 4 | 1 | D14 #15; D14 #16; D14 #22 |
| `cards -line- cards` | 4 | 1 | D14 #16; D14 #23 |
| `shape -connector-> card` | 4 | 1 | D15 #7; D15 #67 |
| `card -connector-> shape` | 3 | 1 | D15 #7; D15 #67 |
| `shape -connector-> shapechart` | 3 | 1 | D24 #9 |
| `picture -arrow-> table` | 2 | 1 | D04 #34; D04 #35 |


Link types: `connector` = cxnSp/line with arrowhead (or glued both ends); `arrow_between` = arrow_shape lying between two exhibits; `highlight` = unfilled outlined box over an exhibit; `badge_xref` = same 1-2 char badge in two places.

| link type | count | slides |
|---|---|---|
| connector | 254 | 105 |
| badge_xref | 61 | 17 |
| highlight | 50 | 38 |
| arrow_between | 25 | 23 |


## 3. Arrangements (layout signature of exhibits)

| layout | slides | share | decks |
|---|---|---|---|
| 1 | 311 | 42% | 26 |
| 0 | 148 | 20% | 23 |
| 2col | 116 | 16% | 25 |
| 3col | 44 | 6% | 19 |
| T|B | 33 | 4% | 16 |
| 4col | 19 | 3% | 13 |
| L|R1 | 15 | 2% | 11 |
| L2|R | 13 | 2% | 7 |
| 5+col | 13 | 2% | 11 |
| 3row | 8 | 1% | 7 |
| L|R2 | 4 | 1% | 3 |
| 2x2 | 4 | 1% | 3 |
| 4row | 3 | 0% | 2 |
| T4|B | 2 | 0% | 1 |
| T|B3 | 1 | 0% | 1 |


Typical exhibit kind per position (ordered left-to-right, then top-to-bottom; most common kind and its share):

| layout | slides | position: kind share |
|---|---|---|
| 1 | 311 | 1: shapechart 40%, picture 27% ; 2: picture 100% |
| 2col | 116 | 1: shapechart 38%, chart 24% ; 2: shapechart 28%, chart 21% ; 3: table 100% |
| 3col | 44 | 1: shapechart 59%, chart 20% ; 2: chart 41%, shapechart 36% ; 3: chart 41%, shapechart 23% |
| T|B | 33 | 1: table 33%, shapechart 24% ; 2: table 30%, picture 21% |
| 4col | 19 | 1: shapechart 58%, chart 16% ; 2: chart 42%, shapechart 21% ; 3: chart 37%, shapechart 37% ; 4: chart 63%, shapechart 16% |
| L|R1 | 15 | 1: picture 40%, chart 20% ; 2: picture 40%, cards 27% |
| L2|R | 13 | 1: table 38%, picture 31% ; 2: table 54%, cards 23% ; 3: table 54%, chart 23% ; 4: table 100% ; 5: table 100% |


## 4. Density (content slides)

| metric | mean | median |
|---|---|---|
| words/slide | 180.03 | 174.5 |
| exhibits/slide | 1.49 | 1.0 |
| min body font (pt) | 11.42 | 11.0 |
| median body font (pt) | 12.65 | 12.0 |
| body area covered | 0.63 | 0.62 |


### Per deck (mean)

| deck | content slides | words/slide | exhibits/slide | min body font (pt) | median body font (pt) | body area covered |
|---|---|---|---|---|---|---|
| D02 | 2 | 89.5 | 1.5 | - | 12.0 | 0.75 |
| D03 | 39 | 154.62 | 0.95 | 10.97 | 13.28 | 0.54 |
| D04 | 44 | 162.61 | 1.39 | 11.55 | 12.44 | 0.57 |
| D05 | 38 | 160.11 | 1.13 | 11.5 | 13.54 | 0.6 |
| D06 | 32 | 135.59 | 1.81 | 11.93 | 12.92 | 0.67 |
| D07 | 22 | 129.23 | 1.82 | 10.77 | 12.73 | 0.61 |
| D08 | 17 | 169.35 | 2 | 10.56 | 12.06 | 0.68 |
| D09 | 15 | 252.13 | 2 | 10.73 | 12.13 | 0.76 |
| D10 | 11 | 308.55 | 2.73 | 7.73 | 9.27 | 0.69 |
| D11 | 25 | 151.8 | 1.24 | 11.59 | 12.48 | 0.7 |
| D12 | 41 | 181.63 | 1.12 | 11.28 | 12.12 | 0.58 |
| D13 | 20 | 279.45 | 2.05 | 10.25 | 11.65 | 0.74 |
| D14 | 69 | 216.12 | 1.97 | 11.1 | 12.06 | 0.67 |
| D15 | 60 | 181.58 | 1.32 | 10.73 | 11.99 | 0.63 |
| D16 | 43 | 206.86 | 1.26 | 10.64 | 11.3 | 0.68 |
| D17 | 8 | 160.38 | 2 | 13.94 | 14.0 | 0.88 |
| D18 | 26 | 183.62 | 1.23 | 11.9 | 12.38 | 0.65 |
| D19 | 32 | 191.44 | 1.34 | 11.81 | 12.67 | 0.58 |
| D20 | 21 | 210.81 | 1.19 | 11.28 | 12.0 | 0.6 |
| D21 | 32 | 216.81 | 1 | 11.2 | 12.45 | 0.62 |
| D22 | 14 | 144.36 | 0.79 | 12.19 | 13.43 | 0.54 |
| D23 | 33 | 125 | 1.67 | 14.55 | 15.26 | 0.63 |
| D24 | 19 | 147.05 | 1.26 | 10.47 | 12.84 | 0.61 |
| D25 | 20 | 188.1 | 1.95 | 10.93 | 12.6 | 0.67 |
| D26 | 27 | 270.26 | 2.19 | 8.76 | 10.93 | 0.68 |
| D27 | 30 | 48.5 | 1.47 | 15.83 | 17.33 | 0.59 |


## 5. Blind spots (need vision)

| item | count |
|---|---|
| slides with chart add-in data stub (charts are drawn shapes, found as `shapechart`) | 590 |
| `shapechart` composites (shape-drawn charts/diagrams) | 335 |
| pictures >4% of slide (photo / map / chart image, unclassified) | 221 |
| pictures named "chart" >4% of slide (chart images, not native) | 0 |
| content slides with layout "0" (no exhibit found) | 148 |
| decks skipped (not 16:9 or <3 slides) | 12 |


## 6. Vision labels

556 labelled elements (shapechart / big picture) and 148 labelled body crops (slides with no exhibit found).


### Element crops: kind / sub

| kind | sub | count | decks |
|---|---|---|---|
| table | plain | 84 | 21 |
| screenshot | - | 80 | 14 |
| cards | - | 61 | 21 |
| photo | - | 59 | 18 |
| text_block | - | 47 | 18 |
| diagram | process | 22 | 13 |
| map | brazil | 22 | 8 |
| chart | column | 21 | 8 |
| chart | line | 18 | 9 |
| diagram | matrix_2x2 | 18 | 13 |
| other | - | 15 | 9 |
| chart | waterfall | 12 | 10 |
| diagram | tree | 12 | 4 |
| map | city | 12 | 4 |
| chart | stacked_column | 10 | 9 |
| chart | gantt | 8 | 8 |
| table | heatmap | 7 | 3 |
| chart | combo | 6 | 4 |
| chart | scatter | 5 | 4 |
| diagram | flow | 5 | 4 |
| diagram | funnel | 4 | 2 |
| map | world | 4 | 4 |
| chart | doughnut | 3 | 2 |
| diagram | timeline | 3 | 3 |
| chart | bar | 2 | 2 |
| chart | bubble | 2 | 2 |
| icon | - | 2 | 1 |
| logo | - | 2 | 2 |
| table | harvey_balls | 2 | 1 |
| chart | pie | 1 | 1 |
| chart | stacked100_column | 1 | 1 |
| chart | stacked_bar | 1 | 1 |
| diagram | cycle | 1 | 1 |
| diagram | org | 1 | 1 |
| diagram | pyramid | 1 | 1 |
| map | region | 1 | 1 |
| table | checkmarks | 1 | 1 |


### Element crops: annotations

| annotation | count | share of crops | decks |
|---|---|---|---|
| data_labels | 57 | 10% | 20 |
| numbered_badges | 55 | 10% | 20 |
| legend | 48 | 9% | 19 |
| callout | 43 | 8% | 17 |
| connector_arrow | 34 | 6% | 17 |
| axis_labels | 30 | 5% | 10 |
| highlight_box | 11 | 2% | 7 |
| totals | 7 | 1% | 6 |
| cagr_arrow | 4 | 1% | 3 |


multi-exhibit crops: 123; confidence: med 268, high 187, low 101


### Body crops (layout "0"): kind / sub

| kind | sub | count | decks |
|---|---|---|---|
| text_block | - | 61 | 17 |
| cards | - | 33 | 16 |
| table | plain | 27 | 12 |
| diagram | process | 9 | 6 |
| screenshot | - | 4 | 3 |
| diagram | tree | 3 | 3 |
| diagram | flow | 2 | 2 |
| diagram | timeline | 2 | 2 |
| other | - | 2 | 2 |
| table | harvey_balls | 2 | 2 |
| diagram | matrix_2x2 | 1 | 1 |
| diagram | other | 1 | 1 |
| diagram | venn | 1 | 1 |


### Body crops (layout "0"): annotations

| annotation | count | share of crops | decks |
|---|---|---|---|
| numbered_badges | 19 | 13% | 6 |
| highlight_box | 7 | 5% | 5 |
| callout | 6 | 4% | 4 |
| connector_arrow | 5 | 3% | 4 |
| data_labels | 5 | 3% | 2 |
| axis_labels | 2 | 1% | 2 |
| legend | 1 | 1% | 1 |


multi-exhibit crops: 34; confidence: med 92, low 35, high 21
