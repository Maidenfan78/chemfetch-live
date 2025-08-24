#!/usr/bin/env python3

"""
Quick test script for the ultra-lightweight OCR service
Tests the deployment to ensure everything is working correctly
"""

import sys
import os

print("🧪 Testing ChemFetch Ultra-Lightweight OCR Service...")
print("=" * 60)

# Test 1: Basic import test
print("\n1️⃣  Testing imports...")
try:
    # Add the ocr_service directory to Python path
    sys.path.insert(0, os.path.join(os.getcwd(), 'ocr_service'))
    
    # Test basic imports
    import flask
    print("✅ Flask imported successfully")
    
    import PyMuPDF as fitz
    print("✅ PyMuPDF imported successfully")
    
    import pdfminer.high_level
    print("✅ pdfminer imported successfully")
    
    import numpy
    print("✅ NumPy imported successfully")
    
    import requests
    print("✅ Requests imported successfully")
    
    # Test OCR service import
    import ocr_service
    print("✅ OCR service imported successfully")
    
    print("\n🎉 All imports successful!")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Check OCR availability detection
print("\n2️⃣  Testing OCR availability detection...")
try:
    if hasattr(ocr_service, 'OCR_AVAILABLE'):
        ocr_available = ocr_service.OCR_AVAILABLE
        print(f"✅ OCR_AVAILABLE = {ocr_available}")
        
        if not ocr_available:
            print("✅ Correctly detected lightweight mode (OCR not available)")
        else:
            print("ℹ️  OCR dependencies are available")
    else:
        print("❌ OCR_AVAILABLE not found")
        
except Exception as e:
    print(f"❌ OCR availability test failed: {e}")

# Test 3: Check Flask app creation
print("\n3️⃣  Testing Flask app...")
try:
    if hasattr(ocr_service, 'app'):
        app = ocr_service.app
        print("✅ Flask app created successfully")
        
        # Test health endpoint exists
        with app.test_client() as client:
            response = client.get('/health')
            if response.status_code == 200:
                import json
                health_data = json.loads(response.data)
                print("✅ Health endpoint working")
                print(f"   Status: {health_data.get('status')}")
                print(f"   OCR Available: {health_data.get('ocr_available')}")
                print(f"   Memory Mode: {health_data.get('memory_mode')}")
            else:
                print(f"❌ Health endpoint returned {response.status_code}")
    else:
        print("❌ Flask app not found")
        
except Exception as e:
    print(f"❌ Flask app test failed: {e}")

# Test 4: Memory usage estimation
print("\n4️⃣  Estimating memory usage...")
try:
    import psutil
    import os
    
    # Get current process memory
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"✅ Current process memory: {memory_mb:.1f} MB")
    
    if memory_mb < 200:
        print("🎉 Excellent! Well under 200MB limit")
    elif memory_mb < 300:
        print("✅ Good! Under 300MB limit")
    else:
        print("⚠️  Memory usage higher than expected")
        
except ImportError:
    print("ℹ️  psutil not available, skipping memory test")
except Exception as e:
    print(f"⚠️  Memory test failed: {e}")

# Test 5: Environment variables
print("\n5️⃣  Testing environment variables...")
try:
    ocr_mode = os.getenv('OCR_MODE', 'auto')
    print(f"✅ OCR_MODE = {ocr_mode}")
    
    if ocr_mode == 'text-only':
        print("✅ Correctly configured for ultra-lightweight mode")
    
except Exception as e:
    print(f"❌ Environment test failed: {e}")

print("\n" + "=" * 60)
print("🎉 Ultra-Lightweight OCR Service Test Complete!")
print("\nNext steps:")
print("• Start the service: python ocr_service/ocr_service.py")
print("• Test health endpoint: curl http://localhost:5001/health")
print("• Deploy to Render with the updated configuration")
print("• Monitor memory usage should be ~100-150MB")
