from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass

_MAX_SIZE = 200


@dataclass
class _CacheEntry:
    content: str
    raw_chars: int
    expires_at: float  # time.monotonic() deadline


class _Cache:
    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}

    def make_key(self, url: str, headers: dict[str, str] | None = None, **kwargs: object) -> str:
        payload = url + json.dumps({"headers": sorted((headers or {}).items()), **kwargs}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> _CacheEntry | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if time.monotonic() >= entry.expires_at:
            del self._store[key]
            return None
        return entry

    def set(self, key: str, entry: _CacheEntry) -> None:
        if len(self._store) >= _MAX_SIZE:
            now = time.monotonic()
            self._store = {k: v for k, v in self._store.items() if v.expires_at > now}
            if len(self._store) >= _MAX_SIZE:
                del self._store[next(iter(self._store))]
        self._store[key] = entry


_response_cache: _Cache = _Cache()
