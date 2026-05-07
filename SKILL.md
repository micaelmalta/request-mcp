---
name: fetch-mcp
description: Use and maintain the fetch-mcp networking server. Applies when fetching URLs, optimizing JSON, using smart_fetch, browser_fetch, web_search, css_query, CLI commands, MCP tools, Playwright rendering, or handling HTTP-client-blocked pages and CAPTCHA.
---

# Fetch MCP

## When To Use

Use this skill when the user wants to fetch web pages, search the web, reduce JSON/token size, debug fetch-mcp behavior, or choose between `smart_fetch`, `browser_fetch`, `css_query`, `web_search`, and `optimize_json`.

## Command Choices

Use `smart_fetch` first for normal URLs:

```bash
uv run fetch-mcp smart_fetch https://example.com
uv run fetch-mcp smart_fetch https://api.github.com/orgs/python/repos --jsonpath '$[*].name'
```

Use `browser_fetch` when a page needs JavaScript rendering or blocks simple HTTP clients:

```bash
uv run fetch-mcp browser_fetch https://example.com
uv run fetch-mcp browser_fetch https://example.com --selector main
```

Use headed browser mode only for human-in-the-loop login or CAPTCHA:

```bash
uv run fetch-mcp browser_fetch https://example.com --headed --wait-ms 30000
```

Use `optimize` for JSON already available on stdin:

```bash
curl -s https://api.github.com/orgs/python/repos | uv run fetch-mcp optimize
cat response.json | uv run fetch-mcp optimize --jsonpath '$[*].name'
```

Use `report` to inspect cumulative savings:

```bash
uv run fetch-mcp report
```

## Safety And Site Access

Do not bypass CAPTCHA, login walls, paywalls, robots restrictions, or anti-bot systems with stealth headers, proxy rotation, CAPTCHA solvers, or fingerprint evasion.

If `smart_fetch` returns `403` or anti-bot content, switch to `browser_fetch` only to render the page like a normal browser. If a CAPTCHA or login appears, use `--headed` and require the human to complete it manually before extraction.

## Implementation Notes

The server is split across `fetch_mcp/` modules:
- `fetch_mcp/server.py` — MCP tool registrations (`@mcp.tool`)
- `fetch_mcp/cli.py` — CLI dispatch and `main()`
- `fetch_mcp/json_optimizer.py` — pruning pipeline and schema-first mode
- `fetch_mcp/html.py` — HTML→Markdown conversion
- `fetch_mcp/http.py` — HTTP client, SSL, Chrome detection
- `fetch_mcp/savings.py` — savings logger
- `fetch_mcp/_resolve.py` — `optimize_json` input resolution

Keep `smart_fetch` as the fast HTTP path using `httpx`.

Keep `browser_fetch` as the slower Playwright/Chrome path. It should be optional at runtime when possible, and its CLI help should make headed mode discoverable.

For HTML conversion, use the local `_html_to_markdown()` helper from `fetch_mcp/html.py` so output stays consistent across `smart_fetch`, `css_query`, and `browser_fetch`.

For large JSON, preserve schema-first behavior by default and use JSONPath for drill-down.

## Validation

After changes, run:

```bash
uv run python -m pytest tests/ -v
uv run ruff check .
uv run fetch-mcp -h
uv run fetch-mcp smart_fetch https://example.com
uv run fetch-mcp browser_fetch https://example.com --max-chars 2000
printf '{"items":[{"name":"a"},{"name":"b"}]}' | uv run fetch-mcp optimize
```
