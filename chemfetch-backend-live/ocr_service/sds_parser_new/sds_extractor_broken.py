#!/usr/bin/env python3
"""
Improved SDS extractor - fixing specific issues identified in testing
Integration of working_parser.py into the modular structure with enhancements
"""
import re
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import fitz
    import pdfplumber
    from pdfminer.high_level import extract_text as pdfminer_extract
import sys

# Ensure local modules are importable when run as script
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Use improved modular field extraction helpers
from modules.field_extractor import (
    extract_product_name, 
    extract_manufacturer, 
    extract_description,
    extract_date_from_header,
    extract_section14_field
)
from modules.text_extractor import extract_text
from modules.utils import get_section
from modules.date_parser import extract_issue_date

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import PDF libraries with fallbacks
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
except ImportError:
    pdfminer_extract = None
    PDFMINER_AVAILABLE = False


def parse_pdf(path: Path) -> Dict[str, Any]:
    """Main parsing function that fixes the specific issues found in testing."""
    
    logger.info(f"Starting to parse: {path}")
    
    # Extract text using improved text extractor
    text, ocr_error = extract_text(path)
    if not text:
        return {
            "error": f"Could not extract text from PDF{': ' + ocr_error if ocr_error else ''}",
            "extraction_info": {
                "text_length": 0,
                "available_methods": {
                    "pymupdf": PYMUPDF_AVAILABLE,
                    "pdfplumber": PDFPLUMBER_AVAILABLE,
                    "pdfminer": PDFMINER_AVAILABLE
                },
                "extraction_mode": "failed",
                "ocr_error": ocr_error
            }
        }
    
    # Get sections
    section1 = get_section(text, 1)
    section14 = get_section(text, 14)
    
    logger.info(f"Section 1: {len(section1)} chars, Section 14: {len(section14)} chars")
    
    # Extract fields
    result = {
        "extraction_info": {
            "text_length": len(text),
            "available_methods": {
                "pymupdf": PYMUPDF_AVAILABLE,
                "pdfplumber": PDFPLUMBER_AVAILABLE,
                "pdfminer": PDFMINER_AVAILABLE
            },
            "extraction_mode": "full",
            "ocr_error": ocr_error
        }
    }
    
    # Product name (improved extraction)
    product_name = extract_product_name(section1)
    if not product_name:
        # Fallback: try first part of document
        prefix = '\n'.join(text.splitlines()[:15])
        product_name = extract_product_name(prefix)
    result['product_name'] = {'value': product_name, 'confidence': 1.0 if product_name else 0.0}
    
    # Manufacturer (improved extraction)
    manufacturer = extract_manufacturer(section1)
    result['manufacturer'] = {'value': manufacturer, 'confidence': 1.0 if manufacturer else 0.0}
    
    # Product description/use (new field requested)
    description = extract_description(section1)
    if not description:
        # Try broader search in full text
        description = extract_description(text)
    result['description'] = {'value': description, 'confidence': 1.0 if description else 0.0}
    
    # Product use (keeping existing for compatibility)
    product_use = description  # Use same value as description for now
    result['product_use'] = {'value': product_use, 'confidence': 1.0 if product_use else 0.0}
    
    # Dangerous goods class (improved extraction from Section 14)
    dg_class_labels = [
        r'DG\s+Class',
        r'Class',
        r'Transport\s+hazard\s+class',
        r'(?:IMDG|IATA|ADG)?\s*Hazard\s+Class',
        r'Dangerous\s+goods\s+class',
        r'Australian\s+Dangerous\s+Goods\s+class',
        r'UN\s+Class'
    ]
    
    dg_class = extract_section14_field(section14, dg_class_labels, 'dangerous_goods_class')
    result['dangerous_goods_class'] = {'value': dg_class, 'confidence': 1.0 if dg_class else 0.0}
    
    # Subsidiary risk
    subsidiary_risk_labels = [
        r'Subsidiary\s+risk',
        r'Subsidiary\s+hazard',
        r'Secondary\s+risk'
    ]
    subsidiary_risk = extract_section14_field(section14, subsidiary_risk_labels, 'subsidiary_risk')
    result['subsidiary_risk'] = {'value': subsidiary_risk, 'confidence': 1.0 if subsidiary_risk else 0.0}
    
    # Packing group (improved extraction from Section 14 including tables)
    packing_group_labels = [
        r'Packing\s+group',
        r'PG',
        r'.*packing\s+group',
        r'Australian\s+Dangerous\s+Goods\s+packing\s+group'
    ]
    packing_group = extract_section14_field(section14, packing_group_labels, 'packing_group')
    result['packing_group'] = {'value': packing_group, 'confidence': 1.0 if packing_group else 0.0}
    
    # Issue date (improved extraction including headers)
    issue_date = extract_issue_date(text)
    if not issue_date:
        # Try header extraction for cases like sds_3.pdf
        issue_date = extract_date_from_header(text)
    result['issue_date'] = {'value': issue_date, 'confidence': 1.0 if issue_date else 0.0}
    
    # Log results
    logger.info("Extraction complete:")
    for field in ['product_name', 'manufacturer', 'description', 'dangerous_goods_class', 'packing_group', 'issue_date']:
        value = result[field].get('value')
        logger.info(f"  {field}: '{value if value is not None else 'None'}'")
    
    return result


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python sds_extractor.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        sys.exit(1)
    
    try:
        result = parse_pdf(pdf_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        error_msg = str(e) if e is not None else 'Unknown error'
        print(f"Error: {error_msg}")
        logger.exception("Parsing failed")
