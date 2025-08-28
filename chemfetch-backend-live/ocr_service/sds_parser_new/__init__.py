"""
SDS Parser New - Enhanced SDS parsing for ChemFetch
Provides lightweight SDS parsing compatible with 512MB memory limits.
"""

# Import main functions for easy access
try:
    from .sds_extractor import parse_pdf
    __all__ = ['parse_pdf']
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"Failed to import parse_pdf: {e}")
    __all__ = []

# Version info
__version__ = "2025.08.28"
__author__ = "ChemFetch Team"
