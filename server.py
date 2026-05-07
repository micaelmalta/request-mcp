"""fetch-mcp — The high-efficiency networking layer for LLMs.

Also usable as a CLI for hooking into other tool outputs:
    python server.py smart_fetch https://example.com
    python server.py smart_fetch https://api.github.com/orgs/python/repos --jsonpath '$[*].name'
    echo '{"big": "json"}' | python server.py optimize
    echo '{"big": "json"}' | python server.py optimize --jsonpath '$.key'

`gh run view` requires explicit JSON fields, for example:
    gh run view <id> --repo owner/repo --json jobs,conclusion,status,displayTitle \\
      | python server.py optimize
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from jsonpath_ng.ext import parse as jsonpath_parse
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Lazy-init: `python server.py optimize` must not import httpx/html_to_markdown/ddgs.
_ssl_ctx = None


def _get_ssl_ctx():
    """System certificate store (fixes macOS SSL issues with Homebrew Python)."""
    global _ssl_ctx
    if _ssl_ctx is None:
        import ssl

        import truststore

        _ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return _ssl_ctx

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


# --- Shared Utilities ---


def _build_client():
    """Build a configured async HTTP client."""
    import httpx

    return httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        verify=_get_ssl_ctx(),
    )


def _find_chrome_executable() -> str | None:
    """Return a local Chrome/Chromium executable if one is installed."""
    candidates = [
        os.environ.get("REQUEST_MCP_CHROME_PATH"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ]
    return next((path for path in candidates if path and Path(path).exists()), None)


async def _fetch_raw(url: str):
    """Fetch a URL and return the raw response."""
    async with _build_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response


def _html_to_markdown(
    html: str,
    max_chars: int = DEFAULT_MAX_CHARS,
    extract_metadata: bool = False,
) -> str:
    """Convert HTML to clean markdown, truncating if needed."""
    import html_to_markdown

    # html-to-markdown 3.3.2 raises a KeyError when converting Python-side
    # ConversionOptions to Rust options on Python 3.14, so use package defaults.
    raw = html_to_markdown.convert(html)
    # html-to-markdown versions vary: 3.x returns ConversionResult, older releases
    # returned either a dict or a string.
    if isinstance(raw, dict):
        result = raw.get("content", "")
        if not isinstance(result, str):
            result = str(result)
    elif isinstance(raw, str):
        result = raw
    elif isinstance(getattr(raw, "content", None), str):
        result = raw.content
    else:
        result = str(raw)
    if not extract_metadata:
        result = re.sub(r"\A---\n.*?\n---\n*", "", result, count=1, flags=re.DOTALL)
    if len(result) > max_chars:
        result = result[:max_chars] + "\n\n[... truncated]"
    return result


# --- JSON Pruning ---

# URL template patterns common in REST APIs (e.g. "{/id}", "{?since,all}")
_URL_TEMPLATE_RE = re.compile(r"\{[/+?]?[^}]+\}")


def _prune_json(data: object, jsonpath: str | None = None, max_depth: int = 5) -> object:
    """Aggressively prune a JSON object to minimise token usage.

    Pipeline (in order):
    1. JSONPath extraction — if provided, narrow to matching subtree first.
    2. Strip API URL templates — keys whose values are templated URLs (e.g. forks_url).
    3. Remove empty / null / false-boolean values.
    4. Deduplicate repeated sub-objects across an array.
    5. Flatten dicts beyond max_depth with dot-notation keys.
    """
    if jsonpath:
        expr = jsonpath_parse(jsonpath)
        matches = expr.find(data)
        if not matches:
            return {"_info": "No matches for JSONPath expression", "jsonpath": jsonpath}
        if len(matches) == 1:
            data = matches[0].value
        else:
            data = [m.value for m in matches]

    data = _clean(data, current_depth=0, max_depth=max_depth)

    # Deduplicate repeated objects inside arrays
    if isinstance(data, list):
        data = _dedup_array(data)

    return data


def _clean(obj: object, current_depth: int, max_depth: int) -> object:
    """Recursively clean a JSON value."""
    if isinstance(obj, dict):
        if current_depth >= max_depth:
            return _flatten_dict(obj)
        cleaned = {}
        for k, v in obj.items():
            # Strip API URL templates (huge token saver for REST APIs)
            if isinstance(v, str) and _is_api_url_template(v):
                continue
            v = _clean(v, current_depth + 1, max_depth)
            if not _is_empty(v):
                cleaned[k] = v
        return cleaned
    if isinstance(obj, list):
        cleaned = [_clean(item, current_depth, max_depth) for item in obj]
        return [item for item in cleaned if not _is_empty(item)]
    return obj


def _is_api_url_template(v: str) -> bool:
    """Detect templated API URLs like 'https://api.github.com/repos/x/y/issues{/number}'."""
    return v.startswith(("http://", "https://")) and bool(_URL_TEMPLATE_RE.search(v))


def _flatten_dict(d: dict, prefix: str = "") -> dict:
    """Flatten nested dict into dot-notation keys."""
    items: dict = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, key))
        elif not _is_empty(v):
            items[key] = v
    return items


def _is_empty(v: object) -> bool:
    """Check if a value is 'empty' and should be pruned."""
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, (list, dict)) and len(v) == 0:
        return True
    return False


def _dedup_array(items: list) -> list:
    """Deduplicate repeated sub-objects in an array of dicts.

    When the same nested dict value appears across multiple array items
    (e.g. `owner` is identical for all repos in an org), extract it once
    as a top-level _ref and replace inline occurrences with a pointer.
    Also collapses keys that have the same scalar value across ALL items.
    """
    if not items or not all(isinstance(i, dict) for i in items):
        return items

    # --- Phase 1: collapse keys with uniform scalar values ---
    all_keys = set()
    for item in items:
        all_keys.update(item.keys())

    uniform: dict[str, object] = {}
    for key in list(all_keys):
        values = [item.get(key, _SENTINEL) for item in items]
        non_missing = [v for v in values if v is not _SENTINEL]
        if (
            len(non_missing) == len(items)
            and all(not isinstance(v, (dict, list)) for v in non_missing)
            and len(set(_hashable(v) for v in non_missing)) == 1
        ):
            uniform[key] = non_missing[0]

    # --- Phase 2: deduplicate repeated nested dicts ---
    # Fingerprint every nested dict across all items
    dict_registry: dict[str, tuple[str, object]] = {}  # fingerprint -> (ref_name, value)

    for item in items:
        for key, val in item.items():
            if not isinstance(val, dict) or key in uniform:
                continue
            fp = json.dumps(val, sort_keys=True, default=str)
            if fp not in dict_registry:
                # First time seeing this dict — register it
                dict_registry[fp] = (key, val)

    # Only keep dicts that appear more than once
    dup_fps: dict[str, str] = {}  # fingerprint -> ref_name
    fp_counts: dict[str, int] = {}
    for item in items:
        for key, val in item.items():
            if isinstance(val, dict):
                fp = json.dumps(val, sort_keys=True, default=str)
                fp_counts[fp] = fp_counts.get(fp, 0) + 1

    for fp, count in fp_counts.items():
        if count > 1 and fp in dict_registry:
            ref_name, _ = dict_registry[fp]
            dup_fps[fp] = ref_name

    if not uniform and not dup_fps:
        return items

    # --- Apply deduplication ---
    result_items = []
    for item in items:
        new_item = {}
        for k, v in item.items():
            if k in uniform:
                continue
            if isinstance(v, dict):
                fp = json.dumps(v, sort_keys=True, default=str)
                if fp in dup_fps:
                    new_item[k] = f"→ (same as _common.{dup_fps[fp]})"
                    continue
            new_item[k] = v
        result_items.append(new_item)

    # Build wrapper with extracted common data
    wrapper: dict[str, object] = {}
    if uniform:
        wrapper["_common_values"] = uniform
    if dup_fps:
        refs: dict[str, object] = {}
        for fp, ref_name in dup_fps.items():
            _, val = dict_registry[fp]
            refs[ref_name] = val
        wrapper["_common"] = refs
    wrapper["items"] = result_items
    return wrapper  # type: ignore[return-value]


_SENTINEL = object()


def _hashable(v: object) -> object:
    """Make a value hashable for set comparison."""
    if isinstance(v, (list, dict)):
        return json.dumps(v, sort_keys=True, default=str)
    return v


def _is_json_content(response) -> bool:
    """Detect if a response contains JSON content."""
    ct = response.headers.get("content-type", "")
    return "json" in ct or "javascript" in ct


# --- Schema-first / Lazy mode ---

# Threshold: arrays with this many items or more get schema-only treatment
_SCHEMA_THRESHOLD = 5


def _infer_type(v: object) -> str:
    """Return a concise type descriptor for a JSON value."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        if len(v) > 80:
            return "string(long)"
        return "string"
    if isinstance(v, list):
        if not v:
            return "[]"
        inner = _infer_type(v[0])
        return f"[{inner}, ...{len(v)}]"
    if isinstance(v, dict):
        return f"object({len(v)} keys)"
    return type(v).__name__


