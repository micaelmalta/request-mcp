# Phase 3 — Auth Headers

**Parent plan:** [2026-05-06-features.md](2026-05-06-features.md)  
**Depends on:** Phase 2 (cache key must include headers)  
**Goal:** Add a `headers` parameter to `smart_fetch` and `browser_fetch` so callers can pass `Authorization`, cookies, or any custom header per call.

---

## Objective

Allow LLMs to pass arbitrary HTTP headers (most commonly `Authorization: Bearer <token>`) on a per-call basis to `smart_fetch` and `browser_fetch`. The cache key already accounts for headers (Phase 2), so cached responses are correctly scoped.

**Explicitly deferred:** Named env-var profiles, cookie jar persistence, header validation.

---

## Modified Files

- `fetch_mcp/http.py` — `_fetch_raw` gains `extra_headers: dict[str, str] | None`
- `fetch_mcp/server.py` — `smart_fetch` and `browser_fetch` gain `headers` parameter; thread headers through to `_fetch_raw` and Playwright `page.set_extra_http_headers`

---

## Interface Changes

### `_fetch_raw` (http.py)

```python
async def _fetch_raw(url: str, extra_headers: dict[str, str] | None = None) -> httpx.Response:
    async with _build_client() as client:
        response = await client.get(url, headers=extra_headers or {})
        response.raise_for_status()
        return response
```

### `smart_fetch` (server.py) — new parameter

```python
headers: Annotated[
    dict[str, str] | None,
    Field(description="Optional HTTP headers (e.g. {'Authorization': 'Bearer token'})"),
] = None
```

Headers are passed to `_fetch_raw` and also to the cache key via `cache.make_key(url, headers)`.

### `browser_fetch` (server.py) — new parameter

```python
headers: Annotated[
    dict[str, str] | None,
    Field(description="Optional HTTP headers injected into the browser context"),
] = None
```

In Playwright: `await page.set_extra_http_headers(headers or {})` before `page.goto`.

---

## Security Note

Headers are passed directly to the outbound request. The LLM caller is responsible for not leaking secrets in logs. `_log_savings` does **not** log header values — only URL prefix is included in the `source` field.

---

## Graceful Degradation

| Failure | Behaviour |
|---|---|
| Remote server rejects auth token | `_handle_error` returns `"Error: HTTP 401 — ..."` |
| Caller passes malformed header dict | Pydantic validation rejects at MCP layer before `_fetch_raw` is called |
| `page.set_extra_http_headers` raises | Caught by existing `browser_fetch` `except Exception` handler |

---

## Implementation Steps

- [ ] test(auth): write tests for _fetch_raw with extra_headers — assert header appears in outgoing request (httpx_mock)
- [ ] feat(http): add extra_headers parameter to _fetch_raw
- [ ] feat(server): add headers parameter to smart_fetch; pass to _fetch_raw and cache key
- [ ] feat(server): add headers parameter to browser_fetch; call page.set_extra_http_headers before page.goto
- [ ] test(auth): add smart_fetch test — header forwarded, cache keyed separately for different header values

---

## Test Annotations

### `tests/test_auth.py`

```python
@pytest.mark.asyncio
async def test_fetch_raw_sends_extra_headers(httpx_mock)
    # assert request.headers["Authorization"] == "Bearer test"

@pytest.mark.asyncio
async def test_smart_fetch_forwards_headers(httpx_mock)

@pytest.mark.asyncio
async def test_smart_fetch_cache_keyed_by_headers(httpx_mock)
    # same URL, different headers → two distinct cache entries → two network calls
```

---

## Success Criteria

- All Phase 1 and 2 tests still pass
- Auth header tests pass
- `headers=None` (default) produces identical behaviour to pre-Phase-3 calls
