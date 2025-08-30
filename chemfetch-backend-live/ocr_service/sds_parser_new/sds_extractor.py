import re
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

# Graceful imports for lightweight mode
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] PyMuPDF available")
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.info("[SDS_EXTRACTOR] PyMuPDF not available")

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] OCR libraries available")
except ImportError:
    OCR_AVAILABLE = False
    logger.info("[SDS_EXTRACTOR] OCR libraries not available")

# Fallback to pdfplumber for text extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] pdfplumber available")
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("[SDS_EXTRACTOR] pdfplumber not available")

# Always available fallback
try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] pdfminer.six available")
except ImportError:
    PDFMINER_AVAILABLE = False
    logger.error("[SDS_EXTRACTOR] pdfminer.six not available - this should not happen!")

# Patterns for parsing
SECTION_PATTERN = re.compile(r'^\s*(?:section\s*)?(\d{1,2})(?:\s|:|\.)(?=\s)', re.IGNORECASE | re.MULTILINE)

DATE_PATTERN = re.compile(
    r'(\b(?:Revision(?: Date)?|Issue Date|Date of issue|Version date|SDS creation date|Date Prepared|Issued)[^\n]{0,40})\s*[:]?\s*(?:\nPage[^\n]*\n)?\s*'
    r'((?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(?:[A-Za-z]+\s+\d{1,2},?\s*\d{4})|(?:\d{4}-\d{2}-\d{2}))',
    re.IGNORECASE)

FIELD_LABELS = {
    'product_name': [r'Product identifier', r'Product Name', r'Trade name'],
    'manufacturer': [r'Manufacturer', r'Supplier', r'Company name of supplier', r'Producer', r'Company'],
    'product_use': [r'Recommended use', r'Intended use', r'Use', r'Product use', r'Relevant identified uses', r'Identified uses'],
    'dangerous_goods_class': [r'DG Class', r'Class', r'Transport hazard class', r'(?:IMDG|IATA|ADG)?\s*Hazard Class', r'Australian Dangerous Goods class'],
    'subsidiary_risk': [r'Subsidiary risk'],
    'packing_group': [r'Packing group', r'PG', r'.*packing group', r'Australian Dangerous Goods packing group'],
}

# Additional keywords that frequently appear after labels but are not part of the field value
CONTACT_LABELS = [
    r'Telephone', r'Tel', r'Phone', r'Fax', r'E[-]?mail', r'Website',
    r'Emergency', r'Address', r'Poison', r'Product code'
]

# Flattened list of all label regexes for filtering
ALL_LABELS = [lab for labs in FIELD_LABELS.values() for lab in labs] + ['SDS no.', 'SDS number'] + CONTACT_LABELS

# Precompiled regex for detecting labels within values
LABEL_SPLIT_RE = re.compile(r"\b(?:" + "|".join(ALL_LABELS) + r")\b", re.IGNORECASE)


