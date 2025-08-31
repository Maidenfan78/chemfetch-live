#!/usr/bin/env python3
"""
SDS Parser Test Script for ChemFetch
Simple script to test SDS parser with local PDF files.
"""

import subprocess
import sys
from pathlib import Path
import json

def main():
    """Test SDS parser with PDFs in test-data/sds-pdfs directory."""
    
    print("🧪 ChemFetch SDS Parser Test")
    print("=" * 30)
    
    # Setup paths
    script_dir = Path(__file__).parent
    test_dir = script_dir / "test-data" / "sds-pdfs"
    parser_script = script_dir / "ocr_service" / "sds_parser_new" / "sds_extractor.py"
    
    # Check if parser exists
    if not parser_script.exists():
        print(f"❌ Parser not found: {parser_script}")
        return 1
    
    # Create test directory if needed
    if not test_dir.exists():
        print(f"📁 Creating: {test_dir}")
        test_dir.mkdir(parents=True, exist_ok=True)
    
    # Find PDF files
    pdf_files = list(test_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ No PDF files in: {test_dir}")
        print("📋 Copy your SDS PDFs to test-data/sds-pdfs/ and run again")
        return 0
    
    print(f"📄 Found {len(pdf_files)} PDF files")

    # Define fields to extract and prepare results container
    fields = [
        "product_name",
        "manufacturer",
        "issue_date",
        "dangerous_goods_class",
        "packing_group",
    ]
    total_fields = len(fields)
    results = {}
    
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] Testing: {pdf_path.name}")
        print("-" * 40)
        
        try:
            result = subprocess.run(
                [sys.executable, str(parser_script), str(pdf_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(script_dir)
            )
            
            if result.returncode == 0:
                try:
                    # Find the JSON part (skip header lines)
                    stdout_lines = result.stdout.strip().split('\n')
                    json_start = -1
                    for idx, line in enumerate(stdout_lines):
                        if line.strip().startswith('{'):
                            json_start = idx
                            break
                    
                    if json_start >= 0:
                        json_text = '\n'.join(stdout_lines[json_start:])
                        data = json.loads(json_text)
                    else:
                        # Fallback: try parsing the whole output
                        data = json.loads(result.stdout)
                    # Show key extracted fields
                    found = 0
                    extracted_values = {}

                    for field in fields:
                        field_data = data.get(field)
                        value = None
                        confidence = 0

                        if isinstance(field_data, dict):
                            value = field_data.get("value")
                            confidence = field_data.get("confidence", 0)
                        elif field_data is not None:
                            value = field_data
                            confidence = 1.0

                        if value is not None:
                            print(f"✅ {field}: {value}")
                            found += 1
                        else:
                            print(f"⚠️ {field}: None")

                        extracted_values[field] = {
                            "value": value,
                            "confidence": confidence,
                        }

                    print(f"📊 Extracted {found}/{total_fields} key fields")
                    
                    # Store successful result
                    results[pdf_path.name] = {
                        'success': True,
                        'fields_extracted': found,
                        'total_fields': total_fields,
                        'extracted_values': extracted_values,
                        'full_data': data,
                        'file_size_mb': round(pdf_path.stat().st_size / (1024 * 1024), 2)
                    }
                    
                except json.JSONDecodeError as e:
                    print(f"⚠️  JSON parse error: {e}")
                    print("Raw output:")
                    print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
                    
                    results[pdf_path.name] = {
                        'success': False,
                        'error': f'JSON parse error: {e}',
                        'raw_output': result.stdout,
                        'file_size_mb': round(pdf_path.stat().st_size / (1024 * 1024), 2)
                    }
            else:
                print(f"❌ Failed: {result.stderr}")
                results[pdf_path.name] = {
                    'success': False,
                    'error': result.stderr,
                    'return_code': result.returncode,
                    'file_size_mb': round(pdf_path.stat().st_size / (1024 * 1024), 2)
                }
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout (60s)")
            results[pdf_path.name] = {
                'success': False,
                'error': 'Timeout after 60 seconds',
                'file_size_mb': round(pdf_path.stat().st_size / (1024 * 1024), 2)
            }
        except Exception as e:
            print(f"❌ Error: {e}")
            results[pdf_path.name] = {
                'success': False,
                'error': str(e),
                'file_size_mb': round(pdf_path.stat().st_size / (1024 * 1024), 2)
            }
    
    # Save results to JSON file
    results_file = script_dir / "test-data" / "sds_test_results.json"
    try:
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                'test_timestamp': str(Path(__file__).stat().st_mtime),
                'total_files': len(pdf_files),
                'successful': sum(1 for r in results.values() if r.get('success')),
                'failed': sum(1 for r in results.values() if not r.get('success')),
                'results': results
            }, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Results saved to: {results_file}")
    except Exception as e:
        print(f"❌ Failed to save results: {e}")
    
    # Summary
    successful = sum(1 for r in results.values() if r.get('success'))
    failed = len(pdf_files) - successful
    
    print(f"\n📊 **SUMMARY**")
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📄 Total: {len(pdf_files)}")
    
    if successful > 0:
        avg_fields = (
            sum(r.get('fields_extracted', 0) for r in results.values() if r.get('success'))
            / successful
        )
        print(f"📈 Avg fields: {avg_fields:.1f}/{total_fields}")
    
    print(f"\n🎉 Testing complete!")

if __name__ == '__main__':
    sys.exit(main())
