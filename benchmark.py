"""Benchmark: compare raw vs fetch-mcp optimized token usage for HTML and JSON."""

import asyncio
import json
import time

import httpx
import tiktoken
import ssl

import truststore
from server import (
    _build_schema_summary,
    _html_to_markdown,
    _prune_json,
    _should_use_schema_mode,
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

HTML_URLS = [
    ("GitHub Blog", "https://github.blog/"),
    ("Hacker News", "https://news.ycombinator.com/"),
    ("MDN — JavaScript", "https://developer.mozilla.org/en-US/docs/Web/JavaScript"),
    ("BBC News", "https://www.bbc.com/news"),
    ("Rust Lang", "https://www.rust-lang.org/"),
    ("Go pkg — net/http", "https://pkg.go.dev/net/http"),
    ("Python docs — asyncio", "https://docs.python.org/3/library/asyncio.html"),
    ("Socket.dev — Axios compromise", "https://socket.dev/blog/hidden-blast-radius-of-the-axios-compromise"),
]

JSON_URLS = [
    ("GitHub API — repos", "https://api.github.com/orgs/python/repos?per_page=10"),
    ("JSONPlaceholder — posts", "https://jsonplaceholder.typicode.com/posts"),
    ("JSONPlaceholder — users", "https://jsonplaceholder.typicode.com/users"),
    ("JSONPlaceholder — comments", "https://jsonplaceholder.typicode.com/comments?postId=1"),
]

ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 / Claude approximation


def count_tokens(text: str) -> int:
    if not isinstance(text, str):
        text = str(text)
    return len(enc.encode(text))


async def fetch(url: str) -> httpx.Response:
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        verify=ssl_ctx,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp


async def benchmark_html(name: str, url: str) -> dict | None:
    try:
        resp = await fetch(url)
        html = resp.text
    except Exception as e:
        print(f"  SKIP {name}: {e}")
        return None

    t0 = time.perf_counter()
    # html-to-markdown 3.x returns a dict; _html_to_markdown matches server.py / smart_fetch.
    md = _html_to_markdown(html, max_chars=10_000_000)
    convert_ms = (time.perf_counter() - t0) * 1000

    raw_tokens = count_tokens(html)
    opt_tokens = count_tokens(md)
    saved = raw_tokens - opt_tokens
    pct = (saved / raw_tokens * 100) if raw_tokens else 0

    return {
        "name": name,
        "type": "HTML",
        "raw_chars": len(html),
        "opt_chars": len(md),
        "raw_tokens": raw_tokens,
        "opt_tokens": opt_tokens,
        "saved_tokens": saved,
        "saved_pct": pct,
        "convert_ms": convert_ms,
    }


async def benchmark_json(name: str, url: str) -> dict | None:
    try:
        resp = await fetch(url)
        data = resp.json()
    except Exception as e:
        print(f"  SKIP {name}: {e}")
        return None

    raw_text = json.dumps(data, indent=2, ensure_ascii=False)

    t0 = time.perf_counter()
    pruned = _prune_json(data, max_depth=5)
    pruned_text = json.dumps(pruned, indent=2, ensure_ascii=False, default=str)
    convert_ms = (time.perf_counter() - t0) * 1000

    raw_tokens = count_tokens(raw_text)
    opt_tokens = count_tokens(pruned_text)
    saved = raw_tokens - opt_tokens
    pct = (saved / raw_tokens * 100) if raw_tokens else 0

    # Also compute schema-mode savings
    schema_tokens = opt_tokens  # fallback if schema mode doesn't apply
    if _should_use_schema_mode(data):
        summary = _build_schema_summary(data, max_depth=5)
        schema_text = json.dumps(summary, indent=2, ensure_ascii=False, default=str)
        schema_tokens = count_tokens(schema_text)

    return {
        "name": name,
        "type": "JSON",
        "raw_chars": len(raw_text),
        "opt_chars": len(pruned_text),
        "raw_tokens": raw_tokens,
        "opt_tokens": opt_tokens,
        "schema_tokens": schema_tokens,
        "saved_tokens": saved,
        "saved_pct": pct,
        "convert_ms": convert_ms,
    }


def print_html_table(rows: list[dict]) -> int:
    header = (
        f"{'Page':<30} {'Raw tokens':>12} {'Opt tokens':>12} {'Saved':>12} {'%':>7} {'Time':>8}"
    )
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print(f"  HTML → Markdown")
    print(f"{'=' * len(header)}")
    print(f"{header}\n{sep}")

    total_raw = total_opt = 0
    for r in rows:
        total_raw += r["raw_tokens"]
        total_opt += r["opt_tokens"]
        print(
            f"{r['name']:<30} {r['raw_tokens']:>12,} {r['opt_tokens']:>12,} "
            f"{r['saved_tokens']:>12,} {r['saved_pct']:>6.1f}% "
            f"{r['convert_ms']:>6.1f}ms"
        )

    total_saved = total_raw - total_opt
    total_pct = (total_saved / total_raw * 100) if total_raw else 0
    print(sep)
    print(
        f"{'TOTAL':<30} {total_raw:>12,} {total_opt:>12,} "
        f"{total_saved:>12,} {total_pct:>6.1f}%"
    )
    print(sep)
    return total_saved


def print_json_table(rows: list[dict]) -> int:
    header = (
        f"{'Endpoint':<30} {'Raw tokens':>12} {'Pruned':>12} {'Schema':>12} {'Best %':>8}"
    )
    sep = "-" * len(header)
    print(f"\n{'=' * len(header)}")
    print(f"  JSON Optimization (Pruned vs Schema-first)")
    print(f"{'=' * len(header)}")
    print(f"{header}\n{sep}")

    total_raw = total_best = 0
    for r in rows:
        raw = r["raw_tokens"]
        pruned = r["opt_tokens"]
        schema = r.get("schema_tokens", pruned)
        best = min(pruned, schema)
        total_raw += raw
        total_best += best
        pct = ((raw - best) / raw * 100) if raw else 0
        schema_str = f"{schema:>12,}" if schema != pruned else f"{'n/a':>12}"
        print(
            f"{r['name']:<30} {raw:>12,} {pruned:>12,} {schema_str} {pct:>7.1f}%"
        )

    total_saved = total_raw - total_best
    total_pct = (total_saved / total_raw * 100) if total_raw else 0
    print(sep)
    print(
        f"{'TOTAL':<30} {total_raw:>12,} {'':>12} {'':>12} {total_pct:>7.1f}%"
    )
    print(f"  Best-case tokens: {total_best:,} (saved {total_saved:,})")
    print(sep)
    return total_saved


def print_cost_summary(total_saved: int) -> None:
    print(f"\nAt $3/M input tokens (Claude Sonnet), savings ≈ ${total_saved * 3 / 1_000_000:.4f} per batch")
    print(f"At $15/M input tokens (Claude Opus), savings ≈ ${total_saved * 15 / 1_000_000:.4f} per batch")


async def main() -> None:
    print("fetch-mcp benchmark: Raw vs Optimized token usage\n")

    # HTML benchmarks
    html_results = []
    for name, url in HTML_URLS:
        print(f"  Fetching {name}...")
        r = await benchmark_html(name, url)
        if r:
            html_results.append(r)

    # JSON benchmarks
    json_results = []
    for name, url in JSON_URLS:
        print(f"  Fetching {name}...")
        r = await benchmark_json(name, url)
        if r:
            json_results.append(r)

    total_saved = 0
    if html_results:
        total_saved += print_html_table(html_results)
    if json_results:
        total_saved += print_json_table(json_results)

    if total_saved:
        print_cost_summary(total_saved)


if __name__ == "__main__":
    asyncio.run(main())
