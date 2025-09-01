# SDS Parser Enhancement - Agent Instructions

## Parser Overview

Advanced Safety Data Sheet (SDS) parsing system focused on accurate extraction of chemical data, hazard information, and regulatory compliance details from PDF documents. This module is called directly by the Flask service (`/parse-pdf-direct`) and indirectly via the unified `/parse-sds` pipeline.

## Setup Commands

- Install dependencies: `pip install -r requirements.txt` (from ocr_service directory)
- Test primary parser: `python sds_parser_new/sds_extractor.py <pdf_path>`
- Test quick parser: `python quick_parser.py <pdf_path>`
- Full parsing test: `python parse_sds.py <pdf_path>`
- Run parser improvements: `python analyze_improvements.py`

## Parser Architecture

```
sds_parser_new/
├── sds_extractor.py     # Primary advanced extraction engine (exports parse_pdf)
├── __init__.py          # Package initialization
└── modules/             # Supporting extraction components
    ├── config.py        # Parsing configuration, thresholds
    ├── text_extractor.py# Text extraction helpers
    ├── field_extractor.py# Field-level parsing (CAS, DG class, etc.)
    ├── date_parser.py   # Date normalization helpers
    ├── dependencies.py  # Optional deps and guards
    └── utils.py         # Utilities and confidence helpers (incl. doubled-label cleanup)

Root-level (in ocr_service/):
├── parse_sds.py         # CLI/unified parser wrapper
├── quick_parser.py      # Lightweight regex-based fallback
└── ocr_service.py       # Flask app using this module

Additional developer helpers:
- `ocr_service/dump_text.py` – small utility to dump PDF text (pdfplumber/pdfminer) for debugging parser behavior.
```

## Parsing Strategy (Layered Approach)

1. **Primary Parser**: `sds_parser_new/sds_extractor.py` (`parse_pdf`) - Advanced extraction with high accuracy
2. **Verification Parser**: Extract from `/verify-sds` endpoint text output
3. **Quick Parser**: `quick_parser.py` - Regex-based fallback for basic data
4. **Error Recovery**: Return partial results with confidence indicators

## Key Extraction Targets

### Product Information

- **Product Name**: Official chemical product name
- **Manufacturer**: Company name, address, contact information
- **Description**: Product use
- **Product Code**: Internal product codes, batch numbers
- **Synonyms**: Alternative names and trade names
- **CAS Numbers**: Chemical Abstract Service registry numbers
- **Chemical Formula**: Molecular formula and structure identifiers

### Hazard Classification

- **GHS Symbols**: Pictogram identification and meanings
- **Hazard Statements**: H-codes (H200-H499) with descriptions
- **Precautionary Statements**: P-codes (P100-P500) with safety instructions
- **Signal Words**: "Danger" or "Warning" classification
- **Hazard Classes**: Physical, health, and environmental hazards
- **Dangerous Goods Class**: UN classification (Class 1-9)

### Physical/Chemical Properties

- **Physical State**: Solid, liquid, gas at standard conditions
- **Appearance**: Color, odor, transparency
- **pH Value**: Acidity/alkalinity measurements
- **Melting/Boiling Points**: Temperature ranges
- **Density/Specific Gravity**: Mass per unit volume
- **Solubility**: Water solubility and other solvents
- **Flash Point**: Ignition temperature for flammable materials
- **Vapor Pressure**: Volatility measurements

### Regulatory Information

- **Issue Date**: Document creation or last revision date
- **Version Number**: Document version for tracking updates
- **Regulatory Standards**: OSHA, EPA, DOT compliance references
- **Use Restrictions**: Authorized uses and prohibited applications
- **Exposure Limits**: Occupational exposure limits (OEL, TWA, STEL)

## Text Extraction Optimization

### Primary Extraction Methods

```python
# pdfplumber - best for digital PDFs
import pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()

# PyMuPDF - alternative for complex layouts
import fitz
doc = fitz.open(pdf_path)
for page in doc:
    text = page.get_text()
```

### OCR Integration

```python
# Tesseract OCR for scanned documents
import pytesseract
from pdf2image import convert_from_path

images = convert_from_path(pdf_path)
for image in images:
    text = pytesseract.image_to_string(image)
```

