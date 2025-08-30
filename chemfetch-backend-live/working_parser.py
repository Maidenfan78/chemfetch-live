#!/usr/bin/env python3
"""
Working SDS extractor - fixing specific issues identified in testing
"""
import re
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import PDF libraries with fallbacks
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False


def is_noise_text(text: str) -> bool:
    """Check if text is likely noise that shouldn't be extracted as field values."""
    if not text or len(text.strip()) < 2:
        return True
    
    text = text.strip()
    
    # Specific noise patterns found in test results
    noise_patterns = [
        r'^MSDS\s+Date$',
        r'^Alternative\s+number\(s\)$', 
        r'^Facsimile\s+Number$',
        r'^safety\s+data\s+sheet$',
        r'^Name$',
        r'^Registered\s+company\s+name$',
        r'^\:$',
        r'^\'s$',
        r'^UK,?\s+NPIS.*\d{2,4}\s+\d{2,4}\s+\d{2,4}',
        r'^Australia\s+-\s+\d{2,4}\s+\d{2,4}\s+\d{2,4}',
        r'^\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}',
        r'^Emergency\s+telephone',
        r'^Contact\s+details',
        r'^Details\s+of\s+the\s+supplier',
        r'^Telephone',
        r'^Phone',
        r'^Fax',
        r'^Email',
        r'^Address',
        r'^Website',
    ]
    
    for pattern in noise_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            logger.debug(f"Rejecting noise text: '{text}' (matched: {pattern})")
            return True
    
    return False


def validate_dangerous_goods_class(value: str) -> bool:
    """Validate dangerous goods class - only accept 1-9.x or valid N/A responses."""
    if not value:
        return False
    
    value = value.strip()
    
    # Valid class patterns: 1, 1.1, 2.1, etc.
    if re.match(r'^[1-9](?:\.[1-9])?$', value):
        return True
    
    # Valid N/A responses
    na_patterns = [
        r'^not?\s+regulated',
        r'^not?\s+applicable', 
        r'^none$',
        r'^n/?a$',
        r'^not\s+a\s+dangerous\s+good',
        r'^not\s+subject\s+to',
    ]
    
    for pattern in na_patterns:
        if re.match(pattern, value, re.IGNORECASE):
            return True
    
    # Reject invalid values like "14.5", "1950"
    logger.debug(f"Rejecting invalid DG class: '{value}'")
    return False


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text using available PDF libraries."""
    text = ""
    
    # Try PyMuPDF first (fastest)
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(str(pdf_path))
            for page in doc:
                text += page.get_text()
            doc.close()
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using PyMuPDF")
                return text
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}")
    
    # Try pdfplumber
    if PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text() or ""
                    text += page_text
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using pdfplumber")
                return text
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")
    
    # Try pdfminer as fallback
    if PDFMINER_AVAILABLE:
        try:
            with open(pdf_path, 'rb') as f:
                text = pdfminer_extract(f)
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using pdfminer")
                return text
        except Exception as e:
            logger.warning(f"pdfminer failed: {e}")
    
    logger.error("All text extraction methods failed")
    return ""


def get_section(text: str, section_num: int) -> str:
    """Extract a specific section from SDS text."""
    # Look for section headers
    pattern = rf'(?:^|\n)\s*(?:section\s*)?{section_num}(?:\s|:|\.).*?(?=\n\s*(?:section\s*)?\d{{1,2}}(?:\s|:|\.)|$)'
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(0) if match else ""


def extract_field_value(text: str, field_labels: list, section_text: str = None) -> Optional[str]:
    """Extract field value following labels, with improved validation."""
    
    # Use section text if provided, otherwise full text
    search_text = section_text if section_text else text
    
    if not search_text:
        return None
    
    lines = search_text.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        for label in field_labels:
            # Pattern: "Label: value" on same line
            pattern = rf'^{label}\s*[:\-]?\s*(.+)$'
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                
                # Clean up common trailing noise
                value = re.sub(r'\s*[:\-]\s*$', '', value)  # Remove trailing punctuation
                value = re.sub(r'\s+(Tel|Phone|Fax|Email|Emergency).*$', '', value, re.IGNORECASE)  # Remove contact info
                
                if value and not is_noise_text(value):
                    return value
            
            # Pattern: Label on one line, value on next
            if re.match(rf'^{label}\s*[:\-]?\s*$', line, re.IGNORECASE):
                # Look at next few lines for the value
                for j in range(i + 1, min(i + 4, len(lines))):
                    candidate = lines[j].strip()
                    if candidate and not candidate.startswith(':'):
                        if not is_noise_text(candidate):
                            return candidate
    
    return None


def extract_product_name(section1_text: str) -> Optional[str]:
    """Extract product name with multiple strategies."""
    
    # Strategy 1: Look for explicit labels
    labels = [
        r'Product\s+identifier',
        r'Product\s+name',
        r'Trade\s+name',
        r'Commercial\s+product\s+name'
    ]
    
    result = extract_field_value("", labels, section1_text)
    if result:
        return result
    
    # Strategy 2: Look for meaningful product-like text in early lines
    lines = section1_text.split('\n')
    
    for line in lines[:15]:  # Check first 15 lines
        line = line.strip()
        if not line:
            continue
            
        # Skip obvious headers and labels
        if re.match(r'^\d+\.|\bsection\b|\bidentification\b', line, re.IGNORECASE):
            continue
        if any(x in line.lower() for x in ['supplier', 'emergency', 'telephone', 'contact', 'details']):
            continue
        if is_noise_text(line):
            continue
        
        # Check if line looks like a product name (has alphanumeric content, reasonable length)
        if re.search(r'[A-Za-z0-9]', line) and 3 <= len(line) <= 100:
            # Avoid lines that are obviously not product names
            if not re.search(r'@|www\.|\.com|\.org', line, re.IGNORECASE):
                if not re.match(r'^[:\-\s]+$', line):
                    logger.info(f"Found potential product name: '{line}'")
                    return line
    
    return None


def extract_manufacturer(section1_text: str) -> Optional[str]:
    """Extract manufacturer with multiple strategies."""
    
    # Strategy 1: Look for explicit labels
    labels = [
        r'Manufacturer',
        r'Supplier', 
        r'Company\s+name\s+of\s+supplier',
        r'Producer',
        r'Company\s+name'
    ]
    
    result = extract_field_value("", labels, section1_text)
    if result and not is_noise_text(result):
        return result
    
    # Strategy 2: Look in "Details of the supplier" section
    supplier_match = re.search(r'Details\s+of\s+the\s+supplier[^\n]*\n(.{1,500}?)(?:\n\s*[A-Z][a-z]|\n\s*\d|$)', 
                              section1_text, re.IGNORECASE | re.DOTALL)
    if supplier_match:
        supplier_section = supplier_match.group(1)
        lines = supplier_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not is_noise_text(line) and len(line) > 3:
                # Skip phone numbers
                if not re.search(r'\b\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}\b', line):
                    return line
    
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract issue/revision date."""
    
    # Look for date patterns with labels
    date_pattern = re.compile(
        r'(?:Issue\s+Date|Revision\s+Date|Date\s+of\s+issue|Version\s+date|Date\s+Prepared|Issued)[^\n]{0,30}?[:\-]?\s*'
        r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},?\s*\d{4})',
        re.IGNORECASE
    )
    
    matches = date_pattern.findall(text)
    if matches:
        # Try to parse and validate date
        try:
            from datetime import datetime, date
            
            for date_str in matches:
                try:
                    # Try different formats
                    for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt).date()
                            if parsed_date <= date.today():  # Must be in the past
                                return parsed_date.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                except Exception:
                    continue
        except ImportError:
            # If datetime not available, return first match
            return matches[0]
    
    return None