def extract_text(path: Path) -> str:
    """Extract text from PDF with multiple fallback methods and improved OCR triggering"""
    logger.info(f"[SDS_EXTRACTOR] Starting text extraction from: {path}")
    
    best_text = ""
    extraction_method = None
    
    # Method 1: PyMuPDF (if available - fastest)
    if PYMUPDF_AVAILABLE:
        try:
            logger.info("[SDS_EXTRACTOR] Attempting PyMuPDF text extraction...")
            doc = fitz.open(str(path))
            logger.info(f"[SDS_EXTRACTOR] PDF opened, pages: {len(doc)}")
            
            text = ""
            for i, page in enumerate(doc):
                page_text = page.get_text()
                text += page_text
                if i == 0:  # Log first page for debugging
                    logger.info(f"[SDS_EXTRACTOR] PyMuPDF page 1: {len(page_text)} chars")
            
            doc.close()
            logger.info(f"[SDS_EXTRACTOR] PyMuPDF extracted {len(text)} characters total")
            
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                extraction_method = "PyMuPDF"
                
        except Exception as e:
            logger.error(f"[SDS_EXTRACTOR] PyMuPDF extraction failed: {e}")
    
    # Method 2: pdfplumber (reliable for text-based PDFs)
    if PDFPLUMBER_AVAILABLE:
        try:
            logger.info("[SDS_EXTRACTOR] Attempting pdfplumber text extraction...")
            with pdfplumber.open(path) as pdf:
                text = ""
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    text += page_text
                    if i == 0:
                        logger.info(f"[SDS_EXTRACTOR] pdfplumber page 1: {len(page_text)} chars")
            
            logger.info(f"[SDS_EXTRACTOR] pdfplumber extracted {len(text)} characters total")
            
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                extraction_method = "pdfplumber"
                
        except Exception as e:
            logger.error(f"[SDS_EXTRACTOR] pdfplumber extraction failed: {e}")
    
    # Method 3: pdfminer.six fallback (always available)
    if PDFMINER_AVAILABLE:
        try:
            logger.info("[SDS_EXTRACTOR] Attempting pdfminer.six text extraction...")
            with open(path, 'rb') as f:
                text = pdfminer_extract(f)
            
            logger.info(f"[SDS_EXTRACTOR] pdfminer.six extracted {len(text)} characters")
            
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                extraction_method = "pdfminer.six"
                
        except Exception as e:
            logger.error(f"[SDS_EXTRACTOR] pdfminer.six extraction failed: {e}")
    
    # Check if we need OCR (insufficient text from all methods)
    text_length = len(best_text.strip())
    logger.info(f"[SDS_EXTRACTOR] Best text extraction: {text_length} chars using {extraction_method}")
    
    # Method 4: OCR fallback (if text is insufficient AND OCR is available)
    if text_length < 100 and OCR_AVAILABLE:
        try:
            logger.warning(f"[SDS_EXTRACTOR] Text too short ({text_length} chars), falling back to OCR...")
            logger.info("[SDS_EXTRACTOR] Converting PDF to images for OCR...")
            
            # Convert PDF to images
            images = convert_from_path(str(path), dpi=300, first_page=1, last_page=10)
            logger.info(f"[SDS_EXTRACTOR] Converted to {len(images)} images for OCR")
            
            ocr_text = ""
            for i, img in enumerate(images):
                try:
                    logger.info(f"[SDS_EXTRACTOR] Running OCR on page {i+1}...")
                    # Try different PSM modes for better results
                    page_text = pytesseract.image_to_string(img, config='--psm 1 -l eng')
                    ocr_text += f"\n--- Page {i+1} ---\n{page_text}"
                    logger.info(f"[SDS_EXTRACTOR] OCR page {i+1}: {len(page_text)} chars extracted")
                    
                    # Show a sample of what was extracted
                    if page_text.strip():
                        sample = page_text.strip()[:100].replace('\n', ' ')
                        logger.info(f"[SDS_EXTRACTOR] OCR page {i+1} sample: '{sample}...'")
                    
                except Exception as page_error:
                    logger.error(f"[SDS_EXTRACTOR] OCR failed for page {i+1}: {page_error}")
                    continue
            
            logger.info(f"[SDS_EXTRACTOR] OCR extracted {len(ocr_text)} characters total")
            
            if len(ocr_text.strip()) > text_length:
                logger.info(f"[SDS_EXTRACTOR] OCR successful! Using OCR text ({len(ocr_text)} chars)")
                return ocr_text
            else:
                logger.warning(f"[SDS_EXTRACTOR] OCR didn't improve results (OCR: {len(ocr_text)}, text: {text_length})")
                
        except Exception as e:
            logger.error(f"[SDS_EXTRACTOR] OCR extraction failed: {e}")
            import traceback
            logger.error(f"[SDS_EXTRACTOR] OCR traceback: {traceback.format_exc()}")
    
    elif text_length < 100 and not OCR_AVAILABLE:
        logger.error(f"[SDS_EXTRACTOR] Insufficient text ({text_length} chars) and OCR not available")
    elif text_length >= 100:
        logger.info(f"[SDS_EXTRACTOR] Sufficient text extracted ({text_length} chars), no OCR needed")
    
    if not best_text.strip():
        logger.error("[SDS_EXTRACTOR] All text extraction methods failed")
        return ""
    
    logger.info(f"[SDS_EXTRACTOR] Final text: {len(best_text)} chars using {extraction_method}")
    return best_text


