"""Tests for fetch_mcp/cache.py — _Cache TTL store."""

from __future__ import annotations

import time

from fetch_mcp.cache import _Cache, _CacheEntry


def test_cache_miss_returns_none():
    c = _Cache()
    assert c.get("nonexistent") is None


def test_cache_hit_returns_entry():
    c = _Cache()
    entry = _CacheEntry(content="hello", raw_chars=100, expires_at=time.monotonic() + 60)
    c.set("k", entry)
    result = c.get("k")
    assert result is entry


def test_cache_entry_expires_after_ttl(monkeypatch):
    c = _Cache()
    entry = _CacheEntry(content="hello", raw_chars=100, expires_at=time.monotonic() - 1)
    c.set("k", entry)
    assert c.get("k") is None


def test_cache_evicts_expired_on_overflow(monkeypatch):
    c = _Cache()
    # Fill cache beyond _MAX_SIZE with expired entries
    past = time.monotonic() - 1
    for i in range(201):
        c.set(f"key{i}", _CacheEntry(content="x", raw_chars=1, expires_at=past))
    # Add one fresh entry — triggers eviction sweep
    c.set("fresh", _CacheEntry(content="y", raw_chars=1, expires_at=time.monotonic() + 60))
    # All expired entries should be gone, fresh one survives
    assert c.get("fresh") is not None
    assert c.get("key0") is None


def test_make_key_stable_for_same_url():
    c = _Cache()
    k1 = c.make_key("https://example.com")
    k2 = c.make_key("https://example.com")
    assert k1 == k2


def test_make_key_stable_regardless_of_header_order():
    c = _Cache()
    k1 = c.make_key("https://example.com", {"Authorization": "Bearer x", "X-Foo": "bar"})
    k2 = c.make_key("https://example.com", {"X-Foo": "bar", "Authorization": "Bearer x"})
    assert k1 == k2


def test_make_key_differs_for_different_headers():
    c = _Cache()
    k1 = c.make_key("https://example.com", {"Authorization": "Bearer token1"})
    k2 = c.make_key("https://example.com", {"Authorization": "Bearer token2"})
    assert k1 != k2


def test_make_key_differs_for_different_urls():
    c = _Cache()
    assert c.make_key("https://a.com") != c.make_key("https://b.com")


def test_make_key_none_headers_same_as_empty():
    c = _Cache()
    assert c.make_key("https://example.com", None) == c.make_key("https://example.com", {})