def parse_pdf(pdf_path: Path) -> Dict[str, Any]:
    """Main parsing function that fixes the specific issues found in testing."""
    
    logger.info(f"Starting to parse: {pdf_path}")
    
    # Extract text
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return {
            "error": "Could not extract text from PDF",
            "extraction_info": {
                "text_length": 0,
                "available_methods": {
                    "pymupdf": PYMUPDF_AVAILABLE,
                    "pdfplumber": PDFPLUMBER_AVAILABLE,
                    "pdfminer": PDFMINER_AVAILABLE
                }
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
            }
        }
    }
    
    # Product name
    product_name = extract_product_name(section1)
    result['product_name'] = {'value': product_name, 'confidence': 1.0 if product_name else 0.0}
    
    # Manufacturer
    manufacturer = extract_manufacturer(section1)
    result['manufacturer'] = {'value': manufacturer, 'confidence': 1.0 if manufacturer else 0.0}
    
    # Product use
    product_use = extract_field_value(text, [
        r'Recommended\s+use',
        r'Intended\s+use',
        r'Use\s+of\s+the\s+substance',
        r'Product\s+use',
        r'Relevant\s+identified\s+uses'
    ], section1)
    result['product_use'] = {'value': product_use, 'confidence': 1.0 if product_use else 0.0}
    
    # Dangerous goods class (from Section 14)
    dg_class = extract_field_value(text, [
        r'DG\s+Class',
        r'Class',
        r'Transport\s+hazard\s+class',
        r'(?:IMDG|IATA|ADG)?\s*Hazard\s+Class',
        r'Dangerous\s+goods\s+class'
    ], section14)
    
    # Validate dangerous goods class
    if dg_class and not validate_dangerous_goods_class(dg_class):
        logger.warning(f"Invalid DG class rejected: '{dg_class}'")
        dg_class = None
    
    result['dangerous_goods_class'] = {'value': dg_class, 'confidence': 1.0 if dg_class else 0.0}
    
    # Subsidiary risk
    subsidiary_risk = extract_field_value(text, [r'Subsidiary\s+risk'], section14)
    result['subsidiary_risk'] = {'value': subsidiary_risk, 'confidence': 1.0 if subsidiary_risk else 0.0}
    
    # Packing group
    packing_group = extract_field_value(text, [
        r'Packing\s+group',
        r'PG'
    ], section14)
    result['packing_group'] = {'value': packing_group, 'confidence': 1.0 if packing_group else 0.0}
    
    # Issue date
    issue_date = extract_date(text)
    result['issue_date'] = {'value': issue_date, 'confidence': 1.0 if issue_date else 0.0}
    
    # Final validation - remove any remaining noise
    for field_name in ['product_name', 'manufacturer']:
        if result[field_name]['value'] and is_noise_text(result[field_name]['value']):
            logger.warning(f"Final validation rejected {field_name}: '{result[field_name]['value']}'")
            result[field_name] = {'value': None, 'confidence': 0.0}
    
    # Log results
    logger.info("Extraction complete:")
    for field in ['product_name', 'manufacturer', 'dangerous_goods_class', 'issue_date']:
        value = result[field].get('value')
        logger.info(f"  {field}: '{value}'")
    
    return result


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python working_parser.py <pdf_file>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: {pdf_path} not found")
        sys.exit(1)
    
    try:
        result = parse_pdf(pdf_path)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Parsing failed")