def _build_schema_summary(data: list[dict], max_depth: int = 5) -> dict:
    """Build a schema-only summary of a uniform JSON array.

    Returns a compact representation with:
    - _schema: key -> type mapping (inferred from a pruned item)
    - _count: total items
    - _sample: first 2 items (pruned) so the agent knows what the data looks like
    - _hint: instruction for the agent to use JSONPath to drill in
    """
    # Prune first item to infer schema from the cleaned version
    pruned_first = _prune_json(data[0], max_depth=max_depth)
    schema: dict[str, str] = {}
    if isinstance(pruned_first, dict):
        for k, v in pruned_first.items():
            schema[k] = _infer_type(v)

    sample_count = min(2, len(data))
    sample = [_prune_json(item, max_depth=max_depth) for item in data[:sample_count]]

    return {
        "_mode": "schema",
        "_count": len(data),
        "_schema": schema,
        "_sample": sample,
        "_hint": (
            f"Returned schema + {sample_count} sample items out of {len(data)}. "
            "Use the jsonpath parameter to fetch specific items or fields. "
            "Examples: '$[0:5]' (first 5 items), '$[*].name' (all names), "
            "'$[?@.id==42]' (item with id 42)."
        ),
    }


def _should_use_schema_mode(data: object) -> bool:
    """Decide whether to use schema-first mode for this data."""
    if not isinstance(data, list):
        return False
    if len(data) < _SCHEMA_THRESHOLD:
        return False
    # Check if it's a uniform array of dicts
    if not all(isinstance(item, dict) for item in data):
        return False
    return True


