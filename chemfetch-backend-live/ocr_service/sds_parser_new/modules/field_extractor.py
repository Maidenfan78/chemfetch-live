"""
Improved Field extraction module - fixes for specific SDS parsing issues
"""
import re
import logging
from typing import List, Optional

from .config import FIELD_LABELS
from .utils import (
    is_noise_text,
    validate_dangerous_goods_class,
    clean_company_candidate,
    strip_doubled_label_prefix,
    looks_like_numeric_code,
    compress_duplicates_with_map,
)
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
                # Handle case with whitespace but no colon/hyphen, but avoid matching section headers like
                # "Manufacturer or supplier's details" or "Recommended use of the chemical and restrictions on use".
                # Use a generic whitespace matcher after the label (no word-boundary), so labels ending with
                # non-word characters (e.g., "Use(s)") are supported.
                tmp = re.search(rf"^{label}\s+(.+)$", clean, re.IGNORECASE)
                if tmp:
                    tail = tmp.group(1).strip()
                    # Common continuation phrases that indicate this is still part of the label header, not a value
                    continuation_noise = [
                        r"^of\s+the\s+chemical\s+and\s+restrictions\s+on\s+use$",
                        r"^of\s+the\s+safety\s+data\s+sheet$",
                        r"^or\s+supplier'?s\s+details$",
                        r"^of\s+the\s+company/undertaking$",
                    ]
                    if any(re.fullmatch(p, tail, re.IGNORECASE) for p in continuation_noise):
                        same = None
                    else:
                        same = tmp

            # Fallback: handle labels that appear mid-line (e.g., after another field)
            # Example: "Address: ... Product Use: Lubricant, ..."
            if not same:
                mid_line_pattern = rf"{label}\s*[:\-]\s*(.+)$"
                mid = re.search(mid_line_pattern, clean, re.IGNORECASE)
                if mid:
                    same = mid

            # Final fallback: duplicate-letter tolerant label match (no delimiter required)
            if not same and field_name in ('description', 'product_use'):
                try:
                    norm_line, idx_map = compress_duplicates_with_map(clean)
                    tolerant = re.compile(rf"({label})\s*[:\-\s]*?(.*)$", re.IGNORECASE)
                    # Prefer start-of-line, then fallback to anywhere on the line
                    m = re.match(tolerant, norm_line)
                    if not m:
                        m = tolerant.search(norm_line)
                    if m and m.group(2) is not None:
                        end_norm = m.end(1)
                        start_orig = idx_map[end_norm - 1] + 1 if 0 < end_norm <= len(idx_map) else 0
                        tail_orig = clean[start_orig:].lstrip(" :\t-.")
                        if tail_orig:
                            same = re.match(r"^(.+)$", tail_orig)
                except re.error:
                    pass
            search_next = False
            if same:
                value = same.group(1).strip()

                # Remove leading possessive artifacts like "'s" or "'s"
                value = re.sub(r"^[\"''`]+s\b\s*", "", value)

                # Normalize common label continuation fragments that trail after generic labels like 'Use'
                # Example: "Use : of the Substance/Mixture : Washing and cleaning products ..."
                value = re.sub(
                    r'^(?:of\s+the\s+(?:substance|chemical)(?:\s*/\s*mixture|\s+or\s+mixture)?)(?:\s+and\s+uses\s+advised\s+against)?\s*[:\-]*\s*',
                    '', value, flags=re.IGNORECASE)
                
                # Special cleaning for common noise patterns that were causing issues
                value = re.sub(r"^of\s+the\s+safety\s+data\s+sheet\s*", "", value, re.IGNORECASE)
                value = re.sub(r"^of\s+the\s+substance\s+or\s+mixture\s+and\s+uses\s+advised\s+against\s*", "", value, re.IGNORECASE)

                # Skip if the value clearly refers to a product code or similar non-name data
                if re.search(r"product\s+code", value, re.IGNORECASE):
                    logger.debug(f"[SDS_EXTRACTOR] Skipping value containing product code: '{value}'")
                    continue

                logger.debug(f"[SDS_EXTRACTOR] Found same-line match: '{value}'")

                # Clean up the value - remove trailing noise
                # Split on common separators that indicate end of value or start of another label on same line
                for separator in [
                    r'\s+Tel:', r'\s+Phone:', r'\s+Fax:', r'\s+Email:', r'\s+Website:',
                    r'\s+Emergency:', r'\s+Address:', r'\s+Contact:', r'\s+Product\s+code:',
                    # Guard: if another label starts on same line, trim at that point
                    r'\s+Intended\s+use\b', r'\s+Identified\s+uses\b', r'\s+Uses\s+advised\s+against\b',
                    r'\s+Use\s+of\s+the\s+substance\b', r'\s+Restrictions\s+on\s+use\b'
                ]:
                    split_match = re.split(separator, value, flags=re.IGNORECASE)
                    if len(split_match) > 1:
                        value = split_match[0].strip()
                        break

                # Remove common trailing noise patterns
                value = re.sub(r'\s*[:\-]\s*$', '', value)  # Remove trailing colons/dashes
                value = re.sub(r'\s+Page\s+\d+.*$', '', value, flags=re.IGNORECASE)  # Remove page numbers

                # If value is actually a continuation of the label header, skip and search next lines
                header_continuations = [
                    r"^of\s+the\s+chemical\s+and\s+restrictions\s+on\s+use$",
                    r"^of\s+the\s+safety\s+data\s+sheet$",
                    r"^or\s+supplier'?s\s+details$",
                    r"^of\s+the\s+company/undertaking$",
                ]
                if any(re.fullmatch(p, value, re.IGNORECASE) for p in header_continuations):
                    logger.debug(f"[SDS_EXTRACTOR] Skipping header continuation value: '{value}'")
                    search_next = True
                    value = ''

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

                    # Avoid registration numbers being treated as product name values
                    if field_name == 'product_name' and re.match(r'^registration\s+no\.?', candidate, re.IGNORECASE):
                        j += 1
                        continue

                    # Skip if candidate is a known header continuation fragment
                    if any(re.fullmatch(p, candidate, re.IGNORECASE) for p in [
                        r"^of\s+the\s+chemical\s+and\s+restrictions\s+on\s+use$",
                        r"^of\s+the\s+safety\s+data\s+sheet$",
                        r"^or\s+supplier'?s\s+details$",
                        r"^of\s+the\s+company/undertaking$",
                    ]):
                        j += 1
                        continue

                    # Skip if the candidate is actually a section header
                    if field_name == 'product_name' and re.match(r'^\s*(?:section\s*)?\d', candidate, re.IGNORECASE):
                        j += 1
                        continue

                    if candidate and not is_noise_text(candidate):
                        logger.debug(f"[SDS_EXTRACTOR] Found value on next line: '{candidate}'")
                        return candidate
                    j += 1

    return None


