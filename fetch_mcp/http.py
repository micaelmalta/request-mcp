from __future__ import annotations

import os
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_CHARS = 20_000

_ssl_ctx = None


def _get_ssl_ctx():
    """System certificate store (fixes macOS SSL issues with Homebrew Python)."""
    global _ssl_ctx
    if _ssl_ctx is None:
        import ssl

        import truststore

        _ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return _ssl_ctx


def _build_client():
    """Build a configured async HTTP client."""
    import httpx

    return httpx.AsyncClient(
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        verify=_get_ssl_ctx(),
    )


def _find_chrome_executable() -> str | None:
    """Return a local Chrome/Chromium executable if one is installed."""
    candidates = [
        os.environ.get("REQUEST_MCP_CHROME_PATH"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    ]
    return next((path for path in candidates if path and Path(path).exists()), None)


async def _fetch_raw(url: str):
    """Fetch a URL and return the raw response."""
    async with _build_client() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response


def _is_json_content(response) -> bool:
    """Detect if a response contains JSON content."""
    ct = response.headers.get("content-type", "")
    return "json" in ct or "javascript" in ct


def _handle_error(e: Exception) -> str:
    """Format errors consistently."""
    import httpx

    if isinstance(e, httpx.TimeoutException):
        return f"Error: Request timed out — {e}"
    if isinstance(e, httpx.HTTPStatusError):
        return f"Error: HTTP {e.response.status_code} — {e}"
    return f"Error: {type(e).__name__} — {e}"
