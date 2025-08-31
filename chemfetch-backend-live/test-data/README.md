# SDS Parser Testing Guide

This directory contains tools for testing the ChemFetch SDS parser with local PDF files.

## Quick Start

1. **Copy your SDS PDF files** to the `sds-pdfs/` directory
2. **Run the test script**:
   ```bash
   cd C:\Users\Sav\ProgramingProjects\chemfetch-live\chemfetch-backend-live
   python test_sds.py
   ```
3. **Check results** in `test-data/sds_test_results.json`

## Directory Structure

```
test-data/
├── README.md              ← This file
├── sds-pdfs/             ← Put your PDF files here
└── sds_test_results.json ← Test results (generated)
```

## What the Test Script Does

The `test_sds.py` script:

- ✅ Automatically finds all PDF files in `test-data/sds-pdfs/`
- ✅ Tests each PDF with the current SDS parser
- ✅ Shows real-time parsing results in the terminal
- ✅ Saves detailed results to `sds_test_results.json`

## Test Output

### Console Output

- Progress indicator for each PDF
- Key extracted fields (product name, manufacturer, issue date, etc.)
- Success/failure status
- Summary statistics

### JSON Results File

The `sds_test_results.json` contains:

```json
{
  "test_timestamp": "...",
  "total_files": 3,
  "successful": 2,
  "failed": 1,
  "results": {
    "example.pdf": {
      "success": true,
      "fields_extracted": 4,
      "total_fields": 4,
      "extracted_values": {
        "product_name": { "value": "Chemical X", "confidence": 1.0 },
        "manufacturer": { "value": "Company Y", "confidence": 0.9 }
      },
      "full_data": {
        /* complete parser output */
      },
      "file_size_mb": 2.5
    }
  }
}
```

## Parser Information

### Current Parser: `sds_parser_new/sds_extractor.py`

- **Text extraction methods**: PyMuPDF, pdfplumber, pdfminer.six, OCR fallback
- **Key fields extracted**:
  - Product name
  - Manufacturer
  - Issue date
  - Dangerous goods class
  - Packing group
  - Subsidiary risks

### Extraction Methods (with fallback)

1. **PyMuPDF** (fastest, if available)
2. **pdfplumber** (reliable for text-based PDFs)
3. **pdfminer.six** (always available fallback)
4. **OCR via pytesseract** (for image-based PDFs, if available)

## Testing Tips

### Good Test Files

- Mix of different SDS formats (different manufacturers)
- Various PDF types (text-based vs image-based)
- Different file sizes
- Both simple and complex layouts

### Analyzing Results

- Check `confidence` scores for extracted fields
- Low confidence may indicate parsing issues
- Compare `text_length` to identify extraction problems
- Review `full_data` for detailed parser output

### Common Issues

- **Low text extraction**: May indicate image-based PDF needing OCR
- **Missing fields**: Parser regex patterns may need adjustment
- **Date parsing failures**: Date format not recognized
- **Manufacturer extraction**: Complex layouts confusing parser

## Improving the Parser

Use the test results to identify patterns in parsing failures:

1. **Check `sds_test_results.json`** for systematic issues
2. **Review failed extractions** to understand why fields weren't found
3. **Compare successful vs failed PDFs** to identify format differences
4. **Test parser improvements** by re-running `python test_sds.py`

## Manual Testing

You can also test individual files directly:

```bash
python ocr_service/sds_parser_new/sds_extractor.py "test-data/sds-pdfs/your-file.pdf"
```

## File Requirements

- **Format**: PDF files only
- **Location**: Must be in `test-data/sds-pdfs/` directory
- **Size**: No strict limit, but large files (>50MB) may timeout
- **Content**: Safety Data Sheets in standard format

---

**Need help?** Check the main parser documentation in `ocr_service/sds_parser_new/` or review the existing parser code for implementation details.
