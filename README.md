# pdf-ocr-extraction

A standalone PDF OCR extraction tool. Give it a PDF, get back its text
as `.txt`, `.docx`, or `.md`, with a per-line confidence score and every
uncertain span flagged rather than silently trusted.

No mail server, no external platform, no paid API — a single CPU-only
pipeline you can run from the command line or import as a library.

## Project Overview

Scanned documents (contracts, invoices, forms) routinely arrive as PDFs
with no machine-readable text layer. This tool extracts that text
automatically: point it at a PDF, and it returns the recognized content
in your chosen format, with anything Tesseract wasn't confident about
marked `【like this】` so it gets a human's attention instead of being
trusted blindly.

## Architecture & Workflow

```
PDF file --> ocr_extraction.py --> DocumentResult --> result_formatting.py --> .txt / .md / .docx
```

1. **`ocr_extraction.py`** opens the PDF with PyMuPDF and inspects each
   page individually:
   - A page with an embedded image covering most of its area is
     treated as a scan — even if it also carries a broken text layer
     (common after a bad previous OCR pass) — and is rendered to an
     image and sent through Tesseract.
   - A page with a genuine digital text layer is read directly: no
     OCR, no ambiguity, 100% confidence.
   - Text on a scanned page is grouped into columns (single or
     two-column layouts are auto-detected) so multi-column documents
     come back in correct reading order, not interleaved.
2. **`result_formatting.py`** renders the result as plain text,
   Markdown, or a `.docx` file, flagging any line below a configurable
   confidence threshold.
3. **`cli.py`** ties the two together as a command-line tool.

## Tech Stack & Libraries

| Library | Purpose |
|---|---|
| [`PyMuPDF`](https://pymupdf.readthedocs.io/) (`pymupdf`) | Opens PDFs, renders pages to images, and reads existing digital text layers directly. |
| [`pytesseract`](https://github.com/madmaze/pytesseract) | Python binding to the Tesseract OCR engine — text and per-word confidence extraction. |
| [`Pillow`](https://python-pillow.org/) (`PIL`) | Decodes rendered page images before they're handed to Tesseract. |
| [`python-docx`](https://python-docx.readthedocs.io/) | Generates the `.docx` output format. |
| `logging`, `dataclasses`, `argparse` (standard library) | Structured logging, typed data structures, and the CLI — no other runtime dependencies. |
| `pytest` (dev dependency) | The test suite — 21 tests covering both the digital-text and OCR code paths, column detection, confidence flagging, and every output format. |

## OCR Engine

**Tesseract OCR**, via `pytesseract`.

**Why Tesseract:**
- Free and open source — no per-page API cost, and no document content
  ever leaves the machine it runs on.
- Mature multi-language support, including combined-language models
  (e.g. `rus+eng` in a single pass) for bilingual documents.
- Runs entirely on CPU.
- Exposes per-word confidence scores directly, which this tool relies
  on to flag uncertain text instead of returning it as fact.

**System dependencies** (not installable via `pip`):
- The `tesseract` binary.
- Language data (`tessdata`) for every language you need. Add more via
  your OS package manager, or by downloading `.traineddata` files from
  [tesseract-ocr/tessdata](https://github.com/tesseract-ocr/tessdata)
  into Tesseract's `tessdata` directory.

**Honest limitation**: OCR accuracy is bounded by the source scan, not
by this pipeline. Tested against 15 real scanned contracts: 14 scored
87–100% mean confidence; the one outlier (64%) was traced to a
low-resolution phone-camera capture (~100 DPI effective resolution) —
preprocessing (contrast, sharpening, binarization) was tested against
it and made results *worse*, because Tesseract cannot recover detail
that was never captured. A low-quality source needs a proper re-scan,
not more post-processing.

## Installation & Setup

### Prerequisites

- Python 3.12+
- The Tesseract OCR binary with the language packs you need

**Windows:**
```bash
winget install --id UB-Mannheim.TesseractOCR
```

**Debian/Ubuntu (including GitLab CI runners):**
```bash
apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-rus
```

### Local setup

```bash
git clone <this-repository-url>
cd pdf-ocr-extraction

python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/macOS

pip install -r requirements-dev.txt
cp .env.example .env           # optional — defaults work out of the box
```

### Running the tests

```bash
pytest tests/ -v
```

### GitLab CI/CD

A ready-to-use `.gitlab-ci.yml` is included — it provisions Tesseract
on a `python:3.12-slim` image and runs the test suite on every push.

## Usage Guide

### CLI

```bash
python cli.py contract.pdf --format markdown
```

Options:

| Flag | Default | Description |
|---|---|---|
| `--format` | `text` | `text`, `markdown`, or `word` |
| `--output` | `<input>.<ext>` | Output file path |
| `--langs` | `rus+eng` (or `$OCR_LANGS`) | Tesseract language string, e.g. `rus+eng+chi_sim` |
| `--conf-threshold` | `0.80` (or `$OCR_CONF_THRESHOLD`) | Lines below this confidence are flagged |
| `--dpi` | `300` (or `$OCR_DPI`) | Render resolution for scanned pages |
| `--verbose` | off | Debug-level logging |

Example:
```bash
python cli.py invoice.pdf --format word --langs rus+eng+uzb_cyrl --conf-threshold 0.75
```

### As a library

```python
from ocr_extraction import ocr_pdf_bytes
from result_formatting import to_markdown

pdf_bytes = open("contract.pdf", "rb").read()
document = ocr_pdf_bytes(pdf_bytes, langs="rus+eng", conf_threshold=0.80)

print(f"{document.mean_confidence:.0%} confidence, {document.flagged_count} flagged spans")
markdown_text = to_markdown(document, conf_threshold=0.80)
```

### Configuration

All CLI defaults can be set via environment variables instead of flags
(see `.env.example`):

| Env var | Default |
|---|---|
| `OCR_LANGS` | `rus+eng` |
| `OCR_DPI` | `300` |
| `OCR_CONF_THRESHOLD` | `0.80` |
| `OCR_TESSERACT_CMD` | auto-detected |

## Known Limitations

- OCR accuracy depends entirely on source scan quality — see the OCR
  Engine section above.
- Language selection is a single explicit string (e.g. `rus+eng`) —
  there is no automatic language detection.
- Very large PDFs are processed page-by-page in memory; there is no
  streaming or batching for extremely large documents.
