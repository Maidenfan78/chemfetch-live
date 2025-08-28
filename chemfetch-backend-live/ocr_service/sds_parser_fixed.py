# IMMEDIATE FIX - Replace the broken parse-sds endpoint
# Add this to the end of your ocr_service.py file (before if __name__ == '__main__':)

@app.route('/parse-sds-fixed', methods=['POST'])
def parse_sds_fixed():
    """
    Working SDS parser that uses the successful verification logic
    """
    logger.info("Fixed SDS parsing endpoint called")
    
    data = request.json or {}
    product_id = data.get("product_id")
    pdf_url = data.get("pdf_url")
    
    if not product_id or not pdf_url:
        return jsonify({"error": "Missing product_id or pdf_url"}), 400

    try:
        # Use the working verification function (we know this works)
        verification_result = verify_pdf_sds(pdf_url, "Product")
        
        if not verification_result.get('verified'):
            return jsonify({
                "error": "PDF failed verification",
                "verification_result": verification_result
            }), 400
        
        # Extract basic SDS information using simple patterns
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            
            tmp_path = Path(tmp_file.name)
        
        try:
            # Extract text using pdfplumber (working method)
            import pdfplumber
            text = ""
            with pdfplumber.open(tmp_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            
            # Basic regex extraction
            vendor_match = re.search(r'(?:Manufacturer|Company):\s*([^\n\r]+)', text, re.IGNORECASE)
            vendor = vendor_match.group(1).strip() if vendor_match else None
            
            date_match = re.search(r'(?:Issue Date|Revision Date):\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
            issue_date = date_match.group(1).strip() if date_match else None
            
            dg_match = re.search(r'(?:Hazard Class|Class):\s*([1-9](?:\.\d+)?)', text, re.IGNORECASE)
            dangerous_goods_class = dg_match.group(1).strip() if dg_match else None
            
            is_dangerous = bool(dangerous_goods_class and dangerous_goods_class.lower() not in ['none', 'n/a'])
            
            result = {
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
                    "verification_result": verification_result,
                    "text_length": len(text),
                    "parsing_method": "simple_regex"
                },
                "ocr_available": True
            }
            
            logger.info("Simple parsing successful")
            return result
            
        finally:
            if tmp_path.exists():
                os.unlink(tmp_path)
    
    except Exception as e:
        logger.error(f"Simple parsing failed: {e}")
        return {
            "product_id": int(product_id),
            "error": str(e)
        }

# Test function
if __name__ == "__main__":
    test_result = parse_sds_simple(
        "https://sdshosting.chemalert.com/company/10021710/download/3089176_001_001.pdf", 
        999
    )
    print("Test result:", test_result)
