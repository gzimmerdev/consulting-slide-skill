"""Generates schemas/archetypes.schema.json (single source of truth for input specs). Run: py -3 -I tools/gen_schema.py"""
import json, pathlib
S = lambda n, mn=1: {"type": "string", "minLength": mn, "maxLength": n}
def arr(item, mn, mx): return {"type": "array", "items": item, "minItems": mn, "maxItems": mx}
BUL = lambda mn, mx, n=150: arr(S(n), mn, mx)
def obj(req, props): return {"type": "object", "required": req, "additionalProperties": False, "properties": props}
NUM = {"type": "number"}
common = {
    "lang": {"enum": ["pt", "en"], "default": "pt"},
    "theme": {**S(40), "description": "style name from slidegen/themes.json (list: py -3 build.py --styles)"},
    "primary": {"type": "string", "pattern": "^#?[0-9A-Fa-f]{6}$", "description": "overrides theme primary colour; tints are derived"},
    "font": S(60), "heading_font": S(60),
    "source": {**S(320), "description": "prints as 'Fonte:'/'Source:'. Required on data slides; never invent one"},
    "page_number": {"type": ["integer", "string"]}, "footer_tag": S(40), "footer_bar": obj(["x", "w"], {"x": NUM, "w": NUM}),
    "accent_words": {"type": "array", "items": S(80), "description": "headline phrases drawn in the theme primary colour"},
    "tag": {**S(40), "description": "stamp top-right, e.g. ILUSTRATIVO / PRELIMINAR"},
    "logo": {"oneOf": [LOGO := obj(["file"], {"file": {**S(260), "description": "image path (PNG/JPG); missing file = build error. Overrides the theme token 'logo'"},
        "position": {"enum": ["footer-right", "footer-left", "top-right"], "default": "footer-right", "description": "source line and page number shift clear of it; a logo replaces the theme's text wordmark (footer_brand)"},
        "height": {"type": "number", "minimum": 0.15, "maximum": 0.9, "default": 0.3, "description": "inches; width follows the aspect ratio"}}), arr(LOGO, 1, 3)],
        "description": "one logo, or a list of up to 3 (logos with the same position sit side by side)"},
    "tracker": obj(["sections"], {"sections": BUL(2, 6, 24), "active": {"type": "integer", "minimum": 0}, "position": {"enum": ["right", "footer"], "description": "footer: right of the source line on the footer row; right: right-aligned above the footer rule (default: centred in the footer line)"}, "style": {"enum": ["boxes", "nodes"], "description": "boxes: dashed-outline rounded boxes, the active section filled in the brand colour; nodes: line with circle nodes and caps labels (replaces the footer rule); default: grey bars with labels"}, "line": {"type": "string", "description": "nodes style: line/outline hex (default 1A1A1A)"}}),
}
HEAD = {"headline": {**S(190), "description": "ACTION TITLE: full sentence stating the insight, <=2 lines at 20pt"}}
TAKE = {"takeaway": {**S(160), "description": "one-sentence so-what"}}
CHART = obj(["kind", "categories", "series"], {
    "kind": {"enum": ["column", "stacked", "stacked100", "bar", "line", "pie", "doughnut"]},
    "title": S(60), "subtitle": {**S(80), "description": "unit + period, e.g. '2024 - em R$ bi'"},
    "categories": arr({"type": "string", "maxLength": 40}, 2, 30),
    "series": arr(obj(["name", "values"], {"name": S(40), "values": arr(NUM, 2, 30)}), 1, 4),
    "number_format": {"type": "string", "description": "Excel code: '#,##0', '0.0', '0%'"},
    "highlight": {"type": "array", "items": {"type": "integer", "minimum": 0}, "maxItems": 3,
                  "description": "single series only: indexes in primary colour, rest grey"},
    "callout": {**S(24), "description": "bubble top-right of the chart, e.g. 'CAGR +9%'"},
    "percent": {"type": "boolean"}, "gridlines": {"type": "boolean"}, "value_axis": {"type": "boolean", "description": "show the value axis (grey 9pt labels); default hidden"}, "min": NUM, "max": NUM, "markers": {"type": "boolean"}, "smooth": {"type": "boolean", "description": "line charts: smooth curves instead of straight segments"}, "colors": arr(S(6), 1, 6), "labels": {"type": "boolean"}, "end_labels": {"type": "boolean", "description": "label only the first and last point"}, "axis_format": {"type": "string", "description": "tick label Excel code when value_axis is shown, e.g. '#,##0'"}, "labels_above": {"type": "boolean", "description": "waterfall: delta labels above the bars instead of inside"}, "names": {"type": "boolean", "description": "pie/doughnut: show category names in the labels"}, "legend": {"type": "boolean"}, "max_height_in": {"type": "number", "minimum": 1, "maximum": 8, "description": "cap the chart height in inches (compact columns)"}, "legend_pos": {"enum": ["top", "top_tight", "inside"], "description": "legend above the plot instead of below (top_tight: reserves only 0.10 of the frame; inside: floats over the plot bottom-right)"}})
member = obj(["name", "role"], {"name": S(40), "role": S(70), "photo": S(260)})


def arch(name, req, props, desc):
    return {"type": "object", "description": desc, "required": ["type", *req], "additionalProperties": False,
            "properties": {"type": {"const": name}, **common, **props}}


A = {}
# structure
A["cover"] = arch("cover", ["title", "team", "event"], {"title": S(90), "subtitle": S(140), "team": S(50), "members": BUL(0, 6, 40),
    "event": S(70), "date": S(30), "image": S(260)}, "Opening slide: photo/dark backdrop, title, team, event, date.")
