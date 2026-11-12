# Research: how AI "reads" documents through patches or pixels, and what it means for the slide tool

Date: 2026-11-06. Method: I opened the arXiv abstract pages (and, for DeepSeek-OCR and PPTAgent, the HTML full text and GitHub READMEs) listed in "Sources". Everything marked **[unverified]** is general knowledge I did not confirm in a source I opened. Per-item "local cost" lines are mostly my engineering judgement, not claims from the papers, unless a README is cited.

Our situation: ~110 decks (39 .pptx, ~95 PDFs, ~2,300 slides, PT/EN). Exact style stats already come from the .pptx XML. ~2,070 PDF slides were classified into 25 types by a vision LLM on contact sheets.

## 0. The one-paragraph answer

The article is almost certainly about **DeepSeek-OCR (Oct 2025)**: render text as an image, encode it with a vision encoder into few "vision tokens", and let an LLM decode it back. The paper claims ~97% OCR precision when text tokens are at most 10x the vision tokens, and ~60% at ~20x. It is a token-compression / OCR result, not a layout- or style-discovery method. The directly useful ideas for us come from a different branch of the same "patch" family: page-image embeddings (ColPali, CLIP/SigLIP/DINOv2) for similarity search and clustering, and PPTAgent, which already does "cluster rendered slide images, then have a multimodal LLM name the layout in each cluster". For exact fonts, sizes, colours and positions, the PDF text layer (or the .pptx XML) beats every learned model.

## 1. Vocabulary: what "patches" and "pixels" mean

- **Patch**: the image is cut into a grid (ViT uses 16x16-pixel squares); each patch becomes one token fed to a Transformer. ViT's abstract: "a pure transformer applied directly to sequences of image patches" (Dosovitskiy et al., 2020).
- **Pixels instead of tokens**: text is rendered as an image and the model never sees a tokenizer or vocabulary (PIXEL, CLIPPO, DeepSeek-OCR).
- **OCR + layout**: an OCR engine (or the PDF text layer) supplies words and boxes; a model combines them with the image (LayoutLMv3, UDOP).
- **OCR-free**: the model maps image to text/structure directly (Donut, Nougat, Pix2Struct, DocOwl).

## 2. Item-by-item

### 2.1 Patch encoders on document images

| Item | What it does / how it reads | What it gives us | Local cost | Source, year |
|---|---|---|---|---|
| **ViT** | Transformer over 16x16 image patches; the base of nearly everything below. | Nothing directly; it is the backbone. | n/a | arXiv 2010.11929, 2020 |
| **DiT** (Document Image Transformer) | Self-supervised ViT-style model pre-trained on large unlabeled document images; used as backbone for document classification, layout analysis, table detection, OCR text detection. Reads pixels/patches, no OCR. Reported gains e.g. layout analysis 91.0 to 94.9. | A document-domain visual backbone; its features could embed slides. Not specialised for slides. | Open code/weights (aka.ms/msdit per abstract). Small enough for CPU/modest GPU **[unverified]**. | arXiv 2203.02378, 2022 |
| **LayoutLMv3** | Multimodal Transformer over text tokens plus image patches with unified masking and a word-patch alignment objective. Needs OCR words and boxes as input. | Text+layout+image joint embedding; good for field extraction, overkill for slide typing. | Code/models public per abstract. Licence **[unverified]**, I recall non-commercial restrictions but did not check. | arXiv 2204.08387, 2022 |
| **Pix2Struct** | Image-to-text model pre-trained to parse masked web-page screenshots into simplified HTML; variable-resolution input; questions rendered on top of the image. Pure pixels. Works across documents, illustrations, UIs. | Closest conceptual match to "screenshot to structure". Fine-tuning needed to emit slide layouts. | Code availability not on the abstract page **[unverified]**. Fine-tuning needs a GPU. | arXiv 2210.03347, 2022 |
| **Donut** | OCR-free document understanding Transformer: image in, structured text out. Motivation: OCR cost, inflexibility on languages, error propagation. | Reads text without OCR; weak fit, we have a text layer. | Code, model, synthetic data at github.com/clovaai/donut (per abstract). | arXiv 2111.15664, 2021 |
| **Nougat** | Visual Transformer that converts scientific-document PDFs (page images) into markup. | Not relevant: academic papers, math. | Released code/models. | arXiv 2308.13418, 2023 |
| **UDOP** | Unifies vision, text, layout in one Vision-Text-Layout Transformer; can also generate document images from text+layout. | Interesting for "layout to image" research, but heavy and not a practical tool for us. | Code availability not on the abstract page **[unverified]**. | arXiv 2212.02623, 2022 |
| **Florence-2** | Prompt-based vision foundation model: captioning, object detection, grounding, segmentation, text output. | Could localise regions (title, chart, image) on slide renders zero-shot; OCR-with-regions mode exists **[unverified, not on abstract]**. | Sizes and licence **[unverified]**; I recall small variants run on consumer GPUs. | arXiv 2311.06242, 2023 |
| **UReader** | Multimodal LLM, OCR-free; "shape-adaptive cropping" splits a high-res image into crops that each fit a frozen low-res encoder. | The cropping trick is how modern VLMs read dense slides at high resolution. | Fine-tunes 1.2% of parameters; code said "will be released" at abstract time. | arXiv 2310.05126, 2023 |
| **mPLUG-DocOwl 1.5** | Adds "Unified Structure Learning" and an H-Reducer that merges horizontally adjacent patches by convolution to keep layout while shortening the visual sequence. SOTA on 10 document benchmarks. | Evidence that preserving 2-D layout in the token sequence matters. Usable as an open 7B VLM. | 7B-class LLM: needs a sizeable GPU (roughly 16 GB+ **[unverified]**). Code/data on GitHub per abstract. | arXiv 2403.12895, 2024 |

