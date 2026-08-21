from __future__ import annotations

import ocr_extraction


def test_digital_pdf_is_read_directly_without_ocr(digital_pdf_bytes: bytes) -> None:
    document = ocr_extraction.ocr_pdf_bytes(digital_pdf_bytes, source_name="digital.pdf")

    assert len(document.pages) == 1
    page = document.pages[0]
    assert page.source == "digital"
    assert page.mean_confidence == 1.0
    assert document.flagged_count == 0
    all_text = " ".join(box.text for column in page.columns for box in column)
    assert "Hello" in all_text


def test_scanned_pdf_goes_through_tesseract(scanned_pdf_bytes: bytes) -> None:
    document = ocr_extraction.ocr_pdf_bytes(scanned_pdf_bytes, source_name="scanned.pdf", langs="rus+eng")

    assert len(document.pages) == 1
    page = document.pages[0]
    assert page.source == "ocr"
    assert 0.0 <= page.mean_confidence <= 1.0
    all_text = " ".join(box.text for column in page.columns for box in column)
    assert "canned" in all_text
    assert "simulation" in all_text.lower()


def test_flagged_boxes_are_exactly_those_below_threshold(scanned_pdf_bytes: bytes) -> None:
    document = ocr_extraction.ocr_pdf_bytes(scanned_pdf_bytes, source_name="scanned.pdf", conf_threshold=0.0)
    assert document.flagged_count == 0

    document_strict = ocr_extraction.ocr_pdf_bytes(scanned_pdf_bytes, source_name="scanned.pdf", conf_threshold=1.01)
    total_boxes = sum(len(column) for page in document_strict.pages for column in page.columns)
    assert document_strict.flagged_count == total_boxes


def test_document_result_mean_confidence_is_one_when_no_pages() -> None:
    document = ocr_extraction.DocumentResult(source_name="empty.pdf", pages=[])
    assert document.mean_confidence == 1.0
    assert document.flagged_count == 0


def test_page_result_mean_confidence_is_one_when_no_boxes() -> None:
    page = ocr_extraction.PageResult(page_number=1, width=100, height=100, source="digital", columns=[])
    assert page.mean_confidence == 1.0


def test_group_into_columns_single_column_layout_sorted_top_to_bottom() -> None:
    boxes = [
        ocr_extraction.TextBox(text="third", confidence=1.0, bbox=(10, 300, 590, 320)),
        ocr_extraction.TextBox(text="first", confidence=1.0, bbox=(10, 10, 590, 30)),
        ocr_extraction.TextBox(text="second", confidence=1.0, bbox=(10, 150, 590, 170)),
    ]
    columns = ocr_extraction._group_into_columns(boxes, page_width=600)

    assert len(columns) == 1
    assert [box.text for box in columns[0]] == ["first", "second", "third"]


def test_group_into_columns_two_column_layout_splits_left_and_right() -> None:
    left_boxes = [
        ocr_extraction.TextBox(text=f"left-{i}", confidence=1.0, bbox=(10, i * 20, 150, i * 20 + 15))
        for i in range(30)
    ]
    right_boxes = [
        ocr_extraction.TextBox(text=f"right-{i}", confidence=1.0, bbox=(450, i * 20, 590, i * 20 + 15))
        for i in range(30)
    ]
    columns = ocr_extraction._group_into_columns(left_boxes + right_boxes, page_width=600)

    assert len(columns) == 2
    assert all(box.text.startswith("left-") for box in columns[0])
    assert all(box.text.startswith("right-") for box in columns[1])


def test_group_into_columns_empty_input_returns_empty_list() -> None:
    assert ocr_extraction._group_into_columns([], page_width=600) == []


def test_configure_tesseract_binary_accepts_explicit_path(tmp_path) -> None:
    original_cmd = ocr_extraction.pytesseract.pytesseract.tesseract_cmd
    try:
        fake_binary = tmp_path / "tesseract.exe"
        fake_binary.write_bytes(b"")
        ocr_extraction.configure_tesseract_binary(str(fake_binary))
        assert ocr_extraction.pytesseract.pytesseract.tesseract_cmd == str(fake_binary)
    finally:
        ocr_extraction.pytesseract.pytesseract.tesseract_cmd = original_cmd
