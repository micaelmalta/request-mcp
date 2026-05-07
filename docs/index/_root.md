# LOI Index

Generated: 2026-05-06
Source paths: server.py, main.py, benchmark.py, evals/run_evals.py, tests/test_json_optimizer.py

## TASK → LOAD

| Task | Load |
|------|------|
| Add, modify, or debug any MCP tool (smart_fetch, browser_fetch, web_search, css_query, optimize_json) | server.md |
| Change JSON pruning logic (null removal, dedup, URL template stripping, flattening) | server.md |
| Modify schema-first mode or change the array threshold | server.md |
| Edit HTML→Markdown conversion or browser fetch (Playwright) | server.md |
| Add or change CLI subcommands (optimize, smart_fetch, browser_fetch, report) | server.md |
| Work on the savings logger or report command | server.md |
| Debug SSL or Chrome executable detection | server.md |
| Reproduce or update README token savings numbers | benchmark.md |
| Verify pruning pipeline doesn't regress on real URLs | benchmark.md |
| Add offline JSON fixtures to verify pruning without network | evals.md |
| Check savings regressions against static payloads | evals.md |
| Write or extend unit tests for the pruning pipeline | tests.md |
| Add JSONPath extraction test cases | tests.md |

## PATTERN → LOAD

| Pattern | Load |
|---------|------|
| schema-first (large arrays → schema + 2 samples) | server.md |
| json-pruning-pipeline (URL template stripping, null removal, dedup, flattening) | server.md |
| lazy-import (defer httpx/playwright/ddgs import for fast CLI startup) | server.md |
| savings-logging (append JSONL per call, print cumulative report) | server.md |
| cli-dispatch (sys.argv[1] routing to subcommand functions) | server.md |
| fixture-driven-eval (static JSON files, no network) | evals.md |
| parametrized-pytest (pytest.mark.parametrize for edge cases) | tests.md |

## GOVERNANCE WATCHLIST

No rooms flagged.

## Rooms

| Room | Source paths | Files |
|------|-------------|-------|
| server.md | server.py, main.py | 2 |
| benchmark.md | benchmark.py | 1 |
| evals.md | evals/run_evals.py | 1 |
| tests.md | tests/test_json_optimizer.py | 1 |
