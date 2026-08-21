from __future__ import annotations

import sys
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pymupdf


@pytest.fixture(scope="session")
def digital_pdf_bytes() -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Hello OCR test contract. Продавец покупает товар.")
    page.insert_text((72, 100), "This line has a real, selectable text layer.")
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture(scope="session")
def scanned_pdf_bytes() -> bytes:
    text_page = pymupdf.open()
    page = text_page.new_page(width=600, height=300)
    page.insert_text((40, 60), "Scanned page simulation", fontsize=24)
    page.insert_text((40, 100), "Второй текстовый ряд для проверки OCR.", fontsize=20)
    pixmap = page.get_pixmap(dpi=200)
    image_bytes = pixmap.tobytes("png")
    text_page.close()

    image_pdf = pymupdf.open()
    image_page = image_pdf.new_page(width=pixmap.width, height=pixmap.height)
    image_page.insert_image(image_page.rect, stream=image_bytes)
    buffer = BytesIO()
    image_pdf.save(buffer)
    return buffer.getvalue()
