#!/usr/bin/env python3
"""
Quick test of the improved SDS parser on specific problematic PDFs
"""

import sys
import subprocess
from pathlib import Path

def test_specific_pdfs():
    """Test the improved parser on the problematic PDFs mentioned in issues.txt"""
    
    base_dir = Path(__file__).parent
    parser_script = base_dir / "ocr_service" / "sds_parser_new" / "sds_extractor.py"
    test_pdfs_dir = base_dir / "test-data" / "sds-pdfs"
    
    # Test specific problematic PDFs
    problematic_pdfs = [
        "sds_1.PDF",  # Manufacturer issue: should be "Würth Chile Ltda." not "of the safety data sheet"
        "sds_2.pdf",  # Packing group issue: should be "III" not None
        "sds_3.pdf",  # Issue date missing: should be "2024-01-19" not None  
        "sds_5.pdf"   # Product name issue: should be "WD-40 Aerosol" not "Pty Ltd"
    ]
    
    print("🔧 Testing Improved SDS Parser")
    print("=" * 50)
    
    for pdf_name in problematic_pdfs:
        pdf_path = test_pdfs_dir / pdf_name
        if not pdf_path.exists():
            print(f"❌ {pdf_name} not found")
            continue
            
        print(f"\n📄 Testing: {pdf_name}")
        print("-" * 30)
        
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
                import json
                # Parse the JSON output
                try:
                    data = json.loads(result.stdout)
                    
                    # Show key extracted fields
                    fields = ['product_name', 'manufacturer', 'description', 'issue_date', 'dangerous_goods_class', 'packing_group']
                    
                    for field in fields:
                        field_data = data.get(field, {})
                        if isinstance(field_data, dict):
                            value = field_data.get('value')
                        else:
                            value = field_data
                        
                        status = "✅" if value else "⚠️"
                        print(f"{status} {field}: {value}")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ JSON parse error: {e}")
                    print("Raw output:", result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout)
            else:
                print(f"❌ Parser failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout (30s)")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_specific_pdfs()
