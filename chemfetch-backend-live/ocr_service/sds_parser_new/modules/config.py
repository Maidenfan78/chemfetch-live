"""
Configuration and constants for SDS parser
"""
import re

# Patterns for parsing
SECTION_PATTERN = re.compile(r'^\s*(?:section\s*)?(\d{1,2})(?:\s|:|\.)(?=\s)', re.IGNORECASE | re.MULTILINE)

DATE_PATTERN = re.compile(
    r'(\b(?:Revision(?: Date)?|Issue Date|Date of issue|Version date|SDS creation date|Date Prepared|Issued)[^\n]{0,40})\s*[:]?\s*(?:\nPage[^\n]*\n)?\s*'
    r'((?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(?:[A-Za-z]+\s+\d{1,2},?\s*\d{4})|(?:\d{4}-\d{2}-\d{2}))',
    re.IGNORECASE)

# Improved field label patterns - more specific and comprehensive
FIELD_LABELS = {
    'product_name': [
        r'Product\s+identifier',
        r'Product\s+Name',
        r'Trade\s+name',
        r'Product\s+code',
        r'Commercial\s+product\s+name',
        r'Product\s+designation'
    ],
    'manufacturer': [
        r'Manufacturer',
        r'Supplier',
        r'Company\s+name\s+of\s+supplier',
        r'Producer',
        r'Company\s+name',
        r'Distributor',
        r'Manufacturer\s*/\s*Supplier'
    ],
    'product_use': [
        r'Recommended\s+use',
        r'Intended\s+use',
        r'Use\s+of\s+the\s+substance',
        r'Product\s+use',
        r'Relevant\s+identified\s+uses',
        r'Identified\s+uses',
        r'Uses\s+advised\s+against'
    ],
    'dangerous_goods_class': [
        r'DG\s+Class',
        r'Class',
        r'Transport\s+hazard\s+class',
        r'(?:IMDG|IATA|ADG)?\s*Hazard\s+Class',
        r'Australian\s+Dangerous\s+Goods\s+class',
        r'Dangerous\s+goods\s+class',
        r'UN\s+Class'
    ],
    'subsidiary_risk': [
        r'Subsidiary\s+risk',
        r'Subsidiary\s+hazard',
        r'Secondary\s+risk'
    ],
    'packing_group': [
        r'Packing\s+group',
        r'PG',
        r'.*packing\s+group',
        r'Australian\s+Dangerous\s+Goods\s+packing\s+group'
    ],
}

# Expanded noise labels to exclude from values
NOISE_LABELS = [
    r'Telephone', r'Tel', r'Phone', r'Fax', r'E[-]?mail', r'Website', r'Email',
    r'Emergency', r'Address', r'Poison', r'Product\s+code', r'SDS\s+no\.?', r'SDS\s+number',
    r'Page\s+\d+', r'Date\s+of\s+issue', r'Revision\s+date', r'Version',
    r'Details\s+of\s+the\s+supplier', r'Contact\s+details', r'Emergency\s+telephone',
    r'MSDS\s+Date', r'Alternative\s+number', r'Facsimile\s+Number', r'Name',
    r'Australia\s+-\s+\d+', r'UK,?\s+NPIS', r'Registered\s+company\s+name',
    r'Safety\s+data\s+sheet', r'Document\s+number', r'\d{2,4}\s+\d{2,4}\s+\d{2,4}',
    r'Document\s+type', r'Country', r'Language', r'Format'
]

# Valid dangerous goods classes (1-9 with possible subdivisions)
VALID_DG_CLASSES = re.compile(r'^[1-9](?:\.[1-9])?$')

# Valid packing groups
VALID_PACKING_GROUPS = re.compile(r'^(?:I{1,3}|IV?|N\.?/?A\.?|None|Not\s+(?:applicable|required|assigned)|Not\s+subject)$', re.IGNORECASE)

# Minimum text length before triggering OCR fallback
MIN_TEXT_LENGTH = 50
