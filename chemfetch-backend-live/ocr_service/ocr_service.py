import os
import tempfile
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Union
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

# Multiple PDF extraction options for better compatibility
PDF_EXTRACTOR = None
try:
    import PyMuPDF as fitz
    from pdfminer.high_level import extract_text
    PDF_EXTRACTOR = "pymupdf"
    logger.info("Using PyMuPDF for PDF text extraction")
except ImportError:
    try:
        import pdfplumber
        from pdfminer.high_level import extract_text
        PDF_EXTRACTOR = "pdfplumber"
        logger.info("Using pdfplumber for PDF text extraction (PyMuPDF not available)")
    except ImportError:
        from pdfminer.high_level import extract_text
        PDF_EXTRACTOR = "pdfminer"
        logger.info("Using pdfminer.six only for PDF text extraction")

import numpy as np
from flask import Flask, request, jsonify

# Optional OCR imports - graceful fallback if not available
OCR_AVAILABLE = False
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    import cv2
    OCR_AVAILABLE = True
    logger.info("OCR dependencies available - full functionality enabled")
except ImportError as e:
    logger.warning(f"OCR dependencies not available: {e}. Running in text-only mode.")
    # Create dummy classes to prevent import errors
    class Image:
        pass
    
    def convert_from_path(*args, **kwargs):
        raise RuntimeError("OCR not available in lightweight mode")

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
app = Flask(__name__)
# Debug image dumping via env var or ?mode=debug
# Use temporary directory for Render compatibility (read-only filesystem)
DEBUG_IMAGES_ENV = os.getenv("DEBUG_IMAGES", "0") == "1"
DEBUG_DIR = Path(tempfile.gettempdir()) / "debug_images"
DEBUG_DIR.mkdir(exist_ok=True)

# OCR mode detection
OCR_MODE = os.getenv("OCR_MODE", "auto").lower()  # auto, text-only, full

# -----------------------------------------------------------------------------
# Cross-platform timeout utility
# -----------------------------------------------------------------------------
class TimeoutError(Exception):
    pass

def run_with_timeout(func, args=(), kwargs=None, timeout=120):
    """Run ``func`` enforcing a timeout without using threads.

    To keep the call in the main thread we use ``signal.alarm`` on Unix-like 
    systems. On platforms without ``SIGALRM`` (e.g. Windows) we simply execute 
    the function without a timeout.
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
# Lightweight OCR helper functions (only used when OCR_AVAILABLE)
# -----------------------------------------------------------------------------
def extract_text_from_pdf_with_ocr(pdf_path: Path, max_pages: int = 10) -> Tuple[str, bool]:
    """
    Extract text from PDF using multiple extraction methods and OCR fallback.
    Returns (text, used_ocr)
    """
    if not OCR_AVAILABLE:
        # Text-only fallback with multiple PDF library support
        return extract_text_from_pdf_multiple_methods(pdf_path, max_pages)
        
    # Full OCR mode available - try text first, then OCR
    text, image_only = extract_text_from_pdf_multiple_methods(pdf_path, max_pages)
    
    if not image_only:
        return text, False  # Text extraction successful
        
    # Fallback to OCR for image-only PDFs
    try:
        logger.info("Low text content, attempting OCR...")
        pages = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=min(max_pages, 10))
        
        ocr_text = ""
        for i, page in enumerate(pages):
            try:
                page_text = pytesseract.image_to_string(page, config='--psm 1')
                ocr_text += f"\n--- Page {i+1} ---\n{page_text}"
            except Exception as e:
                logger.warning(f"OCR failed for page {i+1}: {e}")
                continue
        
        logger.info(f"Extracted {len(ocr_text)} characters using OCR")
        return ocr_text, True
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}")
        return text, True  # Return original text even if OCR failed
        

def extract_text_from_pdf_multiple_methods(pdf_path: Path, max_pages: int = 10) -> Tuple[str, bool]:
    """
    Extract text from PDF using multiple methods for maximum compatibility.
    Returns (text, is_image_only_pdf)
    """
    text = ""
    
    # Method 1: Try PyMuPDF (fastest and most reliable)
    if PDF_EXTRACTOR == "pymupdf":
        try:
            import PyMuPDF as fitz
            doc = fitz.open(pdf_path)
            for page_num in range(min(len(doc), max_pages)):
                page = doc[page_num]
                text += page.get_text()
            doc.close()
            
            if len(text.strip()) >= 50:
                logger.info(f"Extracted {len(text)} characters using PyMuPDF")
                return text, False
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
    
    # Method 2: Try pdfplumber (good for tables and complex layouts)
    if PDF_EXTRACTOR == "pdfplumber" or (not text.strip() and 'pdfplumber' in globals()):
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page_num in range(min(len(pdf.pages), max_pages)):
                    page = pdf.pages[page_num]
                    page_text = page.extract_text() or ""
                    text += page_text
            
            if len(text.strip()) >= 50:
                logger.info(f"Extracted {len(text)} characters using pdfplumber")
                return text, False
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
    
    # Method 3: Fallback to pdfminer.six (always available)
    try:
        with open(pdf_path, 'rb') as f:
            text = extract_text(f, maxpages=max_pages)
        
        if len(text.strip()) >= 50:
            logger.info(f"Extracted {len(text)} characters using pdfminer.six")
            return text, False
        else:
            logger.info(f"Low text content detected ({len(text.strip())} chars) - likely image-only PDF")
            return text, True  # Flag as image-only PDF
            
    except Exception as e:
        logger.error(f"All PDF text extraction methods failed: {e}")
        return "", True



# -----------------------------------------------------------------------------
# Health check with OCR capability reporting
# -----------------------------------------------------------------------------
@app.route("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "ocr_available": OCR_AVAILABLE,
        "ocr_mode": OCR_MODE,
        "memory_mode": "lightweight" if not OCR_AVAILABLE else "full",
        "pdf_extractor": PDF_EXTRACTOR
    })

@app.route("/gpu-check")
def gpu_check():
    """Legacy endpoint - OCR mode doesn't use GPU"""
    return jsonify({
        "cuda_compiled": False,
        "device_count": 0,
        "note": "Running in CPU-only mode without PaddleOCR"
    })

