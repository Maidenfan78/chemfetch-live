import os
import tempfile
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Union
from pdfminer.high_level import extract_text
import requests
import logging

# Setup logging for Render - use stdout/stderr only
# Render captures console output automatically
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Console output only - Render captures this
    ]
)
logger = logging.getLogger(__name__)

import cv2
import numpy as np
from flask import Flask, request, jsonify
from paddleocr import PaddleOCR
from PIL import Image

# -----------------------------------------------------------------------------
# Try to import parse_sds_pdf from the local module. Provide a fallback path if
# the service is started from project root.
# -----------------------------------------------------------------------------
try:
    from parse_sds import parse_sds_pdf  # when running inside ocr_service
except Exception:
    try:
        # Fallback if app is executed from project root and ocr_service is a pkg
        from ocr_service.parse_sds import parse_sds_pdf  # type: ignore
    except Exception as e:
        parse_sds_pdf = None  # will be checked before use
        _import_err = e

# Also import the new SDS extractor directly for the HTTP endpoint
try:
    from sds_parser_new.sds_extractor import parse_pdf as parse_pdf_direct
except Exception as e:
    parse_pdf_direct = None
    _direct_import_err = e

# -----------------------------------------------------------------------------
# Environment & global config
# -----------------------------------------------------------------------------
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")
os.environ.setdefault("FLAGS_log_dir", tempfile.gettempdir())

app = Flask(__name__)
# Debug image dumping via env var or ?mode=debug
# Use temporary directory for Render compatibility (read-only filesystem)
DEBUG_IMAGES_ENV = os.getenv("DEBUG_IMAGES", "0") == "1"
DEBUG_DIR = Path(tempfile.gettempdir()) / "debug_images"
DEBUG_DIR.mkdir(exist_ok=True)

# -----------------------------------------------------------------------------
# Cross-platform timeout utility
# -----------------------------------------------------------------------------
class TimeoutError(Exception):
    pass

def run_with_timeout(func, args=(), kwargs=None, timeout=120):
    """Run ``func`` enforcing a timeout without using threads.

    PaddleOCR's predictors are not thread-safe, so running the OCR call in a
    separate thread (as was previously done) could leave the underlying
    predictor in a bad state which manifested as "RuntimeError: Unknown
    exception" on subsequent requests.  To keep the call in the main thread we
    use ``signal.alarm`` on Unix-like systems.  On platforms without
    ``SIGALRM`` (e.g. Windows) we simply execute the function without a
    timeout.  This prioritises reliability of the OCR service over strict
    cross-platform timeouts.
    """

    if kwargs is None:
        kwargs = {}

    if os.name != "nt":  # Unix: use signal-based alarm
        import signal

        def _handler(signum, frame):  # pragma: no cover - simple signal handler
            raise TimeoutError("Function execution timeout")

        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(timeout)
        try:
            return func(*args, **kwargs)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        # Windows (no SIGALRM): run without enforced timeout
        return func(*args, **kwargs)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def box_area(box: List[List[float]] | np.ndarray) -> float:
    pts = np.asarray(box, dtype=np.float32).reshape(-1, 2)
    if pts.shape[0] < 3:
        _, _, w, h = cv2.boundingRect(pts.astype(np.int32))
        return float(w * h)
    return float(cv2.contourArea(pts))


def box_origin(box: List[List[float]] | np.ndarray) -> Tuple[float, float]:
    pts = np.asarray(box, dtype=np.float32).reshape(-1, 2)
    return float(pts[:, 0].min()), float(pts[:, 1].min())


def resize_to_max_side(img: Image.Image, max_side: int) -> Image.Image:
    w, h = img.size
    scale = min(max_side / w, max_side / h, 1.0)
    new_w, new_h = int(w * scale), int(h * scale)
    return img.resize((new_w, new_h))


