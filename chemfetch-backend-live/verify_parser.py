#!/usr/bin/env python3
"""
Quick verification of the SDS extractor files
"""

import sys
from pathlib import Path
import importlib.util

def check_file_imports():
    """Check if the main SDS extractor can be imported and has the required functions."""
    
    base_dir = Path(__file__).parent
    extractor_path = base_dir / "ocr_service" / "sds_parser_new" / "sds_extractor.py"
    
    print("🔍 Checking SDS Extractor...")
    print(f"📁 File path: {extractor_path}")
    print(f"📊 File size: {extractor_path.stat().st_size} bytes")
    
    # Check if file exists and has content
    if not extractor_path.exists():
        print("❌ File does not exist!")
        return False
    
    if extractor_path.stat().st_size < 1000:  # Should be much larger
        print("❌ File appears to be empty or too small!")
        return False
    
    # Try to import the module
    try:
        spec = importlib.util.spec_from_file_location("sds_extractor", extractor_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules["sds_extractor"] = module
            spec.loader.exec_module(module)
            
            # Check if main function exists
            if hasattr(module, 'parse_pdf'):
                print("✅ Module imported successfully")
                print("✅ parse_pdf function found")
                return True
            else:
                print("❌ parse_pdf function not found")
                return False
                
        else:
            print("❌ Could not create module spec")
            return False
            
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def check_field_extractor():
    """Check if the field extractor module can be imported."""
    
    base_dir = Path(__file__).parent
    field_extractor_path = base_dir / "ocr_service" / "sds_parser_new" / "modules" / "field_extractor.py"
    
    print(f"\n🔍 Checking Field Extractor...")
    print(f"📁 File path: {field_extractor_path}")
    print(f"📊 File size: {field_extractor_path.stat().st_size} bytes")
    
    if not field_extractor_path.exists():
        print("❌ Field extractor file does not exist!")
        return False
    
    if field_extractor_path.stat().st_size < 5000:  # Should be large
        print("❌ Field extractor appears to be empty or too small!")
        return False
    
    try:
        # Try to read the file and check for key functions
        with open(field_extractor_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        required_functions = [
            'extract_product_name',
            'extract_manufacturer', 
            'extract_description',
            'extract_date_from_header',
            'extract_section14_field'
        ]
        
        missing_functions = []
        for func in required_functions:
            if f"def {func}" not in content:
                missing_functions.append(func)
        
        if missing_functions:
            print(f"❌ Missing functions: {missing_functions}")
            return False
        else:
            print("✅ All required functions found")
            return True
            
    except Exception as e:
        print(f"❌ Error checking field extractor: {e}")
        return False

def main():
    print("🧪 SDS Parser Verification")
    print("=" * 40)
    
    extractor_ok = check_file_imports()
    field_extractor_ok = check_field_extractor()
    
    print(f"\n📋 Summary:")
    print(f"{'✅' if extractor_ok else '❌'} Main extractor: {'OK' if extractor_ok else 'FAILED'}")
    print(f"{'✅' if field_extractor_ok else '❌'} Field extractor: {'OK' if field_extractor_ok else 'FAILED'}")
    
    if extractor_ok and field_extractor_ok:
        print("\n🎉 All files are properly configured!")
        print("\nYou can now test with:")
        print("  python test_sds.py")
        print("  python test_improvements.py")
        return 0
    else:
        print("\n❌ Some files have issues that need to be fixed.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
