"""Tests for fetch_mcp/cli.py — CLI subcommand dispatch."""

from __future__ import annotations

import io
import json
import sys

from fetch_mcp.cli import main


def _run_main(argv: list[str], stdin_text: str = "") -> tuple[str, str]:
    """Call main() with patched sys.argv and sys.stdin; return (stdout, stderr)."""
    old_argv = sys.argv
    old_stdin = sys.stdin
    sys.argv = ["fetch-mcp"] + argv
    sys.stdin = io.StringIO(stdin_text)
    try:
        main()
    except SystemExit:
        pass
    finally:
        sys.argv = old_argv
        sys.stdin = old_stdin


def test_cli_optimize_from_stdin(capsys):
    data = json.dumps({"a": None, "b": 1})
    _run_main(["optimize"], stdin_text=data)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "a" not in parsed  # None pruned
    assert parsed["b"] == 1


def test_cli_optimize_prunes_large_array_to_schema(capsys):
    data = json.dumps([{"id": i} for i in range(10)])
    _run_main(["optimize"], stdin_text=data)
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["_mode"] == "schema"
    assert parsed["_count"] == 10


def test_cli_optimize_with_jsonpath(capsys):
    data = json.dumps([{"id": 1}, {"id": 2}])
    _run_main(["optimize", "--jsonpath", "$[*].id"], stdin_text=data)
    out = capsys.readouterr().out
    assert json.loads(out) == [1, 2]


def test_cli_optimize_from_file(capsys, tmp_path):
    f = tmp_path / "data.json"
    f.write_text(json.dumps({"x": 1, "y": None}))
    _run_main(["optimize"], stdin_text=f.read_text())
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert "y" not in parsed
    assert parsed["x"] == 1


def test_cli_optimize_empty_stdin_prints_error(capsys):
    _run_main(["optimize"], stdin_text="   ")
    err = capsys.readouterr().err
    assert "No input on stdin" in err


def test_cli_report_prints_table(capsys, tmp_path, monkeypatch):
    log_path = tmp_path / "savings.jsonl"
    entry = {
        "ts": "2026-01-01T00:00:00+00:00",
        "source": "test",
        "raw_chars": 1000,
        "opt_chars": 400,
        "saved_chars": 600,
        "saved_pct": 60.0,
    }
    log_path.write_text(json.dumps(entry) + "\n")
    monkeypatch.setenv("REQUEST_MCP_SAVINGS_LOG", str(log_path))

    import importlib

    import fetch_mcp.savings as savings_mod

    importlib.reload(savings_mod)

    import fetch_mcp.cli as cli_mod

    monkeypatch.setattr(cli_mod, "_print_savings_report", savings_mod._print_savings_report)

    _run_main(["report"])
    out = capsys.readouterr().out
    assert "test" in out
    assert "1,000" in out or "1000" in out


def test_cli_help_prints_commands(capsys):
    _run_main(["--help"])
    out = capsys.readouterr().out
    assert "smart_fetch" in out
    assert "optimize" in out
