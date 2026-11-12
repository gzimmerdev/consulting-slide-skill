"""Print the Claude Desktop config block for this copy of the project (your Python + your folder), and where the config file is.
usage: py -3 tools/desktop_config.py"""
import json, os, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
block = {"slidegen": {"command": sys.executable, "args": [str(root / "mcp_server.py")]}}
cfg = Path(os.environ.get("APPDATA", "")) / "Claude" / "claude_desktop_config.json" if sys.platform == "win32" \
    else Path.home() / "Library/Application Support/Claude/claude_desktop_config.json"
print(f"Claude Desktop -> Settings -> Developer -> Edit Config opens:\n  {cfg}\n")
print('Put this inside "mcpServers": { ... } (add a comma if other servers are already there):\n')
print(json.dumps(block, indent=2)[1:-1].strip())
print('\nIf the file is empty, the whole file is:\n')
print(json.dumps({"mcpServers": block}, indent=2))
