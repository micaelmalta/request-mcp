# Phase 4 — pdf_fetch Tool

**Parent plan:** [2026-05-06-features.md](2026-05-06-features.md)  
**Depends on:** Phase 3 (auth headers available for authenticated PDF endpoints)  
**Goal:** Add a `pdf_fetch` MCP tool that downloads a PDF URL and returns its text as markdown.

---

## Objective

Fetch a URL that serves a PDF, extract text via `pdfminer.six` (optional dep), and return clean markdown-style output. Handles missing dep gracefully, scanned-PDF warning, and falls back to `smart_fetch` HTML path if the URL is not actually a PDF.

**Explicitly deferred:** OCR for scanned PDFs, table extraction, multi-column layout reflow.

---

## New Files

- `fetch_mcp/pdf.py` — `_extract_pdf_text(data: bytes, max_chars: int) -> str`

---

## Modified Files

- `fetch_mcp/server.py` — `@mcp.tool() pdf_fetch`
- `fetch_mcp/cli.py` — add `pdf_fetch` dispatch entry

---

## Interface: `fetch_mcp/pdf.py`

```python
def _extract_pdf_text(data: bytes, max_chars: int = 20_000, pages: str | None = None) -> str:
    """Extract text from PDF bytes using pdfminer.six.

    Returns:
    - Extracted text as plain paragraphs (markdown-compatible)
    - "Warning: No extractable text found in PDF (N pages). May be scanned." if no text
    - "Error: pdfminer.six is not installed." if import fails
    """
```

Internally uses `pdfminer.high_level.extract_text_to_fp` or `extract_text` (pure Python, no native deps).

---

## Interface: `pdf_fetch` tool (server.py)

```python
@mcp.tool(annotations={"readOnlyHint": True, ...})
async def pdf_fetch(
    url: Annotated[str, Field(description="URL of a PDF document")],
    pages: Annotated[
        str | None,
        Field(description="Page range to extract, e.g. '1-5' or '3'. Default: all pages."),
    ] = None,
    headers: Annotated[
        dict[str, str] | None,
        Field(description="Optional HTTP headers (e.g. Authorization)"),
    ] = None,
    max_chars: Annotated[int, Field(...)] = DEFAULT_MAX_CHARS,
) -> str:
    """Fetch a PDF URL and return its text content as markdown."""
```

**Flow:**
1. `_fetch_raw(url, extra_headers=headers)` → response
2. Check `Content-Type`: if not `application/pdf`, return `smart_fetch`-style result with a note: `"Note: URL did not return a PDF. Returning HTML content instead.\n\n{html_result}"`
3. `_extract_pdf_text(response.content, max_chars=max_chars)` (filtered by `pages` if provided)
4. `_log_savings(len(response.content), len(result), source=f"pdf_fetch:{url[:60]}")`
5. Return result

---

## Graceful Degradation

| Failure | Behaviour |
|---|---|
| `pdfminer.six` not installed | Returns `"Error: pdfminer.six is not installed. Run \`uv add pdfminer.six\` to enable PDF extraction."` |
| URL returns HTML (not PDF) | Falls back to HTML→markdown with a leading note |
| PDF has no text layer (scanned) | Returns `"Warning: No extractable text found in PDF (N pages). May be scanned. Consider using browser_fetch with OCR if available."` |
| HTTP error fetching PDF | `_handle_error` returns `"Error: HTTP N — ..."` |
| `pages` range out of bounds | `pdfminer` silently returns whatever is available; no error |

---

## Implementation Steps

- [ ] test(pdf): write tests for _extract_pdf_text — normal PDF bytes, empty PDF, missing dep (monkeypatched ImportError)
- [ ] feat(pdf): implement fetch_mcp/pdf.py with _extract_pdf_text using pdfminer.six lazy import
- [ ] test(pdf_fetch): write mocked tests for pdf_fetch tool — PDF content-type path, non-PDF fallback path, HTTP error path
- [ ] feat(server): register pdf_fetch MCP tool in server.py
- [ ] docs(readme): add pdf_fetch to the tool list and example CLI invocation

---

## Test Annotations

A `conftest.py` fixture provides `sample_pdf_bytes` and `blank_pdf_bytes` using `fpdf2` (add to dev deps) or a minimal hardcoded valid PDF bytestring.

### `tests/test_pdf.py`

```python
def test_extract_pdf_text_returns_string(sample_pdf_bytes)
    # fixture: minimal valid PDF generated with reportlab or fpdf2 in conftest

def test_extract_pdf_text_scanned_warning(blank_pdf_bytes)
    # PDF with no text layer → warning string

def test_extract_pdf_text_missing_dep(monkeypatch)
    # monkeypatch builtins.__import__ to raise ImportError for pdfminer
    # → "Error: pdfminer.six is not installed."
```

### `tests/test_pdf_tool.py`

```python
@pytest.mark.asyncio
async def test_pdf_fetch_pdf_url(httpx_mock, sample_pdf_bytes)
    # content-type: application/pdf → extracted text returned

@pytest.mark.asyncio
async def test_pdf_fetch_non_pdf_url_falls_back(httpx_mock)
    # content-type: text/html → note + markdown

@pytest.mark.asyncio
async def test_pdf_fetch_http_error(httpx_mock)
    # 403 → "Error: HTTP 403 ..."

@pytest.mark.asyncio
async def test_pdf_fetch_with_auth_headers(httpx_mock, sample_pdf_bytes)
    # assert Authorization header forwarded
```

---

## Success Criteria

- All Phase 1–3 tests still pass
- PDF tests pass with `pdfminer.six` installed
- `uv run fetch-mcp pdf_fetch https://example.com/doc.pdf` works from CLI (add CLI dispatch)
- `pdfminer.six` is listed as an optional dep in `pyproject.toml` (not in `[project.dependencies]`, separate `[project.optional-dependencies] pdf = ["pdfminer.six"]`)
