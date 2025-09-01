#!/usr/bin/env python3
"""
FIXED SDS extractor - preserves working functionality while addressing specific issues
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

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except Exception:
    convert_from_path = None
    pytesseract = None
    OCR_AVAILABLE = False

try:
    # Prefer modular extractors for better maintainability
    from .modules.section_1 import (
        description as fe_extract_description,
        product_name as fe_extract_product_name,
        manufacturer as fe_extract_manufacturer,
    )
    from .modules.field_extractor import (
        extract_section14_field as fe_extract_section14_field,
        extract_date_from_header as fe_extract_date_from_header,
    )
except ImportError:  # pragma: no cover - fallback when run as script
    from modules.section_1 import (
        description as fe_extract_description,
        product_name as fe_extract_product_name,
        manufacturer as fe_extract_manufacturer,
    )
    from modules.field_extractor import (
        extract_section14_field as fe_extract_section14_field,
        extract_date_from_header as fe_extract_date_from_header,
    )

# Common field labels used to trim values when multiple labels appear on one line
COMMON_FIELD_LABELS = [
    r'Product\s+identifier',
    r'Product\s+name',
    r'Trade\s+name',
    r'Commercial\s+product\s+name',
    r'Manufacturer',
    r'Supplier\s+Name',
    r'Supplier',
    r'Company\s+name\s+of\s+supplier',
    r'Producer',
    r'Company\s+name',
    r'Registered\s+company\s+name',
    r'Distributor',
    r'Product\s+description',
    r'Description',
    r'Use\s+of\s+the\s+substance',
    r'Recommended\s+use',
    r'Intended\s+use',
    r'Product\s+use',
    r'Relevant\s+identified\s+uses',
    r'Identified\s+uses',
    r'Application',
    r'Chemical\s+Name',
    r'Product\s+code',
    r'Synonyms?',
    r'Proper\s+shipping\s+name',
    r'UN\s+number',
    r'Hazchem',
    r'EPG',
    r'Packing\s*Group(?:\(s\))?',
    r'Hazard\s*class(?:\(es\))?',
]


def is_noise_text(text: str) -> bool:
    """Check if text is likely noise that shouldn't be extracted as field values."""
    if not text:
        return True

    text = text.strip()
    if not text:
        return True

    # Allow short numeric values like "9" for DG class
    if len(text) < 2 and not re.match(r"^\d(?:\.\d)?$", text):
        return True

    # Specific noise patterns found in test results
    noise_patterns = [
        r'^MSDS\s+Date$',
        r'^Alternative\s+number\(s\)$',
        r'^Facsimile\s+Number$',
        r'^safety\s+data\s+sheet$',
        r'^Name$',
        r'^Registered\s+company\s+name$',
        r'^\:$',
        r"^[’'`´]s$",
        r'^UK,?\s+NPIS.*\d{2,4}\s+\d{2,4}\s+\d{2,4}',
        r'^Australia\s+-\s+\d{2,4}\s+\d{2,4}\s+\d{2,4}',
        r'^\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}',
        r'^Emergency\s+telephone',
        r'^Contact\s+details',
        r'^Details\s+of\s+the\s+supplier$',
        r'^Telephone',
        r'^Phone',
        r'^Fax',
        r'^Email',
        r'^Address',
        r'^Website',
        r'^Emergency\s+Telephone\s+Number$',
        r'^Company[:.]?\s*$',
        r'^Company\s+No\.?[:.]?\s*$',
        r'^Other\s+Name\(s\)$',
        r'^Formulation\s+#$',
        r'^Registration\s+no\.?\s*–?\s*US:?\s*$',
        r'^Group$',
        r'^Synonyms',
        r'^Product\s+Code',
        r'^HS\s+Code',
        r'^-\s*-$'
    ]

    for pattern in noise_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            logger.debug("Rejecting noise text: '%s' (matched: %s)", text, pattern)
            return True

    return False


def dedup_repeated_phrase(value: str) -> str:
    """Collapse exact duplicated phrases like 'Chemtools Pty Ltd Chemtools Pty Ltd'."""
    if not value:
        return value
    # Trim excessive whitespace
    cleaned = re.sub(r"\s+", " ", value).strip()
    # If the whole phrase is repeated twice, collapse
    m = re.match(r"^(?P<p>.+?)\s+(?P=p)$", cleaned)
    if m:
        return m.group('p')
    return cleaned


