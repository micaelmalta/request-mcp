---
room: server
source_paths: [fetch_mcp/server.py, server.py]
architectural_health: normal
security_tier: normal
see_also: [cli.md, json_optimizer.md, html.md, http.md, savings.md, resolve.md]
hot_paths: [smart_fetch, optimize_json, browser_fetch]
---

# fetch_mcp/server.py

DOES: Registers all five MCP tools on the FastMCP instance (`mcp`). Each tool delegates to helpers in the other `fetch_mcp` modules — this file contains only tool signatures, docstrings, and the glue between them.
SYMBOLS:
- smart_fetch(url: str, jsonpath: str | None, max_depth: int, extract_metadata: bool, max_chars: int) -> str
- browser_fetch(url: str, selector: str | None, wait_ms: int, timeout_ms: int, headed: bool, extract_metadata: bool, max_chars: int) -> str
- web_search(query: str, max_results: int, region: str) -> str
- css_query(url: str, selector: str, max_chars: int) -> str
- optimize_json(data: str, jsonpath: str | None, max_depth: int, max_chars: int) -> str
- mcp (FastMCP instance)
DEPENDS: fetch_mcp.html, fetch_mcp.http, fetch_mcp.json_optimizer, fetch_mcp._resolve, fetch_mcp.savings
PATTERNS: mcp-tool-registration
USE WHEN: Adding or modifying any MCP tool signature, description, or annotation; changing what a tool does end-to-end.

---

# server.py

DOES: Thin root-level shim — imports `main` from `fetch_mcp.cli` and calls it. Exists only to preserve `python server.py <cmd>` backward compatibility.
SYMBOLS:
- (imports only)
DEPENDS: fetch_mcp.cli
PATTERNS: (none)
USE WHEN: Never edit directly. If `python server.py` behavior needs to change, edit `fetch_mcp/cli.py`.
