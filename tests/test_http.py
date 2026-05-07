"""Tests for fetch_mcp/http.py helpers."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from fetch_mcp.http import _find_chrome_executable, _handle_error, _is_json_content


def _mock_response(content_type: str) -> MagicMock:
    r = MagicMock()
    r.headers = {"content-type": content_type}
    return r


def test_is_json_content_true_for_application_json():
    assert _is_json_content(_mock_response("application/json")) is True


def test_is_json_content_true_for_application_json_with_charset():
    assert _is_json_content(_mock_response("application/json; charset=utf-8")) is True


def test_is_json_content_true_for_javascript():
    assert _is_json_content(_mock_response("application/javascript")) is True


def test_is_json_content_false_for_text_html():
    assert _is_json_content(_mock_response("text/html; charset=utf-8")) is False


def test_is_json_content_false_for_text_plain():
    assert _is_json_content(_mock_response("text/plain")) is False


def test_handle_error_timeout():
    e = httpx.TimeoutException("timed out")
    result = _handle_error(e)
    assert result.startswith("Error: Request timed out")


def test_handle_error_http_status():
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(404, request=request)
    e = httpx.HTTPStatusError("not found", request=request, response=response)
    result = _handle_error(e)
    assert "404" in result
    assert result.startswith("Error: HTTP 404")


def test_handle_error_generic():
    e = ValueError("something went wrong")
    result = _handle_error(e)
    assert "ValueError" in result
    assert "something went wrong" in result


def test_find_chrome_returns_none_when_no_chrome(monkeypatch):
    monkeypatch.delenv("REQUEST_MCP_CHROME_PATH", raising=False)
    monkeypatch.setattr(Path, "exists", lambda self: False)
    assert _find_chrome_executable() is None


def test_find_chrome_returns_path_when_env_set(monkeypatch, tmp_path):
    fake_chrome = tmp_path / "chrome"
    fake_chrome.touch()
    monkeypatch.setenv("REQUEST_MCP_CHROME_PATH", str(fake_chrome))
    result = _find_chrome_executable()
    assert result == str(fake_chrome)
