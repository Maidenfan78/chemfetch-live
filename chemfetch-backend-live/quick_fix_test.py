#!/usr/bin/env python3
"""
Quick fix for parse-sds endpoint
Replace the broken function with this working version
"""

# Add this function to your ocr_service.py file to replace the broken one

def parse_sds_working(product_id, pdf_url):
    """
    Working SDS parser using the successful verification logic
    """
    print(f"Starting working SDS parser for product {product_id}") 
    
    try:
        # Import what we need
        import tempfile
        import re
        from pathlib import Path
        import requests
        import pdfplumber
        
        # Download PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            
            tmp_path = Path(tmp_file.name)
        
        try:
            # Extract text using pdfplumber (we know this works)
            text = ""
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            print(f"Extracted {len(text)} characters")
            
            if len(text) < 100:
                return {"error": "Insufficient text extracted"}
            
            # Basic field extraction
            vendor = None
            issue_date = None
            dangerous_goods_class = None
            
            # Extract vendor
            vendor_match = re.search(r'(?:Manufacturer|Company):\s*([^\n\r]+)', text, re.IGNORECASE)
            if vendor_match:
                vendor = vendor_match.group(1).strip()
            
            # Extract issue date
            date_match = re.search(r'(?:Issue Date|Revision Date):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
            if date_match:
                issue_date = date_match.group(1).strip()
            
            # Extract dangerous goods class
            dg_match = re.search(r'(?:Hazard Class|Class):\s*([1-9](?:\.\d+)?)', text, re.IGNORECASE)
            if dg_match:
                dangerous_goods_class = dg_match.group(1).strip()
            
            is_dangerous = bool(dangerous_goods_class and dangerous_goods_class.lower() not in ['none', 'n/a'])
            
            return {
                "product_id": int(product_id),
                "vendor": vendor,
                "issue_date": issue_date,
                "hazardous_substance": is_dangerous,
                "dangerous_good": is_dangerous,
                "dangerous_goods_class": dangerous_goods_class,
                "packing_group": None,
                "subsidiary_risks": [],
                "hazard_statements": [],
                "raw_json": {
                    "text_length": len(text),
                    "parsing_method": "simple_working",
                    "fields_extracted": {
                        "vendor": bool(vendor),
                        "issue_date": bool(issue_date),
                        "dangerous_goods_class": bool(dangerous_goods_class)
                    }
                },
                "ocr_available": True
            }
            
        finally:
            if tmp_path.exists():
                tmp_path.unlink()
    
    except Exception as e:
        print(f"Parsing failed: {e}")
        return {"error": str(e)}

# Test it
if __name__ == "__main__":
    result = parse_sds_working(
        999, 
        "https://sdshosting.chemalert.com/company/10021710/download/3089176_001_001.pdf"
    )
    print("Result:", result)
