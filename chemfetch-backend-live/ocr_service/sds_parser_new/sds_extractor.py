import re
from pathlib import Path
from typing import cast
import fitz
from pdf2image import convert_from_path
import pytesseract
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)


# detect section headers like "Section 3" or "14:" but avoid subpoints such as "1.1"
SECTION_PATTERN = re.compile(r'^\s*(?:section\s*)?(\d{1,2})(?:\s|:|\.)(?=\s)', re.IGNORECASE | re.MULTILINE)

# allow some text (e.g. "/ Date of revision") and optional footer lines between
# the label and the actual date value
DATE_PATTERN = re.compile(
    r'(\b(?:Revision(?: Date)?|Issue Date|Date of issue|Version date|SDS creation date|Date Prepared|Issued)[^\n]{0,40})\s*[:]?\s*(?:\nPage[^\n]*\n)?\s*'
    r'((?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(?:[A-Za-z]+\s+\d{1,2},?\s*\d{4})|(?:\d{4}-\d{2}-\d{2}))',
    re.IGNORECASE)

FIELD_LABELS = {
    'product_name': [r'Product identifier', r'Product Name', r'Trade name'],
    'manufacturer': [r'Manufacturer', r'Supplier', r'Company name of supplier', r'Producer', r'Company'],
    'product_use': [r'Recommended use', r'Intended use', r'Use', r'Product use', r'Relevant identified uses', r'Identified uses'],
    # section 14 labels handled separately
    'dangerous_goods_class': [r'DG Class', r'Class', r'Transport hazard class', r'(?:IMDG|IATA|ADG)?\s*Hazard Class', r'Australian Dangerous Goods class'],
    'subsidiary_risk': [r'Subsidiary risk'],
    'packing_group': [r'Packing group', r'PG', r'.*packing group', r'Australian Dangerous Goods packing group'],
}

# flattened list of all label regexes for filtering
ALL_LABELS = [lab for labs in FIELD_LABELS.values() for lab in labs] + ['SDS no.', 'SDS number']


def extract_text(path: Path) -> str:
    logger.info(f"[SDS_EXTRACTOR] Starting text extraction from: {path}")
    logger.info(f"[SDS_EXTRACTOR] File size: {path.stat().st_size} bytes")
    
    try:
        logger.info(f"[SDS_EXTRACTOR] Attempting PyMuPDF text extraction...")
        doc = fitz.open(str(path))
        logger.info(f"[SDS_EXTRACTOR] PDF opened, pages: {len(doc)}")
        
        text = "".join(cast(fitz.Page, page).get_text() for page in doc)  # type: ignore[attr-defined]
        logger.info(f"[SDS_EXTRACTOR] PyMuPDF extracted {len(text)} characters")
        
        if text.strip():
            logger.info(f"[SDS_EXTRACTOR] PyMuPDF extraction successful")
            return text
            
        logger.warning(f"[SDS_EXTRACTOR] PyMuPDF extracted empty text, falling back to OCR...")
        
    except Exception as e:
        logger.error(f"[SDS_EXTRACTOR] PyMuPDF extraction failed: {type(e).__name__}: {e}")
        logger.info(f"[SDS_EXTRACTOR] Falling back to OCR...")
    
    try:
        logger.info(f"[SDS_EXTRACTOR] Converting PDF to images for OCR...")
        images = convert_from_path(str(path))
        logger.info(f"[SDS_EXTRACTOR] Converted to {len(images)} images")
        
        logger.info(f"[SDS_EXTRACTOR] Running OCR on images...")
        ocr_text = ''.join(pytesseract.image_to_string(img) for img in images)
        logger.info(f"[SDS_EXTRACTOR] OCR extracted {len(ocr_text)} characters")
        
        return ocr_text
        
    except Exception as e:
        logger.error(f"[SDS_EXTRACTOR] OCR extraction failed: {type(e).__name__}: {e}")
        raise Exception(f"Both PyMuPDF and OCR text extraction failed: {e}")


