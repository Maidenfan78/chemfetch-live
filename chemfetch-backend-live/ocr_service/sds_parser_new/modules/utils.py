"""
Text extraction utilities
"""
import re
import logging
from .config import NOISE_LABELS, VALID_DG_CLASSES, VALID_PACKING_GROUPS

logger = logging.getLogger(__name__)


def is_noise_text(text: str) -> bool:
    """Check if text is likely noise (labels, contact info, etc.) that shouldn't be extracted as values."""
    if not text or len(text.strip()) < 2:
        return True
    
    text_clean = text.strip()
    
    # Check against noise patterns
    for pattern in NOISE_LABELS:
        if re.fullmatch(pattern, text_clean, re.IGNORECASE):
            return True
    
    # Additional checks for common noise patterns
    if re.match(r'^[:\-\s]*$', text_clean):  # Just punctuation
        return True
    if re.match(r'^\d{2,4}[-\s]\d{2,4}[-\s]\d{2,4}$', text_clean):  # Phone number pattern
        return True
    # Country code headers like "UK, NPIS" (be conservative to avoid rejecting real product names)
    if re.match(r'^(UK|US|USA|EU|AU|NZ|JP|CN),?\s+[A-Z]{2,4}\b', text_clean):
        return True
    if re.search(r'\b\d{2,4}\s+\d{2,4}\s+\d{2,4}\b', text_clean):  # Phone numbers
        return True
    if text_clean.lower() in ['name', 'date', 'address', 'contact', 'details', 'information']:
        return True
    if text_clean.lower() in {
        'australia', 'new zealand', 'united states', 'united kingdom',
        'usa', 'uk', 'canada'
    }:
        return True

    return False


def validate_dangerous_goods_class(value: str) -> bool:
    """Validate if a dangerous goods class is valid (1-9 with optional subdivision)."""
    if not value:
        return False
    
    value = value.strip()
    
    # Check for valid class numbers
    if VALID_DG_CLASSES.match(value):
        return True
    
    # Check for valid "not applicable" type responses
    not_applicable_patterns = [
        r'not?\s+regulated',
        r'not?\s+applicable',
        r'not?\s+required',
        r'not?\s+subject',
        r'none',
        r'n/?a',
        r'not\s+a\s+dangerous\s+good'
    ]
    
    for pattern in not_applicable_patterns:
        if re.fullmatch(pattern, value, re.IGNORECASE):
            return True
    
    return False


def get_section(text: str, number: int) -> str:
    """Extract a specific numbered section from the SDS text"""
    from .config import SECTION_PATTERN
    
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
