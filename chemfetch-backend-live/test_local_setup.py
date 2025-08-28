#!/usr/bin/env python3
"""
ChemFetch Local Development Test Script
Tests the full SDS parsing pipeline locally before deployment
"""
import subprocess
import time
import requests
import json
import os
import sys
from pathlib import Path

def test_ocr_service_local():
    """Test OCR service running locally"""
    print("🧪 Testing OCR Service Locally")
    print("=" * 40)
    
    # Check if OCR service is running
    try:
        response = requests.get("http://localhost:5001/health", timeout=5)
        print(f"✅ OCR Service: {response.status_code}")
        print(f"📊 Health Data: {json.dumps(response.json(), indent=2)}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ OCR service not running on localhost:5001")
        return False
    except Exception as e:
        print(f"❌ Error testing OCR service: {e}")
        return False

def start_ocr_service():
    """Start OCR service locally"""
    print("🚀 Starting OCR Service...")
    
    ocr_dir = Path("ocr_service")
    if not ocr_dir.exists():
        print("❌ ocr_service directory not found")
        return False
    
    try:
        # Install requirements first
        print("📦 Installing requirements...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], cwd=ocr_dir, check=True, capture_output=True)
        
        # Start the service
        print("🟢 Starting Python OCR service...")
        process = subprocess.Popen([
            sys.executable, "ocr_service.py"
        ], cwd=ocr_dir)
        
        # Give it time to start
        time.sleep(3)
        
        # Test if it started successfully
        if test_ocr_service_local():
            print(f"✅ OCR service started successfully (PID: {process.pid})")
            return True
        else:
            print("❌ OCR service failed to start properly")
            process.terminate()
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install requirements: {e}")
        return False
    except Exception as e:
        print(f"❌ Failed to start OCR service: {e}")
        return False

def test_sds_parsing():
    """Test the complete SDS parsing pipeline"""
    print("\n🧾 Testing SDS Parsing Pipeline")
    print("=" * 40)
    
    test_data = {
        "url": "https://sdshosting.chemalert.com/company/10021710/download/3089176_001_001.pdf",
        "name": "Isocol Rubbing Alcohol"
    }
    
    # Test SDS verification
    try:
        print("🔍 Testing SDS verification...")
        response = requests.post(
            "http://localhost:5001/verify-sds",
            json=test_data,
            timeout=60
        )
        
        print(f"✅ Verification Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"📄 Verification Results:")
            print(f"   - Verified: {result.get('verified')}")
            print(f"   - Text Length: {result.get('text_length')}")
            print(f"   - Keyword Matches: {result.get('keyword_matches')}")
            print(f"   - Used OCR: {result.get('used_ocr')}")
            print(f"   - Image Only PDF: {result.get('image_only_pdf')}")
            
            if result.get('verified'):
                print("✅ SDS verification passed!")
            else:
                print("⚠️ SDS verification failed - check PDF content")
                
        else:
            print(f"❌ Verification failed: {response.text}")
            
    except Exception as e:
        print(f"❌ SDS verification error: {e}")
    
    # Test SDS parsing
    try:
        print("\n📝 Testing SDS parsing...")
        parse_data = {
            "product_id": 999,
            "pdf_url": test_data["url"]
        }
        
        response = requests.post(
            "http://localhost:5001/parse-sds",
            json=parse_data,
            timeout=120
        )
        
        print(f"✅ Parsing Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"📊 Parsing Results:")
            print(f"   - Product ID: {result.get('product_id')}")
            print(f"   - Vendor: {result.get('vendor')}")
            print(f"   - Issue Date: {result.get('issue_date')}")
            print(f"   - Hazardous Substance: {result.get('hazardous_substance')}")
            print(f"   - Dangerous Good: {result.get('dangerous_good')}")
            print(f"   - OCR Available: {result.get('ocr_available')}")
            
        else:
            print(f"❌ Parsing failed: {response.text}")
            
    except Exception as e:
        print(f"❌ SDS parsing error: {e}")

def test_backend_connection():
    """Test if backend can connect to OCR service"""
    print("\n🔗 Testing Backend Connection")
    print("=" * 40)
    
    # Check if backend is running
    try:
        response = requests.get("http://localhost:3001/health", timeout=5)
        print(f"✅ Backend Health: {response.status_code}")
        
        if response.status_code == 200:
            # Test a scan request that should trigger SDS parsing
            scan_data = {"code": "93549004"}  # Isocol product from logs
            
            print("🔍 Testing scan with SDS trigger...")
            scan_response = requests.post(
                "http://localhost:3001/scan",
                json=scan_data,
                timeout=30
            )
            
            print(f"📱 Scan Status: {scan_response.status_code}")
            if scan_response.status_code == 200:
                result = scan_response.json()
                print(f"🎯 Scan successful for: {result.get('product', {}).get('name')}")
            else:
                print(f"❌ Scan failed: {scan_response.text[:200]}")
        
    except requests.exceptions.ConnectionError:
        print("❌ Backend not running on localhost:3001")
        print("💡 Start backend with: npm run dev")
    except Exception as e:
        print(f"❌ Backend connection error: {e}")

def main():
    """Main test function"""
    print("🚀 ChemFetch Local Development Test")
    print("=" * 50)
    print("This script tests your OCR service and SDS parsing locally")
    print("before deploying to Render.\n")
    
    # Check if we're in the right directory
    if not Path("ocr_service").exists():
        print("❌ Error: ocr_service directory not found")
        print("💡 Please run this script from chemfetch-backend-live directory")
        sys.exit(1)
    
    # Test if OCR service is already running
    ocr_running = test_ocr_service_local()
    
    if not ocr_running:
        print("\n🚀 OCR service not running, attempting to start...")
        if not start_ocr_service():
            print("❌ Failed to start OCR service")
            sys.exit(1)
    
    # Test SDS parsing functionality
    test_sds_parsing()
    
    # Test backend integration
    test_backend_connection()
    
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    print("✅ If all tests passed, your setup is working!")
    print("🚀 Ready to deploy to Render with:")
    print("   1. Updated render.yaml configuration")
    print("   2. Optimized requirements.txt for 512MB limit")
    print("   3. Enhanced error handling and logging")
    print("\n💡 Next steps:")
    print("   1. Commit and push your changes")
    print("   2. Deploy to Render")
    print("   3. Check Render logs for startup success")
    print("   4. Test production endpoints")

if __name__ == "__main__":
    main()