def extract_from_table_structure(text: str, field_name: str) -> Optional[str]:
    """Extract values from tabular layouts where standard label matching fails."""
    if not text:
        return None
    
    lines = text.splitlines()
    
    # Strategy for packing group in tables
    if field_name == 'packing_group':
        # Look for table rows with "Packing Group" header
        for i, line in enumerate(lines):
            if re.search(r'packing\s+group', line, re.IGNORECASE):
                # Check same line for value after the header
                parts = re.split(r'\s{2,}|\t|\|', line)  # Split on multiple spaces, tabs, or pipes
                if len(parts) > 1:
                    for part in parts[1:]:  # Skip the header part
                        part = part.strip()
                        if part and VALID_PACKING_GROUPS.match(part):
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
                        cell = cell.strip()
                        if cell and VALID_PACKING_GROUPS.match(cell):
                            logger.info(f"[SDS_EXTRACTOR] Found packing group in table row: '{cell}'")
                            return cell
    
    # Strategy for dangerous goods class in tables  
    elif field_name == 'dangerous_goods_class':
        for i, line in enumerate(lines):
            # Allow header to be split across lines (e.g., 'Transport hazard' then 'class(es)')
            header_hit = re.search(r'(?:DG\s*Class|Hazard\s*Class|Transport\s+hazard(?:\s+class(?:\(es\))?)?)', line, re.IGNORECASE)
            if not header_hit:
                # If current line is just 'class(es)', also accept when previous had 'Transport hazard'
                if i > 0 and re.search(r'^\s*class(?:\(es\))?\s*$', line, re.IGNORECASE) and re.search(r'Transport\s+hazard', lines[i-1], re.IGNORECASE):
                    header_hit = True
            if header_hit:
                # Gather this line and the next couple lines to scan for class tokens
                segment = [line]
                for j in range(i + 1, min(i + 4, len(lines))):
                    nxt = lines[j].strip()
                    if nxt:
                        segment.append(nxt)
                # Check tokens across the segment
                for seg_line in segment:
                    tokens = re.split(r'\s+|\|', seg_line)
                    for tok in tokens:
                        tok = tok.strip(',;')
                        if validate_dangerous_goods_class(tok):
                            logger.info(f"[SDS_EXTRACTOR] Found DG class in table segment: '{tok}'")
                            return tok
    
    return None


