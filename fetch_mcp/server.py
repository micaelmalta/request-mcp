"""fetch-mcp MCP tool registrations."""

from __future__ import annotations

import json
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from fetch_mcp._resolve import _resolve_json_input
from fetch_mcp.cache import _CacheEntry, _response_cache
from fetch_mcp.html import _html_to_markdown
from fetch_mcp.http import (
    DEFAULT_MAX_CHARS,
    USER_AGENT,
    _fetch_raw,
    _find_chrome_executable,
    _handle_error,
    _is_json_content,
)
from fetch_mcp.json_optimizer import (
    _build_schema_summary,
    _prune_json,
    _should_use_schema_mode,
)
from fetch_mcp.savings import _log_savings

mcp = FastMCP(
    "fetch-mcp",
    instructions=(
        "High-efficiency networking tools for LLMs. "
        "Use smart_fetch to auto-optimize any URL (HTML or JSON). "
        "Use web_search to find information. "
        "Use css_query to extract specific page elements via CSS selectors. "
        "IMPORTANT: Use optimize_json to reduce token usage on large JSON responses "
        "from ANY other MCP tool (GitHub, Jira, Datadog, etc.). "
        "When another tool returns a large JSON payload, pipe it through optimize_json "
        "before reasoning over it."
    ),
)


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def smart_fetch(
    url: Annotated[str, Field(description="URL to fetch")],
    jsonpath: Annotated[
        str | None,
        Field(description="JSONPath expression to drill into JSON data (e.g. '$[0:5]', '$[*].name', '$[?@.id==42]')"),
    ] = None,
    max_depth: Annotated[
        int,
        Field(description="Max nesting depth for JSON before flattening (default 5)", ge=1, le=20),
    ] = 5,
    extract_metadata: Annotated[
        bool, Field(description="Include YAML frontmatter with page metadata (HTML only)")
    ] = False,
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
    use_cache: Annotated[bool, Field(description="Return cached response if available (default True)")] = True,
    ttl: Annotated[int, Field(description="Cache TTL in seconds (default 1800)", ge=60, le=86400)] = 1800,
) -> str:
    """Fetch any URL and auto-optimize based on content type.

    For HTML: converts to clean markdown, stripping navigation, ads, and scripts.
    For JSON: returns a schema + sample by default for large arrays. Use the jsonpath
    parameter to drill into specific items or fields on follow-up calls.
    Dramatically reduces token usage compared to raw fetching.
    """
    import time

    cache_key = _response_cache.make_key(url)

    if use_cache:
        try:
            cached = _response_cache.get(cache_key)
            if cached is not None:
                _log_savings(cached.raw_chars, len(cached.content), source=f"cache_hit:{url[:60]}")
                return cached.content
        except Exception:
            pass

    try:
        response = await _fetch_raw(url)

        if _is_json_content(response):
            try:
                data = response.json()
            except json.JSONDecodeError:
                return _html_to_markdown(response.text, max_chars=max_chars)

            raw_chars = len(response.text)

            if not jsonpath and _should_use_schema_mode(data):
                summary = _build_schema_summary(data, max_depth=max_depth)
                result = json.dumps(summary, indent=2, ensure_ascii=False, default=str)
                if len(result) > max_chars:
                    result = result[:max_chars] + "\n\n... [truncated]"
                _log_savings(raw_chars, len(result), source=f"smart_fetch:{url[:60]}")
                if use_cache:
                    try:
                        _response_cache.set(cache_key, _CacheEntry(result, raw_chars, time.monotonic() + ttl))
                    except Exception:
                        pass
                return result

            pruned = _prune_json(data, jsonpath=jsonpath, max_depth=max_depth)
            result = json.dumps(pruned, indent=2, ensure_ascii=False, default=str)
            if len(result) > max_chars:
                result = result[:max_chars] + "\n\n... [truncated]"
            _log_savings(raw_chars, len(result), source=f"smart_fetch:{url[:60]}")
            if use_cache:
                try:
                    _response_cache.set(cache_key, _CacheEntry(result, raw_chars, time.monotonic() + ttl))
                except Exception:
                    pass
            return result

        raw_chars = len(response.text)
        result = _html_to_markdown(
            response.text,
            max_chars=max_chars,
            extract_metadata=extract_metadata,
        )
        _log_savings(raw_chars, len(result), source=f"smart_fetch:{url[:60]}")
        if use_cache:
            try:
                _response_cache.set(cache_key, _CacheEntry(result, raw_chars, time.monotonic() + ttl))
            except Exception:
                pass
        return result

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
async def web_search(
    query: Annotated[str, Field(description="Search query")],
    max_results: Annotated[int, Field(description="Number of results to return", ge=1, le=20)] = 10,
    region: Annotated[str, Field(description="Region code for results (e.g. 'us-en', 'wt-wt' for global)")] = "wt-wt",
) -> str:
    """Search the web using DuckDuckGo and return results as a markdown list."""
    try:
        from ddgs import DDGS

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
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def css_query(
    url: Annotated[str, Field(description="URL to fetch")],
    selector: Annotated[
        str, Field(description="CSS selector to extract (e.g. '#pricing-table', '.product-description', 'article')")
    ],
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
) -> str:
    """Fetch a page and return only the content matching a CSS selector."""
    try:
        from bs4 import BeautifulSoup

        response = await _fetch_raw(url)
        soup = BeautifulSoup(response.text, "html.parser")
        elements = soup.select(selector)

        if not elements:
            return f"No elements matched selector: {selector}"

        parts: list[str] = []
        for el in elements:
            md = _html_to_markdown(str(el), max_chars=max_chars)
            parts.append(md)

        result = "\n\n---\n\n".join(parts)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n\n[... truncated]"
        return result

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
async def browser_fetch(
    url: Annotated[str, Field(description="URL to fetch with a real browser")],
    selector: Annotated[
        str | None,
        Field(description="Optional CSS selector to extract from the rendered page"),
    ] = None,
    wait_ms: Annotated[int, Field(description="Milliseconds to wait after DOMContentLoaded", ge=0, le=120_000)] = 3_000,
    timeout_ms: Annotated[int, Field(description="Navigation timeout in milliseconds", ge=1_000, le=120_000)] = 30_000,
    headed: Annotated[
        bool,
        Field(description="Open a visible browser window for human-in-the-loop CAPTCHA/login"),
    ] = False,
    extract_metadata: Annotated[bool, Field(description="Include YAML frontmatter with page metadata")] = False,
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
) -> str:
    """Fetch a JavaScript-rendered page with Playwright and return markdown."""
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except ImportError:
        return (
            "Error: Playwright is not installed. Install it with `uv add playwright`, "
            "then retry. If no Chrome is installed, also run `uv run playwright install chromium`."
        )

    browser = None
    try:
        async with async_playwright() as p:
            launch_kwargs: dict[str, object] = {"headless": not headed}
            chrome_path = _find_chrome_executable()
            if chrome_path:
                launch_kwargs["executable_path"] = chrome_path

            browser = await p.chromium.launch(**launch_kwargs)
            page = await browser.new_page(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 900},
            )

            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            if wait_ms:
                await page.wait_for_timeout(wait_ms)

            if selector:
                locator = page.locator(selector)
                count = await locator.count()
                if count == 0:
                    return f"No elements matched selector: {selector}"
                html = await locator.evaluate_all("els => els.map(el => el.outerHTML).join('\\n\\n')")
            else:
                html = await page.content()

            result = _html_to_markdown(
                html,
                max_chars=max_chars,
                extract_metadata=extract_metadata,
            )
            status = response.status if response else "unknown"
            _log_savings(len(html), len(result), source=f"browser_fetch:{url[:60]}")
            if isinstance(status, int) and status >= 400:
                return f"HTTP status from browser: {status}\n\n{result}"
            return result
    except PlaywrightTimeoutError as e:
        return f"Error: Browser navigation timed out — {e}"
    except Exception as e:
        return _handle_error(e)
    finally:
        if browser is not None:
            await browser.close()


