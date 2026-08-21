from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import ocr_extraction
import result_formatting
from config import OcrSettings

logger = logging.getLogger("pdf_ocr_extraction.cli")


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
    )


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Extract text from a scanned or digital PDF via OCR.")
    parser.add_argument("pdf_path", type=Path, help="Path to the input PDF file.")
    parser.add_argument("--format", choices=["text", "markdown", "word"], default="text")
    parser.add_argument("--output", type=Path, default=None, help="Output file path (default: alongside the input).")
    parser.add_argument("--langs", default=None, help="Tesseract language string, e.g. rus+eng+chi_sim.")
    parser.add_argument("--conf-threshold", type=float, default=None)
    parser.add_argument("--dpi", type=int, default=None)
    parser.add_argument("--verbose", action="store_true")
    return parser


def run(args: argparse.Namespace) -> int:
    if not args.pdf_path.is_file():
        logger.error("File not found: %s", args.pdf_path)
        return 1

    settings = OcrSettings.from_environment()
    ocr_extraction.configure_tesseract_binary(settings.tesseract_cmd)

    langs = args.langs or settings.langs
    conf_threshold = settings.conf_threshold if args.conf_threshold is None else args.conf_threshold
    dpi = settings.dpi if args.dpi is None else args.dpi

    try:
        pdf_bytes = args.pdf_path.read_bytes()
        document = ocr_extraction.ocr_pdf_bytes(
            pdf_bytes, source_name=args.pdf_path.name, langs=langs, dpi=dpi, conf_threshold=conf_threshold
        )
    except Exception:
        logger.exception("OCR extraction failed for %s", args.pdf_path)
        return 1

    formatter = result_formatting.FORMATTERS[args.format]
    rendered = formatter(document, conf_threshold=conf_threshold)
    output_bytes = rendered.encode("utf-8") if isinstance(rendered, str) else rendered

    extension = result_formatting.FORMAT_EXTENSIONS[args.format]
    output_path = args.output or args.pdf_path.with_suffix(f".{extension}")
    output_path.write_bytes(output_bytes)

    logger.info(
        "pages=%d mean_confidence=%.1f%% flagged=%d",
        len(document.pages), document.mean_confidence * 100, document.flagged_count,
    )
    logger.info("output written to %s", output_path)
    return 0


def main() -> int:
    args = _build_arg_parser().parse_args()
    _configure_logging(args.verbose)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