# -----------------------------------------------------------------------------
# PDF SDS Verification Endpoint - Enhanced with OCR awareness
# -----------------------------------------------------------------------------
def verify_pdf_sds(url: str, product_name: str, keywords=None) -> Dict[str, Any]:
    """
    Enhanced verification that returns detailed results including OCR status.
    Returns: {
        "verified": bool,
        "used_ocr": bool,
        "image_only_pdf": bool,
        "text_length": int,
        "keyword_matches": int
    }
    """
    # More comprehensive SDS keyword list
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
        
        # Australian specific terms
        "australian dangerous goods", "adg", "workplace health and safety",
        "whs", "safe work australia", "nohsc", "acgih", "aioh"
    ]
    
    try:
        # Download PDF with size limits
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Check content-type header first
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type:
            logger.info(f"Not a PDF: {content_type}")
            return {
                "verified": False,
                "error": "Not a PDF file",
                "used_ocr": False,
                "image_only_pdf": False,
                "text_length": 0,
                "keyword_matches": 0
            }
        
        # Limit download size to 50MB max
        max_size = 50 * 1024 * 1024  # 50MB
        
        # Download to temporary file for OCR processing if needed
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            size = 0
            logger.info(f"Starting PDF download with {max_size // (1024*1024)}MB limit...")
            
            for chunk in response.iter_content(chunk_size=8192):
                size += len(chunk)
                if size > max_size:
                    logger.warning(f"PDF too large: {size} bytes")
                    os.unlink(tmp_file.name)
                    return {
                        "verified": False,
                        "error": "PDF file too large",
                        "used_ocr": False,
                        "image_only_pdf": False,
                        "text_length": 0,
                        "keyword_matches": 0
                    }
                tmp_file.write(chunk)
            
            tmp_path = Path(tmp_file.name)
        
        try:
            # Extract text with OCR fallback
            logger.info(f"Extracting text from PDF...")
            text, used_ocr = extract_text_from_pdf_with_ocr(tmp_path, max_pages=10)
            text_lower = text.lower()
            
            logger.info(f"Extracted {len(text)} characters (OCR: {used_ocr})")
            
            # Check for keywords
            keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            matched_keywords = [kw for kw in keywords if kw.lower() in text_lower]
            
            logger.info(f"Found {keyword_matches}/{len(keywords)} keyword matches")
            logger.debug(f"Matched keywords: {matched_keywords[:5]}...")
            
            # Enhanced validation logic
            is_valid_sds = keyword_matches >= 1
            
            # Boost score for filename indicators
            filename_has_sds = any(term in url.lower() for term in ['sds', 'msds', 'safety', 'data', 'sheet'])
            if filename_has_sds and keyword_matches >= 1:
                is_valid_sds = True
            
            # Flag image-only PDFs that couldn't be processed
            image_only_pdf = (len(text.strip()) < 50) and (not OCR_AVAILABLE or used_ocr)
            
            result = {
                "verified": is_valid_sds,
                "used_ocr": used_ocr,
                "image_only_pdf": image_only_pdf,
                "text_length": len(text),
                "keyword_matches": keyword_matches,
                "ocr_available": OCR_AVAILABLE
            }
            
            if image_only_pdf:
                result["warning"] = "Image-only PDF detected but OCR not available"
            
            return result
            
        finally:
            # Clean up temporary file
            if tmp_path.exists():
                os.unlink(tmp_path)
        
    except Exception as e:
        logger.error(f"Failed to verify {url}: {type(e).__name__}: {e}")
        import traceback
        logger.debug(f"Verification traceback: {traceback.format_exc()}")
        return {
            "verified": False,
            "error": str(e),
            "used_ocr": False,
            "image_only_pdf": False,
            "text_length": 0,
            "keyword_matches": 0
        }


