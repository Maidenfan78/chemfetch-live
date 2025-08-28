# OCR Service Connection Fix

## Problem Identified:
Your backend was trying to connect to `https://chemfetch-ocr.onrender.com` but your actual OCR service is at `chemfetch-ocr:5001`.

## Root Cause:
- Render.yaml had mismatched service names (`chemfetch-ocr-lightweight` vs `chemfetch-ocr`)
- Missing port specification in service URLs
- Backend was using external URLs instead of internal service networking

## Fixes Applied:

### 1. Updated render.yaml Service Names:
- Changed `chemfetch-ocr-lightweight` → `chemfetch-ocr`
- This matches your actual service name

### 2. Fixed OCR Service URLs:
- `EXPO_PUBLIC_OCR_API_URL`: `http://chemfetch-ocr:5001`
- `OCR_SERVICE_URL`: `http://chemfetch-ocr:5001`

### 3. Changed from Dynamic Service Discovery to Static URLs:
- Before: Used `fromService` property (which was returning external URLs)
- After: Direct internal service URLs with proper port

## Expected Results After Deployment:

1. **OCR Health Checks Pass**: Backend will successfully connect to OCR service
2. **SDS Parsing Works**: Auto-SDS parsing will use OCR instead of fallback mode
3. **No More 404 Errors**: OCR service endpoints will be reachable
4. **No More 504 Timeouts**: `/verify-sds` endpoint will work properly

## Deploy Commands:
```bash
cd chemfetch-backend-live
git add render.yaml
git commit -m "Fix OCR service connection - use internal service networking"
git push origin main
```

## Verification:
After deployment, check logs for:
- `Auto-SDS: OCR service healthy, proceeding with parsing`
- No more `OCR service not found` errors
- Successful SDS metadata parsing instead of fallback mode
