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


def clean_company_candidate(value: str) -> str:
    """Clean up a manufacturer/supplier candidate string.

    - Remove leading bullets/arrows and stray symbols (e.g., '▼', '•', '-', '—')
    - Strip redundant inline label prefixes like 'Company and address:'
    - Trim at noisy tokens like 'Association / Organisation', 'Poisons Information', 'Emergency'
    - Drop obvious section headers like 'Section 1 - Identification ...'
    """
    if not value:
        return ''

    s = value.strip()

    # 1) Remove leading bullets/arrows and punctuation noise
    s = re.sub(r"^[\s\-–—:*•■●►➤▼◆▪]+", "", s)

    # 2) Remove inline label prefixes that sometimes bleed into the value
    s = re.sub(r"^(?:Company\s+and\s+address|Company|Manufacturer|Supplier(?:\s+Name)?|Distributor|Producer)\s*[:\-]\s*",
               "", s, flags=re.IGNORECASE)

    # 3) If string is a section header, reject
    if re.match(r"^(Section\s*\d+\b|\d+\.?\s*(Identification|Hazard)\b)", s, re.IGNORECASE):
        return ''

    # 4) Remove parentheses containing registry/formerly info
    s = re.sub(r"\s*\([^)]*(?:ABN|ACN|Formerly)\s*[^)]*\)", "", s, flags=re.IGNORECASE)

    # 5) Trim after known noise tokens
    noise_tokens = [
        r"Association\s*/?\s*Organisation",
        r"Poisons?\s+Information",
        r"Poison\s+Information",
        r"Emergency(?:\s+telephone|\s+phone)?",
        r"ABN\b",
        r"ACN\b",
        r"Address",
        r"Contact",
        r"Website",
        r"Email",
        r"Tel\.?",
        r"Phone",
        r"Fax",
    ]
    pattern = re.compile(r"\b(?:" + "|".join(noise_tokens) + r")\b", re.IGNORECASE)
    m = pattern.search(s)
    if m:
        s = s[:m.start()].strip()

    # 6) If a corporate suffix is present, clip anything after it
    suffix_clip = re.compile(r"^(.*?\b(?:PTY\s+LTD|P/L|LTD|LIMITED|INC\.?|CORP\.?|CORPORATION|GMBH|PLC|BV|S\.?A\.?|S\.P\.A\.|LLC))\b.*$",
                             re.IGNORECASE)
    sm = suffix_clip.match(s)
    if sm:
        s = sm.group(1).strip()

    # 7) Remove trailing commas/periods and stray punctuation
    s = re.sub(r"[\s,.;:]+$", "", s)

    return s.strip()


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


def _compress_consecutive_duplicates(token: str) -> str:
    """Compress consecutive duplicate characters (e.g., 'PPRROODDUUCCTT' -> 'PRODUCT').

    This is used for recognizing corrupted labels. Do not apply blindly to product names
    because it would incorrectly change legitimate double letters (e.g., 'Bitter').
    """
    if not token:
        return token
    return __import__('re').sub(r"(.)\1+", r"\1", token)


def strip_doubled_label_prefix(text: str) -> str:
    """Strip a leading label prefix even if rendered with doubled letters.

    Example:
      'PPRROODDUUCCTT NNAAMMEE Whiteboard cleaner' -> 'Whiteboard cleaner'

    Recognizes common label heads: 'PRODUCT NAME', 'PRODUCT IDENTIFIER', 'TRADE NAME',
    'GHS PRODUCT IDENTIFIER'.
    """
    if not text:
        return text

    raw = text.strip()
    if not raw:
        return raw

    labels = [
        ["PRODUCT", "NAME"],
        ["PRODUCT", "IDENTIFIER"],
        ["TRADE", "NAME"],
        ["GHS", "PRODUCT", "IDENTIFIER"],
    ]

    parts = raw.split()
    # Try to match any label at the beginning (2-3 tokens)
    for tokens in labels:
        n = len(tokens)
        if len(parts) >= n:
            head = parts[:n]
            # Normalize and compress duplicates for comparison
            norm_head = [
                _compress_consecutive_duplicates(p).upper().strip(" :\t-._") for p in head
            ]
            if norm_head == tokens:
                remainder = " ".join(parts[n:]).lstrip(" :\t-._").strip()
                return remainder or raw

    return raw


def looks_like_numeric_code(value: str) -> bool:
    """Heuristic: true if the candidate is primarily a numeric code (e.g., '0000003477')."""
    if not value:
        return False
    s = value.strip()
    # Consider codes with >= 6 digits and no letters as numeric codes
    if len(s) >= 6 and not __import__('re').search(r"[A-Za-z]", s) and __import__('re').search(r"\d", s):
        return True
    return False

def compress_duplicates_with_map(s: str):
    """Compress consecutive duplicate alphabetic characters while keeping an index map.

    Returns a tuple of (normalized_string, index_map) where index_map[i] gives the
    index in the original string that produced normalized_string[i]. Only alphabetic
    characters are de-duplicated; digits, whitespace and punctuation are preserved
    to avoid corrupting values.
    """
    if not s:
        return "", []
    out_chars = []
    index_map = []
    prev_alpha_lower = None
    for idx, ch in enumerate(s):
        if ch.isalpha():
            low = ch.lower()
            if low == prev_alpha_lower:
                # Update mapping to point to the last index of this duplicate run
                if index_map:
                    index_map[-1] = idx
                continue
            prev_alpha_lower = low
        else:
            prev_alpha_lower = None if ch.strip() else prev_alpha_lower
        out_chars.append(ch)
        index_map.append(idx)
    return "".join(out_chars), index_map
