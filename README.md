# Fetch MCP Server

The high-efficiency networking layer for LLMs. Reduce token consumption by **73–87%** by cleaning web and API data before it hits your context window.

No API keys required — search is powered by DuckDuckGo.

## Why

When an LLM fetches a URL or calls an API, most of the response is noise — nav bars, scripts, tracking pixels, templated API URLs, null fields, repeated sub-objects. You pay for all of it in tokens, latency, and reduced reasoning room.

Fetch MCP sits between your agent and the network. It strips the noise, returns only what matters, and lets the agent drill into specifics on demand.

## How It Works

```
Agent calls smart_fetch(url)
        │
        ▼
   ┌─────────┐
   │  Fetch   │
   └────┬─────┘
        │
   HTML ▼          JSON ▼
┌──────────────┐  ┌──────────────────────┐
│ → Markdown   │  │ Strip URL templates  │
│ Strip noise  │  │ Remove nulls/empties │
│ 73% savings  │  │ Dedup sub-objects    │
└──────────────┘  │ Schema-first mode    │
                  │ 87% savings          │
                  └──────────────────────┘
```

For JSON, the default behavior is **schema-first**: large arrays return the structure + 2 sample items instead of all data. The agent then uses `jsonpath` to fetch exactly what it needs.

```
1. smart_fetch("https://api.github.com/orgs/python/repos")
   → { _schema: {id: int, name: string, ...}, _count: 30, _sample: [...2 items] }

2. smart_fetch("https://api.github.com/orgs/python/repos", jsonpath="$[*].name")
   → ["cpython", "mypy", "typeshed", ...]
```

## Token Savings

Run `uv run python scripts/benchmark.py` to reproduce. Results from real endpoints:

### HTML → Markdown

| Page | Raw tokens | Optimized | Saved |
|------|-----------|-----------|-------|
| GitHub Blog | 92,352 | 26,459 | 71% |
| Hacker News | 11,790 | 4,237 | 64% |
| MDN — JavaScript | 51,417 | 8,855 | 83% |
| BBC News | 116,111 | 27,207 | 77% |
| Rust Lang | 5,107 | 1,163 | 77% |
| Go pkg — net/http | 121,427 | 55,383 | 54% |
| Python docs — asyncio | 6,692 | 1,473 | 78% |
| Socket.dev — Axios compromise | 138,981 | 23,788 | 83% |
| **Total** | **543,877** | **148,565** | **73%** |

### JSON → Schema-first

| Endpoint | Raw tokens | Pruned | Schema-first | Best |
|----------|-----------|--------|-------------|------|
| GitHub API — repos | 16,518 | 7,055 | 2,474 | **85%** |
| GitHub API — issues | 20,790 | 16,690 | 3,785 | **82%** |
| JSONPlaceholder — posts | 8,761 | 8,761 | 315 | **96%** |
| JSONPlaceholder — todos | 8,240 | 8,240 | 202 | **98%** |
| JSONPlaceholder — users | 1,839 | 1,839 | 529 | **71%** |
| JSONPlaceholder — comments | 492 | 479 | 330 | **33%** |
| npm — typescript | 1,750 | 1,745 | n/a | **0%** |
| OpenLibrary — search | 1,646 | 1,640 | n/a | **0%** |
| **Total** | **60,036** | — | **11,020** | **82%** |

At Sonnet pricing ($3/M), that's **$1.33 saved per batch**. At Opus pricing ($15/M), **$6.67**.

## Tools

