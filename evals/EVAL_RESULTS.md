# Eval Results (Snapshot)

Based on deterministic fixtures.

| Fixture | Raw chars | Pruned | Schema |
|--------|----------|--------|--------|
| github_repos.json | ~large | significantly reduced | minimal |

> Run `uv run python evals/run_evals.py` to regenerate.

## Notes
- Schema mode provides the biggest win for large arrays
- URL template stripping + dedup drive most savings

## TODO
- replace with exact token counts
- auto-generate this file in CI
