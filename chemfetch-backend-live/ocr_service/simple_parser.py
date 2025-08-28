# Simple SDS parser that works without complex imports
# Fallback version for when main parse_sds.py has import issues

import tempfile
import requests
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def parse_sds_pdf_simple(pdf_url: str, product_id: int):
    """
    Simplified SDS parser that uses the direct extractor
    Returns data in the format expected by the backend
    """
    logger.info(f"[SIMPLE_PARSER] Starting simple SDS parsing for product {product_id}")
    
    try:
        # Import the working extractor
        from sds_parser_new.sds_extractor import parse_pdf
        
        # Download PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            
            tmp_path = Path(tmp_file.name)
        
        try:
            # Parse the PDF
            parsed_data = parse_pdf(tmp_path)
            logger.info("[SIMPLE_PARSER] PDF parsing successful")
            
            # Extract values with confidence checking
            def get_value(field_name):
                field = parsed_data.get(field_name, {})
                if isinstance(field, dict) and field.get('confidence', 0) > 0:
                    return field.get('value')
                return None
            
            # Convert to backend format
            dangerous_goods_class = get_value('dangerous_goods_class')
            is_dangerous_good = False
            
            if dangerous_goods_class:
                dangerous_goods_class = dangerous_goods_class.strip()
                if dangerous_goods_class.lower() not in ['none', 'not applicable', 'n/a', 'na']:
                    is_dangerous_good = True
            
            subsidiary_risk = get_value('subsidiary_risk')
            subsidiary_risks = []
            if subsidiary_risk and subsidiary_risk.lower() not in ['none', 'not applicable', 'n/a', 'na']:
                subsidiary_risks = [subsidiary_risk]
            
            result = {
                'product_id': product_id,
                'vendor': get_value('manufacturer'),
                'issue_date': get_value('issue_date'),
                'hazardous_substance': is_dangerous_good,
                'dangerous_good': is_dangerous_good,
                'dangerous_goods_class': dangerous_goods_class,
                'packing_group': get_value('packing_group'),
                'subsidiary_risks': subsidiary_risks,
                'hazard_statements': [],
                'raw_json': parsed_data
            }
            
            logger.info("[SIMPLE_PARSER] Parsing completed successfully")
            return result
            
        finally:
            # Cleanup
            if tmp_path.exists():
                tmp_path.unlink()
                
    except Exception as e:
        logger.error(f"[SIMPLE_PARSER] Parsing failed: {e}")
        raise
