"""MCP server: lets Claude Desktop (your subscription) generate slides with this tool.

Claude talks to you, writes the spec, calls build_slide, looks at the rendered PNG it gets back, and fixes what's off.
Registered in %APPDATA%\\Claude\\claude_desktop_config.json as "slidegen" (see docs/mcp.md).
Never print to stdout here: stdout is the MCP channel.
"""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from mcp.server.fastmcp import FastMCP, Image                      # noqa: E402
import build                                                       # noqa: E402
from slidegen.core import themes, find_icons as _find_icons       # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
import style_from_deck, compose, retrieve, rank                                    # noqa: E402

OUT = ROOT / "out" / "mcp"
CATALOG = json.loads((ROOT / "examples" / "catalog.json").read_text(encoding="utf8"))
BRANCHES = {b["properties"]["type"]["const"]: b for b in build.SCHEMA["oneOf"]}

mcp = FastMCP("slidegen", instructions="""
You build ONE finished, editable PowerPoint slide in the user's consulting-competition style (pt or en) from the data,
text and research the user gives. Dense is the default (archive: ~180 words, ~63% of the body covered).
Whenever the user asks for a slide ("/slide", "slide", "gera um slide"), use THESE slidegen tools, never a pptx/slides skill
or your own python-pptx code. Workflow:
1) Read everything the user gave. Excel: use {"excel": {"file", "sheet", "range"}} in chart/table/waterfall data
   (first row = series names, first column = categories). 2) Write a content profile: message, items (id, kind
   bridge|trend|composition|ranking|comparison|distribution|correlation|kpi|geo|process|matrix|lookup_table|list|text,
   points, series, words, label), relations (leads_to|compares|sums_to|explains|located_in|zooms_into), insights, decisions.
   Data shapes to name explicitly: parts that sum to a total (CAPEX = a+b+c) -> kind breakdown (points = leaves, groups [3,3]);
   assumptions with their origin/source -> kind assumptions (points = rows, series = columns); time series with named phases
   -> trend + phases N; negative-then-positive cash flow -> trend + signed true (+ payback true); KPIs (payback, IRR) -> kpi.
   RULES: composite is the DEFAULT for anything with 2+ data blocks (a cost tree, a chart, assumptions, KPIs...); the
   fallback archetypes (multi_chart, chart_takeaway, ...) only for ONE exhibit + prose. Every data block the user gave must
   appear on the slide (numbers, assumptions, sources, KPIs); do not restate the headline in panel banners (panel titles name
   the exhibit and unit, e.g. "Fluxo de caixa anual, R$ mi"); no mirrored symmetric halves; build_slide warns on fallbacks.
3) slide_grammar() once per conversation: how archive slides combine sections, blocks, headers, grey boxes, dividers and connectors
   (frequencies from 419 labelled slides). Use it to choose and fill the composition; the layout still comes from the content.
   suggest_composition(profile) -> density, 3 options (layout, panels, links, why, spec skeleton, archive examples) and
   "nearest" (closest archive slides with PNG paths, closest ready specs from examples/ and exemplars/). Use them as a check, not
   a template: build from the option's skeleton (its layout comes from the content); copy element styling from exemplars, never
   a whole layout (user ruling: the archive is a library of elements, not slides to copy). Edit a whole spec only to rebuild an archive slide.
4) If density is "thin": FIRST tell the user the slide may be less dense than usual for this case ("os dados podem deixar
   o slide menos denso que o normal para este tipo de caso"), then present the options that fit, then continue with the best.
5) Say the chosen option in one line: why it fits the content, plus an archive slide with the same element pairing if any.
6) Fill the skeleton: headline = action title with a number (<=190 chars); all the data; insights with ==accent== keywords
   (rich text: **bold**, ==accent==, //italic//); source on every slide - never invent one ("Dados ilustrativos" if none);
   do the arithmetic yourself. Ask the style only if not given (list_styles); keep bain_red's look as is.
7) build_slide(spec): read the WARNINGs (density, overflow) and fix them: fill empty cells, add content, grey panels only
   if the style uses them. 8) Look at the returned image: overlaps, overflow, title <=2 lines; fix and rebuild.
9) Make 3 variants (different layout or element choice), call rank_candidates(specs): it builds, measures against the
   archive and orders them. Render the top one (build_slide), check density, hierarchy and styling against the nearest archive image, do ONE fix round.
10) Reply with the .pptx path and your assumptions. When the user approves the slide, call save_exemplar(spec, png_path, note).
find_similar(profile_or_spec) re-runs the retrieval for any spec you edited.
New: layouts up to 6 panels (4col, 2x3, L|R3, T|B3, T2|B3), chart kind scatter/bubble (points {x,y,label,size}, quadrants,
highlight) for correlations, and spec field logo {file, position footer-right|footer-left|top-right, height} or a list of up to 3; tag + tag_style "plain" =
small caps kicker above the title; title_size (pt, short titles); panel title_badge (numbered circle before the panel title).
Also: layout "cols" (free columns split into rows, column title + intro; use it to follow an archive slide's arrangement),
panel kind flow (boxes + connectors + "+" operator circles), icons on kpis/cards/bullets and in table cells {icon, text},
pill cells {pill, color} + pill_legend, table styling (up to 10 columns; head_fill one colour or per column, col_fill,
bands, grid; cells {text, fill, bold, box} to tint, bold or dash-box one figure), side_label strips, scale (gradient bar), chart phases / doughnut callouts /
legend_pos inside, spec chart_font (archive charts are often 8-10 pt), tracker style nodes|boxes, links connector
(bar -> table row) and note (dotted callout). Details: get_archetype("composite"). Maps are made externally, not by the tool.
Show the parts (user ruling): on slides with 3+ panels use cols column titles as section headers (title_badge 1,2,3 for an order),
divider true (dashed line between columns), dividers true (dashed line between stacked blocks) and panel "grey" on 1-2 blocks
of a different kind (results, assumptions); never grey on every block.
Dense, not crammed (user ruling): at most 3 sections, each = header + ONE main exhibit + at most ONE
supporting element (big numbers, small table or 2 one-line bullets); a 1-2 line intro (12 pt) under a header is optional
(archive: ~9% of headers), only when header + exhibit do not say the point; 12 pt prose under ~110 words per slide, detail in tables
(9-10 pt) or charts. Density reference (not layout templates): exemplars 024, 029, 030, 031, 032.
For 4-6 blocks suggest_composition returns structurally different section options (user rulings): "sections" (2-4 equal columns),
"wide" (the main exhibit's section ~1.6x wider), "L" (a tall section beside two stacked sections with their own headers, cols row_titles),
"grid" (2x2 sections), "band" (the main exhibit across the top, when it needs width), "strip" (KPIs across the top, when they relate
to no other block). Their order is drawn from how often the archive uses each disposition (slide_grammar), boosted by the content.
Pick by the content and say why in one line; do not always take the same structure. Keep the skeleton's section_style (section
header look from the archive mix: label, centred_rule, bar, rule). Build WARNINGs about a header needing 2 lines, a table header
breaking mid-word, or chart category labels too long for their bars must be fixed before you show the slide.
Icons by default (user ruling): a bullets panel or cards/kpis with 2-5 short items (recommendations, drivers, KPIs) gets one icon
per item (find_icons for names), chosen for each item's point; at most one icon set per slide; long-text bullets stay plain.
Emphasis (optional, 1-3 per slide, only where they carry the message): spec "emphasis" [{kind backdrop (panels, y [from,to],
fill grey|pale|hex, outline) = grey box behind the key panel or a so-what band; pointer (from, to, shape triangle|block) =
triangle/arrow between two neighbouring panels; accent_bar (panel)}], panel title_shape pentagon|chevron (step headers),
kpis item delta up|down. Archive uses them for contrast on 90% of slides; see get_archetype("composite") "Emphasis shapes".
Fallback (one exhibit with a prose column is genuinely best): the other 25 archetypes - list_archetypes, get_archetype.
Icons: find_icons("money").
Own design (colours, fonts, logo): when the user describes their look or sends their slides (.pptx/.pdf path, or
screenshots), save it as their style: extract_style(path, save_as=NAME) for a deck (colours, fonts, title, corners, a corner
logo; it notes missing fonts / no logo), or add_style(NAME, tokens, logo_file=..., logo_position=...) from words or
screenshots (read the hex colours). Then build_slide a sample with style=NAME, compare it with their slides, fix tokens with
add_style (two rounds at most), and ask whether it should be the default (add_style(NAME, {}, default=True)): the default
applies to every slide that names no style. Styles live in my_styles/ (local). Never copy another team's logo.
Gotchas: recommendations go in decisions: N only (not also a list item); a bullets panel takes items (bullets = text under a
chart/table); table_header is spec-level; percents: fractions + "0%" or numbers + '0"%"'; a waterfall of reductions = total_first
with lever magnitudes; in cols, panels fill column 1 top to bottom, then column 2; skeleton links are suggestions.
Styling (as exemplars 024/029): the section header (cols title, title_badge 1-3) is the only bar; panel titles under it are
title_plain: true (never two bars stacked). Rating pills: one brand colour for favourable, grey for neutral, dark for
unfavourable, judged per criterion (a HIGH cost or HIGH risk is unfavourable); no red/yellow traffic lights. A section header
must fit on one line (~40 characters in a third-width column); table headers must not break mid-word (shorter header or col_weights).
""")


