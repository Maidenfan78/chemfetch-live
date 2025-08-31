"""
Section 1 parsing helpers: identification fields extracted from SDS Section 1.
Wraps field_extractor with a few extra guards for common header-continuation noise.
"""
from typing import Optional
import re

from . import field_extractor as fe


HEADER_CONTINUATIONS = [
    r"^of\s+the\s+chemical\s+and\s+restrictions\s+on\s+use$",
    r"^of\s+the\s+safety\s+data\s+sheet$",
    r"^or\s+supplier'?s\s+details$",
    r"^of\s+the\s+company/undertaking$",
]


def _is_header_continuation(text: str) -> bool:
    return any(re.fullmatch(p, text.strip(), re.IGNORECASE) for p in HEADER_CONTINUATIONS)


def product_name(section1_text: str) -> Optional[str]:
    name = fe.extract_product_name(section1_text)
    if name and not _is_header_continuation(name):
        return name
    return None


def manufacturer(section1_text: str) -> Optional[str]:
    m = fe.extract_manufacturer(section1_text)
    if m and not _is_header_continuation(m):
        return m
    return None


def description(section1_text: str) -> Optional[str]:
    d = fe.extract_description(section1_text)
    if d and not _is_header_continuation(d):
        return d
    return None


def product_use(section1_text: str) -> Optional[str]:
    # Reuse description logic for use-related labels
    u = fe.extract_after_label(section1_text, fe.FIELD_LABELS['product_use'], 'product_use')
    if u and not _is_header_continuation(u):
        return u
    return None

