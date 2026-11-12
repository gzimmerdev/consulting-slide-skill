# Using the slide tool from Claude Desktop

`mcp_server.py` is an MCP server ("slidegen"). Claude Desktop starts it on your machine and gets 13 tools:
`suggest_composition`, `slide_grammar`, `find_similar`, `rank_candidates`, `save_exemplar`, `list_archetypes`,
`get_archetype`, `list_styles`, `find_icons`, `build_slide` (validates, builds the .pptx and, on Windows with PowerPoint,
renders it and shows Claude the image), `open_in_powerpoint`, `extract_style` (style from any .pptx/.pdf), `add_style`;
plus one prompt, `slide`. It runs on your Claude plan; no API key.

## Setup
1. Install the Python packages: `py -3 -m pip install -r requirements.txt` (macOS: `python3 -m pip ...`).
2. Print your config block: `py -3 tools/desktop_config.py`. It shows the config file path and the `"slidegen"` entry with
   your Python and your copy of the project.
3. Claude Desktop -> Settings -> Developer -> **Edit Config**, paste the entry inside `"mcpServers": { ... }`, save.
4. Quit Claude Desktop completely (tray / menu bar icon -> Quit) and open it again. The slidegen tools appear under the
   tools icon of a new chat.
5. Optional, so that typing `/slide` works in Desktop: Settings -> Capabilities -> Skills -> upload `desktop/slide.zip`.
   It only routes the request to the slidegen tools. (After editing `desktop/slide/SKILL.md`, rebuild the zip:
   `Compress-Archive -Path desktop\slide -DestinationPath desktop\slide.zip -Force`.)

Built slides land in `out/mcp/<name>.pptx`; ask Claude to open one in PowerPoint.

Without the Desktop skill, start the message with "Usando o slidegen, ..." (or "Using slidegen, ..."): Desktop otherwise
may pick its own built-in slides skill.

## Check it
- `py -3 -I tools/test_mcp.py` starts the server exactly like Claude Desktop does, lists the tools and builds a slide.
- `py -3 -I tools/check_desktop.py` (Windows) checks the config entry, that the running server is newer than the code,
  and that the tools are listed.

## Claude Code
Claude Code also runs on your subscription: open this folder and type `/slide` followed by your request
(`.claude/skills/slide/SKILL.md`).
