"""Tests for fetch_mcp/pdf.py — _extract_pdf_text."""

from __future__ import annotations

import builtins

from fetch_mcp.pdf import _extract_pdf_text


def test_extract_pdf_text_returns_string(sample_pdf_bytes):
    result = _extract_pdf_text(sample_pdf_bytes)
    assert isinstance(result, str)
    assert "Hello" in result


def test_extract_pdf_text_respects_max_chars(sample_pdf_bytes):
    result = _extract_pdf_text(sample_pdf_bytes, max_chars=5)
    assert len(result) <= 5 + len("\n\n[... truncated]")


def test_extract_pdf_text_scanned_warning(blank_pdf_bytes):
    result = _extract_pdf_text(blank_pdf_bytes)
    assert result.startswith("Warning:")
    assert "No extractable text" in result


def test_extract_pdf_text_missing_dep(monkeypatch):
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pdfminer" or name.startswith("pdfminer."):
            raise ImportError("No module named 'pdfminer'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    result = _extract_pdf_text(b"fake pdf bytes")
    assert result.startswith("Error:")
    assert "pdfminer.six" in result