@mcp.prompt()
def slide(request: str) -> str:
    """Make one slide with the slidegen tools (pick it from the + menu in Claude Desktop)."""
    return ("Use the slidegen MCP tools (not a pptx/slides skill) and follow their workflow: profile -> suggest_composition -> "
            "slide_grammar -> fill the skeleton -> build_slide -> check the image -> fix. Request:\n\n" + request)


@mcp.tool()
def suggest_composition(profile: dict) -> dict:
    """Content profile -> density verdict + top 3 composite-slide options (layout, panels, links, why, spec skeleton, archive examples).
    profile = {message, lang, items:[{id, kind, points, series, words, label}], relations:[{from, to, type}], insights, decisions}.
    Item kinds: bridge trend composition ranking comparison distribution correlation kpi geo process matrix lookup_table list text, plus
    breakdown (parts summing to a total; points = leaves, groups = [leaves per sub-total] -> flow panel with "+" junctions),
    assumptions (rows with an origin/source; or lookup_table/list with sourced:true -> table with pill cells + pill_legend),
    trend flags phases:N (named phases -> chart phases), signed:true (negative then positive -> column), payback:true (note link);
    composition flag hierarchy:true or parts:[...] = breakdown. Other flags: br_states qualitative share numeric titled dimensions.
    If density is "thin", tell the user first, then show the options that fit."""
    return compose.suggest(profile)


