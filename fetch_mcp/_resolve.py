from __future__ import annotations

import json
from pathlib import Path


def _try_read_file(path: str) -> str:
    """Try to read a file, return its content or raise a clear error."""
    p = Path(path.strip())
    if not p.exists():
        return json.dumps({"_error": f"File not found: {path}"})
    content = p.read_text(encoding="utf-8")
    try:
        obj = json.loads(content)
        if isinstance(obj, dict) and "result" in obj and isinstance(obj["result"], str) and len(obj) == 1:
            return obj["result"]
    except json.JSONDecodeError:
        pass
    return content


def _resolve_json_input(data: str) -> str:
    """Resolve JSON input that might be a file path, a JSON-wrapped file ref, or raw JSON."""
    stripped = data.strip()

    if stripped.startswith("/") and not stripped.startswith("//") and "\n" not in stripped:
        return _try_read_file(stripped)

    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            if "file" in obj and isinstance(obj["file"], str) and obj["file"].startswith("/"):
                return _try_read_file(obj["file"])
            if "result" in obj and isinstance(obj["result"], str) and len(obj) == 1:
                inner = obj["result"].strip()
                if inner.startswith("/") and "\n" not in inner:
                    return _try_read_file(inner)
                return inner
    except json.JSONDecodeError:
        pass

    return stripped
