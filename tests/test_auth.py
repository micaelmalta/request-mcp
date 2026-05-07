"""Tests for auth header forwarding in _fetch_raw and smart_fetch."""

from __future__ import annotations

import json

import pytest

from fetch_mcp.http import _fetch_raw
from fetch_mcp.server import smart_fetch


async def test_fetch_raw_sends_extra_headers(httpx_mock):
    httpx_mock.add_response(url="https://api.example.com/secure", json={"ok": True})
    await _fetch_raw("https://api.example.com/secure", extra_headers={"Authorization": "Bearer test-token"})
    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer test-token"


async def test_fetch_raw_no_extra_headers_still_works(httpx_mock):
    httpx_mock.add_response(url="https://api.example.com/open", json={"ok": True})
    response = await _fetch_raw("https://api.example.com/open")
    assert response.status_code == 200


async def test_smart_fetch_forwards_headers(httpx_mock):
    httpx_mock.add_response(url="https://api.example.com/auth", json={"data": "secret"})
    result = await smart_fetch("https://api.example.com/auth", headers={"Authorization": "Bearer mytoken"})
    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer mytoken"
    assert "data" in result


async def test_smart_fetch_cache_keyed_by_headers(httpx_mock):
    # Same URL, different auth tokens → two distinct cache entries → two network calls
    httpx_mock.add_response(url="https://api.example.com/keyed", json={"user": "alice"}, is_reusable=False)
    httpx_mock.add_response(url="https://api.example.com/keyed", json={"user": "bob"}, is_reusable=False)

    result1 = await smart_fetch(
        "https://api.example.com/keyed",
        use_cache=True,
        headers={"Authorization": "Bearer token-alice"},
    )
    result2 = await smart_fetch(
        "https://api.example.com/keyed",
        use_cache=True,
        headers={"Authorization": "Bearer token-bob"},
    )
    assert "alice" in result1
    assert "bob" in result2


async def test_smart_fetch_cache_hit_with_same_headers(httpx_mock):
    # Same URL + same headers → cache hit on second call (only one network request)
    httpx_mock.add_response(
        url="https://api.example.com/same-auth",
        json={"value": 42},
        is_reusable=False,
    )
    headers = {"Authorization": "Bearer shared-token"}
    result1 = await smart_fetch("https://api.example.com/same-auth", use_cache=True, headers=headers)
    result2 = await smart_fetch("https://api.example.com/same-auth", use_cache=True, headers=headers)
    assert result1 == result2
    assert "42" in result1


async def test_smart_fetch_none_headers_is_default(httpx_mock):
    httpx_mock.add_response(url="https://example.com/noauth", html="<p>public</p>")
    result = await smart_fetch("https://example.com/noauth", headers=None)
    assert "public" in result