def pil_to_cv(img: Image.Image) -> np.ndarray:
    arr = np.array(img.convert("RGB"))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def preprocess_array(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

# -----------------------------------------------------------------------------
# Initialize OCR model
# -----------------------------------------------------------------------------
try:
    ocr_model = PaddleOCR(
        lang="en",
        det_model_dir=None,
        rec_model_dir=None,
        use_angle_cls=True,
    )
except Exception as e:
    raise RuntimeError(f"Failed to initialize PaddleOCR: {e}")

# -----------------------------------------------------------------------------
# Health check
# -----------------------------------------------------------------------------
@app.route("/gpu-check")
def gpu_check():
    import paddle

    compiled = getattr(paddle, "is_compiled_with_cuda", lambda: False)()
    try:
        count = paddle.device.cuda.device_count()
    except Exception:
        count = 0
    return jsonify({"cuda_compiled": compiled, "device_count": count})

# -----------------------------------------------------------------------------
# OCR endpoint - DISABLED (product name OCR removed)
# -----------------------------------------------------------------------------
# @app.route('/ocr', methods=['POST'])
# def ocr():
#     # This endpoint has been disabled as product name OCR was unreliable
#     # for cylindrical, shiny products with stylized text
#     return jsonify({'error': 'OCR endpoint disabled'}), 404

# -----------------------------------------------------------------------------
# PDF SDS Verification Endpoint
# -----------------------------------------------------------------------------

def verify_pdf_sds(url: str, product_name: str, keywords=None) -> bool:
    # More comprehensive SDS keyword list with broader terms
    keywords = keywords or [
        # Core SDS Terms (most important)
        "safety data sheet", "sds", "msds", "material safety data sheet",
        "product safety data sheet", "chemical safety data sheet",
        "hazard communication", "ghs",
        
        # Standard SDS Section Headers
        "product identification", "hazard identification", "composition",
        "first aid measures", "fire fighting measures", "accidental release",
        "handling and storage", "exposure controls", "physical and chemical properties",
        "stability and reactivity", "toxicological information", "ecological information",
        "disposal considerations", "transport information", "regulatory information",
        
        # Format Indicators
        "un number", "cas number", "dangerous goods", "hazard class",
        "packing group", "signal word", "hazard statement", "precautionary statement",
        
        # Section numbering (SDS documents have numbered sections 1-16)
        "section 1", "section 2", "section 3", "section 4", "section 5",
        
        # Additional common SDS terms
        "emergency contact", "manufacturer", "supplier", "emergency phone",
        "revision date", "preparation date", "issue date", "version",
        "flammable", "corrosive", "toxic", "irritant", "oxidizing",
        "exposure limit", "threshold limit", "workplace exposure",
        "personal protective equipment", "ppe", "respiratory protection",
        "eye protection", "skin protection", "hand protection",
        
        # Australian specific terms
        "australian dangerous goods", "adg", "workplace health and safety",
        "whs", "safe work australia", "nohsc", "acgih", "aioh"
    ]
    
    try:
        # Use streaming and size limits to prevent massive downloads
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Check content-type header first
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type:
            print(f"[verify_pdf_sds] Not a PDF: {content_type}")
            return False
        
        # Limit download size to 50MB max
        max_size = 50 * 1024 * 1024  # 50MB
        content = BytesIO()
        size = 0
        
        print(f"[verify_pdf_sds] Starting PDF download with {max_size // (1024*1024)}MB limit...")
        
        for chunk in response.iter_content(chunk_size=8192):
            size += len(chunk)
            if size > max_size:
                print(f"[verify_pdf_sds] PDF too large: {size} bytes")
                return False
            content.write(chunk)
            
            # Log progress every 5MB
            if size % (5 * 1024 * 1024) == 0:
                print(f"[verify_pdf_sds] Downloaded {size // (1024*1024)}MB...")
        
        print(f"[verify_pdf_sds] Download complete: {size} bytes")
        content.seek(0)
        
        # Extract text with timeout protection - check more pages for better coverage
        print(f"[verify_pdf_sds] Extracting text from PDF (max 10 pages)...")
        text = extract_text(content, maxpages=10).lower()  # Increased from 5 to 10 pages
        print(f"[verify_pdf_sds] Extracted {len(text)} characters of text")
        
        # Score-based keyword matching - no product name requirement
        print(f"[verify_pdf_sds] Checking for SDS keywords in extracted text...")
        keyword_matches = sum(1 for kw in keywords if kw.lower() in text)
        
        print(f"[verify_pdf_sds] Found keyword matches: {keyword_matches}/{len(keywords)}")
        
        # Log some of the matched keywords for debugging
        matched_keywords = [kw for kw in keywords if kw.lower() in text]
        print(f"[verify_pdf_sds] Matched keywords: {matched_keywords[:10]}...")  # Show first 10
        
        # More lenient threshold - require only 1 keyword match for SDS documents
        # Many legitimate SDS documents might not have all standard keywords
        is_valid_sds = keyword_matches >= 1
        
        # Additional check: if the filename contains SDS/MSDS terms, be even more lenient
        filename_has_sds = any(term in url.lower() for term in ['sds', 'msds', 'safety', 'data', 'sheet'])
        if filename_has_sds and keyword_matches >= 1:
            is_valid_sds = True
            print(f"[verify_pdf_sds] Filename indicates SDS document: {url}")
        
        print(f"[verify_pdf_sds] URL: {url[:100]}... Keyword matches: {keyword_matches}//{len(keywords)} - Valid SDS: {is_valid_sds}")
        return is_valid_sds
        
    except Exception as e:
        print(f"[verify_pdf_sds] Failed to verify {url}: {type(e).__name__}: {e}")
        import traceback
        print(f"[verify_pdf_sds] Verification traceback: {traceback.format_exc()}")
        return False


@app.route('/verify-sds', methods=['POST'])
def verify_sds():
    data = request.json or {}
    url = data.get('url', '')
    name = data.get('name', '')
    
    print(f"[verify-sds] Endpoint called with URL: {url}")
    print(f"[verify-sds] Product name: {name}")
    
    if not url or not name:
        print(f"[verify-sds] Missing required parameters: url={bool(url)}, name={bool(name)}")
        return jsonify({'error': 'Missing url or name'}), 400

    try:
        print(f"[verify-sds] Starting verification with 120s timeout...")
        # Use cross-platform timeout protection
        verified = run_with_timeout(verify_pdf_sds, args=(url, name), timeout=120)
        print(f"[verify-sds] Verification complete: {verified}")
        return jsonify({'verified': verified}), 200
        
    except TimeoutError:
        print(f"[verify-sds] Verification timeout after 120s")
        return jsonify({'error': 'Verification timeout - PDF too large or slow to process'}), 408
    except Exception as e:
        print(f"[verify-sds] Verification exception: {type(e).__name__}: {e}")
        import traceback
        print(f"[verify-sds] Exception traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Verification failed: {str(e)}'}), 500

# -----------------------------------------------------------------------------
# NEW: Parse SDS over HTTP (reuses parse_sds.parse_sds_pdf)
# -----------------------------------------------------------------------------
# -------------------------------------------------------------------------
# NEW: Parse SDS over HTTP (reuses parse_sds.parse_sds_pdf)
# -------------------------------------------------------------------------
@app.route('/parse-sds', methods=['POST'])
def parse_sds_http():
    """
    Body: { "product_id": 123, "pdf_url": "https://..." }
    Returns: Parsed fields suitable for upsert into sds_metadata.
    """
    print(f"[parse-sds] HTTP endpoint called")
    
    if parse_sds_pdf is None:
        # Avoid syntax errors by building string normally
        err_msg = f"parse_sds_pdf could not be imported: {_import_err}" if '_import_err' in globals() else "Unknown import error"
        print(f"[parse-sds] Import error: {err_msg}")
        return jsonify({"error": err_msg}), 500

    data = request.json or {}
    product_id = data.get("product_id")
    pdf_url = data.get("pdf_url")
    
    print(f"[parse-sds] Product ID: {product_id}")
    print(f"[parse-sds] PDF URL: {pdf_url}")

    if not product_id or not pdf_url:
        print(f"[parse-sds] Missing required parameters: product_id={bool(product_id)}, pdf_url={bool(pdf_url)}")
        return jsonify({"error": "Missing product_id or pdf_url"}), 400

    try:
        print(f"[parse-sds] Starting SDS parsing...")
        parsed = parse_sds_pdf(pdf_url, product_id=int(product_id))
        print(f"[parse-sds] Parsing complete")

        def _get(attr, default=None):
            if hasattr(parsed, attr):
                return getattr(parsed, attr)
            if isinstance(parsed, dict):
                return parsed.get(attr, default)
            return default

        return jsonify({
            "product_id": _get("product_id", int(product_id)),
            "vendor": _get("vendor"),
            "issue_date": _get("issue_date"),
            "hazardous_substance": _get("hazardous_substance"),
            "dangerous_good": _get("dangerous_good"),
            "dangerous_goods_class": _get("dangerous_goods_class"),
            "packing_group": _get("packing_group"),
            "subsidiary_risks": _get("subsidiary_risks"),
            "hazard_statements": _get("hazard_statements", []),
            "raw_json": _get("raw_json"),
        }), 200

    except Exception as e:
        print(f"[parse-sds] Parsing failed: {type(e).__name__}: {e}")
        import traceback
        print(f"[parse-sds] Exception traceback: {traceback.format_exc()}")
        return jsonify({"error": f"parse_sds failed: {e}"}), 500


# -----------------------------------------------------------------------------
# NEW: Direct PDF Parsing Endpoint (using improved parser)
# -----------------------------------------------------------------------------
@app.route('/parse-pdf-direct', methods=['POST'])
def parse_pdf_direct_http():
    """
    Parse PDF directly using the improved parser.
    Body: { "pdf_url": "https://...", "product_id": 123 }
    Returns: Raw parsed fields from the improved parser.
    """
    if parse_pdf_direct is None:
        err_msg = f"parse_pdf_direct could not be imported: {_direct_import_err}" if '_direct_import_err' in globals() else "Direct parser not available"
        return jsonify({"error": err_msg}), 500

    data = request.json or {}
    pdf_url = data.get("pdf_url")
    product_id = data.get("product_id")

    if not pdf_url:
        return jsonify({"error": "Missing pdf_url"}), 400

    try:
        # Download PDF to temporary file
        import tempfile
        import os
        from pathlib import Path
        
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            
            tmp_path = Path(tmp_file.name)
        
        try:
            # Parse using the new parser
            parsed_result = parse_pdf_direct(tmp_path)
            
            # Clean up temporary file
            os.unlink(tmp_path)
            
            return jsonify({
                "success": True,
                "product_id": product_id,
                "parsed_data": parsed_result
            }), 200
            
        except Exception as parse_error:
            # Clean up temporary file on error
            if tmp_path.exists():
                os.unlink(tmp_path)
            raise parse_error
            
    except Exception as e:
        return jsonify({"error": f"PDF parsing failed: {e}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)