@app.route('/verify-sds', methods=['POST'])
def verify_sds():
    data = request.json or {}
    url = data.get('url', '')
    name = data.get('name', '')
    
    logger.info(f"SDS verification requested - URL: {url[:100]}...")
    logger.info(f"Product name: {name}")
    
    if not url or not name:
        logger.warning(f"Missing required parameters: url={bool(url)}, name={bool(name)}")
        return jsonify({'error': 'Missing url or name'}), 400

    try:
        logger.info(f"Starting verification with 120s timeout...")
        # Use cross-platform timeout protection
        result = run_with_timeout(verify_pdf_sds, args=(url, name), timeout=120)
        logger.info(f"Verification complete: {result}")
        
        # Return the enhanced result structure
        return jsonify(result), 200
        
    except TimeoutError:
        logger.error(f"Verification timeout after 120s")
        return jsonify({
            'error': 'Verification timeout - PDF too large or slow to process',
            'verified': False,
            'used_ocr': False,
            'image_only_pdf': False
        }), 408
    except Exception as e:
        logger.error(f"Verification exception: {type(e).__name__}: {e}")
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return jsonify({
            'error': f'Verification failed: {str(e)}',
            'verified': False,
            'used_ocr': False,
            'image_only_pdf': False
        }), 500

# -----------------------------------------------------------------------------
# Parse SDS over HTTP (reuses existing parser)
# -----------------------------------------------------------------------------
@app.route('/parse-sds', methods=['POST'])
def parse_sds_http():
    """
    Body: { "product_id": 123, "pdf_url": "https://..." }
    Returns: Parsed fields suitable for upsert into sds_metadata.
    """
    logger.info(f"SDS parsing endpoint called")
    
    if parse_sds_pdf is None:
        err_msg = f"parse_sds_pdf could not be imported: {_import_err}" if '_import_err' in globals() else "Unknown import error"
        logger.error(f"Import error: {err_msg}")
        return jsonify({"error": err_msg}), 500

    data = request.json or {}
    product_id = data.get("product_id")
    pdf_url = data.get("pdf_url")
    
    logger.info(f"Product ID: {product_id}, PDF URL: {pdf_url[:100]}...")

    if not product_id or not pdf_url:
        logger.warning(f"Missing required parameters: product_id={bool(product_id)}, pdf_url={bool(pdf_url)}")
        return jsonify({"error": "Missing product_id or pdf_url"}), 400

    try:
        logger.info(f"Starting SDS parsing...")
        parsed = parse_sds_pdf(pdf_url, product_id=int(product_id))
        logger.info(f"Parsing complete")

        def _get(attr, default=None):
            if hasattr(parsed, attr):
                return getattr(parsed, attr)
            if isinstance(parsed, dict):
                return parsed.get(attr, default)
            return default

        result = {
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
            "ocr_available": OCR_AVAILABLE,
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Parsing failed: {type(e).__name__}: {e}")
        import traceback
        logger.debug(f"Exception traceback: {traceback.format_exc()}")
        return jsonify({"error": f"parse_sds failed: {e}"}), 500


# -----------------------------------------------------------------------------
# Direct PDF Parsing Endpoint (using improved parser)
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
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            
            tmp_path = Path(tmp_file.name)
        
        try:
            # Parse using the new parser
            parsed_result = parse_pdf_direct(tmp_path)
            
            return jsonify({
                "success": True,
                "product_id": product_id,
                "parsed_data": parsed_result,
                "ocr_available": OCR_AVAILABLE
            }), 200
            
        finally:
            # Clean up temporary file
            if tmp_path.exists():
                os.unlink(tmp_path)
            
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        return jsonify({"error": f"PDF parsing failed: {e}"}), 500


if __name__ == '__main__':
    logger.info(f"Starting ChemFetch OCR Service")
    logger.info(f"OCR Mode: {OCR_MODE}")
    logger.info(f"OCR Available: {OCR_AVAILABLE}")
    logger.info(f"Memory Mode: {'lightweight' if not OCR_AVAILABLE else 'full'}")
    
    app.run(host='0.0.0.0', port=5001, debug=False)
