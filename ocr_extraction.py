from __future__ import annotations

import logging
import shutil
import statistics
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image
from pytesseract import Output

logger = logging.getLogger(__name__)

IMAGE_PAGE_AREA_RATIO = 0.5
MIN_DIGITAL_TEXT_CHARS = 40
DEFAULT_DPI = 300
DEFAULT_CONF_THRESHOLD = 0.80
DEFAULT_LANGS = "rus+eng"


def configure_tesseract_binary(explicit_path: str | None = None) -> None:
    resolved = explicit_path or shutil.which("tesseract") or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if Path(resolved).exists():
        pytesseract.pytesseract.tesseract_cmd = resolved
    else:
        logger.warning("Tesseract binary not found at %s; OCR calls will fail", resolved)


configure_tesseract_binary()


@dataclass
class TextBox:
    text: str
    confidence: float
    bbox: tuple[float, float, float, float]

    @property
    def x_center(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2

    @property
    def y_center(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


@dataclass
class PageResult:
    page_number: int
    width: int
    height: int
    source: str
    columns: list[list[TextBox]] = field(default_factory=list)
    flagged: list[TextBox] = field(default_factory=list)

    @property
    def mean_confidence(self) -> float:
        boxes = [box for column in self.columns for box in column]
        if not boxes:
            return 1.0
        return statistics.mean(box.confidence for box in boxes)


@dataclass
class DocumentResult:
    source_name: str
    pages: list[PageResult]

    @property
    def mean_confidence(self) -> float:
        if not self.pages:
            return 1.0
        return statistics.mean(page.mean_confidence for page in self.pages)

    @property
    def flagged_count(self) -> int:
        return sum(len(page.flagged) for page in self.pages)


def _page_is_scanned(page: pymupdf.Page) -> bool:
    images = page.get_images(full=True)
    if not images:
        return False
    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return False

    covered_area = 0.0
    for image in images:
        try:
            for bbox in page.get_image_rects(image[0]):
                covered_area += bbox.width * bbox.height
        except Exception as exc:
            logger.debug("Could not compute image rect on page %d: %s", page.number, exc)
            continue

    return (covered_area / page_area) >= IMAGE_PAGE_AREA_RATIO


def _digital_text_boxes(page: pymupdf.Page) -> list[TextBox]:
    boxes: list[TextBox] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if not text:
                continue
            x0, y0, x1, y1 = line["bbox"]
            boxes.append(TextBox(text=text, confidence=1.0, bbox=(x0, y0, x1, y1)))
    return boxes


def _tesseract_line_boxes(image_bytes: bytes, langs: str) -> list[TextBox]:
    image = Image.open(BytesIO(image_bytes))
    data = pytesseract.image_to_data(image, lang=langs, output_type=Output.DICT)

    lines: dict[tuple[int, int, int], dict] = {}
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        confidence = float(data["conf"][i])
        if not text or confidence < 0:
            continue

        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        left, top = data["left"][i], data["top"][i]
        right, bottom = left + data["width"][i], top + data["height"][i]

        entry = lines.setdefault(key, {"words": [], "confidences": [], "bbox": [left, top, right, bottom]})
        entry["words"].append(text)
        entry["confidences"].append(confidence)
        bbox = entry["bbox"]
        bbox[0], bbox[1] = min(bbox[0], left), min(bbox[1], top)
        bbox[2], bbox[3] = max(bbox[2], right), max(bbox[3], bottom)

    return [
        TextBox(
            text=" ".join(entry["words"]),
            confidence=statistics.mean(entry["confidences"]) / 100.0,
            bbox=tuple(entry["bbox"]),
        )
        for entry in lines.values()
    ]


def _group_into_columns(boxes: list[TextBox], page_width: int) -> list[list[TextBox]]:
    if not boxes:
        return []

    midpoint = page_width / 2
    center_band = page_width * 0.06
    boxes_near_center = [box for box in boxes if abs(box.x_center - midpoint) < center_band]
    is_two_column_layout = len(boxes_near_center) <= max(1, len(boxes) // 25)

    if not is_two_column_layout:
        return [sorted(boxes, key=lambda box: (box.y_center, box.x_center))]

    left_column = sorted((box for box in boxes if box.x_center < midpoint), key=lambda box: box.y_center)
    right_column = sorted((box for box in boxes if box.x_center >= midpoint), key=lambda box: box.y_center)
    return [left_column, right_column]


def ocr_pdf_bytes(
    pdf_bytes: bytes,
    source_name: str = "document.pdf",
    langs: str = DEFAULT_LANGS,
    dpi: int = DEFAULT_DPI,
    conf_threshold: float = DEFAULT_CONF_THRESHOLD,
) -> DocumentResult:
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    pages: list[PageResult] = []

    for page_index, page in enumerate(document):
        is_scanned = _page_is_scanned(page)
        digital_boxes = [] if is_scanned else _digital_text_boxes(page)
        digital_char_count = sum(len(box.text) for box in digital_boxes)

        if not is_scanned and digital_char_count >= MIN_DIGITAL_TEXT_CHARS:
            width, height = int(page.rect.width), int(page.rect.height)
            boxes = digital_boxes
            source = "digital"
        else:
            pixmap = page.get_pixmap(dpi=dpi)
            width, height = pixmap.width, pixmap.height
            boxes = _tesseract_line_boxes(pixmap.tobytes("png"), langs)
            source = "ocr"

        columns = _group_into_columns(boxes, width)
        flagged_boxes = [box for column in columns for box in column if box.confidence < conf_threshold]

        pages.append(
            PageResult(
                page_number=page_index + 1,
                width=width,
                height=height,
                source=source,
                columns=columns,
                flagged=flagged_boxes,
            )
        )

    return DocumentResult(source_name=source_name, pages=pages)
