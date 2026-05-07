---
room: server
source_paths: [server.py, main.py]
architectural_health: normal
security_tier: normal
see_also: [benchmark.md, tests.md, evals.md]
hot_paths: [smart_fetch, optimize_json, _prune_json, _build_schema_summary]
---

# server.py

DOES: FastMCP server and CLI for the fetch-mcp tool. Registers all five MCP tools (`smart_fetch`, `browser_fetch`, `web_search`, `css_query`, `optimize_json`), implements the full JSON pruning pipeline, schema-first mode, HTML→Markdown conversion, savings logging, and CLI dispatch.
SYMBOLS:
- smart_fetch(url: str, jsonpath: str | None, max_depth: int, extract_metadata: bool, max_chars: int) -> str
- browser_fetch(url: str, selector: str | None, wait_ms: int, timeout_ms: int, headed: bool, extract_metadata: bool, max_chars: int) -> str
- web_search(query: str, max_results: int, region: str) -> str
- css_query(url: str, selector: str, max_chars: int) -> str
- optimize_json(data: str, jsonpath: str | None, max_depth: int, max_chars: int) -> str
- _prune_json(data: object, jsonpath: str | None, max_depth: int) -> object
- _clean(obj: object, current_depth: int, max_depth: int) -> object
- _dedup_array(items: list) -> list
- _flatten_dict(d: dict, prefix: str) -> dict
- _build_schema_summary(data: list[dict], max_depth: int) -> dict
- _should_use_schema_mode(data: object) -> bool
- _html_to_markdown(html: str, max_chars: int, extract_metadata: bool) -> str
- _build_client() -> httpx.AsyncClient
- _fetch_raw(url: str) -> httpx.Response
- _find_chrome_executable() -> str | None
- _log_savings(raw_chars: int, opt_chars: int, source: str) -> None
- _print_savings_report() -> None
- _resolve_json_input(data: str) -> str
- _try_read_file(path: str) -> str
- _is_api_url_template(v: str) -> bool
- _is_empty(v: object) -> bool
- _is_json_content(response) -> bool
- _infer_type(v: object) -> str
- _handle_error(e: Exception) -> str
- _cli_optimize() -> None
- _cli_smart_fetch() -> None
- _cli_browser_fetch() -> None
- _print_cli_help() -> None
- main() -> None
- Types: FastMCP instance (mcp)
DEPENDS: mcp.server.fastmcp, jsonpath_ng.ext, pydantic, httpx, truststore, html_to_markdown, bs4, playwright, ddgs
PATTERNS: schema-first, lazy-import, json-pruning-pipeline, savings-logging, cli-dispatch
USE WHEN: Adding, modifying, or debugging any MCP tool; changing JSON pruning or schema-first logic; editing CLI behavior; working on the savings logger.

---

# main.py

DOES: Stub entry point that prints a hello message. Not used by the MCP server or CLI; the real entry point is `server:main` registered in `pyproject.toml`.
SYMBOLS:
- main() -> None
TYPE: (no types)
DEPENDS: (none)
PATTERNS: (none)
USE WHEN: Inspecting the package entry point wiring — see `pyproject.toml` `[project.scripts]` instead.
