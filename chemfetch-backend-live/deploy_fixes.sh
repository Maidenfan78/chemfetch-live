#!/bin/bash
# ChemFetch Deployment Script
# Fixes OCR service communication and deploys optimized version

echo "🚀 ChemFetch Deployment Script"
echo "=============================="
echo "This script fixes and deploys your OCR service for 512MB free tier"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

# Check if we're in the right directory
if [ ! -d "ocr_service" ]; then
    print_error "ocr_service directory not found!"
    print_info "Please run this script from chemfetch-backend-live directory"
    exit 1
fi

print_info "Found ocr_service directory"

# Step 1: Test local setup
echo ""
echo "📋 Step 1: Testing Local Setup"
echo "------------------------------"

if command -v python &> /dev/null; then
    print_status "Python found: $(python --version)"
else
    print_error "Python not found in PATH"
    exit 1
fi

# Test OCR service requirements
print_info "Testing OCR service requirements..."
cd ocr_service

if python -c "import flask; print(f'Flask: {flask.__version__}')" 2>/dev/null; then
    print_status "Flask available"
else
    print_warning "Flask not available, installing requirements..."
    pip install -r requirements.txt
fi

if python -c "import pdfplumber; print('pdfplumber: OK')" 2>/dev/null; then
    print_status "pdfplumber available"
else
    print_warning "pdfplumber not available"
fi

# Test OCR service startup
print_info "Testing OCR service startup..."
timeout 10 python -c "
import sys
sys.path.append('.')
from ocr_service import app
print('OCR service imports working')
" 2>/dev/null

if [ $? -eq 0 ]; then
    print_status "OCR service imports working"
else
    print_error "OCR service import test failed"
fi

cd ..

# Step 2: Run comprehensive tests
echo ""
echo "🧪 Step 2: Running Tests"
echo "------------------------"

print_info "Running connection test..."
if python test_ocr_connection.py; then
    print_status "OCR connection test passed"
else
    print_warning "OCR connection test failed (service may not be running)"
fi

# Step 3: Check Git status
echo ""
echo "📝 Step 3: Git Status"
echo "--------------------"

if git status --porcelain | grep -q .; then
    print_info "Found uncommitted changes:"
    git status --short
    
    echo ""
    read -p "Do you want to commit these changes? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Committing changes..."
        git add .
        git commit -m "Fix: OCR service communication and memory optimization for 512MB limit

- Fixed OCR service URL configuration in render.yaml
- Optimized requirements.txt for 512MB memory limit  
- Enhanced error handling and logging
- Added fallback text extraction methods
- Improved debugging and health checks"
        print_status "Changes committed"
    else
        print_warning "Skipping commit - you can commit manually later"
    fi
else
    print_status "No uncommitted changes found"
fi

# Step 4: Deployment instructions
echo ""
echo "🚀 Step 4: Deployment Instructions"
echo "---------------------------------- "

echo ""
print_info "Ready to deploy! Follow these steps:"
echo ""

echo "1. 📤 Push to Git (if you committed changes):"
echo "   git push origin main"
echo ""

echo "2. 🔧 Deploy OCR Service First:"
echo "   - Go to Render Dashboard"
echo "   - Find 'chemfetch-ocr-lightweight' service"
echo "   - Click 'Manual Deploy' > 'Deploy latest commit'"
echo "   - Wait for successful deployment"
echo ""

echo "3. 🖥️  Deploy Backend Second:"
echo "   - Find 'chemfetch-backend' service"
echo "   - Click 'Manual Deploy' > 'Deploy latest commit'"
echo "   - Wait for successful deployment"
echo ""

echo "4. ✅ Verify Deployment:"
echo "   - Test OCR health: curl https://chemfetch-ocr-lightweight.onrender.com/health"
echo "   - Test backend: curl https://chemfetch-backend.onrender.com/health"
echo "   - Test SDS parsing: Use scan endpoint with barcode 93549004"
echo ""

print_info "Expected results after deployment:"
echo "   ✅ OCR service responds with 200 (not 404)"
echo "   ✅ Memory usage under 512MB"
echo "   ✅ SDS parsing works in text-only mode"
echo "   ✅ Products get metadata (even without OCR)"
echo ""

echo "🎯 Troubleshooting:"
echo "   - If OCR still returns 404: Check service name in Render dashboard"
echo "   - If memory issues: Service will restart automatically"  
echo "   - If parsing fails: Check logs for specific PDF issues"
echo ""

print_status "Deployment script complete!"
print_info "Run 'python test_ocr_connection.py' after deployment to verify"
