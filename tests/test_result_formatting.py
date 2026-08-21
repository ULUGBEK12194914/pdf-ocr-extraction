from __future__ import annotations

from io import BytesIO

import pytest
from docx import Document as DocxDocument

import result_formatting
from ocr_extraction import DocumentResult, PageResult, TextBox


@pytest.fixture()
def sample_document() -> DocumentResult:
    high_confidence_box = TextBox(text="Trusted line", confidence=0.95, bbox=(0, 0, 100, 20))
    low_confidence_box = TextBox(text="Uncertain line", confidence=0.40, bbox=(0, 30, 100, 50))
    page = PageResult(
        page_number=1, width=600, height=800, source="ocr",
        columns=[[high_confidence_box, low_confidence_box]],
        flagged=[low_confidence_box],
    )
    return DocumentResult(source_name="sample.pdf", pages=[page])


def test_to_text_flags_low_confidence_lines(sample_document: DocumentResult) -> None:
    text = result_formatting.to_text(sample_document, conf_threshold=0.80)

    assert "Trusted line" in text
    assert "【Uncertain line】" in text
    assert "Page 1" in text


def test_to_text_does_not_flag_when_threshold_is_zero(sample_document: DocumentResult) -> None:
    text = result_formatting.to_text(sample_document, conf_threshold=0.0)
    assert "【" not in text


def test_to_markdown_includes_heading_and_flag_summary(sample_document: DocumentResult) -> None:
    markdown = result_formatting.to_markdown(sample_document, conf_threshold=0.80)

    assert markdown.startswith("# sample.pdf")
    assert "## Page 1" in markdown
    assert "【Uncertain line】" in markdown
    assert "Low-confidence" in markdown


def test_to_docx_bytes_produces_a_valid_document(sample_document: DocumentResult) -> None:
    docx_bytes = result_formatting.to_docx_bytes(sample_document, conf_threshold=0.80)

    document = DocxDocument(BytesIO(docx_bytes))
    all_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "Trusted line" in all_text
    assert "【Uncertain line】" in all_text


def test_multi_column_layout_renders_column_headings() -> None:
    left_box = TextBox(text="Left column text", confidence=1.0, bbox=(0, 0, 100, 20))
    right_box = TextBox(text="Right column text", confidence=1.0, bbox=(400, 0, 500, 20))
    page = PageResult(page_number=1, width=600, height=800, source="digital", columns=[[left_box], [right_box]])
    document = DocumentResult(source_name="two_column.pdf", pages=[page])

    text = result_formatting.to_text(document, conf_threshold=0.80)
    assert "column 1" in text
    assert "column 2" in text
    assert "Left column text" in text
    assert "Right column text" in text


def test_page_with_no_flags_omits_flag_summary() -> None:
    box = TextBox(text="All good", confidence=1.0, bbox=(0, 0, 100, 20))
    page = PageResult(page_number=1, width=600, height=800, source="digital", columns=[[box]], flagged=[])
    document = DocumentResult(source_name="clean.pdf", pages=[page])

    text = result_formatting.to_text(document, conf_threshold=0.80)
    assert "Low-confidence" not in text


@pytest.mark.parametrize("format_key", ["text", "txt", "markdown", "md", "word", "docx"])
def test_every_declared_format_key_has_a_formatter_and_extension(format_key: str) -> None:
    assert format_key in result_formatting.FORMATTERS
    assert format_key in result_formatting.FORMAT_EXTENSIONS
