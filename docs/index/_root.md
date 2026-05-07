# LOI Index

Generated: 2026-05-06
Source paths: fetch_mcp/, server.py (shim), scripts/benchmark.py, evals/run_evals.py, tests/test_json_optimizer.py

## TASK → LOAD

| Task | Load |
|------|------|
| Add, modify, or debug any MCP tool (smart_fetch, browser_fetch, web_search, css_query, optimize_json) | server.md |
| Change JSON pruning logic (null removal, dedup, URL template stripping, flattening) | json_optimizer.md |
| Modify schema-first mode or change the array threshold | json_optimizer.md |
| Edit HTML→Markdown conversion | html.md |
| Work on browser fetch (Playwright, Chrome detection) | http.md |
| Change HTTP client, SSL setup, or Chrome path detection | http.md |
| Add or change CLI subcommands (optimize, smart_fetch, browser_fetch, report) | cli.md |
| Work on the savings logger or report command | savings.md |
| Debug how optimize_json handles file paths or JSON wrappers | resolve.md |
| Reproduce or update README token savings numbers | benchmark.md |
| Add offline JSON fixtures to verify pruning without network | evals.md |
| Write or extend unit tests for the pruning pipeline | tests.md |

## PATTERN → LOAD

| Pattern | Load |
|---------|------|
| schema-first (large arrays → schema + 2 samples) | json_optimizer.md |
| json-pruning-pipeline (URL template stripping, null removal, dedup, flattening) | json_optimizer.md |
| lazy-import (defer httpx/playwright/ddgs import for fast CLI startup) | cli.md |
| savings-logging (append JSONL per call, print cumulative report) | savings.md |
| cli-dispatch (sys.argv[1] routing to subcommand functions) | cli.md |
| fixture-driven-eval (static JSON files, no network) | evals.md |
| parametrized-pytest (pytest.mark.parametrize for edge cases) | tests.md |

## GOVERNANCE WATCHLIST

No rooms flagged.

## Rooms

| Room | Source paths | Files |
|------|-------------|-------|
| server.md | fetch_mcp/server.py, server.py (shim) | 2 |
| cli.md | fetch_mcp/cli.py | 1 |
| json_optimizer.md | fetch_mcp/json_optimizer.py | 1 |
| html.md | fetch_mcp/html.py | 1 |
| http.md | fetch_mcp/http.py | 1 |
| savings.md | fetch_mcp/savings.py | 1 |
| resolve.md | fetch_mcp/_resolve.py | 1 |
| benchmark.md | scripts/benchmark.py | 1 |
| evals.md | evals/run_evals.py | 1 |
| tests.md | tests/test_json_optimizer.py | 1 |
