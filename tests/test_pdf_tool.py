"""Tests for the pdf_fetch MCP tool."""

from __future__ import annotations

from fetch_mcp.server import pdf_fetch


async def test_pdf_fetch_pdf_url(httpx_mock, sample_pdf_bytes):
    httpx_mock.add_response(
        url="https://example.com/doc.pdf",
        content=sample_pdf_bytes,
        headers={"content-type": "application/pdf"},
    )
    result = await pdf_fetch("https://example.com/doc.pdf")
    assert isinstance(result, str)
    assert "Hello" in result
    assert result.startswith("Note:") is False


async def test_pdf_fetch_non_pdf_url_falls_back(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/page",
        html="<p>Not a PDF</p>",
    )
    result = await pdf_fetch("https://example.com/page")
    assert result.startswith("Note: URL did not return a PDF")
    assert "Not a PDF" in result


async def test_pdf_fetch_http_error(httpx_mock):
    httpx_mock.add_response(
        url="https://example.com/secret.pdf",
        status_code=403,
        text="Forbidden",
    )
    result = await pdf_fetch("https://example.com/secret.pdf")
    assert result.startswith("Error:")
    assert "403" in result


async def test_pdf_fetch_with_auth_headers(httpx_mock, sample_pdf_bytes):
    httpx_mock.add_response(
        url="https://example.com/private.pdf",
        content=sample_pdf_bytes,
        headers={"content-type": "application/pdf"},
    )
    await pdf_fetch("https://example.com/private.pdf", headers={"Authorization": "Bearer secret"})
    request = httpx_mock.get_request()
    assert request.headers["Authorization"] == "Bearer secret"


async def test_pdf_fetch_page_range(httpx_mock, sample_pdf_bytes):
    httpx_mock.add_response(
        url="https://example.com/multi.pdf",
        content=sample_pdf_bytes,
        headers={"content-type": "application/pdf"},
    )
    result = await pdf_fetch("https://example.com/multi.pdf", pages="1")
    assert isinstance(result, str)