def _handle_error(e: Exception) -> str:
    """Format errors consistently."""
    import httpx

    if isinstance(e, httpx.TimeoutException):
        return f"Error: Request timed out — {e}"
    if isinstance(e, httpx.HTTPStatusError):
        return f"Error: HTTP {e.response.status_code} — {e}"
    return f"Error: {type(e).__name__} — {e}"


# --- Savings Logger ---

_SAVINGS_LOG = Path(os.environ.get(
    "REQUEST_MCP_SAVINGS_LOG",
    Path.home() / ".local" / "share" / "fetch-mcp" / "savings.jsonl",
))


def _log_savings(raw_chars: int, opt_chars: int, source: str = "") -> None:
    """Append a savings entry to the JSONL log file."""
    try:
        _SAVINGS_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "raw_chars": raw_chars,
            "opt_chars": opt_chars,
            "saved_chars": raw_chars - opt_chars,
            "saved_pct": round((raw_chars - opt_chars) / raw_chars * 100, 1) if raw_chars else 0,
        }
        with open(_SAVINGS_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass  # never fail the tool over logging


def _print_savings_report() -> None:
    """Print a summary of all logged savings."""
    if not _SAVINGS_LOG.exists():
        print(f"No savings logged yet. Log file: {_SAVINGS_LOG}")
        return

    entries = []
    with open(_SAVINGS_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if not entries:
        print("No savings entries found.")
        return

    total_raw = sum(e["raw_chars"] for e in entries)
    total_opt = sum(e["opt_chars"] for e in entries)
    total_saved = total_raw - total_opt
    total_pct = round(total_saved / total_raw * 100, 1) if total_raw else 0

    print("fetch-mcp savings report")
    print(f"Log: {_SAVINGS_LOG}")
    print(f"Entries: {len(entries)}")
    print()

    # Per-source breakdown
    by_source: dict[str, dict] = {}
    for e in entries:
        src = e.get("source", "unknown") or "unknown"
        if src not in by_source:
            by_source[src] = {"count": 0, "raw": 0, "opt": 0}
        by_source[src]["count"] += 1
        by_source[src]["raw"] += e["raw_chars"]
        by_source[src]["opt"] += e["opt_chars"]

    header = f"{'Source':<30} {'Calls':>6} {'Raw chars':>12} {'Opt chars':>12} {'Saved':>12} {'%':>7}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for src, s in sorted(by_source.items()):
        saved = s["raw"] - s["opt"]
        pct = round(saved / s["raw"] * 100, 1) if s["raw"] else 0
        print(f"{src:<30} {s['count']:>6} {s['raw']:>12,} {s['opt']:>12,} {saved:>12,} {pct:>6.1f}%")
    print(sep)
    print(f"{'TOTAL':<30} {len(entries):>6} {total_raw:>12,} {total_opt:>12,} {total_saved:>12,} {total_pct:>6.1f}%")
    print()

    # Last 10 entries
    print(f"Last {min(10, len(entries))} entries:")
    for e in entries[-10:]:
        ts = e["ts"][:19].replace("T", " ")
        src = e.get("source", "")[:20]
        print(f"  {ts}  {src:<20} {e['raw_chars']:>8,} → {e['opt_chars']:>8,}  ({e['saved_pct']}% saved)")


# --- Input Resolution ---


def _resolve_json_input(data: str) -> str:
    """Resolve JSON input that might be a file path, a JSON-wrapped file ref, or raw JSON.

    Handles these cases from MCP tool overflow:
    - Raw JSON string: '{"key": "value"}' or '[...]'
    - Direct file path: '/path/to/file.txt'
    - JSON-wrapped file ref: '{"file": "/path/to/file.txt"}'
    - JSON with "result" key wrapping: '{"result": "..."}'
    """
    stripped = data.strip()

    # Case 1: Looks like a file path
    if stripped.startswith("/") and not stripped.startswith("//") and "\n" not in stripped:
        return _try_read_file(stripped)

    # Case 2: Try to detect JSON-wrapped file reference
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            # {"file": "/path/to/file.txt"}
            if "file" in obj and isinstance(obj["file"], str) and obj["file"].startswith("/"):
                return _try_read_file(obj["file"])
            # {"result": "<json string>"} — unwrap
            if "result" in obj and isinstance(obj["result"], str) and len(obj) == 1:
                inner = obj["result"].strip()
                # If the result is itself a file path
                if inner.startswith("/") and "\n" not in inner:
                    return _try_read_file(inner)
                return inner
    except json.JSONDecodeError:
        pass

    return stripped


def _try_read_file(path: str) -> str:
    """Try to read a file, return its content or raise a clear error."""
    p = Path(path.strip())
    if not p.exists():
        return json.dumps({"_error": f"File not found: {path}"})
    content = p.read_text(encoding="utf-8")
    # The file might contain a JSON wrapper like {"result": "..."}
    try:
        obj = json.loads(content)
        if isinstance(obj, dict) and "result" in obj and isinstance(obj["result"], str) and len(obj) == 1:
            return obj["result"]
    except json.JSONDecodeError:
        pass
    return content


# --- Tools ---


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
        int, Field(description="Max nesting depth for JSON before flattening (default 5)", ge=1, le=20),
    ] = 5,
    extract_metadata: Annotated[
        bool, Field(description="Include YAML frontmatter with page metadata (HTML only)")
    ] = False,
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
) -> str:
    """Fetch any URL and auto-optimize based on content type.

    For HTML: converts to clean markdown, stripping navigation, ads, and scripts.
    For JSON: returns a schema + sample by default for large arrays. Use the jsonpath
    parameter to drill into specific items or fields on follow-up calls.
    Dramatically reduces token usage compared to raw fetching.
    """
    try:
        response = await _fetch_raw(url)

        if _is_json_content(response):
            try:
                data = response.json()
            except json.JSONDecodeError:
                return _html_to_markdown(response.text, max_chars=max_chars)

            raw_chars = len(response.text)

            # Schema-first mode: if it's a large uniform array and the agent
            # hasn't asked for specific data yet, return schema + sample only.
            if not jsonpath and _should_use_schema_mode(data):
                summary = _build_schema_summary(data, max_depth=max_depth)
                result = json.dumps(summary, indent=2, ensure_ascii=False, default=str)
                if len(result) > max_chars:
                    result = result[:max_chars] + "\n\n... [truncated]"
                _log_savings(raw_chars, len(result), source=f"smart_fetch:{url[:60]}")
                return result

            # Full mode: agent is drilling in with JSONPath or data is small
            pruned = _prune_json(data, jsonpath=jsonpath, max_depth=max_depth)
            result = json.dumps(pruned, indent=2, ensure_ascii=False, default=str)
            if len(result) > max_chars:
                result = result[:max_chars] + "\n\n... [truncated]"
            _log_savings(raw_chars, len(result), source=f"smart_fetch:{url[:60]}")
            return result

        # HTML content — log savings too
        raw_chars = len(response.text)
        result = _html_to_markdown(
            response.text,
            max_chars=max_chars,
            extract_metadata=extract_metadata,
        )
        _log_savings(raw_chars, len(result), source=f"smart_fetch:{url[:60]}")
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
    max_results: Annotated[
        int, Field(description="Number of results to return", ge=1, le=20)
    ] = 10,
    region: Annotated[
        str, Field(description="Region code for results (e.g. 'us-en', 'wt-wt' for global)")
    ] = "wt-wt",
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
    """Fetch a page and return only the content matching a CSS selector.

    Use this to extract specific sections of a page (e.g. a pricing table,
    product description, or article body) to save maximum tokens.
    """
    try:
        from bs4 import BeautifulSoup

        response = await _fetch_raw(url)
        soup = BeautifulSoup(response.text, "html.parser")
        elements = soup.select(selector)

        if not elements:
            return f"No elements matched selector: {selector}"

        # Convert each matched element to markdown
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
    wait_ms: Annotated[
        int, Field(description="Milliseconds to wait after DOMContentLoaded", ge=0, le=120_000)
    ] = 3_000,
    timeout_ms: Annotated[
        int, Field(description="Navigation timeout in milliseconds", ge=1_000, le=120_000)
    ] = 30_000,
    headed: Annotated[
        bool,
        Field(description="Open a visible browser window for human-in-the-loop CAPTCHA/login"),
    ] = False,
    extract_metadata: Annotated[
        bool, Field(description="Include YAML frontmatter with page metadata")
    ] = False,
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
) -> str:
    """Fetch a JavaScript-rendered page with Playwright and return markdown.

    This is useful when a site blocks simple HTTP clients or requires client-side
    rendering. It does not bypass CAPTCHA; use headed mode to solve challenges
    manually, then let the tool extract the page.
    """
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
                html = await locator.evaluate_all(
                    "els => els.map(el => el.outerHTML).join('\\n\\n')"
                )
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
        Field(description=(
            "Raw JSON string to optimize, OR a file path to a JSON file. "
            "When an MCP tool response is too large and gets saved to a file, "
            "pass the file path here (e.g. '/path/to/tool-results/file.txt')."
        )),
    ],
    jsonpath: Annotated[
        str | None,
        Field(description="JSONPath expression to extract specific fields (e.g. '$[*].name', '$[?@.state==\"open\"]')"),
    ] = None,
    max_depth: Annotated[
        int, Field(description="Max nesting depth before flattening (default 5)", ge=1, le=20),
    ] = 5,
    max_chars: Annotated[
        int, Field(description="Maximum characters in output", ge=1000, le=100_000)
    ] = DEFAULT_MAX_CHARS,
) -> str:
    """Optimize any JSON payload to reduce token usage.

    Use this as a post-processing hook on output from other MCP tools
    (GitHub, Jira, Datadog, Confluence, etc.). It applies:
    - Schema-first mode for large arrays (returns structure + 2 samples)
    - API URL template stripping
    - Empty/null value removal
    - Repeated sub-object deduplication
    - Deep nesting flattening
    - JSONPath extraction for targeted drill-in

    Accepts either raw JSON or a file path. When MCP tool responses are too
    large and get saved to a file, just pass the file path directly.

    Typical workflow:
    1. Call another MCP tool (e.g. GitHub list_issues)
    2. If it returns JSON, pass it directly. If it was saved to a file, pass the file path.
    3. Get back a compact version; use jsonpath to drill into specifics
    """
    # Resolve file path — handle both direct paths and JSON-wrapped paths
    raw_json = _resolve_json_input(data)

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON — {e}"

    raw_chars = len(raw_json)

    # Schema-first for large arrays when not drilling in
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


