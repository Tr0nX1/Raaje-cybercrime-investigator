"""
PDF type detection for SDR reports.
"""
import os
import re
from pathlib import Path


def detect_report_type(pdf_path: str) -> str:
    """
    Detect the type of SDR report based on filename and content patterns.

    Returns:
        "khoj_osint" for Khoj OSINT reports
        "scaninfoga" for Scaninfoga reports
        "unknown" if cannot determine
    """
    filename = Path(pdf_path).name.lower()

    # Check filename patterns
    if "khoj" in filename and "osint" in filename:
        return "khoj_osint"
    elif "scaninfoga" in filename:
        return "scaninfoga"

    # If filename doesn't give clear indication, try to read first few lines
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                first_page_text = pdf.pages[0].extract_text()[:500].lower()

                # Check for Khoj OSINT indicators
                if "osint report" in first_page_text and "operator details" in first_page_text:
                    return "khoj_osint"

                # Check for Scaninfoga indicators
                if "scaninfoga" in first_page_text or "comprehensive intelligence report" in first_page_text:
                    return "scaninfoga"

                # Check for specific field patterns
                if "security score" in first_page_text and "cibil score" in first_page_text:
                    return "scaninfoga"

                if "alias" in first_page_text and "email address" in first_page_text:
                    return "khoj_osint"

    except Exception as e:
        print(f"[warn] Could not detect report type for {pdf_path}: {e}")

    return "unknown"


def is_text_based(pdf_path: str) -> bool:
    """
    Check if PDF is text-based (not scanned image).
    """
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            if pdf.pages:
                # Check if first page has extractable text
                text = pdf.pages[0].extract_text()
                return len(text.strip()) > 100  # Consider it text-based if we get substantial text
    except Exception:
        pass
    return False


def detect_pdf_type(pdf_path: str) -> str:
    """
    Determine PDF processing type: 'text', 'scanned', or 'mixed'.
    """
    if is_text_based(pdf_path):
        return "text"
    else:
        return "scanned"