"""End-to-end MCP check: start mcp_server.py over stdio like Claude Desktop does, list tools, build a slide.
Run: py -3 -I tools/test_mcp.py"""
import asyncio, json, sys, pathlib
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
root = pathlib.Path(__file__).resolve().parent.parent

async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(root / "mcp_server.py")])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = [t.name for t in (await s.list_tools()).tools]; print("tools:", tools)
        assert {"build_slide", "list_archetypes", "get_archetype", "list_styles", "find_icons", "suggest_composition", "find_similar", "rank_candidates", "save_exemplar", "slide_grammar"} <= set(tools)
        gr = (await s.call_tool("slide_grammar", {})).content[0].text; assert "Sections and widths" in gr and "120" in gr, gr[:200]
        spec = json.loads((root / "examples" / "catalog.json").read_text("utf8"))["kpi_tiles"]
        res = await s.call_tool("build_slide", {"spec": spec, "name": "mcp_test", "style": "lek_green"})
        kinds = [c.type for c in res.content]; print("build_slide ->", kinds, res.content[0].text)
        assert kinds == ["text", "image"], kinds
        bad = await s.call_tool("build_slide", {"spec": {"type": "kpi_tiles", "headline": "x", "kpis": []}, "preview": False})
        assert "Spec invalid" in bad.content[0].text; print("invalid spec ->", bad.content[0].text.splitlines()[1][:90])
        prof = json.loads((root / "examples" / "profiles" / "orbital.json").read_text("utf8"))
        sc = json.loads((await s.call_tool("suggest_composition", {"profile": prof})).content[0].text)
        assert sc["options"][0]["layout"] == "L|R2" and sc["density"] == "ok", sc["options"][0]["layout"]; print("suggest_composition ->", sc["options"][0]["layout"])
        print((await s.call_tool("find_icons", {"query": "dollar"})).content[0].text[:80])
asyncio.run(main())