Takeaway: these models are built to extract **text and fields** from pages. None targets "what layout archetype is this slide".

### 2.2 Pixels instead of tokens

- **PIXEL (Language Modelling with Pixels)**: renders text as images and is trained to reconstruct masked pixel patches instead of predicting tokens. 86M parameters. Beats BERT on unseen scripts, slightly weaker on Latin script; more robust to orthographic attacks. ICLR 2023. arXiv 2207.06991, 2022. *Use for us: none; it is about multilingual language modelling.*
- **CLIPPO**: one encoder for images and for text rendered as images, trained with contrastive loss only; about CLIP-level retrieval/zero-shot with half the parameters, no tokenizer, multilingual retrieval without modification. CVPR 2023; code in google-research/big_vision. arXiv 2212.08045, 2022. *Use for us: shows image-of-text embeddings are viable for retrieval across PT/EN; not something we would train.*
- **DeepSeek-OCR: Contexts Optical Compression** (Wei, Sun, Li; DeepSeek-AI; arXiv 2510.18234, 21 Oct 2025).
  - What it is: DeepEncoder (~380M parameters: 80M SAM-base then 300M CLIP-large, with a convolutional compressor between them) plus a 3B MoE decoder (570M active). Page image in, text/markdown out.
  - Headline claims from the abstract: at text/vision-token ratio under 10x, ~97% OCR precision; at ~20x, ~60%. On OmniDocBench it beats GOT-OCR2.0 (256 tokens/page) with 100 vision tokens, and beats MinerU2.0 (6000+ tokens/page) with under 800. Production claim: 200k+ pages/day on a single A100-40G.
  - The numbers in detail (their Table 2, Fox benchmark, English documents with 600-1300 text tokens, only 7 to 28 pages per row): with 100 vision tokens, precision falls from 98.5% (6.7x) to 87.1% (12.6x); with 64 vision tokens from 96.5% (10.5x) to 59.1% (19.7x). Note the "60% at 20x" figure rests on 4 pages.
  - Resolution modes (GitHub README): Tiny 512x512 = 64 vision tokens; Small 640x640 = 100; Base 1024x1024 = 256; Large 1280x1280 = 400; Gundam = tiled n x 640x640 + 1 x 1024x1024. README states CUDA 11.8, torch 2.6.0, python 3.12.9, vLLM 0.8.5, MIT licence. So: open weights, **NVIDIA GPU required** in the documented setup; Windows support not mentioned (I did not verify).
  - The authors' own caveats: above 10x, accuracy drops, possibly due to complex layouts or blurred text at low resolution; "preliminary", "initial investigation". Their per-category table says **slides need only 64 vision tokens**, because slides carry little text (this is the one sentence in the paper about our document type).
  - Follow-ups and critiques I opened: (a) "Visual Merit or Linguistic Crutch? A Close Look at DeepSeek-OCR" (arXiv 2601.03714, Jan 2026): argues much of the accuracy comes from language priors, with accuracy inflated by 60-80% under compression and about 20% in zero-prior settings; VQA about 20% vs >90% for text-QA; collapse between 8,000 and 10,500 text tokens. Note this is a search-result excerpt of an anonymous-submission paper; treat as a single critique, not consensus. (b) "DeepSeek-OCR 2: Visual Causal Flow" (arXiv 2601.20552, Jan 2026): replaces fixed raster-order patch flattening with a learned semantic reading order, 256 to 1120 visual tokens. (c) "Context Cascade Compression" (arXiv 2511.15244) appeared in results; I did not read it, **[unverified]**.
  - Relevance to us: it is an OCR/long-context compression result. It does not claim and does not provide layout classification, style extraction or retrieval. Its one useful hint is that slides are cheap to encode (few tokens), which matters if we ever feed slide images to a VLM.