def extract_product_name(section_text: str) -> Optional[str]:
    """Enhanced product name extraction with multiple strategies to fix sds_5.pdf issue."""
    if not section_text:
        return None
    
    # Strategy 1: Look for explicit product name labels
    product_name = extract_after_label(section_text, FIELD_LABELS['product_name'], 'product_name')
    if product_name:
        product_name = strip_doubled_label_prefix(product_name)
    if product_name and not is_noise_text(product_name) and not looks_like_numeric_code(product_name):
        # Additional validation - reject if it looks like a company suffix
        if not re.match(r'^(Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company)$', product_name, re.IGNORECASE):
            logger.info(f"[SDS_EXTRACTOR] Product name from label: '{product_name}'")
            return product_name
    
    # Strategy 2: Look for split-table format (addressing sds_5.pdf issue)
    # Pattern: "Product Name: WD-40 Aerosol" might be split across cells
    # Only allow spaces/tabs after label; do not cross newlines
    product_name_match = re.search(r'Product\s+Name[:\t ]*([^:\n]*)', section_text, re.IGNORECASE)
    if product_name_match:
        candidate = product_name_match.group(1).strip()
        # Clean up noise like trailing company info
        candidate = re.sub(r'\s+(?:Pty\s+Ltd|Ltd|Inc\.?|Corp\.?).*$', '', candidate, re.IGNORECASE)
        candidate = strip_doubled_label_prefix(candidate)
        if candidate and not is_noise_text(candidate) and len(candidate) > 2 and not looks_like_numeric_code(candidate):
            logger.info(f"[SDS_EXTRACTOR] Product name from split table: '{candidate}'")
            return candidate
    
    # Strategy 2b: If a bare "Product Name" label appears, use the previous non-empty line
    lines = section_text.splitlines()
    for idx, line in enumerate(lines):
        if re.fullmatch(r'\s*Product\s+Name\s*', line, re.IGNORECASE):
            j = idx - 1
            while j >= 0:
                prev = lines[j].strip()
                if prev:
                    # Avoid section headers and boilerplate
                    if not re.match(r'^\d+\.', prev) and not re.search(r'safety\s+data\s+sheet|version|msds\s+date|page\s+\d+', prev, re.IGNORECASE):
                        prev = strip_doubled_label_prefix(prev)
                        if not is_noise_text(prev) and not looks_like_numeric_code(prev):
                            logger.info(f"[SDS_EXTRACTOR] Product name from line above label: '{prev}'")
                            return prev
                    break
                j -= 1

    # Strategy 3: Look for product name in the first few meaningful lines
    meaningful_lines = []
    
    for line in lines[:15]:  # Check first 15 lines only
        clean = line.strip()
        if not clean:
            continue
        
        # Skip obvious header/label lines
        if re.match(r'^\s*(?:section\s*)?1(?:\s|$)', clean, re.IGNORECASE):
            continue
        if re.search(r'identification|supplier|manufacturer|emergency|contact|telephone|fax|email|web\s*site|details|address|synonym|regulation', clean, re.IGNORECASE):
            continue
        # Skip common Section 1 label continuations and use headers
        if re.search(r"^use\(s\)|^use\s+of\s+the\s+substance|uses\s+advised\s+against|of\s+the\s+chemical\s+and\s+restrictions\s+on\s+use", clean, re.IGNORECASE):
            continue
        # Skip registration identifiers often near headers
        if re.search(r"^registration\s+no\.?|\bregistration\s+no\.\b", clean, re.IGNORECASE):
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

        # Remove any doubled-letter label prefix that leaked into the line
        candidate = strip_doubled_label_prefix(candidate)
        if re.search(r'[A-Za-z0-9]', candidate) and len(candidate) > 3 and not looks_like_numeric_code(candidate):
            if not re.search(r'\b\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}\b', candidate):
                if not re.search(r'@|www\.|\.com|\.org', candidate, re.IGNORECASE):
                    # Additional check to reject company suffixes
                    if not re.match(r'^(Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company)$', candidate, re.IGNORECASE):
                        logger.info(f"[SDS_EXTRACTOR] Product name from meaningful line: '{candidate}'")
                        return candidate
    
    logger.warning("[SDS_EXTRACTOR] Could not extract product name")
    return None


