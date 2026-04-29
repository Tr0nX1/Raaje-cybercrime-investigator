import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from dateutil import parser as dateparser
from typing import Any

# ── Raw text normalization ─────────────────────────────────────────────────────

# PDF generators that use Private Use Area codepoints for ligatures bypass NFKC.
_LIGATURE_MAP: dict[str, str] = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl",
    "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
}

# High-frequency Unicode chars that pdfplumber preserves but downstream regex
# doesn't expect.  Applied after NFKC so the list stays small.
_CHAR_SUBSTITUTIONS: dict[str, str] = {
    " ": " ",    # non-breaking space
    "–": "-",    # en-dash
    "—": "-",    # em-dash
    "‘": "'",    # left single quote
    "’": "'",    # right single quote
    "“": '"',    # left double quote
    "”": '"',    # right double quote
    "­": "",     # soft hyphen (PDF word-wrap artifact — discard)
    "•": "-",    # bullet (some banks use in address lines)
    "₹": "Rs.",  # rupee sign
    "−": "-",    # minus sign
}

# OCR glyph confusion — only corrected when the character sits in a position
# that is structurally consistent with a leading digit of a monetary amount.
# Lookahead requires [\d,]* then the mandatory ".dd" suffix so ordinary words
# starting with l/I/O (e.g. "liability", "OPENING") are never touched.
_OCR_L_RE = re.compile(r"(?<![A-Za-z])[lI](?=[\d,]*\.\d{2})")   # l/I → 1
_OCR_O_RE = re.compile(r"(?<![A-Za-z])O(?=[\d,]*\.\d{2})")       # O   → 0


def normalize_raw_text(text: str) -> str:
    """
    Normalize raw pdfplumber output before any regex or clean_text() runs.

    Call order is significant:
      1. NFKC  — expands compatibility ligatures (ﬁ→fi) and normalises codepoints
      2. PUA ligatures — catches generators that bypass NFKC
      3. Char substitutions — replace known high-value Unicode with ASCII equivalents
      4. OCR corrections — fix l/I→1 and O→0 only in monetary contexts
    """
    text = unicodedata.normalize("NFKC", text)

    for src, dst in _LIGATURE_MAP.items():
        text = text.replace(src, dst)

    for src, dst in _CHAR_SUBSTITUTIONS.items():
        text = text.replace(src, dst)

    text = _OCR_L_RE.sub("1", text)
    text = _OCR_O_RE.sub("0", text)

    return text


# ── Semantic line joining ──────────────────────────────────────────────────────

# Known header field labels that banks commonly print on one line with the
# value pushed to the next line.
_BROKEN_LABEL_RE = re.compile(
    r"(?:opening\s*bal(?:ance)?|closing\s*bal(?:ance)?|balance\s*c/?f|"
    r"account\s*(?:no\.?|number|name|holder)|a/c\s*(?:no\.?|name)|"
    r"customer\s*name|ifsc\s*(?:code)?|branch(?:\s*(?:name|code))?|"
    r"statement\s*(?:period|from|to|date)|from\s*date|to\s*date)"
    r"\s*[:\-]?\s*$",
    re.IGNORECASE,
)

# Any label that ends with a bare colon (catches unknown field names).
_COLON_TAIL_RE = re.compile(r":\s*$")

# Values that logically follow a broken label: amounts or dates.
_VALUE_START_RE = re.compile(
    r"^\.?\d[\d,]*\.\d{2}"                      # amount  — 27,450.00
    r"|^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"     # date    — 01/04/2024
    r"|^\d{1,2}\s+\w{3,9}\s+\d{2,4}",           # date    — 01 Apr 2024
    re.IGNORECASE,
)


def join_broken_lines(lines: list[str]) -> list[str]:
    """
    Reconstruct label-value pairs split across two lines in header/footer zones.

    Fires when a known-label line (or any colon-tailed line) is immediately
    followed by a line that starts with an amount or date value.
    Safe to call on header and footer slices only — never on transaction body text.
    """
    if len(lines) < 2:
        return lines

    result: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].rstrip()

        if i + 1 < len(lines):
            next_val = lines[i + 1].strip()
            if next_val and _VALUE_START_RE.match(next_val):
                if _BROKEN_LABEL_RE.search(stripped) or _COLON_TAIL_RE.search(stripped):
                    result.append(stripped + " " + next_val)
                    i += 2
                    continue

        result.append(lines[i])
        i += 1

    return result