A["team"] = arch("team", ["headline", "members"], {**HEAD, "members": arr(member, 2, 6)}, "Round photos (or initials) + name + role.")
A["agenda_divider"] = arch("agenda_divider", ["sections"], {"title": S(30), "image": S(260),
    "sections": arr(obj(["name"], {"name": S(40), "topics": BUL(0, 4, 50)}), 2, 6),
    "active": {"type": "integer", "minimum": 0, "description": "highlighted section; omit for a plain agenda"}},
    "Agenda / section divider; active section highlighted, others dimmed.")
A["key_insight"] = arch("key_insight", ["statement"], {"label": S(30), "statement": S(220), "image": S(260)},
    "Dark full-bleed punchline statement.")
A["closing"] = arch("closing", [], {"word": S(30), "subtitle": S(100), "contacts": S(200), "image": S(260)}, "Q&A / Obrigado.")
A["exhibit_annotated"] = arch("exhibit_annotated", ["headline", "notes"], {**HEAD, **TAKE, "image": S(260), "image_label": S(40),
    "notes_title": S(40), "notes": BUL(2, 5, 200)}, "User image (screenshot, map, code, mock-up) + numbered explanation.")
# text
A["executive_summary"] = arch("executive_summary", ["headline", "columns"], {**HEAD, **TAKE,
    "columns": arr(obj(["header", "bullets"], {"header": S(40), "kpi": S(16), "bullets": BUL(2, 6)}), 2, 4)},
    "2-4 columns with filled headers, optional KPI per column, dense bullets.")
A["two_column"] = arch("two_column", ["headline", "left", "right"], {**HEAD, **TAKE,
    "left": obj(["header", "bullets"], {"header": S(40), "bullets": BUL(2, 6)}),
    "right": obj(["header", "bullets"], {"header": S(40), "bullets": BUL(2, 6)})}, "Two rule-underlined columns.")
A["icon_columns"] = arch("icon_columns", ["headline", "cards"], {**HEAD, **TAKE,
    "cards": arr(obj(["header", "bullets"], {"header": S(40), "icon": S(260), "bullets": BUL(1, 5, 120)}), 3, 5),
    "active": {"type": "integer", "minimum": 0, "description": "gradual reveal: highlight one card, dim the rest"}},
    "3-5 equal cards: icon/number, header, bullets.")
A["kpi_tiles"] = arch("kpi_tiles", ["headline", "kpis"], {**HEAD, **TAKE,
    "kpis": arr(obj(["value", "label"], {"value": S(12), "label": S(60), "note": S(100), "icon": S(260)}), 3, 5), "bullets": BUL(0, 4)},
    "Big numbers in brand colour with labels.")
A["quote_interview"] = arch("quote_interview", ["headline", "person", "factors"], {"headline": {**S(200), "description": "the quote"},
    "person": member, "factors": arr(obj(["label", "detail"], {"label": S(40), "detail": S(220)}), 2, 5)},
    "Expert interview: photo, quote as title, key factors | detail.")
# charts
A["chart_takeaway"] = arch("chart_takeaway", ["headline", "chart", "insights"], {**HEAD, **TAKE, "insights_title": S(40),
    "chart": {**CHART, "required": ["kind", "title", "categories", "series"]}, "insights": BUL(2, 4, 170)},
    "Chart left + numbered insights right + takeaway bar.")
A["multi_chart"] = arch("multi_chart", ["headline", "panels"], {**HEAD, **TAKE,
    "panels": arr(obj(["claim", "chart"], {"claim": S(90), "chart": CHART, "note": S(140)}), 2, 3)},
    "2-3 chart panels, each with its own claim banner.")
A["waterfall"] = arch("waterfall", ["headline", "chart_title", "steps", "insights"], {**HEAD, **TAKE, "chart_title": S(60),
    "subtitle": S(80), "steps": arr(obj(["label", "value"], {"label": S(24), "value": NUM}), 3, 12),
    "number_format": {"type": "string"}, "callout": S(24), "total_last": {"type": "boolean", "default": True},
    "insights_title": S(40), "insights": BUL(2, 4, 170)},
    "Bridge chart: first = start total, middle = deltas (+/-), last = end total.")
A["scenarios"] = arch("scenarios", ["headline", "scenarios"], {**HEAD, **TAKE,
    "scenarios": arr(obj(["name", "value"], {"name": S(24), "value": S(16), "value_label": S(40),
        "metrics": arr(obj(["label", "value"], {"label": S(30), "value": S(16)}), 0, 6), "assumptions": BUL(0, 4, 110)}), 2, 4),
    "recommended": {"type": "integer", "minimum": 0}}, "Bear/base/bull cards, recommended one highlighted.")
# tables
A["comparison_table"] = arch("comparison_table", ["headline", "columns", "rows"], {**HEAD, **TAKE, "corner": S(30),
    "columns": arr(S(30), 2, 6), "rows": arr(obj(["label", "cells"], {"label": S(40), "cells": BUL(2, 6, 90)}), 2, 8),
    "highlight_row": {"type": "integer", "minimum": 0}},
    "Options compared; cells may be a tick, a cross, 'harvey:0-4' or short text; pick dashed-outlined.")
A["scorecard"] = arch("scorecard", ["headline", "criteria", "options"], {**HEAD, **TAKE,
    "criteria": arr(obj(["name", "weight"], {"name": S(24), "weight": {"type": "number", "exclusiveMinimum": 0}}), 2, 6),
    "options": arr(obj(["name", "scores"], {"name": S(30), "scores": arr(NUM, 2, 6)}), 2, 7),
    "max_score": {"type": "number", "default": 5}}, "Weighted scoring; totals computed by the tool, winner highlighted.")
