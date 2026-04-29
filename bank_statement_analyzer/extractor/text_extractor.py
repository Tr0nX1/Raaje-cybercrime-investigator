import re
import pdfplumber
from pathlib import Path
from models.schema import BankStatement, AccountInfo, Summary, Transaction, StatementPeriod
from extractor.normalizer import (
    parse_amount, parse_date, detect_transaction_type, categorize, clean_text,
    normalize_raw_text, join_broken_lines, ExtractedField, MAX_AMOUNT_VALUE,
    validate_statement,
)


def _fval(fields: dict, key: str, default: str = "") -> str:
    """Unwrap an ExtractedField to its raw string value, or return default."""
    f = fields.get(key)
    return f.value if f is not None else default

# ── Constants ──────────────────────────────────────────────────────────────────

_HEADER_LINE_LIMIT = 40
_FOOTER_LINE_LIMIT = 60   # lines from END of document to search for closing balance

_AMOUNT_COL_MIN_SAMPLES = 3

# Two-char column keywords that appear mid-word in unrelated headers
# (e.g. "cr" in "des-cr-iption"). Require word boundaries for these.
_WORD_BOUNDARY_COL_KW = frozenset({"cr", "dr"})
_PAGE_DROP_THRESHOLD = 5


# ── RULE 1 helpers — strict monetary cell pattern ──────────────────────────────

_AMOUNT_CELL_RE = re.compile(r"^\s*(?:\d[\d,]*|\.)?\.\d{2}\s*$")


def _validate_amount_col(cells: list[str], sparse: bool = False) -> bool:  # noqa: ARG001
    non_empty = [c for c in cells if c and c.strip()]
    if len(non_empty) < _AMOUNT_COL_MIN_SAMPLES:
        return True
    valid = 0
    for c in non_empty:
        if not _AMOUNT_CELL_RE.match(c):
            continue
        try:
            if float(c.strip().replace(",", "")) <= MAX_AMOUNT_VALUE:
                valid += 1
        except ValueError:
            pass
    # Presence-based: accept any column with at least one valid amount cell.
    # The 70% threshold was rejecting sparse debit/credit columns and valid
    # balance columns that contain subtotals rows with text cells.
    return valid >= 1


def _validate_col_map(col: dict, data_rows: list[list]) -> dict:
    validated = dict(col)
    for field in ("debit", "credit", "balance"):
        idx = col.get(field)
        if idx is None:
            continue
        cells = [
            str(row[idx] or "").strip()
            for row in data_rows
            if row and idx < len(row)
        ]
        if not _validate_amount_col(cells, sparse=field in ("debit", "credit")):
            validated[field] = None
    return validated


# ── Header field patterns (RULE 7) ────────────────────────────────────────────
# FIX-17: Enhanced account holder name extraction with alternative field name variations
# Supports: customer name, account holder, account holder name, customer/account holder, etc.
_HOLDER_RE = re.compile(
    r"(?:customer\s*(?:name|details|account\s*holder)?|"
    r"account\s*(?:title|holder(?:\s*names?)?)?|"
    r"(?:account|customer)?\s*holder(?:\s*names?)?|"
    r"name\s*of\s*(?:account|customer)|a/c\s*(?:name|holder)|"
    r"acct\s*(?:name|holder)|member\s*name|"
    r"(?:account|acc)\s*name|"
    r"sole\s*proprietor|"
    r"account\s*details)\s*[:\-]?\s*"
    r"([A-Za-z][A-Za-z .&]{1,60})",
    re.IGNORECASE,
)
# Salutation-anchored: "Mr. ARJUN CHAUHAN" on its own line
_SALUTATION_RE = re.compile(
    r"^(?:Mr\.?|Mrs\.?|Ms\.?|M/S\.?|Dr\.)\s+([A-Z][A-Za-z .&]{2,50})\s*$",
    re.MULTILINE,
)
_ACCOUNT_RE = re.compile(
    r"(?:account\s*(?:no|number|#|id)|a/c\s*(?:no\.?|id)|customer\s*id|cust\s*id)\s*[:\-]?\s*([\dX*]{6,25})",
    re.IGNORECASE,
)

# FIX-03: Bank name searched in HEADER ZONE only, with expanded bank list.
# KKBK\d{7} matches the full Kotak IFSC code format (e.g. KKBK0003726) which
# appears in the "IFSC Code:" header line of Kotak statements.  Plain "KKBK"
# is intentionally NOT used — it would also match UPI narrations like
# "MA~KKBK~mattavishu@oki" that appear in other banks' statements.
_BANK_HEADER_RE = re.compile(
    r"((?:HDFC|SBI|ICICI|AXIS|KOTAK|KKBK\d{7}|PNB|BOB|YES\s*BANK|IDBI|CANARA|UNION|"
    r"DCB|INDUSIND|FEDERAL|RBL|BANDHAN|IOB|BOI|BANK\s+OF\s+(?:INDIA|BARODA|"
    r"MAHARASHTRA)|IDFC|KARNATAKA|SARASWAT\b|UCO|CENTRAL\s+BANK|EQUITAS)[^\n]{0,40})",
    re.IGNORECASE,
)

