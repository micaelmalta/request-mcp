---
room: evals
source_paths: [evals/run_evals.py]
architectural_health: normal
security_tier: normal
see_also: [server.md, tests.md]
hot_paths: [run_json_eval, main]
---

# evals/run_evals.py

DOES: Reproducible offline eval harness that runs JSON fixtures through the pruning pipeline and reports raw/pruned/schema char counts. Reads JSON fixtures from `evals/fixtures/json/` — no network calls required.
SYMBOLS:
- run_json_eval(file_path: Path) -> dict
- count_chars(s: str) -> int
- main() -> None
DEPENDS: server (_prune_json, _build_schema_summary, _should_use_schema_mode)
PATTERNS: fixture-driven-eval
USE WHEN: Adding new JSON test fixtures to verify pruning behavior without network access; checking savings regressions against static payloads.
