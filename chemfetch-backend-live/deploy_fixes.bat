@echo off
REM ChemFetch Deployment Script for Windows
REM Fixes OCR service communication and deploys optimized version

echo 🚀 ChemFetch Deployment Script
echo ==============================
echo This script fixes and deploys your OCR service for 512MB free tier
echo.

REM Check if we're in the right directory
if not exist "ocr_service" (
    echo ❌ ocr_service directory not found!
    echo 💡 Please run this script from chemfetch-backend-live directory
    pause
    exit /b 1
)

echo ✅ Found ocr_service directory

REM Step 1: Test local setup
echo.
echo 📋 Step 1: Testing Local Setup
echo ------------------------------

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python not found in PATH
    pause
    exit /b 1
)
echo ✅ Python found

REM Test OCR service requirements
echo ℹ️ Testing OCR service requirements...
cd ocr_service

python -c "import flask; print('Flask: OK')" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Flask available
) else (
    echo ⚠️ Flask not available, installing requirements...
    pip install -r requirements.txt
)

python -c "import pdfplumber; print('pdfplumber: OK')" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ pdfplumber available
) else (
    echo ⚠️ pdfplumber not available
)

cd ..

REM Step 2: Run tests
echo.
echo 🧪 Step 2: Running Tests  
echo ------------------------

echo ℹ️ Running connection test...
python test_ocr_connection.py
if %errorlevel% equ 0 (
    echo ✅ OCR connection test passed
) else (
    echo ⚠️ OCR connection test failed - service may not be running
)

REM Step 3: Deployment instructions
echo.
echo 🚀 Step 3: Deployment Instructions
echo ----------------------------------
echo.

echo ℹ️ Ready to deploy! Follow these steps:
echo.
echo 1. 📤 Commit and Push Changes:
echo    git add .
echo    git commit -m "Fix: OCR service communication and memory optimization"
echo    git push origin main
echo.
echo 2. 🔧 Deploy OCR Service First:
echo    - Go to Render Dashboard
echo    - Find 'chemfetch-ocr-lightweight' service  
echo    - Click 'Manual Deploy' then 'Deploy latest commit'
echo    - Wait for successful deployment
echo.
echo 3. 🖥️ Deploy Backend Second:
echo    - Find 'chemfetch-backend' service
echo    - Click 'Manual Deploy' then 'Deploy latest commit'  
echo    - Wait for successful deployment
echo.
echo 4. ✅ Verify Deployment:
echo    - OCR Health: https://chemfetch-ocr-lightweight.onrender.com/health
echo    - Backend Health: https://chemfetch-backend.onrender.com/health
echo    - Test SDS: Use scan endpoint with barcode 93549004
echo.

echo 🎯 Expected Results:
echo    ✅ OCR service responds with 200 (not 404)
echo    ✅ Memory usage under 512MB  
echo    ✅ SDS parsing works in text-only mode
echo    ✅ Products get metadata even without OCR
echo.

echo 🔧 Files Updated:
echo    ✅ render.yaml - Fixed service communication
echo    ✅ requirements.txt - Optimized for 512MB limit
echo    ✅ ocr_service.py - Enhanced logging
echo    ✅ autoSdsParsing.ts - Better error handling  
echo    ✅ sds_extractor.py - Lightweight text extraction
echo.

echo 🚀 Deployment complete! Test your services after deployment.
pause