@mcp.tool()
def slide_grammar() -> str:
    """Archive slide grammar (brain/30-patterns, generated by tools/grammar.py from vision labels of 419 archive slides): sections and
    widths, headers and intros, what stacks in a section, grey boxes and dividers, connectors. Habits with frequencies, not layouts to copy."""
    d = ROOT / "brain" / "30-patterns"
    return "\n\n".join(f.read_text("utf8") for f in sorted(d.glob("*.md"))) if d.exists() else "brain/30-patterns missing: run py -3 -I tools/grammar.py"


@mcp.tool()
def find_similar(profile_or_spec: dict, k: int = 3) -> dict:
    """k closest archive slides (deck, slide, structure summary, png path or how to export it) and k closest ready specs
    (examples/ + approved exemplars/) to a content profile or a spec. Use them to check density and element styling; edit a whole
    spec only when the user asks to rebuild that archive slide."""
    return retrieve.nearest(profile_or_spec, k)


@mcp.tool()
def rank_candidates(specs: list[dict]) -> list[dict]:
    """Build 2-3 candidate specs and rank them (best first): structure distance to the nearest archive slide, metrics outside
    archive p10-p90, build warnings, with a one-line reason and the .pptx path. You still pick visually from the renders."""
    return rank.rank(specs)


@mcp.tool()
def save_exemplar(spec: dict, png_path: str, note: str = "") -> str:
    """Save a slide the user approved (spec + its rendered png) to exemplars/ so find_similar can return it next time."""
    return retrieve.save_exemplar(spec, png_path, note)


@mcp.tool()
def list_archetypes() -> str:
    """The 25 slide types with what each is for. Choose by the message you want to say."""
    return "\n".join(f"{t}: {b.get('description', '')}" for t, b in BRANCHES.items())


@mcp.tool()
def get_archetype(type: str) -> str:
    """JSON Schema (fields, required, character limits) and one valid example spec for a slide type."""
    if type not in BRANCHES: return f"unknown type. Types: {', '.join(BRANCHES)}"
    return json.dumps({"schema": BRANCHES[type], "example": CATALOG.get(type)}, ensure_ascii=False)


@mcp.tool()
def list_styles() -> str:
    """Available visual styles (colours, fonts, header/takeaway style). Pass the name as `style` to build_slide."""
    keys = ("primary", "heading_font", "body_font", "title_size", "header_style", "takeaway_style", "corners")
    return "\n".join(f"{n}: " + ", ".join(f"{k}={v[k]}" for k in keys) + f"  ({v.get('_src', '')})" for n, v in themes().items())


@mcp.tool()
def find_icons(query: str) -> list[str]:
    """Icon names (Lucide line icons) containing a word, e.g. 'chart', 'users', 'dollar'. Use the name in `icon` fields."""
    return _find_icons(query.lower().strip(), 30)


