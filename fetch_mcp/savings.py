from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

_SAVINGS_LOG = Path(
    os.environ.get(
        "REQUEST_MCP_SAVINGS_LOG",
        Path.home() / ".local" / "share" / "fetch-mcp" / "savings.jsonl",
    )
)


def _log_savings(raw_chars: int, opt_chars: int, source: str = "") -> None:
    """Append a savings entry to the JSONL log file."""
    try:
        _SAVINGS_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "raw_chars": raw_chars,
            "opt_chars": opt_chars,
            "saved_chars": raw_chars - opt_chars,
            "saved_pct": round((raw_chars - opt_chars) / raw_chars * 100, 1) if raw_chars else 0,
        }
        with open(_SAVINGS_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def _print_savings_report() -> None:
    """Print a summary of all logged savings."""
    if not _SAVINGS_LOG.exists():
        print(f"No savings logged yet. Log file: {_SAVINGS_LOG}")
        return

    entries = []
    with open(_SAVINGS_LOG) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if not entries:
        print("No savings entries found.")
        return

    total_raw = sum(e["raw_chars"] for e in entries)
    total_opt = sum(e["opt_chars"] for e in entries)
    total_saved = total_raw - total_opt
    total_pct = round(total_saved / total_raw * 100, 1) if total_raw else 0

    print("fetch-mcp savings report")
    print(f"Log: {_SAVINGS_LOG}")
    print(f"Entries: {len(entries)}")
    print()

    by_source: dict[str, dict] = {}
    for e in entries:
        src = e.get("source", "unknown") or "unknown"
        if src not in by_source:
            by_source[src] = {"count": 0, "raw": 0, "opt": 0}
        by_source[src]["count"] += 1
        by_source[src]["raw"] += e["raw_chars"]
        by_source[src]["opt"] += e["opt_chars"]

    header = f"{'Source':<30} {'Calls':>6} {'Raw chars':>12} {'Opt chars':>12} {'Saved':>12} {'%':>7}"
    sep = "-" * len(header)
    print(header)
    print(sep)
    for src, s in sorted(by_source.items()):
        saved = s["raw"] - s["opt"]
        pct = round(saved / s["raw"] * 100, 1) if s["raw"] else 0
        print(f"{src:<30} {s['count']:>6} {s['raw']:>12,} {s['opt']:>12,} {saved:>12,} {pct:>6.1f}%")
    print(sep)
    print(f"{'TOTAL':<30} {len(entries):>6} {total_raw:>12,} {total_opt:>12,} {total_saved:>12,} {total_pct:>6.1f}%")
    print()

    print(f"Last {min(10, len(entries))} entries:")
    for e in entries[-10:]:
        ts = e["ts"][:19].replace("T", " ")
        src = e.get("source", "")[:20]
        print(f"  {ts}  {src:<20} {e['raw_chars']:>8,} → {e['opt_chars']:>8,}  ({e['saved_pct']}% saved)")
