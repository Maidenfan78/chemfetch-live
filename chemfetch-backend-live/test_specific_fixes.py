#!/usr/bin/env python3
"""
Test script to verify fixes for specific issues mentioned in issues.txt
"""

import sys
import subprocess
from pathlib import Path
import json

def test_specific_issues():
    """Test the fixed parser on the specific issues from issues.txt"""
    
    base_dir = Path(__file__).parent
    parser_script = base_dir / "ocr_service" / "sds_parser_new" / "sds_extractor.py"
    test_pdfs_dir = base_dir / "test-data" / "sds-pdfs"
    
    # Expected results based on issues.txt
    expected_results = {
        "sds_1.PDF": {
            "description": "Use Antibacterial rub preparation for topical human use.",
            "dangerous_goods_class": "9",
            "packing_group": "III",
            "issues": ["Description should be from Section 1", "DG class should be 9", "Packing group should be III"]
        },
        "sds_2.pdf": {
            "dangerous_goods_class": "3",
            "packing_group": "III", 
            "issues": ["DG class and packing group are in tables"]
        },
        "sds_3.pdf": {
            "product_name": "Armor All Original Protectant - Spray", # Trade name
            "issue_date": "2024-01-19",
            "issues": ["Product name should be trade name", "Issue date should be 2024-01-19 from header"]
        },
        "sds_5.pdf": {
            "issue_date": "2021-08-03", # Should extract REVISION DATE: 3 August 2021
            "issues": ["Issue date should be extracted from REVISION DATE format"]
        }
    }
    
    print("🔧 Testing Fixed SDS Parser - Specific Issues")
    print("=" * 60)
    
    for pdf_name, expected in expected_results.items():
        pdf_path = test_pdfs_dir / pdf_name
        if not pdf_path.exists():
            print(f"❌ {pdf_name} not found")
            continue
            
        print(f"\n📄 Testing: {pdf_name}")
        print("-" * 40)
        print("🎯 Expected issues to fix:")
        for issue in expected["issues"]:
            print(f"   • {issue}")
        print()
        
        try:
            # Run the parser
            result = subprocess.run(
                [sys.executable, str(parser_script), str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(base_dir)
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    
                    # Check specific fields mentioned in issues.txt
                    for field, expected_value in expected.items():
                        if field == "issues":
                            continue
                            
                        field_data = data.get(field, {})
                        if isinstance(field_data, dict):
                            actual_value = field_data.get('value')
                        else:
                            actual_value = field_data
                        
                        # Compare with expected
                        if field in ["dangerous_goods_class", "packing_group"]:
                            if actual_value == expected_value:
                                print(f"✅ {field}: {actual_value} (FIXED!)")
                            else:
                                print(f"❌ {field}: {actual_value} (expected: {expected_value})")
                        elif field == "issue_date":
                            if actual_value and expected_value in actual_value:
                                print(f"✅ {field}: {actual_value} (FIXED!)")
                            else:
                                print(f"❌ {field}: {actual_value} (expected: {expected_value})")
                        elif field == "product_name":
                            if actual_value and expected_value.lower() in actual_value.lower():
                                print(f"✅ {field}: {actual_value} (FIXED!)")
                            else:
                                print(f"❌ {field}: {actual_value} (expected: {expected_value})")
                        elif field == "description":
                            if actual_value:
                                print(f"✅ {field}: {actual_value}")
                            else:
                                print(f"❌ {field}: None (expected something from Section 1)")
                    
                    # Show all extracted fields for context
                    print(f"\n📋 All extracted fields:")
                    fields = ['product_name', 'manufacturer', 'description', 'issue_date', 'dangerous_goods_class', 'packing_group']
                    for field in fields:
                        field_data = data.get(field, {})
                        if isinstance(field_data, dict):
                            value = field_data.get('value')
                        else:
                            value = field_data
                        
                        status = "✅" if value else "⚠️"
                        print(f"   {status} {field}: {value}")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parse error: {e}")
                    print("Raw output:", result.stdout[:300] + "..." if len(result.stdout) > 300 else result.stdout)
            else:
                print(f"❌ Parser failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout (30s)")
        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\n📊 Test Complete!")
    print("Next step: Run 'python test_sds.py' to see full results")

if __name__ == '__main__':
    test_specific_issues()