def extract_manufacturer(section_text: str) -> Optional[str]:
    """Enhanced manufacturer extraction with validation to fix sds_1.pdf and sds_15.pdf issues."""
    if not section_text:
        return None
    
    # Strategy 1: Look for explicit manufacturer labels
    manufacturer = extract_after_label(section_text, FIELD_LABELS['manufacturer'], 'manufacturer')
    if manufacturer:
        manufacturer = clean_company_candidate(manufacturer)
    if manufacturer and not is_noise_text(manufacturer):
        # Additional validation for manufacturer - reject obvious noise fragments
        if not re.match(r'^of\s+the\s+safety\s+data\s+sheet', manufacturer, re.IGNORECASE) and not re.match(r"^or\s+supplier'?s\s+details$", manufacturer, re.IGNORECASE):
            if len(manufacturer) > 2 and not re.match(r'^[:\-\s]*$', manufacturer):
                logger.info(f"[SDS_EXTRACTOR] Manufacturer from label: '{manufacturer}'")
                return manufacturer

    # Strategy 1b: handle inline 'Details of the supplier' patterns
    details_match = re.search(r'Details\s+of\s+the\s+supplier[^\n]*?:\s*(.+)', section_text, re.IGNORECASE)
    if details_match:
        candidate = details_match.group(1).splitlines()[0].strip()
        candidate = clean_company_candidate(candidate)
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
                    cleaned = clean_company_candidate(clean)
                    if cleaned and not is_noise_text(cleaned):
                        logger.info(f"[SDS_EXTRACTOR] Manufacturer from supplier details: '{cleaned}'")
                        return cleaned
    
    # Strategy 3: Look for company names that appear before product names
    # This helps with cases where layout is: "Company Name" followed by "Product Name: actual product"
    lines = section_text.splitlines()
    for i, line in enumerate(lines):
        clean = line.strip()
        if not clean:
            continue
        
        # Look for lines that contain company indicators
        if re.search(r'\b(?:Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company|Corporation)\b', clean, re.IGNORECASE):
            # Check if this looks like a company name (not just "Product Name: Pty Ltd")
            if not re.search(r'Product\s+Name\s*:', clean, re.IGNORECASE):
                # Clean up the company name
                company_name = re.sub(r'^.*?([A-Z][^:\n]*(?:Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company|Corporation)[^:\n]*).*$', 
                                    r'\1', clean, re.IGNORECASE)
                if company_name != clean and company_name:  # If regex matched and extracted something
                    company_name = clean_company_candidate(company_name.strip())
                    if company_name and not is_noise_text(company_name):
                        logger.info(f"[SDS_EXTRACTOR] Manufacturer from company pattern: '{company_name}'")
                        return company_name
                else:
                    fallback = clean_company_candidate(clean)
                    if fallback and not is_noise_text(fallback):
                        logger.info(f"[SDS_EXTRACTOR] Manufacturer from company line: '{fallback}'")
                        return fallback
    
    logger.warning("[SDS_EXTRACTOR] Could not extract manufacturer")
    return None


