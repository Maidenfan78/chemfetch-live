"""
Dependency imports and availability checks
"""
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

# Graceful imports for lightweight mode
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] PyMuPDF available")
except ImportError:
    fitz = None
    PYMUPDF_AVAILABLE = False
    logger.info("[SDS_EXTRACTOR] PyMuPDF not available")

try:
    import pytesseract
    OCR_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] pytesseract available")
except ImportError:
    pytesseract = None
    OCR_AVAILABLE = False
    logger.info("[SDS_EXTRACTOR] pytesseract not available")

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] pdf2image available")
except ImportError:
    convert_from_path = None
    PDF2IMAGE_AVAILABLE = False
    logger.info("[SDS_EXTRACTOR] pdf2image not available")

# Fallback to pdfplumber for text extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] pdfplumber available")
except ImportError:
    pdfplumber = None
    PDFPLUMBER_AVAILABLE = False
    logger.warning("[SDS_EXTRACTOR] pdfplumber not available")

# Always available fallback
try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    PDFMINER_AVAILABLE = True
    logger.info("[SDS_EXTRACTOR] pdfminer.six available")
except ImportError:
    pdfminer_extract = None
    PDFMINER_AVAILABLE = False
    logger.error("[SDS_EXTRACTOR] pdfminer.six not available - this should not happen!")
