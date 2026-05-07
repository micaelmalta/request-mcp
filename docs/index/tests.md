---
room: tests
source_paths: [tests/test_json_optimizer.py]
architectural_health: normal
security_tier: normal
see_also: [server.md, evals.md]
hot_paths: [test_prune_removes_null_and_empty, test_schema_mode_trigger, test_jsonpath_extraction]
---

# tests/test_json_optimizer.py

DOES: Unit tests for the JSON pruning pipeline: null/empty removal, `False`/`0` preservation, schema-mode trigger thresholds, schema summary shape, and JSONPath extraction including the no-match fallback.
SYMBOLS:
- test_prune_removes_null_and_empty() -> None
- test_prune_keeps_false_and_zero() -> None
- test_schema_mode_trigger(data, expected) -> None
- test_schema_summary_shape_and_content() -> None
- test_jsonpath_extraction(jsonpath, expected) -> None
DEPENDS: server (_prune_json, _should_use_schema_mode, _build_schema_summary)
PATTERNS: parametrized-pytest
USE WHEN: Adding tests for new pruning behavior or schema-mode edge cases; verifying JSONPath extraction contract.