A["data_table"] = arch("data_table", ["headline", "columns", "rows"], {**HEAD, **TAKE, "unit": S(60), "corner": S(30),
    "decimals": {"type": "integer", "minimum": 0, "maximum": 3}, "columns": arr(S(14), 2, 10),
    "rows": arr(obj(["label", "values"], {"label": S(40), "values": arr({"type": ["number", "null"]}, 2, 10),
        "style": {"enum": ["normal", "sub", "total"]}}), 2, 16)}, "Financial / numeric table, total rows emphasised.")
# diagrams
A["process_steps"] = arch("process_steps", ["headline", "steps"], {**HEAD, **TAKE, "style": {"enum": ["chevrons", "numbered"]},
    "steps": arr(obj(["title"], {"title": S(40), "description": S(160)}), 3, 6), "active": {"type": "integer", "minimum": 0}},
    "Chevrons or numbered circles; active step highlighted.")
A["timeline"] = arch("timeline", ["headline"], {**HEAD, **TAKE,
    "milestones": arr(obj(["when", "title"], {"when": S(20), "title": S(40), "description": S(120)}), 3, 8),
    "periods": arr(S(20), 2, 8),
    "bars": arr(obj(["label", "start", "end"], {"label": S(40), "start": {"type": "integer", "minimum": 0},
        "end": {"type": "integer", "minimum": 0}, "note": S(40), "level": {"type": "integer", "minimum": 0, "maximum": 3}}), 1, 10)},
    "Milestone line, or Gantt when periods + bars are given (bar start/end are period indexes).")
A["matrix_2x2"] = arch("matrix_2x2", ["headline", "x_label", "y_label", "items"], {**HEAD, **TAKE, "x_label": S(30), "y_label": S(30),
    "quadrants": arr({"type": "string", "maxLength": 30}, 4, 4), "list_title": S(30),
    "items": arr(obj(["label", "x", "y"], {"label": S(30), "description": S(110), "x": {"type": "number", "minimum": 0, "maximum": 10},
        "y": {"type": "number", "minimum": 0, "maximum": 10}, "size": {"type": "number", "minimum": 1, "maximum": 10}}), 2, 8)},
    "Prioritisation / risk matrix, numbered bubbles + numbered list.")
NODES = arr(obj(["id", "label"], {"id": S(20), "label": S(60), "parent": S(20)}), 2, 15)
A["flowchart"] = arch("flowchart", ["headline", "nodes"], {**HEAD, **TAKE, "nodes": NODES}, "Top-down org chart / hierarchy.")
A["issue_tree"] = arch("issue_tree", ["headline", "nodes"], {**HEAD, **TAKE, "nodes": NODES}, "Left-to-right logic tree.")
A["funnel"] = arch("funnel", ["headline", "stages"], {**HEAD, **TAKE,
    "stages": arr(obj(["label", "value"], {"label": S(40), "value": S(14), "criterion": S(140)}), 3, 6)}, "Filtering funnel.")
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB",
       "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
A["tile_map"] = arch("tile_map", ["headline", "values"], {**HEAD, **TAKE, "ranking_title": S(30), "unit": S(12),
    "decimals": {"type": "integer", "minimum": 0, "maximum": 2}, "top": {"type": "integer", "minimum": 3, "maximum": 8},
    "highlight": {"type": "array", "items": {"enum": UFS}},
    "values": {"type": "object", "propertyNames": {"enum": UFS}, "additionalProperties": NUM, "minProperties": 3},
    "insights": BUL(0, 3)}, "Brazil tile-grid choropleth + ranking.")

# composite: several elements joined by links (see slidegen/composite.py)
CCHART = obj(["kind", "categories", "series"], {
    **{k: v for k, v in CHART["properties"].items() if k not in ("callout", "title")},
    "kind": {"enum": ["column", "stacked", "stacked100", "bar", "line", "pie", "doughnut", "waterfall"]},
    "title": {**S(70), "description": "heading-font (serif) chart title drawn above the grey subtitle"},
    "major_unit": {"type": "number", "exclusiveMinimum": 0, "description": "value-axis tick step (default auto)"}, "axis_size": {"type": "integer", "minimum": 8, "maximum": 14, "description": "value-axis tick label size in pt when value_axis is shown (default 9)"}, "axis_color": {**S(6), "description": "value-axis tick label hex colour (default 7F7F7F)"},
    "totals": {"type": "boolean", "description": "stacked only: total label above each stack"},
    "highlight_colors": arr(S(6), 1, 3), "end_color": S(6), "bold_labels": arr({"type": "integer", "minimum": 0, "maximum": 12}, 1, 4), "connectors": {"type": "boolean", "description": "waterfall: thin dashed lines joining each bar end to the next bar"}, "total_first": {"type": "boolean", "description": "waterfall only: first value = total bar, the others (positive magnitudes) hang down from it"},
    "total_last": {"type": "boolean", "description": "waterfall only: last value is an end total (default true; ignored with total_first)"},
    "series_labels": {"enum": ["left"], "description": "stacked only: series names written left of the first stack with grey leader lines to their segments (no legend)"},
    "small_callouts": {"type": "boolean", "description": "stacked only: segment values too small for an inside label are written outside, right of the stack, with a thin leader"},
    "cat_size": {"type": "number", "minimum": 6, "maximum": 14, "description": "category-axis label size in pt (default = chart font size)"},
    "inside_labels": {"type": "array", "items": {"type": "integer", "minimum": 0}, "description": "total_first waterfall: category indices whose value label is white and centred inside the bar"},
    "inside_color": {"type": "string", "pattern": "^[0-9A-Fa-f]{6}$", "description": "colour of the inside_labels text (default FFFFFF; dark for light bars)"},
    "gap": {"type": "integer", "minimum": 0, "maximum": 300, "description": "gap width between columns in % (default 80; waterfall 50)"},
    "phases": {**arr(obj(["start", "label"], {"start": {"type": "integer", "minimum": 0, "description": "index of the first category of the phase"}, "label": S(20)}), 2, 5), "description": "column/stacked/stacked100/line/waterfall: dashed vertical divider before each phase after the first, its label (\"1\", \"2\" or text) above the span; starts increase. Do not combine with legend_pos top"},
    "callouts": {"type": "boolean", "description": "pie/doughnut: bold category name + value outside the ring with leader lines, instead of a legend and inside labels (needs a panel >= 4.5in wide; percent: true shows shares)"}})