### 2.3 Visual document retrieval and page embeddings

- **ColPali** (Faysse et al., ICLR 2025; arXiv 2407.01449, 2024). Embeds the *image* of a page with a vision-language model into a *multi-vector* (one vector per patch) representation and matches queries with late interaction (ColBERT-style). Introduces the ViDoRe benchmark. Beats text-extraction retrieval pipelines while "drastically simpler". Per the README, the ColVision family includes ColPali, ColQwen2/2.5 (768 image patches per page for the ColQwen2 variants listed), and small ColSmol-256M / 500M. Pip package `colpali-engine`. Licences: Gemma for the original ColPali, Apache 2.0 for ColQwen2/2.5 and ColSmol. The README page I read does not state VRAM; I would expect a GPU to be needed for ColPali/ColQwen (3B-class) and ColSmol to be the practical local choice **[unverified]**. The README mentions a Mac MPS issue, nothing about Windows. *What it gives us*: text-query to slide-image search ("two-column comparison with a chart"), the closest published fit to our retrieval goal. Caveat: it is trained on pages and queries about *content*; query-by-layout quality is untested by the paper **[unverified for slides]**.
- **CLIP/SigLIP/DINOv2 page embeddings**. SigLIP (arXiv 2303.15343, 2023): CLIP-style image-text model with a pairwise sigmoid loss, models released in big_vision. DINOv2 (arXiv 2304.07193, 2023): self-supervised "all-purpose visual features" that work without fine-tuning, distilled into small models. *What they give us*: one fixed-length vector per slide render; cosine similarity gives "slides like this one"; k-means/HDBSCAN/UMAP over the vectors gives cluster discovery. DINOv2 features are more layout/structure-oriented (no text supervision); SigLIP/CLIP features lean semantic ("a bar chart slide"). Which clusters better for slide layouts is an empirical question I did not find answered in an opened source **[unverified]**. Cost: small variants run on CPU for ~2,300 images in minutes to an hour; GPU optional **[estimate]**. Hugging Face `transformers` loads both.

### 2.4 Layout detection on rendered pages

- **DocLayNet** (arXiv 2206.01062, 2022): 80,863 manually annotated pages, COCO-format boxes, 11 classes; argues PubLayNet/DocBank (scientific articles only) generalise poorly, and DocLayNet-trained models are more robust. Classes are document-oriented (text, title, table, picture, caption, page-header...), not slide-oriented.
- **DocLayout-YOLO** (arXiv 2410.12628, 2024): YOLO-based layout detector pre-trained on a synthetic dataset (DocSynth-300K), "speed and accuracy"; code, data, models at github.com/opendatalab/DocLayout-YOLO. Pure pixels, fast. Local cost: pip install and run, GPU helpful but CPU possible **[unverified]**; licence **[unverified]**.
- **LayoutParser** (arXiv 2103.15348, 2021): open-source toolkit wrapping layout-detection and OCR models behind a common API, plus a model zoo. Older stack (Detectron2), which is often painful on Windows **[unverified]**.
- *What they give us*: boxes labelled title/text/figure/table per slide image. But for *our* PDFs and .pptx we already have exact text boxes, images, and shapes from the file itself. These detectors only add value for slides that are flattened images (scanned or exported as pictures). They were trained on documents, not slides, so box classes would be noisy on slides **[my inference]**.

### 2.5 Slide-specific work