# Normalize raw regex match to a clean bank name — prevents address strings
# like "HDFCBANKLTD," or "IOBA/" from being stored as the bank name.
_BANK_CANONICAL: list[tuple[str, str]] = [
    ("HDFC", "HDFC Bank"),
    ("ICICI", "ICICI Bank"),
    ("STATE BANK OF INDIA", "SBI"),
    ("SBI", "SBI"),
    ("AXIS", "Axis Bank"),
    ("KOTAK", "Kotak Bank"),
    ("YES BANK", "YES Bank"),
    ("IDBI", "IDBI Bank"),
    ("CANARA", "Canara Bank"),
    ("UNION BANK", "Union Bank of India"),
    ("DCB", "DCB Bank"),
    ("INDUSIND", "IndusInd Bank"),
    ("FEDERAL", "Federal Bank"),
    ("RBL", "RBL Bank"),
    ("BANDHAN", "Bandhan Bank"),
    ("BANK OF INDIA", "Bank of India"),
    ("BOI", "Bank of India"),
    ("BANK OF BARODA", "Bank of Baroda"),
    ("BOB", "Bank of Baroda"),
    ("BANK OF MAHARASHTRA", "Bank of Maharashtra"),
    ("PNB", "Punjab National Bank"),
    ("IDFC", "IDFC First Bank"),
    ("IOB", "Indian Overseas Bank"),
    ("KARNATAKA", "Karnataka Bank"),
    ("SARASWAT", "Saraswat Bank"),
    ("UCO", "UCO Bank"),
    ("CENTRAL BANK", "Central Bank of India"),
    ("KKBK", "Kotak Bank"),
    ("EQUITAS", "Equitas Small Finance Bank"),
]


def _normalize_bank_name(raw: str) -> str:
    up = raw.upper()
    for key, canonical in _BANK_CANONICAL:
        if key in up:
            return canonical
    return raw.strip()

# FIX-14: Period date patterns — extended to handle dot-separated and month-name dates
_DATE_PART = r"(\d{1,2}[\-/.]\d{1,2}[\-/.]\d{2,4}|\d{1,2}\s+\w{3,9}\s+\d{2,4})"
_PERIOD_RE = re.compile(
    r"(?:period|statement\s*period)\s*[:\-]\s*" + _DATE_PART + r"\s+(?:to|TO)\s+" + _DATE_PART,
    re.IGNORECASE,
)
_FROM_DATE_RE = re.compile(
    r"(?:statement\s*from|from\s*date|from)\s*[:\-]\s*" + _DATE_PART,
    re.IGNORECASE,
)
_TO_DATE_RE = re.compile(
    r"(?:statement\s*to|to\s*date)\s*[:\-]\s*" + _DATE_PART,
    re.IGNORECASE,
)
# FIX-14: Filename date range — e.g. "924020060238644-08-10-2024to19-09-2025"
_FILENAME_DATE_RANGE_RE = re.compile(
    r"(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*(?:to|TO)\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
)

# FIX-04: All-caps standalone name pattern (2+ words, uppercase only, no digits)
_ALLCAPS_NAME_RE = re.compile(r"^[A-Z][A-Z .&]{5,49}$")
# FIX-16: Expanded Opening Balance patterns (B/F, Previous Balance, Op Bal)
_OPENING_BAL_RE = re.compile(
    r"(?:opening\s*balance|balance\s*b/?f|prev(?:ious)?\s*balance|op(?:\s*ening)?\s*bal)\s*[:\-]?\s*(\.?\d[\d,.]*)",
    re.IGNORECASE,
)

# FIX-02: Closing balance patterns — more label variants
_CLOSING_BAL_RE = re.compile(
    r"(?:closing\s*balance|balance\s*c/?f|balance\s*carried\s*forward|"
    r"c/?f\s*balance|final\s*balance|closing\s*bal|cl(?:\s*osing)?\s*bal)\s*[:\-]?\s*(\.?\d[\d,.]*)",
    re.IGNORECASE,
)


