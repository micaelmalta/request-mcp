# Phase 2 — In-Process TTL Cache

**Parent plan:** [2026-05-06-features.md](2026-05-06-features.md)  
**Depends on:** Phase 1 (test suite must be green)  
**Goal:** Add a per-process TTL cache to `smart_fetch` (and `css_query`) so repeated calls within a session return instantly without network I/O.

---

## Objective

Cache successful `smart_fetch` and `css_query` responses in memory with a configurable TTL (default 1800 s / 30 min). Cache key includes URL + sorted headers so auth variance is handled. Cache hits still call `_log_savings` to log the savings.

**Explicitly deferred:** `browser_fetch` caching (JS-rendered pages are more likely to change; defer until there's a real use case), disk/SQLite persistence.

---

## New Files

- `fetch_mcp/cache.py` — `_CacheEntry`, `_Cache`, module-level `_response_cache`

---

## Modified Files

- `fetch_mcp/http.py` — `_fetch_raw` gains an optional `cache: _Cache | None` parameter
- `fetch_mcp/server.py` — `smart_fetch` and `css_query` pass `_response_cache` + `ttl` parameter

---

## Interface: `fetch_mcp/cache.py`

```python
@dataclass
class _CacheEntry:
    content: str          # already-processed output (markdown or JSON string)
    raw_chars: int        # for savings logging
    expires_at: float     # time.monotonic() deadline

class _Cache:
    def get(self, key: str) -> _CacheEntry | None: ...
    def set(self, key: str, entry: _CacheEntry) -> None: ...
    def make_key(self, url: str, headers: dict[str, str] | None = None) -> str: ...
    # make_key: SHA-256(url + json.dumps(sorted(headers or {})))
    # get: returns None if expired (lazy eviction)
    # set: stores entry; evicts all expired entries if len > _MAX_SIZE (default 200)

_response_cache: _Cache  # module-level singleton
```

`_Cache` uses only `hashlib`, `time`, `json`, `dataclasses` (all stdlib).

---

## New Parameter on `smart_fetch` and `css_query`

```python
use_cache: Annotated[bool, Field(description="Return cached response if available (default True)")] = True
ttl: Annotated[int, Field(description="Cache TTL in seconds (default 1800)", ge=60, le=86400)] = 1800
```

Cache is **opt-out** (`use_cache=True` by default) because the primary use case is reducing redundant fetches in a session.

---

## Cache Hit Flow

1. `smart_fetch` computes cache key from `(url, headers=None)` at this phase.
2. If hit: return `entry.content` immediately; call `_log_savings(entry.raw_chars, len(entry.content), source="cache_hit:...")`.
3. If miss: fetch normally, then `cache.set(key, _CacheEntry(...))`.

---

## Graceful Degradation

| Failure | Behaviour |
|---|---|
| `_Cache.get` raises | Caught, treated as cache miss, fetch proceeds normally |
| `_Cache.set` raises | Caught, logged to stderr at DEBUG level, result returned normally |
| TTL=0 effectively | Not allowed by `ge=60` validator |

---

## Implementation Steps

- [ ] test(cache): write tests for _Cache.get, _Cache.set, _Cache.make_key, TTL expiry, and max-size eviction
- [ ] feat(cache): implement fetch_mcp/cache.py with _CacheEntry, _Cache, and _response_cache singleton
- [ ] feat(server): add use_cache and ttl parameters to smart_fetch; integrate _response_cache on hit and miss paths
- [ ] feat(server): add use_cache and ttl parameters to css_query; integrate _response_cache
- [ ] test(smart_fetch): add cache-hit test — second call to same URL does not trigger httpx_mock

---

## Test Annotations

### `tests/test_cache.py`

```python
def test_cache_miss_returns_none()
def test_cache_hit_returns_entry()
def test_cache_entry_expires_after_ttl(monkeypatch)  # monkeypatch time.monotonic
def test_cache_evicts_expired_on_overflow()
def test_make_key_stable_for_same_url()
def test_make_key_differs_for_different_headers()
```

### Addition to `tests/test_smart_fetch.py`

```python
@pytest.mark.asyncio
async def test_smart_fetch_cache_hit_skips_network(httpx_mock)
    # call smart_fetch twice with same URL
    # httpx_mock configured for 1 call; second call must NOT raise "unexpected request"
```

---

## Success Criteria

- All Phase 1 tests still pass
- Cache tests pass
- `use_cache=False` bypasses cache completely (confirmed by test)
- Cache hit logged as `cache_hit:` in savings JSONL