- **DOC2PPT** (Fu et al., AAAI 2022; arXiv 2101.11796, 2021): document-to-slides with a hierarchical seq2seq model with paraphrasing and layout-prediction modules; releases ~6K paired documents and decks. Old; neural layout prediction, not agentic. Historical interest only.
- **SlideVQA** (Tanaka et al., AAAI 2023; arXiv 2301.04883, 2023): 2.6k+ decks, 52k+ slide images, 14.5k questions; multi-image document VQA. Useful as a source of real slide *images* and as a benchmark if we want to test a VLM's slide reading; not a layout-pattern method.
- **AutoPresent / SlidesBench** (Ge et al.; arXiv 2501.00912, 2025): benchmark of 7k train / 585 test examples from 310 decks across 10 domains; finds **programmatic generation (code that builds the slide) beats image generation** and yields editable output; AutoPresent is an 8B Llama fine-tuned on 7k instruction-code pairs, comparable to GPT-4o; self-refinement improves quality. Evidence supporting our native-PPTX approach.
- **PPTAgent** (Zheng et al., ICIP-CAS; arXiv 2501.03936, Jan 2025, v3 Feb 2025; github.com/icip-cas/PPTAgent). Two-stage, edit-based: Stage I analyses *reference presentations* "to extract slide-level functional types and content schemas"; Stage II drafts an outline and generates editing actions on selected reference slides. From the HTML full text: structural slides (opening, outline, closing) are found by an LLM reading all slide text and labelling roles; **content slides are converted to images and grouped with hierarchical clustering, then a multimodal LLM names the layout pattern in each cluster.** Also introduces PPTEval (Content, Design, Coherence). This is the closest published analogue of what we want, and it is the same recipe we partly did by hand (contact sheets plus a vision LLM). I could not confirm from the README page the exact embedding used for clustering, nor models and licence; **[unverified]**, read the repo code before copying.

## 3. What this means for us

Our three jobs, honest ranking. "Learned" below means a model we download; "non-ML" means reading the file.

### (iii) Extract style (fonts, colours, positions) from PDFs: **non-ML wins, clearly**

1. **Read the PDF text layer with PyMuPDF** (`page.get_text("dict")` returns per-span font name, size, colour, bbox; `page.get_drawings()` returns vector shapes with fill colours and rects; `page.get_images()` returns image rects). Exact, instant, CPU-only, no hallucination. I did not open the PyMuPDF docs in this session, **[unverified here]**, but this is standard documented behaviour and trivial to test on one PDF. Where a PDF has no text layer (slide exported as image) fall back to a layout detector plus OCR; none of the papers above are needed for text-layer PDFs.
2. Keep the .pptx XML stats as ground truth and use them to *check* the PDF extraction on the 39 decks that exist in both forms, if any overlap.
3. No learned model is justified for fonts/colours/positions. A VLM can mis-read a font size or a hex colour; a patch model cannot output either exactly.

### (i) Discover slide-type / layout patterns across the archive: **learned image embeddings plus clustering, then use the existing LLM labels as a check**

