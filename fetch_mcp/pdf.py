from __future__ import annotations

import io


def _extract_pdf_text(data: bytes, max_chars: int = 20_000, pages: str | None = None) -> str:
    """Extract text from PDF bytes using pdfminer.six.

    Returns extracted text, a warning if no text is found (scanned PDF),
    or an error message if pdfminer.six is not installed.
    """
    try:
        from pdfminer.high_level import extract_text
        from pdfminer.pdfdocument import PDFDocument
        from pdfminer.pdfpage import PDFPage
        from pdfminer.pdfparser import PDFParser
    except ImportError:
        return "Error: pdfminer.six is not installed. Run `uv add pdfminer.six` to enable PDF extraction."

    # Parse page range if provided (e.g. "1-5" or "3")
    page_numbers: set[int] | None = None
    if pages:
        page_numbers = set()
        for part in pages.split(","):
            part = part.strip()
            if "-" in part:
                start, _, end = part.partition("-")
                page_numbers.update(range(int(start) - 1, int(end)))
            else:
                page_numbers.add(int(part) - 1)

    # Count pages to report in warning
    parser = PDFParser(io.BytesIO(data))
    doc = PDFDocument(parser)
    page_count = sum(1 for _ in PDFPage.create_pages(doc))

    # Extract text
    kwargs: dict = {}
    if page_numbers is not None:
        kwargs["page_numbers"] = page_numbers
    text = extract_text(io.BytesIO(data), **kwargs)

    text = text.strip()
    if not text:
        return (
            f"Warning: No extractable text found in PDF ({page_count} pages). "
            "May be scanned. Consider using browser_fetch with OCR if available."
        )

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... truncated]"

    return text