# --- CLI for hook usage ---


def _cli_optimize() -> None:
    """CLI entrypoint: reads JSON from stdin, writes optimized JSON to stdout.

    Usage as a Claude Code hook or shell pipe:
        echo '<json>' | python server.py optimize [--jsonpath '$.x'] [--max-depth 5]
        cat response.json | python server.py optimize --jsonpath '$[*].name'
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="fetch-mcp optimize",
        description="Optimize JSON from stdin to reduce LLM token usage.",
    )
    parser.add_argument(
        "--jsonpath", default=None, help="JSONPath expression to extract specific fields"
    )
    parser.add_argument(
        "--max-depth", type=int, default=5, help="Max nesting depth before flattening"
    )
    # Parse only known args so "optimize" subcommand doesn't interfere
    args, _ = parser.parse_known_args(sys.argv[2:])

    raw = sys.stdin.read()
    if not raw.strip():
        print("Error: No input on stdin", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON — {e}", file=sys.stderr)
        sys.exit(1)

    raw_chars = len(raw)

    if not args.jsonpath and _should_use_schema_mode(data):
        result = _build_schema_summary(data, max_depth=args.max_depth)
    else:
        result = _prune_json(data, jsonpath=args.jsonpath, max_depth=args.max_depth)

    output = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    _log_savings(raw_chars, len(output), source="cli")
    print(output)


def _cli_smart_fetch() -> None:
    """CLI entrypoint: fetches a URL and writes optimized content to stdout.

    Usage:
        python server.py smart_fetch <url> [--jsonpath '$[*].name']
        python server.py smart_fetch <url> --max-depth 5 --max-chars 20000
    """
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        prog="fetch-mcp smart_fetch",
        description="Fetch a URL and auto-optimize HTML or JSON for LLM usage.",
    )
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument(
        "--jsonpath", default=None, help="JSONPath expression to extract specific fields"
    )
    parser.add_argument(
        "--max-depth", type=int, default=5, help="Max JSON nesting depth before flattening"
    )
    parser.add_argument(
        "--extract-metadata",
        action="store_true",
        help="Include YAML frontmatter with page metadata for HTML responses",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Maximum characters to output",
    )
    args = parser.parse_args(sys.argv[2:])

    result = asyncio.run(
        smart_fetch(
            args.url,
            jsonpath=args.jsonpath,
            max_depth=args.max_depth,
            extract_metadata=args.extract_metadata,
            max_chars=args.max_chars,
        )
    )
    print(result)


def _cli_browser_fetch() -> None:
    """CLI entrypoint: fetches a rendered page with Playwright."""
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(
        prog="fetch-mcp browser_fetch",
        description="Fetch a URL with Playwright/Chrome and return optimized markdown.",
    )
    parser.add_argument("url", help="URL to fetch")
    parser.add_argument(
        "--selector", default=None, help="CSS selector to extract from the rendered page"
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=3_000,
        help="Milliseconds to wait after DOMContentLoaded",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=30_000,
        help="Navigation timeout in milliseconds",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Open a visible browser window for manual CAPTCHA/login steps",
    )
    parser.add_argument(
        "--extract-metadata",
        action="store_true",
        help="Include YAML frontmatter with page metadata",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Maximum characters to output",
    )
    args = parser.parse_args(sys.argv[2:])

    result = asyncio.run(
        browser_fetch(
            args.url,
            selector=args.selector,
            wait_ms=args.wait_ms,
            timeout_ms=args.timeout_ms,
            headed=args.headed,
            extract_metadata=args.extract_metadata,
            max_chars=args.max_chars,
        )
    )
    print(result)


def _print_cli_help() -> None:
    print(
        """usage: python server.py [command] [options]

Commands:
  smart_fetch URL      Fetch a URL and auto-optimize HTML or JSON
  smart-fetch URL      Alias for smart_fetch
  browser_fetch URL    Fetch a rendered page with Playwright/Chrome
  browser-fetch URL    Alias for browser_fetch
  optimize            Optimize JSON from stdin
  report              Show cumulative savings report

Run `python server.py <command> --help` for command-specific options.
Run without a command to start the MCP stdio server.
"""
    )


# --- Entry point ---


def main():
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help", "help"}:
        _print_cli_help()
    elif len(sys.argv) > 1 and sys.argv[1] == "optimize":
        _cli_optimize()
    elif len(sys.argv) > 1 and sys.argv[1] in {"smart_fetch", "smart-fetch"}:
        _cli_smart_fetch()
    elif len(sys.argv) > 1 and sys.argv[1] in {"browser_fetch", "browser-fetch"}:
        _cli_browser_fetch()
    elif len(sys.argv) > 1 and sys.argv[1] == "report":
        _print_savings_report()
    else:
        mcp.run()


if __name__ == "__main__":
    main()