| Tool | What it does |
|------|-------------|
| [`smart_fetch`](#smart_fetch) | Fetch any URL — auto-optimizes HTML (→ markdown) and JSON (→ schema-first) |
| [`browser_fetch`](#browser_fetch) | Fetch JavaScript-rendered pages with Playwright/Chrome |
| [`web_search`](#web_search) | Search the web via DuckDuckGo, no API key needed |
| [`css_query`](#css_query) | Fetch a page, return only elements matching a CSS selector |
| [`pdf_fetch`](#pdf_fetch) | Fetch a PDF URL and return its text content (requires `pdfminer.six`) |
| [`optimize_json`](#optimize_json) | Optimize any JSON blob — use on output from other MCP servers |

### `smart_fetch`

Fetches a URL and auto-detects the content type:

- **HTML** — strips navigation, ads, scripts, and tracking. Converts to clean markdown.
- **JSON arrays (5+ items)** — returns schema + 2 sample items. Use `jsonpath` to drill in.
- **JSON objects / small arrays** — prunes empty values, strips URL templates, deduplicates.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | *required* | URL to fetch |
| `jsonpath` | str | `None` | JSONPath to extract specific fields (e.g. `$[*].name`, `$[?@.id==42]`) |
| `max_depth` | int | `5` | Max JSON nesting depth before flattening to dot-notation |
| `extract_metadata` | bool | `False` | Include YAML frontmatter with page metadata (HTML only) |
| `max_chars` | int | `20000` | Maximum characters in output (1,000–100,000) |

### `browser_fetch`

Fetches a URL with Playwright/Chrome, waits for the rendered page, and converts the final HTML to markdown.

Use this for pages that block simple HTTP clients or require JavaScript rendering. It does **not** bypass CAPTCHA; use headed mode when a human needs to complete a challenge or login before extraction.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | *required* | URL to fetch |
| `selector` | str | `None` | Optional CSS selector to extract from the rendered page |
| `wait_ms` | int | `3000` | Milliseconds to wait after `DOMContentLoaded` |
| `timeout_ms` | int | `30000` | Navigation timeout in milliseconds |
| `headed` | bool | `False` | Open a visible browser window for manual CAPTCHA/login |
| `extract_metadata` | bool | `False` | Include YAML frontmatter with page metadata |
| `max_chars` | int | `20000` | Maximum characters in output (1,000–100,000) |

### `web_search`

Search the web via DuckDuckGo. Returns results as a markdown list.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | *required* | Search query |
| `max_results` | int | `10` | Number of results (1–20) |
| `region` | str | `"wt-wt"` | Region code (`"us-en"`, `"wt-wt"` for global) |

### `css_query`

Fetch a page and return only content matching a CSS selector. Use when you know exactly which part of a page you need (a pricing table, an article body, a specific `div`).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | *required* | URL to fetch |
| `selector` | str | *required* | CSS selector (e.g. `#pricing-table`, `.product-card`, `article`) |
| `max_chars` | int | `20000` | Maximum characters in output (1,000–100,000) |

### `pdf_fetch`

Fetch a URL that serves a PDF and return its text as plain markdown. Falls back to HTML→markdown if the URL does not return a PDF.


| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | *required* | URL of a PDF document |
| `pages` | str | `None` | Page range to extract, e.g. `"1-5"` or `"3"`. Default: all pages. |
| `headers` | dict | `None` | Optional HTTP headers (e.g. `{"Authorization": "Bearer token"}`) |
| `max_chars` | int | `20000` | Maximum characters in output (1,000–100,000) |

### `optimize_json`

Optimize any JSON payload — from other MCP servers, API responses, or files. This is the key tool for reducing token usage across your entire MCP stack.

Accepts raw JSON strings **or file paths**. When an MCP tool response is too large and gets saved to a file by Claude, pass the file path directly.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `data` | str | *required* | Raw JSON string, or a file path to a JSON file |
| `jsonpath` | str | `None` | JSONPath to extract specific fields |
| `max_depth` | int | `5` | Max nesting depth before flattening |
| `max_chars` | int | `20000` | Maximum characters in output (1,000–100,000) |

**Typical workflow with other MCP servers:**

```
1. Call mcp__github__list_pull_requests → agent gets large JSON response
2. Call optimize_json(data=<response>) → schema + 2 samples, 85% fewer tokens
3. Call optimize_json(data=<response>, jsonpath="$[?@.state=='open'].title") → exactly what's needed
```

### JSON Optimization Pipeline

Applied by both `smart_fetch` (on JSON URLs) and `optimize_json` (on any JSON blob):

| Step | What it does | Impact |
|------|-------------|--------|
| Schema-first mode | Large arrays → structure + 2 samples | Huge on list endpoints |
| URL template stripping | Removes `forks_url`, `keys_url{/key_id}`, etc. | ~30 keys per object in REST APIs |
| Empty/null removal | Strips `null`, `""`, `[]`, `{}` | Moderate |
| Sub-object dedup | Identical nested dicts (e.g. `owner`) extracted once | Large on org/user APIs |
| Deep flattening | Dicts beyond `max_depth` → dot-notation keys | Prevents runaway nesting |
| JSONPath drill-in | Extract only matching fields on follow-up calls | Surgical precision |

## CLI

The fetcher and optimizer are also available as a standalone CLI for shell pipes, scripts, and hooks.

```bash
# Smart-fetch any URL
uv run fetch-mcp smart_fetch https://example.com

# Smart-fetch JSON and extract specific fields with JSONPath
uv run fetch-mcp smart_fetch https://api.github.com/orgs/python/repos --jsonpath '$[*].name'

# Browser-fetch a JavaScript-rendered or HTTP-client-blocked page
uv run fetch-mcp browser_fetch https://example.com

# Open a visible browser for manual CAPTCHA/login, then extract after waiting
uv run fetch-mcp browser_fetch https://example.com --headed --wait-ms 30000

# Fetch a PDF and extract its text (requires: uv add pdfminer.six)
uv run fetch-mcp pdf_fetch https://example.com/paper.pdf

# Extract specific pages from a PDF
uv run fetch-mcp pdf_fetch https://example.com/report.pdf --pages 1-5

# Optimize any JSON from stdin
curl -s https://api.github.com/orgs/python/repos | uv run fetch-mcp optimize

# Extract specific fields with JSONPath
cat response.json | uv run fetch-mcp optimize --jsonpath '$[*].name'

# Control nesting depth
echo '{"deep": {"nested": {"data": 1}}}' | uv run fetch-mcp optimize --max-depth 2

# View savings report
uv run fetch-mcp report
```

### Savings Tracking

Every call to `optimize_json`, `smart_fetch`, and the CLI logs the before/after character counts to `~/.local/share/fetch-mcp/savings.jsonl`. View the cumulative report:

```bash
uv run fetch-mcp report
```

```
Source                          Calls    Raw chars    Opt chars        Saved       %
------------------------------------------------------------------------------------
optimize_json                      12      284,103       41,220      242,883   85.5%
smart_fetch:https://api.gith       3       59,986       24,823       35,163   58.6%
hook:mcp__jira__jira_search         5       93,052       93,052            0    0.0%
------------------------------------------------------------------------------------
TOTAL                              20      437,141      159,095      278,046   63.6%
```

The `hook:*` entries track raw MCP response sizes before optimization. The `optimize_json` entries track actual savings.

Override the log path with `REQUEST_MCP_SAVINGS_LOG=/custom/path.jsonl`.

## Setup

No local clone required — run directly from GitHub with [uv](https://docs.astral.sh/uv/):

```bash
uvx --from git+https://github.com/micaelmalta/fetch-mcp.git fetch-mcp
```

Or clone locally for development:

```bash
git clone https://github.com/micaelmalta/fetch-mcp.git && cd fetch-mcp
uv sync --group dev
```

Install as a Claude skill:

```bash
curl -fsSL https://raw.githubusercontent.com/micaelmalta/fetch-mcp/main/install.sh | bash
```

Install a different branch or tag:

```bash
curl -fsSL https://raw.githubusercontent.com/micaelmalta/fetch-mcp/main/install.sh | REQUEST_MCP_REF=your-branch-or-tag bash
```

## Integration

### Claude Code

**1. Add the MCP server:**

```bash
claude mcp add fetch-mcp -- uvx --from git+https://github.com/micaelmalta/fetch-mcp.git fetch-mcp
```

**2. (Optional) Instruct the agent via `CLAUDE.md`:**

```markdown
## JSON Optimization

When any MCP tool (GitHub, Jira, Datadog, Confluence, etc.) returns a JSON response
larger than ~50 lines, pass it through the `optimize_json` tool from fetch-mcp before
reasoning over it. You can pass raw JSON or a file path directly. Use jsonpath to drill
into specifics rather than consuming the full payload.
```

**3. (Optional) Auto-hook for logging + nudging:**

Add to `~/.claude/settings.json` to automatically log MCP response sizes and remind the agent to optimize:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "mcp__github__*|mcp__jira__*|mcp__datadog__*|mcp__confluence__*",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '{tool: .tool_name, chars: (.tool_response | tostring | length)}' | jq -r '\"\\(.tool) \\(.chars)\"' | { read -r tool chars; mkdir -p ~/.local/share/fetch-mcp; echo \"{\\\"ts\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"source\\\":\\\"hook:$tool\\\",\\\"raw_chars\\\":$chars,\\\"opt_chars\\\":$chars,\\\"saved_chars\\\":0,\\\"saved_pct\\\":0}\" >> ~/.local/share/fetch-mcp/savings.jsonl; echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PostToolUse\\\",\\\"additionalContext\\\":\\\"MCP response was ${chars} chars. Pipe it through optimize_json from fetch-mcp to reduce token usage. You can pass raw JSON or a file path directly.\\\"}}\"; }"
          }
        ]
      }
    ]
  }
}
```

Add or remove MCP prefixes from the matcher as needed.

### Cursor

**1. Add to `.cursor/mcp.json`** (project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "fetch-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/micaelmalta/fetch-mcp.git", "fetch-mcp"]
    }
  }
}
```

**2. Add to Cursor Rules** (Settings > Rules, or `.cursorrules`):

```
When any MCP tool returns a large JSON response (>50 lines), pass it through the
optimize_json tool from fetch-mcp before reasoning. You can pass raw JSON or a
file path directly. Use the jsonpath parameter to drill into specific fields.
```

### OpenCode

**1. Add to `.opencode.json`** (project) or `~/.opencode.json` (global):

```json
{
  "mcpServers": {
    "fetch-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/micaelmalta/fetch-mcp.git", "fetch-mcp"]
    }
  }
}
```

**2. Add to `.opencode.md`** (project memory):

```markdown
## JSON Optimization

When any MCP tool (GitHub, Jira, Datadog, Confluence, etc.) returns a JSON response
larger than ~50 lines, pass it through the `optimize_json` tool from fetch-mcp before
reasoning over it. You can pass raw JSON or a file path directly. Use jsonpath to drill
into specifics rather than consuming the full payload.
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fetch-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/micaelmalta/fetch-mcp.git", "fetch-mcp"]
    }
  }
}
```

### MCP Inspector (dev)

```bash
uv run mcp dev fetch_mcp/server.py
```

### Integration Summary

| | Claude Code | Cursor | OpenCode | Claude Desktop |
|---|---|---|---|---|
| **Add MCP** | `claude mcp add` | `.cursor/mcp.json` | `.opencode.json` | `claude_desktop_config.json` |
| **Instruct agent** | `CLAUDE.md` | `.cursorrules` | `.opencode.md` | Server instructions (built-in) |
| **Auto-hook + logging** | `PostToolUse` hook | Not supported | Not supported | Not supported |
| **CLI pipe** | `\| uv run fetch-mcp optimize` | N/A | N/A | N/A |

## Benchmark

```bash
uv run python scripts/benchmark.py
```

Fetches real pages and API endpoints, counts tokens with `tiktoken` (cl100k_base), and compares raw vs optimized output across HTML and JSON with cost estimates.

## Dependencies

| Package | Purpose |
|---------|---------|
| [mcp](https://github.com/modelcontextprotocol/python-sdk) | FastMCP server framework |
| [httpx](https://www.python-httpx.org/) | Async HTTP client |
| [html-to-markdown](https://github.com/nichochar/html-to-markdown) | Rust-based HTML → Markdown (~200 MB/s) |
| [beautifulsoup4](https://www.crummy.com/software/BeautifulSoup/) | CSS selector extraction |
| [jsonpath-ng](https://github.com/h2non/jsonpath-ng) | JSONPath query support |
| [ddgs](https://github.com/deedy5/ddgs) | DuckDuckGo search (no API key) |
| [truststore](https://github.com/sethmlarson/truststore) | System certificate store for SSL |
| [tiktoken](https://github.com/openai/tiktoken) | Token counting (dev only, for benchmark) |