def strip_leading_label_prefix(value: str) -> str:
    """Remove leading field labels that may have leaked into values."""
    if not value:
        return value
    patterns = [
        r"^(?:product\s+identifier)\s*[:\-]?\s*",
        r"^(?:product\s+name)\s*[:\-]?\s*",
        r"^(?:trade\s+name)\s*[:\-]?\s*",
        r"^(?:commercial\s+product\s+name)\s*[:\-]?\s*",
        r"^(?:manufacturer|supplier\s+name|supplier|company\s+name\s+of\s+supplier|producer|company\s+name|registered\s+company\s+name|distributor)\s*[:\-]?\s*",
    ]
    out = value
    for pat in patterns:
        out = re.sub(pat, "", out, flags=re.IGNORECASE).strip()
    return out


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
    """Extract text using available PDF libraries, preferring the most complete output."""

    text = ""

    if PDFPLUMBER_AVAILABLE and pdfplumber:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using pdfplumber")
                return text
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}")

    if PYMUPDF_AVAILABLE and fitz:
        try:
            doc = fitz.open(str(pdf_path))
            for page in doc:
                text += page.get_text()  # type: ignore
            doc.close()
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using PyMuPDF")
                return text
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}")

    if PDFMINER_AVAILABLE and pdfminer_extract:
        try:
            with open(pdf_path, 'rb') as f:
                text = pdfminer_extract(f)  # type: ignore
            if text and text.strip():
                logger.info(f"Extracted {len(text)} chars using pdfminer")
                return text
        except Exception as e:
            logger.warning(f"pdfminer failed: {e}")

    if OCR_AVAILABLE and convert_from_path and pytesseract:
        try:
            images = convert_from_path(str(pdf_path))
            for image in images:
                text += pytesseract.image_to_string(image)
            if text.strip():
                logger.info(f"Extracted {len(text)} chars using OCR")
                return text
        except Exception as e:
            logger.warning(f"OCR failed: {e}")

    logger.error("All text extraction methods failed")
    return ""


