#!/usr/bin/env python3
"""
Enhanced SDS Parser for ChemFetch System
Integrates the improved sds_extractor.py with the existing chemfetch backend.
"""

import sys 
import json
import argparse
import tempfile
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import the new SDS extractor
try:
    from sds_parser_new.sds_extractor import parse_pdf
    logger.info("[PARSE_SDS] Successfully imported sds_extractor.parse_pdf")
except ImportError as e:
    logger.error(f"[PARSE_SDS] Failed to import sds_extractor: {e}")
    logger.error(
        "[PARSE_SDS] Check that sds_parser_new directory exists and contains sds_extractor.py"
    )
    # Create a fallback parse function
    def parse_pdf(pdf_path):
        return {
            "error": "SDS extractor not available",
            "fallback": True,
            "note": "Using basic text extraction only",
        }

    logger.warning("[PARSE_SDS] Using fallback parse function")


def download_pdf(url: str, temp_dir: Path) -> Optional[Path]:
    """Download PDF from URL to temporary file."""
    try:
        logger.info(f"[PARSE_SDS] Starting PDF download from: {url}")
        logger.info(f"[PARSE_SDS] Download timeout: 30 seconds")
        logger.info(f"[PARSE_SDS] Temp directory: {temp_dir}")
        
        response = requests.get(url, timeout=30, stream=True)
        logger.info(f"[PARSE_SDS] HTTP response status: {response.status_code}")
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        content_length = response.headers.get('content-length', 'unknown')
        logger.info(f"[PARSE_SDS] Content type: {content_type}")
        logger.info(f"[PARSE_SDS] Content length: {content_length} bytes")
        
        if 'pdf' not in content_type:
            logger.warning(f"[PARSE_SDS] Content type is not PDF: {content_type}")
        
        # Save to temporary file
        temp_file = temp_dir / f"sds_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        logger.info(f"[PARSE_SDS] Saving to temp file: {temp_file}")
        
        downloaded_bytes = 0
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded_bytes += len(chunk)
                if downloaded_bytes % (1024 * 1024) == 0:  # Log every MB
                    logger.info(f"[PARSE_SDS] Downloaded {downloaded_bytes // (1024 * 1024)}MB...")
        
        logger.info(f"[PARSE_SDS] Download complete: {temp_file} ({downloaded_bytes} bytes)")
        return temp_file
        
    except Exception as e:
        logger.error(f"[PARSE_SDS] Failed to download PDF: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[PARSE_SDS] Download traceback: {traceback.format_exc()}")
        return None


def transform_to_chemfetch_format(parsed_data: Dict[str, Any], product_id: int) -> Dict[str, Any]:
    """Transform the parsed data to match chemfetch's expected format."""
    
    def get_value(field_name: str) -> Optional[str]:
        """Extract value from confidence-based field."""
        field = parsed_data.get(field_name, {})
        if isinstance(field, dict) and field.get('confidence', 0) > 0:
            return field.get('value')
        return None
    
    # Map dangerous goods class to boolean
    dangerous_goods_class = get_value('dangerous_goods_class')
    is_dangerous_good = False
    
    if dangerous_goods_class:
        dangerous_goods_class = dangerous_goods_class.strip()
        # Consider it a dangerous good if it has a class number/code and is not "none" or "not applicable"
        if dangerous_goods_class.lower() not in ['none', 'not applicable', 'n/a', 'na']:
            is_dangerous_good = True
    
    # Determine if it's a hazardous substance (simple heuristic)
    # In a real implementation, this would use more sophisticated logic
    product_name = get_value('product_name') or ''
    manufacturer = get_value('manufacturer') or ''
    is_hazardous = is_dangerous_good  # Basic heuristic
    
    # Format subsidiary risks as array
    subsidiary_risk = get_value('subsidiary_risk')
    subsidiary_risks = []
    if subsidiary_risk and subsidiary_risk.lower() not in ['none', 'not applicable', 'n/a', 'na']:
        subsidiary_risks = [subsidiary_risk]
    
    result = {
        'product_id': product_id,
        'product_name': get_value('product_name'),
        'vendor': manufacturer,
        'issue_date': get_value('issue_date'),
        'hazardous_substance': is_hazardous,
        'dangerous_good': is_dangerous_good,
        'dangerous_goods_class': dangerous_goods_class,
        'packing_group': get_value('packing_group'),
        'subsidiary_risks': subsidiary_risks,
        'hazard_statements': [],  # Not extracted by current parser
        'raw_json': parsed_data
    }
    
    return result