XYPT = obj(["x", "y"], {"x": NUM, "y": NUM, "label": {**S(30), "description": "name written next to the point"}, "size": {"type": "number", "exclusiveMinimum": 0, "description": "bubble size (kind bubble: required)"}})
CSCAT = {**obj(["kind"], {
    "kind": {"enum": ["scatter", "bubble"], "description": "native XY chart; bubble = third value 'size'"},
    "title": CCHART["properties"]["title"], "subtitle": CCHART["properties"]["subtitle"],
    "points": {**arr(XYPT, 3, 40), "description": "one series of points {x, y, label?, size?}"},
    "series": {**arr(obj(["name", "points"], {"name": S(40), "points": arr(XYPT, 2, 40)}), 1, 4), "description": "alternative to 'points': several series of points"},
    "x_title": S(40), "y_title": S(40), "x_format": {"type": "string", "description": "x tick label Excel code, e.g. '0%'"}, "y_format": {"type": "string"},
    "x_min": NUM, "x_max": NUM, "y_min": NUM, "y_max": NUM, "bubble_scale": {"type": "integer", "minimum": 10, "maximum": 200, "description": "bubble size in % (default 50)"},
    "highlight": {"type": "array", "items": {"type": "integer", "minimum": 0}, "maxItems": 8, "description": "single series: point indexes in primary colour, the rest grey"},
    "quadrants": obj([], {"x": {"oneOf": [NUM, {"const": "mean"}]}, "y": {"oneOf": [NUM, {"const": "mean"}]}, "labels": {**arr(S(40), 4, 4), "description": "corner labels: top-left, top-right, bottom-left, bottom-right"}}),
    "labels": {"type": "boolean", "description": "write point labels (default true)"}, "legend": {"type": "boolean"}, "gridlines": {"type": "boolean"}, "colors": arr(S(6), 1, 6),
    "axis_size": CCHART["properties"]["axis_size"], "axis_color": CCHART["properties"]["axis_color"], "max_height_in": CCHART["properties"]["max_height_in"]}),
    "anyOf": [{"required": ["points"]}, {"required": ["series"]}]}
SCHART = {"if": {"properties": {"kind": {"enum": ["scatter", "bubble"]}}, "required": ["kind"]}, "then": CSCAT, "else": CCHART}
ICON = {**S(40), "description": "Lucide icon name (find_icons), e.g. 'rocket'"}
PILLC = {"pill": S(24), "color": {**S(20), "description": "theme key (primary, dark, accent, pale) or 6-digit hex; default primary"}}
PHEAD = {"id": {**S(20), "description": "unique panel id, referenced by links"}, "title": {**S(70), "description": "optional panel sub-header"},
         "tag": {**S(24), "description": "small rounded light-grey outlined tag at the top-left of the element, e.g. 'Fora de Escala'"}}
