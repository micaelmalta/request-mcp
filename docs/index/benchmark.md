---
room: benchmark
source_paths: [scripts/benchmark.py]
architectural_health: normal
security_tier: normal
see_also: [server.md, json_optimizer.md]
hot_paths: [benchmark_html, benchmark_json, main]
---

# scripts/benchmark.py

DOES: Measures token savings for HTML→Markdown and JSON optimization by fetching real URLs, counting tokens with tiktoken (cl100k_base), and printing comparison tables with cost estimates. Dev-only; not part of the pytest suite.
SYMBOLS:
- benchmark_html(name: str, url: str) -> dict | None
- benchmark_json(name: str, url: str) -> dict | None
- print_html_table(rows: list[dict]) -> int
- print_json_table(rows: list[dict]) -> int
- print_cost_summary(total_saved: int) -> None
- count_tokens(text: str) -> int
- fetch(url: str) -> httpx.Response
- main() -> None
DEPENDS: fetch_mcp.html, fetch_mcp.json_optimizer, httpx, tiktoken, truststore
PATTERNS: async-benchmark, token-counting
USE WHEN: Reproducing or updating the token savings figures in the README; verifying that a change to the pruning pipeline doesn't regress savings.