1. **Render each slide to an image, embed with DINOv2 (small/base) and/or SigLIP, cluster (HDBSCAN or agglomerative), then review each cluster once** (montage plus a vision-LLM name, i.e. PPTAgent's recipe). Local cost: low; CPU feasible for ~2,300 slides. Value over what we did: clusters are driven by pixels, not by a model's prior idea of 25 categories, so they can reveal types the LLM lumped together or split; compare against the 25 existing labels (adjusted Rand / confusion matrix) to find disagreements.
2. **Add cheap structural features from the text layer / XML** (counts and normalised bboxes of text blocks, images, tables/charts, title position, column count, text-area fraction) and cluster on those too, or concatenate with the embedding. For layout archetypes this is often more discriminative than pixels, and it is exact. **[my judgement; not tested]** Do this one first because it costs an afternoon and needs no model.
3. Do not use DeepSeek-OCR, Donut, Nougat or LayoutLMv3 here: they target text recovery.

### (ii) Retrieve "slides like this one" to choose an archetype: **embedding nearest-neighbour search first; ColPali/ColSmol only if text-query-to-slide search proves necessary**

1. **Same DINOv2/SigLIP vectors in a flat index** (numpy cosine or FAISS; 2,300 vectors need no database). Query by an example slide image, or a short textual description via SigLIP's text tower. Combine with the structural features from (i) and a filter on slide-type label. Cheapest, fully local, easy to evaluate.
2. **ColSmol-256M/500M (Apache 2.0) or ColQwen2.5 via `colpali-engine`** if users will type free-text requests ("slide comparing three options with a chart") and single-vector SigLIP is too weak. Heavier (multi-vector, ~hundreds of patch vectors per slide) and likely GPU-dependent; verify VRAM and Windows install before committing **[unverified]**.
3. For *choosing* an archetype, remember the PPTAgent/AutoPresent lesson: retrieval picks a reference slide, then code/edit actions fill it. That matches our native generator; neither paper argues for generating slide pixels.

### Where learned patch models clearly win

- Embedding-based **similarity and cluster discovery over rendered slides** (no need to define features by hand).
- **Text-to-slide-image retrieval** (ColPali family).
- **Flattened/image-only slides** where no text layer exists (layout detector or VLM).

### Where they do not

- Exact fonts, sizes, colours, bboxes (PDF text layer / XML).
- Reading text from born-digital PDFs (the text layer is exact; DeepSeek-OCR's 97% is an OCR figure, a worse number than 100%).
- DeepSeek-OCR-style optical compression: irrelevant to our goals unless we later want a cheap way to put whole decks into an LLM context, and the critique above suggests caution.

### Suggested order of work (all low-cost)

1. PyMuPDF structural dump for every PDF slide (fonts, colours, boxes) and a structural feature vector.
2. DINOv2-small and SigLIP embeddings of slide renders; cluster; compare with the 25 LLM labels.
3. Build the nearest-neighbour lookup for archetype selection; only then decide if ColSmol is needed.

## 4. Doc inconsistencies and caveats

- I was not given project docs to check against, so I make no claims about inconsistencies with the existing code or notes.
- The brief mentions "DeepSeek-OCR ... probably the article the user saw". I confirmed the paper and its claims, but I have no sight of the article itself.
- Not covered or not opened: Donut/Pix2Struct/UDOP licences and hardware, Florence-2 model sizes, DocLayout-YOLO licence, ColPali VRAM, PubLayNet paper, PyMuPDF documentation, Windows install status of any model.

## Sources (all opened in this session)

1. ViT: https://arxiv.org/abs/2010.11929 (2020)
2. DiT: https://arxiv.org/abs/2203.02378 (2022)
3. LayoutLMv3: https://arxiv.org/abs/2204.08387 (2022)
4. Pix2Struct: https://arxiv.org/abs/2210.03347 (2022)
5. Donut: https://arxiv.org/abs/2111.15664 (2021)
6. Nougat: https://arxiv.org/abs/2308.13418 (2023)
7. UDOP: https://arxiv.org/abs/2212.02623 (2022)
8. Florence-2: https://arxiv.org/abs/2311.06242 (2023)
9. UReader: https://arxiv.org/abs/2310.05126 (2023)
10. mPLUG-DocOwl 1.5: https://arxiv.org/abs/2403.12895 (2024)
11. PIXEL: https://arxiv.org/abs/2207.06991 (2022; ICLR 2023)
12. CLIPPO: https://arxiv.org/abs/2212.08045 (2022; CVPR 2023)
13. DeepSeek-OCR (abstract and HTML full text): https://arxiv.org/abs/2510.18234 , https://arxiv.org/html/2510.18234v1 (2025)
14. DeepSeek-OCR GitHub README: https://github.com/deepseek-ai/DeepSeek-OCR (accessed 2026)
15. Critique, "Visual Merit or Linguistic Crutch? A Close Look at DeepSeek-OCR": https://arxiv.org/html/2601.03714v2 (2026; search-result excerpt only)
16. DeepSeek-OCR 2: https://arxiv.org/html/2601.20552v1 (2026; search-result excerpt only)
17. ColPali: https://arxiv.org/abs/2407.01449 (2024; ICLR 2025)
18. ColPali/ColQwen README: https://github.com/illuin-tech/colpali (accessed 2026)
19. SigLIP: https://arxiv.org/abs/2303.15343 (2023)
20. DINOv2: https://arxiv.org/abs/2304.07193 (2023)
21. DocLayNet: https://arxiv.org/abs/2206.01062 (2022)
22. DocLayout-YOLO: https://arxiv.org/abs/2410.12628 (2024)
23. LayoutParser: https://arxiv.org/abs/2103.15348 (2021)
24. DOC2PPT: https://arxiv.org/abs/2101.11796 (2021; AAAI 2022)
25. SlideVQA: https://arxiv.org/abs/2301.04883 (2023)
26. AutoPresent / SlidesBench: https://arxiv.org/abs/2501.00912 (2025)
27. PPTAgent (abstract and HTML full text): https://arxiv.org/abs/2501.03936 , https://arxiv.org/html/2501.03936v3 (2025); repo page https://github.com/icip-cas/PPTAgent (opened, but the page excerpt did not describe method or licence)
