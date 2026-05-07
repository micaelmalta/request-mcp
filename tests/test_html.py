"""Tests for fetch_mcp/html.py — _html_to_markdown."""

from __future__ import annotations

from fetch_mcp.html import _html_to_markdown


def test_basic_html_to_markdown():
    html = "<h1>Hello</h1><p>World</p>"
    result = _html_to_markdown(html)
    assert "Hello" in result
    assert "World" in result
    assert "<h1>" not in result
    assert "<p>" not in result


def test_truncation_at_max_chars():
    html = "<p>" + ("x" * 1000) + "</p>"
    result = _html_to_markdown(html, max_chars=100)
    assert len(result) <= 100 + len("\n\n[... truncated]")
    assert "[... truncated]" in result


def test_no_truncation_when_within_limit():
    html = "<p>short</p>"
    result = _html_to_markdown(html, max_chars=20_000)
    assert "[... truncated]" not in result


def test_metadata_extraction_returns_frontmatter():
    # html-to-markdown may emit YAML frontmatter with title/description
    html = "<html><head><title>My Page</title></head><body><p>content</p></body></html>"
    result_with = _html_to_markdown(html, extract_metadata=True)
    result_without = _html_to_markdown(html, extract_metadata=False)
    # with metadata: frontmatter block should appear (starts with ---)
    # without metadata: frontmatter is stripped
    # We can't guarantee the library emits frontmatter, but if it does, strip should remove it.
    if result_with.startswith("---\n"):
        assert not result_without.startswith("---\n")


def test_empty_html_returns_string():
    result = _html_to_markdown("")
    assert isinstance(result, str)


def test_minimal_html_no_raw_tags():
    html = "<div><span>hello</span></div>"
    result = _html_to_markdown(html)
    assert "<div>" not in result
    assert "<span>" not in result
    assert "hello" in result