def get_section(text: str, number: int) -> str:
    pattern = re.compile(rf'^\s*(?:section\s*)?{number}\b[^\n]*', re.IGNORECASE | re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ''
    start = match.end()
    end = len(text)
    for m in SECTION_PATTERN.finditer(text, start):
        num = int(m.group(1))
        if num > number:
            end = m.start()
            break
    return text[start:end]


def extract_after_label(section_text: str, labels):
    lines = section_text.splitlines()
    for i, line in enumerate(lines):
        clean = line.strip()
        label_part = clean.split(':', 1)[0]
        for label in labels:
            if re.fullmatch(label, label_part, re.IGNORECASE):
                # try same line after colon
                if ':' in clean:
                    after = clean.split(':', 1)[1].strip()
                    if after and not any(re.fullmatch(lab, after, re.IGNORECASE) for lab in ALL_LABELS):
                        return after
                # look at subsequent lines for value
                j = i + 1
                while j < len(lines):
                    candidate = lines[j].strip()
                    if candidate and not candidate.startswith(':') and not re.match(r'^[:\-]+$', candidate, re.IGNORECASE):
                        if not any(re.fullmatch(lab, candidate, re.IGNORECASE) for lab in ALL_LABELS):
                            return candidate
                    j += 1
    return None


def extract_section14_field(sec14: str, labels, value_pattern):
    lines = sec14.splitlines()
    value_re = re.compile(value_pattern, re.IGNORECASE)
    for i, line in enumerate(lines):
        stripped = line.strip()
        for lab in labels:
            # handle "Label: value" on the same line
            same_line = re.search(rf'{lab}\s*[:\-]?\s*({value_pattern})', stripped, re.IGNORECASE)
            if same_line:
                candidate = same_line.group(1).strip()
                if value_re.fullmatch(candidate):
                    return candidate
            # label present in this line, value on subsequent line
            if re.search(lab, stripped, re.IGNORECASE):
                j = i + 1
                while j < len(lines):
                    candidate = lines[j].strip()
                    if candidate and not candidate.startswith(':') and not any(re.search(l, candidate, re.IGNORECASE) for l in ALL_LABELS):
                        if not re.match(r'^\d+\.[A-Za-z]', candidate):
                            if value_re.fullmatch(candidate):
                                return candidate
                    j += 1
            # handle label split across two lines
            if i + 1 < len(lines):
                combined = stripped + " " + lines[i + 1].strip()
                if re.search(lab, combined, re.IGNORECASE):
                    j = i + 2
                    while j < len(lines):
                        candidate = lines[j].strip()
                        if candidate and not candidate.startswith(':') and not any(re.search(l, candidate, re.IGNORECASE) for l in ALL_LABELS):
                            if not re.match(r'^\d+\.[A-Za-z]', candidate):
                                if value_re.fullmatch(candidate):
                                    return candidate
                        j += 1
    # fallback: search across entire section text
    compact = ' '.join(lines)
    for lab in labels:
        m = re.search(rf'{lab}\s*[:\-]?\s*({value_pattern})', compact, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    if labels is FIELD_LABELS.get('dangerous_goods_class'):
        for line in lines:
            cand = line.strip()
            if value_re.fullmatch(cand):
                return cand
    return None


def parse_pdf(path: Path):
    logger.info(f"[SDS_EXTRACTOR] Starting PDF parsing: {path}")
    
    # Step 1: Extract text
    logger.info(f"[SDS_EXTRACTOR] Step 1: Extracting text from PDF...")
    text = extract_text(path)
    logger.info(f"[SDS_EXTRACTOR] Text extraction complete, total length: {len(text)}")
    
    if len(text) < 100:
        logger.warning(f"[SDS_EXTRACTOR] Very short text extracted ({len(text)} chars), may indicate extraction failure")
    
    result = {}
    
    # Step 2: Extract sections
    logger.info(f"[SDS_EXTRACTOR] Step 2: Extracting sections...")
    sec1 = get_section(text, 1)
    sec14 = get_section(text, 14)
    
    logger.info(f"[SDS_EXTRACTOR] Section 1 length: {len(sec1)} chars")
    logger.info(f"[SDS_EXTRACTOR] Section 14 length: {len(sec14)} chars")
    
    if len(sec1) == 0:
        logger.warning(f"[SDS_EXTRACTOR] Section 1 not found or empty")
    if len(sec14) == 0:
        logger.warning(f"[SDS_EXTRACTOR] Section 14 not found or empty")
    # product name with fallback
    product_name = extract_after_label(sec1, FIELD_LABELS['product_name'])
    if not product_name or 'sds' in product_name.lower() or 'use' in product_name.lower():
        candidates = []
        for l in sec1.splitlines():
            l = l.strip()
            if not l or l.startswith(':'):
                continue
            if any(re.fullmatch(lab, l, re.IGNORECASE) for lab in ALL_LABELS):
                continue
            if any(x in l.lower() for x in ['use', 'telephone', 'emergency', 'poison', 'fax', 'website', 'email', 'details', 'supplier', 'australia', 'new zealand', 'company', 'sds']):
                continue
            if re.match(r'^\d', l):
                continue
            candidates.append(l)
        product_name = candidates[-1] if candidates else None
    result['product_name'] = {'value': product_name, 'confidence': 1.0 if product_name else 0.0}
    manufacturer = extract_after_label(sec1, FIELD_LABELS['manufacturer'])
    if not manufacturer:
        m = re.search(r'Details of the supplier[^\n]*\n([^\n]+)', sec1, re.IGNORECASE)
        if m:
            manufacturer = m.group(1).strip()
    result['manufacturer'] = {'value': manufacturer, 'confidence': 1.0 if manufacturer else 0.0}
    value = extract_after_label(sec1, FIELD_LABELS['product_use'])
    result['product_use'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    # Section 14 fields: allow table-style layouts
    value = extract_section14_field(sec14, FIELD_LABELS['dangerous_goods_class'], r'\d[0-9A-Za-z\.]*|not\b.*|none')
    result['dangerous_goods_class'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    value = extract_section14_field(sec14, FIELD_LABELS['subsidiary_risk'], r'\d[0-9A-Za-z\.]*|none|not\b.*')
    result['subsidiary_risk'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    value = extract_section14_field(sec14, FIELD_LABELS['packing_group'], r'I{1,3}|IV|V|N\.?/?A|none|not\b.*')
    if not value:
        value = extract_section14_field(sec14, FIELD_LABELS['packing_group'], r'\d+|N\.?/?A|none|not\b.*')
    result['packing_group'] = {'value': value, 'confidence': 1.0 if value else 0.0}
    matches = list(DATE_PATTERN.finditer(text))
    chosen = None
    chosen_iso = None
    if matches:
        from datetime import date
        from dateutil import parser as dateparser
        today = date.today()
        for m in matches:
            label = m.group(1).lower()
            candidate = m.group(2).strip()
            try:
                # Try parsing with dayfirst=True for Australian/UK format (DD/MM/YYYY)
                d = dateparser.parse(candidate, dayfirst=True).date()
                if d > today:
                    continue
                # Convert to ISO format for database compatibility
                chosen_iso = d.strftime('%Y-%m-%d')
                logger.info(f"[SDS_EXTRACTOR] Parsed date '{candidate}' as {d} -> ISO: {chosen_iso}")
            except Exception as e:
                logger.warning(f"[SDS_EXTRACTOR] Failed to parse date '{candidate}': {e}")
                continue
            if any(key in label for key in ['issue', 'prepared', 'issued', 'creation']):
                chosen = chosen_iso
                break
            if not chosen:
                chosen = chosen_iso
    result['issue_date'] = {'value': chosen, 'confidence': 1.0 if chosen else 0.0}
    
    # Step 5: Summary
    logger.info(f"[SDS_EXTRACTOR] Parsing complete. Results:")
    for key, value in result.items():
        conf = value.get('confidence', 0) if isinstance(value, dict) else 0
        val = value.get('value', value) if isinstance(value, dict) else value
        logger.info(f"[SDS_EXTRACTOR]   {key}: '{val}' (confidence: {conf})")
    
    return result


if __name__ == '__main__':
    import json, sys
    for pdf in sys.argv[1:]:
        res = parse_pdf(Path(pdf))
        print(pdf)
        print(json.dumps(res, indent=2, ensure_ascii=False))