def parse_sds_pdf(pdf_url: str, product_id: int) -> Dict[str, Any]:
    """
    Main function to parse SDS PDF from URL.
    
    Args:
        pdf_url: URL of the PDF to parse
        product_id: ID of the product in the database
        
    Returns:
        Dictionary with parsed SDS data in chemfetch format
    """
    
    logger.info(f"[PARSE_SDS] Starting SDS parsing for product {product_id}")
    logger.info(f"[PARSE_SDS] PDF URL: {pdf_url}")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        logger.info(f"[PARSE_SDS] Created temp directory: {temp_path}")
        
        # Download PDF
        logger.info(f"[PARSE_SDS] Step 1: Downloading PDF...")
        pdf_file = download_pdf(pdf_url, temp_path)
        if not pdf_file:
            raise Exception("Failed to download PDF") 
        
        logger.info(f"[PARSE_SDS] Step 2: PDF downloaded successfully: {pdf_file}")
        logger.info(f"[PARSE_SDS] File size: {pdf_file.stat().st_size} bytes")
        
        # Parse PDF
        logger.info(f"[PARSE_SDS] Step 3: Starting PDF parsing...")
        try:
            parsed_data = parse_pdf(pdf_file)
            logger.info(f"[PARSE_SDS] Step 3 complete: PDF parsing successful")
            logger.info(f"[PARSE_SDS] Parsed data keys: {list(parsed_data.keys()) if isinstance(parsed_data, dict) else 'Non-dict result'}")
        except Exception as e:
            logger.error(f"[PARSE_SDS] PDF parsing failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[PARSE_SDS] Parsing traceback: {traceback.format_exc()}")
            raise
        
        # Transform to chemfetch format
        logger.info(f"[PARSE_SDS] Step 4: Transforming to chemfetch format...")
        try:
            result = transform_to_chemfetch_format(parsed_data, product_id)
            logger.info(f"[PARSE_SDS] Step 4 complete: Transformation successful")
            logger.info(f"[PARSE_SDS] Result keys: {list(result.keys())}")
        except Exception as e:
            logger.error(f"[PARSE_SDS] Format transformation failed: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[PARSE_SDS] Transform traceback: {traceback.format_exc()}")
            raise
        
        logger.info(f"[PARSE_SDS] Successfully parsed SDS for product {product_id}")
        return result


def main():
    """Command line interface for SDS parsing."""
    parser = argparse.ArgumentParser(description='Parse SDS PDF for ChemFetch')
    parser.add_argument('--product-id', type=int, required=True, help='Product ID')
    parser.add_argument('--url', required=True, help='PDF URL')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info(f"[PARSE_SDS] Script started with args: product_id={args.product_id}, url={args.url}")
    logger.info(f"[PARSE_SDS] Verbose mode: {args.verbose}")
    logger.info(f"[PARSE_SDS] Python version: {sys.version}")
    logger.info(f"[PARSE_SDS] Working directory: {Path.cwd()}")
    
    try:
        start_time = datetime.now()
        logger.info(f"[PARSE_SDS] Starting parse at: {start_time.isoformat()}")
        
        result = parse_sds_pdf(args.url, args.product_id)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"[PARSE_SDS] Parse completed at: {end_time.isoformat()}")
        logger.info(f"[PARSE_SDS] Total duration: {duration:.2f} seconds")
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
        
    except Exception as e:
        error_result = {
            'error': str(e),
            'product_id': args.product_id,
            'timestamp': datetime.now().isoformat()
        }
        print(json.dumps(error_result, indent=2))
        logger.error(f"[PARSE_SDS] Script failed to parse SDS: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[PARSE_SDS] Script traceback: {traceback.format_exc()}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
