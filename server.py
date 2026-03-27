"""Websearch MCP Server — web search and page fetching with markdown conversion."""

import asyncio
import ssl
from typing import Annotated

import html_to_markdown
from html_to_markdown import ConversionOptions
import httpx
import truststore
from ddgs import DDGS
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Use system certificate store (fixes macOS SSL issues with Homebrew Python)
_ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

# --- Constants ---

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_CHARS = 20_000

# --- Server ---

mcp = FastMCP(
    "websearch",
    instructions=(
        "Web search and page fetching tools. "
        "Use websearch_search to find information, "
        "websearch_fetch_page to get a specific URL as markdown, "
        "or websearch_search_and_fetch for a combined workflow."
    ),
)


# --- Shared Utilities ---


async def _fetch_and_convert(
    url: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    extract_metadata: bool = False,
    heading_style: str = "atx",
) -> str:
    """Fetch a URL and convert its HTML to markdown."""
    async with httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        verify=_ssl_ctx,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()

    html = response.text
    # html-to-markdown has built-in metadata extraction (title, meta tags as YAML frontmatter)
    options = ConversionOptions(
        heading_style=heading_style,
        extract_metadata=extract_metadata,
    )
    result = html_to_markdown.convert(html, options=options)

    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n[... truncated]"

    return result


def _handle_error(e: Exception) -> str:
    """Format errors consistently."""
    if isinstance(e, httpx.TimeoutException):
        return f"Error: Request timed out — {e}"
    if isinstance(e, httpx.HTTPStatusError):
        return f"Error: HTTP {e.response.status_code} — {e}"
    return f"Error: {type(e).__name__} — {e}"


# --- Tools ---


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def websearch_fetch_page(
    url: Annotated[str, Field(description="URL to fetch")],
    extract_metadata: Annotated[
        bool, Field(description="Include YAML frontmatter with page metadata")
    ] = False,
    heading_style: Annotated[
        str, Field(description='Heading style: "atx" (#) or "underlined"')
    ] = "atx",
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
) -> str:
    """Fetch a URL and return its content as clean markdown. Uses html-to-markdown for high-performance conversion that dramatically reduces token usage."""
    try:
        return await _fetch_and_convert(
            url,
            max_chars=max_chars,
            extract_metadata=extract_metadata,
            heading_style=heading_style,
        )
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def websearch_search(
    query: Annotated[str, Field(description="Search query")],
    max_results: Annotated[
        int, Field(description="Number of results to return", ge=1, le=20)
    ] = 10,
    region: Annotated[
        str, Field(description="Region code for results (e.g. 'us-en', 'wt-wt' for global)")
    ] = "wt-wt",
) -> str:
    """Search the web using DuckDuckGo and return results as a markdown list."""
    try:
        results = DDGS().text(query, max_results=max_results, region=region)
    except Exception as e:
        return _handle_error(e)

    if not results:
        return "No results found."

    lines: list[str] = [f"## Search results for: {query}\n"]
    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("href", "")
        snippet = r.get("body", "")
        lines.append(f"### {i}. [{title}]({url})")
        lines.append(f"{snippet}\n")

    return "\n".join(lines)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    }
)
async def websearch_search_and_fetch(
    query: Annotated[str, Field(description="Search query")],
    max_results: Annotated[
        int, Field(description="Number of top results to fetch", ge=1, le=5)
    ] = 3,
    max_chars_per_page: Annotated[
        int, Field(description="Maximum characters per fetched page", ge=1000, le=50_000)
    ] = 5000,
) -> str:
    """Search the web and fetch top result pages as markdown. Combines search + fetch in one call for efficiency."""
    try:
        results = DDGS().text(query, max_results=max_results)
    except Exception as e:
        return _handle_error(e)

    if not results:
        return "No results found."

    urls = [r.get("href", "") for r in results if r.get("href")]
    titles = [r.get("title", "Untitled") for r in results if r.get("href")]

    async def fetch_one(url: str, title: str) -> str:
        try:
            content = await _fetch_and_convert(url, max_chars=max_chars_per_page)
            return f"## [{title}]({url})\n\n{content}"
        except Exception as e:
            return f"## [{title}]({url})\n\n{_handle_error(e)}"

    pages = await asyncio.gather(
        *(fetch_one(url, title) for url, title in zip(urls, titles))
    )

    header = f"# Search & Fetch: {query}\n\nFetched {len(pages)} pages.\n"
    return header + "\n\n---\n\n".join(pages)


# --- Entry point ---

if __name__ == "__main__":
    mcp.run()
