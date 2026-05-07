# Phase 1 — Test Coverage

**Parent plan:** [2026-05-06-features.md](2026-05-06-features.md)  
**Goal:** Establish a full test suite for `smart_fetch`, `html.py`, `http.py`, and `cli.py` so that Phases 2–4 can refactor with confidence.

---

## Objective

Currently only `json_optimizer` is tested. This phase adds tests for the four remaining areas: `smart_fetch` end-to-end (mocked HTTP), `_html_to_markdown`, `http.py` helpers, and CLI subcommands.

**Explicitly deferred:** integration tests that hit live URLs, CI configuration.

---

## New Files

- `tests/test_smart_fetch.py`
- `tests/test_html.py`
- `tests/test_http.py`
- `tests/test_cli.py`

---

## New Dependencies (dev only)

- `pytest-httpx` — async-aware HTTP mocking for `httpx.AsyncClient`
- `pytest-asyncio` — `@pytest.mark.asyncio` support

Add to `pyproject.toml` `[dependency-groups] dev`:
```toml
"pytest-httpx>=0.35",
"pytest-asyncio>=0.24",
```

Add to `pyproject.toml` `[tool.pytest.ini_options]`:
```toml
asyncio_mode = "auto"
```

---

## Interface Boundaries

| Boundary | Contract |
|---|---|
| `_fetch_raw(url)` → `httpx.Response` | Mocked via `pytest-httpx`'s `httpx_mock` fixture |
| `smart_fetch(url, ...)` → `str` | Tested as an async function via `pytest.mark.asyncio` |
| CLI `main()` → stdout | Tested via `capsys` + direct `main()` call with `sys.argv` patched |

---

## Implementation Steps

- [ ] test(deps): add pytest-httpx to dev dependencies in pyproject.toml
- [ ] test(http): add tests for _is_json_content, _handle_error, and _find_chrome_executable
- [ ] test(html): add tests for _html_to_markdown — basic conversion, navigation stripping, truncation, metadata extraction
- [ ] test(smart_fetch): add mocked HTTP tests for JSON path, HTML path, schema-mode path, and HTTP error path
- [ ] test(cli): add tests for optimize subcommand (stdin/file), smart_fetch subcommand (mocked), and report subcommand

---

## Test Annotations

### `tests/test_http.py`

```python
def test_is_json_content_true_for_application_json()
def test_is_json_content_true_for_javascript()
def test_is_json_content_false_for_text_html()
def test_handle_error_timeout()
def test_handle_error_http_status()
def test_handle_error_generic()
def test_find_chrome_returns_none_when_no_chrome(monkeypatch)
def test_find_chrome_returns_path_when_env_set(monkeypatch, tmp_path)
```

### `tests/test_html.py`

```python
def test_basic_html_to_markdown()
def test_truncation_at_max_chars()
def test_metadata_extraction_returns_frontmatter()
def test_empty_html_returns_empty_or_minimal()
```

### `tests/test_smart_fetch.py`

```python
@pytest.mark.asyncio
async def test_smart_fetch_json_response(httpx_mock)
    # asserts result is valid JSON, schema mode triggered for 5+ uniform dicts

@pytest.mark.asyncio
async def test_smart_fetch_html_response(httpx_mock)
    # asserts result is markdown string (no raw HTML tags)

@pytest.mark.asyncio
async def test_smart_fetch_jsonpath_drills_in(httpx_mock)
    # jsonpath="$[*].id" → list of IDs only

@pytest.mark.asyncio
async def test_smart_fetch_http_error_returns_error_string(httpx_mock)
    # 404 → "Error: HTTP 404 ..."

@pytest.mark.asyncio
async def test_smart_fetch_logs_savings(httpx_mock, tmp_path, monkeypatch)
    # asserts _log_savings called (check JSONL file written)
```

### `tests/test_cli.py`

```python
def test_cli_optimize_from_stdin(monkeypatch, capsys)
    # sys.stdin = json string → pruned output on stdout

def test_cli_optimize_from_file(monkeypatch, capsys, tmp_path)

def test_cli_report_prints_table(monkeypatch, capsys, tmp_path)

@pytest.mark.asyncio
async def test_cli_smart_fetch_html(monkeypatch, httpx_mock, capsys)
```

---

## Success Criteria

- `uv run python -m pytest tests/ -v` exits 0 with all new tests passing
- No existing `test_json_optimizer.py` tests regress
- `uv run ruff check .` exits 0