def _extract_header_fields(
    full_text: str,
    source_file: str = "",
    header_zone: str = "",
    footer_zone: str = "",
) -> dict[str, ExtractedField]:
    """
    RULE 7 — Safe header extraction.
    Returns dict[str, ExtractedField] — every value carries confidence + method.
    FIX-02: closing_balance searched in footer (last 60 lines) + fallback to last txn balance.
    FIX-03: bank_name restricted to header zone.
    FIX-04: holder_name patterns expanded.
    FIX-14: period date patterns expanded.
    header_zone / footer_zone: coordinate-cropped text from split_page_zones(); when
    provided these replace the line-count slices so text-density variance doesn't
    bleed transaction rows into the header search space.
    """
    lines = full_text.splitlines()
    header_text = (
        header_zone if header_zone
        else "\n".join(join_broken_lines(lines[:_HEADER_LINE_LIMIT]))
    )
    footer_text = (
        footer_zone if footer_zone
        else "\n".join(join_broken_lines(lines[-_FOOTER_LINE_LIMIT:]))
    )

    fields: dict[str, ExtractedField] = {}

    def _set(key: str, value: str, confidence: float, method: str) -> None:
        fields[key] = ExtractedField(value=value, confidence=confidence, method=method)

    # Account number — full document, unique format
    m = _ACCOUNT_RE.search(full_text)
    if m:
        _set("account_number", m.group(1).strip(), 0.90, "label_regex")

    # FIX-03: Bank name — filename is checked FIRST (higher confidence than regex).
    _FILENAME_BANK = [
        ("BOM_", "Bank of Maharashtra"),
        ("BANK OF MAHARASHTRA", "Bank of Maharashtra"),
        ("UNIPIN", "Axis Bank"),
        ("INDUSIND", "IndusInd Bank"),
        ("FEDERAL", "Federal Bank"),
        ("CANARA", "Canara Bank"),
        ("ICICI", "ICICI Bank"),
        ("KOTAK", "Kotak Bank"),
        ("HDFC", "HDFC Bank"),
        ("AXIS", "Axis Bank"),
        ("IDBI", "IDBI Bank"),
        ("YES", "YES Bank"),
        ("PNB", "Punjab National Bank"),
        ("BOB", "Bank of Baroda"),
        ("BOI", "Bank of India"),
        ("DCB", "DCB Bank"),
        ("SBI", "SBI"),
    ]
    if source_file:
        basename_up = Path(source_file).name.upper()
        stem_up = Path(source_file).stem.upper()
        for kw, name in _FILENAME_BANK:
            if basename_up.startswith(kw) or re.search(r'\b' + re.escape(kw) + r'\b', stem_up):
                _set("bank_name", name, 0.95, "filename")
                break

    # FIX-03: Bank name from HEADER ZONE if filename didn't provide it
    if not fields.get("bank_name"):
        m = _BANK_HEADER_RE.search(header_text)
        if m:
            _set("bank_name", _normalize_bank_name(m.group(1).strip()), 0.80, "header_regex")

    # Holder name — label-anchored first
    m = _HOLDER_RE.search(header_text)
    if m:
        name = m.group(1).strip()
        if len(name) >= 3 and not re.search(r"\d", name):
            _set("holder_name", name, 0.90, "label_regex")

    # BOM-style: "Account Holder Names Mr. ANKIT UIKEY" (space separator, no colon)
    _LABEL_TERM_RE = re.compile(
        r"\b(Primary|Nominee|CIF|GSTIN|Mobile|Email|KYC|Address|CKYC)\b",
        re.IGNORECASE,
    )
    if not fields.get("holder_name"):
        m = re.search(
            r"account\s*holder\s*names?\s+([A-Z][A-Za-z .&]{2,60})",
            header_text, re.IGNORECASE,
        )
        if m:
            name = m.group(1).strip()
            end = _LABEL_TERM_RE.search(name)
            if end:
                name = name[:end.start()].strip()
            if len(name) >= 3 and not re.search(r"\d", name):
                _set("holder_name", name, 0.85, "label_regex_bom")

    # Salutation fallback
    if not fields.get("holder_name"):
        m = _SALUTATION_RE.search(header_text)
        if m:
            _set("holder_name", m.group(0).strip(), 0.80, "salutation_regex")

    # FIX-17: Additional fallback patterns for alternative field names
    # Pattern: "Customer: NAME" or "Holder: NAME" or "Account Holder: NAME"
    if not fields.get("holder_name"):
        m = re.search(
            r"(?:customer|holder|account\s+holder|account\s+holder\s+name)[\s:]*?\s+([A-Z][A-Za-z .&]{2,60})(?=\s|$|\n)",
            header_text, re.IGNORECASE,
        )
        if m:
            name = m.group(1).strip()
            if len(name) >= 3 and not re.search(r"\d", name):
                _set("holder_name", name, 0.82, "alt_field_regex")

    # Pattern: "Customer Name:" or "Account Holder:" without trailing punctuation
    if not fields.get("holder_name"):
        m = re.search(
            r"(?:customer\s+name|account\s+holder)\s*[:]\s*([A-Za-z][A-Za-z .&]{2,60})",
            header_text, re.IGNORECASE,
        )
        if m:
            name = m.group(1).strip()
            if len(name) >= 3 and not re.search(r"\d", name):
                _set("holder_name", name, 0.81, "alt_colon_regex")

    # FIX-04: All-caps heuristic — standalone line in first 20 lines
    _INSTITUTION_WORDS = frozenset({
        "BANK", "LTD", "LIMITED", "BRANCH", "FINANCE", "INSTITUTE",
        "STATEMENT", "STATEMENTS", "ACCOUNT", "ACCOUNTS", "FACILITY",
        "SWEEP", "DETAIL", "DETAILS", "OPERATIVE", "COMBINED", "REPORT",
        "TRANSACTION", "TRANSACTIONS",
    })
    bank_upper = _fval(fields, "bank_name").upper()
    bank_line_idx = -1
    if bank_upper:
        for _i, _ln in enumerate(lines[:20]):
            if bank_upper in _ln.strip().upper():
                bank_line_idx = _i
                break
    if not fields.get("holder_name"):
        for i, line in enumerate(lines[:20]):
            if bank_line_idx >= 0 and abs(i - bank_line_idx) <= 4:
                continue
            stripped = line.strip()
            words = stripped.split()
            if (6 <= len(stripped) <= 50 and
                    _ALLCAPS_NAME_RE.match(stripped) and
                    not re.search(r"\d", stripped) and
                    len(words) >= 2 and
                    all(sum(1 for c in w if c.isalpha()) >= 3 for w in words) and
                    not any(w in _INSTITUTION_WORDS for w in words) and
                    stripped.upper() != bank_upper):
                _set("holder_name", stripped, 0.70, "allcaps_heuristic")
                break

    # Date range — header zone only
    m = _PERIOD_RE.search(header_text)
    if m:
        _set("from_date", m.group(1).strip(), 0.90, "period_regex")
        _set("to_date",   m.group(2).strip(), 0.90, "period_regex")
    else:
        m = _FROM_DATE_RE.search(header_text)
        if m:
            _set("from_date", m.group(1).strip(), 0.85, "from_date_regex")
        m = _TO_DATE_RE.search(header_text)
        if m:
            _set("to_date", m.group(1).strip(), 0.85, "to_date_regex")

    # FIX-14 fallback: date range from filename
    if source_file and (not fields.get("from_date") or not fields.get("to_date")):
        stem = Path(source_file).stem
        m = _FILENAME_DATE_RANGE_RE.search(stem)
        if m:
            if not fields.get("from_date"):
                _set("from_date", m.group(1), 0.75, "filename_date")
            if not fields.get("to_date"):
                _set("to_date", m.group(2), 0.75, "filename_date")

    # Opening balance — header zone
    m = _OPENING_BAL_RE.search(header_text)
    if m:
        _set("opening_balance", m.group(1).strip(), 0.90, "label_regex")

    # FIX-02: Closing balance — footer first, then header
    m = _CLOSING_BAL_RE.search(footer_text)
    if m:
        _set("closing_balance", m.group(1).strip(), 0.85, "footer_regex")
    else:
        m = _CLOSING_BAL_RE.search(header_text)
        if m:
            _set("closing_balance", m.group(1).strip(), 0.90, "header_regex")

    return fields


# ── Table row helpers ──────────────────────────────────────────────────────────