Fallback without Poppler (uses PyMuPDF + Pillow):

```python
import fitz  # PyMuPDF
from PIL import Image
import pytesseract

doc = fitz.open(pdf_path)
mat = fitz.Matrix(2, 2)  # ~200 DPI
parts = []
for page in doc:
    pix = page.get_pixmap(matrix=mat, alpha=False)
    mode = 'RGB' if pix.n >= 3 else 'L'
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    img = img.convert('L') if mode != 'L' else img
    parts.append(pytesseract.image_to_string(img))
text = '\n'.join(parts)
```

## Pattern Matching & Regex

### Chemical Identification Patterns

```python
# CAS number pattern (XXX-XX-X or XXXXXXX-XX-X format)
cas_pattern = r'\b\d{2,7}-\d{2}-\d\b'

# Product name extraction (common SDS formats)
product_patterns = [
    r'Product\s+name\s*:?\s*(.+)',
    r'Trade\s+name\s*:?\s*(.+)',
    r'Chemical\s+name\s*:?\s*(.+)'
]

# H-code pattern (H200-H499)
hazard_pattern = r'\bH[2-4]\d{2}\b'

# P-code pattern (P100-P500)
precaution_pattern = r'\bP[1-5]\d{2}\b'
```

### Structured Data Extraction

```python
# Extract sections using headers
def extract_sections(text):
    sections = {}
    section_patterns = {
        'identification': r'^(?:section\s*)?1\s*[:\.-]?\s',  # relaxed for OCR
        'hazards': r'section\s+2[:\.\s]*hazard',
        'composition': r'section\s+3[:\.\s]*composition',
        # ... additional sections
    }
```

## Confidence Scoring System

- **High Confidence (90-100%)**: Exact pattern matches, structured data found
- **Medium Confidence (70-89%)**: Partial matches, inferred data
- **Low Confidence (50-69%)**: Weak patterns, uncertain extraction
- **No Confidence (<50%)**: Failed extraction, return null/empty

## Error Handling & Recovery

```python
def safe_extract(extraction_func, default_value=None):
    try:
        result = extraction_func()
        return result if result else default_value
    except Exception as e:
        logger.warning(f"Extraction failed: {e}")
        return default_value
```

## Performance Optimization

- **Memory Management**: Clean up PDF objects after processing
- **Processing Speed**: Target <5 seconds per SDS document
- **Batch Processing**: Handle multiple PDFs efficiently
- **Caching**: Cache extraction patterns and compiled regex
- **Resource Limits**: Stay within 512MB memory constraint

## Testing & Validation

```python
# Test different SDS formats
test_files = [
    'traditional_sds.pdf',      # Standard 16-section format
    'simplified_sds.pdf',       # Abbreviated format
    'scanned_sds.pdf',         # Image-based PDF requiring OCR
    'multi_language_sds.pdf',   # Multiple languages
    'damaged_sds.pdf'          # Corrupted or incomplete PDF
]
```

## Recent Updates

- Section detection: tolerates leading bullets/symbols before headers (e.g., "\* SECTION 1").
- Manufacturer/Description: added German labels (Hersteller, Lieferant, Verwendung, Anwendung, Verpackungsgruppe, Gefahrklasse) and improved near-label scanning that avoids codes (SU/PROC) and prefers lines with nearby contact info.
- Description prioritization: prefer Application/Use lines over filler like "No further relevant information available.".
- Dangerous goods class: extended windowed scanning and context-based upgrade to prefer subclasses (e.g., 2.1) when a bare class was initially found.

## Common SDS Formats & Variations

- **Standard GHS Format**: 16-section internationally standardized format
- **OSHA Format**: US-specific variations with additional requirements
- **Abbreviated SDS**: Shortened versions for low-hazard materials
- **Multi-language**: PDFs with multiple language sections
- **Legacy Formats**: Older MSDS (Material Safety Data Sheet) formats

## Improvement Strategies

### Accuracy Enhancement