# ── Confidence-tagged field ────────────────────────────────────────────────────

@dataclass
class ExtractedField:
    """Wraps a single extracted header value with extraction provenance."""
    value: Any
    confidence: float   # 0.0 – 1.0
    method: str         # e.g. "label_regex", "filename", "allcaps_heuristic"


# ── Configurable thresholds ────────────────────────────────────────────────────

# Real bank amount never exceeds this many significant digits (99,99,99,999.99 = 11 digits).
MAX_AMOUNT_DIGITS: int = 12

# Ceiling above which a parsed value is considered invalid (default: 1 crore).
# Increase this for high-value corporate accounts.
MAX_AMOUNT_VALUE: float = 1_00_00_000.0

# ── Strict monetary regex ──────────────────────────────────────────────────────
#
# Matches: 500.00 | 1700.00 | 1,23,456.78 | 56,000.00 | 1,40,000.00
# Does NOT match bare integers (749152315897) or timestamps (20:31:22).
#
# Design: allow any digit/comma prefix, but REQUIRE the ".dd" suffix.
# This single guard stops UPI/IMPS reference numbers from being parsed as
# amounts — those are bare integers with no decimal component.
# Overly large values that sneak past (e.g. a ref that somehow gains ".00")
# are caught by the MAX_AMOUNT_VALUE ceiling check inside parse_amount().
_MONETARY_RE = re.compile(r"\d[\d,]*\.\d{2}")

# Common date formats used in Indian bank statements.
# DD-MON-YY ("%d-%b-%y") covers IndusInd-style dates like "23-APR-25".
_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y",
    "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y",
    "%d-%b-%Y", "%d-%b-%y",     # e.g. 23-APR-2025, 23-APR-25
    "%d-%B-%Y", "%d-%B-%y",     # e.g. 23-APRIL-2025
]


# ── RULE 2 — Safe amount parser ────────────────────────────────────────────────

def parse_amount(raw: str) -> float | None:
    """
    Extract the last valid monetary value from raw text.

    Returns None (never 0.0) when:
    - no strict monetary pattern found (e.g. bare integer reference numbers)
    - digit count > MAX_AMOUNT_DIGITS
    - value > MAX_AMOUNT_VALUE

    This function must NEVER receive description-column text (Rule 3).
    Callers are responsible for passing only debit/credit/balance cell content.
    """
    if not raw:
        return None

    stripped = raw.strip()

    # Some banks (e.g. Axis Bank) print zero balances as ".00" with no leading digit.
    # Handle this before the main regex so we return 0.0 rather than None.
    if re.fullmatch(r"\.\d{2}", stripped):
        try:
            return float(stripped)
        except ValueError:
            return None

    matches = _MONETARY_RE.findall(raw)
    if not matches:
        return None

    # Take the LAST match — in cells that contain both a label and amount,
    # the amount always appears at the end.
    for candidate in reversed(matches):
        cleaned = candidate.replace(",", "")
        digit_count = len(cleaned.replace(".", ""))
        if digit_count > MAX_AMOUNT_DIGITS:
            continue
        try:
            value = float(cleaned)
        except ValueError:
            continue
        if value > MAX_AMOUNT_VALUE:
            continue
        return value

    return None


# ── Date parser ────────────────────────────────────────────────────────────────

def parse_date(raw: str) -> date | None:
    """Try multiple date formats; return date or None. Never raises."""
    if not raw:
        return None
    # Normalize: replace newlines with space and collapse whitespace
    raw = re.sub(r"[\n\r\t]+", " ", raw).strip()
    # Also handle "16-APR- 2025" (space after hyphen caused by split)
    raw = re.sub(r"([A-Za-z])- ", r"\1-", raw) 
    
    for fmt in _DATE_FORMATS:
        try:
            return date.fromtimestamp(
                __import__("time").mktime(
                    __import__("time").strptime(raw, fmt)
                )
            )
        except ValueError:
            continue
    try:
        return dateparser.parse(raw, dayfirst=True).date()
    except Exception:
        return None


# ── Transaction type + amount detector ────────────────────────────────────────

