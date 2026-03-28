import json
from server import _prune_json, _should_use_schema_mode, _build_schema_summary


def test_prune_removes_null_and_empty():
    data = {"a": None, "b": "", "c": [], "d": {}, "e": 1}
    result = _prune_json(data)
    assert result == {"e": 1}


def test_schema_mode_trigger():
    data = [{"id": i} for i in range(10)]
    assert _should_use_schema_mode(data) is True


def test_schema_summary_shape():
    data = [{"id": 1, "name": "x"}, {"id": 2, "name": "y"}]
    summary = _build_schema_summary(data)
    assert "_schema" in summary
    assert "_sample" in summary
    assert summary["_count"] == 2


def test_jsonpath_extraction():
    data = [{"id": 1}, {"id": 2}]
    result = _prune_json(data, jsonpath="$[*].id")
    assert result == [1, 2]