_DATE_CELL_RE = re.compile(
    r"^\d{1,2}[\/\-](?:\d{1,2}|\w{3,9})[\/\-]\d{2,4}$"
    r"|^\d{1,2}\s+\w{3,9}\s+\d{2,4}$",
    re.IGNORECASE,
)
_DATE_ROW_RE = re.compile(
    r"^(\d{1,2}[\/\-](?:\d{1,2}|\w{3,9})[\/\-]\d{2,4}"
    r"|\d{1,2}\s+\w{3,9}\s+\d{2,4})",
    re.MULTILINE,
)
_AMOUNT_LINE_RE = re.compile(r"\d[\d,]*\.\d{2}")
_DR_CR_SUFFIX_RE = re.compile(r"(\d[\d,]*\.\d{2})\s*([Dd][Rr]|[Cc][Rr])\b")

# FIX-07: Extended B/F pattern to also match "Opening Balance" prefix
_BF_RE = re.compile(r"^(?:B/?F\b|BROUGHT\s+FORWARD|OPENING\s+BALANCE)", re.IGNORECASE)

# Summary/footer rows that should be silently skipped (not stored as transactions)
_SUMMARY_ROW_RE = re.compile(
    r"^(?:CLOSING\s+(?:BALANCE|BAL)|TOTAL\s+(?:DEBIT|CREDIT|AMOUNT|TXN|TRANSACTION)|"
    r"STATEMENT\s+SUMMARY|GRAND\s+TOTAL|NET\s+(?:BALANCE|AMOUNT)|BALANCE\s+C/?F)",
    re.IGNORECASE,
)


def _is_header_row(row: list) -> bool:
    first = str(row[0] or "").strip()
    return bool(first) and not _DATE_CELL_RE.match(first)


def _find_col(header: list[str], candidates: list[str]) -> int | None:
    for candidate in candidates:
        for i, h in enumerate(header):
            if candidate in _WORD_BOUNDARY_COL_KW:
                # "cr" matches des-cr-iption; "dr" matches with-dr-aws.
                # Require a word boundary so these only match standalone tokens.
                if re.search(r"(?<!\w)" + re.escape(candidate) + r"(?!\w)", h):
                    return i
            else:
                if candidate in h:
                    return i
    return None


def _detect_col_map(header: list[str]) -> dict:
    return {
        "date":    _find_col(header, ["date", "tran date", "txn date", "value date", "trans date"]),
        "desc":    _find_col(header, ["description", "narration", "particulars", "details", "remarks"]),
        "debit":   _find_col(header, ["debit", "dr", "withdrawal", "withdrawals", "withdraws", "withdraw", "dr amount", "debit amount"]),
        "credit":  _find_col(header, ["credit", "cr", "deposit", "cr amount", "credit amount", "deposits"]),
        "balance": _find_col(header, ["balance", "bal", "running balance", "effective balance"]),
    }


# ── RULE 5 + RULE 6 — row-to-transaction conversion ───────────────────────────

def _rows_to_transactions(
    rows: list[list],
    col: dict,
) -> tuple[list[Transaction], float | None]:
    transactions: list[Transaction] = []
    opening_balance: float | None = None

    def cell(idx: int | None, _row: list = None) -> str:
        if idx is None or _row is None or idx >= len(_row):
            return ""
        return str(_row[idx] or "").strip()

    for row in rows:
        if not row or all(c is None or str(c).strip() == "" for c in row):
            continue

        raw_date = cell(col["date"], row)

        # RULE 5 — no date: continuation of the previous transaction
        if not raw_date or not re.search(r"\d", raw_date):
            if transactions and col.get("desc") is not None:
                extra = clean_text(cell(col["desc"], row))
                if extra:
                    transactions[-1].description += "\n" + extra
            continue

        desc_raw = cell(col["desc"], row)
        desc = clean_text(desc_raw)

        # FIX-07/RULE 6 — B/F / Opening Balance row
        if _BF_RE.match(desc):
            bal = parse_amount(cell(col["balance"], row))
            if bal is None:
                bal = parse_amount(desc_raw)
            if bal is not None and opening_balance is None:
                opening_balance = bal
            continue

        # Skip statement summary rows (Closing Balance, Total Debit/Credit, etc.)
        if _SUMMARY_ROW_RE.match(desc):
            continue

        tx_type, amount = detect_transaction_type(
            cell(col["debit"],   row),
            cell(col["credit"],  row),
            desc,
        )

        transactions.append(Transaction(
            date=parse_date(raw_date),
            description=desc,
            type=tx_type,
            amount=amount,
            balance=parse_amount(cell(col["balance"], row)),
            category=categorize(desc),
            # Track which amount columns were available in the source for validation
            has_debit_col=col.get("debit") is not None,
            has_credit_col=col.get("credit") is not None,
            raw_text=" | ".join(str(c).strip() for c in row if c and str(c).strip())
        ))

    # FIX-13 post-processing: retroactively detect B/F if the description of
    # the first transaction starts with a B/F pattern (can happen when B/F is
    # on a continuation row that got appended to the previous date row).
    for i, tx in enumerate(transactions[:3]):
        if _BF_RE.match(tx.description):
            bal = tx.balance if tx.balance is not None else parse_amount(tx.description)
            if bal is not None and opening_balance is None:
                opening_balance = bal
            transactions.pop(i)
            break

    return transactions, opening_balance


# ── RULE 1 — table parser with column validation ───────────────────────────────

# FIX-12: Keywords that appear in legitimate column-header rows.
# Title rows ("ACCOUNT STATEMENT", "CUSTOMER DETAILS") won't have these.
_COL_KW = frozenset({
    "date", "tran", "txn", "narration", "description", "particulars",
    "debit", "credit", "deposit", "withdrawal", "withdrawals", "deposits",
    "balance", "amount", "dr", "cr", "cheque", "chq", "remarks", "details",
})