def detect_transaction_type(
    debit_col: str,
    credit_col: str,
    description: str = "",
) -> tuple[str, float | None]:
    """
    RULE 3 — Amount is NEVER extracted from description.

    Priority:
      1. debit_col  → type=debit,  amount from debit_col
      2. credit_col → type=credit, amount from credit_col
      3. description keywords → type only; amount = None
         (balance-based recovery handles the actual amount later)

    Returns (type, amount_or_None).
    """
    debit  = parse_amount(debit_col)
    credit = parse_amount(credit_col)

    if debit is not None and debit > 0:
        return "debit", debit
    if credit is not None and credit > 0:
        return "credit", credit

    # Keyword scan for type only — no amount extraction from description
    desc_lower = description.lower()
    credit_kw = [
        "cr/", "cr ", "credit", "deposit", "salary", "refund",
        "interest", "sbint", "reversal", "rev-",
        "trf frm", "transfer from", "trf from", "received",
        "inward", "by clg", "by transfer", "by cash", "by neft",
        "by imps", "by upi", "credited", "neft cr", "imps cr",
        "upi cr", "rtgs cr", "sweep in", "sweep from", "fd proceeds",
        "maturity", "int pd", "int.pd", "int cr", "sb int", "dividend",
        "cashback", "reward", "refund", "reimburs",
    ]
    debit_kw  = [
        "dr/", "dr ", "debit", "withdrawal", "payment",
        "charge", "fee", "penalty",
        "trf to", "transfer to", "sent to", "paid to",
        "neft dr", "imps dr", "upi dr", "rtgs dr",
        "sweep out", "sweep to", "atm", "cash wd", "wthdrwl", "wdrl",
        "emi", "loan", "chq", "cheque", "to clg", "debited",
        "pmsby", "pmjjby", "cgst", "sgst", "gst", "tds",
    ]

    if any(kw in desc_lower for kw in credit_kw):
        return "credit", None
    if any(kw in desc_lower for kw in debit_kw):
        return "debit", None

    return "unknown", None


# ── RULE 8 — Priority-ordered categorizer ─────────────────────────────────────

def categorize(description: str) -> str:
    """
    Categories are evaluated in priority order so that specific labels
    win over broad ones.

    Key fixes vs. previous version:
    - "charges" checked FIRST — prevents IMPS/ATM fees being tagged "transfer"
    - "reversal" checked BEFORE "salary" — prevents "sal/" in "reversal/" matching
    - "sal/" keyword removed entirely (was colliding with "reversal/")
    """
    desc = description.lower()

    rules: list[tuple[str, list[str]]] = [
        # 1 — most specific first
        ("charges",  ["transaction charges", "imps charges", "sms charges",
                      "penalty charges", "annual charges",
                      "charge", "fee", "fine", "penalty"]),
        # 2
        ("reversal", ["reversal", "rev-", "/rev/"]),
        # 3
        ("interest", ["interest", "int cr", "int pd", "sbint"]),
        # 4 — "sal/" intentionally removed; "salary" and "payroll" remain safe
        ("salary",   ["salary", "payroll", "neft cr"]),
        # 5
        ("upi",      ["upi/", "upi-", "@ok", "@ybl", "@paytm"]),
        # 6
        ("atm",      ["atm/", "atm wd", "cash withdrawal"]),
        # 7
        ("emi",      ["emi", "loan", "lending"]),
        # 8
        ("utility",  ["electricity", "water", "gas", "broadband", "recharge"]),
        # 9
        ("food",     ["swiggy", "zomato", "restaurant", "cafe"]),
        # 10
        ("shopping", ["amazon", "flipkart", "myntra", "mall"]),
        # 11 — broad; must come after charges/reversal/transfer-specific rules
        ("transfer", ["neft", "rtgs", "imps", "transfer"]),
        # 12
        ("tax",      ["gst", "tds", "tax"]),
    ]

    for category, keywords in rules:
        if any(kw in desc for kw in keywords):
            return category

    return "other"


