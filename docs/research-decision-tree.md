# Research: a decision tree for slide structure (message -> structure -> exhibits -> emphasis)

Date: 2026-11-08. Scope: how to build a human-editable decision tree the skill walks, from classic frameworks plus our archive. Sources were opened as search excerpts or pages as noted; anything beyond that is marked **[inference]**. Builds on `research-slide-coherence.md` (PPTAgent, RALF, LayoutPrompter, Draco, VizML are not re-explained).

## 1. Bottom line

1. Build a **small hand-written tree in Markdown/YAML**, organised by **message type first** (what the reader must conclude), not by data shape first. Every leaf points to archive slides plus an exemplar spec.
2. **Do not learn the tree from `elements_labeled.jsonl` for the upper levels.** The archive has no message labels, and the layout is almost a function of the number of exhibits (feasibility check, section 4). Use the archive to **calibrate and audit** the tree (counts per leaf, example retrieval), not to generate it.
3. Keep `compose.py` as the executor of levels 3-5 (layout, exhibits, links). Add levels 1-2 as data it reads, so Claude and the tool share one source of truth.

## 2. What the classic frameworks give us (and what they do not)

| Framework | What it maps | Use in our tree |
|---|---|---|
| Zelazny, *Say It With Charts* (via secondary summaries) | Message -> one of five comparison types (component, item/ranking, time series, frequency distribution, correlation) -> chart form (pie/bar/column/line/histogram/scatter). | Level 1 -> level 2. Our `kind` vocabulary (composition, ranking, trend, distribution, correlation) is already Zelazny's five plus bridge/kpi/geo/process/matrix. Primary book not opened; treat the five-type list as well known but unverified here. |
| Abela chart chooser | Same idea as a picture: relationship (comparison, distribution, composition, relationship) -> data amount -> chart. | Confirms that "number of items/series" is the second split. |
| Financial Times Visual Vocabulary (https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md, page opened via search; poster https://ft-interactive.github.io/visual-vocabulary/) | Starts from "your story": categories such as correlation, ranking, magnitude, change over time, part-to-whole, flow, spatial; each lists chart types and cautions (for example area charts: changes to the total are visible, changes in components are hard to read). | Closest template for our level 1 labels and for per-leaf "cautions". |
| data-to-viz (https://www.data-to-viz.com/, opened via search) | Decision tree on **input data format** (numeric, categoric, num+cat, maps, time series, network), leading to candidate charts plus a caveats gallery (order your data, spaghetti chart, pie). | Model for level 2 and for a "caveats" field on each leaf. Weakness: format-first trees ignore the message, which is why they give many candidates. |
| Minto pyramid / SCQA (summaries: https://modelthinkers.com/mental-model/minto-pyramid-scqa, https://genppt.com/blog/mckinsey-slides) | Answer first; 3-5 MECE supports; action title = the insight and the exhibit is its proof; one message per slide ("1-3-1": one key message, up to three supporting points, one visual). | Governs the **slide-level contract**: title states the message, each panel proves one support. Gives the message types a place: SCQA's complication = "problem/gap" slides, answer = "recommendation/decision". |
| McKinsey / Bain / BCG practice | Action title, source line, takeaway, restrained colour; chart add-in charts with annotations (CAGR arrows, difference arrows, brackets). | Emphasis devices (level 5). Our archive already shows them as `links` (connector 254, badge_xref 61, highlight 50, arrow_between 25). |

Lesson: every classic tree is **one-dimensional** (message or data shape, picking one chart). None addresses **multi-panel slides with relations between exhibits**, which is our actual output (2-6 panels, 42% single-exhibit, 16% two-column). That part we must design ourselves, from relations (`leads_to`, `explains`, `zooms_into`, `compares`, `sums_to`) as `compose.py` already does.

## 3. What research says about automating this

- **Draco** (https://idl.uw.edu/draco/, paper https://idl.cs.washington.edu/files/2019-Draco-InfoVis.pdf): design knowledge as hard and soft constraints solved with ASP (Clingo); soft-constraint weights learned from perception-experiment data. Rules stay readable and editable, learning only tunes weights. Our `compose.py` is a hand-weighted version of the same shape (SHAPE_FIT, LAYOUT_SHARE, BIG).
- **DracoGPT** (https://arxiv.org/html/2408.06845v2): extracts design preferences from LLMs as numeric weights, an argument that LLM preference can be audited as rules.
- **VizML / Data2Vis / DeepEye / LIDA** (see coherence doc, section 5): learned from large generic corpora (VizML about 1M dataset-chart pairs). Our 740 slides is three orders of magnitude smaller and has no raw datasets. **[inference]** Transfer is weak; borrow their *features* (cardinality, series count, sign mix, monotonicity), not their models.
- **Slide generation** (PPTAgent https://arxiv.org/abs/2501.03936, AutoPresent https://arxiv.org/abs/2501.00912): coherence comes from editing retrieved reference slides; they do not use a decision tree. Retrieval is already in our tool (`examples()`, `retrieve.nearest`).
- **Which method wins?** No paper compares the four on our task. **[inference]** At ~700 samples, no message labels and a human who must be able to correct the output: hand-written rules (with archive-derived priors) + retrieval + an LLM to classify the message beats CART/boosting (opaque, brittle at this size), and is far cheaper than an ASP solver for a tool with 12 layouts and 17 elements. A constraint solver pays off only when the combinatorial space is large; ours is enumerated in under a second (`place()` has at most 24 permutations).
- **Chosen hybrid**: LLM does the fuzzy step (classify the message and fill the content profile), the tree does the deterministic steps (structure, exhibits, emphasis), retrieval supplies examples, the render-and-judge loop (coherence doc, items 2, 3, 7) verifies.

## 4. Learning from OUR data: feasibility check

Script (scratchpad, not committed): features = number of exhibits, count per normalised exhibit kind (`compose._norm`), count per link type; target = layout (classes with >= 15 slides, 5-fold CV, `sklearn` 1.9.1 `DecisionTreeClassifier`, min leaf 10). 740 content slides.

| Fit | CV accuracy |
|---|---|
| Majority class (layout "1") | 45% |
| Depth 2 | 86% |
| Depth 3 | 92% |
| Depth 4-5 | 94% |
| `n_exhibits` alone, depth 3 | 92% |
| Adding words and area_covered | no gain (94%) |

The depth-3 tree is simply: 0 exhibits -> layout "0" (148 text-only slides); 1 -> "1"; 2 -> "2col"; 3+ -> "3col". Findings:

- **Layout is determined by exhibit count**, because the layout label was derived from the exhibit geometry. Learning it adds nothing; it is leakage, not insight. The rare layouts (T|B, L2|R, 4col, 5+col) are separated only at depth 4+ and on 13-33 slides each, which is too few to trust.
- **What is not in the archive**: the message type, the data shape behind a chart, the relation between panels (only drawn connectors), and which exhibit mix belongs to which message. These are the interesting levels and they require **labels we do not have**.
- Link types: only four, and `link` is a list of dicts; "connector" dominates (254). No `explains`/`zooms_into` semantics.
- Samples: 740 slides from 26 decks. Folds that split by slide leak deck style (same authors, same template); use **leave-one-deck-out** for any serious test. Small classes (<20) cannot be evaluated.

Conclusion: a learned tree would rediscover "layout = n_exhibits". The useful archive work is **labelling**, below.

## 5. Proposal for this project

### 5.1 Levels

| Level | Question | Values (draft) | Source of truth |
|---|---|---|---|
| 1 Message type | What must the reader conclude? | trend / change over time; comparison (ranking, benchmark); composition (share, mix); breakdown (parts sum to total; bridge); relationship (correlation, segmentation 2x2); process / roadmap; decision / recommendation; geography; sizing (market, KPI strip) | FT vocabulary categories + Zelazny + our `kind` list |
| 2 Data shape and amount | Points, series, signed, units, qualitative? | existing `pick_element` rules + `fit()` ranges, expressed as a table | `compose.ELEMENTS`, `pick_element` |
| 3 Blocks and relations | How many blocks, how do they connect? | 1 / 2 / 3 / 4+ ; shape: single, chain, fan, converge, compare, parallel | `compose.shape()` |
| 4 Layout, exhibits, links | Which layout and which panel types in which slot? | `compose` output (3 options) | `compose.py` |
| 5 Emphasis | How is the "so what" shown? | highlight one bar/category, CAGR or delta arrow, callout with number, bracket, `xref` badges, takeaway box, `==keyword==` bold in bullets | `links` vocabulary + archive counts |

Level 1 is the new part. It adds, per message type: the preferred structure ("2 exhibits where the second explains the first"), the default emphasis device, the title formula (action title pattern with a number, PT/EN), and cautions (spaghetti line, pie with >5 slices, area stack when components matter).

### 5.2 Leaf format

One YAML file, `docs/decision-tree.yaml` (for the skill) mirrored to an MCP tool `get_decision_path`, so Claude reads it the same way in both. Draft leaf:

```yaml
- id: trend.single_series.few_points
  when: {message: trend, series: 1, points: [3, 12]}
  structure: {layout: "T|B", panels: [kpis, chart], relation: leads_to}
  exhibits: [column, kpis]
  emphasis: [highlight_last_bar, cagr_arrow, takeaway]
  title_pattern: {pt: "<métrica> cresce <x>% a.a. até <ano>", en: "<metric> grows <x>% p.a. to <year>"}
  cautions: ["line only if > 8 points or > 1 series"]
  examples: [{deck: "...", slide: 12}]      # filled from the archive
  exemplar_spec: exemplars/<file>.json
  evidence: {archive_n: 0, confidence: low}  # n slides that match, updated by script
```

Reasons for YAML plus Markdown view: Claude reads either; the user can edit a rule without Python; `tools/decision_tree.py` (about 60 lines) loads it, matches `when` against the profile and returns leaf + reasons. `compose.py` keeps geometry and placement, and takes `structure` and `emphasis` from the matched leaf as a **prior** (a score bonus in `suggest()`, not a replacement), so behaviour stays deterministic and old profiles keep working.

### 5.3 How the skill walks it

SKILL.md step order: (1) Claude states the message in one sentence and picks level-1 type (asks the user only when two types fit); (2) writes the content profile as today and adds `message_type`; (3) calls `suggest_composition`, which now returns `decision_path` (the leaves matched, with reasons) beside the 3 options; (4) Claude fills the spec and applies the leaf's emphasis and title pattern; (5) checks the cautions list before building. One tree, one place to read.

### 5.4 Making the leaves from the archive

1. **Label** the 740 content slides with a message type. Cheap route: one LLM pass over title + exhibit kinds (the title is an action title, so it carries the message), then a 10% human audit (about 75 slides, an hour). Record agreement; if the model/human agreement is below about 80%, merge classes.
2. Cross-tab message type x exhibit mix x link types. Each leaf's `archive_n`, examples and default emphasis come from this table (counts, not a fitted model). Leaves with n < 10 are marked `confidence: low` and fall back to the parent.
3. Pick 1-2 exemplar slides per leaf by hand; they become `exemplar_spec`.

## 6. Validation and updating

- **Agreement**: for each labelled archive slide, run the profile derived from it through the tree and `suggest()`; report top-1 and top-3 agreement of (layout, exhibit multiset) with the original. Use **leave-one-deck-out** when any threshold is tuned. Expect high agreement on layout (trivial) and moderate on exhibit mix; the exhibit mix number is the meaningful one.
- **A/B judging**: pairwise, order randomised, both orders, reference-anchored (coherence doc item 2): tree-guided output vs current output on 20-30 held-out cases; humans on a subset to check judge agreement.
- **Update loop**: each time the user corrects a slide ("this should have been a waterfall"), add or edit one leaf and its example; rerun the agreement script. Version the YAML in the project so changes are diffable.

## 7. Phased plan

| Phase | What | Effort | Done when |
|---|---|---|---|
| 0 (smallest useful) | Write the level-1 table (about 9 types x structure, exhibits, emphasis, title pattern, cautions) as `docs/decision-tree.md`, referenced from SKILL.md. No code. | 2-3 h | Claude picks a type and quotes the leaf in its answer. |
| 1 | LLM-label the 740 slides, cross-tab, fill `archive_n` and examples per leaf. Script in `tools/`. | 0.5-1 day | Every leaf has a count and 1-3 examples; audit agreement known. |
| 2 | YAML + `tools/decision_tree.py`; `suggest()` returns `decision_path`; leaf prior in the score. | 0.5-1 day | Existing tests/profiles unchanged; new field present. |
| 3 | Agreement script and A/B judging on held-out cases. | 1 day | Reports before/after numbers. |
| 4 | Optionally learn small weight adjustments (Draco-style) once corrections accumulate (about 100+). | later | Only if rules plateau. |

Risks: label noise (mitigate with audit and merging classes); the archive reflects competition winners' habits and not necessarily the best slide for a message (counts are priors, not truth); deck-style leakage in evaluation; leaf proliferation (cap about 25 leaves; a leaf with n < 10 merges into its parent).

## 8. What NOT to build

- A CART/boosting model or neural net for layout or exhibit choice (the check above shows it only relearns n_exhibits; no message labels).
- An ASP/Clingo constraint solver or Draco port (space is small; adds a dependency).
- A free-form LLM "choose the chart" step without the tree (not reproducible, not auditable).
- A GUI tree editor, or a tree of more than about 25 leaves, or per-deck style branches.
- New chart types just to fill a leaf; map a leaf to existing elements.

## 9. Existing-doc/code inconsistencies noticed

- `compose.py` header and `element-library.md` say "740 content slides"; the jsonl has 874 rows, 740 with `is_content` true: consistent.
- `compose.py` LAYOUT_SHARE lists `"4col": .026` for 19 slides (19/740 = .0257) and gives no counts for L2|R etc.; the archive also has a layout "5+col" (13 slides) and "0" (148 text-only slides) that LAYOUT_SHARE does not carry. "0" is 20% of content slides and is not a composite layout; the tree should state that text-only slides are out of scope.
- `elements_labeled.jsonl` link records are dicts with `type` or `kind` keys, only four types (connector, badge_xref, highlight, arrow_between); they do not map to the relation vocabulary (`leads_to`, `explains`, ...) used in profiles, so link semantics cannot be learned from the archive without relabelling.

## Sources

- Draco (UW IDL): https://idl.uw.edu/draco/ ; paper https://idl.cs.washington.edu/files/2019-Draco-InfoVis.pdf ; repo https://github.com/uwdata/draco ; DracoGPT https://arxiv.org/html/2408.06845v2
- FT Visual Vocabulary: https://github.com/Financial-Times/chart-doctor/blob/main/visual-vocabulary/README.md ; https://ft-interactive.github.io/visual-vocabulary/
- From Data to Viz: https://www.data-to-viz.com/
- Minto/SCQA summaries (secondary): https://modelthinkers.com/mental-model/minto-pyramid-scqa ; https://genppt.com/blog/mckinsey-slides ; https://deckary.com/blog/pyramid-principle-consulting
- PPTAgent https://arxiv.org/abs/2501.03936 ; AutoPresent https://arxiv.org/abs/2501.00912 ; VizML https://arxiv.org/abs/1808.04819 ; LIDA https://arxiv.org/abs/2303.02927 (see coherence doc for the rest)
- Not opened (named from memory, verify before citing): Zelazny, *Say It With Charts*; Abela, *Advanced Presentations by Design*; Voyager/CompassQL (UW IDL); Bain/BCG guidance pages.