def _find_header_row(table: list[list]) -> int | None:
    """
    Scan first 5 rows for a non-date row that contains at least one
    recognizable column keyword.  Title rows (e.g. "ACCOUNT STATEMENT")
    are skipped so the actual column-label row is selected.
    FIX-12: Extending to 5 rows and requiring column keywords prevents
    Canara Bank title rows from being mistaken for header rows.
    """
    for i, row in enumerate(table[:5]):
        if not row:
            continue
        first = str(row[0] or "").strip()
        if not first:
            continue
        if _DATE_CELL_RE.match(first):
            continue  # data row
        if re.search(r"\d{6,}", first):
            continue  # account number / long ref
        row_text = " ".join(str(c or "").lower() for c in row)
        if any(kw in row_text for kw in _COL_KW):
            return i
    return None


def _parse_transactions_from_table(
    table: list[list],
    saved_col: dict | None = None,
) -> tuple[list[Transaction], dict | None, float | None]:
    if not table:
        return [], saved_col, None

    hdr_idx = _find_header_row(table)

    if hdr_idx is not None:
        header = [str(c).lower().strip() if c else "" for c in table[hdr_idx]]
        col = _detect_col_map(header)
        data_rows = table[hdr_idx + 1:]
        col = _validate_col_map(col, data_rows)
    elif saved_col is not None:
        col = saved_col
        data_rows = table
    else:
        return [], saved_col, None

    txns, opening_balance = _rows_to_transactions(data_rows, col)
    return txns, col, opening_balance


# ── Text-fallback parser (when pdfplumber finds no table) ─────────────────────

def _parse_transactions_from_text(page_text: str) -> tuple[list[Transaction], float | None]:
    """
    Last-resort: parse transactions from raw text.
    FIX: Now also returns opening_balance (extracted from B/F non-date lines).
    Returns (transactions, opening_balance_or_None).
    """
    transactions: list[Transaction] = []
    opening_balance: float | None = None
    lines = page_text.splitlines()
    pending_desc: str = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line or len(line) < 3:
            continue

        if not _DATE_ROW_RE.match(line):
            # FIX-13: Non-date line that is a B/F marker → capture opening balance
            if _BF_RE.match(line.strip()):
                bal = parse_amount(line)
                if bal is not None and opening_balance is None:
                    opening_balance = bal
                pending_desc = ""
            elif _SUMMARY_ROW_RE.match(line.strip()):
                pending_desc = ""  # skip summary lines (Closing Balance, etc.)
            else:
                pending_desc = line
            continue

        amounts = _AMOUNT_LINE_RE.findall(line)
        if not amounts:
            pending_desc = line
            continue

        parts     = line.split()
        raw_date  = parts[0]
        balance   = parse_amount(amounts[-1])
        tx_raw    = amounts[-2] if len(amounts) >= 2 else amounts[0]
        tx_amount = parse_amount(tx_raw)

        # If pending_desc is a B/F line, use it as opening_balance, not description
        if pending_desc and _BF_RE.match(pending_desc.strip()):
            bal = parse_amount(pending_desc)
            if bal is not None and opening_balance is None:
                opening_balance = bal
            pending_desc = ""

        first_amt_pos = line.index(amounts[0])
        inline_desc   = clean_text(line[len(raw_date):first_amt_pos])
        desc          = clean_text(pending_desc) if pending_desc else inline_desc
        pending_desc  = ""

        m = _DR_CR_SUFFIX_RE.search(line)
        if m and m.group(1) == tx_raw:
            tx_type = "debit" if m.group(2).lower() == "dr" else "credit"
        else:
            tx_type, _ = detect_transaction_type("", "", desc)

        transactions.append(Transaction(
            date=parse_date(raw_date),
            description=desc,
            type=tx_type,
            amount=tx_amount,
            balance=balance,
            category=categorize(desc),
            raw_text=line,
        ))

    return transactions, opening_balance


# ── Pipe-delimited text parser (Bank of India format) ─────────────────────────

_PIPE_DATE_RE = re.compile(r"^\|\s*(\d{2}-\d{2}-\d{4})\s*\|")
_BAL_CR_DR_RE = re.compile(r"([\d,]+\.\d{2})\s*([Cc][Rr]|[Dd][Rr])")


def _is_pipe_format(page_text: str) -> bool:
    """Detect Bank of India / pipe-delimited format."""
    pipe_lines = sum(1 for ln in page_text.splitlines() if ln.strip().startswith("|") and "|" in ln[1:])
    return pipe_lines >= 3