def get_section(text: str, section_num: int) -> str:
    """Extract a specific section from SDS text with robust boundaries.

    Strategy:
    - Prefer clear section headers that start a line and are either "Section N"
      or "N." / "N:" followed by a plausible title.
    - For Section 1 and 14, further require common title keywords to avoid
      matching numbered list items (e.g., "1. Classified by Chemwatch").
    - If strict matching fails (rare layouts), fall back to a looser regex similar
      to previous logic.
    """
    # Build start pattern
    if section_num == 1:
        start_pat = rf'^\s*(?:section\s*)?1\s*[:\.]?\s.*identification.*$'
    elif section_num == 14:
        start_pat = rf'^\s*(?:section\s*)?14\s*[:\.]?\s.*transport.*$'
    else:
        # Require punctuation after number to avoid addresses like "2 Fred ..."
        start_pat = rf'^\s*(?:section\s*)?{section_num}\s*[:\.]\s.*$'

    next_pat = r'^\s*(?:section\s*)?\d{1,2}\s*[:\.]\s'

    start_m = re.search(start_pat, text, re.IGNORECASE | re.MULTILINE)
    if start_m:
        start = start_m.start()
        # Find the next header after start
        next_m = re.search(next_pat, text[start+1:], re.IGNORECASE | re.MULTILINE)
        end = (start + 1 + next_m.start()) if next_m else len(text)
        return text[start:end]

    # Fallback (looser) single pass, keeps prior behavior if strict fails
    loose = rf'(?:^|\n)\s*(?:section\s*)?{section_num}(?!\s*/)(?:\s|:|\.).*?' \
            rf'(?=\n\s*(?:section\s*)?\d{{1,2}}(?!\.\d)(?!\s*/)(?:\s|:|\.)|$)'
    m2 = re.search(loose, text, re.IGNORECASE | re.DOTALL)
    return m2.group(0) if m2 else ""


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
            pattern = rf'^{label}\s*[:\-]?\s*(.+)$'
            match = re.search(pattern, line, re.IGNORECASE)
            if not match:
                pattern = rf'{label}\s*[:\-]\s*(.+)'
                match = re.search(pattern, line, re.IGNORECASE)
            if match:
                value = match.group(1).strip()

                # Remove leading possessive artifacts like various apostrophes followed by s
                value = re.sub(r"^[’'`´]+s\b\s*", "", value)

                value = re.sub(r'\s*[:\-]\s*$', '', value)
                value = re.sub(r'\s+(Tel|Phone|Fax|Email|Emergency).*$', '', value, re.IGNORECASE)

                for other in COMMON_FIELD_LABELS:
                    other_match = re.search(other + r'\s*[:\-]?', value, re.IGNORECASE)
                    if other_match:
                        value = value[:other_match.start()].strip()
                        break

                value = re.sub(r'\b[A-Z0-9]{2,}[/A-Z0-9\-]*$', '', value).strip()

                if any('manufacturer' in str(label).lower() or 'supplier' in str(label).lower() for label in field_labels):
                    if re.match(r'^of\s+the\s+safety\s+data\s+sheet\s*$', value, re.IGNORECASE):
                        continue

                if value and not is_noise_text(value):
                    return value
            
            # Pattern: Label on one line, value on next
            if re.match(rf'^{label}\s*[:\-]?\s*$', line, re.IGNORECASE):
                for j in range(i + 1, min(i + 6, len(lines))):
                    candidate = lines[j].strip()
                    if not candidate or candidate == ':':
                        continue
                    if candidate.startswith(':'):
                        continue

                    value = re.sub(r'\s*[:\-]\s*$', '', candidate)
                    value = re.sub(r'\s+(Tel|Phone|Fax|Email|Emergency).*$', '', value, re.IGNORECASE)
                    for other in COMMON_FIELD_LABELS:
                        other_match = re.search(other + r'\s*[:\-]?', value, re.IGNORECASE)
                        if other_match:
                            value = value[:other_match.start()].strip()
                            break
                    value = re.sub(r'\b[A-Z0-9]{2,}[/A-Z0-9\-]*$', '', value).strip()

                    # Remove leading possessive artifacts like various apostrophes followed by s
                    value = re.sub(r"^[’'`´]+s\b\s*", "", value)

                    if value and not is_noise_text(value):
                        return value
    
    return None


def extract_dg_class_from_table(section_text: str) -> Optional[str]:
    """Extract DG class from tabular section 14 layouts."""
    if not section_text:
        return None

    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    header_index = None
    for idx, line in enumerate(lines):
        if re.search(r'DG\s+Class|Class\s*:', line, re.IGNORECASE):
            header_index = idx
            break

    if header_index is None:
        return None

    # Look in the header line and next few lines for DG class value
    for line in lines[header_index: header_index + 6]:
        tokens = re.split(r'\s+', line.replace('|', ' '))
        for token in tokens:
            token = token.strip(',;')
            if validate_dangerous_goods_class(token):
                logger.info(f"[SDS_EXTRACTOR] Found DG class in table: '{token}'")
                return token

    return None


def extract_packing_group_from_table(section_text: str) -> Optional[str]:
    """Extract packing group from tabular layouts."""
    if not section_text:
        return None

    lines = section_text.splitlines()
    
    # Look for packing group in table format
    for i, line in enumerate(lines):
        if re.search(r'packing\s+group', line, re.IGNORECASE):
            # Check same line for value after the header
            parts = re.split(r'\s{2,}|\t|\|', line)  # Split on multiple spaces, tabs, or pipes
            if len(parts) > 1:
                for part in parts[1:]:  # Skip the header part
                    part = part.strip(',;')
                    if part and re.match(r'^(I{1,3}|IV?|N\.?/?A\.?|None|Not\s+(?:applicable|required|assigned)|Not\s+subject)$', part, re.IGNORECASE):
                        logger.info(f"[SDS_EXTRACTOR] Found packing group in table: '{part}'")
                        return part
            
            # Check next few lines for table data
            for j in range(i + 1, min(i + 4, len(lines))):
                table_line = lines[j].strip()
                if not table_line:
                    continue
                
                # Split table row into cells
                cells = re.split(r'\s{2,}|\t|\|', table_line)
                for cell in cells:
                    cell = cell.strip(',;')
                    if cell and re.match(r'^(I{1,3}|IV?|N\.?/?A\.?|None|Not\s+(?:applicable|required|assigned)|Not\s+subject)$', cell, re.IGNORECASE):
                        logger.info(f"[SDS_EXTRACTOR] Found packing group in table row: '{cell}'")
                        return cell
    
    return None


