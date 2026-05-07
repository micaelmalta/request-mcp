---
room: html
source_paths: [fetch_mcp/html.py]
architectural_health: normal
security_tier: normal
see_also: [server.md, http.md]
hot_paths: [_html_to_markdown]
---

# fetch_mcp/html.py

DOES: Converts raw HTML to clean markdown using the `html-to-markdown` Rust-backed library, strips YAML frontmatter unless `extract_metadata=True`, and truncates output to `max_chars`.
SYMBOLS:
- _html_to_markdown(html: str, max_chars: int, extract_metadata: bool) -> str
DEPENDS: fetch_mcp.http (DEFAULT_MAX_CHARS), html_to_markdown
PATTERNS: (none)
USE WHEN: Debugging HTML→Markdown output quality; handling html-to-markdown version differences (3.x returns ConversionResult, older returns str/dict); changing truncation behavior.