def _parse_transactions_from_pipe_text(page_text: str) -> tuple[list[Transaction], float | None]:
    """Parse pipe-delimited Bank of India format."""
    transactions: list[Transaction] = []
    opening_balance: float | None = None

    # Merge continuation lines: lines that don't start with | get appended to previous
    merged_lines: list[str] = []
    for raw in page_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("|"):
            merged_lines.append(line)
        elif merged_lines:
            merged_lines[-1] += " " + line

    for line in merged_lines:
        m = _PIPE_DATE_RE.match(line)
        if not m:
            # Check for B/F / Opening Balance row in pipe format:
            # e.g. |B/F | | | | | | | 2,30,429.96 Cr |
            raw_parts = [p.strip() for p in line.split("|")]
            raw_parts = [p for p in raw_parts if p]
            if raw_parts and _BF_RE.match(raw_parts[0]):
                for p in reversed(raw_parts):
                    bal = parse_amount(p)
                    if bal is not None:
                        if opening_balance is None:
                            opening_balance = bal
                        break
            continue
        raw_date = m.group(1)
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p != ""]  # remove empty boundary parts

        # parts[0] = date, parts[1] = narration, rest = amounts
        if len(parts) < 3:
            continue

        desc = clean_text(parts[1]) if len(parts) > 1 else ""

        # B/F check
        if _BF_RE.match(desc):
            # Extract balance from the last part
            for p in reversed(parts[2:]):
                bal = parse_amount(p)
                if bal is not None:
                    if opening_balance is None:
                        opening_balance = bal
                    break
            continue

        # Find balance: scan ALL parts from the end for a Cr/Dr-suffixed value.
        # Continuation text appended after the last | can displace parts[-1],
        # so we must search the entire parts list rather than just the last element.
        balance: float | None = None
        tx_type = "unknown"
        amount: float | None = None
        balance_idx = -1

        for j, p in enumerate(parts):
            m_bal = _BAL_CR_DR_RE.search(p)
            if m_bal:
                balance = parse_amount(m_bal.group(1))
                balance_idx = j  # track so we can exclude it from amount_parts

        if balance is None:
            # Fallback: last part that contains any monetary value (no Cr/Dr suffix)
            for j in range(len(parts) - 1, 1, -1):
                val = parse_amount(parts[j])
                if val is not None and val > 0:
                    balance = val
                    balance_idx = j
                    break

        # Amount: first non-zero value in columns between narration and balance
        amount_parts = parts[2:balance_idx] if balance_idx > 2 else (parts[2:-1] if len(parts) > 2 else [])
        for p in amount_parts:
            val = parse_amount(p)
            if val is not None and val > 0:
                amount = val
                break

        # Infer type from keywords; balance-recovery will refine
        tx_type, _ = detect_transaction_type("", "", desc)

        transactions.append(Transaction(
            date=parse_date(raw_date),
            description=desc,
            type=tx_type,
            amount=amount,
            balance=balance,
            category=categorize(desc),
            raw_text=line,
        ))

    return transactions, opening_balance


# ── RULE 4 — Balance-based amount recovery ─────────────────────────────────────

def _recover_amounts_from_balance(
    transactions: list[Transaction],
    opening_balance: float | None,
) -> list[Transaction]:
    """
    RULE 4 — Recover missing amounts and infer types from balance movement.
    FIX-06: Also infers type from balance delta for transactions that have an
    amount already but type='unknown' (e.g. single-column amount formats).
    """
    prev_balance = opening_balance

    for tx in transactions:
        if tx.balance is not None and prev_balance is not None:
            delta = tx.balance - prev_balance

            if tx.amount is None:
                if delta != 0.0:
                    tx.amount = round(abs(delta), 2)
                    if tx.type == "unknown":
                        tx.type = "credit" if delta > 0 else "debit"
                else:
                    tx.amount = 0.0

            elif tx.type == "unknown" and delta != 0.0:
                # FIX-06: amount is set but type is unknown — infer from balance direction
                tx.type = "credit" if delta > 0 else "debit"

        if tx.balance is not None:
            prev_balance = tx.balance

    return transactions


# ── FIX-08 — Multi-account balance reset detection ────────────────────────────

def _detect_balance_resets(
    transactions: list[Transaction],
    opening_balance: float | None,
) -> list[str]:
    """
    FIX-08: Detect DCB-style consolidated statements where multiple sub-accounts
    are concatenated, causing abrupt small balance resets after large balances.
    Returns warning strings; does NOT split transactions (avoids false positives).
    """
    warnings: list[str] = []
    prev_balance = opening_balance

    for i, tx in enumerate(transactions):
        if tx.balance is not None and prev_balance is not None and prev_balance > 5_000:
            # A reset is: new balance is <10% of previous AND absolutely small (<1000)
            if tx.balance < prev_balance * 0.1 and tx.balance < 1_000:
                warnings.append(
                    f"Balance reset at transaction {i + 1} on {tx.date} "
                    f"({prev_balance:.2f} → {tx.balance:.2f}) — "
                    f"possible multi-account consolidated statement segment boundary."
                )
        if tx.balance is not None:
            prev_balance = tx.balance

    return warnings


# ── RULE 9 — Page completeness check ──────────────────────────────────────────

def _check_page_completeness(
    page_stats: list[dict],
    total_pages: int,
) -> list[str]:
    warnings: list[str] = []
    processed = len(page_stats)
    if processed < total_pages:
        warnings.append(
            f"Only {processed} of {total_pages} pages produced output — "
            f"{total_pages - processed} page(s) may have been skipped."
        )
    for i in range(1, len(page_stats)):
        prev = page_stats[i - 1]
        curr = page_stats[i]
        if prev["tx_count"] >= _PAGE_DROP_THRESHOLD and curr["tx_count"] == 0:
            warnings.append(
                f"Page {curr['page']}: 0 transactions detected after "
                f"{prev['tx_count']} on page {prev['page']} — "
                f"possible missing or blank page."
            )
    return warnings


# ── Positional page zone splitter ─────────────────────────────────────────────

def split_page_zones(
    page,
    header_pct: float = 0.20,
    footer_pct: float = 0.12,
) -> dict[str, str]:
    """
    Split a pdfplumber page into header/body/footer using PDF point-space Y
    coordinates via page.crop().  Zones are defined as fractions of page height,
    not line counts.
    Returns {'header': str, 'body': str, 'footer': str}.
    """
    w = float(page.width)
    h = float(page.height)
    header_bottom = h * header_pct
    footer_top    = h * (1.0 - footer_pct)

    def _zone(y0: float, y1: float) -> str:
        return normalize_raw_text(page.crop((0, y0, w, y1)).extract_text() or "")

    return {
        "header": _zone(0,             header_bottom),
        "body":   _zone(header_bottom, footer_top),
        "footer": _zone(footer_top,    h),
    }


# ── Typographic name heuristic ────────────────────────────────────────────────

