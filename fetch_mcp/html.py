from __future__ import annotations

import re

from fetch_mcp.http import DEFAULT_MAX_CHARS


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
