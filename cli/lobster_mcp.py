"""
Lobster MCP 入口 (供 pip entry_point / Claude Desktop 使用)
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root / "python"))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from mcp.server import main

if __name__ == "__main__":
    main()