# Words that disqualify a header line from being an account holder name.
_NAME_STOP_WORDS = frozenset({
    "BANK", "LTD", "LIMITED", "BRANCH", "FINANCE", "INSTITUTE",
    "STATEMENT", "STATEMENTS", "ACCOUNT", "ACCOUNTS", "FACILITY",
    "SWEEP", "DETAIL", "DETAILS", "OPERATIVE", "COMBINED", "REPORT",
    "TRANSACTION", "TRANSACTIONS", "PERIOD", "DATE", "FROM", "TO",
    "CUSTOMER", "HOLDER", "NAME", "NUMBER", "BALANCE", "OPENING",
    "CLOSING", "TOTAL", "DEBIT", "CREDIT", "PAGE", "SUMMARY",
    # Bank brand identifiers that appear in large header fonts
    "HDFC", "ICICI", "AXIS", "KOTAK", "CANARA", "INDUSIND",
    "FEDERAL", "BANDHAN", "EQUITAS", "SARASWAT", "IDFC", "RBL",
})

# Font-name substrings that indicate bold weight.
_BOLD_TOKENS = ("Bold", "bold", "-Bd", "-BD", "BoldMT", "Heavy", "Black", "Demi")

# Broad character-set for names: letters, space, dot, ampersand, apostrophe, hyphen.
_NAME_VALID_RE = re.compile(r"^[A-Za-z][A-Za-z .&'/\-]{1,58}$")


def _score_line_chars(chars: list[dict]) -> float:
    if not chars:
        return 0.0
    avg_size = sum(c.get("size", 0) for c in chars) / len(chars)
    fontnames = " ".join(c.get("fontname") or "" for c in chars)
    bold_bonus = 1.25 if any(tok in fontnames for tok in _BOLD_TOKENS) else 1.0
    return avg_size * bold_bonus


def _is_valid_name_candidate(text: str) -> bool:
    if not _NAME_VALID_RE.match(text):
        return False
    if re.search(r"\d", text):
        return False
    words = text.split()
    if not (2 <= len(words) <= 6):
        return False
    upper_words = {w.upper().strip(".&'/") for w in words}
    if upper_words & _NAME_STOP_WORDS:
        return False
    # Require at least one purely-alphabetic word of 3+ chars (screens "A/C & CO.")
    if not any(w.isalpha() and len(w) >= 3 for w in words):
        return False
    return True


def detect_holder_name_heuristic(page) -> str | None:
    """
    Fallback holder_name detection via typographic scoring.
    Uses pdfplumber char metadata (font size, boldness) to rank lines in the
    top 30% of the first page by visual prominence, then returns the
    highest-scoring line that passes name-validity checks.
    Only called when all label-anchored patterns in _extract_header_fields fail.
    """
    chars = page.chars
    if not chars:
        return None

    zone_bottom = float(page.height) * 0.30
    header_chars = [
        c for c in chars
        if c.get("top", 0) < zone_bottom and c.get("text", "").strip()
    ]
    if not header_chars:
        return None

    # Group chars into logical lines using 3pt Y buckets.
    lines_map: dict[int, list[dict]] = {}
    for c in header_chars:
        key = int(c["top"] / 3)
        lines_map.setdefault(key, []).append(c)

    candidates: list[tuple[float, str]] = []

    for key in sorted(lines_map):
        line_chars = sorted(lines_map[key], key=lambda c: c["x0"])

        # Reconstruct line text; insert space when inter-char X gap exceeds 4pt.
        parts: list[str] = []
        prev_x1: float | None = None
        for c in line_chars:
            ch = c.get("text", "")
            if not ch:
                continue
            x0 = c["x0"]
            if prev_x1 is not None and (x0 - prev_x1) > 4.0:
                parts.append(" ")
            parts.append(ch)
            prev_x1 = c.get("x1", x0 + c.get("width", 4.0))

        line_text = "".join(parts).strip()
        if not line_text:
            continue

        candidates.append((_score_line_chars(line_chars), line_text))

    candidates.sort(key=lambda x: -x[0])

    for _, text in candidates:
        if _is_valid_name_candidate(text):
            return text

    return None


# ── Main extractor ─────────────────────────────────────────────────────────────

def extract_text_pdf(pdf_path: str) -> BankStatement:
    statement = BankStatement(source_file=pdf_path, extraction_method="text")
    all_transactions: list[Transaction] = []
    full_text_parts:  list[str] = []
    page_stats:       list[dict] = []

    saved_col:       dict | None  = None
    opening_balance: float | None = None
    heuristic_name:  str | None   = None
    page_0_header:   str          = ""
    last_page_footer: str         = ""

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages):
            page_text = normalize_raw_text(page.extract_text() or "")
            full_text_parts.append(page_text)

            if page_num == 0:
                heuristic_name = detect_holder_name_heuristic(page)
                page_0_header = split_page_zones(page)["header"]

            if page_num == total_pages - 1:
                last_page_footer = split_page_zones(page)["footer"]

            page_txns: list[Transaction] = []
            found_table = False

            for table in page.extract_tables():
                txns, saved_col, ob = _parse_transactions_from_table(table, saved_col)
                if txns:
                    page_txns.extend(txns)
                    found_table = True
                if ob is not None and opening_balance is None:
                    opening_balance = ob

            if not found_table and page_text:
                if _is_pipe_format(page_text):
                    txns, ob = _parse_transactions_from_pipe_text(page_text)
                else:
                    txns, ob = _parse_transactions_from_text(page_text)
                page_txns.extend(txns)
                if ob is not None and opening_balance is None:
                    opening_balance = ob

            all_transactions.extend(page_txns)
            page_stats.append({"page": page_num + 1, "tx_count": len(page_txns)})

    full_text = "\n".join(full_text_parts)

    # RULE 7 — safe header extraction (FIX-02, FIX-03, FIX-04, FIX-14 applied inside)
    fields = _extract_header_fields(
        full_text,
        source_file=pdf_path,
        header_zone=page_0_header,
        footer_zone=last_page_footer,
    )

    # Typographic fallback — only when all label-anchored patterns returned null
    if not fields.get("holder_name") and heuristic_name:
        fields["holder_name"] = ExtractedField(heuristic_name, 0.65, "typographic_heuristic")

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

    # Drop completely empty rows (no date, no amount, no description)
    all_transactions = [
        t for t in all_transactions
        if t.date is not None or (t.amount is not None and t.amount > 0) or len(t.description) > 2
    ]

    # Sort, then recover amounts (RULE 4 requires chronological order)
    all_transactions.sort(
        key=lambda t: (t.date or __import__("datetime").date.min)
    )
    all_transactions = _recover_amounts_from_balance(all_transactions, opening_balance)

    # FIX-02 fallback: if still no closing balance, use last transaction's balance
    if hdr_closing is None and all_transactions:
        last_bal = next(
            (t.balance for t in reversed(all_transactions) if t.balance is not None),
            None,
        )
        hdr_closing = last_bal

    # Summary — compute AFTER type recovery so totals are accurate
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
    statement.transactions = all_transactions

    # FIX-08: Check for DCB-style multi-account balance resets
    reset_warnings = _detect_balance_resets(all_transactions, opening_balance)

    # Confidence warnings — surface fields extracted by low-confidence methods
    _CONF_THRESHOLD = 0.70
    conf_warnings = [
        f"Low confidence ({f.confidence:.0%}) on '{k}' "
        f"[method: {f.method}] — verify manually"
        for k, f in fields.items()
        if f.confidence < _CONF_THRESHOLD
    ]

    statement.warnings = (
        _check_page_completeness(page_stats, total_pages)
        + reset_warnings
        + conf_warnings
        + validate_statement(statement)
    )

    return statement


