import fitz  # PyMuPDF
import easyocr
import numpy as np
from PIL import Image
import io
from concurrent.futures import ThreadPoolExecutor, as_completed

from models.schema import BankStatement, AccountInfo, Summary, Transaction, StatementPeriod
from extractor.normalizer import parse_amount, parse_date, detect_transaction_type, categorize, clean_text
from extractor.text_extractor import (
    _extract_header_fields,
    _parse_transactions_from_text,
    _recover_amounts_from_balance,
    _detect_balance_resets,
    _HEADER_LINE_LIMIT,
    _FOOTER_LINE_LIMIT,
)
from extractor.normalizer import ExtractedField, join_broken_lines, validate_statement

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
    FIX-15: Returns confidence so caller can retry at higher DPI for low-quality pages.
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
) -> BankStatement:
    """
    Extract a scanned/image PDF using EasyOCR.
    Pages are processed in parallel via ThreadPoolExecutor so all threads
    share the same EasyOCR model instance (avoids parallel model download conflicts).
    """
    statement = BankStatement(source_file=pdf_path, extraction_method="ocr")

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

    # FIX-15: Retry low-quality pages at higher DPI
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

    # Extract header and footer zones to prevent body text from contaminating header parsing
    lines = full_text.splitlines()
    header_zone = "\n".join(join_broken_lines(lines[:_HEADER_LINE_LIMIT]))
    footer_zone = "\n".join(join_broken_lines(lines[-_FOOTER_LINE_LIMIT:]))

    all_transactions: list[Transaction] = []
    opening_balance: float | None = None
    for page_text in ordered_texts:
        txns, ob = _parse_transactions_from_text(page_text)
        all_transactions.extend(txns)
        if ob is not None and opening_balance is None:
            opening_balance = ob

    fields = _extract_header_fields(full_text, source_file=pdf_path, header_zone=header_zone, footer_zone=footer_zone)

    hdr_opening = parse_amount(_fval(fields, "opening_balance"))
    hdr_closing = parse_amount(_fval(fields, "closing_balance"))
    if hdr_opening is not None:
        opening_balance = hdr_opening

    statement.account = AccountInfo(
        holder_name=_fval(fields, "holder_name") or None,
        account_number=_fval(fields, "account_number") or None,
        bank_name=_fval(fields, "bank_name") or None,
        statement_period=StatementPeriod(
            from_date=parse_date(_fval(fields, "from_date")),
            to_date=parse_date(_fval(fields, "to_date")),
        ),
    )

    # Sort then recover amounts/types (FIX-17: compute totals AFTER recovery)
    all_transactions.sort(
        key=lambda t: (t.date or __import__("datetime").date.min)
    )
    all_transactions = _recover_amounts_from_balance(all_transactions, opening_balance)

    # FIX-02 fallback: closing balance from last transaction
    if hdr_closing is None and all_transactions:
        hdr_closing = next(
            (t.balance for t in reversed(all_transactions) if t.balance is not None),
            None,
        )

    total_credits = sum(
        t.amount for t in all_transactions
        if t.type == "credit" and t.amount is not None
    )
    total_debits = sum(
        t.amount for t in all_transactions
        if t.type == "debit" and t.amount is not None
    )

    statement.summary = Summary(
        opening_balance=opening_balance,
        closing_balance=hdr_closing,
        total_credits=round(total_credits, 2),
        total_debits=round(total_debits, 2),
    )
    statement.transactions = all_transactions if all_transactions is not None else []
    statement.warnings = _detect_balance_resets(all_transactions, opening_balance) + validate_statement(statement)

    return statement
