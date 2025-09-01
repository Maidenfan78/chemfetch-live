# ChemFetch OCR Service - Agent Instructions

## Service Overview

Python Flask microservice for Safety Data Sheet (SDS) verification, text extraction, and parsing.
Provides HTTP endpoints consumed by the Node.js backend for PDF processing and chemical data extraction.

## Setup Commands

- Install dependencies: `pip install -r requirements.txt`
- Start development server: `python ocr_service.py` (Flask dev server, default port 5001)
- Start production: `gunicorn -w 2 -b 0.0.0.0:5001 ocr_service:app` (or `-b 0.0.0.0:${PORT}`)
- Test parsing: `python parse_sds.py <pdf_path>`
- Quick parser test: `python quick_parser.py <pdf_path>`

## Architecture & Components

```
ocr_service/
├── ocr_service.py       # Flask app with HTTP endpoints
├── parse_sds.py         # CLI parser for metadata extraction
├── quick_parser.py      # Lightweight regex-based fallback parser
├── sds_parser_new/      # Primary SDS extraction system
│   └── sds_extractor.py # Advanced parsing with layered extraction
├── requirements.txt     # Optimized for 512MB memory limit
└── README.md           # Service documentation
```

## Key Endpoints

- **GET `/health`**: Service status, memory usage, environment info
- **POST `/verify-sds`**: Verify PDF is valid SDS, extract text with OCR fallback
- **POST `/parse-sds`**: Unified parsing with layered fallbacks (primary → verification → quick parser)
- **POST `/parse-pdf-direct`**: Direct parsing using `sds_parser_new` extractor

## Python Code Standards

- **PEP 8**: Follow Python style guidelines consistently
- **Type Hints**: Use type annotations where beneficial
- **Error Handling**: Comprehensive exception handling with logging
- **Memory Efficiency**: Critical - service runs in 512MB container
- **Modular Design**: Separate concerns across focused modules

## PDF Processing Workflow

1. **File Validation**: Check PDF format and size limits
2. **Text Extraction**: Try direct text extraction first (fast)
3. **OCR Fallback**: Use Tesseract for scanned/image-based PDFs
4. **Multi-Method Parsing**: Layer parsing approaches for accuracy
5. **Data Extraction**: Extract chemical properties, hazard data, classifications
6. **Response Formatting**: Return structured JSON with confidence scores

## Dependencies & Memory Management

```python
# Core (lightweight)
Flask==2.3.3           # ~20MB
flask-cors==4.0.0
requests==2.31.0
gunicorn==21.2.0

# PDF Processing (~50MB total)
pdfplumber==0.11.4     # Primary text extraction
pdfminer.six==20231228 # PDF parsing engine
PyMuPDF==1.26.4        # Alternative PDF library

# OCR Support (~30MB)
pytesseract==0.3.13    # Tesseract OCR wrapper
pdf2image==1.17.0      # PDF to image conversion
Pillow>=10.0.0         # Image processing

# Data Processing (~30MB)
numpy>=1.24.0,<2.0.0   # Numerical operations
python-dateutil==2.8.2 # Date parsing
regex==2024.5.15       # Advanced regex patterns
```

## SDS Parsing Strategy

**Layered Parsing Approach** (best to fallback):

1. **Primary Parser** (`sds_parser_new/`): Advanced extraction with confidence scoring
2. **Verification Parser**: Text-based extraction using `/verify-sds` output
3. **Quick Parser** (`quick_parser.py`): Regex-based fallback for basic data
4. **Error Recovery**: Return partial results with clear status indicators

## Text Extraction Methods

- **pdfplumber**: Primary method for digital PDFs with embedded text
- **PyMuPDF**: Alternative extraction for complex PDF structures
- **OCR Pipeline**: Tesseract + pdf2image for scanned documents
- **OCR Fallback (no Poppler)**: When Poppler is not installed, a PyMuPDF rasterization path renders pages to images (via Pillow) and runs Tesseract OCR. This enables robust scanned-PDF support without system Poppler.
- **Hybrid Approach**: Combine methods based on PDF characteristics

