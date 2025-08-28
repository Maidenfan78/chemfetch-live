# Quick fix for SDS parsing - uses the working verification logic
# This bypasses the complex import issues

import re
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def parse_sds_from_text(text: str, product_id: int) -> Dict[str, Any]:
    """
    Extract SDS information from already-extracted text.
    Uses simple regex patterns to find key information.
    """
    logger.info(f"[QUICK_PARSER] Parsing SDS text ({len(text)} chars) for product {product_id}")
    
    # Basic field extraction patterns
    patterns = {
        'vendor': [
            r'(?:Manufacturer|Company|Supplier):\s*([^\n\r]+)',
            r'Details of the supplier[^\n]*\n([^\n]+)',
            r'Company name[^\n]*:\s*([^\n]+)'
        ],
        'issue_date': [
            r'(?:Issue Date|Revision Date|Date of issue|Prepared)[^\n]*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:Issue Date|Revision Date|Date of issue|Prepared)[^\n]*:\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})'
        ],
        'dangerous_goods_class': [
            r'(?:Hazard Class|Transport hazard class|Class)[^\n]*:\s*([1-9](?:\.\d+)?)',
            r'(?:ADG|IMDG|IATA)\s*Class[^\n]*:\s*([1-9](?:\.\d+)?)',
        ],
        'packing_group': [
            r'Packing group[^\n]*:\s*(I{1,3}|IV|V)',
            r'PG[^\n]*:\s*(I{1,3}|IV|V|\d+)'
        ]
    }
    
    # Extract fields
    result = {
        'product_id': product_id,
        'vendor': None,
        'issue_date': None,
        'hazardous_substance': None,
        'dangerous_good': None,
        'dangerous_goods_class': None,
        'packing_group': None,
        'subsidiary_risks': [],
        'hazard_statements': [],
        'raw_json': {
            'text_length': len(text),
            'extraction_method': 'regex_patterns',
            'source': 'verification_text'
        },
        'ocr_available': True,  # Will be updated by caller
        'parsing_method': 'quick_parser'
    }
    
    # Apply patterns
    for field, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                result[field] = value
                logger.info(f"[QUICK_PARSER] Found {field}: {value}")
                break
    
    # Determine dangerous good status
    dgc = result['dangerous_goods_class']
    if dgc and dgc.lower() not in ['none', 'not applicable', 'n/a']:
        result['dangerous_good'] = True
        result['hazardous_substance'] = True
    
    # Check for common hazard indicators in text
    hazard_indicators = ['flammable', 'corrosive', 'toxic', 'irritant', 'harmful']
    text_lower = text.lower()
    has_hazard = any(indicator in text_lower for indicator in hazard_indicators)
    
    if result['hazardous_substance'] is None:
        result['hazardous_substance'] = has_hazard
    
    logger.info(f"[QUICK_PARSER] Parsing complete for product {product_id}")
    return result