EXTRAS = {"title_shape": {"enum": ["pentagon", "chevron"], "description": "panel title drawn as an arrow-shaped banner (pentagon = homePlate, chevron) in the header fill / brand colour instead of the plain header (archive step headers); needs title"}, "icon_style": {"enum": ["disc", "line"], "description": "icons on cards/kpis/bullets items: disc = white line icon on a brand-colour disc (default), line = plain brand-colour line icon"},
          "pill_legend": obj(["pills"], {"label": {**S(30), "description": "bold lead-in, e.g. 'Input source:'"}, "pills": arr(obj(["pill"], PILLC), 1, 6)}),
          "callout": obj(["text"], {"lead": S(60), "text": S(260)}),
          "footnotes": {**BUL(1, 3, 160), "description": "small grey 9pt notes at the bottom of the panel"},
          "row_max": {"type": "number", "minimum": 0.2, "maximum": 1.5, "description": "table only: max row height in inches (overrides theme table_row_max)"},
          "x_inset": {"type": "number", "minimum": 0, "maximum": 3, "description": "inches the panel content starts right of its slot edge (e.g. right column clear of the divider); default 0"},
          "w": {"type": "number", "minimum": 2, "maximum": 12, "description": "table only: table width in inches (left-aligned); default full slot width"},
          "row_h": {"type": "number", "minimum": 0.15, "maximum": 1.0, "description": "table only: fixed row height in inches (compact rows); spare space centres the table in its slot"},
          "tight": {"type": "boolean", "description": "table only: compact row padding (0.07in instead of 0.12in; body cell margins 0.01in)"},
          "header_fill": {**S(6), "description": "bar-style header only: own header fill hex for this panel (white text)"}, "header_rule": {"type": "boolean", "description": "table only: false = no dark rule under a rule-style header row"},
          "align": {**arr({"enum": ["l", "c", "r"]}, 2, 10), "description": "table only: alignment per column"}, "header_align": {**arr({"enum": ["l", "c", "r"]}, 2, 10), "description": "table only: header alignment per column (default = align)"},
          "fit_bullets": {"type": "boolean", "description": "reserve bullet height at bullet_size instead of 12pt (frees chart room under smaller bullets)"}, "text_size": {"type": "number", "minimum": 8, "maximum": 14, "description": "cards panel body size in pt (default 12)"}, "table_note_italic": {"type": "boolean", "description": "table_note fully italic (default true); false + //italic// runs for partial"}, "title_font": {"enum": ["heading"], "description": "panel title in the heading font, regular weight (serif originals)"}, "title_badge": {"type": "integer", "minimum": 0, "maximum": 20, "description": "numbered circle (brand colour) left of the panel title, e.g. section 1 / 2"}, "title_plain": {"type": "boolean", "description": "chart/table/flow panel title as a plain sentence-case title even on a dotline-header theme"}, "col_weights": {"type": "array", "items": {"type": "number", "minimum": 0.05}, "minItems": 2, "maxItems": 10, "description": "table only: relative column widths (default: from text length)"}, "bullet_size": {"type": "integer", "minimum": 9, "maximum": 14, "description": "bullets panel only: font size pt (default 12)"}, "callout_fill": {"type": "string", "description": "panel callout box fill hex (default theme callout_fill, F2F2F2; FFFFFF = no visible box)"}, "note_gap": {"type": "number", "description": "table only: extra inches reserved under table_note so it clears the block below"},
          "row_pad": {"type": "boolean", "description": "table only: reserve the cell-margin overrun below a fixed-size table so what sits under it clears the last row"},
          "side_label": {"description": "vertical (270 deg) label strip at the panel's left edge: a string (whole panel height), or a list of {text, rows: [first, last] (table body rows / cards items), fill, level 0|1} for strips aligned to rows; level 1 sits right of level 0",
                         "oneOf": [S(30), arr(obj(["text"], {"text": S(30), "rows": arr({"type": "integer", "minimum": 0}, 2, 2), "fill": {**S(6), "description": "theme key or hex, 'none' = no fill; default brand (level 0) / pale (level 1)"}, "level": {"type": "integer", "minimum": 0, "maximum": 1}}), 1, 5)]},
          "side_fill": {**S(20), "description": "fill of a string side_label (theme key or hex; default brand colour)"},
          "scale": obj([], {"colors": {**arr(S(20), 2, 4), "description": "gradient stops left to right, theme keys or hex (default green, yellow, red)"}, "left": {**S(24), "description": "end label under the left end"}, "right": {**S(24), "description": "end label under the right end"},
                            "markers": arr(obj(["at"], {"at": {"type": "number", "minimum": 0, "maximum": 1}, "label": S(24)}), 1, 3), "frame": {"type": "boolean", "description": "dashed brand box round the scale"}}),
          "bullet_fill": {"type": "boolean", "description": "bullets panel: false = natural spacing instead of spreading over the slot"},
          "bullets_position": {"enum": ["top"], "description": "put the panel bullets above the element (default below)"}}
UNDER = {"bullets": {**BUL(1, 4, 170), "description": "optional ■ bullets under the element; **bold** lead-ins"}}
PGREY = {"panel": {"enum": ["grey", "none"], "description": "grey = light-grey (F2F2F2) panel behind this panel incl. its title; none overrides the theme token 'panels'"}}
def panel(kind, req, props, under=True):
    return obj(["id", "kind", *req], {**PHEAD, "kind": {"const": kind}, **PGREY, **props, **EXTRAS, **(UNDER if under else {})})
TONE = {"type": "string", "pattern": "^(#?[0-9A-Fa-f]{6}|grey|grey_dark|grey_mid|pale|primary|dark)$", "description": "hex or grey|grey_dark|grey_mid|pale|primary|dark (theme colours)"}
CELL = {"oneOf": [S(180, 0), obj(["pill"], PILLC), obj(["icon", "text"], {"icon": ICON, "text": S(180), "pos": {"enum": ["top", "left"], "description": "icon above the text (default) or left of it"}}), {**arr(S(140), 1, 5), "description": "list of short strings: bulleted lines inside the cell"}, obj(["bars"], {"bars": arr(obj(["value", "label"], {"value": {"type": "number", "minimum": 0}, "label": S(12), "series": {"type": "integer", "minimum": 0, "maximum": 3}}), 1, 3)}),
    {**obj(["text"], {"text": S(180), "fill": {**TONE, "description": "cell fill"}, "bold": {"type": "boolean"}, "box": {**TONE, "description": "dashed outline around the cell (highlight one figure)"}}), "description": "styled text cell"}]}   # text or mini-bar cell