- Normalize corrupted label text: Some PDFs render label headers with doubled letters (e.g., `PPRROODDUUCCTT NNAAMMEE`). The parser strips such doubled-letter label prefixes before evaluating candidates, ensuring clean product names like `Whiteboard cleaner`.
- Duplicate-letter tolerant label matching for Section 1 use/description: When labels like `RReeccoommmmeennddeedd UUssee` occur, the extractor compresses duplicate letters on-the-fly and matches the intended label, correctly capturing values such as `Used to clean whiteboards.` without hardcoding product names.
- Issue date fallback: If standard Issue/Revision/Prepared date patterns aren’t found, the parser scans for trailing labels like `Last Updated`, `Last Revision`, `Updated on`, etc., and accepts month–year forms (e.g., `August 2015`) by normalizing to the first of the month (`2015-08-01`). This is applied only as a fallback to avoid altering correct earlier matches.
- Avoid mislabeling product codes: `Product code` is no longer used as a product-name label. This prevents numeric codes (e.g., `0000003477`) from being captured as the product name, favoring `GHS product identifier` / `Product Identifier` instead.
- Manufacturer cleanup: Manufacturer strings are trimmed to the legal entity suffix (e.g., `PTY LTD`, `LTD`, `INC`, etc.) and parentheses that contain registry numbers or historical names (e.g., `ABN`, `ACN`, `Formerly`) are removed.
- Section header robustness: Section detection tolerates hyphens after section numbers (e.g., `Section 1 - ...`) and falls back to global label extraction when Section 1 headers are OCR-mangled.

1. **Train on More Samples**: Test with diverse SDS document types
2. **Pattern Refinement**: Improve regex patterns based on extraction failures
3. **Context Analysis**: Use surrounding text to validate extracted data
4. **Cross-Reference**: Validate CAS numbers against chemical databases
5. **Machine Learning**: Consider ML models for complex extraction tasks

### Performance Optimization

## Integration & Environment

- Default OCR service port: `5001` (Node backend proxies via `OCR_SERVICE_URL`)
- Ensure `ocr_service/requirements.txt` dependencies remain aligned with memory limits (Render free tier, ~512MB)
- The Flask endpoints using this module: `/parse-pdf-direct` and `/parse-sds`

## Documentation Update Policy

When code changes in this module, update the related docs/readmes in the same PR to keep behavior aligned.

Relevant documentation locations:

- Parser guide (this file): `chemfetch-backend-live/ocr_service/sds_parser_new/AGENTS.md`
- OCR service agent guide: `chemfetch-backend-live/ocr_service/AGENTS.md`
- OCR service overview: `chemfetch-backend-live/ocr_service/README.md`
- Backend agent guide (integration notes): `chemfetch-backend-live/AGENTS.md`
- Test data/results: `chemfetch-backend-live/test-data/`

If changes affect API shapes or behavior, also review:

- Backend routes: `chemfetch-backend-live/server/routes/`
- Root overview: `README.md`

1. **Preprocessing**: Optimize PDF text extraction methods
2. **Parallel Processing**: Process multiple sections simultaneously
3. **Smart Fallbacks**: Efficient cascading between parsing methods
4. **Memory Profiling**: Monitor and optimize memory usage patterns
5. **Caching**: Cache successful extraction patterns

### Robustness Improvement

1. **Error Recovery**: Better handling of malformed PDFs
2. **Format Detection**: Automatically detect SDS format type
3. **Language Support**: Multi-language extraction capabilities
4. **Quality Scoring**: More sophisticated confidence metrics
5. **Validation**: Cross-validate extracted data for consistency

## Development Workflow

1. **Identify Issues**: Use test cases to find parsing failures
2. **Pattern Analysis**: Examine failed extractions to understand patterns
3. **Code Enhancement**: Improve extraction methods and patterns
4. **Testing**: Validate improvements against test suite
5. **Performance Check**: Ensure memory and speed requirements are met
6. **Integration**: Update Flask endpoints to use improved parser

## Debugging Tools

- **Debug Images**: Save processed images for OCR troubleshooting
- **Text Dumps**: Output extracted text for pattern analysis
- **Confidence Logs**: Track confidence scores for different extraction methods
- **Performance Metrics**: Monitor parsing speed and memory usage
- **Error Tracking**: Log and categorize parsing failures for improvement
