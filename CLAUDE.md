# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`fetch-mcp` is a FastMCP server that acts as a high-efficiency networking layer for LLMs. It reduces token consumption by 58–87% by cleaning HTML and JSON before it reaches the context window. The server exposes five tools: `smart_fetch`, `browser_fetch`, `web_search`, `css_query`, and `optimize_json`.

The entire server lives in a single file: `server.py`. There is no framework beyond FastMCP — all tools, utilities, and CLI entry points are in that one file.

## Commands

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_json_optimizer.py::test_prune_removes_null_and_empty

# Start the MCP server (stdio mode)
uv run python server.py

# CLI — fetch a URL
uv run python server.py smart_fetch https://example.com
uv run python server.py smart_fetch https://api.github.com/orgs/python/repos --jsonpath '$[*].name'

# CLI — browser fetch (Playwright)
uv run python server.py browser_fetch https://example.com

# CLI — optimize JSON from stdin
curl -s https://api.github.com/orgs/python/repos | uv run python server.py optimize

# View savings report
uv run python server.py report

# Run benchmark (requires tiktoken, hits real URLs)
uv run python benchmark.py

# Inspect MCP server in browser (dev)
uv run mcp dev server.py
```

## Architecture

### `server.py` — the entire server

All logic lives here. Key sections:

- **Shared utilities** (`_build_client`, `_html_to_markdown`, `_find_chrome_executable`) — HTTP client setup, HTML→Markdown conversion via `html-to-markdown` (Rust-based).
- **JSON pruning pipeline** (`_prune_json`, `_clean`, `_dedup_array`, `_flatten_dict`) — strips URL templates, removes nulls/empties, deduplicates repeated sub-objects across arrays, and flattens deep nesting to dot-notation keys.
- **Schema-first mode** (`_should_use_schema_mode`, `_build_schema_summary`) — for arrays of 5+ uniform dicts, returns `_schema` + 2 `_sample` items instead of all data. The agent then calls with `jsonpath` to drill in. Threshold: `_SCHEMA_THRESHOLD = 5`.
- **Savings logger** (`_log_savings`, `_print_savings_report`) — every tool call appends before/after char counts to `~/.local/share/fetch-mcp/savings.jsonl`. Override path with `REQUEST_MCP_SAVINGS_LOG`.
- **MCP tools** (`smart_fetch`, `browser_fetch`, `web_search`, `css_query`, `optimize_json`) — registered with `@mcp.tool()` using Pydantic `Field` annotations for parameter descriptions.
- **CLI entry points** (`_cli_optimize`, `_cli_smart_fetch`, `_cli_browser_fetch`) — `main()` dispatches based on `sys.argv[1]`; no subcommand → `mcp.run()` for stdio server mode.

### `optimize_json` input resolution

`_resolve_json_input` handles four input formats: raw JSON string, direct file path, `{"file": "/path"}` JSON wrapper, and `{"result": "..."}` JSON wrapper. This handles the case where Claude's tool response overflow is saved to a temp file.

### `browser_fetch` Chrome detection

`_find_chrome_executable` walks a priority list of OS-specific paths before falling back to Playwright's bundled Chromium. Override with `REQUEST_MCP_CHROME_PATH`.

### SSL

`_get_ssl_ctx()` lazily initializes a `truststore.SSLContext` to use the system certificate store — fixes macOS SSL errors with Homebrew Python. `httpx` imports are deferred so `python server.py optimize` (JSON-only CLI path) doesn't require the full dependency set.

## Testing

Tests are in `tests/test_json_optimizer.py` and cover `_prune_json`, `_should_use_schema_mode`, `_build_schema_summary`, and JSONPath extraction. `benchmark.py` is a manual benchmark only (hits real URLs, requires `tiktoken`).

The `evals/` directory contains eval harness (`run_evals.py`) and fixtures for end-to-end eval runs — not part of the pytest suite.

## Skill Installation

`install.sh` downloads the repo archive and installs `SKILL.md` into `~/.claude/skills/fetch-mcp/`. Override with `REQUEST_MCP_REF` (branch/tag), `REQUEST_MCP_REPO_URL`, or `CLAUDE_SKILLS_DIR`.
