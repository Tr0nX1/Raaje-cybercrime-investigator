# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Single file → JSON
python main.py "input files/statement.pdf"

# Single file → TOON (tab-delimited flat format)
python main.py "input files/statement.pdf" --format toon

# Batch all PDFs in folder → JSON
python main.py "input files/" --batch --format json --parallel 1

# Force OCR even on text-based PDFs
python main.py "input files/statement.pdf" --force-ocr --dpi 300

# Batch + full analysis report
python main.py "input files/" --batch --format both --report

# Quick extraction test on a single file (no CLI overhead)
python -c "
from pipeline import process_single
import json
s = process_single('input files/YOUR.pdf')
print(json.dumps(s.model_dump(mode='json'), indent=2, default=str))
"
```

Use `--parallel 1` for debugging — parallel workers suppress tracebacks.

## Architecture

```
main.py           CLI entry point (argparse) → process_single / process_batch
pipeline.py       Routes each PDF: is_text_based? → text_extractor : ocr_extractor
extractor/
  detector.py     is_text_based() — samples first 3 pages for selectable text
  text_extractor.py  Core pdfplumber-based extractor (9 deterministic rules)
  ocr_extractor.py   EasyOCR fallback for scanned/image PDFs
  normalizer.py   parse_amount, parse_date, detect_transaction_type, categorize
models/schema.py  Pydantic models: BankStatement → AccountInfo + Summary + [Transaction]
analyzer/calculations.py  Pure functions on BankStatement (cashflow, ADB, EMI, anomalies)
input files/      Source PDFs
output/           JSON / TOON output files
```

### Extraction flow (text path)

`extract_text_pdf` processes each PDF page in order:
1. Try `page.extract_tables()` — if tables found, pass to `_parse_transactions_from_table`
2. Fallback to `_parse_transactions_from_text` (free-text line parser) when no table detected
3. After all pages: run `_extract_header_fields` on the joined full text
4. Sort all transactions by date, then run `_recover_amounts_from_balance` (Rule 4)
5. Build `Summary` (opening/closing balance, totals)

### The 9 Rules (in `text_extractor.py` + `normalizer.py`)

| Rule | Location | Purpose |
|------|----------|---------|
| 1 | `_validate_col_map` | Reject columns where <70% of cells match `\d[\d,]*\.\d{2}` — prevents description columns being used as amount columns |
| 2 | `parse_amount` | Strict `\d[\d,]*\.\d{2}` pattern; bare integers return None; MAX_AMOUNT_VALUE cap |
| 3 | `detect_transaction_type` | Amount NEVER extracted from description column |
| 4 | `_recover_amounts_from_balance` | `amount = abs(curr_bal - prev_bal)` for None-amount rows; also infers debit/credit from balance direction |
| 5 | `_rows_to_transactions` | Rows without date cell → append to previous transaction's description |
| 6 | `_rows_to_transactions` | B/F / BROUGHT FORWARD rows set `opening_balance`, not stored as transactions |
| 7 | `_extract_header_fields` | `holder_name` only from label-anchored patterns; dates only from top 40 lines |
| 8 | `categorize` | Priority-ordered: charges > reversal > interest > salary > upi > transfer |
| 9 | `_check_page_completeness` | Warn when page drops from ≥5 transactions to 0 (possible blank/missing page) |

### Key regex anchors

- `_BANK_RE` matches `HDFC|SBI|ICICI|AXIS|KOTAK|PNB|BOB|YES|IDBI|CANARA|UNION` anywhere in full document — this is the source of bank_name corruption (picks up NEFT payee codes like `YESB/...` in transaction narrations).
- `_HOLDER_RE` requires labels `customer name / account title / a/c name / account holder` — misses most bank formats.
- `_CLOSING_BAL_RE` and `_OPENING_BAL_RE` are searched only in the top 40 header lines — misses banks that print closing balance in the footer.

### detect_transaction_type priority

1. Non-zero `debit_col` → `("debit", amount)`
2. Non-zero `credit_col` → `("credit", amount)`
3. Keyword scan of description → type only, `amount=None` (Rule 4 fills the amount later)
4. No match → `("unknown", None)`

Transactions with `type="unknown"` are excluded from `total_credits` / `total_debits` in Summary — so corrupt totals always indicate widespread unknown-type transactions.

### OCR path

`extract_ocr_pdf` renders pages via PyMuPDF → EasyOCR → joins text → calls the same `_parse_transactions_from_text` + `_extract_header_fields` as the text path. No table parsing — only line-regex mode.

### Output formats

- **JSON**: `statement.model_dump(mode="json")` — nested `account`, `summary`, `transactions[]`
- **TOON**: `statement.to_toon()` — TSV with `#`-prefixed header metadata lines

### Known bank-format gaps (as of audit 2026-04-21)

- **DCB Bank**: Multi-account consolidated statements produce balance resets mid-file; "Opening Balance" rows not suppressed by Rule 6 (B/F pattern doesn't match "Opening Balance" text)
- **YES Bank / BOM**: Transaction tables extracted but column map detection fails for some layouts → 0 transactions
- **Password-protected PDFs**: Crash at pdfplumber open with `PDFPasswordIncorrect` — not handled
- **closing_balance**: Only captured if printed in the top 40 lines; footer placement (all other banks) is missed