def get_section(text: str, number: int) -> str:
    """Extract a specific numbered section from the SDS text"""
    pattern = re.compile(rf'^\s*(?:section\s*)?{number}\b[^\n]*', re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ''
    
    start = match.end()
    end = len(text)
    
    # Find the start of the next section
    for m in SECTION_PATTERN.finditer(text, start):
        num = int(m.group(1))
        if num > number:
            end = m.start()
            break
    
    return text[start:end]


def extract_after_label(section_text: str, labels):
    """Extract value that follows a label from Section text."""
    lines = section_text.splitlines()

    for i, line in enumerate(lines):
        clean = line.strip()
        if not clean:
            continue

        for label in labels:
            # Case 1: label and value on same line (colon/dash optional)
            same = re.search(rf"^{label}\b\s*(?:[:\-]\s*)?(.+)", clean, re.IGNORECASE)
            if same:
                value = same.group(1).strip()
                # Truncate at appearance of other labels/contact keywords
                trunc = LABEL_SPLIT_RE.search(value)
                if trunc:
                    value = value[:trunc.start()].strip()
                if value:
                    return value

            # Case 2: label alone on this line, value on next lines
            if re.fullmatch(label, clean, re.IGNORECASE):
                j = i + 1
                while j < len(lines):
                    candidate = lines[j].strip()
                    if not candidate:
                        j += 1
                        continue
                    # Handle value on separate line prefixed by a colon
                    if candidate.startswith(':'):
                        candidate = candidate[1:].strip()
                        if candidate and not LABEL_SPLIT_RE.search(candidate):
                            return candidate
                        j += 1
                        continue
                    if not LABEL_SPLIT_RE.search(candidate):
                        return candidate
                    j += 1

    return None


def extract_section14_field(sec14: str, labels, value_pattern):
    """Extract specific fields from Section 14 (Transport Information)"""
    lines = sec14.splitlines()
    value_re = re.compile(value_pattern, re.IGNORECASE)
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        for lab in labels:
            # Handle "Label: value" on the same line
            same_line = re.search(rf'{lab}\s*[:\-]?\s*({value_pattern})', stripped, re.IGNORECASE)
            if same_line:
                candidate = same_line.group(1).strip()
                if value_re.fullmatch(candidate):
                    return candidate
            
            # Label present in this line, value on subsequent line
            if re.search(lab, stripped, re.IGNORECASE):
                j = i + 1
                while j < len(lines):
                    candidate = lines[j].strip()
                    if candidate and not candidate.startswith(':'):
                        if not any(re.search(l, candidate, re.IGNORECASE) for l in ALL_LABELS):
                            if not re.match(r'^\d+\.[A-Za-z]', candidate):
                                if value_re.fullmatch(candidate):
                                    return candidate
                    j += 1
    
    return None


def parse_pdf(path: Path) -> Dict[str, Any]:
    """
    Parse SDS PDF and extract key information.
    Enhanced for lightweight deployment with graceful degradation and improved OCR fallback.
    
    Args:
        path: Path to the PDF file
        
    Returns:
        Dictionary with extracted SDS data
    """
    logger.info(f"[SDS_EXTRACTOR] Starting PDF parsing: {path}")
    logger.info(f"[SDS_EXTRACTOR] File size: {path.stat().st_size / (1024*1024):.2f} MB")
    logger.info(f"[SDS_EXTRACTOR] Available extraction methods: PyMuPDF={PYMUPDF_AVAILABLE}, pdfplumber={PDFPLUMBER_AVAILABLE}, OCR={OCR_AVAILABLE}")
    
    # Step 1: Extract text
    logger.info("[SDS_EXTRACTOR] Step 1: Extracting text from PDF...")
    try:
        text = extract_text(path)
        text_length = len(text.strip())
        logger.info(f"[SDS_EXTRACTOR] Text extraction complete, total length: {text_length}")
        
        # Enhanced debugging for short text
        if text_length < 100:
            logger.warning(f"[SDS_EXTRACTOR] Very short text extracted ({text_length} chars)")
            logger.info(f"[SDS_EXTRACTOR] Text sample: '{text.strip()[:200]}'")
            
            # If we have OCR available, this should have been handled in extract_text()
            if OCR_AVAILABLE:
                logger.error("[SDS_EXTRACTOR] OCR was available but insufficient text still extracted")
            else:
                logger.error("[SDS_EXTRACTOR] OCR not available and insufficient text extracted")
            
            return {
                "error": "Insufficient text extracted from PDF",
                "text_length": text_length,
                "text_sample": text.strip()[:200] if text.strip() else "",
                "available_methods": {
                    "pymupdf": PYMUPDF_AVAILABLE,
                    "pdfplumber": PDFPLUMBER_AVAILABLE, 
                    "ocr": OCR_AVAILABLE
                },
                "extraction_mode": "text-only" if not OCR_AVAILABLE else "full",
                "debug_info": "OCR fallback should have triggered but didn't"
            }
    except Exception as e:
        logger.error(f"[SDS_EXTRACTOR] Text extraction failed: {e}")
        import traceback
        logger.error(f"[SDS_EXTRACTOR] Extraction traceback: {traceback.format_exc()}")
        return {
            "error": f"Text extraction failed: {e}",
            "available_methods": {
                "pymupdf": PYMUPDF_AVAILABLE,
                "pdfplumber": PDFPLUMBER_AVAILABLE,
                "ocr": OCR_AVAILABLE
            },
            "extraction_mode": "text-only" if not OCR_AVAILABLE else "full"
        }
    
    result = {
        "extraction_info": {
            "text_length": len(text),
            "available_methods": {
                "pymupdf": PYMUPDF_AVAILABLE,
                "pdfplumber": PDFPLUMBER_AVAILABLE,
                "ocr": OCR_AVAILABLE
            },
            "extraction_mode": "text-only" if not OCR_AVAILABLE else "full"
        }
    }
    
    # Step 2: Extract sections
    logger.info("[SDS_EXTRACTOR] Step 2: Extracting sections...")
    sec1 = get_section(text, 1)
    sec14 = get_section(text, 14)
    
    logger.info(f"[SDS_EXTRACTOR] Section 1 length: {len(sec1)} chars")
    logger.info(f"[SDS_EXTRACTOR] Section 14 length: {len(sec14)} chars")
    
    # Step 3: Extract fields
    logger.info("[SDS_EXTRACTOR] Step 3: Extracting fields...")
    
    # Product name with fallback logic
    product_name = extract_after_label(sec1, FIELD_LABELS['product_name'])
    if not product_name or 'sds' in product_name.lower():
        # Try to find a reasonable product name from section 1
        candidates = []
        for line in sec1.splitlines():
            line = line.strip()
            if not line or line.startswith(':'):
                continue
            if any(re.fullmatch(lab, line, re.IGNORECASE) for lab in ALL_LABELS):
                continue
            if any(x in line.lower() for x in ['use', 'telephone', 'emergency', 'poison', 'fax', 'website', 'email']):
                continue
            if re.match(r'^\d', line):
                continue
            candidates.append(line)
        product_name = candidates[-1] if candidates else None
    
    result['product_name'] = {'value': product_name, 'confidence': 1.0 if product_name else 0.0}
    
    # Manufacturer
    manufacturer = extract_after_label(sec1, FIELD_LABELS['manufacturer'])
    if not manufacturer:
        # Try alternative pattern grabbing first non-empty line after heading
        m = re.search(r'Details of the supplier[^\n]*\n\s*([^\n]+)', sec1, re.IGNORECASE)
        if m:
            manufacturer = m.group(1).strip()
    result['manufacturer'] = {'value': manufacturer, 'confidence': 1.0 if manufacturer else 0.0}
    
    # Product use
    value = extract_after_label(sec1, FIELD_LABELS['product_use'])
    result['product_use'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    
    # Section 14 fields (Transport Information)
    value = extract_section14_field(sec14, FIELD_LABELS['dangerous_goods_class'], r'\d[0-9A-Za-z\.]*|not\b.*|none')
    result['dangerous_goods_class'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    
    value = extract_section14_field(sec14, FIELD_LABELS['subsidiary_risk'], r'\d[0-9A-Za-z\.]*|none|not\b.*')
    result['subsidiary_risk'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    
    value = extract_section14_field(sec14, FIELD_LABELS['packing_group'], r'I{1,3}|IV|V|N\.?/?A|none|not\b.*')
    if not value:
        value = extract_section14_field(sec14, FIELD_LABELS['packing_group'], r'\d+|N\.?/?A|none|not\b.*')
    result['packing_group'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    
    # Issue date extraction
    matches = list(DATE_PATTERN.finditer(text))
    chosen = None
    chosen_iso = None
    
    if matches:
        try:
            from datetime import date
            from dateutil import parser as dateparser
            
            today = date.today()
            for m in matches:
                label = m.group(1).lower()
                candidate = m.group(2).strip()
                
                try:
                    # Parse with dayfirst=True for Australian format (DD/MM/YYYY)
                    d = dateparser.parse(candidate, dayfirst=True).date()
                    if d > today:  # Skip future dates
                        continue
                    
                    # Convert to ISO format
                    chosen_iso = d.strftime('%Y-%m-%d')
                    logger.info(f"[SDS_EXTRACTOR] Parsed date '{candidate}' as {d} -> ISO: {chosen_iso}")
                    
                    # Prefer issue/prepared dates
                    if any(key in label for key in ['issue', 'prepared', 'issued', 'creation']):
                        chosen = chosen_iso
                        break
                    if not chosen:
                        chosen = chosen_iso
                        
                except Exception as e:
                    logger.warning(f"[SDS_EXTRACTOR] Failed to parse date '{candidate}': {e}")
                    continue
                    
        except ImportError:
            logger.warning("[SDS_EXTRACTOR] python-dateutil not available, skipping date parsing")
            chosen = None
    
    result['issue_date'] = {'value': chosen, 'confidence': 1.0 if chosen else 0.0}
    
    # Step 4: Summary logging
    logger.info("[SDS_EXTRACTOR] Step 4: Parsing complete. Results summary:")
    for key, value in result.items():
        if key == 'extraction_info':
            continue
        conf = value.get('confidence', 0) if isinstance(value, dict) else 0
        val = value.get('value', value) if isinstance(value, dict) else value
        logger.info(f"[SDS_EXTRACTOR]   {key}: '{val}' (confidence: {conf})")
    
    return result


if __name__ == '__main__':
    import json
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python sds_extractor.py <pdf_file> [pdf_file2] ...]")
        sys.exit(1)
    
    for pdf_path in sys.argv[1:]:
        path = Path(pdf_path)
        if not path.exists():
            print(f"Error: {pdf_path} not found")
            continue
            
        print(f"\n{'='*50}")
        print(f"Processing: {pdf_path}")
        print('='*50)
        
        try:
            result = parse_pdf(path)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Error parsing {pdf_path}: {e}")
            logger.error(f"[SDS_EXTRACTOR] Failed to parse {pdf_path}: {e}")
