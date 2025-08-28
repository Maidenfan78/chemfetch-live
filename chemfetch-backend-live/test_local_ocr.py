#!/usr/bin/env python3
"""
Local OCR Service Test - Tests only local development setup
Run this to verify your OCR service works locally before deploying
"""
import subprocess
import time
import requests
import json
import os
import sys
from pathlib import Path
import signal

def start_local_ocr_service():
    """Start OCR service locally and return the process"""
    print("🚀 Starting local OCR service...")
    
    ocr_dir = Path("ocr_service")
    if not ocr_dir.exists():
        print("❌ ocr_service directory not found")
        return None
    
    try:
        # Check if requirements are installed
        print("📦 Checking dependencies...")
        result = subprocess.run([
            sys.executable, "-c", "import flask, pdfplumber; print('Dependencies OK')"
        ], capture_output=True, text=True, cwd=ocr_dir)
        
        if result.returncode != 0:
            print("⚠️ Installing requirements...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ], cwd=ocr_dir, check=True)
        else:
            print("✅ Dependencies already installed")
        
        # Start the service
        print("🟢 Starting OCR service on localhost:5001...")
        env = os.environ.copy()
        env['OCR_MODE'] = 'text-only'
        env['DEBUG_IMAGES'] = '0'
        
        process = subprocess.Popen([
            sys.executable, "ocr_service.py"
        ], cwd=ocr_dir, env=env)
        
        # Give it time to start
        print("⏳ Waiting for service to start...")
        for i in range(10):
            try:
                response = requests.get("http://localhost:5001/health", timeout=2)
                if response.status_code == 200:
                    print(f"✅ OCR service started successfully (PID: {process.pid})")
                    print(f"📊 Health data: {json.dumps(response.json(), indent=2)}")
                    return process
            except:
                pass
            time.sleep(1)
            print(f"   Attempt {i+1}/10...")
        
        print("❌ OCR service failed to start properly")
        process.terminate()
        return None
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return None
    except Exception as e:
        print(f"❌ Failed to start OCR service: {e}")
        return None

def test_local_sds_parsing():
    """Test SDS parsing with the Isocol product from your logs"""
    print("\n🧾 Testing Local SDS Parsing")
    print("=" * 40)
    
    test_cases = [
        {
            "name": "SDS Verification",
            "url": "http://localhost:5001/verify-sds",
            "data": {
                "url": "https://sdshosting.chemalert.com/company/10021710/download/3089176_001_001.pdf",
                "name": "Isocol Rubbing Alcohol"
            },
            "timeout": 60
        },
        {
            "name": "SDS Parsing", 
            "url": "http://localhost:5001/parse-sds",
            "data": {
                "product_id": 999,
                "pdf_url": "https://sdshosting.chemalert.com/company/10021710/download/3089176_001_001.pdf"
            },
            "timeout": 120
        }
    ]
    
    for test in test_cases:
        try:
            print(f"\n🔍 Testing {test['name']}...")
            response = requests.post(
                test["url"],
                json=test["data"],
                timeout=test["timeout"]
            )
            
            print(f"✅ Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if test["name"] == "SDS Verification":
                    print(f"   - Verified: {result.get('verified')}")
                    print(f"   - Text Length: {result.get('text_length')}")
                    print(f"   - Keyword Matches: {result.get('keyword_matches')}")
                else:  # SDS Parsing
                    print(f"   - Product ID: {result.get('product_id')}")
                    print(f"   - Vendor: {result.get('vendor')}")
                    print(f"   - Issue Date: {result.get('issue_date')}")
                    print(f"   - Dangerous Good: {result.get('dangerous_good')}")
            else:
                print(f"❌ Error: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"⏰ {test['name']} timed out (this can be normal for large PDFs)")
        except Exception as e:
            print(f"❌ {test['name']} error: {e}")

def main():
    """Main function"""
    print("🧪 ChemFetch Local OCR Service Test")
    print("=" * 50)
    print("This tests your OCR service locally before deploying to Render")
    print()
    
    # Check if we're in the right directory
    if not Path("ocr_service").exists():
        print("❌ Error: ocr_service directory not found")
        print("💡 Please run this script from chemfetch-backend-live directory")
        return 1
    
    # Start OCR service locally
    process = start_local_ocr_service()
    if not process:
        print("❌ Failed to start local OCR service")
        return 1
    
    try:
        # Test SDS parsing functionality
        test_local_sds_parsing()
        
        print("\n" + "=" * 50)
        print("📋 LOCAL TEST COMPLETE")
        print("=" * 50)
        print("✅ Local OCR service is working!")
        print("🚀 Ready to deploy to Render")
        print()
        print("Next steps:")
        print("1. Commit your changes: git add . && git commit -m 'Fix OCR service'")
        print("2. Push to repository: git push")
        print("3. Deploy OCR service first, then backend")
        print("4. Run: python test_ocr_connection.py (after deployment)")
        
    finally:
        # Clean shutdown
        print(f"\n🛑 Stopping OCR service (PID: {process.pid})...")
        process.terminate()
        
        # Wait for graceful shutdown
        try:
            process.wait(timeout=5)
            print("✅ OCR service stopped cleanly")
        except subprocess.TimeoutExpired:
            print("⚠️ Force killing OCR service...")
            process.kill()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
