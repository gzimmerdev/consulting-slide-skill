"""Check the Claude Desktop setup: slidegen in claude_desktop_config.json, server process newer than the last server/compose change, tools + prompt listed."""
import json, os, subprocess, sys, asyncio, pathlib
root = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root)); ok = True
cfg = json.loads((pathlib.Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json").read_text("utf8"))
e = cfg.get("mcpServers", {}).get("slidegen"); good = bool(e) and pathlib.Path(e["command"]).exists() and pathlib.Path(e["args"][0]).resolve() == root / "mcp_server.py"
print("config entry slidegen:", "ok" if good else f"MISSING/WRONG {e}"); ok &= good
ps = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -like '*mcp_server.py*' } | % { $_.CreationDate.ToString('s') }"], capture_output=True, text=True).stdout.split()
last = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cI", "--", "mcp_server.py", "tools/compose.py", "slidegen"], capture_output=True, text=True).stdout.strip()[:19]
fresh = bool(ps) and min(ps) >= last
print("server process started:", ps or "NOT RUNNING (open Claude Desktop)", "| last code change:", last, "->", "ok" if fresh else "RESTART Claude Desktop (tray icon -> Quit)"); ok &= fresh
import mcp_server as m
tools = {t.name for t in asyncio.run(m.mcp.list_tools())}; prompts = {p.name for p in asyncio.run(m.mcp.list_prompts())}
need = {"suggest_composition", "slide_grammar", "build_slide", "rank_candidates", "save_exemplar"}
print("tools:", len(tools), "ok" if need <= tools else f"MISSING {need - tools}", "| prompt slide:", "ok" if "slide" in prompts else "MISSING"); ok &= need <= tools and "slide" in prompts
z = root / "desktop" / "slide.zip"; print("desktop skill zip:", z if z.exists() else "not built")
sys.exit(0 if ok else 1)