def extract_product_name(section1_text: str) -> Optional[str]:
    """Extract product name with multiple strategies - FIXED to avoid labels."""
    
    # Strategy 0: Use modular extractor first
    try:
        mod_val = fe_extract_product_name(section1_text)
        if mod_val:
            return mod_val
    except Exception:
        pass

    # Strategy 1: Look for explicit labels
    labels = [
        r'Product\s+identifier',
        r'Product\s+name',
        r'Trade\s+name',
        r'Commercial\s+product\s+name'
    ]
    
    result = extract_field_value("", labels, section1_text)
    if result and not is_noise_text(result):
        # Additional validation - reject obvious labels and company suffixes
        if not re.match(r'^(Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company|Alternative\s+number\(s\)|Other\s+Name\(s\)|Formulation\s+#|Registration\s+no\.?\s*–?\s*US:?|Group)$', result, re.IGNORECASE):
            # Reject transport/composition phrases sometimes picked up as values
            lowered = result.lower()
            # Also reject if the result is itself a generic label like 'Product Identifier'
            if re.fullmatch(r'(product\s+identifier|product\s+name|trade\s+name|commercial\s+product\s+name)', lowered):
                pass
            elif any(tok in lowered for tok in ['proper shipping name', 'chemical formula', 'un number']) or lowered in ['not applicable', 'n/a', 'na']:
                pass
            else:
                cleaned = strip_leading_label_prefix(result)
                cleaned = dedup_repeated_phrase(cleaned)
                logger.info(f"[SDS_EXTRACTOR] Product name from label: '{cleaned}'")
                return cleaned or None
    
    # Strategy 2: Look for meaningful product-like text in early lines (RESTORE WORKING LOGIC)
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
        if re.match(r'^synonym\(s\)', line, re.IGNORECASE):
            continue
        if re.match(r'^(use\(s\)|use of the substance|recommended use)', line, re.IGNORECASE):
            continue
        if re.match(r'^(msds|sds)\s+date\b', line, re.IGNORECASE):
            continue
        if is_noise_text(line):
            continue
        
        # Check if line looks like a product name (has alphanumeric content, reasonable length)
        if re.search(r'[A-Za-z0-9]', line) and 3 <= len(line) <= 100:
            # Avoid lines that are obviously not product names
            if not re.search(r'@|www\.|\.com|\.org', line, re.IGNORECASE):
                if not re.match(r'^[:\-\s]+$', line):
                    # Additional check to avoid obvious label patterns
                    if not re.match(r'^(Alternative\s+number\(s\)|Other\s+Name\(s\)|Formulation\s+#|Registration\s+no\.?\s*–?\s*US:?|Group)$', line, re.IGNORECASE):
                        # Skip common transport-related labels
                        lowered = line.lower()
                        if any(tok in lowered for tok in ['proper shipping name', 'shipping name', 'un number', 'transport', 'hazchem', 'epg', 'chemical formula', 'not applicable']):
                            continue
                        # Skip date headers that sometimes appear as standalone lines
                        if re.match(r'^(msds\s+date|date\s+of\s+issue|revision\s+date|version\s+date)\b', lowered, re.IGNORECASE):
                            continue
                        candidate = strip_leading_label_prefix(line)
                        candidate = dedup_repeated_phrase(candidate)
                        logger.info(f"Found potential product name: '{candidate}'")
                        return candidate or None
    
    return None


