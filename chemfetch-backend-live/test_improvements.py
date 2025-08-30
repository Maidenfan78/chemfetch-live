#!/usr/bin/env python3
"""
Test the working parser on specific problem PDFs
"""
import sys
from pathlib import Path
import json

# Import our working parser
sys.path.insert(0, str(Path(__file__).parent))
from working_parser import parse_pdf

def test_problem_pdfs():
    """Test the parser on PDFs that had specific issues."""
    
    problem_cases = [
        {
            "file": "sds_12.pdf",
            "expected_issues": [
                "Product name should NOT be 'MSDS Date'",
                "Manufacturer should NOT be 'Name'"
            ]
        },
        {
            "file": "sds_13.pdf", 
            "expected_issues": [
                "Product name should NOT be phone number",
                "Manufacturer should NOT be 'safety data sheet'"
            ]
        },
        {
            "file": "sds_14.pdf",
            "expected_issues": [
                "Manufacturer should NOT be ':'",
                "DG class should NOT be '1950' (UN number)"
            ]
        },
        {
            "file": "sds_8.pdf",
            "expected_issues": [
                "Product name should NOT be 'Australia - 13 11 26'",
                "Product/manufacturer might be swapped"
            ]
        },
        {
            "file": "sds_3.pdf",
            "expected_issues": [
                "Product name should NOT be 'Alternative number(s)'",
                "DG class should NOT be '14.5'"
            ]
        }
    ]
    
    print("🧪 TESTING IMPROVED PARSER")
    print("=" * 50)
    
    test_dir = Path("test-data/sds-pdfs")
    
    for case in problem_cases:
        pdf_path = test_dir / case["file"]
        
        if not pdf_path.exists():
            print(f"❌ {case['file']}: File not found")
            continue
            
        print(f"\n📄 Testing: {case['file']}")
        print("-" * 30)
        
        try:
            result = parse_pdf(pdf_path)
            
            # Check the results
            fields = ['product_name', 'manufacturer', 'dangerous_goods_class', 'issue_date']
            improvements = []
            remaining_issues = []
            
            for field in fields:
                if field in result:
                    value = result[field].get('value')
                    if value:
                        print(f"✅ {field}: '{value}'")
                        
                        # Check specific improvements based on file
                        if case["file"] == "sds_12.pdf":
                            if field == "product_name" and value == "MSDS Date":
                                remaining_issues.append(f"Still extracting 'MSDS Date' as product name")
                            elif field == "manufacturer" and value == "Name":
                                remaining_issues.append(f"Still extracting 'Name' as manufacturer")
                        
                        elif case["file"] == "sds_13.pdf":
                            if field == "product_name" and "NPIS" in value:
                                remaining_issues.append(f"Still extracting phone number as product name")
                            elif field == "manufacturer" and value == "safety data sheet":
                                remaining_issues.append(f"Still extracting 'safety data sheet' as manufacturer")
                        
                        elif case["file"] == "sds_14.pdf":
                            if field == "manufacturer" and value == ":":
                                remaining_issues.append(f"Still extracting ':' as manufacturer")
                            elif field == "dangerous_goods_class" and value == "1950":
                                remaining_issues.append(f"Still extracting '1950' as DG class")
                        
                        elif case["file"] == "sds_8.pdf":
                            if field == "product_name" and "Australia - 13 11 26" in value:
                                remaining_issues.append(f"Still extracting phone number as product name")
                        
                        elif case["file"] == "sds_3.pdf":
                            if field == "product_name" and value == "Alternative number(s)":
                                remaining_issues.append(f"Still extracting 'Alternative number(s)' as product name")
                            elif field == "dangerous_goods_class" and value == "14.5":
                                remaining_issues.append(f"Still extracting invalid DG class '14.5'")
                    else:
                        print(f"❌ {field}: Not extracted")
                        
            # Summary for this file
            if remaining_issues:
                print(f"\n🔴 Remaining issues:")
                for issue in remaining_issues:
                    print(f"  - {issue}")
            else:
                print(f"\n🟢 All major issues appear to be fixed!")
            
        except Exception as e:
            print(f"❌ Error parsing {case['file']}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    test_problem_pdfs()
