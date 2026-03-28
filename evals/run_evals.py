import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import _prune_json, _build_schema_summary, _should_use_schema_mode

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "json"


def count_chars(s: str) -> int:
    return len(s)


def run_json_eval(file_path: Path):
    raw = json.loads(file_path.read_text())
    raw_text = json.dumps(raw, indent=2)

    pruned = _prune_json(raw)
    pruned_text = json.dumps(pruned, indent=2)

    schema_text = pruned_text
    if _should_use_schema_mode(raw):
        schema = _build_schema_summary(raw)
        schema_text = json.dumps(schema, indent=2)

    return {
        "file": file_path.name,
        "raw_chars": count_chars(raw_text),
        "pruned_chars": count_chars(pruned_text),
        "schema_chars": count_chars(schema_text),
    }


def main():
    results = []
    for file in FIXTURE_DIR.glob("*.json"):
        results.append(run_json_eval(file))

    print("\nReproducible eval results:\n")
    for r in results:
        print(f"{r['file']}: raw={r['raw_chars']}, pruned={r['pruned_chars']}, schema={r['schema_chars']}")


if __name__ == "__main__":
    main()
