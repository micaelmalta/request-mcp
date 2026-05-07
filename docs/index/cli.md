---
room: cli
source_paths: [fetch_mcp/cli.py]
architectural_health: normal
security_tier: normal
see_also: [server.md, json_optimizer.md, savings.md]
hot_paths: [main, _cli_optimize]
---

# fetch_mcp/cli.py

DOES: CLI entry point and dispatch. `main()` routes `sys.argv[1]` to the appropriate subcommand handler or starts the MCP stdio server. All heavy imports (httpx, playwright, MCP server) are deferred inside subcommand functions so the `optimize` path stays lightweight.
SYMBOLS:
- main() -> None
- _cli_optimize() -> None
- _cli_smart_fetch() -> None
- _cli_browser_fetch() -> None
- _print_cli_help() -> None
DEPENDS: fetch_mcp.json_optimizer, fetch_mcp.savings, fetch_mcp.http, fetch_mcp.server
PATTERNS: cli-dispatch, lazy-import
USE WHEN: Adding CLI subcommands; changing the `optimize` stdin pipeline; modifying help text; debugging why a CLI flag isn't working.
