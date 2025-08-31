"""
FIXED Field extraction module - addresses regressions while keeping improvements
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

                # Remove leading possessive artifacts like "'s" or "'s"
                value = re.sub(r"^[\"''`]+s\b\s*", "", value)
                
                # Special cleaning for common noise patterns that were causing issues
                # BUT BE MORE CAREFUL - only clean obvious noise, not valid content
                if re.match(r"^of\s+the\s+safety\s+data\s+sheet\s*$", value, re.IGNORECASE):
                    logger.debug(f"[SDS_EXTRACTOR] Removing noise pattern: '{value}'")
                    search_next = True
                    continue
                elif re.match(r"^of\s+the\s+substance\s+or\s+mixture\s+and\s+uses\s+advised\s+against\s*$", value, re.IGNORECASE):
                    logger.debug(f"[SDS_EXTRACTOR] Removing noise pattern: '{value}'")
                    search_next = True
                    continue

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
            if re.search(r'(?:DG\s+Class|Transport\s+hazard\s+class|Hazard\s+Class)', line, re.IGNORECASE):
                # Check same line for value
                parts = re.split(r'\s{2,}|\t|\|', line)
                if len(parts) > 1:
                    for part in parts[1:]:
                        part = part.strip()
                        if part and validate_dangerous_goods_class(part):
                            logger.info(f"[SDS_EXTRACTOR] Found DG class in table: '{part}'")
                            return part
                
                # Check next few lines
                for j in range(i + 1, min(i + 4, len(lines))):
                    table_line = lines[j].strip()
                    if not table_line:
                        continue
                    
                    cells = re.split(r'\s{2,}|\t|\|', table_line)
                    for cell in cells:
                        cell = cell.strip()
                        if cell and validate_dangerous_goods_class(cell):
                            logger.info(f"[SDS_EXTRACTOR] Found DG class in table row: '{cell}'")
                            return cell
    
    return None


def extract_product_name(section_text: str) -> Optional[str]:
    """FIXED product name extraction - restore working logic with targeted improvements."""
    if not section_text:
        return None
    
    # Strategy 1: Look for explicit product name labels
    product_labels = FIELD_LABELS.get('product_name', [
        r'Product\s+identifier',
        r'Product\s+Name',
        r'Trade\s+name',
        r'Product\s+code',
        r'Commercial\s+product\s+name',
        r'Product\s+designation'
    ])
    
    product_name = extract_after_label(section_text, product_labels, 'product_name')
    if product_name and not is_noise_text(product_name):
        # Additional validation - reject if it looks like a company suffix or obvious label
        if not re.match(r'^(Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company|Alternative\s+number\(s\)|Other\s+Name\(s\)|Formulation\s+#|Registration\s+no\.?\s*–?\s*US:?)$', product_name, re.IGNORECASE):
            logger.info(f"[SDS_EXTRACTOR] Product name from label: '{product_name}'")
            return product_name
    
    # Strategy 2: Look for split-table format (addressing sds_5.pdf issue)
    # Pattern: "Product Name: WD-40 Aerosol" might be split across cells
    product_name_match = re.search(r'Product\s+Name[:\s]*([^:\n]*)', section_text, re.IGNORECASE)
    if product_name_match:
        candidate = product_name_match.group(1).strip()
        # Clean up noise like trailing company info
        candidate = re.sub(r'\s+(?:Pty\s+Ltd|Ltd|Inc\.?|Corp\.?).*$', '', candidate, re.IGNORECASE)
        if candidate and not is_noise_text(candidate) and len(candidate) > 2:
            if not re.match(r'^(Alternative\s+number\(s\)|Other\s+Name\(s\)|Formulation\s+#)$', candidate, re.IGNORECASE):
                logger.info(f"[SDS_EXTRACTOR] Product name from split table: '{candidate}'")
                return candidate
    
    # Strategy 3: Look for product name in the first few meaningful lines (MORE CONSERVATIVE)
    lines = section_text.splitlines()
    meaningful_lines = []
    
    for line in lines[:20]:  # Check first 20 lines, increased from 15
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

        # Also reject obvious label patterns
        if re.match(r'^(Alternative\s+number\(s\)|Other\s+Name\(s\)|Formulation\s+#|Registration\s+no\.?\s*–?\s*US:?)$', clean, re.IGNORECASE):
            continue

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
                    # Additional check to reject company suffixes and obvious labels
                    if not re.match(r'^(Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company|Alternative\s+number\(s\)|Other\s+Name\(s\)|Formulation\s+#)$', candidate, re.IGNORECASE):
                        logger.info(f"[SDS_EXTRACTOR] Product name from meaningful line: '{candidate}'")
                        return candidate
    
    logger.warning("[SDS_EXTRACTOR] Could not extract product name")
    return None


def extract_manufacturer(section_text: str) -> Optional[str]:
    """FIXED manufacturer extraction - restore working logic while keeping improvements."""
    if not section_text:
        return None
    
    # Strategy 1: Look for explicit manufacturer labels
    manufacturer_labels = FIELD_LABELS.get('manufacturer', [
        r'Manufacturer',
        r'Supplier\s+Name',
        r'Supplier',
        r'Company\s+name\s+of\s+supplier',
        r'Details\s+of\s+the\s+supplier',
        r'Producer',
        r'Company\s+name',
        r'Registered\s+company\s+name',
        r'Distributor',
        r'Manufacturer\s*/\s*Supplier'
    ])
    
    manufacturer = extract_after_label(section_text, manufacturer_labels, 'manufacturer')
    if manufacturer and not is_noise_text(manufacturer):
        # Additional validation for manufacturer - reject obvious noise fragments and labels
        if not re.match(r'^(of\s+the\s+safety\s+data\s+sheet|Emergency\s+Telephone\s+Number|Company[:.]?\s*$|Company\s+No\.?[:.]?\s*$)', manufacturer, re.IGNORECASE):
            if len(manufacturer) > 2 and not re.match(r'^[:\-\s]*$', manufacturer):
                logger.info(f"[SDS_EXTRACTOR] Manufacturer from label: '{manufacturer}'")
                return manufacturer

    # Strategy 1b: handle inline 'Details of the supplier' patterns
    details_match = re.search(r'Details\s+of\s+the\s+supplier[^\n]*?:\s*(.+)', section_text, re.IGNORECASE)
    if details_match:
        candidate = details_match.group(1).splitlines()[0].strip()
        if candidate and not is_noise_text(candidate):
            if not re.match(r'^(Emergency\s+Telephone\s+Number|Company[:.]?\s*$)', candidate, re.IGNORECASE):
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
                    if not re.match(r'^(Emergency\s+Telephone\s+Number|Company[:.]?\s*$)', clean, re.IGNORECASE):
                        logger.info(f"[SDS_EXTRACTOR] Manufacturer from supplier details: '{clean}'")
                        return clean
    
    # Strategy 3: Look for company names that appear in meaningful lines
    lines = section_text.splitlines()
    for i, line in enumerate(lines[:15]):  # Check first 15 lines
        clean = line.strip()
        if not clean:
            continue
        
        # Look for lines that contain company indicators
        if re.search(r'\b(?:Pty\s+Ltd|Ltd|Inc\.?|Corp\.?|Company|Corporation)\b', clean, re.IGNORECASE):
            # Check if this looks like a company name (not just "Product Name: Pty Ltd")
            if not re.search(r'Product\s+Name\s*:', clean, re.IGNORECASE):
                # Skip obvious label patterns
                if not re.match(r'^(Emergency\s+Telephone\s+Number|Company[:.]?\s*$|Company\s+No\.?[:.]?\s*$)', clean, re.IGNORECASE):
                    if not is_noise_text(clean):
                        logger.info(f"[SDS_EXTRACTOR] Manufacturer from company line: '{clean}'")
                        return clean
    
    logger.warning("[SDS_EXTRACTOR] Could not extract manufacturer")
    return None


def extract_description(section_text: str) -> Optional[str]:
    """Extract product description/use information - ENSURE it comes from Section 1."""
    if not section_text:
        return None
    
    # Look for description-related labels
    description_labels = [
        r'Product\s+description',
        r'Description',
        r'Use\s+of\s+the\s+substance',
        r'Recommended\s+use',
        r'Intended\s+use',
        r'Product\s+use',
        r'Relevant\s+identified\s+uses',
        r'Identified\s+uses',
        r'Application'
    ]
    
    description = extract_after_label(section_text, description_labels, 'description')
    if description and not is_noise_text(description):
        # Clean up common noise in descriptions but be more conservative
        description = re.sub(r'^of\s+the\s+substance\s+or\s+mixture\s+and\s+uses\s+advised\s+against\s*', '', description, re.IGNORECASE)
        description = re.sub(r'^/Mixture\s*:\s*', '', description, re.IGNORECASE)
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
    
    # Look for date patterns in the first few lines of each page
    for line in lines[:20]:  # Check first 20 lines where headers typically appear
        line = line.strip()
        if not line:
            continue
        
        # Look for revision date patterns in headers - MORE PATTERNS
        revision_patterns = [
            r'Revision[:\s]+(\d{4}-\d{2}-\d{2})',
            r'Revision[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'Rev[:\s]+(\d{4}-\d{2}-\d{2})',
            r'Rev[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'Date[:\s]+(\d{4}-\d{2}-\d{2})',
            r'Date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            # Additional patterns for different formats
            r'REVISION\s+DATE[:\s]*(\d{1,2}\s+\w+\s+\d{4})',  # "REVISION DATE: 3 August 2021"
            r'Revision[:\s]*(\d{1,2}\s+\w+\s+\d{4})'  # "Revision: 19 January 2024"
        ]
        
        for pattern in revision_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    from datetime import datetime, date
                    # Try to parse and validate
                    formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%d %B %Y', '%d %b %Y']
                    for fmt in formats:
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


# Legacy compatibility functions - restore original working extraction patterns
def extract_field_value_legacy(text: str, field_labels: list, section_text: str = None) -> Optional[str]:
    """Legacy field value extraction for backward compatibility."""
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
                for j in range(i + 1, min(i + 6, len(lines))):
                    candidate = lines[j].strip()
                    if not candidate or candidate == ':':
                        continue
                    if not candidate.startswith(':') and not is_noise_text(candidate):
                        return candidate
    
    return None
