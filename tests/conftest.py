"""Shared pytest fixtures."""

from __future__ import annotations

import io

import pytest


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF with extractable text, generated via fpdf2."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(text="Hello from fetch-mcp PDF fixture.")
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()


@pytest.fixture
def blank_pdf_bytes() -> bytes:
    """Minimal valid PDF with no text layer (blank page)."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()