@mcp.tool(
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
)
async def optimize_json(
    data: Annotated[
        str,
        Field(
            description=(
                "Raw JSON string to optimize, OR a file path to a JSON file. "
                "When an MCP tool response is too large and gets saved to a file, "
                "pass the file path here (e.g. '/path/to/tool-results/file.txt')."
            )
        ),
    ],
    jsonpath: Annotated[
        str | None,
        Field(description="JSONPath expression to extract specific fields (e.g. '$[*].name', '$[?@.state==\"open\"]')"),
    ] = None,
    max_depth: Annotated[
        int,
        Field(description="Max nesting depth before flattening (default 5)", ge=1, le=20),
    ] = 5,
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
) -> str:
    """Optimize any JSON payload to reduce token usage."""
    raw_json = _resolve_json_input(data)

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON — {e}"

    raw_chars = len(raw_json)

    if not jsonpath and _should_use_schema_mode(parsed):
        summary = _build_schema_summary(parsed, max_depth=max_depth)
        result = json.dumps(summary, indent=2, ensure_ascii=False, default=str)
    else:
        pruned = _prune_json(parsed, jsonpath=jsonpath, max_depth=max_depth)
        result = json.dumps(pruned, indent=2, ensure_ascii=False, default=str)

    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n... [truncated]"

    _log_savings(raw_chars, len(result), source="optimize_json")
    return result
