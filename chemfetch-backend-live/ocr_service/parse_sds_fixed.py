# Fixed parse-sds function - replace the existing one
# This version works with the verification logic that's already successful

def parse_sds_http_fixed():
    """
    WORKING version of parse-sds that uses the successful verification logic
    """
    logger.info("SDS parsing endpoint called")
    
    data = request.json or {}
    product_id = data.get("product_id")
    pdf_url = data.get("pdf_url")
    
    logger.info(f"Product ID: {product_id}, PDF URL: {pdf_url[:100] if pdf_url else 'None'}...")

    if not product_id or not pdf_url:
        logger.warning(f"Missing required parameters: product_id={bool(product_id)}, pdf_url={bool(pdf_url)}")
        return jsonify({"error": "Missing product_id or pdf_url"}), 400

    try:
        logger.info("Starting SDS parsing using working verification method...")
        
        # Use the working verification function to extract and analyze text
        verification_result = verify_pdf_sds(pdf_url, "Product")
        
        if not verification_result.get('verified'):
            logger.error("PDF failed verification")
            return jsonify({
                "error": "PDF failed verification - not a valid SDS",
                "verification_result": verification_result
            }), 400
        
        logger.info(f"Verification passed - extracted {verification_result.get('text_length')} chars")
        
        # Since verification worked, extract basic SDS info from the text
        # Download PDF again to get the full text for parsing
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            
            tmp_path = Path(tmp_file.name)
        
        try:
            # Extract text using same method as verification
            text, used_ocr = extract_text_from_pdf_with_ocr(tmp_path, max_pages=10)
            
            # Basic regex extraction for key fields
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
                r'(?:Issue Date|Revision Date|Date of issue):\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4})'
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
            
            # Determine if it's hazardous/dangerous
            is_dangerous_good = bool(dangerous_goods_class and dangerous_goods_class.lower() not in ['none', 'n/a'])
            
            # Check for hazard indicators
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
                    "verification_result": verification_result,
                    "extraction_method": "regex_patterns",
                    "text_length": len(text),
                    "fields_found": {
                        "vendor": bool(vendor),
                        "issue_date": bool(issue_date),
                        "dangerous_goods_class": bool(dangerous_goods_class),
                        "packing_group": bool(packing_group)
                    }
                },
                "ocr_available": OCR_AVAILABLE,
                "parsing_method": "verification_with_regex"
            }
            
            logger.info("SDS parsing successful using verification method")
            return jsonify(result), 200
            
        finally:
            if tmp_path.exists():
                os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Parsing failed: {type(e).__name__}: {e}")
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return jsonify({"error": f"SDS parsing failed: {e}"}), 500
