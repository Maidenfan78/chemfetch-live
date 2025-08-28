#!/usr/bin/env python3
"""
Test SDS Parsing Import - Quick test for the import fix
"""
import sys
import os
from pathlib import Path

def test_imports():
    """Test if all imports work correctly"""
    print("Testing Python imports for SDS parsing...")
    
    # Change to ocr_service directory
    ocr_dir = Path("ocr_service")
    if ocr_dir.exists():
        os.chdir(ocr_dir)
        print(f"Changed to directory: {os.getcwd()}")
    
    # Test imports one by one
    import_results = {}
    
    # Test 1: Basic Flask import
    try:
        import flask
        import_results['flask'] = f"OK - {flask.__version__}"
    except ImportError as e:
        import_results['flask'] = f"FAILED - {e}"
    
    # Test 2: PDF processing imports
    try:
        import pdfplumber
        import_results['pdfplumber'] = "OK"
    except ImportError as e:
        import_results['pdfplumber'] = f"FAILED - {e}"
    
    # Test 3: parse_sds import
    try:
        from parse_sds import parse_sds_pdf
        import_results['parse_sds'] = "OK"
    except ImportError as e:
        import_results['parse_sds'] = f"FAILED - {e}"
    
    # Test 4: sds_extractor import
    try:
        from sds_parser_new.sds_extractor import parse_pdf
        import_results['sds_extractor'] = "OK"
    except ImportError as e:
        import_results['sds_extractor'] = f"FAILED - {e}"
    
    # Test 5: OCR service main module
    try:
        # Don't actually import the main app to avoid starting Flask
        with open('ocr_service.py', 'r') as f:
            content = f.read()
            if 'parse_sds_pdf' in content and 'parse_pdf_direct' in content:
                import_results['ocr_service_structure'] = "OK"
            else:
                import_results['ocr_service_structure'] = "FAILED - Missing function references"
    except Exception as e:
        import_results['ocr_service_structure'] = f"FAILED - {e}"
    
    # Print results
    print("\nImport Test Results:")
    print("=" * 40)
    for module, result in import_results.items():
        status = "✅" if result.startswith("OK") else "❌"
        print(f"{status} {module}: {result}")
    
    # Overall status
    failed_imports = [k for k, v in import_results.items() if not v.startswith("OK")]
    
    if not failed_imports:
        print("\n🎉 All imports working correctly!")
        return True
    else:
        print(f"\n⚠️ {len(failed_imports)} import(s) failed:")
        for failed in failed_imports:
            print(f"   - {failed}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