def extract_manufacturer(section1_text: str) -> Optional[str]:
    """Extract manufacturer with multiple strategies - FIXED to avoid labels."""
    
    # Strategy 0: Use modular extractor first
    try:
        mod_val = fe_extract_manufacturer(section1_text)
        if mod_val:
            return mod_val
    except Exception:
        pass

    # Strategy 1: Look for explicit labels
    labels = [
        r'Manufacturer',
        r'Supplier\s+Name', 
        r'Supplier',
        r'Company\s+name\s+of\s+supplier',
        r'Producer',
        r'Company\s+name',
        r'Registered\s+company\s+name',
        r'Distributor'
    ]
    
    result = extract_field_value("", labels, section1_text)
    if result and not is_noise_text(result):
        # Additional validation - reject obvious noise fragments
        if not re.match(r'^(of\s+the\s+safety\s+data\s+sheet|Emergency\s+Telephone\s+Number|Company[:.]?\s*$|Company\s+No\.?[:.]?\s*$)$', result, re.IGNORECASE):
            cleaned = strip_leading_label_prefix(result)
            cleaned = dedup_repeated_phrase(cleaned)
            logger.info(f"[SDS_EXTRACTOR] Manufacturer from label: '{cleaned}'")
            return cleaned or None
    
    # Strategy 2: Look in "Details of the supplier" section (RESTORE WORKING LOGIC)
    supplier_match = re.search(r'Details\s+of\s+the\s+supplier[^\n]*\n(.{1,500}?)(?:\n\s*[A-Z][a-z]|\n\s*\d|$)', 
                              section1_text, re.IGNORECASE | re.DOTALL)
    if supplier_match:
        supplier_section = supplier_match.group(1)
        lines = supplier_section.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not is_noise_text(line) and len(line) > 3:
                # Skip phone numbers and obvious noise
                if not re.search(r'\b\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}\b', line):
                    if not re.match(r'^(Emergency\s+Telephone\s+Number|Company[:.]?\s*$)', line, re.IGNORECASE):
                        # Skip generic SDS headers if they slipped through
                        if re.search(r'safety\s+data\s+sheet|^section\b|^page\b', line, re.IGNORECASE):
                            continue
                        cleaned = strip_leading_label_prefix(line)
                        cleaned = dedup_repeated_phrase(cleaned)
                        logger.info(f"[SDS_EXTRACTOR] Manufacturer from supplier details: '{cleaned}'")
                        return cleaned or None
    
    return None


def extract_description(section1_text: str) -> Optional[str]:
    """Extract product description/use information from Section 1."""
    try:
        return fe_extract_description(section1_text)
    except Exception:
        # Fall back to legacy inline label extraction
        return extract_field_value(
            section1_text,
            [
                r'Product\s+description',
                r'Description',
                r'Use\s+of\s+the\s+substance',
                r'Recommended\s+use',
                r'Intended\s+use',
                r'Product\s+use',
                r'Relevant\s+identified\s+uses',
                r'Identified\s+uses',
                r'Application',
            ],
            section1_text,
        )

def extract_manufacturer_global(full_text: str) -> Optional[str]:
    """Fallback manufacturer search across the first page/lines of the document.
    Avoids section scoping issues when details are outside Section 1.
    """
    if not full_text:
        return None
    head = "\n".join(full_text.splitlines()[:60])
    labels = [
        r'Manufacturer',
        r'Supplier\s+Name',
        r'Supplier',
        r'Company\s+name\s+of\s+supplier',
        r'Producer',
        r'Company\s+name',
        r'Registered\s+company\s+name',
        r'Distributor',
        r'Manufacturer\s*/\s*Supplier',
        r'Details\s+of\s+the\s+supplier',
    ]
    val = extract_field_value(head, labels, head)
    if val and not is_noise_text(val):
        return strip_leading_label_prefix(dedup_repeated_phrase(val))
    return None


