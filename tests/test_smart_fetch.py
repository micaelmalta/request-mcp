"""Tests for smart_fetch MCP tool — mocked HTTP via pytest-httpx."""

from __future__ import annotations

import json

from fetch_mcp.server import smart_fetch


async def test_smart_fetch_html_response(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/",
        html="<h1>Hello</h1><p>World</p>",
    )
    result = await smart_fetch("https://example.com/")
    assert isinstance(result, str)
    assert "Hello" in result
    assert "<h1>" not in result


async def test_smart_fetch_json_small_response(httpx_mock):
    httpx_mock.add_response(
        url="https://api.example.com/item",
        json={"id": 1, "name": "test"},
    )
    result = await smart_fetch("https://api.example.com/item")
    parsed = json.loads(result)
    assert parsed["id"] == 1


async def test_smart_fetch_json_schema_mode_for_large_array(httpx_mock):
    data = [{"id": i, "name": f"item{i}"} for i in range(10)]
    httpx_mock.add_response(
        url="https://api.example.com/items",
        json=data,
    )
    result = await smart_fetch("https://api.example.com/items")
    parsed = json.loads(result)
    assert parsed.get("_mode") == "schema"
    assert parsed.get("_count") == 10


async def test_smart_fetch_jsonpath_drills_in(httpx_mock):
    httpx_mock.add_response(
        url="https://api.example.com/list",
        json=[{"id": 1, "name": "a"}, {"id": 2, "name": "b"}],
    )
    result = await smart_fetch("https://api.example.com/list", jsonpath="$[*].id")
    parsed = json.loads(result)
    assert parsed == [1, 2]


async def test_smart_fetch_http_error_returns_error_string(httpx_mock):
    httpx_mock.add_response(
        url="https://api.example.com/notfound",
        status_code=404,
        text="Not Found",
    )
    result = await smart_fetch("https://api.example.com/notfound")
    assert result.startswith("Error:")
    assert "404" in result


async def test_smart_fetch_logs_savings(httpx_mock, tmp_path, monkeypatch):
    log_path = tmp_path / "savings.jsonl"
    monkeypatch.setenv("REQUEST_MCP_SAVINGS_LOG", str(log_path))

    import importlib

    import fetch_mcp.savings as savings_mod

    importlib.reload(savings_mod)

    import fetch_mcp.server as server_mod

    monkeypatch.setattr(server_mod, "_log_savings", savings_mod._log_savings)

    httpx_mock.add_response(
        url="https://example.com/log",
        html="<p>" + "x" * 500 + "</p>",
    )
    await smart_fetch("https://example.com/log")

    assert log_path.exists()
    line = log_path.read_text().strip()
    assert line
    entry = json.loads(line)
    assert entry["raw_chars"] > 0
