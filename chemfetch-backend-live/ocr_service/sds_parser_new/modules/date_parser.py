"""
Date parsing module
"""
import logging
from typing import Optional, List
from .config import DATE_PATTERN

logger = logging.getLogger(__name__)


def extract_issue_date(text: str) -> Optional[str]:
    """Extract and parse issue date from SDS text."""
    matches = list(DATE_PATTERN.finditer(text))
    chosen = None
    
    if matches:
        try:
            from datetime import date
            from dateutil import parser as dateparser
            
            today = date.today()
            for m in matches:
                label = m.group(1).lower()
                candidate = m.group(2).strip()
                
                try:
                    # Parse with dayfirst=True for Australian format (DD/MM/YYYY)
                    d = dateparser.parse(candidate, dayfirst=True).date()
                    if d > today:  # Skip future dates
                        continue
                    
                    # Normalize month abbreviations with trailing dot (e.g., Jan.)
                    candidate = candidate.replace('Jan.', 'Jan').replace('Feb.', 'Feb').replace('Mar.', 'Mar').replace('Apr.', 'Apr').replace('Jun.', 'Jun').replace('Jul.', 'Jul').replace('Aug.', 'Aug').replace('Sep.', 'Sep').replace('Oct.', 'Oct').replace('Nov.', 'Nov').replace('Dec.', 'Dec')
                    # Convert to ISO format
                    chosen_iso = d.strftime('%Y-%m-%d')
                    logger.info(f"[SDS_EXTRACTOR] Parsed date '{candidate}' as {d} -> ISO: {chosen_iso}")
                    
                    # Prefer issue/revision/prepared/issued/creation/version over print
                    if any(key in label for key in ['issue', 'prepared', 'issued', 'creation', 'revision', 'version']):
                        chosen = chosen_iso
                        break
                    if not chosen:
                        chosen = chosen_iso
                        
                except Exception as e:
                    logger.warning(f"[SDS_EXTRACTOR] Failed to parse date '{candidate}': {e}")
                    continue
                    
        except ImportError:
            logger.warning("[SDS_EXTRACTOR] python-dateutil not available, skipping date parsing")
            chosen = None
    
    return chosen
