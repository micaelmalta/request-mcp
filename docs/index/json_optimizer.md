---
room: json_optimizer
source_paths: [fetch_mcp/json_optimizer.py]
architectural_health: normal
security_tier: normal
see_also: [server.md, tests.md, evals.md]
hot_paths: [_prune_json, _build_schema_summary, _should_use_schema_mode]
---

# fetch_mcp/json_optimizer.py

DOES: The full JSON pruning pipeline and schema-first mode. `_prune_json` runs five steps in order: JSONPath extraction, URL template stripping, null/empty removal, sub-object deduplication, and deep-nesting flattening. `_build_schema_summary` returns a compact schema + 2 sample items for large uniform arrays.
SYMBOLS:
- _prune_json(data: object, jsonpath: str | None, max_depth: int) -> object
- _clean(obj: object, current_depth: int, max_depth: int) -> object
- _dedup_array(items: list) -> list
- _flatten_dict(d: dict, prefix: str) -> dict
- _build_schema_summary(data: list[dict], max_depth: int) -> dict
- _should_use_schema_mode(data: object) -> bool
- _infer_type(v: object) -> str
- _is_api_url_template(v: str) -> bool
- _is_empty(v: object) -> bool
- _hashable(v: object) -> object
- Constants: _SCHEMA_THRESHOLD, _SENTINEL, _URL_TEMPLATE_RE
DEPENDS: jsonpath_ng.ext
PATTERNS: json-pruning-pipeline, schema-first
USE WHEN: Changing any pruning step; adjusting the schema-first threshold (`_SCHEMA_THRESHOLD = 5`); adding JSONPath behavior; writing tests for the optimizer.