@mcp.tool()
def build_slide(spec: dict, name: str = "slide", style: str | None = None, primary: str | None = None,
                font: str | None = None, heading_font: str | None = None, preview: bool = True) -> list:
    """Validate and build one native .pptx slide; returns the file path and (preview=True) a PNG rendered by PowerPoint.
    On invalid input returns the list of errors to fix. style/primary/font override the spec's theme."""
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", name)[:60] or "slide"
    out = OUT / f"{safe}.pptx"
    try:
        spec = build.resolve_excel(dict(spec), ROOT)
    except Exception as e:                                          # bad Excel path/range -> tell Claude
        return [f"Spec invalid: {e}"]
    warns = []; errs = build.build_specs([spec], str(out), style, primary, font, heading_font, warns)
    if errs: return ["Spec invalid - fix these and call build_slide again:\n" + "\n".join(errs)]
    result = [f"Built {out}" + "".join(f"\nWARNING {w}" for w in warns)]
    if preview:
        png = out.with_suffix(".png")
        try:      # preview needs Windows + Microsoft PowerPoint (tools/preview.ps1); elsewhere the .pptx is still built
            r = subprocess.run(["powershell", "-NoProfile", "-File", str(ROOT / "tools" / "preview.ps1"), str(out)],
                               capture_output=True, text=True, timeout=180); err = r.stderr[-300:]
        except (OSError, subprocess.TimeoutExpired) as e: err = f"{e} (preview needs Windows + PowerPoint; open the .pptx to check it)"
        result.append(Image(path=str(png)) if png.exists() else f"(preview failed: {err})")
    return result


@mcp.tool()
def open_in_powerpoint(name: str = "slide") -> str:
    """Open a slide built by build_slide in PowerPoint on the user's machine."""
    p = OUT / f"{re.sub(r'[^A-Za-z0-9_-]+', '_', name)}.pptx"
    if not p.exists(): return f"not found: {p}"
    if sys.platform == "win32": os.startfile(p)
    else: subprocess.run(["open" if sys.platform == "darwin" else "xdg-open", str(p)])
    return f"opened {p}"


@mcp.tool()
def extract_style(deck_path: str, save_as: str | None = None, default: bool = False) -> str:
    """Copy the design of the user's own slides: derive a style (primary + series colours, fonts, title size/bold, corners and a
    logo repeated in a slide corner) from a .pptx or .pdf. With save_as it is saved in my_styles/ (local, survives updates) and
    build_slide(style=save_as) uses it; default=True makes it the style of every slide that names none. After saving, build a
    sample slide with it, compare with the user's deck and adjust tokens with add_style."""
    p = Path(deck_path)
    if not p.exists() or p.suffix.lower() not in (".pptx", ".pdf"): return "give the full path of a .pptx or .pdf"
    if not save_as: return json.dumps(style_from_deck.derive(str(p)), ensure_ascii=False, indent=1)
    r = style_from_deck.from_deck(str(p), save_as, default=default); st = next(v for k, v in r.items() if k != "_default")
    notes = ([] if "logo" in st else ["no repeated corner logo found: ask the user for a logo file and call add_style(name, {}, logo_file=...)"]) + \
            [f"font '{f}' is not installed on this PC: slides will fall back; ask to install it or set another font" for f in style_from_deck.missing_fonts(st)]
    return json.dumps(r, ensure_ascii=False, indent=1) + "".join("\nNOTE " + n for n in notes)


@mcp.tool()
def add_style(name: str, tokens: dict, logo_file: str | None = None, logo_position: str | None = None, default: bool = False) -> str:
    """Create or update the user's own style from a description ("our colour is #1F6FEB, titles in Georgia, logo bottom-left"):
    tokens that differ from defaults, e.g. {"primary": "1F6FEB", "heading_font": "Georgia", "header_style": "bar",
    "corners": "rounded", "series": [4 hex dark->light]}; every token is in docs/styles.md (primary, title_color, heading_font,
    body_font, title_size, title_bold, header_style, rule_width, takeaway_style, corners, badge, footer_rule, title_rule, series,
    dark, on_primary, ...). logo_file = path of a logo image (png/jpg), logo_position footer-right | footer-left | top-right.
    Saved in my_styles/ (local); default=True makes it the style of every slide that names none."""
    try: r = style_from_deck.save(name, {k: (v.lstrip("#").upper() if isinstance(v, str) and re.fullmatch(r"#?[0-9A-Fa-f]{6}", v) else v) for k, v in tokens.items()},
                                  logo=logo_file, logo_position=logo_position, default=default)
    except (ValueError, OSError) as e: return str(e)
    return f"saved: {json.dumps(r, ensure_ascii=False)}"


if __name__ == "__main__":
    mcp.run()
