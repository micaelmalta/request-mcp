# Request MCP Server

The high-efficiency networking layer for LLMs. Reduce token consumption by **58–87%** by cleaning web and API data before it hits your context window.

No API keys required — search is powered by DuckDuckGo.

## Why

When an LLM fetches a URL or calls an API, most of the response is noise — nav bars, scripts, tracking pixels, templated API URLs, null fields, repeated sub-objects. You pay for all of it in tokens, latency, and reduced reasoning room.

Request MCP sits between your agent and the network. It strips the noise, returns only what matters, and lets the agent drill into specifics on demand.

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
│ 58% savings  │  │ Dedup sub-objects    │
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

Run `uv run python benchmark.py` to reproduce. Results from real endpoints:

### HTML → Markdown

| Page | Raw tokens | Optimized | Saved |
|------|-----------|-----------|-------|
| GitHub Blog | 90,829 | 50,702 | 44% |
| Hacker News | 11,883 | 4,381 | 63% |
| MDN — JavaScript | 51,862 | 23,324 | 55% |
| BBC News | 123,673 | 28,855 | 77% |
| Rust Lang | 5,107 | 1,515 | 70% |
| Python docs — asyncio | 6,686 | 2,385 | 64% |
| **Total** | **410,034** | **171,514** | **58%** |

### JSON → Schema-first

| Endpoint | Raw tokens | Pruned | Schema-first | Best |
|----------|-----------|--------|-------------|------|
| GitHub API — repos | 16,518 | 7,055 | 2,474 | **85%** |
| JSONPlaceholder — posts | 8,761 | 8,761 | 315 | **96%** |
| JSONPlaceholder — users | 1,839 | 1,839 | 529 | **71%** |
| JSONPlaceholder — comments | 492 | 479 | 330 | **33%** |
| **Total** | **27,610** | — | **3,648** | **87%** |

At Sonnet pricing ($3/M), that's **$0.79 saved per batch**. At Opus pricing ($15/M), **$3.94**.

## Tools

| Tool | What it does |
|------|-------------|
| [`smart_fetch`](#smart_fetch) | Fetch any URL — auto-optimizes HTML (→ markdown) and JSON (→ schema-first) |
| [`web_search`](#web_search) | Search the web via DuckDuckGo, no API key needed |
| [`css_query`](#css_query) | Fetch a page, return only elements matching a CSS selector |
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

The optimizer is also available as a standalone CLI for shell pipes, scripts, and hooks.

```bash
# Optimize any JSON from stdin
curl -s https://api.github.com/orgs/python/repos | python server.py optimize

# Extract specific fields with JSONPath
cat response.json | python server.py optimize --jsonpath '$[*].name'

# Control nesting depth
echo '{"deep": {"nested": {"data": 1}}}' | python server.py optimize --max-depth 2

# View savings report
python server.py report
```

### Savings Tracking

Every call to `optimize_json`, `smart_fetch`, and the CLI logs the before/after character counts to `~/.local/share/request-mcp/savings.jsonl`. View the cumulative report:

```bash
python server.py report
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
uvx --from git+https://github.com/micaelmalta/request-mcp.git request-mcp
```

Or clone locally for development:

```bash
git clone https://github.com/micaelmalta/request-mcp.git && cd request-mcp
uv sync
```

## Integration

### Claude Code

**1. Add the MCP server:**

```bash
claude mcp add request-mcp -- uvx --from git+https://github.com/micaelmalta/request-mcp.git request-mcp
```

**2. (Optional) Instruct the agent via `CLAUDE.md`:**

```markdown
## JSON Optimization

When any MCP tool (GitHub, Jira, Datadog, Confluence, etc.) returns a JSON response
larger than ~50 lines, pass it through the `optimize_json` tool from request-mcp before
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
            "command": "jq -r '{tool: .tool_name, chars: (.tool_response | tostring | length)}' | jq -r '\"\\(.tool) \\(.chars)\"' | { read -r tool chars; mkdir -p ~/.local/share/request-mcp; echo \"{\\\"ts\\\":\\\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\\\",\\\"source\\\":\\\"hook:$tool\\\",\\\"raw_chars\\\":$chars,\\\"opt_chars\\\":$chars,\\\"saved_chars\\\":0,\\\"saved_pct\\\":0}\" >> ~/.local/share/request-mcp/savings.jsonl; echo \"{\\\"hookSpecificOutput\\\":{\\\"hookEventName\\\":\\\"PostToolUse\\\",\\\"additionalContext\\\":\\\"MCP response was ${chars} chars. Pipe it through optimize_json from request-mcp to reduce token usage. You can pass raw JSON or a file path directly.\\\"}}\"; }"
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
    "request-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/micaelmalta/request-mcp.git", "request-mcp"]
    }
  }
}
```

**2. Add to Cursor Rules** (Settings > Rules, or `.cursorrules`):

```
When any MCP tool returns a large JSON response (>50 lines), pass it through the
optimize_json tool from request-mcp before reasoning. You can pass raw JSON or a
file path directly. Use the jsonpath parameter to drill into specific fields.
```

### OpenCode

**1. Add to `.opencode.json`** (project) or `~/.opencode.json` (global):

```json
{
  "mcpServers": {
    "request-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/micaelmalta/request-mcp.git", "request-mcp"]
    }
  }
}
```

**2. Add to `.opencode.md`** (project memory):

```markdown
## JSON Optimization

When any MCP tool (GitHub, Jira, Datadog, Confluence, etc.) returns a JSON response
larger than ~50 lines, pass it through the `optimize_json` tool from request-mcp before
reasoning over it. You can pass raw JSON or a file path directly. Use jsonpath to drill
into specifics rather than consuming the full payload.
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "request-mcp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/micaelmalta/request-mcp.git", "request-mcp"]
    }
  }
}
```

### MCP Inspector (dev)

```bash
uv run mcp dev server.py
```

### Integration Summary

| | Claude Code | Cursor | OpenCode | Claude Desktop |
|---|---|---|---|---|
| **Add MCP** | `claude mcp add` | `.cursor/mcp.json` | `.opencode.json` | `claude_desktop_config.json` |
| **Instruct agent** | `CLAUDE.md` | `.cursorrules` | `.opencode.md` | Server instructions (built-in) |
| **Auto-hook + logging** | `PostToolUse` hook | Not supported | Not supported | Not supported |
| **CLI pipe** | `\| python server.py optimize` | N/A | N/A | N/A |

## Benchmark

```bash
uv run python benchmark.py
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
