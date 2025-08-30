#!/usr/bin/env python3
"""
Manual test of improved SDS parser
"""
import sys
import json
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from ocr_service.sds_parser_new.sds_extractor import parse_pdf
    print("✅ Successfully imported improved parser")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_specific_pdf(pdf_name):
    """Test a specific PDF and show results"""
    pdf_path = Path(f"test-data/sds-pdfs/{pdf_name}")
    
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        return None
        
    print(f"\n🧪 Testing: {pdf_name}")
    print("=" * 50)
    
    try:
        result = parse_pdf(pdf_path)
        
        print("📊 EXTRACTION RESULTS:")
        
        # Check each field
        fields = ['product_name', 'manufacturer', 'dangerous_goods_class', 'issue_date']
        
        for field in fields:
            if field in result and isinstance(result[field], dict):
                value = result[field].get('value')
                confidence = result[field].get('confidence', 0)
                
                if value:
                    print(f"✅ {field}: '{value}' (confidence: {confidence})")
                else:
                    print(f"❌ {field}: Not extracted")
            else:
                print(f"❌ {field}: Missing from result")
        
        print(f"\n📋 FULL RESULT:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        return result
        
    except Exception as e:
        print(f"❌ Error parsing {pdf_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # Test a few specific PDFs that had issues
    problem_pdfs = [
        'sds_12.pdf',  # Had "MSDS Date" as product name
        'sds_13.pdf',  # Had phone number as product name  
        'sds_8.pdf',   # Had swapped product name/manufacturer
        'sds_1.PDF'    # Known good baseline
    ]
    
    for pdf in problem_pdfs:
        test_specific_pdf(pdf)
        print("\n" + "="*60 + "\n")
