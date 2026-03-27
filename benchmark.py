"""Benchmark: compare raw HTML vs html-to-markdown token usage."""

import asyncio
import time

import html_to_markdown
import httpx
import tiktoken
import ssl

import truststore

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

URLS = [
    ("GitHub Blog", "https://github.blog/"),
    ("Hacker News", "https://news.ycombinator.com/"),
    ("MDN — JavaScript", "https://developer.mozilla.org/en-US/docs/Web/JavaScript"),
    ("BBC News", "https://www.bbc.com/news"),
    ("Rust Lang", "https://www.rust-lang.org/"),
    ("Go pkg — net/http", "https://pkg.go.dev/net/http"),
    ("Python docs — asyncio", "https://docs.python.org/3/library/asyncio.html"),
]

ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
enc = tiktoken.get_encoding("cl100k_base")  # GPT-4 / Claude approximation


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


async def fetch(url: str) -> str:
    async with httpx.AsyncClient(
        timeout=30.0,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        verify=ssl_ctx,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


async def benchmark_url(name: str, url: str) -> dict | None:
    try:
        html = await fetch(url)
    except Exception as e:
        print(f"  SKIP {name}: {e}")
        return None

    t0 = time.perf_counter()
    md = html_to_markdown.convert(html)
    convert_ms = (time.perf_counter() - t0) * 1000

    html_tokens = count_tokens(html)
    md_tokens = count_tokens(md)
    saved = html_tokens - md_tokens
    pct = (saved / html_tokens * 100) if html_tokens else 0

    return {
        "name": name,
        "html_chars": len(html),
        "md_chars": len(md),
        "html_tokens": html_tokens,
        "md_tokens": md_tokens,
        "saved_tokens": saved,
        "saved_pct": pct,
        "convert_ms": convert_ms,
    }


def print_table(rows: list[dict]) -> None:
    header = (
        f"{'Page':<30} {'HTML chars':>12} {'MD chars':>12} "
        f"{'HTML tokens':>12} {'MD tokens':>12} {'Saved':>12} {'%':>7} {'Time':>8}"
    )
    sep = "-" * len(header)
    print(f"\n{sep}\n{header}\n{sep}")

    total_html = total_md = 0
    for r in rows:
        total_html += r["html_tokens"]
        total_md += r["md_tokens"]
        print(
            f"{r['name']:<30} {r['html_chars']:>12,} {r['md_chars']:>12,} "
            f"{r['html_tokens']:>12,} {r['md_tokens']:>12,} "
            f"{r['saved_tokens']:>12,} {r['saved_pct']:>6.1f}% "
            f"{r['convert_ms']:>6.1f}ms"
        )

    total_saved = total_html - total_md
    total_pct = (total_saved / total_html * 100) if total_html else 0
    print(sep)
    print(
        f"{'TOTAL':<30} {'':>12} {'':>12} "
        f"{total_html:>12,} {total_md:>12,} "
        f"{total_saved:>12,} {total_pct:>6.1f}%"
    )
    print(sep)
    print(f"\nAt $3/M input tokens (Claude Sonnet), savings ≈ ${total_saved * 3 / 1_000_000:.4f} per batch")
    print(f"At $15/M input tokens (Claude Opus), savings ≈ ${total_saved * 15 / 1_000_000:.4f} per batch")


async def main() -> None:
    print("Fetching pages and comparing HTML vs Markdown token usage...\n")
    results = []
    for name, url in URLS:
        print(f"  Fetching {name}...")
        r = await benchmark_url(name, url)
        if r:
            results.append(r)

    if results:
        print_table(results)


if __name__ == "__main__":
    asyncio.run(main())