def extract_mixed_pdf(pdf_path: str, ocr_dpi: int = 200, ocr_workers: int = 4) -> BankStatement:
    """
    Per-page hybrid extraction for mixed PDFs (text + scanned pages).
    Each page is extracted ONCE using only the appropriate method.
    """
    from extractor.ocr_extractor import _ocr_page
    from extractor.normalizer import normalize_raw_text as norm_text

    statement = BankStatement(source_file=pdf_path, extraction_method="mixed")
    all_transactions: list[Transaction] = []
    full_text_parts: list[str] = []
    page_stats: list[dict] = []

    saved_col: dict | None = None
    opening_balance: float | None = None
    heuristic_name: str | None = None
    all_header_fields: dict[str, ExtractedField] = {}
    page_0_header: str = ""
    last_page_footer: str = ""

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages):
            page_text = normalize_raw_text(page.extract_text() or "")
            full_text_parts.append(page_text)

            # Per-page detection: is this page text or scanned?
            is_text_page = len(page_text.strip()) >= 50

            page_txns: list[Transaction] = []
            page_ob: float | None = None

            if is_text_page:
                # Text page: use pdfplumber extraction
                for table in page.extract_tables():
                    txns, saved_col, ob = _parse_transactions_from_table(table, saved_col)
                    if txns:
                        page_txns.extend(txns)
                    if ob is not None and page_ob is None:
                        page_ob = ob

                if not page_txns and page_text:
                    if _is_pipe_format(page_text):
                        txns, ob = _parse_transactions_from_pipe_text(page_text)
                    else:
                        txns, ob = _parse_transactions_from_text(page_text)
                    page_txns.extend(txns)
                    if ob is not None and page_ob is None:
                        page_ob = ob
            else:
                # Scanned page: use OCR
                ocr_text, _ = _ocr_page(pdf_path, page_num, ocr_dpi)
                if ocr_text:
                    if _is_pipe_format(ocr_text):
                        txns, ob = _parse_transactions_from_pipe_text(ocr_text)
                    else:
                        txns, ob = _parse_transactions_from_text(ocr_text)
                    page_txns.extend(txns)
                    if ob is not None and page_ob is None:
                        page_ob = ob

            all_transactions.extend(page_txns)
            page_stats.append({"page": page_num + 1, "tx_count": len(page_txns)})

            if page_ob is not None and opening_balance is None:
                opening_balance = page_ob

            # Collect header from first page, footer from last
            if page_num == 0:
                heuristic_name = detect_holder_name_heuristic(page)
                page_0_header = split_page_zones(page)["header"]

            if page_num == total_pages - 1:
                last_page_footer = split_page_zones(page)["footer"]

    full_text = "\n".join(full_text_parts)

    # Header extraction with zones
    fields = _extract_header_fields(
        full_text,
        source_file=pdf_path,
        header_zone=page_0_header,
        footer_zone=last_page_footer,
    )

    # Typographic fallback
    if not fields.get("holder_name") and heuristic_name:
        fields["holder_name"] = ExtractedField(heuristic_name, 0.65, "typographic_heuristic")

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

    # Clean, sort, recover amounts
    all_transactions = [
        t for t in all_transactions
        if t.date is not None or (t.amount is not None and t.amount > 0) or len(t.description) > 2
    ]
    all_transactions.sort(
        key=lambda t: (t.date or __import__("datetime").date.min)
    )
    all_transactions = _recover_amounts_from_balance(all_transactions, opening_balance)

    # Fallback closing balance
    if hdr_closing is None and all_transactions:
        last_bal = next(
            (t.balance for t in reversed(all_transactions) if t.balance is not None),
            None,
        )
        hdr_closing = last_bal

    # Summary
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

    # Warnings
    reset_warnings = _detect_balance_resets(all_transactions, opening_balance)
    _CONF_THRESHOLD = 0.70
    conf_warnings = [
        f"Low confidence ({f.confidence:.0%}) on '{k}' "
        f"[method: {f.method}] — verify manually"
        for k, f in fields.items()
        if f.confidence < _CONF_THRESHOLD
    ]

    statement.warnings = (
        _check_page_completeness(page_stats, total_pages)
        + reset_warnings
        + conf_warnings
        + validate_statement(statement)
    )

    return statement