def extract_description(section_text: str) -> Optional[str]:
    """Extract product description/use information."""
    if not section_text:
        return None
    
    # Look for description-related labels
    description_labels = [
        r'Product\s+description',
        r'Description',
        r'Use\s+of\s+the\s+substance',
        r'Use\s*\(s\)',
        r'Use\b',
        r'Recommended\s+use',
        r'Intended\s+use',
        r'Product\s+use',
        r'Relevant\s+identified\s+uses',
        r'Identified\s+uses',
        r'Application'
    ]
    
    description = extract_after_label(section_text, description_labels, 'description')
    if description and not is_noise_text(description):
        # Clean up common noise in descriptions
        # 1) Remove leading continuation fragments like "of the Substance/Mixture :"
        description = re.sub(
            r'^(?:of\s+the\s+(?:substance|chemical)(?:\s*/\s*mixture|\s+or\s+mixture)?)(?:\s+and\s+uses\s+advised\s+against)?\s*[:\-]*\s*',
            '', description, re.IGNORECASE)
        # 2) Remove specific verbose header phrase
        description = re.sub(r'^of\s+the\s+substance\s+or\s+mixture\s+and\s+uses\s+advised\s+against\s*', '', description, re.IGNORECASE)
        # 3) Tidy odd prefix variants like "/Mixture :"
        description = re.sub(r'^/Mixture\s*:\s*', '', description, re.IGNORECASE)
        # 4) Normalize stray leading punctuation
        description = re.sub(r'^[\s:;\-]+', '', description)
        if description.strip():
            logger.info(f"[SDS_EXTRACTOR] Description from label: '{description}'")
            return description.strip()
    
    return None


def extract_date_from_header(text: str) -> Optional[str]:
    """Extract date from page headers to fix sds_3.pdf issue."""
    if not text:
        return None
    
    # Split text into lines and look for header patterns
    lines = text.splitlines()
    
    # Look for date patterns in the first few lines where headers typically appear
    for line in lines[:20]:  # Check first 20 lines where headers typically appear
        line = line.strip()
        if not line:
            continue
        
        # Look for revision date patterns in headers
        revision_patterns = [
            # Generic Revision / Rev / Date labels
            r'Revision(?:\s*Date)?[:\s]+(\d{4}-\d{2}-\d{2})',
            r'Revision(?:\s*Date)?[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Revision(?:\s*Date)?[:\s]+(\d{1,2}[\-\/.][A-Za-z]{3,}\.?[\-\/.]\d{2,4})',
            r'Rev[:\s]+(\d{4}-\d{2}-\d{2})',
            r'Rev[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Rev[:\s]+(\d{1,2}[\-\/.][A-Za-z]{3,}\.?[\-\/.]\d{2,4})',
            r'Date[:\s]+(\d{4}-\d{2}-\d{2})',
            r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'Date[:\s]+(\d{1,2}\s+[A-Za-z]{3,}\.?\s+\d{2,4})',
            # Header/footer variants
            r'Printing\s+date[:\s]+(\d{1,2}\s+[A-Za-z]{3,}\.?\s+\d{4})',
            r'Printed\s+on[:\s]+(\d{1,2}[\-\/.][A-Za-z]{3,}\.?[\-\/.]\d{2,4})',
        ]
        
        for pattern in revision_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Normalize month abbreviations with trailing period (e.g., "Jan.")
                date_str = re.sub(r'\b([A-Za-z]{3,})\.', r'\1', date_str)
                try:
                    from datetime import datetime, date
                    # Try to parse and validate
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d %b %Y', '%d %B %Y', '%d-%b-%Y', '%d-%b-%y', '%d.%b.%Y', '%d.%b.%y']:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt).date()
                            if parsed_date <= date.today():  # Must be in the past
                                formatted_date = parsed_date.strftime('%Y-%m-%d')
                                logger.info(f"[SDS_EXTRACTOR] Date from header: '{formatted_date}'")
                                return formatted_date
                        except ValueError:
                            continue
                except ImportError:
                    # If datetime not available, return as-is
                    return date_str
    
    return None


def extract_section14_field(sec14: str, labels: List[str], field_name: str) -> Optional[str]:
    """Extract specific fields from Section 14 (Transport Information) with validation."""
    if not sec14:
        return None
    
    # First try standard label extraction
    result = extract_after_label(sec14, labels, field_name)
    if result:
        # Validate based on field type
        if field_name == 'dangerous_goods_class':
            if validate_dangerous_goods_class(result):
                logger.info(f"[SDS_EXTRACTOR] Valid DG class from label: '{result}'")
                return result
        elif field_name == 'packing_group':
            if VALID_PACKING_GROUPS.match(result):
                logger.info(f"[SDS_EXTRACTOR] Valid packing group from label: '{result}'")
                return result
        else:
            return result
    
    # If label extraction failed, try table extraction
    table_result = extract_from_table_structure(sec14, field_name)
    if table_result:
        return table_result
    
    return None
