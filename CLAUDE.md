# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

`fetch-mcp` is a FastMCP server that acts as a high-efficiency networking layer for LLMs. It reduces token consumption by 58–87% by cleaning HTML and JSON before it reaches the context window. The server exposes six tools: `smart_fetch`, `browser_fetch`, `web_search`, `css_query`, `pdf_fetch`, and `optimize_json`.

## Commands

```bash
# Install dependencies
uv sync --group dev

# Run tests
uv run python -m pytest tests/ -v

# Run a single test
uv run python -m pytest tests/test_json_optimizer.py::test_prune_removes_null_and_empty

# Lint and format
uv run ruff check .
uv run ruff format .

# Start the MCP server (stdio mode)
uv run fetch-mcp
# or via shim:
uv run python server.py

# CLI — fetch a URL
uv run fetch-mcp smart_fetch https://example.com
uv run fetch-mcp smart_fetch https://api.github.com/orgs/python/repos --jsonpath '$[*].name'

# CLI — browser fetch (Playwright)
uv run fetch-mcp browser_fetch https://example.com

# CLI — optimize JSON from stdin
curl -s https://api.github.com/orgs/python/repos | uv run fetch-mcp optimize

# View savings report
uv run fetch-mcp report

# Run benchmark (requires tiktoken, hits real URLs)
uv run python scripts/benchmark.py

# Inspect MCP server in browser (dev)
uv run mcp dev fetch_mcp/server.py
```

## Architecture

### Package layout

```
fetch_mcp/
├── __init__.py        # re-exports main() for the entry point
├── server.py          # FastMCP instance (mcp) + all six @mcp.tool() registrations
├── cli.py             # CLI dispatch: main(), _cli_optimize/smart_fetch/browser_fetch/pdf_fetch
├── cache.py           # _Cache, _CacheEntry, _response_cache — in-process TTL cache
├── json_optimizer.py  # _prune_json pipeline, schema-first mode (_build_schema_summary)
├── html.py            # _html_to_markdown (wraps html-to-markdown Rust lib)
├── http.py            # _build_client, _fetch_raw (extra_headers), _find_chrome_executable
├── pdf.py             # _extract_pdf_text (pdfminer.six, page range, scanned-PDF warning)
├── savings.py         # _log_savings, _print_savings_report (JSONL at ~/.local/share/fetch-mcp/)
└── _resolve.py        # _resolve_json_input (handles file paths and JSON wrappers)

server.py              # thin shim: imports main() from fetch_mcp.cli
scripts/benchmark.py   # dev-only token benchmark (not in pytest suite)
```

### JSON pruning pipeline (`fetch_mcp/json_optimizer.py`)

`_prune_json` runs five steps in order: JSONPath extraction → URL template stripping → null/empty removal → sub-object deduplication (`_dedup_array`) → deep nesting flattening (`_flatten_dict`). Schema-first mode (`_should_use_schema_mode`) triggers for arrays of 5+ uniform dicts, returning `_schema` + 2 `_sample` items instead of all data. Threshold: `_SCHEMA_THRESHOLD = 5`.

### `optimize_json` input resolution (`fetch_mcp/_resolve.py`)

`_resolve_json_input` handles four formats: raw JSON string, direct file path, `{"file": "/path"}` wrapper, and `{"result": "..."}` wrapper — to handle Claude's tool response overflow files.

### SSL and lazy imports (`fetch_mcp/http.py`)

`_get_ssl_ctx()` lazily initializes a `truststore.SSLContext` (system cert store — fixes macOS SSL errors). `httpx`, `playwright`, `ddgs`, and `html_to_markdown` imports are deferred in `cli.py` so the `optimize` subcommand doesn't load the full networking stack.

### In-process cache (`fetch_mcp/cache.py`)

`_Cache` stores processed responses keyed by SHA-256(url + sorted headers + all output-affecting params). TTL-based lazy eviction; FIFO eviction if the store hits `_MAX_SIZE` (200) without enough expired entries. Module-level singleton `_response_cache` is shared by `smart_fetch` and `css_query`. Both tools expose `use_cache=True` and `ttl=1800` parameters.

### Auth headers (`fetch_mcp/http.py` + `fetch_mcp/server.py`)

`_fetch_raw` accepts `extra_headers: dict[str, str] | None`, merged per-request into the httpx client. `smart_fetch`, `browser_fetch`, and `pdf_fetch` all expose a `headers` parameter that threads through. For `browser_fetch`, headers are applied via `page.set_extra_http_headers`.

### PDF extraction (`fetch_mcp/pdf.py`)

`_extract_pdf_text(data, max_chars, pages)` uses `pdfminer.six` (required dep). Handles page ranges (`"1-5"`, `"3"`), returns a warning for scanned PDFs (no text layer), and page-counts lazily — only if extraction produces no text.

### Chrome detection (`fetch_mcp/http.py`)

`_find_chrome_executable` walks a priority list of OS-specific paths. Override with `REQUEST_MCP_CHROME_PATH`.

## Testing

Tests are in `tests/test_json_optimizer.py`. Run with `uv run python -m pytest` (not `uv run pytest` — the latter can resolve to the wrong binary on some systems).

`scripts/benchmark.py` is a manual benchmark that hits real URLs; `evals/run_evals.py` runs against static fixtures in `evals/fixtures/json/`. Neither is part of the pytest suite.

## Skill Installation

`install.sh` downloads the repo archive and installs `SKILL.md` into `~/.claude/skills/fetch-mcp/`. Override with `REQUEST_MCP_REF` (branch/tag), `REQUEST_MCP_REPO_URL`, or `CLAUDE_SKILLS_DIR`.
