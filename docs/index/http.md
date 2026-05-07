---
room: http
source_paths: [fetch_mcp/http.py]
architectural_health: normal
security_tier: normal
see_also: [server.md]
hot_paths: [_build_client, _fetch_raw, _get_ssl_ctx]
---

# fetch_mcp/http.py

DOES: HTTP client factory, SSL setup, Chrome executable detection, and shared constants. `_get_ssl_ctx` lazily initializes a `truststore.SSLContext` to fix macOS SSL errors with Homebrew Python. `_find_chrome_executable` walks an OS-specific candidate list before Playwright falls back to its bundled Chromium.
SYMBOLS:
- _get_ssl_ctx() -> ssl.SSLContext
- _build_client() -> httpx.AsyncClient
- _fetch_raw(url: str) -> httpx.Response
- _find_chrome_executable() -> str | None
- _is_json_content(response) -> bool
- _handle_error(e: Exception) -> str
- Constants: USER_AGENT, DEFAULT_TIMEOUT, DEFAULT_MAX_CHARS
DEPENDS: httpx, truststore
PATTERNS: lazy-init
USE WHEN: Changing HTTP timeout or redirect behavior; debugging SSL errors; adding a new Chrome/browser path candidate; changing the User-Agent string.
