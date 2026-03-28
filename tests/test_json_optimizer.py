import pytest
from server import _prune_json, _should_use_schema_mode, _build_schema_summary


def test_prune_removes_null_and_empty():
    data = {"a": None, "b": "", "c": [], "d": {}, "e": 1}
    result = _prune_json(data)
    assert result == {"e": 1}


def test_prune_keeps_false_and_zero():
    """_is_empty does not prune False or 0 — only None, empty string/list/dict."""
    data = {"a": False, "b": 0, "c": None}
    result = _prune_json(data)
    assert result == {"a": False, "b": 0}


@pytest.mark.parametrize(
    "data, expected",
    [
        ([{"id": i} for i in range(10)], True),
        ([{"id": i} for i in range(5)], True),
        ([{"id": i} for i in range(4)], False),
        ([], False),
        ([1, 2, 3, 4, 5], False),
        ({"a": 1}, False),
    ],
)
def test_schema_mode_trigger(data, expected):
    assert _should_use_schema_mode(data) is expected


def test_schema_summary_shape_and_content():
    data = [{"id": 1, "name": "x"}, {"id": 2, "name": "y"}]
    summary = _build_schema_summary(data)

    assert summary["_mode"] == "schema"
    assert summary["_count"] == 2
    assert summary["_schema"] == {"id": "int", "name": "string"}
    assert summary["_sample"] == data
    assert "_hint" in summary


@pytest.mark.parametrize(
    "jsonpath, expected",
    [
        ("$[*].id", [1, 2]),
        ("$[0]", {"id": 1}),
        ("$.foo", {"_info": "No matches for JSONPath expression", "jsonpath": "$.foo"}),
    ],
)
def test_jsonpath_extraction(jsonpath, expected):
    data = [{"id": 1}, {"id": 2}]
    result = _prune_json(data, jsonpath=jsonpath)
    assert result == expected