PANELS = [
    panel("chart", ["chart"], {"chart": SCHART, "title_font": {"enum": ["heading"], "description": "chart panel title in the heading font, regular weight (serif originals)"}, "backing": {"type": "boolean", "description": "draw a light-grey context panel behind this chart (all panels with backing share one panel)"}}),
    panel("table", ["columns", "rows"], {"columns": arr(S(40), 2, 10), "rows": arr({"oneOf": [arr(CELL, 2, 10), obj(["group"], {"group": S(60)}), obj(["total"], {"total": arr(S(60, 0), 2, 10)})]}, 1, 16),
    "head_fill": {"oneOf": [TONE, arr({"oneOf": [TONE, {"type": "null"}]}, 2, 10)], "description": "column-header fill: one colour, or one per column (null = style default); text turns white on dark fills"},
    "col_fill": {**arr({"oneOf": [TONE, {"type": "null"}]}, 2, 10), "description": "body fill per column (null = none), e.g. tint the label or total column"},
    "bands": {**TONE, "description": "tint every second body row with this colour"},
    "grid": {**TONE, "description": "full cell grid (all borders) in this colour, e.g. 1A1A1A"}, "size": {"type": "integer", "minimum": 7, "maximum": 14, "description": "body font size in pt (overrides the theme table_size); use 8-9 for text-heavy grids"}, "numeral_order": {"enum": ["row", "column"], "description": "numeral_grid reading order: row (1,2 / 3,4, default) or column (1,3 / 2,4)"}, "legend_title": {**S(40), "description": "numeral_grid only: heading above the grid"}, "legend": {"oneOf": [{"enum": ["numeral_grid"]}, arr(S(20), 1, 4)], "description": "'numeral_grid': render the panel bullets as a 2x2 grid of large numerals with brand bars (item '**1** a; b; c'; max 4 items). Array of names: series legend top-right of the panel for mini-bar cells"}, "footnote": {"type": "boolean", "description": "render the panel bullets as plain footnote text (no bullet glyph)"}, "table_note": {**S(200), "description": "9pt italic note directly under the table (reserves 0.25in)"}, "matrix": {"type": "boolean", "description": "centre figure columns and grey-band group rows (rows with only a label)"}, "backing": {"type": "boolean", "description": "draw the light-grey context panel behind this table (theme backing_fill/backing_line)"}, "pill_size": {"type": "integer", "minimum": 6, "maximum": 11, "description": "table pill cells: text size in pt (default 9); the chip scales with it"}, "first_col_bold": {"type": "boolean", "description": "first_col heading cells bold"}, "header_size": {"type": "integer", "minimum": 8, "maximum": 20, "description": "table column-header font size in pt (default = body size)"}, "header_font": {"enum": ["heading"], "description": "table column headers in the heading (serif) font"}, "bar_label_size": {"type": "integer", "minimum": 8, "maximum": 16, "description": "mini-bar value label size in pt"}, "subtitle_font": {"enum": ["body", "heading"], "description": "panel subtitle font (default heading)"}, "subtitle_color": {**S(6), "description": "panel subtitle colour hex"}, "first_col": {"enum": ["heading"], "description": "first-column cells in the heading font, 15pt regular"}, "chevrons": {"type": "integer", "minimum": 1, "maximum": 5, "description": "column index: light-grey chevron in each body row just left of that column"}, "rules": {"enum": ["rows"], "description": "thin light-grey rule between body rows"}, "subtitle": {**S(60), "description": "bold heading-font title inside the panel above tag/legend"}, "subtitle_note": {**S(60), "description": "grey note under the panel subtitle"}, "legend_layout": {"enum": ["stack"], "description": "legend array: one entry per line, right-aligned (default one row)"}}),
    panel("flow", ["nodes"], {"node_size": {"type": "integer", "minimum": 7, "maximum": 14, "description": "node text size in pt (default 11); lower for 4+ leaves in a narrow column"}, "direction": {"enum": ["td", "lr"], "description": "td (default): inputs on top flowing down to the result at the bottom; lr: inputs left, result right"},
          "nodes": {**arr(obj(["id", "text"], {"id": S(20), "text": S(40), "parent": {**S(20), "description": "id of the node this one feeds (omit on the single root = the result)"},
              "style": {"enum": ["grey", "outline", "fill", "plain"], "description": "grey = input/context, outline = brand outline, fill = brand-filled result, plain = thin grey outline (default by depth)"},
              "op": {"enum": ["+", "×", "=", "−"], "description": "operator circle where this node's inputs join"}}), 2, 15), "description": "boxes joined by connectors; parent = the node a box feeds, the root is the result"}}, under=False),
    panel("bullets", ["items"], {"items": arr(S(220), 1, 6), "icons": {**arr({"type": "string", "maxLength": 40}, 1, 6), "description": "one Lucide icon name per item (\"\" = none): icon rows instead of bullets"}, "backing": {"type": "boolean", "description": "draw a light-grey context panel behind this text block (shares one panel with other flagged panels)"}}, under=False),
    panel("cards", ["items"], {"numbered": {"type": "boolean"}, "card_fill": {**S(6), "description": "card fill colour hex (default theme pale)"},
          "items": arr(obj(["title", "text"], {"title": S(40), "text": S(170), "icon": ICON}), 2, 5)}, under=False),
    panel("kpis", ["items"], {"items": arr(obj(["value", "label"], {"value": S(20), "label": S(60), "icon": ICON, "delta": {"enum": ["up", "down"], "description": "small triangle after the figure (up/down marker)"}, "delta_color": {**S(20), "description": "triangle fill: grey, grey_dark, theme key or hex; default 4D4D4D"}}), 1, 4), "backing": {"type": "boolean", "description": "draw a light-grey context panel behind these KPIs (shares one panel with other flagged panels)"}}),
    panel("map_br", ["values"], {"number_format": {"type": "string"}, "highlight": {"type": "array", "items": {"enum": UFS}},
          "values": {"type": "object", "propertyNames": {"enum": UFS}, "additionalProperties": NUM, "minProperties": 3}}),
    panel("process", ["steps"], {"steps": arr(obj(["title"], {"title": S(30), "text": S(110)}), 2, 5)}),
    panel("matrix", ["x_label", "y_label", "items"], {"x_label": S(30), "y_label": S(30), "quadrants": arr(S(30), 4, 4),
          "items": arr(obj(["label", "x", "y"], {"label": S(24), "x": {"type": "number", "minimum": 0, "maximum": 10},
          "y": {"type": "number", "minimum": 0, "maximum": 10}, "size": {"type": "number", "minimum": 1, "maximum": 10}}), 2, 8)}),
]
IDS = lambda: S(20)
CI = {"type": "integer", "minimum": 0}
TONE = {**S(20), "description": "grey (F2F2F2), grey_dark (D9D9D9), grey_mid (A6A6A6), a theme key (pale, primary, dark) or a 6-digit hex"}
EMPH = [
    obj(["kind", "panels"], {"kind": {"const": "backdrop"}, "panels": arr(IDS(), 1, 6), "y": {**arr({"type": "number", "minimum": 0, "maximum": 1}, 2, 2), "description": "vertical band [from, to] of the panels' union as fractions, e.g. [0.7, 1] for a so-what row; default whole height"}, "fill": TONE, "outline": {"enum": ["none", "dashed", "solid"], "description": "default none"}}),
    obj(["kind", "from", "to"], {"kind": {"const": "pointer"}, "from": IDS(), "to": IDS(), "shape": {"enum": ["triangle", "block"], "description": "triangle (default) or block arrow"}, "fill": TONE}),
    obj(["kind", "panel"], {"kind": {"const": "accent_bar"}, "panel": IDS(), "fill": TONE}),
]
LINKS = [
    obj(["kind", "panel", "from", "to"], {"kind": {"const": "cagr"}, "panel": IDS(), "from": CI, "to": CI, "label": S(20), "style": {"enum": ["pill", "diagonal"], "description": "pill (default) = bracket with rounded label; diagonal = one slim brand arrow, plain bold label above"}}),
    obj(["kind", "from", "to"], {"kind": {"const": "arrow"}, "from": IDS(), "to": IDS(), "anchor": {"enum": ["centre"], "description": "side-by-side panels: put the disc at the vertical centre of both panels"}}),
    obj(["kind", "from", "to"], {"kind": {"const": "bracket"}, "from": arr(IDS(), 2, 3), "to": IDS(), "label": S(20)}),
    obj(["kind", "panel", "categories"], {"kind": {"const": "highlight"}, "panel": IDS(), "categories": arr(CI, 1, 4), "label": S(24)}),
    obj(["kind", "panel", "category", "text"], {"kind": {"const": "callout"}, "panel": IDS(), "category": CI, "text": S(60)}),
    obj(["kind", "from", "category", "to", "row"], {"kind": {"const": "connector"}, "from": IDS(), "category": CI, "to": IDS(), "row": CI, "via": {"type": "number", "minimum": 0.05, "maximum": 0.95, "description": "position of the vertical leg between bar and row (default 0.5)"}}),
    obj(["kind", "panel", "text"], {"kind": {"const": "note"}, "panel": IDS(), "text": S(90), "at": {"oneOf": [{"enum": ["top-right", "top-left", "bottom-right", "bottom-left"]}, CI], "description": "corner of the panel (default top-right) or a chart category index (box above that bar, with an arrow to it)"}, "target": {**CI, "description": "corner box: also draw a thin arrow to this chart category"}, "size": {"type": "integer", "minimum": 8, "maximum": 14, "description": "text size in pt (default 9)"}, "w": {"type": "number", "minimum": 0.8, "maximum": 4, "description": "box width in inches (default: fits the text, max 2.2)"}}),
    obj(["kind", "panel", "to", "pairs"], {"kind": {"const": "xref"}, "panel": IDS(), "to": IDS(),
        "pairs": {**arr(arr(CI, 2, 2), 1, 6), "description": "[item index in panel, category index in the chart panel 'to']; badge number = item index + 1"}}),
]
A["composite"] = arch("composite", ["headline", "layout", "panels", "source"], {**HEAD, **TAKE,
    "layout": {"enum": ["1", "2col", "3col", "4col", "T|B", "L|R2", "L2|R", "2x2", "2x3", "L|R3", "T|B3", "T2|B3", "cols"],
               "description": "slots in reading order: cols=free columns, each split into rows (spec 'cols'; slots column by column, top to bottom), 1=1, 2col=2, 3col=3, 4col=4, T|B=top/bottom (2), L|R2=left full + right top/bottom (3), L2|R=left top/bottom + right full (3), 2x2=4, 2x3=2 rows x 3 cols (6, row by row), L|R3=left full + right 3 stacked (4), T|B3=top full + bottom 3 side by side (4), T2|B3=top 2 + bottom 3 (5)"},
    "cols": {**arr(obj(["w", "rows"], {"w": {"type": "number", "exclusiveMinimum": 0, "description": "column width proportion"}, "rows": {**arr({"type": "number", "exclusiveMinimum": 0}, 1, 4), "description": "height proportions of the column's slots (one number per slot)"},
        "title": S(60), "intro": {**S(260), "description": "text under the column header, above its slots"}, "intro_size": {"type": "integer", "minimum": 8, "maximum": 16, "description": "intro text pt (default 11)"},
        "span": {"type": "integer", "minimum": 2, "maximum": 3, "description": "the header (title, intro) runs across this and the next span-1 columns, which carry no header of their own"}, "title_font": {"enum": ["heading"], "description": "serif column title"}, "title_badge": {"type": "integer", "minimum": 0, "maximum": 20, "description": "numbered circle before the column title"}, "title_plain": {"type": "boolean"}, "header_fill": {"type": "string"}}), 1, 4),
        "description": "layout 'cols' only: each column has width proportion w, row proportions rows, and optionally a header title (spanning the column) with an intro text under it"},
    "band": {"type": "object", "additionalProperties": False, "required": ["h"], "properties": {"h": {"type": "number", "minimum": 0.12, "maximum": 0.6, "description": "band height as a share of the body"}, "title": {"type": "string", "maxLength": 70}, "title_badge": {"type": "integer", "minimum": 0, "maximum": 20}}, "description": "layout cols: the FIRST panel runs across the full width on top (an exhibit that needs width, or a KPI strip at h ~0.15-0.2), with its own section header; the columns fill the rest below a dashed line"},
    "section_style": {"enum": ["bar", "label", "rule", "centred_rule"], "description": "layout cols: look of the section (column) headers only, overriding the style's header (archive mix: label 36%, centred_rule 22%, bar 11%, rule 10%); bar = filled pill, label = bold brand-colour 14pt text, rule = bold text on a grey hairline, centred_rule = centred bold text on a hairline. compose picks one per slide"},
    "header_style": {"enum": ["dotline", "bar"], "description": "panel header look for this slide, overriding the theme (dotline = centred caps title on a hairline with a dot at each end; bar = filled brand-colour pill with white label)"},
    "header_fill": {"type": "string", "description": "hex fill for bar headers (with header_style bar), dark label; default brand colour"},
    "header_text": {"type": "string", "description": "hex label colour on header_fill bars (default dark 1A1A1A; white on dark fills)"},
    "header_caps": {"type": "boolean", "description": "dotline headers in capitals (default true); false keeps the typed case"},
    "header_bold": {"type": "boolean", "description": "dotline headers bold (default true)"},
    "header_italic": {"type": "boolean", "description": "panel headers italic (true) or upright (false), overriding the theme"},
    "source_label": {"type": "string", "maxLength": 20, "description": "footer label before the source, overriding 'Fonte:'/'Source:' (e.g. 'Fontes')"},
    "emphasis": {**arr({"oneOf": EMPH}, 0, 8), "description": "optional native contrast/emphasis shapes: backdrop (grey/pale box behind panels or a band of them), pointer (triangle or block arrow in the gutter between neighbours), accent_bar (thin bar left of a panel)"},
    "frame": obj(["panels"], {"panels": arr(IDS(), 1, 3), "style": {"enum": ["dashed", "solid", "none"], "description": "outline of the grey panel (default dashed A6A6A6)"}, "title_outside": {"type": "boolean", "description": "frame starts below the panel titles so the section header sits outside it"}}),
    "dividers": {"type": "boolean", "description": "horizontal dashed grey line between vertically stacked slots, also between the rows of each cols column (default: theme token 'dividers')"},
    "divider": {"type": "boolean", "description": "grey dashed vertical divider at the last column gutter (2col, L2|R)"},
    "right_weights": {**arr({"type": "number", "exclusiveMinimum": 0}, 2, 3), "description": "L|R2 (2 values) / L|R3 (3): height proportions of the right-column slots; T|B3, T2|B3 (3): width proportions of the bottom row; default equal"},
    "waterfall_label_style": {"enum": ["bold_axis"], "description": "waterfall: bold dark category labels, value labels 2pt larger, regular, dark"},
    "group_fill": {"type": ["string", "null"], "description": "table group-row fill hex, or null for none (default F2F2F2)"},
    "group_color": {"type": "string", "description": "table group-row text colour hex"},
    "accent_bold": {"type": "boolean", "description": "accent_words render bold"},
    "title_size": {"type": "integer", "minimum": 14, "maximum": 40, "description": "action-title size in pt for this slide, overriding the theme (archive covers/annexes use 28-40)"},
    "tag_style": {"enum": ["plain", "box"], "description": "tag look: plain = small grey caps kicker top-left above the title (e.g. ANEXOS, APÊNDICE); box = outlined stamp top-right (default unless the theme says plain)"},
    "source_font": {"type": "string", "description": "footer source-line font, overriding the theme"},
    "table_header": {"type": "string", "enum": ["plain", "rule", "fill"], "description": "table header style, overriding the theme"},
    "subtitle_italic": {"type": "boolean", "description": "chart subtitle italic (true) or upright (false), overriding the theme"},
    "title_rule": {"type": "boolean", "description": "rule under the action title, overriding the theme"},
    "panel_title_bold": {"type": "boolean", "description": "serif (title_font heading) chart titles bold, overriding the theme"},
    "serif_title_rule": {"type": "boolean", "description": "hairline under serif (title_font heading) chart titles"},
    "page_number_font": {"enum": ["heading", "body"], "description": "page number typeface (default body)"}, "page_number_size": {"type": "integer", "minimum": 8, "maximum": 32}, "page_number_bold": {"type": "boolean"},
    "chart_font": {"type": "integer", "minimum": 7, "maximum": 14, "description": "text size (pt) of all chart labels/axes on this slide, overriding the theme (dense originals: 8-10)"},
    "title_bold": {"type": "boolean", "description": "action title bold (true) or regular (false), overriding the theme"},
    "source_italic": {"type": "boolean", "description": "footer source line italic or upright, overriding the theme"},
    "corners": {"enum": ["square", "rounded"], "description": "box corners for this slide (callouts, highlight boxes), overriding the theme"},
    "weights": {**arr({"type": "number", "exclusiveMinimum": 0}, 2, 4), "description": "column proportions (row proportions for T|B, T|B3, T2|B3); default equal"},
    "panels": {**arr({"oneOf": PANELS}, 1, 6), "description": "fill the layout slots in reading order; count must equal the slots"},
    "links": {**arr({"oneOf": LINKS}, 0, 10), "description": "arrow (chevron between panels), bracket (merge panels -> one), highlight/callout (annotate chart categories), xref (numbered badges tying items to chart categories), connector (elbow arrow from a chart bar to a table row), note (dotted callout box)"}},
    "Dense multi-element slide: 1-6 panels (chart/table/bullets/cards/kpis/map_br/process/matrix/flow) joined by arrows, brackets, highlight boxes, callouts and numbered cross-references.")

schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "slidegen spec", "oneOf": list(A.values())}
pathlib.Path("schemas/archetypes.schema.json").write_text(json.dumps(schema, indent=1, ensure_ascii=False), encoding="utf8")
print(len(A), "archetypes")