def extract_date(text: str) -> Optional[str]:
    """Extract issue/revision date with enhanced patterns and prioritization.

    Priority: Issue/Revision/Prepared (and similar) over Print/Printed.
    """

    # 1) Prefer modular labeled extraction (captures and prioritizes by label)
    try:
        try:
            from .modules.date_parser import extract_issue_date as mod_extract_issue_date
        except ImportError:  # pragma: no cover
            from modules.date_parser import extract_issue_date as mod_extract_issue_date
        labeled = mod_extract_issue_date(text)
        if labeled:
            return labeled
    except Exception:
        pass

    # 2) Fallback to explicit labeled regexes (legacy)
    date_patterns = [
        # Labeled + various formats, including dd-MMM-YYYY
        r'(?:Issue\s*Date|Revision(?:\s*Date)?|Date\s*of\s*issue|Version\s*date|Date\s*Prepared|Prepared\s*on|Issued|MSDS\s*Date)[^\n]{0,30}?[:\-]?\s*' \
        r'(\d{1,2}[\-\/\.]+\d{1,2}[\-\/\.]+\d{2,4}|\d{4}-\d{2}-\d{2}|[A-Za-z]+\.?\s+\d{1,2},?\s*\d{4}|\d{1,2}\s+[A-Za-z]+\.?\s+\d{4}|\d{1,2}[\-\/.][A-Za-z]{3,}\.?[\-\/.]\d{2,4})',
        r'Revision[:\s]*(\d{4}-\d{2}-\d{2})',
        r'Revision[:\s]*(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{4})',
        r'Revision[:\s]*(\d{1,2}[\-\/.][A-Za-z]{3,}\.?[\-\/.]\d{2,4})',
        r'REVISION\s+DATE[:\s]*(\d{1,2}\s+\w+\.?\s+\d{4})',
        r'REVISION\s+DATE[:\s]*(\d{1,2}[\-\/]\d{1,2}[\-\/]\d{4})',
        r'REVISION\s+DATE[:\s]*(\d{1,2}[\-\/.][A-Za-z]{3,}\.?[\-\/.]\d{2,4})',
    ]
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                from datetime import datetime, date
                for date_str in matches:
                    # Normalize month abbreviations with trailing dot
                    cleaned = re.sub(r'\b([A-Za-z]{3,})\.', r'\1', date_str)
                    for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%d %b %Y', '%d %B %Y', '%b %d %Y', '%B %d %Y', '%d-%b-%Y', '%d-%b-%y', '%d.%b.%Y', '%d.%b.%y']:
                        try:
                            parsed_date = datetime.strptime(cleaned, fmt).date()
                            if parsed_date <= date.today():
                                return parsed_date.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
            except ImportError:
                return matches[0]

    # 3) Finally, header-based extraction (includes print/printing date variants)
    try:
        hdr = fe_extract_date_from_header(text)
        if hdr:
            return hdr
    except Exception:
        pass

    return None


