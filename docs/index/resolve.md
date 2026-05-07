---
room: resolve
source_paths: [fetch_mcp/_resolve.py]
architectural_health: normal
security_tier: normal
see_also: [server.md]
hot_paths: [_resolve_json_input]
---

# fetch_mcp/_resolve.py

DOES: Normalizes the `data` argument for `optimize_json` into a raw JSON string. Handles four input formats: raw JSON string, direct file path starting with `/`, `{"file": "/path"}` JSON wrapper, and `{"result": "..."}` single-key wrapper (the last two arise when Claude's MCP tool response overflows to a temp file).
SYMBOLS:
- _resolve_json_input(data: str) -> str
- _try_read_file(path: str) -> str
DEPENDS: (stdlib only)
PATTERNS: (none)
USE WHEN: Adding a new input format for `optimize_json`; debugging why a file path isn't being read; understanding how MCP tool overflow files are handled.
