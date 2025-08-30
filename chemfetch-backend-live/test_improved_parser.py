#!/usr/bin/env python3
"""
Simple test script to verify the improved SDS parser
"""
import json
import sys
from pathlib import Path

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from ocr_service.sds_parser_new.sds_extractor import parse_pdf

def test_single_pdf():
    """Test a single PDF to see if our improvements work."""
    
    # Test with sds_1.PDF first
    test_pdf = Path("test-data/sds-pdfs/sds_1.PDF")
    
    if not test_pdf.exists():
        print(f"Error: Test PDF not found: {test_pdf}")
        return
    
    print(f"Testing improved parser with: {test_pdf}")
    print("=" * 50)
    
    try:
        result = parse_pdf(test_pdf)
        
        print("RESULTS:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # Quick validation
        if 'product_name' in result and result['product_name'].get('value'):
            product_name = result['product_name']['value']
            print(f"\n✅ Product name extracted: '{product_name}'")
            
            # Check if it's noise
            if product_name in ['MSDS Date', 'Alternative number(s)', ':', 'Name']:
                print(f"❌ ERROR: Product name appears to be noise!")
            else:
                print(f"✅ Product name looks valid")
        else:
            print("❌ No product name extracted")
            
        if 'manufacturer' in result and result['manufacturer'].get('value'):
            manufacturer = result['manufacturer']['value']
            print(f"✅ Manufacturer extracted: '{manufacturer}'")
            
            # Check if it's noise
            if manufacturer in ['Facsimile Number', 'safety data sheet', ':', 'Name']:
                print(f"❌ ERROR: Manufacturer appears to be noise!")
            else:
                print(f"✅ Manufacturer looks valid")
        else:
            print("❌ No manufacturer extracted")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_single_pdf()
