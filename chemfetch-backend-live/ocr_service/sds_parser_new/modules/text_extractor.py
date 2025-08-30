"""
PDF text extraction module
"""
import io
import logging
from pathlib import Path
from typing import Tuple, Optional
from PIL import Image

from .dependencies import (
    PYMUPDF_AVAILABLE, PDFPLUMBER_AVAILABLE, PDFMINER_AVAILABLE,
    OCR_AVAILABLE, PDF2IMAGE_AVAILABLE,
    pytesseract, convert_from_path, pdfminer_extract, fitz, pdfplumber
)
from .config import MIN_TEXT_LENGTH

logger = logging.getLogger(__name__)


def extract_text(path: Path) -> Tuple[str, Optional[str]]:
    """Extract text from PDF with multiple fallback methods and improved OCR triggering."""
    logger.info(f"[SDS_EXTRACTOR] Starting text extraction from: {path}")

    best_text = ""
    extraction_method = None
    ocr_error: Optional[str] = None
    
    # Method 1: PyMuPDF (if available - fastest)
    if PYMUPDF_AVAILABLE and fitz:
        try:
            logger.info("[SDS_EXTRACTOR] Attempting PyMuPDF text extraction...")
            doc = fitz.open(str(path))
            logger.info(f"[SDS_EXTRACTOR] PDF opened, pages: {len(doc)}")
            
            text = ""
            for i, page in enumerate(doc):
                page_text = page.get_text()
                text += page_text
                if i == 0:  # Log first page for debugging
                    logger.info(f"[SDS_EXTRACTOR] PyMuPDF page 1: {len(page_text)} chars")
            
            doc.close()
            logger.info(f"[SDS_EXTRACTOR] PyMuPDF extracted {len(text)} characters total")
            
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                extraction_method = "PyMuPDF"
                
        except Exception as e:
            logger.error(f"[SDS_EXTRACTOR] PyMuPDF extraction failed: {e}")
    
    # Method 2: pdfplumber (reliable for text-based PDFs)
    if PDFPLUMBER_AVAILABLE and pdfplumber:
        try:
            logger.info("[SDS_EXTRACTOR] Attempting pdfplumber text extraction...")
            with pdfplumber.open(path) as pdf:
                text = ""
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    text += page_text
                    if i == 0:
                        logger.info(f"[SDS_EXTRACTOR] pdfplumber page 1: {len(page_text)} chars")
            
            logger.info(f"[SDS_EXTRACTOR] pdfplumber extracted {len(text)} characters total")
            
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                extraction_method = "pdfplumber"
                
        except Exception as e:
            logger.error(f"[SDS_EXTRACTOR] pdfplumber extraction failed: {e}")
    
    # Method 3: pdfminer.six fallback (always available)
    if PDFMINER_AVAILABLE and pdfminer_extract:
        try:
            logger.info("[SDS_EXTRACTOR] Attempting pdfminer.six text extraction...")
            with open(path, 'rb') as f:
                text = pdfminer_extract(f)
            
            logger.info(f"[SDS_EXTRACTOR] pdfminer.six extracted {len(text)} characters")
            
            if len(text.strip()) > len(best_text.strip()):
                best_text = text
                extraction_method = "pdfminer.six"
                
        except Exception as e:
            logger.error(f"[SDS_EXTRACTOR] pdfminer.six extraction failed: {e}")
    
    # Check if we need OCR (insufficient text from all methods)
    text_length = len(best_text.strip())
    logger.info(f"[SDS_EXTRACTOR] Best text extraction: {text_length} chars using {extraction_method}")

    # Method 4: OCR fallback (if text is insufficient AND OCR is available)
    if text_length < MIN_TEXT_LENGTH and OCR_AVAILABLE and pytesseract:
        logger.warning(f"[SDS_EXTRACTOR] Text too short ({text_length} chars), falling back to OCR...")
        logger.info("[SDS_EXTRACTOR] Converting PDF to images for OCR...")

        images = []
        if PDF2IMAGE_AVAILABLE and convert_from_path:
            try:
                images = convert_from_path(str(path), dpi=300, first_page=1, last_page=10)
                logger.info(f"[SDS_EXTRACTOR] Converted to {len(images)} images for OCR using pdf2image")
            except Exception as e:
                ocr_error = f"convert_from_path failed: {e}"
                logger.exception(f"[SDS_EXTRACTOR] {ocr_error}")
                return best_text, ocr_error
        elif PYMUPDF_AVAILABLE and fitz:
            try:
                doc = fitz.open(str(path))
                for i, page in enumerate(doc):
                    pix = page.get_pixmap(dpi=300)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    images.append(img)
                doc.close()
                logger.info(f"[SDS_EXTRACTOR] Converted to {len(images)} images for OCR using PyMuPDF")
            except Exception as e:
                ocr_error = f"PyMuPDF image conversion failed: {e}"
                logger.exception(f"[SDS_EXTRACTOR] {ocr_error}")
                return best_text, ocr_error
        else:
            ocr_error = "No PDF to image converter available"
            logger.error(f"[SDS_EXTRACTOR] {ocr_error}")
            return best_text, ocr_error

        ocr_text = ""
        page_errors = []
        for i, img in enumerate(images):
            try:
                logger.info(f"[SDS_EXTRACTOR] Running OCR on page {i+1}...")
                page_text = pytesseract.image_to_string(img, config='--psm 1 -l eng')
                ocr_text += f"\n--- Page {i+1} ---\n{page_text}"
                logger.info(f"[SDS_EXTRACTOR] OCR page {i+1}: {len(page_text)} chars extracted")
                if page_text.strip():
                    sample = page_text.strip()[:100].replace('\n', ' ')
                    logger.info(f"[SDS_EXTRACTOR] OCR page {i+1} sample: '{sample}...'")
            except Exception as page_error:
                err = f"pytesseract failed for page {i+1}: {page_error}"
                logger.exception(f"[SDS_EXTRACTOR] {err}")
                page_errors.append(err)
                continue

        logger.info(f"[SDS_EXTRACTOR] OCR extracted {len(ocr_text)} characters total")

        if ocr_text.strip():
            logger.info(f"[SDS_EXTRACTOR] OCR successful! Using OCR text ({len(ocr_text)} chars)")
            return ocr_text, None

        ocr_error = "; ".join(page_errors) if page_errors else "OCR produced no text"
        logger.error(f"[SDS_EXTRACTOR] {ocr_error}")

    elif text_length < MIN_TEXT_LENGTH and not OCR_AVAILABLE:
        ocr_error = "OCR not available"
        logger.error(f"[SDS_EXTRACTOR] Insufficient text ({text_length} chars) and OCR not available")
    else:
        logger.info(f"[SDS_EXTRACTOR] Sufficient text extracted ({text_length} chars), no OCR needed")

    if not best_text.strip():
        err_msg = ocr_error or "All text extraction methods failed"
        logger.error(f"[SDS_EXTRACTOR] {err_msg}")
        return "", ocr_error

    logger.info(f"[SDS_EXTRACTOR] Final text: {len(best_text)} chars using {extraction_method}")
    return best_text, ocr_error
