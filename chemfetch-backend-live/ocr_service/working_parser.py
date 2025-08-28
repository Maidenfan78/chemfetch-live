import os
import tempfile
import re
from pathlib import Path
from typing import Dict, Any
import requests
import logging

logger = logging.getLogger(__name__)

def parse_sds_simple(pdf_url: str, product_id: int) -> Dict[str, Any]:
    """
    Simple SDS parser that works without complex imports
    Uses the same text extraction logic that's working in verification
    """
    logger.info(f"Simple SDS parsing for product {product_id}")
    
    # Download PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        response = requests.get(pdf_url, timeout=30, stream=True)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=8192):
            tmp_file.write(chunk)
        
        tmp_path = Path(tmp_file.name)
    
    try:
        # Extract text using pdfplumber (we know this works from your logs)
        import pdfplumber
        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text
        
        logger.info(f"Extracted {len(text)} characters")
        
        if len(text) < 100:
            return {
                "product_id": int(product_id),
                "error": "Insufficient text extracted",
                "text_length": len(text)
            }
        
        # Basic field extraction using regex patterns
        vendor = None
        issue_date = None
        dangerous_goods_class = None
        packing_group = None
        
        # Extract vendor/manufacturer
        vendor_patterns = [
            r'(?:Manufacturer|Company|Supplier):\s*([^\n\r]+)',
            r'Details of the supplier[^\n]*\n([^\n]+)'
        ]
        for pattern in vendor_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                vendor = match.group(1).strip()
                break
        
        # Extract issue date  
        date_patterns = [
            r'(?:Issue Date|Revision Date|Date of issue):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'(?:Issue Date|Revision Date):\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                issue_date = match.group(1).strip()
                break
        
        # Extract dangerous goods class
        dg_patterns = [
            r'(?:Hazard Class|Transport hazard class|Class):\s*([1-9](?:\.\d+)?)',
            r'(?:ADG|IMDG|IATA)\s*Class:\s*([1-9](?:\.\d+)?)'
        ]
        for pattern in dg_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dangerous_goods_class = match.group(1).strip()
                break
        
        # Extract packing group
        pg_patterns = [
            r'Packing group:\s*(I{1,3}|IV|V)',
            r'PG:\s*(I{1,3}|IV|V|\d+)'
        ]
        for pattern in pg_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                packing_group = match.group(1).strip()
                break
        
        # Determine hazardous status
        is_dangerous_good = bool(dangerous_goods_class and dangerous_goods_class.lower() not in ['none', 'n/a'])
        hazard_indicators = ['flammable', 'corrosive', 'toxic', 'irritant', 'harmful']
        has_hazard = any(indicator in text.lower() for indicator in hazard_indicators)
        
        result = {
            "product_id": int(product_id),
            "vendor": vendor,
            "issue_date": issue_date,
            "hazardous_substance": is_dangerous_good or has_hazard,
            "dangerous_good": is_dangerous_good,
            "dangerous_goods_class": dangerous_goods_class,
            "packing_group": packing_group,
            "subsidiary_risks": [],
            "hazard_statements": [],
            "raw_json": {
                "extraction_method": "simple_regex",
                "text_length": len(text),
                "fields_found": {
                    "vendor": bool(vendor),
                    "issue_date": bool(issue_date),
                    "dangerous_goods_class": bool(dangerous_goods_class),
                    "packing_group": bool(packing_group)
                }
            },
            "ocr_available": True,  # Will be updated by caller
            "parsing_method": "simple_regex"
        }
        
        logger.info("Simple SDS parsing successful")
        return result
        
    finally:
        if tmp_path.exists():
            os.unlink(tmp_path)

if __name__ == "__main__":
    # Test the parser
    test_url = "https://sdshosting.chemalert.com/company/10021710/download/3089176_001_001.pdf"
    result = parse_sds_simple(test_url, 999)
    print("Test result:", result)
