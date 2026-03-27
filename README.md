# Websearch MCP Server

An MCP server for web search and page fetching. Converts HTML to clean markdown using [html-to-markdown](https://github.com/nichochar/html-to-markdown) (Rust-based, ~200 MB/s), cutting token usage by **~60%** when LLMs consume web content.

No API keys required — search is powered by DuckDuckGo.

## Token Savings

Run `uv run python benchmark.py` to reproduce. Results from fetching real pages:

| Page | HTML tokens | MD tokens | Saved |
|------|-------------|-----------|-------|
| GitHub Blog | 90,829 | 50,733 | 44% |
| Hacker News | 11,884 | 4,381 | 63% |
| MDN — JavaScript | 51,862 | 23,326 | 55% |
| BBC News | 123,997 | 28,918 | 77% |
| Go pkg — net/http | 119,994 | 60,344 | 50% |
| Python docs — asyncio | 6,686 | 2,405 | 64% |
| Rust Lang | 5,107 | 1,515 | 70% |
| **Total** | **410,359** | **171,622** | **58%** |

At Sonnet pricing ($3/M input tokens), that's **$0.72 saved per batch** of 7 pages.

## Tools

| Tool | Description |
|------|-------------|
| `websearch_search` | Search the web via DuckDuckGo |
| `websearch_fetch_page` | Fetch a URL and return content as markdown |
| `websearch_search_and_fetch` | Search + fetch top results in one call |

### `websearch_search`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | *required* | Search query |
| `max_results` | int | `10` | Number of results (1–20) |
| `region` | str | `"wt-wt"` | Region code (`"us-en"`, `"wt-wt"` for global) |

### `websearch_fetch_page`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `url` | str | *required* | URL to fetch |
| `max_chars` | int | `20000` | Truncate output (1,000–100,000) |
| `extract_metadata` | bool | `False` | Include YAML frontmatter (title, meta tags) |
| `heading_style` | str | `"atx"` | `"atx"` (#) or `"underlined"` |

### `websearch_search_and_fetch`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | str | *required* | Search query |
| `max_results` | int | `3` | Pages to fetch (1–5) |
| `max_chars_per_page` | int | `5000` | Max characters per page (1,000–50,000) |

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Usage

### MCP Inspector (dev)

```bash
uv run mcp dev server.py
```

### Claude Code

```bash
claude mcp add websearch -- uv run --directory /path/to/mcp-websearch-server python server.py
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "websearch": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-websearch-server", "python", "server.py"]
    }
  }
}
```

## Benchmark

```bash
uv run python benchmark.py
```

Fetches a set of real pages, counts tokens with `tiktoken` (cl100k_base), and reports HTML vs markdown savings with cost estimates for Sonnet and Opus pricing.

## Dependencies

- **[mcp](https://github.com/modelcontextprotocol/python-sdk)** — FastMCP framework
- **[httpx](https://www.python-httpx.org/)** — async HTTP client
- **[html-to-markdown](https://github.com/nichochar/html-to-markdown)** — Rust-based HTML-to-Markdown converter
- **[ddgs](https://github.com/deedy5/ddgs)** — DuckDuckGo search (no API key)
- **[truststore](https://github.com/sethmlarson/truststore)** — system certificate store for SSL
- **[tiktoken](https://github.com/openai/tiktoken)** — token counting (dev dependency, for benchmark)