## Performance Optimization

- **Memory Limits**: Stay under 512MB total memory usage
- **Processing Speed**: Target <5 seconds for SDS parsing
- **Error Recovery**: Fast fallback between parsing methods
- **Resource Cleanup**: Properly clean up PDF objects and temp files
- **Concurrent Handling**: Support multiple simultaneous requests

Note: The PyMuPDF OCR fallback renders at ~200 DPI for accuracy while keeping performance within the <5s target on typical SDS documents.

## Data Extraction Patterns

**Key Information to Extract**:

- Product name and manufacturer details
- Chemical composition and CAS numbers
- Hazard classifications (GHS symbols, statements)
- Physical/chemical properties
- Safety precautions and emergency procedures
- Issue date and document version

## Error Handling & Logging

- **Structured Logging**: JSON logging compatible with Pino (Node.js backend)
- **Exception Recovery**: Graceful handling of PDF processing errors
- **Confidence Scoring**: Return confidence levels for extracted data
- **Debug Information**: Preserve debug context without memory leaks
- **Timeout Protection**: Prevent hanging operations on malformed PDFs

## Integration with Node.js Backend

- **Proxy Pattern**: Node.js routes proxy requests to Flask endpoints
- **CLI Integration**: `parse_sds.py` executed directly by Node.js routes
- **Response Format**: Consistent JSON structure across all endpoints
- **Error Propagation**: Proper HTTP status codes and error messages

## Testing & Validation

- **Manual Testing**: Use provided test scripts with sample SDS files
- **Accuracy Validation**: Compare extraction results against known SDS data
- **Memory Profiling**: Monitor memory usage during PDF processing
- **Performance Testing**: Measure processing time for various PDF types
- **Error Scenario Testing**: Test with malformed, corrupted, or non-SDS PDFs

## Deployment Considerations

- **Render Deployment**: Configured for Render free tier (512MB limit)
- **Gunicorn Config**: 2 workers for concurrent request handling
- **Health Monitoring**: `/health` endpoint for service monitoring
- **Environment Variables**: Flask configuration via environment
- **Container Optimization**: Minimal dependencies for fast deployment

## Common Development Tasks

- **Improve Parser Accuracy**: Modify `sds_parser_new/sds_extractor.py`
- **Add New Extraction Pattern**: Extend regex patterns in parsers
- **Optimize Memory Usage**: Profile and reduce memory footprint
- **Handle New PDF Format**: Extend text extraction methods
- **Debug Parsing Issues**: Use debug logging and manual test scripts

## Security & Validation

- **File Type Validation**: Ensure only valid PDFs are processed
- **Size Limits**: Prevent processing of overly large PDFs
- **Input Sanitization**: Clean extracted text before processing
- **Resource Limits**: Prevent resource exhaustion attacks
- **Sandboxing**: Service isolation for security

## Documentation Update Policy

When code changes in this service, update the related docs/readmes in the same PR so instructions and behavior stay aligned.

Relevant documentation locations:

- OCR agent guide (this file): `chemfetch-backend-live/ocr_service/AGENTS.md`
- OCR service overview: `chemfetch-backend-live/ocr_service/README.md`
- SDS parser guide: `chemfetch-backend-live/ocr_service/sds_parser_new/AGENTS.md`
- Backend integration notes: `chemfetch-backend-live/AGENTS.md`, `chemfetch-backend-live/server/AGENTS.md`
- Test data/results: `chemfetch-backend-live/test-data/`

If changes affect API shapes, also review backend routes in `chemfetch-backend-live/server/routes/` and the root `README.md`.

## Conventions

- Type hints where helpful; follow PEP 8 naming (`snake_case`).
- Use `logging` (structured messages) instead of `print`.
- Keep memory footprint low; clean up temp files promptly.
- Prefer `pdfplumber`/`PyMuPDF` before OCR; OCR only as fallback.
- Small, focused modules under `sds_parser_new/modules/` for new parsing logic.
