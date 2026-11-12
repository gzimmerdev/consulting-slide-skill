# Research: a "second brain" for the slide project

Date: 2026-11-08. Scope: how to organise all project content (archive slides/elements, per-case data and research, insights, approved slides, styles, rulings) so both the user and Claude find and reuse it. Source quality note: web search returned mostly secondary write-ups for the PKM methods; where I fetched a primary page it is marked (primary). Claims I could not verify against a primary source are flagged.

## 1. Methods and their fit

| Method | Core idea | Fit here |
|---|---|---|
| PARA / CODE (Forte) | Organise by actionability: Projects, Areas, Resources, Archives; capture-organise-distill-express ([overview, secondary](https://dev.to/gantengx/the-pkm-setup-i-settled-on-after-many-iterations-6pa)) | Good for the per-case lifecycle (active case -> archived case). Bad as the top-level structure: the archive decks are a permanent library, not "resources by status". Take only: one folder per case, move to `done/` when finished. |
| Zettelkasten / evergreen notes (Matuschak) | Notes are atomic, concept-oriented, densely linked, and prefer associative links over hierarchical taxonomies ([primary](https://notes.andymatuschak.org/Evergreen_notes)) | Right for **insights** and **element patterns** ("waterfall + table reads as a bridge story"), which should outlive the case they came from. Overkill for slides/data, which are records, not ideas. |
| Johnny.Decimal | Fixed numbered areas/categories (10x10) ([concepts, community site](https://v4-johnnydecimal.netlify.app/concepts)) | Useful idea only: stable, numbered top folders (`10-archive`, `20-cases`...). Skip the 100-ID discipline. |
| MOC (Nick Milo) | A hand-or-auto-built index note per topic that links to member notes ([secondary](https://digital-garden-jekyll-template.pages.dev/working-with-johnny-decimal)) | Directly useful: one generated MOC per case, per archetype, per exhibit type. Auto-generate, never hand-maintain. |

Consulting firms (secondary sources only; I found nothing primary on McKinsey/BCG internals): knowledge teams write an abstract per engagement and tag it by service and client industry ([law-firm KM tagging](https://www.scl.org/883-knowledge-management-data-tagging-for-law-firms/), [Bain KM role posting](https://careers.bain.com/jobs/FolderDetail/Associate-Knowledge-Management-BIMTECH-PG-Batch-of-2026/99483)); firms use a standard template per knowledge item and a controlled taxonomy (one academic case: 12 top categories, ~500 terms) ([study](https://storage.imrpress.com/imr/journal/KO/article/505545/1752847488617.pdf)); automated tag suggestion with human accept/edit gives better metadata ([vendor case, treat as marketing](https://www.poolparty.biz/auto-tagging-key-to-consulting-knowledge-management-system)). Takeaway: small controlled vocabulary + one-paragraph abstract + a fixed template per item. Your `elements_labeled.jsonl` already is this at element level.

## 2. Formats and how Claude uses them

Anthropic's own guidance points one way:

- Agents work best with lightweight identifiers (paths, stored queries) and load content just in time; folder structure, file names and timestamps are themselves signals; a hybrid (small upfront context + glob/grep exploration) is recommended; persistent notes outside the context window (NOTES.md style) are the memory mechanism ([context engineering, primary](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)).
- Skills load only name+description at start, the SKILL.md body on trigger, and referenced files only when needed ([Agent Skills docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview); I confirmed the redirect but only read secondary summaries of the three-tier model, so verify). CLAUDE.md/memory is loaded every session, so keep it short.
- Contextual Retrieval: below ~200k tokens of knowledge, skip RAG and put it all in the prompt with caching; above that, contextual embeddings + BM25 + reranking cut top-20 retrieval failures 5.7% -> 1.9% ([primary](https://www.anthropic.com/news/contextual-retrieval)).

Sizing against this project: `elements_labeled.jsonl` is 8 MB (about 2M tokens) and `elements.jsonl` 7.9 MB, so the raw archive does NOT fit in context; it needs a compact index. But the **per-slide digest** (deck, slide, layout, exhibit types, density, 1 line; `elements_labeled.jsonl` has no title text or archetype label, so phase 0 leaves them out) for 874 slides is roughly 60-100 KB (~25k tokens), which fits in context or one grep. Everything else (insights, cases, rulings, exemplars) is far below 200k tokens.

Format choice:
- **Markdown + YAML frontmatter files** (Obsidian-compatible, `[[wikilinks]]`): human-readable, git-diffable, greppable by Claude with Grep/Read, no server. Obsidian is optional: it just gives the user a graph/backlinks/search UI over the same folder.
- **JSONL/JSON** stays the machine layer (already there). Notes are *generated views* of it.
- **SQLite** (FTS5): only if grep over notes becomes too slow or you need joins (e.g. "all waterfalls with density > X in energy decks"). `retrieve.py` already does structured retrieval over jsonl; no DB needed yet.
- **Vector/RAG**: not now. The vocabulary is small and labelled; structured filters + keyword search beat embeddings at this scale, and an embedding service is extra infrastructure. Revisit if you add >200k tokens of free text (e.g. research PDFs per case).
- **Knowledge graph database**: no. Wikilinks in frontmatter (`case: [[acme-2026]]`) give 95% of it.
- **MCP access**: Claude Code already reads/writes the folder with Read/Grep/Write; no Obsidian MCP is needed. For Claude Desktop (no filesystem tools), add 2-3 tools to the existing `mcp_server.py` (below) rather than installing a generic filesystem/Obsidian MCP.

## 3. Retrieval research for slide generation: what to index

- PPTAgent (EMNLP 2025) clusters reference slides into functional types, extracts a content schema per type (element category, modality, content), then generates new slides by edit actions on selected reference slides ([paper](https://arxiv.org/abs/2501.03936), [HTML](https://arxiv.org/html/2501.03936v3)). I read the abstract only, not the full method; the cluster-then-schema design matches what this project already does (archetypes, `retrieve.py` retrieve-and-edit, `compose.py`).
- Implication for indexing: index at three granularities, because the user ruled (2026-11-06) that the archive is a library of **elements and their connections**, not slides to copy: (a) slide = composition signature (list of element kinds + layout + density), (b) element = kind/sub/role/bbox/words, (c) link = which element connects to which (`links` in the jsonl). Retrieval keys: exhibit types, composition signature, topic/industry, message type (insight shape), density. Embedding the *title text* is the only place semantic search might help; a keyword match on the action title plus tags is enough to start.
- The Contextual Retrieval lesson transfers cheaply: give every chunk a one-line "situating context" (deck, year, competition, case topic) in its note's first line. Do this in the generator script, no LLM needed.

## 4. Schema proposal

Entities, all Markdown notes with frontmatter unless marked (J = stays JSON):

| Entity | Key fields | Links |
|---|---|---|
| `case` | id, title, client, industry, function, lang, competition, status (active/done), brief | -> sources, data, insights, slides |
| `source` | id, case, kind (pdf/xlsx/web/interview), path/url, date, summary | <- insights, data |
| `data` | id, case, source, metric, unit, period, values path (J/xlsx), caveat | -> slides |
| `insight` (evergreen) | id, claim (full sentence = title), evidence, shape (compare/trend/bridge/...), case, tags | -> data, slides, patterns |
| `slide` (approved/produced) | id, case, spec path (J), png, archetype, lang, style, insights used, status (draft/approved), parent exemplar | -> exemplar, style |
| `archive_slide` (generated, read-only) | deck, slide, title, archetype, exhibits, density, element signature, png crop | <- patterns |
| `pattern` (element pattern / composition) | id, name, composition signature, when to use, 2-5 archive slide refs, spec template | MOC-like |
| `style` | id, tokens file, source deck | <- slides |
| `ruling` | date, text starting "Ruling (user, YYYY-MM-DD):", scope | rendered from memory file |
| `exemplar` | id, spec J, png, note, A/B result | = existing `exemplars/index.json` |

Folder layout (Johnny.Decimal-flavoured, numbered so order is stable):

```
brain/
  00-index/        MOCs (generated): by case, archetype, exhibit type, industry
  10-archive/      archive_slide notes (generated, one per deck, 874 rows -> 27 deck files, not 874 files)
  20-cases/<case-id>/  case.md, sources/, data/, insights/, slides/
  30-patterns/     pattern notes + element-library.md pointers
  40-styles/       style notes -> docs/styles.md, style JSON
  50-rulings/      rulings.md generated from memory
```
Naming: `kebab-case`, case id `YYYY-short-name`, insight file = its claim in 6-10 words. Tags: controlled lists only (`industry/`, `function/`, `exhibit/`, `archetype/`, `lang/`, `status/`), defined once in `00-index/vocab.md`.

Key decision: archive slides get **one note per deck** with a table of slides (not 874 notes). One note per slide would flood Obsidian's graph and Claude's grep with near-duplicate noise. Promote an archive slide to its own note only when it becomes an exemplar or pattern reference.

Mapping of existing assets:
- `analysis/elements_labeled.jsonl` -> source of truth for `archive_slide`; generator `tools/build_brain.py` writes deck notes + a flat `brain/00-index/slides.tsv` digest.
- `exemplars/` + `index.json` -> `exemplar` and approved `slide` entries (note gets `spec:` path and `png:` embed `![[x.png]]`).
- `examples/*.json`, `catalog.json` -> `pattern` templates.
- `docs/element-library.md`, `archetypes.md`, `styles.md` -> stay as-is; brain notes link to them (no duplication).
- memory `slidegen-decisions.md` -> `ruling` list; keep memory as the master, generate a read-only copy (CLAUDE.md global rule: rulings start with "Ruling (user, date):").
- Per-case data/research: new, hand/Claude-written under `20-cases/`.

Claude's read/write path (skill steps, added to `.claude/skills/slide/SKILL.md`):
1. Start of a request: read the case's `case.md` (if any) and `00-index/vocab.md`.
2. Retrieve: existing `suggest_composition`/`retrieve.py`, then Grep `brain/30-patterns` and the insights for the topic.
3. After the user approves a slide: write/append `slides/<id>.md` (frontmatter + link to spec/png), any new `insight` notes (one claim each), and update the exemplar index.
4. New data/research from the user: write a `source` + `data` note immediately (summary + path), so next session does not re-read the xlsx.
For Claude Desktop add MCP tools `brain_search(query, filters)`, `brain_read(id)`, `brain_add(kind, fields)` to `mcp_server.py` (thin wrappers over the same folder).

Sync: archive notes and MOCs are generated and overwritten (marked `generated: true`, never hand-edited); case/insight/slide notes are hand-or-Claude-written and never overwritten. One script, run after `mine_elements.py` or after approving a slide.

## 5. Recommendation and phased plan

Plain-Markdown vault + generated indexes over the existing JSONL; Obsidian optional as a viewer; no DB, no vectors, no new MCP server.

| Phase | Deliverable | Effort | Value |
|---|---|---|---|
| 0 (do first) | `tools/build_brain.py` writes `brain/00-index/slides.tsv` (874 rows digest) + 27 deck notes + vocab.md, from elements_labeled.jsonl | ~0.5 day | Claude can grep the whole archive in one call; user can browse decks in Obsidian |
| 1 | `20-cases/` template + skill steps 1,3,4 (case.md, source/data/insight notes written by Claude) | ~0.5 day | Per-case memory survives sessions; first real "second brain" use |
| 2 | Promote approved slides/exemplars to notes; generated MOCs by archetype/exhibit/industry; rulings export | ~0.5 day | Browsable history, patterns linked to evidence |
| 3 (only if needed) | `brain_*` MCP tools for Claude Desktop; SQLite FTS if grep is slow | ~1 day | Desktop parity |

Risks: (1) drift between generated and hand notes -> strict `generated:` flag and separate folders; (2) over-tagging -> controlled vocab, ≤6 tag facets; (3) Claude not writing notes -> make it a skill step with a checklist, not a hope; (4) duplicated truth with memory/docs -> link, don't copy; (5) archive decks are other teams' work: keep `brain/` out of anything shared.

**Do NOT build (YAGNI):** vector DB or embeddings; a knowledge-graph database; one note per archive slide or per element; a custom UI/web app; a generic Obsidian/filesystem MCP; automatic LLM tagging of all 874 slides (labels already exist); PARA/Zettelkasten ceremony (daily notes, fleeting notes, literature notes); Johnny.Decimal 100-ID scheme; a sync service beyond one idempotent script.

## Inconsistencies noted
None found between docs and code during this research (I did not audit code beyond file sizes and the jsonl keys). `docs/element-library.md` and `analysis/elements_labeled.jsonl` were not cross-checked in detail.
