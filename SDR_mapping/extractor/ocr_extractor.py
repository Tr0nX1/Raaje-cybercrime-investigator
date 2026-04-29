"""
OCR-based SDR report extraction for scanned PDFs.
"""
import fitz  # PyMuPDF
import easyocr
import numpy as np
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.schema import SDRReport
from extractor.text_extractor import _extract_khoj_osint_report, _extract_scaninfoga_report


def _fval(fields: dict, key: str, default: str = "") -> str:
    """Unwrap an ExtractedField to its raw string value, or return default."""
    f = fields.get(key)
    return f.value if f is not None else default


# EasyOCR reader is expensive to init — keep module-level singleton
_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _reader


def _pdf_page_to_image(pdf_path: str, page_number: int, dpi: int = 200) -> Image.Image:
    """Render a single PDF page to a PIL Image at given DPI."""
    doc = fitz.open(pdf_path)
    page = doc[page_number]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img_bytes = pix.tobytes("png")
    doc.close()
    return Image.open(io.BytesIO(img_bytes))


_LOW_QUALITY_CONF = 0.60   # avg confidence below this triggers DPI retry
_RETRY_DPI = 300


def _ocr_page(pdf_path: str, page_number: int, dpi: int = 200) -> tuple[str, float]:
    """
    Run EasyOCR on a single page.
    Returns (text, avg_confidence).
    """
    img = _pdf_page_to_image(pdf_path, page_number, dpi)
    img_array = np.array(img.convert("RGB"))
    reader = _get_reader()
    results = reader.readtext(img_array, detail=1, paragraph=False)
    if not results:
        return "", 0.0
    texts = [r[1] for r in results]
    confidences = [r[2] for r in results]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return "\n".join(texts), avg_conf


def extract_ocr_pdf(
    pdf_path: str,
    dpi: int = 200,
    max_workers: int = 4,
) -> SDRReport:
    """
    Extract a scanned SDR PDF using EasyOCR.
    """
    report = SDRReport(source_file=pdf_path, extraction_method="ocr")

    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()

    # pre-load model in main thread before spawning workers
    _get_reader()

    page_texts: dict[int, str] = {}
    page_confs: dict[int, float] = {}

    def ocr_page_thread(page_number: int, _dpi: int) -> tuple[int, str, float]:
        text, conf = _ocr_page(pdf_path, page_number, _dpi)
        return page_number, text, conf

    with ThreadPoolExecutor(max_workers=min(max_workers, page_count)) as executor:
        futures = {executor.submit(ocr_page_thread, i, dpi): i for i in range(page_count)}
        for future in as_completed(futures):
            page_num, text, conf = future.result()
            page_texts[page_num] = text
            page_confs[page_num] = conf

    # Retry low-quality pages at higher DPI
    avg_conf = sum(page_confs.values()) / len(page_confs) if page_confs else 1.0
    if avg_conf < _LOW_QUALITY_CONF and dpi < _RETRY_DPI:
        print(f"[ocr]   low confidence ({avg_conf:.2f}) — retrying at {_RETRY_DPI} DPI")
        with ThreadPoolExecutor(max_workers=min(max_workers, page_count)) as executor:
            futures = {
                executor.submit(ocr_page_thread, i, _RETRY_DPI): i
                for i in range(page_count)
            }
            for future in as_completed(futures):
                page_num, text, conf = future.result()
                page_texts[page_num] = text

    # reconstruct in page order
    ordered_texts = [page_texts[i] for i in range(page_count)]
    full_text = "\n".join(ordered_texts)

    # Detect report type and extract
    from extractor.text_extractor import _detect_report_type_from_content
    report_type = _detect_report_type_from_content(full_text)
    report.report_type = report_type

    if report_type == "khoj_osint":
        report = _extract_khoj_osint_report(report, full_text)
    elif report_type == "scaninfoga":
        report = _extract_scaninfoga_report(report, full_text)
    else:
        report.warnings.append(f"Unknown report type detected from OCR")

    return report