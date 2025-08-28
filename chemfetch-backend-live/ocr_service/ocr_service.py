import os
import tempfile
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Union
import requests
import logging
import re  # ✅ needed for regex in parsing
import sys
from pdfminer.high_level import extract_text as pdfminer_extract_text


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
except Exception as e:
    logger.warning(f"OCR dependencies not available: {e}. Running in text-only mode.")
    pytesseract = None  # add this line
    class Image:  # dummy
        pass
    def convert_from_path(*args, **kwargs):  # dummy
        raise RuntimeError("OCR not available in lightweight mode")


# -----------------------------------------------------------------------------
# Try to import parse_sds_pdf from the local module. Enhanced path handling.
# -----------------------------------------------------------------------------
try:
    # Method 1: Direct import when running from ocr_service directory
    from parse_sds import parse_sds_pdf
    logger.info("Successfully imported parse_sds_pdf from parse_sds module")
except ImportError:
    try:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        from parse_sds import parse_sds_pdf
        logger.info("Successfully imported parse_sds_pdf with path adjustment")
    except ImportError:
        try:
            from ocr_service.parse_sds import parse_sds_pdf
            logger.info("Successfully imported parse_sds_pdf from ocr_service package")
        except ImportError as e:
            parse_sds_pdf = None
            _import_err = e
            logger.error(f"Failed to import parse_sds_pdf: {e}")

# Also import the new SDS extractor directly for the HTTP endpoint
try:
    from sds_parser_new.sds_extractor import parse_pdf as parse_pdf_direct
    logger.info("Successfully imported parse_pdf_direct from sds_parser_new")
except ImportError:
    try:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        from sds_parser_new.sds_extractor import parse_pdf as parse_pdf_direct
        logger.info("Successfully imported parse_pdf_direct with path adjustment")
    except ImportError as e:
        parse_pdf_direct = None
        _direct_import_err = e

# Import quick parser as backup
try:
    from quick_parser import parse_sds_from_text
    logger.info("Successfully imported quick_parser as backup")
except ImportError as e:
    parse_sds_from_text = None
    logger.error(f"Failed to import quick_parser: {e}")

