---
room: savings
source_paths: [fetch_mcp/savings.py]
architectural_health: normal
security_tier: normal
see_also: [server.md, cli.md]
hot_paths: [_log_savings, _print_savings_report]
---

# fetch_mcp/savings.py

DOES: Appends before/after char counts to a JSONL log file after every tool call, and prints a per-source savings report. Log path defaults to `~/.local/share/fetch-mcp/savings.jsonl`; override with `REQUEST_MCP_SAVINGS_LOG`.
SYMBOLS:
- _log_savings(raw_chars: int, opt_chars: int, source: str) -> None
- _print_savings_report() -> None
- _SAVINGS_LOG (Path)
DEPENDS: (stdlib only)
PATTERNS: savings-logging
USE WHEN: Changing the log format; adding new savings sources; debugging why the `report` command shows unexpected numbers.