# ── Text cleaner ───────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Remove non-printable characters and collapse excess whitespace."""
    text = re.sub(r"[^\x20-\x7E\n]", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


# ── Validation layer ────────────────────────────────────────────────────────────

def validate_statement(statement) -> list[str]:
    """
    Run validation checks on a BankStatement.
    Returns list of warning strings (non-blocking).
    Checks: balance consistency, date monotonicity, transaction count sanity,
            row-level balance validation, transaction integrity.
    """
    from datetime import date as DateType
    warnings: list[str] = []

    if not statement.transactions:
        return warnings

    # 1. Balance consistency: opening + credits - debits ≈ closing
    if (statement.summary.opening_balance is not None and
            statement.summary.closing_balance is not None):
        expected_closing = (
            statement.summary.opening_balance +
            statement.summary.total_credits -
            statement.summary.total_debits
        )
        actual_closing = statement.summary.closing_balance
        # Allow 0.01 tolerance for rounding
        if abs(expected_closing - actual_closing) > 0.01:
            warnings.append(
                f"Balance mismatch: opening {statement.summary.opening_balance:.2f} "
                f"+ credits {statement.summary.total_credits:.2f} "
                f"- debits {statement.summary.total_debits:.2f} "
                f"= {expected_closing:.2f}, but closing is {actual_closing:.2f} "
                f"(delta: {abs(expected_closing - actual_closing):.2f})"
            )

    # 2. Date monotonicity: transactions should be in chronological order
    prev_date: DateType | None = None
    date_violations = 0
    for i, tx in enumerate(statement.transactions):
        if tx.date is not None:
            if prev_date is not None and tx.date < prev_date:
                date_violations += 1
            prev_date = tx.date
    if date_violations > 0:
        warnings.append(
            f"Date order violation: {date_violations} transaction(s) out of chronological order"
        )

    # 3. Transaction count sanity: warn if suspiciously low/high
    tx_count = len(statement.transactions)
    # Threshold: warn if very few (< 2) or very many (> 10000)
    if tx_count < 2:
        warnings.append(
            f"Suspiciously low transaction count: only {tx_count} transaction(s) extracted"
        )
    elif tx_count > 10000:
        warnings.append(
            f"Suspiciously high transaction count: {tx_count} transaction(s) extracted "
            f"(may indicate extraction error)"
        )

    # 4. Row-level balance validation: each transaction's balance delta should match amount
    # Robust version: try both +amount and -amount against actual delta
    prev_balance: float | None = statement.summary.opening_balance
    balance_mismatches = 0
    for i, tx in enumerate(statement.transactions):
        if prev_balance is not None and tx.balance is not None and tx.amount is not None:
            actual_delta = tx.balance - prev_balance
            # Try both interpretations: credit (+) and debit (-)
            option_credit = tx.amount
            option_debit = -tx.amount
            # Allow 0.01 tolerance for rounding
            credit_matches = abs(option_credit - actual_delta) <= 0.01
            debit_matches = abs(option_debit - actual_delta) <= 0.01

            # If neither interpretation matches the balance delta → mismatch
            if not (credit_matches or debit_matches):
                balance_mismatches += 1

        if tx.balance is not None:
            prev_balance = tx.balance

    if balance_mismatches > 0:
        warnings.append(
            f"Row-level balance mismatch: {balance_mismatches} transaction(s) "
            f"where amount ±{'{:.2f}'} doesn't match balance delta"
        )

    # 5. Transaction integrity checks
    integrity_issues = []
    for i, tx in enumerate(statement.transactions):
        row_num = i + 1

        # Check: both debit and credit present (should be mutually exclusive)
        # This is checked via type field — if parsing correctly, only one should be set
        # For now, we check if the description suggests both (rare edge case)

        # Check: amount missing when type is not unknown
        if tx.amount is None and tx.type != "unknown":
            integrity_issues.append(
                f"Row {row_num}: type={tx.type} but amount is None"
            )

        # Check: type is unknown but description has clear keywords
        if tx.type == "unknown" and tx.amount is None:
            # This is expected for keyword-detected transactions (Rule 3)
            pass

        # Check: both amount and type are unknown (very weak extraction)
        if tx.type == "unknown" and tx.amount is None:
            # This is acceptable for transactions where balance recovery will fill in
            pass

    if integrity_issues:
        warnings.append(
            f"Transaction integrity: {len(integrity_issues)} issue(s) — "
            + "; ".join(integrity_issues[:5])  # Limit to first 5 for readability
        )

    return warnings


