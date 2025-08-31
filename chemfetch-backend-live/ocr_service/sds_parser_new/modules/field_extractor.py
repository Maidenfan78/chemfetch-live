"""
Field extraction module
"""
import re
import logging
from typing import List, Optional

from .config import FIELD_LABELS
from .utils import is_noise_text, validate_dangerous_goods_class
from .config import VALID_PACKING_GROUPS

logger = logging.getLogger(__name__)


def extract_after_label(section_text: str, labels: List[str], field_name: str = '') -> Optional[str]:
    """Extract value that follows a label from section text with improved validation."""
    if not section_text:
        return None
        
    lines = section_text.splitlines()
    
    for i, line in enumerate(lines):
        clean = line.strip()
        if not clean:
            continue

        for label in labels:
            logger.debug(f"[SDS_EXTRACTOR] Checking label '{label}' in line: '{clean[:50]}...'")
            
            # Case 1: label and value on same line
            same_line_pattern = rf"^{label}\s*[:\-]\s*(.+)$"
            same = re.search(same_line_pattern, clean, re.IGNORECASE)
            if not same:
                # Handle case with whitespace but no colon/hyphen
                same = re.search(rf"^{label}\b\s+(.+)$", clean, re.IGNORECASE)
            search_next = False
            if same:
                value = same.group(1).strip()

                # Remove leading possessive artifacts like "'s" or "’s"
                value = re.sub(r"^[\"'’`]+s\b\s*", "", value)

                # Skip if the value clearly refers to a product code or similar non-name data
                if re.search(r"product\s+code", value, re.IGNORECASE):
                    logger.debug(f"[SDS_EXTRACTOR] Skipping value containing product code: '{value}'")
                    continue

                logger.debug(f"[SDS_EXTRACTOR] Found same-line match: '{value}'")

                # Clean up the value - remove trailing noise
                # Split on common separators that indicate end of value
                for separator in [r'\s+Tel:', r'\s+Phone:', r'\s+Fax:', r'\s+Email:', r'\s+Website:',
                                r'\s+Emergency:', r'\s+Address:', r'\s+Contact:', r'\s+Product\s+code:']:
                    split_match = re.split(separator, value, flags=re.IGNORECASE)
                    if len(split_match) > 1:
                        value = split_match[0].strip()
                        break

                # Remove common trailing noise patterns
                value = re.sub(r'\s*[:\-]\s*$', '', value)  # Remove trailing colons/dashes
                value = re.sub(r'\s+Page\s+\d+.*$', '', value, flags=re.IGNORECASE)  # Remove page numbers

                if value and not is_noise_text(value):
                    logger.debug(f"[SDS_EXTRACTOR] Accepting value: '{value}'")
                    return value
                else:
                    logger.debug(f"[SDS_EXTRACTOR] Rejecting value as noise: '{value}'")
                    search_next = True

            # Case 2: label alone on this line or previous value rejected as noise, look for value on subsequent lines
            if search_next or re.fullmatch(label, clean, re.IGNORECASE):
                logger.debug(f"[SDS_EXTRACTOR] Looking for value on next lines")
                j = i + 1
                while j < len(lines) and j < i + 5:  # Limit search to next 5 lines
                    candidate_line = lines[j].strip()
                    if not candidate_line:
                        j += 1
                        continue

                    # Handle colon prefix
                    candidate = candidate_line
                    if candidate.startswith(':'):
                        candidate = candidate[1:].strip()

                    # Stop if we hit another label
                    if any(re.search(lab, candidate, re.IGNORECASE) for lab in [l for labs in FIELD_LABELS.values() for l in labs]):
                        break

                    if candidate and not is_noise_text(candidate):
                        logger.debug(f"[SDS_EXTRACTOR] Found value on next line: '{candidate}'")
                        return candidate
                    j += 1

    return None


def extract_product_name(section_text: str) -> Optional[str]:
    """Enhanced product name extraction with multiple strategies."""
    if not section_text:
        return None
    
    # Strategy 1: Look for explicit product name labels
    product_name = extract_after_label(section_text, FIELD_LABELS['product_name'], 'product_name')
    if product_name and not is_noise_text(product_name):
        logger.info(f"[SDS_EXTRACTOR] Product name from label: '{product_name}'")
        return product_name
    
    # Strategy 2: Look for product name in the first few meaningful lines
    lines = section_text.splitlines()
    meaningful_lines = []
    
    for line in lines[:10]:  # Check first 10 lines only
        clean = line.strip()
        if not clean:
            continue
        
        # Skip obvious header/label lines
        if re.match(r'^\s*(?:section\s*)?1(?:\s|$)', clean, re.IGNORECASE):
            continue
        if re.search(r'identification|supplier|manufacturer|emergency|contact|telephone|fax|email|web\s*site|details|address|synonym|regulation', clean, re.IGNORECASE):
            continue
        if clean.startswith('(') or re.search(r'safety\s+data\s+sheet|according\s+to', clean, re.IGNORECASE):
            continue
        if is_noise_text(clean):
            continue
        if re.match(r'^[:\-\s]*$', clean):
            continue

        # Skip lines that are clearly labels (optionally followed by punctuation)
        is_label = False
        for label_group in FIELD_LABELS.values():
            for label in label_group:
                if re.fullmatch(rf"{label}\s*[:\-]?", clean, re.IGNORECASE):
                    is_label = True
                    break
            if is_label:
                break

        if not is_label:
            meaningful_lines.append(clean)
    
    # Take the first meaningful line that looks like a product name
    for line in meaningful_lines:
        candidate = re.sub(r'^\d+(?:\.\d+)?\s*', '', line)
        candidate = re.sub(r'^(?:product\s+identifier\s*[:\-]?\s*)', '', candidate, flags=re.IGNORECASE)

        if re.search(r'^(?:product\s+name|sds\s+no\.?|sds\s+number)', candidate, re.IGNORECASE):
            continue
        if re.match(r'^\d+\s*[\-–]', candidate):
            continue

        if re.search(r'[A-Za-z0-9]', candidate) and len(candidate) > 3:
            if not re.search(r'\b\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}\b', candidate):
                if not re.search(r'@|www\.|\.com|\.org', candidate, re.IGNORECASE):
                    logger.info(f"[SDS_EXTRACTOR] Product name from meaningful line: '{candidate}'")
                    return candidate
    
    logger.warning("[SDS_EXTRACTOR] Could not extract product name")
    return None