# -----------------------------------------------------------------------------
# Environment & global config
# -----------------------------------------------------------------------------
app = Flask(__name__)
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

    On Unix we use ``signal.alarm``. On Windows we run without enforced timeout.
    """
    if kwargs is None:
        kwargs = {}

    if os.name != "nt":
        import signal
        def _handler(signum, frame):
            raise TimeoutError("Function execution timeout")
        old_handler = signal.signal(signal.SIGALRM, _handler)
        signal.alarm(timeout)
        try:
            return func(*args, **kwargs)
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:
        return func(*args, **kwargs)

# -----------------------------------------------------------------------------
# Lightweight OCR/Text helpers
# -----------------------------------------------------------------------------

def extract_text_from_pdf_with_ocr(pdf_path: Path, max_pages: int = 10) -> Tuple[str, bool]:
    """
    Extract text from PDF using multiple extraction methods and OCR fallback.
    Returns (text, used_ocr)
    """
    if not OCR_AVAILABLE:
        return extract_text_from_pdf_multiple_methods(pdf_path, max_pages)

    text, image_only = extract_text_from_pdf_multiple_methods(pdf_path, max_pages)
    if not image_only:
        return text, False

    # OCR fallback
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
        return text, True


def extract_text_from_pdf_multiple_methods(pdf_path: Path, max_pages: int = 10) -> Tuple[str, bool]:
    """
    Extract text from PDF using multiple methods for maximum compatibility.
    Returns (text, is_image_only_pdf)
    """
    text = ""

    # Method 1: PyMuPDF
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

    # Method 2: pdfplumber
    if PDF_EXTRACTOR == "pdfplumber" or ('pdfplumber' in globals() and not text.strip()):
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

    # Method 3: pdfminer.six
    try:
        with open(pdf_path, 'rb') as f:
            text = pdfminer_extract_text(f, maxpages=max_pages)
        if len(text.strip()) >= 50:
            logger.info(f"Extracted {len(text)} characters using pdfminer.six")
            return text, False
        else:
            logger.info(f"Low text content detected ({len(text.strip())} chars) - likely image-only PDF")
            return text, True
    except Exception as e:
        logger.error(f"All PDF text extraction methods failed: {e}")
        return "", True

# -----------------------------------------------------------------------------
# Health check endpoints
# -----------------------------------------------------------------------------
@app.route("/")
def root():
    return jsonify({
        "service": "ChemFetch OCR Service",
        "status": "healthy",
        "version": "2025.08.28",
        "endpoints": ["/health", "/verify-sds", "/parse-sds", "/parse-pdf-direct"],
        "ocr_available": OCR_AVAILABLE,
        "pdf_extractor": PDF_EXTRACTOR,
        "timestamp": datetime.now().isoformat(),
        "port": int(os.getenv('PORT', '5001')),
        "ready": True
    })

@app.route("/health")
def health_check():
    server_host = request.host  # e.g., '127.0.0.1:5001'
    env_port = os.getenv('PORT')
    server_port = int(server_host.split(':')[1]) if ':' in server_host else None

    return jsonify({
        "status": "healthy",
        "service": "ChemFetch OCR Service",
        "ocr_available": OCR_AVAILABLE,
        "ocr_mode": OCR_MODE,
        "memory_mode": "lightweight" if not OCR_AVAILABLE else "full",
        "pdf_extractor": PDF_EXTRACTOR,
        "timestamp": datetime.now().isoformat(),
        # Keep both so you can sanity-check
        "server_port": server_port,
        "env_port": int(env_port) if env_port and env_port.isdigit() else None,
        "endpoints": ["/", "/health", "/verify-sds", "/parse-sds", "/parse-pdf-direct"],  # remove /verify-sds if you didn't add it
        "debug_info": {
            "python_version": sys.version,
            "working_directory": str(os.getcwd()),
            "temp_dir": str(DEBUG_DIR),
            "environment": {
                "PORT": os.getenv('PORT'),
                "OCR_MODE": os.getenv('OCR_MODE'),
                "DEBUG_IMAGES": os.getenv('DEBUG_IMAGES')
            }
        }
    })

@app.route("/gpu-check")
def gpu_check():
    return jsonify({
        "cuda_compiled": False,
        "device_count": 0,
        "note": "Running in CPU-only mode without PaddleOCR"
    })

# -----------------------------------------------------------------------------
# SDS Verification (unchanged except for minor robustness)
# -----------------------------------------------------------------------------
# Add near the other routes
@app.route('/verify-sds', methods=['POST'])
def verify_sds_http():
    data = request.json or {}
    pdf_url = data.get('pdf_url')
    product_name = data.get('product_name') or 'Product'
    if not pdf_url:
        return jsonify({'error': 'Missing pdf_url'}), 400

    res = verify_pdf_sds(pdf_url, product_name)
    # don’t leak raw text in HTTP response
    res.pop('_extracted_text', None)

    # 200 if verified, 400 otherwise (so callers can branch)
    return jsonify(res), 200 if res.get('verified') else 400


def verify_pdf_sds(url: str, product_name: str, keywords=None) -> Dict[str, Any]:
    keywords = keywords or [
        # Core SDS Terms
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
        # Section numbering
        "section 1", "section 2", "section 3", "section 4", "section 5",
        # Extra terms
        "emergency contact", "manufacturer", "supplier", "emergency phone",
        "revision date", "preparation date", "issue date", "version",
        "flammable", "corrosive", "toxic", "irritant", "oxidizing",
        "exposure limit", "threshold limit", "workplace exposure",
        "personal protective equipment", "ppe", "respiratory protection",
        # AU specific
        "australian dangerous goods", "adg", "workplace health and safety",
        "whs", "safe work australia", "nohsc", "acgih", "aioh"
    ]

    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        content_type = response.headers.get('content-type', '').lower()
        if 'pdf' not in content_type:
            logger.info(f"Not a PDF: {content_type}")
            return {"verified": False, "error": "Not a PDF file", "used_ocr": False,
                    "image_only_pdf": False, "text_length": 0, "keyword_matches": 0}

        max_size = 50 * 1024 * 1024
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            size = 0
            logger.info(f"Starting PDF download with {max_size // (1024*1024)}MB limit...")
            for chunk in response.iter_content(chunk_size=8192):
                size += len(chunk)
                if size > max_size:
                    logger.warning(f"PDF too large: {size} bytes")
                    os.unlink(tmp_file.name)
                    return {"verified": False, "error": "PDF file too large", "used_ocr": False,
                            "image_only_pdf": False, "text_length": 0, "keyword_matches": 0}
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)

        try:
            logger.info("Extracting text from PDF...")
            text, used_ocr = extract_text_from_pdf_with_ocr(tmp_path, max_pages=10)
            text_lower = text.lower()
            logger.info(f"Extracted {len(text)} characters (OCR: {used_ocr})")

            keyword_matches = sum(1 for kw in keywords if kw.lower() in text_lower)
            matched_keywords = [kw for kw in keywords if kw.lower() in text_lower]
            logger.info(f"Found {keyword_matches}/{len(keywords)} keyword matches")
            logger.info(f"Top matched keywords: {matched_keywords[:5]}")

            if len(text.strip()) < 50:
                logger.warning(f"Very short text content: {len(text.strip())} chars")
            elif len(text.strip()) < 200:
                logger.info(f"Short text content: {len(text.strip())} chars")
            else:
                logger.info(f"Good text content: {len(text.strip())} chars")

            # validation threshold
            is_valid_sds = keyword_matches >= 3  # tightened to reduce false positives
            filename_has_sds = any(term in url.lower() for term in ['sds', 'msds', 'safety', 'data', 'sheet'])
            if filename_has_sds and keyword_matches >= 1:
                is_valid_sds = True
            if not OCR_AVAILABLE and len(text.strip()) >= 100 and keyword_matches >= 3:
                is_valid_sds = True

            image_only_pdf = (len(text.strip()) < 50) and (not OCR_AVAILABLE or used_ocr)
            result = {
                "verified": is_valid_sds,
                "used_ocr": used_ocr,
                "image_only_pdf": image_only_pdf,
                "text_length": len(text),
                "keyword_matches": keyword_matches,
                "ocr_available": OCR_AVAILABLE,
                "_extracted_text": text  # ⚠️ kept for fallback parser usage; not returned to client
            }
            if image_only_pdf:
                result["warning"] = "Image-only PDF detected but OCR not available"
            return result
        finally:
            if tmp_path.exists():
                os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"Failed to verify {url}: {type(e).__name__}: {e}")
        import traceback
        logger.debug(f"Verification traceback: {traceback.format_exc()}")
        return {"verified": False, "error": str(e), "used_ocr": False,
                "image_only_pdf": False, "text_length": 0, "keyword_matches": 0}

# -----------------------------------------------------------------------------
# ✅ Unified /parse-sds endpoint with layered fallbacks
# Order: parse_sds_pdf → verification-based simple parser → quick_parser
# -----------------------------------------------------------------------------
@app.route('/parse-sds', methods=['POST'])
def parse_sds_http():
    """
    Body: { "product_id": 123, "pdf_url": "https://..." }
    Returns: Parsed fields suitable for upsert into sds_metadata.
    """
    data = request.json or {}
    product_id = data.get("product_id")
    pdf_url = data.get("pdf_url")

    logger.info("SDS parsing endpoint called (UNIFIED)")
    logger.info(f"Product ID: {product_id}, PDF URL: {str(pdf_url)[:100]}...")

    if not product_id or not pdf_url:
        logger.warning(f"Missing required parameters: product_id={bool(product_id)}, pdf_url={bool(pdf_url)}")
        return jsonify({"error": "Missing product_id or pdf_url"}), 400

    # ---------- Attempt 1: Primary parser (if available) ----------
    if parse_sds_pdf is not None:
        try:
            logger.info("Attempt 1: parse_sds_pdf")
            parsed = parse_sds_pdf(pdf_url, product_id=int(product_id))
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
            logger.error(f"Primary parser failed, falling back. Reason: {type(e).__name__}: {e}")

    # ---------- Attempt 2: Verification + simple regex extraction ----------
    try:
        logger.info("Attempt 2: verification + simple extraction")
        verification_result = verify_pdf_sds(pdf_url, "Product")
        if not verification_result.get('verified'):
            return jsonify({
                "error": "PDF failed verification",
                "verification_result": {k: v for k, v in verification_result.items() if k != "_extracted_text"}
            }), 400

        # Prefer using text already extracted during verification to avoid re-download
        text = verification_result.get("_extracted_text", "") or ""
        if not text:
            # fallback: download and extract again
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                response = requests.get(pdf_url, timeout=30, stream=True)
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=8192):
                    tmp_file.write(chunk)
                tmp_path = Path(tmp_file.name)
            try:
                # Try pdfplumber first if available; otherwise use multi-method
                try:
                    import pdfplumber
                    with pdfplumber.open(tmp_path) as pdf:
                        for page in pdf.pages:
                            text += page.extract_text() or ""
                except Exception:
                    text, _ = extract_text_from_pdf_multiple_methods(tmp_path, max_pages=10)
            finally:
                if 'tmp_path' in locals() and tmp_path.exists():
                    os.unlink(tmp_path)

        # Basic regex extraction
        vendor_match = re.search(r'(?:Manufacturer|Company)[:\s]*([^\n\r]+)', text, re.IGNORECASE)
        vendor = vendor_match.group(1).strip() if vendor_match else None

        date_match = re.search(r'(?:Issue Date|Revision Date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', text, re.IGNORECASE)
        issue_date = date_match.group(1).strip() if date_match else None

        dg_match = re.search(r'(?:Hazard Class|Class)[:\s]*([1-9](?:\.\d+)?)', text, re.IGNORECASE)
        dangerous_goods_class = dg_match.group(1).strip() if dg_match else None

        is_dangerous = bool(dangerous_goods_class and dangerous_goods_class.lower() not in ['none', 'n/a'])

        # If quick_parser is available, let it refine/enrich from text
        hazard_statements = []
        packing_group = None
        subsidiary_risks = []
        raw_json = {"verification_result": {k: v for k, v in verification_result.items() if k != "_extracted_text"},
                    "text_length": len(text), "parsing_method": "verification_simple"}

        if parse_sds_from_text is not None and text:
            try:
                logger.info("Refining with quick_parser.parse_sds_from_text")
                qp = parse_sds_from_text(text)
                if isinstance(qp, dict):
                    vendor = qp.get("vendor") or vendor
                    issue_date = qp.get("issue_date") or issue_date
                    dangerous_goods_class = qp.get("dangerous_goods_class") or dangerous_goods_class
                    packing_group = qp.get("packing_group") or packing_group
                    subsidiary_risks = qp.get("subsidiary_risks") or subsidiary_risks
                    hazard_statements = qp.get("hazard_statements") or hazard_statements
                    is_dangerous = qp.get("dangerous_good") if qp.get("dangerous_good") is not None else is_dangerous
                    raw_json["quick_parser"] = {k: v for k, v in qp.items() if k not in {"hazard_statements"}}
            except Exception as e:
                logger.warning(f"quick_parser refinement failed: {e}")

        result = {
            "product_id": int(product_id),
            "vendor": vendor,
            "issue_date": issue_date,
            "hazardous_substance": is_dangerous,
            "dangerous_good": is_dangerous,
            "dangerous_goods_class": dangerous_goods_class,
            "packing_group": packing_group,
            "subsidiary_risks": subsidiary_risks,
            "hazard_statements": hazard_statements,
            "raw_json": raw_json,
            "ocr_available": OCR_AVAILABLE
        }
        logger.info("SDS parsing successful using verification fallback")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Fallback parse failed: {e}")

    # ---------- Attempt 3: if everything else fails ----------
    return jsonify({"error": "parse_sds failed after all fallbacks"}), 500

# -----------------------------------------------------------------------------
# Direct PDF Parsing Endpoint (existing)
# -----------------------------------------------------------------------------
@app.route('/parse-pdf-direct', methods=['POST'])
def parse_pdf_direct_http():
    if parse_pdf_direct is None:
        err_msg = f"parse_pdf_direct could not be imported: {_direct_import_err}" if '_direct_import_err' in globals() else "Direct parser not available"
        return jsonify({"error": err_msg}), 500

    data = request.json or {}
    pdf_url = data.get("pdf_url")
    product_id = data.get("product_id")

    if not pdf_url:
        return jsonify({"error": "Missing pdf_url"}), 400

    try:
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            response = requests.get(pdf_url, timeout=30, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)
        try:
            parsed_result = parse_pdf_direct(tmp_path)
            return jsonify({
                "success": True,
                "product_id": product_id,
                "parsed_data": parsed_result,
                "ocr_available": OCR_AVAILABLE
            }), 200
        finally:
            if tmp_path.exists():
                os.unlink(tmp_path)
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        return jsonify({"error": f"PDF parsing failed: {e}"}), 500

# -----------------------------------------------------------------------------
# OCR Endpoint for image processing (legacy compatibility)
# -----------------------------------------------------------------------------
@app.route('/ocr', methods=['POST'])
def ocr_endpoint():
    if not OCR_AVAILABLE:
        return jsonify({
            "error": "OCR not available in text-only mode",
            "mode": "text-only",
            "available_endpoints": ["/verify-sds", "/parse-sds", "/parse-pdf-direct"],
            "recommendation": "Use /verify-sds for PDF text extraction without OCR"
        }), 501
    return jsonify({"error": "OCR endpoint not yet implemented"}), 501

if __name__ == '__main__':
    logger.info(f"🚀 Starting ChemFetch OCR Service")
    logger.info(f"📊 OCR Mode: {OCR_MODE}")
    logger.info(f"🔬 OCR Available: {OCR_AVAILABLE}")
    logger.info(f"💾 Memory Mode: {'lightweight' if not OCR_AVAILABLE else 'full'}")
    logger.info(f"📄 PDF Extractor: {PDF_EXTRACTOR}")

    port = int(os.getenv('PORT', '5001'))

    logger.info(f"🌐 Environment check:")
    logger.info(f"   PORT: {os.getenv('PORT')}")
    logger.info(f"   OCR_MODE: {os.getenv('OCR_MODE')}")
    logger.info(f"   DEBUG_IMAGES: {os.getenv('DEBUG_IMAGES')}")
    logger.info(f"   Working Directory: {os.getcwd()}")

    if os.getenv('PORT'):
        logger.info(f"🚀 Production mode detected - starting Flask server on port {port}")
        logger.info(f"🔗 Service will be available at: http://0.0.0.0:{port}")
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    else:
        logger.info("🛠️ Development mode - starting Flask dev server")
        logger.info(f"🔗 Service will be available at: http://localhost:5001")
        app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
