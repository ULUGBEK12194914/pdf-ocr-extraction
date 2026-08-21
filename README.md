
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


