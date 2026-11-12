# Research: making generated slides coherent with a reference archive

Date: 2026-11-08. Method: abstract pages (arXiv / project pages) opened for every item below; claims are limited to what the abstract or page states. Anything beyond that is marked **[inference]** (my judgement, not the paper's). Builds on `research-vision-document-ai.md` (embeddings, ColPali, PPTAgent clustering are not repeated). No peer-reviewed venue is claimed unless the page stated one.

## 1. Reference / template-conditioned slide generation

- **PPTAgent** (Zheng et al., arXiv 2025, preprint). Two stages: analyse reference decks to get each slide's functional type and content schema, then generate an outline and iteratively issue *editing actions* on selected reference slides. Introduces PPTEval (Content, Design, Coherence). Reports gains over prior methods on all three. Lesson: output is coherent because it is an edit of a real human slide, not a synthesis.
- **AutoPresent / SlidesBench** (arXiv 2501.00912). 7k train / 585 test examples from 310 decks, 10 domains. Offers *reference-based* scoring (similarity to target slide) and *reference-free* scoring (design quality). Finds programmatic generation beats image generation for editable output; self-refinement helps. Gives us a template for a reference-based metric suite.
- **SlideCoder / Slide2Code** (arXiv 2506.07964, EMNLP 2025 per search results). Reference *image* to editable slide code: colour-gradient segmentation, layout-aware prompt with element positions, hierarchical retrieval-augmented generation. Claims up to 40.5 points over baselines on layout fidelity, execution accuracy, visual consistency; releases a 7B model. Relevant as the inverse of our task (image to spec) and for its fidelity metrics.
- **DOC2PPT** (Fu et al., AAAI 2022; arXiv 2101.11796). Hierarchical seq2seq doc to slides with a layout-prediction module; ~6,000 paired docs/decks. Older, learns layout from pairs; useful only as precedent for learned layout prediction.
- **PreGenie** (arXiv 2505.21660, Findings of EMNLP 2025). Slidev/Markdown code generation with a *Page Reviewer* VLM that looks at the render and regenerates bad slides; claims better aesthetics and alignment with human preference. Render-then-review loop.
- **UniPPTBench** (arXiv 2605.17356, May 2026). Page says generic quality scores ("visual appeal, layout") do not imply task fulfilment. Also (per a search snippet, **not verified on the page I opened**) a "Style Agent" inducing colour/type/spacing tokens per deck.

Takeaway: the best-supported route to reference coherence is edit-from-a-retrieved-reference (PPTAgent) plus render-and-review (PreGenie), with reference-based scoring (SlidesBench).

## 2. Retrieval-augmented / exemplar-conditioned layout

- **RALF** (arXiv 2311.13602, CVPR 2024 oral). Retrieves nearest-neighbour layouts for an input image and feeds them to an autoregressive generator; "simple retrieval augmentation can significantly improve" quality, constrained and unconstrained. Direct evidence that retrieval beats generating from scratch when data is scarce (ours: ~2,300 slides).
- **LayoutPrompter** (Lin et al., NeurIPS 2023; arXiv 2311.06495). Training-free: serialise layouts, *dynamically select exemplars* per input, sample several outputs, rank with a layout ranker. Competitive with SOTA; notably better than a trained baseline in low-data settings. Closest buildable recipe for an LLM-driven tool like ours.
- **LayoutGPT** (NeurIPS 2023; arXiv 2305.15393). In-context demonstrations written as CSS-like style sheets let an LLM plan layouts; strong on numerical/spatial faithfulness. Supports "show layouts as structured text exemplars".
- **PosterLayout** (Hsu et al., CVPR 2023; arXiv 2303.15937). 9,974 poster-layout pairs; 8 metrics, 5 graphic + 3 content-aware (non-salient-area use, salient-object occlusion, text unreadability, underlay availability). Model for content-aware metrics; check paper for exact definitions (I did not open the PDF).
- **LayoutDiffusion** (arXiv 2303.11589). Representative of trained generators; useful mainly for its eval protocol (unconditional / type-conditioned / refinement).

Takeaway: with a small corpus, retrieve + in-context exemplars + rank beats rules and beats training. **[inference]**

## 3. Style / brand consistency, design tokens

I found no paper that cleanly "learns a deck's style from exemplars" end to end. What exists:
- **UniPPTBench Style Agent** (above, snippet-level): style as slots for colour tokens, type hierarchy, spacing scale, component primitives; pages bind to shared tokens.
- **PresentBench** (arXiv 2603.07244, Mar 2026). 238 instances, avg 54.1 binary checklist items each; includes a criterion on font/colour/layout consistency across slides. Claims stronger human alignment than holistic judges (no stats on the page).
- **SlideForge** (arXiv 2609.03109, per search result only, not opened): deck-level judge of shared visual identity (palette, typography, motif). **Unverified; do not cite until read.**
- **PPTAgent** again: consistency comes for free because every slide edits the same template deck.

Takeaway: practical design-token approach = extract tokens (fonts, sizes, palette, margins, spacing scale) from the .pptx XML we already parse, freeze them, and *check* conformance. **[inference]**

## 4. Measuring similarity and quality

- **Layout metrics.** Overlap, alignment (edges/centres), mIoU against nearest real layout, layout-FID with a learned extractor are the standard set; a search summary notes metrics with the same name are computed differently across papers and rankings can disagree (LayoutDiffusion 2303.11589, PosterLayout). So define ours explicitly.
- **LLM/VLM judges.** MT-Bench paper (Zheng et al., NeurIPS D&B 2023; arXiv 2306.05685): strong judges reach >80% agreement with humans on chat, but show position, verbosity, self-enhancement bias; pairwise comparison and mitigations proposed. For design specifically:
  - **DesignSense** (arXiv 2602.23438, Feb 2026): 10,235 human preference pairs for layouts; says frontier VLMs are unreliable, especially on the 4-way label (left/right/both good/both bad); a trained judge gives +54.6% macro-F1; best-of-N with the judge gives +3.6%.
  - **AesEval-Bench** (arXiv 2603.01083, ICLR 2026): 4 dimensions (typography, layout, colour, graphics), 12 indicators; reports clear gaps between VLMs and human-level aesthetic assessment.
  - **AesthetiQ** (CVPR 2025): supplement reports 78.8% human agreement for the VILA judge and 88.6% for GPT-4o (search snippet, different setup; indicative only).
  Explains our 5-8/10 plateau: absolute 1-10 scores from VLMs are noisy; pairwise/reference-anchored is the better-supported protocol. **[inference]**
- **"Looks AI-generated".** I found no solid study. "Usable but Conventional" (arXiv 2605.15124) points the right way but I only saw its title/intro; Creativity-in-the-Age-of-AI (arXiv 2411.00168) cuts the other way (experts found AI outputs more dynamic). A vendor blog claim was discarded. Treat as an open gap: measure it on our own archive (can a judge/human tell original from rebuild in a forced choice?).
- **Embedding similarity** (CLIP/DINO/FID-like): see the earlier doc; use it for nearest-neighbour and distribution distance.

## 5. Data to chart recommendation

- **VizML** (Hu et al., arXiv 1808.04819). ~1M dataset-visualization pairs from Plotly; neural nets predict design choices (chart type, axis assignment) from per-column features; comparable to humans on consensus type on a crowdsourced set; feature importances reported.
- **Data2Vis** (Dibia and Demiralp, arXiv 1804.03126). Seq2seq data to Vega-Lite; qualitative evidence only.
- **Draco / Draco 2** (Moritz et al., IEEE VIS 2019; Draco 2 arXiv 2308.14247). Design guidelines as hard/soft constraints solved with ASP; soft-constraint weights can be *learned from perception experiments or preference data*. Closest match to our rule-based recommender, with a learning story.
- **DeepEye** (Luo et al., ICDE 2018 / Big Data Mining and Analytics 2018). Rule-based candidate enumeration plus learned good/bad classifier and learning-to-rank; trained on 33,412 bivariate charts from 42 datasets with annotations from 100 students (285,236 compared pairs per search summary).
- **LIDA** (Dibia, ACL 2023 demo; arXiv 2303.02927). LLM pipeline: data summary, goal exploration, code generation with refine/filter, optional infographic. Template for "data to proposition" via LLM.
- **Insight-centric visualization recommendation** (arXiv 2103.11297): taxonomy of rule/ML/insight-based approaches (not read in depth).

Takeaway: all of these learn from *generic corpora*; ours is a 40-deck archive, so the relevant move is to learn the mapping "data shape to archive element" from the archive itself, with Draco-style soft constraints as the glue. **[inference]**

## 6. What this means for our tool (ranked)

| # | Improvement | Impact | Effort | Source |
|---|---|---|---|---|
| 1 | **Retrieve-and-edit.** For a request, retrieve the k nearest archive slides (by element-type signature + data shape + optional DINOv2/SigLIP vector), pass 2-3 as in-context exemplars (their JSON specs) and have the AI edit/adapt the closest one instead of composing from rules. Keep rules as fallback and for ranking. | High: addresses density, annotation habits, geometry all at once | M | PPTAgent; RALF; LayoutPrompter |
| 2 | **Reference-anchored pairwise judging.** Replace 1-10 scores with forced-choice "which of A/B is more like reference R / which is the original", randomise order, run both orders, report win-rate vs the archive original. Track judge agreement on a 30-pair human-labelled set. | High: gives a measurable signal where scores plateau | S | MT-Bench judge biases; DesignSense; SlidesBench reference-based scoring |
| 3 | **Generate N, rank, pick.** Sample 3-5 candidate specs per request, rank with metrics (item 4) + pairwise judge, ship the best. | Med-High | S-M | LayoutPrompter ranker; DesignSense best-of-N (+3.6%); PreGenie review loop |
| 4 | **Add explicit coherence metrics to `tools/compare_slides.py`**: element-box overlap; left/right/centre edge-alignment count; margin/gutter conformity; white-space share and balance (we have); box-level IoU / Hungarian-matched IoU against the nearest archive slide (mIoU style); element-count and text-density distance to the archive distribution; font-size set conformity to extracted tokens. Compute box metrics from the spec/XML, not pixels. | Med-High: pixel metrics (white share, ink grid) cannot see alignment or density | S-M | PosterLayout; LayoutDiffusion metric family; PPTEval/SlidesBench |
| 5 | **Freeze design tokens from the archive** (fonts, size ladder, palette, margins, spacing, line weights) and add a lint pass that rejects off-token values; log deviation rate per slide. | Med: removes the "off-brand" tells cheaply | S | UniPPTBench style tokens (snippet); PresentBench consistency criterion |
| 6 | **Layout priors as data.** From the 2,300 classified slides, store per-type statistics (number of elements, box-size distributions, title length, annotation count, source-line presence) and feed the matching type's stats into the prompt and into the lint/rank step. | Med | M | LayoutGPT/LayoutPrompter (structured exemplars); RALF |
| 7 | **Render-and-review loop** with a VLM that compares render vs the retrieved reference and returns a *list of concrete diffs* (not a score), applied as spec edits. 1-2 rounds. | Med | M | PreGenie Page Reviewer; AutoPresent self-refinement |
| 8 | **Data-shape features for chart choice.** Compute per-column features (type, cardinality, monotonicity, share of nulls, #series, #points, sign mix) and map to archive chart elements using archive co-occurrence counts; encode current rules as soft constraints with weights tuned on the archive (Draco-style). Optionally LIDA-style "goal" step before layout. | Med | M-L | VizML features; Draco 2; DeepEye; LIDA |
| 9 | **Fine-tuned/learned judge** on our own preference pairs (original vs rebuild, good vs bad) once we have 200+ labelled pairs. | Med, later | L | DesignSense (trained judge beats frontier VLMs) |
| 10 | **"Original vs rebuild" detectability test** as the headline KPI: forced choice by VLM and by teammates; target ~50%. Fills the gap that no published study covers. | Med (process) | S | gap in literature (section 4) |

Suggested order: 2 and 4 first (cheap, give a ruler), then 1, 3, 5, then 6, 7, 8.

## Caveats

- Several 2026 papers (DesignSense, AesEval-Bench, UniPPTBench, PresentBench) are preprints I read only at abstract level; numbers are the authors' claims.
- SlideForge (2609.03109) and the Style Agent detail came via search snippets, not opened pages.
- No source tested these methods on consulting-style, text-dense, annotated slides; transfer to our domain is **[inference]**.

## Sources

- PPTAgent: Generating and Evaluating Presentations Beyond Text-to-Slides. arXiv 2025. https://arxiv.org/abs/2501.03936
- AutoPresent: Designing Structured Visuals from Scratch (SlidesBench). arXiv 2025. https://arxiv.org/abs/2501.00912
- SlideCoder: Layout-aware RAG-enhanced Hierarchical Slide Generation from Design. EMNLP 2025 / arXiv. https://arxiv.org/abs/2506.07964
- DOC2PPT: Automatic Presentation Slides Generation from Scientific Documents. AAAI 2022. https://arxiv.org/abs/2101.11796
- PreGenie: An Agentic Framework for High-quality Visual Presentation Generation. Findings of EMNLP 2025. https://arxiv.org/abs/2505.21660
- UniPPTBench. arXiv 2026. https://arxiv.org/abs/2605.17356
- PresentBench: A Fine-Grained Rubric-Based Benchmark for Slide Generation. arXiv 2026. https://arxiv.org/abs/2603.07244
- Retrieval-Augmented Layout Transformer for Content-Aware Layout Generation (RALF). CVPR 2024. https://arxiv.org/abs/2311.13602
- LayoutPrompter: Awaken the Design Ability of Large Language Models. NeurIPS 2023. https://arxiv.org/abs/2311.06495
- LayoutGPT: Compositional Visual Planning and Generation with LLMs. NeurIPS 2023. https://arxiv.org/abs/2305.15393
- PosterLayout: A New Benchmark and Approach for Content-aware Visual-Textual Presentation Layout. CVPR 2023. https://arxiv.org/abs/2303.15937
- LayoutDiffusion: Improving Graphic Layout Generation by Discrete Diffusion Probabilistic Models. arXiv 2023. https://arxiv.org/abs/2303.11589
- Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS D&B 2023. https://arxiv.org/abs/2306.05685
- DesignSense: A Human Preference Dataset and Reward Modeling Framework for Graphic Layout Generation. arXiv 2026. https://arxiv.org/abs/2602.23438
- Can Vision Language Models Assess Graphic Design Aesthetics? (AesEval-Bench). ICLR 2026. https://arxiv.org/abs/2603.01083
- AesthetiQ: Enhancing Graphic Layout Design via Aesthetic-Aware Preference Alignment. CVPR 2025 (supplement). https://openaccess.thecvf.com/content/CVPR2025/supplemental/Patnaik_AesthetiQ_Enhancing_Graphic_CVPR_2025_supplemental.pdf
- Usable but Conventional: UX of AI-Generated Interface Prototypes. arXiv 2026 (not read). https://arxiv.org/abs/2605.15124
- Creativity in the Age of AI. arXiv 2024. https://arxiv.org/abs/2411.00168
- VizML: A Machine Learning Approach to Visualization Recommendation. arXiv 2018. https://arxiv.org/abs/1808.04819
- Data2Vis. IEEE VDS 2018. https://arxiv.org/abs/1804.03126
- Draco: Formalizing Visualization Design Knowledge as Constraints. IEEE VIS/TVCG 2019. https://idl.uw.edu/papers/draco
- Draco 2: An Extensible Platform to Model Visualization Design. arXiv 2023. https://arxiv.org/abs/2308.14247
- DeepEye: An Automatic Big Data Visualization Framework. Big Data Mining and Analytics 2018. https://sciopen.com/article/10.26599/BDMA.2018.9020007
- LIDA. ACL 2023 demo. https://arxiv.org/abs/2303.02927
- Insight-centric Visualization Recommendation. arXiv 2021. https://arxiv.org/abs/2103.11297
- SlideForge (unverified). https://arxiv.org/abs/2609.03109
