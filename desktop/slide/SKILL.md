---
name: slide
description: Make ONE finished, editable consulting slide (PowerPoint) from the user's data, text or research, in Portuguese or English, with the local slidegen tools. Use when the user types /slide or asks for a slide ("gera um slide", "make a slide", KPI slide, chart slide).
---

# slide (Claude Desktop)

The slide is built on the user's PC by the **slidegen** MCP connector, not in this sandbox. Do NOT write python-pptx code, do NOT use a pptx or slides skill, do NOT make an HTML/Express design.

1. Check that the slidegen tools are available (`suggest_composition`, `build_slide`, `slide_grammar`). If they are not, stop and tell the user: "o conector slidegen não está ativo: Settings → Developer → slidegen, depois feche o Claude Desktop pelo ícone da bandeja e abra de novo".
2. Follow the slidegen server instructions step by step: content profile -> `slide_grammar` -> `suggest_composition` -> fill the top option's skeleton (replace every TODO) -> `build_slide` -> look at the returned image -> fix -> `rank_candidates` for variants.
3. Own design: when the user gives colours, fonts or a logo, or sends their slides (.pptx/.pdf/screenshots) to copy the look, follow "Own design" in the slidegen server instructions (`extract_style` / `add_style`, then a sample `build_slide` to compare).
4. Reply with the .pptx path (in `out/mcp/`), the image and your assumptions. Offer `open_in_powerpoint`. When the user approves, call `save_exemplar`.
