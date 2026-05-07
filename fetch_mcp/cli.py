"""fetch-mcp CLI entry points.

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
import sys

from fetch_mcp.json_optimizer import _build_schema_summary, _prune_json, _should_use_schema_mode
from fetch_mcp.savings import _log_savings, _print_savings_report


def _print_cli_help() -> None:
    print(
        """usage: fetch-mcp [command] [options]

Commands:
  smart_fetch URL      Fetch a URL and auto-optimize HTML or JSON
  smart-fetch URL      Alias for smart_fetch
  browser_fetch URL    Fetch a rendered page with Playwright/Chrome
  browser-fetch URL    Alias for browser_fetch
  optimize            Optimize JSON from stdin
  report              Show cumulative savings report

Run `fetch-mcp <command> --help` for command-specific options.
Run without a command to start the MCP stdio server.
"""
    )


def _cli_optimize() -> None:
    """CLI: reads JSON from stdin, writes optimized JSON to stdout."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="fetch-mcp optimize",
        description="Optimize JSON from stdin to reduce LLM token usage.",
    )
    parser.add_argument("--jsonpath", default=None)
    parser.add_argument("--max-depth", type=int, default=5)
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
    """CLI: fetches a URL and writes optimized content to stdout."""
    import argparse
    import asyncio

    from fetch_mcp.http import DEFAULT_MAX_CHARS
    from fetch_mcp.server import smart_fetch

    parser = argparse.ArgumentParser(
        prog="fetch-mcp smart_fetch",
        description="Fetch a URL and auto-optimize HTML or JSON for LLM usage.",
    )
    parser.add_argument("url")
    parser.add_argument("--jsonpath", default=None)
    parser.add_argument("--max-depth", type=int, default=5)
    parser.add_argument("--extract-metadata", action="store_true")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
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
    """CLI: fetches a rendered page with Playwright."""
    import argparse
    import asyncio

    from fetch_mcp.http import DEFAULT_MAX_CHARS
    from fetch_mcp.server import browser_fetch

    parser = argparse.ArgumentParser(
        prog="fetch-mcp browser_fetch",
        description="Fetch a URL with Playwright/Chrome and return optimized markdown.",
    )
    parser.add_argument("url")
    parser.add_argument("--selector", default=None)
    parser.add_argument("--wait-ms", type=int, default=3_000)
    parser.add_argument("--timeout-ms", type=int, default=30_000)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--extract-metadata", action="store_true")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
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


def _cli_pdf_fetch() -> None:
    """CLI: fetches a PDF URL and returns extracted text."""
    import argparse
    import asyncio

    from fetch_mcp.http import DEFAULT_MAX_CHARS
    from fetch_mcp.server import pdf_fetch

    parser = argparse.ArgumentParser(
        prog="fetch-mcp pdf_fetch",
        description="Fetch a PDF URL and return its text content.",
    )
    parser.add_argument("url")
    parser.add_argument("--pages", default=None, help="Page range, e.g. '1-5' or '3'")
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args(sys.argv[2:])

    result = asyncio.run(pdf_fetch(args.url, pages=args.pages, max_chars=args.max_chars))
    print(result)


def main() -> None:
    # Lazy import: only load the MCP server when actually starting it,
    # so `fetch-mcp optimize` doesn't pull in httpx/playwright/ddgs.
    if len(sys.argv) > 1 and sys.argv[1] in {"-h", "--help", "help"}:
        _print_cli_help()
    elif len(sys.argv) > 1 and sys.argv[1] == "optimize":
        _cli_optimize()
    elif len(sys.argv) > 1 and sys.argv[1] in {"smart_fetch", "smart-fetch"}:
        _cli_smart_fetch()
    elif len(sys.argv) > 1 and sys.argv[1] in {"browser_fetch", "browser-fetch"}:
        _cli_browser_fetch()
    elif len(sys.argv) > 1 and sys.argv[1] in {"pdf_fetch", "pdf-fetch"}:
        _cli_pdf_fetch()
    elif len(sys.argv) > 1 and sys.argv[1] == "report":
        _print_savings_report()
    else:
        from fetch_mcp.server import mcp

        mcp.run()
