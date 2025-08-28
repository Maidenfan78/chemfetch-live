#!/usr/bin/env python3
"""
OCR Service Connection Test Script
Tests connectivity to OCR service and verifies SDS parsing functionality
"""
import requests
import os
import json
import sys
from datetime import datetime

def test_ocr_service():
    """Test OCR service connectivity and functionality"""
    # Test URLs in order of preference
    test_urls = [
        "https://chemfetch-ocr-lightweight.onrender.com",
        "https://chemfetch-ocr.onrender.com", 
        "http://localhost:5001",
        "http://127.0.0.1:5001"
    ]
    
    print(f"🧪 OCR Service Connection Test - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    working_urls = []
    
    for url in test_urls:
        try:
            print(f"\n🔍 Testing OCR service at: {url}")
            
            # Test health endpoint
            health_response = requests.get(f"{url}/health", timeout=10)
            print(f"✅ Health check: {health_response.status_code}")
            
            if health_response.status_code == 200:
                health_data = health_response.json()
                print(f"📊 Service info:")
                print(f"   - Status: {health_data.get('status')}")
                print(f"   - OCR Available: {health_data.get('ocr_available')}")
                print(f"   - OCR Mode: {health_data.get('ocr_mode')}")
                print(f"   - PDF Extractor: {health_data.get('pdf_extractor')}")
                print(f"   - Memory Mode: {health_data.get('memory_mode')}")
                
                # Test SDS verification if health passes
                print(f"🧾 Testing SDS verification...")
                verify_data = {
                    "url": "https://sdshosting.chemalert.com/company/10021710/download/3089176_001_001.pdf",
                    "name": "Isocol Rubbing Alcohol"
                }
                
                try:
                    verify_response = requests.post(
                        f"{url}/verify-sds", 
                        json=verify_data, 
                        timeout=60  # Give more time for PDF processing
                    )
                    print(f"✅ SDS Verify: {verify_response.status_code}")
                    
                    if verify_response.status_code == 200:
                        verify_result = verify_response.json()
                        print(f"📄 Verification results:")
                        print(f"   - Verified: {verify_result.get('verified')}")
                        print(f"   - Used OCR: {verify_result.get('used_ocr')}")
                        print(f"   - Text Length: {verify_result.get('text_length')}")
                        print(f"   - Keyword Matches: {verify_result.get('keyword_matches')}")
                        if verify_result.get('error'):
                            print(f"   - Error: {verify_result.get('error')}")
                    else:
                        print(f"❌ Verify error: {verify_response.text[:200]}")
                        
                except requests.exceptions.Timeout:
                    print(f"⏰ SDS verification timed out (service may be slow)")
                except Exception as verify_error:
                    print(f"❌ SDS verification failed: {verify_error}")
                
                working_urls.append(url)
                
            else:
                print(f"❌ Health check failed: {health_response.text[:100]}")
                
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection refused - service not running at {url}")
        except requests.exceptions.Timeout:
            print(f"⏰ Connection timeout - service too slow at {url}")
        except Exception as e:
            print(f"❌ Failed to connect to {url}: {e}")
            continue
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    
    if working_urls:
        print(f"✅ Found {len(working_urls)} working OCR service(s):")
        for url in working_urls:
            print(f"   - {url}")
        
        primary_url = working_urls[0]
        print(f"\n🎯 PRIMARY SERVICE: {primary_url}")
        print(f"💡 Set this in your environment:")
        print(f"   export EXPO_PUBLIC_OCR_API_URL='{primary_url}'")
        print(f"   export OCR_SERVICE_URL='{primary_url}'")
        
        return primary_url
    else:
        print("🚨 NO WORKING OCR SERVICES FOUND!")
        print("\n🔧 Troubleshooting steps:")
        print("1. Check if OCR service is deployed on Render")
        print("2. Verify service name matches render.yaml configuration")
        print("3. Check Render service logs for startup errors")
        print("4. Try starting OCR service locally:")
        print("   cd ocr_service && python ocr_service.py")
        
        return None

def test_backend_integration():
    """Test if backend can reach OCR service"""
    backend_urls = [
        "https://chemfetch-backend.onrender.com",
        "http://localhost:3001"
    ]
    
    print(f"\n🔗 Testing Backend Integration")
    print("=" * 40)
    
    for backend_url in backend_urls:
        try:
            print(f"🧪 Testing backend at: {backend_url}")
            
            # Test health endpoint
            health_response = requests.get(f"{backend_url}/health", timeout=10)
            if health_response.status_code == 200:
                print(f"✅ Backend health: OK")
                
                # Test SDS trigger endpoint
                trigger_data = {"product_id": 1}
                trigger_response = requests.post(
                    f"{backend_url}/sds-trigger",
                    json=trigger_data,
                    timeout=10
                )
                print(f"🔄 SDS trigger test: {trigger_response.status_code}")
                
            else:
                print(f"❌ Backend not healthy: {health_response.status_code}")
                
        except Exception as e:
            print(f"❌ Backend connection failed: {e}")

if __name__ == "__main__":
    print("🚀 ChemFetch OCR Service Diagnostic Tool")
    print("This tool tests connectivity to your OCR service and verifies functionality\n")
    
    # Test OCR service connectivity
    working_url = test_ocr_service()
    
    # Test backend integration if requested
    if len(sys.argv) > 1 and sys.argv[1] == "--backend":
        test_backend_integration()
    
    # Exit with appropriate code
    sys.exit(0 if working_url else 1)