def extract_manufacturer(section_text: str) -> Optional[str]:
    """Enhanced manufacturer extraction with validation."""
    if not section_text:
        return None
    
    # Strategy 1: Look for explicit manufacturer labels
    manufacturer = extract_after_label(section_text, FIELD_LABELS['manufacturer'], 'manufacturer')
    if manufacturer and not is_noise_text(manufacturer):
        # Additional validation for manufacturer
        if len(manufacturer) > 2 and not re.match(r'^[:\-\s]*$', manufacturer):
            logger.info(f"[SDS_EXTRACTOR] Manufacturer from label: '{manufacturer}'")
            return manufacturer

    # Strategy 1b: handle inline 'Details of the supplier' patterns
    details_match = re.search(r'Details\s+of\s+the\s+supplier[^\n]*?:\s*(.+)', section_text, re.IGNORECASE)
    if details_match:
        candidate = details_match.group(1).splitlines()[0].strip()
        if candidate and not is_noise_text(candidate):
            logger.info(f"[SDS_EXTRACTOR] Manufacturer from inline supplier details: '{candidate}'")
            return candidate
    
    # Strategy 2: Look in "Details of the supplier" section
    supplier_section = re.search(r'Details\s+of\s+the\s+supplier[^\n]*\n([^:]+?)(?:\n\s*[A-Z]|\n\s*\d|$)', 
                                section_text, re.IGNORECASE | re.DOTALL)
    if supplier_section:
        supplier_text = supplier_section.group(1).strip()
        # Take the first meaningful line from supplier details
        for line in supplier_text.splitlines():
            clean = line.strip()
            if clean and not is_noise_text(clean) and len(clean) > 3:
                if not re.search(r'\b\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}\b', clean):  # Not phone
                    logger.info(f"[SDS_EXTRACTOR] Manufacturer from supplier details: '{clean}'")
                    return clean
    
    logger.warning("[SDS_EXTRACTOR] Could not extract manufacturer")
    return None


def extract_section14_field(sec14: str, labels: List[str], field_name: str) -> Optional[str]:
    """Extract specific fields from Section 14 (Transport Information) with validation."""
    if not sec14:
        return None
    
    lines = sec14.splitlines()
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        
        for label in labels:
            # Handle "Label: value" on the same line
            same_line = re.search(rf'{label}\s*[:\-]?\s*(.+)', stripped, re.IGNORECASE)
            if same_line:
                candidate = same_line.group(1).strip()
                
                # Clean up the candidate
                candidate = re.sub(r'\s*[:\-]\s*$', '', candidate)  # Remove trailing punctuation
                
                if candidate and not is_noise_text(candidate):
                    # Validate based on field type
                    if field_name == 'dangerous_goods_class':
                        if validate_dangerous_goods_class(candidate):
                            logger.info(f"[SDS_EXTRACTOR] Valid DG class: '{candidate}'")
                            return candidate
                        else:
                            logger.debug(f"[SDS_EXTRACTOR] Invalid DG class rejected: '{candidate}'")
                    elif field_name == 'packing_group':
                        if VALID_PACKING_GROUPS.match(candidate):
                            logger.info(f"[SDS_EXTRACTOR] Valid packing group: '{candidate}'")
                            return candidate
                        else:
                            logger.debug(f"[SDS_EXTRACTOR] Invalid packing group rejected: '{candidate}'")
                    else:
                        return candidate
            
            # Label present in this line, value on subsequent line
            if re.search(label, stripped, re.IGNORECASE):
                j = i + 1
                while j < len(lines) and j < i + 3:  # Limit search to next 3 lines
                    candidate_line = lines[j].strip()
                    if not candidate_line:
                        j += 1
                        continue
                    
                    # Skip if it looks like another label
                    if any(re.search(lab, candidate_line, re.IGNORECASE) 
                          for lab_group in FIELD_LABELS.values() for lab in lab_group):
                        break
                    
                    candidate = candidate_line
                    if candidate.startswith(':'):
                        candidate = candidate[1:].strip()
                    
                    if candidate and not is_noise_text(candidate):
                        # Validate based on field type
                        if field_name == 'dangerous_goods_class':
                            if validate_dangerous_goods_class(candidate):
                                logger.info(f"[SDS_EXTRACTOR] Valid DG class from next line: '{candidate}'")
                                return candidate
                        elif field_name == 'packing_group':
                            if VALID_PACKING_GROUPS.match(candidate):
                                logger.info(f"[SDS_EXTRACTOR] Valid packing group from next line: '{candidate}'")
                                return candidate
                        else:
                            return candidate
                    j += 1
    
    return None
