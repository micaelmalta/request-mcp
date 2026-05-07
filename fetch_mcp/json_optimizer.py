from __future__ import annotations

import json
import re

from jsonpath_ng.ext import parse as jsonpath_parse

_URL_TEMPLATE_RE = re.compile(r"\{[/+?]?[^}]+\}")
_SCHEMA_THRESHOLD = 5
_SENTINEL = object()


def _is_api_url_template(v: str) -> bool:
    """Detect templated API URLs like 'https://api.github.com/repos/x/y/issues{/number}'."""
    return v.startswith(("http://", "https://")) and bool(_URL_TEMPLATE_RE.search(v))


def _is_empty(v: object) -> bool:
    """Check if a value is 'empty' and should be pruned."""
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, (list, dict)) and len(v) == 0:
        return True
    return False


def _hashable(v: object) -> object:
    """Make a value hashable for set comparison."""
    if isinstance(v, (list, dict)):
        return json.dumps(v, sort_keys=True, default=str)
    return v


def _flatten_dict(d: dict, prefix: str = "") -> dict:
    """Flatten nested dict into dot-notation keys."""
    items: dict = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            items.update(_flatten_dict(v, key))
        elif not _is_empty(v):
            items[key] = v
    return items


def _clean(obj: object, current_depth: int, max_depth: int) -> object:
    """Recursively clean a JSON value."""
    if isinstance(obj, dict):
        if current_depth >= max_depth:
            return _flatten_dict(obj)
        cleaned = {}
        for k, v in obj.items():
            if isinstance(v, str) and _is_api_url_template(v):
                continue
            v = _clean(v, current_depth + 1, max_depth)
            if not _is_empty(v):
                cleaned[k] = v
        return cleaned
    if isinstance(obj, list):
        cleaned = [_clean(item, current_depth, max_depth) for item in obj]
        return [item for item in cleaned if not _is_empty(item)]
    return obj


def _dedup_array(items: list) -> list:
    """Deduplicate repeated sub-objects in an array of dicts."""
    if not items or not all(isinstance(i, dict) for i in items):
        return items

    all_keys = set()
    for item in items:
        all_keys.update(item.keys())

    uniform: dict[str, object] = {}
    for key in list(all_keys):
        values = [item.get(key, _SENTINEL) for item in items]
        non_missing = [v for v in values if v is not _SENTINEL]
        if (
            len(non_missing) == len(items)
            and all(not isinstance(v, (dict, list)) for v in non_missing)
            and len(set(_hashable(v) for v in non_missing)) == 1
        ):
            uniform[key] = non_missing[0]

    dict_registry: dict[str, tuple[str, object]] = {}

    for item in items:
        for key, val in item.items():
            if not isinstance(val, dict) or key in uniform:
                continue
            fp = json.dumps(val, sort_keys=True, default=str)
            if fp not in dict_registry:
                dict_registry[fp] = (key, val)

    dup_fps: dict[str, str] = {}
    fp_counts: dict[str, int] = {}
    for item in items:
        for key, val in item.items():
            if isinstance(val, dict):
                fp = json.dumps(val, sort_keys=True, default=str)
                fp_counts[fp] = fp_counts.get(fp, 0) + 1

    for fp, count in fp_counts.items():
        if count > 1 and fp in dict_registry:
            ref_name, _ = dict_registry[fp]
            dup_fps[fp] = ref_name

    if not uniform and not dup_fps:
        return items

    result_items = []
    for item in items:
        new_item = {}
        for k, v in item.items():
            if k in uniform:
                continue
            if isinstance(v, dict):
                fp = json.dumps(v, sort_keys=True, default=str)
                if fp in dup_fps:
                    new_item[k] = f"→ (same as _common.{dup_fps[fp]})"
                    continue
            new_item[k] = v
        result_items.append(new_item)

    wrapper: dict[str, object] = {}
    if uniform:
        wrapper["_common_values"] = uniform
    if dup_fps:
        refs: dict[str, object] = {}
        for fp, ref_name in dup_fps.items():
            _, val = dict_registry[fp]
            refs[ref_name] = val
        wrapper["_common"] = refs
    wrapper["items"] = result_items
    return wrapper  # type: ignore[return-value]


def _prune_json(data: object, jsonpath: str | None = None, max_depth: int = 5) -> object:
    """Aggressively prune a JSON object to minimise token usage.

    Pipeline (in order):
    1. JSONPath extraction — if provided, narrow to matching subtree first.
    2. Strip API URL templates — keys whose values are templated URLs (e.g. forks_url).
    3. Remove empty / null / false-boolean values.
    4. Deduplicate repeated sub-objects across an array.
    5. Flatten dicts beyond max_depth with dot-notation keys.
    """
    if jsonpath:
        expr = jsonpath_parse(jsonpath)
        matches = expr.find(data)
        if not matches:
            return {"_info": "No matches for JSONPath expression", "jsonpath": jsonpath}
        if len(matches) == 1:
            data = matches[0].value
        else:
            data = [m.value for m in matches]

    data = _clean(data, current_depth=0, max_depth=max_depth)

    if isinstance(data, list):
        data = _dedup_array(data)

    return data


def _infer_type(v: object) -> str:
    """Return a concise type descriptor for a JSON value."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        if len(v) > 80:
            return "string(long)"
        return "string"
    if isinstance(v, list):
        if not v:
            return "[]"
        inner = _infer_type(v[0])
        return f"[{inner}, ...{len(v)}]"
    if isinstance(v, dict):
        return f"object({len(v)} keys)"
    return type(v).__name__


def _should_use_schema_mode(data: object) -> bool:
    """Decide whether to use schema-first mode for this data."""
    if not isinstance(data, list):
        return False
    if len(data) < _SCHEMA_THRESHOLD:
        return False
    if not all(isinstance(item, dict) for item in data):
        return False
    return True


def _build_schema_summary(data: list[dict], max_depth: int = 5) -> dict:
    """Build a schema-only summary of a uniform JSON array."""
    pruned_first = _prune_json(data[0], max_depth=max_depth)
    schema: dict[str, str] = {}
    if isinstance(pruned_first, dict):
        for k, v in pruned_first.items():
            schema[k] = _infer_type(v)

    sample_count = min(2, len(data))
    sample = [_prune_json(item, max_depth=max_depth) for item in data[:sample_count]]

    return {
        "_mode": "schema",
        "_count": len(data),
        "_schema": schema,
        "_sample": sample,
        "_hint": (
            f"Returned schema + {sample_count} sample items out of {len(data)}. "
            "Use the jsonpath parameter to fetch specific items or fields. "
            "Examples: '$[0:5]' (first 5 items), '$[*].name' (all names), "
            "'$[?@.id==42]' (item with id 42)."
        ),
    }
