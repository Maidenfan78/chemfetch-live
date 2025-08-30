#!/usr/bin/env python3
"""
Compare old vs improved parser results
"""
import json
from pathlib import Path

def compare_results():
    """Compare original test results with improved parser results."""
    
    print("📊 PARSER IMPROVEMENT COMPARISON")
    print("=" * 60)
    
    # Load original results
    original_file = Path("test-data/sds_test_results.json")
    improved_file = Path("test-data/sds_test_results_improved.json")
    
    if not original_file.exists():
        print(f"❌ Original results not found: {original_file}")
        return
    
    with open(original_file) as f:
        original = json.load(f)
    
    if improved_file.exists():
        with open(improved_file) as f:
            improved = json.load(f)
    else:
        print("ℹ️  Improved results not yet available. Run 'python test_improved_sds.py' first.")
        print("For now, showing analysis of what SHOULD be improved based on the working parser:")
        improved = None
    
    print(f"\n📈 BEFORE vs AFTER COMPARISON")
    print("-" * 40)
    
    # Analyze specific problem cases
    problem_files = [
        {
            "filename": "sds_12.pdf",
            "old_issues": ["Product name: 'MSDS Date'", "Manufacturer: 'Name'"],
            "expected_fix": "Should extract actual product name and company name"
        },
        {
            "filename": "sds_13.pdf", 
            "old_issues": ["Product name: 'UK, NPIS - 0344 8920111...'", "Manufacturer: 'safety data sheet'"],
            "expected_fix": "Should filter out phone numbers and document types"
        },
        {
            "filename": "sds_14.pdf",
            "old_issues": ["Manufacturer: ':'", "DG class: '1950' (invalid)"],
            "expected_fix": "Should reject punctuation and validate DG classes"
        },
        {
            "filename": "sds_8.pdf",
            "old_issues": ["Product name: 'Australia - 13 11 26'", "Product/manufacturer swapped"],
            "expected_fix": "Should filter out emergency contact info"
        },
        {
            "filename": "sds_3.pdf",
            "old_issues": ["Product name: 'Alternative number(s)'", "DG class: '14.5' (invalid)"],
            "expected_fix": "Should filter out labels and validate DG classes"
        },
        {
            "filename": "sds_9.pdf",
            "old_issues": ["Product name: ':'", "Manufacturer: ':'"],
            "expected_fix": "Should filter out punctuation marks"
        }
    ]
    
    improvements_count = 0
    total_issues = 0
    
    for case in problem_files:
        filename = case["filename"]
        
        print(f"\n🔍 {filename}")
        print("  " + "-" * (len(filename) + 2))
        
        # Show original issues
        original_result = original["results"].get(filename, {})
        if original_result.get("extracted_values"):
            print("  ❌ BEFORE:")
            for issue in case["old_issues"]:
                print(f"    • {issue}")
                total_issues += 1
        
        # Show improved results if available
        if improved:
            improved_result = improved["results"].get(filename, {})
            if improved_result.get("extracted_values"):
                print("  ✅ AFTER:")
                ev = improved_result["extracted_values"]
                
                # Check if issues were fixed
                fixed_issues = []
                
                # Check product name fixes
                product_name = ev.get("product_name", {}).get("value")
                if product_name:
                    if filename == "sds_12.pdf" and product_name != "MSDS Date":
                        fixed_issues.append(f"Product name: '{product_name}' (no longer 'MSDS Date')")
                    elif filename == "sds_13.pdf" and "NPIS" not in product_name:
                        fixed_issues.append(f"Product name: '{product_name}' (no longer phone number)")
                    elif filename == "sds_8.pdf" and "Australia - 13 11 26" not in product_name:
                        fixed_issues.append(f"Product name: '{product_name}' (no longer emergency contact)")
                    elif filename == "sds_3.pdf" and product_name != "Alternative number(s)":
                        fixed_issues.append(f"Product name: '{product_name}' (no longer label)")
                    elif filename == "sds_9.pdf" and product_name != ":":
                        fixed_issues.append(f"Product name: '{product_name}' (no longer punctuation)")
                    elif product_name not in ["MSDS Date", "Alternative number(s)", ":", "Australia - 13 11 26"]:
                        fixed_issues.append(f"Product name: '{product_name}' ✓")
                
                # Check manufacturer fixes
                manufacturer = ev.get("manufacturer", {}).get("value") 
                if manufacturer:
                    if manufacturer not in ["Facsimile Number", "safety data sheet", ":", "Name", "'s", "Registered company name"]:
                        fixed_issues.append(f"Manufacturer: '{manufacturer}' ✓")
                
                # Check DG class fixes
                dg_class = ev.get("dangerous_goods_class", {}).get("value")
                if dg_class and dg_class not in ["14.5", "1950"]:
                    fixed_issues.append(f"DG class: '{dg_class}' ✓")
                
                if fixed_issues:
                    for fix in fixed_issues:
                        print(f"    • {fix}")
                        improvements_count += 1
                else:
                    print("    • No improvements detected")
        else:
            print("  🔄 EXPECTED AFTER:")
            print(f"    • {case['expected_fix']}")
    
    print(f"\n📈 SUMMARY")
    print("-" * 20)
    if improved:
        print(f"🎯 Issues fixed: {improvements_count}/{total_issues}")
        print(f"📊 Success rate: {(improvements_count/total_issues)*100:.1f}%")
    else:
        print(f"📋 Total issues identified: {total_issues}")
        print("🔧 Run 'python test_improved_sds.py' to see actual improvements")
    
    print(f"\n🚀 KEY IMPROVEMENTS IN WORKING PARSER:")
    improvements = [
        "✅ Enhanced noise detection filters out labels and punctuation",
        "✅ Phone number patterns rejected for product names", 
        "✅ Dangerous goods class validation (only 1-9.x accepted)",
        "✅ Multiple extraction strategies for product names",
        "✅ Better manufacturer detection in supplier sections",
        "✅ Final validation step catches remaining issues"
    ]
    
    for improvement in improvements:
        print(f"  {improvement}")

if __name__ == '__main__':
    compare_results()
