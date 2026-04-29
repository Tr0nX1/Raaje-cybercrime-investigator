import pdfplumber


def is_text_based(pdf_path: str, sample_pages: int = 3, min_chars: int = 50) -> bool:
    """
    Returns True if PDF has selectable text, False if it's scanned/image-based.
    Samples first N pages to decide — avoids reading the whole file.
    """
    with pdfplumber.open(pdf_path) as pdf:
        pages_to_check = min(sample_pages, len(pdf.pages))
        total_chars = 0
        for i in range(pages_to_check):
            text = pdf.pages[i].extract_text() or ""
            total_chars += len(text.strip())

    return total_chars >= min_chars


def detect_pdf_type(pdf_path: str, sample_pages: int = 3, min_chars: int = 50) -> str:
    """
    Detect PDF type by sampling pages.
    Returns "text", "scanned", or "mixed".
    """
    with pdfplumber.open(pdf_path) as pdf:
        text_page_count = 0
        scanned_page_count = 0
        pages_to_check = min(sample_pages, len(pdf.pages))

        for i in range(pages_to_check):
            text = pdf.pages[i].extract_text() or ""
            if len(text.strip()) >= min_chars:
                text_page_count += 1
            else:
                scanned_page_count += 1

        if text_page_count > 0 and scanned_page_count > 0:
            return "mixed"
        elif text_page_count > scanned_page_count:
            return "text"
        else:
            return "scanned"


def get_page_count(pdf_path: str) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