def parse_pdf(path: Path) -> Dict[str, Any]:
    """Main parsing function that fixes the specific issues found in testing."""
    
    logger.info(f"Starting to parse: {path}")
    
    # Extract text
    text = extract_text_from_pdf(path)
    if not text:
        return {
            "error": "Could not extract text from PDF",
            "extraction_info": {
                "text_length": 0,
                "available_methods": {
                    "pymupdf": PYMUPDF_AVAILABLE,
                    "pdfplumber": PDFPLUMBER_AVAILABLE,
                    "pdfminer": PDFMINER_AVAILABLE
                },
                "extraction_mode": "full"
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
            "extraction_mode": "full"
        }
    }
    
    # Product name
    product_name = extract_product_name(section1)
    prefix = '\n'.join(text.splitlines()[:15])
    if not product_name:
        product_name = extract_product_name(prefix)
    # If the found name looks like a date label (e.g., "MSDS Date ..."), prefer header/prefix-derived name
    if product_name and re.match(r'^(msds\s+date|date\s+of\s+issue|revision\s+date|version\s+date)\b', str(product_name), re.IGNORECASE):
        alt = extract_product_name(prefix)
        if alt and not re.match(r'^(msds\s+date|date\s+of\s+issue|revision\s+date|version\s+date)\b', alt, re.IGNORECASE):
            product_name = alt
    result['product_name'] = {'value': product_name, 'confidence': 1.0 if product_name else 0.0}
    
    # Manufacturer
    manufacturer = extract_manufacturer(section1)
    if not manufacturer:
        # Fallback to global scan in case supplier/manufacturer details sit outside Section 1
        manufacturer = extract_manufacturer_global(text)
    # Final cleanup to remove any leaked labels or concatenated fields
    if manufacturer:
        # Trim anything after Product Name/Trade name label fragments
        manufacturer = re.split(r'\b(Product\s+Name|Trade\s+name)\b', manufacturer, flags=re.IGNORECASE)[0].strip()
        manufacturer = strip_leading_label_prefix(dedup_repeated_phrase(manufacturer))
    result['manufacturer'] = {'value': manufacturer, 'confidence': 1.0 if manufacturer else 0.0}
    
    # Product description (NEW FIELD - from Section 1 only)
    description = extract_description(section1)
    result['description'] = {'value': description, 'confidence': 1.0 if description else 0.0}

    # Product use (keeping existing for compatibility)
    product_use = extract_field_value(text, [
        r'Recommended\s+use',
        r'Intended\s+use',
        r'Use\s+of\s+the\s+substance',
        r'Product\s+use',
        r'Relevant\s+identified\s+uses'
    ], section1)
    result['product_use'] = {'value': product_use, 'confidence': 1.0 if product_use else 0.0}
    
    # Dangerous goods class (from Section 14) - RESTORE WORKING LOGIC
    # Prefer modular Section 14 extractor; fallback to legacy patterns
    dg_labels = [
        r'DG\s*Class',
        r'Class',
        r'Class/Division',
        r'Transport\s*hazard\s*class(?:\(es\))?',
        r'(?:IMDG|IATA|ADG)?\s*Hazard\s*Class(?:\(es\))?',
        r'Hazard\s*class(?:\(es\))?',
        r'Dangerous\s*goods\s*class',
        r'UN\s*Class',
    ]
    dg_class = None
    try:
        dg_class = fe_extract_section14_field(section14, dg_labels, 'dangerous_goods_class')
    except Exception:
        dg_class = None
    if not dg_class:
        dg_class = extract_field_value(text, dg_labels, section14)
    if not dg_class:
        dg_class = extract_dg_class_from_table(section14)

    # Validate dangerous goods class
    if dg_class and not validate_dangerous_goods_class(dg_class):
        logger.warning("Invalid DG class rejected: '%s'", dg_class)
        dg_class = None
    
    result['dangerous_goods_class'] = {'value': dg_class, 'confidence': 1.0 if dg_class else 0.0}
    
    # Subsidiary risk
    subsidiary_risk = extract_field_value(text, [r'Subsidiary\s+risk'], section14)
    result['subsidiary_risk'] = {'value': subsidiary_risk, 'confidence': 1.0 if subsidiary_risk else 0.0}
    
    # Packing group - RESTORE WORKING LOGIC + ADD TABLE SUPPORT
    # Packing group via modular extractor, with fallbacks
    pg_labels = [
        r'Packing\s*group(?:\(s\))?',
        r'Packing\s*group\s*\(if\s*applicable\)',
        r'PG',
    ]
    packing_group = None
    try:
        packing_group = fe_extract_section14_field(section14, pg_labels, 'packing_group')
    except Exception:
        packing_group = None
    if not packing_group:
        packing_group = extract_field_value(text, pg_labels, section14)
    if not packing_group:
        packing_group = extract_packing_group_from_table(section14)
    
    result['packing_group'] = {'value': packing_group, 'confidence': 1.0 if packing_group else 0.0}
    
    # Issue date - ENHANCED EXTRACTION
    issue_date = extract_date(text)
    result['issue_date'] = {'value': issue_date, 'confidence': 1.0 if issue_date else 0.0}
    
    # Final validation - remove any remaining noise (BE MORE CONSERVATIVE)
    label_like_pattern = re.compile(r'(product\s+identifier|product\s+name|trade\s+name|commercial\s+product\s+name)\s*$', re.IGNORECASE)
    header_like_pattern = re.compile(r'^\s*\d+\.?\s*(identification|hazard)\b', re.IGNORECASE)
    for field_name in ['product_name', 'manufacturer']:
        val = result[field_name]['value']
        if val and (is_noise_text(val) or label_like_pattern.fullmatch(str(val).strip() or '') or (field_name == 'product_name' and header_like_pattern.match(str(val)))):
            logger.warning(f"Final validation rejected {field_name}: '{val}'")
            result[field_name] = {'value': None, 'confidence': 0.0}
    
    # Log results
    logger.info("Extraction complete:")
    for field in ['product_name', 'manufacturer', 'description', 'dangerous_goods_class', 'issue_date']:
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
