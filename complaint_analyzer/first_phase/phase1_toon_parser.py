"""
Phase 1 - TOON Parser
Accepts any complaint PDF, extracts and reconstructs all tables into a structured TOON JSON.
Usage: python phase1_toon_parser.py <input.pdf> [output.json]
"""

import sys
import json
import re
from pathlib import Path
import pdfplumber

TRANSACTION_TYPE_KEYWORDS = ("imps", "neft", "rtgs", "upi", "wallet")
BANK_KEYWORDS = (
    "bank",
    "payments",
    "finance",
    "small finance",
    "merchant",
    "ltd",
    "limited",
    "credit",
)


# ─────────────────────────────────────────────
# CELL CLEANING
# ─────────────────────────────────────────────

def clean_cell(value):
    if value is None:
        return ""
    value = re.sub(r'[\uf000-\uf8ff]', '', value)   # strip icon glyphs
    value = re.sub(r'[ \t]+', ' ', value)
    return value.strip()


def split_multiline(value):
    lines = [l.strip() for l in value.split('\n') if l.strip()]
    return lines


def collapse(value):
    """Collapse wrapped multi-line text into single clean string."""
    return ' '.join(split_multiline(clean_cell(value)))


def build_row_evidence(row, page_num, table_index, row_index, table_type):
    cleaned_cells = [clean_cell(str(cell or '')) for cell in row]
    raw_cells = []
    for idx, cell in enumerate(cleaned_cells):
        raw_cells.append({
            "column_index": idx,
            "text": cell,
            "lines": split_multiline(cell),
        })

    non_empty_cells = [cell for cell in cleaned_cells if cell]
    return {
        "source_page": page_num,
        "source_table_index": table_index,
        "source_row_index": row_index,
        "source_table_type": table_type,
        "raw_cells": raw_cells,
        "raw_row_text": " | ".join(non_empty_cells),
    }


def attach_evidence(record, evidence):
    if not record:
        return None
    enriched = dict(record)
    enriched.update(evidence)
    return enriched


# ─────────────────────────────────────────────
# TABLE TYPE DETECTION
# ─────────────────────────────────────────────

def _header_text(row):
    return ' '.join(clean_cell(str(c or '')).lower() for c in row)


def _looks_like_transaction_type(value):
    text = clean_cell(str(value or '')).lower()
    return text in TRANSACTION_TYPE_KEYWORDS


def _looks_like_transaction_id(value):
    text = clean_cell(str(value or '')).replace(" ", "")
    if not text:
        return False
    return bool(re.fullmatch(r'[A-Z0-9\-\/]{8,25}', text, re.I))


def _looks_like_amount(value):
    text = clean_cell(str(value or ''))
    return bool(re.fullmatch(r'[\d,]+(?:\.\d{1,2})?', text))


def _looks_like_datetime(value):
    text = clean_cell(str(value or ''))
    return bool(re.search(r'\d{2}/\d{2}/\d{4}', text))


def _looks_like_bank_name(value):
    text = collapse(value).lower()
    if not text:
        return False
    return any(keyword in text for keyword in BANK_KEYWORDS)


def _looks_like_layered_continuation(sample_row, sample_text):
    if 'layer :' in sample_text or 'reassign' in sample_text:
        return True
    if re.search(r'[A-Z]{4}0[A-Z0-9]{6}', sample_text, re.I):
        return True
    if len(sample_row) >= 10 and any('utr' in clean_cell(str(c or '')).lower() for c in sample_row[1:4]):
        return True
    return False


def _looks_like_victim_continuation(sample_row):
    if len(sample_row) < 8:
        return False

    transaction_id_match = _looks_like_transaction_id(sample_row[2]) if len(sample_row) > 2 else False
    transaction_type_match = _looks_like_transaction_type(sample_row[3]) if len(sample_row) > 3 else False
    amount_match = _looks_like_amount(sample_row[4]) if len(sample_row) > 4 else False
    transaction_datetime_match = _looks_like_datetime(sample_row[6]) if len(sample_row) > 6 else False
    complaint_datetime_match = _looks_like_datetime(sample_row[7]) if len(sample_row) > 7 else False
    bank_match = _looks_like_bank_name(sample_row[8]) if len(sample_row) > 8 else False

    return all(
        [
            transaction_id_match,
            transaction_type_match,
            amount_match,
            transaction_datetime_match,
            complaint_datetime_match,
            bank_match,
        ]
    )


def detect_table_type(table):
    """
    Classify table by inspecting header row(s) OR first data row content.
    Some tables have a title row + header row; continuation pages have no header at all.
    """
    if not table or len(table) < 1:
        return 'UNKNOWN'

    row0 = _header_text(table[0])
    row1 = _header_text(table[1]) if len(table) > 1 else ''

    # ── Suspect table ─────────────────────────────
    if 'suspect details' in row0 or 'suspect name' in row0 or 'suspect name' in row1:
        return 'SUSPECT_TABLE'

    # ── ATM withdrawal ────────────────────────────
    if 'withdrawal' in row0 and 'atm' in row0:
        return 'ATM_TABLE'

    # ── Hold / lien table ─────────────────────────
    if 'put on hold' in row0 or 'hold amount' in row0:
        return 'HOLD_TABLE'

    # ── Bank pending summary ──────────────────────
    if ('banks' in row0 or 'bank' in row0) and 'pending' in row0:
        return 'BANK_PENDING_TABLE'

    # ── Layered transaction table (header has "bank /fis" and "ifsc" or "disputed") ──
    if ('bank' in row0 or 'fis' in row0) and ('ifsc' in row0 or 'disputed' in row0 or 'utr' in row0):
        return 'LAYERED_TRANSACTION_TABLE'

    # --- HIGH PRIORITY KEYWORD DETECTION (Handle continuation pages) ---
    full_sample_text = ' '.join(_header_text(r) for r in table[:3])
    if 'layer :' in full_sample_text:
        return 'LAYERED_TRANSACTION_TABLE'
    
    if ('phi comm' in full_sample_text or 'private limit' in full_sample_text) and 'utr' in full_sample_text:
        return 'LAYERED_TRANSACTION_TABLE'

    # -- Victim transaction table (has "wallet id" or "card details" / "transaction id") --
    if ('wallet' in row0 or 'card' in row0) and 'transaction' in row0:
        return 'VICTIM_TRANSACTION_TABLE'

    # -- Attachment / file table -------------------
    if 'md5' in row0 or 'sha' in row0:
        return 'ATTACHMENT_TABLE'

    # -- No header: detect by content of first data row --------------------
    sample_row = table[0]
    sample_text = _header_text(sample_row)

    # Victim transaction continuation: sno numeric + "phi commerce" or "limited"
    if re.match(r'^\d+$', clean_cell(str(sample_row[0] or ''))):
        # Deciding by number of columns + content
        if len(sample_row) >= 10:
            if _looks_like_layered_continuation(sample_row, sample_text):
                return 'LAYERED_TRANSACTION_TABLE'
            if _looks_like_victim_continuation(sample_row):
                return 'VICTIM_TRANSACTION_TABLE'
            return 'GENERIC_TABLE'
        if len(sample_row) == 9:
            if _looks_like_victim_continuation(sample_row):
                return 'VICTIM_TRANSACTION_TABLE'
            if _looks_like_layered_continuation(sample_row, sample_text):
                return 'LAYERED_TRANSACTION_TABLE'
            return 'VICTIM_TRANSACTION_TABLE'
        
        if len(sample_row) == 6 and re.search(r'\d{2}/\d{2}/\d{4}', sample_text):
            return 'HOLD_TABLE'

    return 'GENERIC_TABLE'


# ─────────────────────────────────────────────
# ROW RECONSTRUCTION
# ─────────────────────────────────────────────

def reconstruct_victim_row(row, evidence=None):
    if not row or len(row) < 9:
        return None

    wallet_raw = clean_cell(row[1])
    bank_raw   = clean_cell(row[8])

    # wallet cell: entity name lines + wallet_id (last numeric/dash line)
    wallet_lines  = split_multiline(wallet_raw)
    wallet_entity = ' '.join(wallet_lines[:-1]) if len(wallet_lines) > 1 else wallet_raw
    wallet_id     = wallet_lines[-1] if len(wallet_lines) > 1 else ''

    # bank cell: remove "Reassign Back To Police Date ..." noise
    bank_clean = re.sub(r'Reassign Back To[\s\S]*', '', bank_raw, flags=re.I).strip()
    bank_clean = bank_clean.replace('\n', ' ').strip()

    # dates
    txn_dt = ' '.join(split_multiline(clean_cell(row[6])))
    cmp_dt = ' '.join(split_multiline(clean_cell(row[7])))

    record = {
        "sno":                  clean_cell(row[0]),
        "wallet_entity":        wallet_entity,
        "wallet_id":            wallet_id,
        "transaction_id":       clean_cell(row[2]),
        "transaction_type":     clean_cell(row[3]),
        "amount":               clean_cell(row[4]),
        "reference_no":         clean_cell(row[5]),
        "transaction_datetime": txn_dt,
        "complaint_date":       cmp_dt,
        "bank":                 bank_clean,
    }
    return attach_evidence(record, evidence or {})


def _get_digits(s):
    return re.sub(r'\D', '', str(s))


def _compact_alnum(value):
    return ''.join(re.findall(r'[A-Za-z0-9]+', str(value or '')))


def _extract_ifsc_and_account(dest_raw):
    compact = _compact_alnum(dest_raw)
    if not compact:
        return "", ""

    match = re.search(r'[A-Z]{4}0[A-Z0-9]{6}', compact, re.I)
    if match:
        ifsc = match.group(0).upper()
        account = (compact[:match.start()] + compact[match.end():]).strip()
        return account, ifsc

    return compact, ""


def _join_entity_parts(parts):
    joined = ' '.join(part for part in parts if part).strip()
    return re.sub(r'\s+', ' ', joined)


def _split_numeric_tail(full_digits, preferred_tail=""):
    if preferred_tail and full_digits.endswith(preferred_tail):
        return full_digits[:-len(preferred_tail)], preferred_tail

    if len(full_digits) >= 22:
        return full_digits[:-12], full_digits[-12:]
    if len(full_digits) >= 20:
        return full_digits[:-10], full_digits[-10:]
    return full_digits, ""


def _split_wallet_source(source_lines, transaction_utr):
    text_parts = []
    digit_parts = []

    for line in source_lines:
        alpha_part = re.sub(r'\d+', ' ', line)
        alpha_part = re.sub(r'\s+', ' ', alpha_part).strip()
        digit_part = _get_digits(line)

        if alpha_part:
            text_parts.append(alpha_part)
        if digit_part:
            digit_parts.append(digit_part)

    full_digits = ''.join(digit_parts)
    utr_digits = _get_digits(transaction_utr)
    account_digits, source_utr = _split_numeric_tail(full_digits, preferred_tail=utr_digits)

    entity_text = _join_entity_parts(text_parts)
    if account_digits:
        if entity_text.endswith(('-', ':', '-:')):
            source_account = f"{entity_text}{account_digits}"
        elif entity_text:
            source_account = f"{entity_text} {account_digits}"
        else:
            source_account = account_digits
    else:
        source_account = entity_text

    return source_account.strip(), source_utr


def _split_account_source(source_lines, transaction_utr):
    full_digits = ''.join(_get_digits(line) for line in source_lines)
    utr_digits = _get_digits(transaction_utr)
    return _split_numeric_tail(full_digits, preferred_tail=utr_digits)

def stitch_sequential_blocks(lines, target_ranges):
    """
    Greedily collect lines into blocks based on cumulative digit length.
    target_ranges: list of (min_len, max_len) for each block.
    """
    blocks = []
    current_lines = list(lines)
    
    for min_l, max_l in target_ranges:
        accum = ""
        while current_lines:
            line = current_lines[0]
            digits = _get_digits(line)
            if not digits and not re.search(r'[A-Z]', line):
                current_lines.pop(0)
                continue
            
            # If adding this line stays within or reaches target
            if len(_get_digits(accum + line)) <= max_l or not accum:
                accum += current_lines.pop(0)
            else:
                break
            
            if len(_get_digits(accum)) >= min_l:
                break
        blocks.append(accum)
    
    # Any leftovers go to the last block or are discarded
    return blocks

def reconstruct_layered_row(row, evidence=None):
    if not row or len(row) < 9:
        return None

    source_raw = clean_cell(row[1])
    bank_raw   = clean_cell(row[2])
    dest_raw   = clean_cell(row[3])
    date_raw   = clean_cell(row[5])
    transaction_utr_raw = clean_cell(row[4])
    remarks_raw = clean_cell(row[8]) if len(row) > 8 else ''
    action_raw  = clean_cell(row[9]) if len(row) > 9 else ''

    # -- Source cell (Sequence-Aware Stitching) --
    source_lines  = split_multiline(source_raw)
    is_wallet = _looks_like_wallet_source(source_lines)
    
    if is_wallet:
        source_type    = 'wallet'
        source_account, source_utr = _split_wallet_source(source_lines, transaction_utr_raw)
    else:
        source_type    = 'account'
        source_account, source_utr = _split_account_source(source_lines, transaction_utr_raw)

    # -- Bank / Layer cell --
    bank_lines  = split_multiline(bank_raw)
    bank_name   = bank_lines[0] if bank_lines else ''
    layer_no    = ''
    reassign    = ''
    for bl in bank_lines[1:]:
        lm = re.search(r'Layer\s*:\s*(\d+)', bl, re.I)
        if lm:
            layer_no = lm.group(1)
        if 'Reassign' in bl:
            reassign = collapse(bl)

    # -- Destination cell (Sequence-Aware Stitching) --
    dest_lines   = split_multiline(dest_raw)
    dest_account, dest_ifsc = _extract_ifsc_and_account(dest_raw)
    if not dest_account and dest_lines:
        dest_account = ''.join(_get_digits(line) for line in dest_lines)

    record = {
        "sno":                  clean_cell(row[0]),
        "source_type":          source_type,
        "source_account":       source_account,
        "source_utr":           source_utr,
        "bank":                 bank_name,
        "layer":                layer_no,
        "reassign_info":        reassign,
        "destination_account":  dest_account,
        "destination_ifsc":     dest_ifsc,
        "transaction_utr":      transaction_utr_raw,
        "datetime":             ' '.join(split_multiline(date_raw)),
        "amount":               clean_cell(row[6]),
        "disputed_amount":      clean_cell(row[7]),
        "remarks":              collapse(remarks_raw),
        "action_by":            collapse(action_raw),
    }
    return attach_evidence(record, evidence or {})


def _looks_like_wallet_source(source_lines):
    joined = ' '.join(source_lines).lower()
    alpha_lines = sum(1 for line in source_lines if re.search(r'[A-Za-z]', line))
    digit_lines = sum(1 for line in source_lines if re.search(r'\d', line))

    if any(keyword in joined for keyword in ("wallet", "merchant", "mobile", "commerce", "private", "limited")):
        return True

    # Entity-heavy source blocks followed by a short numeric id are usually wallet-like.
    if alpha_lines >= 1 and digit_lines >= 1 and len(source_lines) >= 2:
        return True

    return False


def reconstruct_suspect_row(row, evidence=None):
    if not row or len(row) < 4:
        return None
    id_type = clean_cell(row[1])
    if not id_type or id_type.lower() in ('id type', 'suspect name', 'suspect details'):
        return None   # skip header rows
    record = {
        "suspect_name": clean_cell(row[0]),
        "id_type":      id_type,
        "country_code": clean_cell(row[2]),
        "id_number":    clean_cell(row[3]),
    }
    return attach_evidence(record, evidence or {})


def reconstruct_bank_pending_row(row, evidence=None):
    if not row or len(row) < 5:
        return None
    record = {
        "sno":                  clean_cell(row[0]),
        "bank":                 collapse(row[1]),
        "transactions_pending": clean_cell(row[2]),
        "total_amount":         clean_cell(row[3]),
        "pending_from":         collapse(row[4]),
    }
    return attach_evidence(record, evidence or {})


def reconstruct_hold_row(row, evidence=None):
    if not row or len(row) < 4:
        return None
    acct_utr = split_multiline(clean_cell(row[1]))
    record = {
        "sno":          clean_cell(row[0]),
        "account_no":   acct_utr[0] if acct_utr else '',
        "utr":          acct_utr[1] if len(acct_utr) > 1 else '',
        "hold_date":    collapse(row[2]),
        "hold_amount":  clean_cell(row[3]),
        "action_by":    collapse(row[4]) if len(row) > 4 else '',
        "action_date":  clean_cell(row[5]) if len(row) > 5 else '',
    }
    return attach_evidence(record, evidence or {})


def reconstruct_atm_row(row, evidence=None):
    if not row or len(row) < 7:
        return None
    acct_utr = split_multiline(clean_cell(row[1]))
    record = {
        "sno":                  clean_cell(row[0]),
        "account_no":           acct_utr[0] if acct_utr else '',
        "utr":                  acct_utr[1] if len(acct_utr) > 1 else '',
        "withdrawal_datetime":  collapse(row[2]),
        "withdrawal_amount":    clean_cell(row[3]),
        "disputed_amount":      clean_cell(row[4]),
        "remarks":              collapse(row[5]),
        "atm_location":         collapse(row[6]),
        "action_by":            collapse(row[7]) if len(row) > 7 else '',
    }
    return attach_evidence(record, evidence or {})


# ─────────────────────────────────────────────
# TABLE DISPATCHER
# ─────────────────────────────────────────────

def is_header_row(row):
    """True if this row is a header/title — skip it from data output."""
    first = clean_cell(str(row[0] or '')).lower()
    return bool(re.match(r'^s[\s.]*no', first) or
                first in ('suspect details', 'suspect name', 'file name',
                           'login id', 's no.', 's\nno.'))


def parse_table(table, table_type, page_num, table_index):
    results = []
    for row_index, row in enumerate(table):
        if not row:
            continue
        if all(clean_cell(str(c or '')) == '' for c in row):
            continue     # empty spacer
        if is_header_row(row):
            continue     # header row

        evidence = build_row_evidence(row, page_num, table_index, row_index, table_type)

        if table_type == 'VICTIM_TRANSACTION_TABLE':
            r = reconstruct_victim_row(row, evidence=evidence)
        elif table_type == 'LAYERED_TRANSACTION_TABLE':
            r = reconstruct_layered_row(row, evidence=evidence)
        elif table_type == 'SUSPECT_TABLE':
            r = reconstruct_suspect_row(row, evidence=evidence)
        elif table_type == 'BANK_PENDING_TABLE':
            r = reconstruct_bank_pending_row(row, evidence=evidence)
        elif table_type == 'HOLD_TABLE':
            r = reconstruct_hold_row(row, evidence=evidence)
        elif table_type == 'ATM_TABLE':
            r = reconstruct_atm_row(row, evidence=evidence)
        else:
            r = {
                f"col_{i}": split_multiline(clean_cell(str(c or '')))
                for i, c in enumerate(row)
            }
            r = attach_evidence(r, evidence)

        if r:
            results.append(r)
    return results


# ─────────────────────────────────────────────
# KEY-VALUE FROM RAW TEXT
# ─────────────────────────────────────────────

KV_PATTERNS = [
    ('acknowledgement_no',      re.compile(r'Acknowledgement No[.\s:]*([^\n]+)', re.I)),
    ('category',                re.compile(r'Category of Complaint[:\s]*([^\n]+)', re.I)),
    ('sub_category',            re.compile(r'Sub Category of Complaint[:\s]*([^\n]+)', re.I)),
    ('user_id',                 re.compile(r'UserId[:\s]*([^\n]+)', re.I)),
    ('have_lost_money',         re.compile(r'Have You Lost Money[:\s]*([^\n]+)', re.I)),
    ('incident_datetime',       re.compile(r'Incident Date/Time[:\s]*([^\n]+)', re.I)),
    ('victim_name',             re.compile(r'\nName\s+([A-Z][^\n]+)', re.I)),
    ('victim_gender',           re.compile(r'Gender\s+(\w+)', re.I)),
    ('victim_dob',              re.compile(r'Date of Birth.*?(\d{2}/\d{2}/\d{4})', re.I)),
    ('victim_mobile',           re.compile(r'Mobile\s+(\d{10})', re.I)),
    ('victim_father_name',      re.compile(r'Father/Mother.*?Name\s+([^\n]+)', re.I)),
    ('victim_street',           re.compile(r'Street Name\s+([^\n]+)', re.I)),
    ('victim_house_no',         re.compile(r'House No\s+([^\n]+)', re.I)),
    ('victim_town',             re.compile(r'Village/ Town\s+([^\n]+)', re.I)),
    ('victim_pincode',          re.compile(r'Pincode\s+(\d{6})', re.I)),
    ('victim_police_station',   re.compile(r'Police Station\s+([^\n]+)', re.I)),
    ('victim_district',         re.compile(r'District\s+([^\n]+)', re.I)),
    ('victim_state',            re.compile(r'\nState\s+([^\n]+)', re.I)),
    ('total_fraudulent_amount', re.compile(r'Total Fraudulent Amount reported.*?:\s*([\d,]+\.?\d*)', re.I)),
    ('total_lien_amount',       re.compile(r'Total Lien Amount\s*:\s*([\d,]+\.?\d*)', re.I)),
]

def extract_kv(text):
    data = {}
    for key, pat in KV_PATTERNS:
        m = pat.search(text)
        if m:
            data[key] = m.group(1).strip()
    return data


# ─────────────────────────────────────────────
# MAIN PARSER
# ─────────────────────────────────────────────

def parse_pdf(pdf_path):
    pdf_path = Path(pdf_path)

    toon = {
        "meta": {
            "source_file":  pdf_path.name,
            "total_pages":  0,
            "parser_phase": "Phase 1 - Structure Detection + Table Reconstruction",
        },
        "document_structure": [],
        "sections": {
            "case_metadata":        {},
            "victim_details":       {},
            "suspect_details":      [],
            "victim_transactions":  [],
            "bank_pending_summary": [],
            "layered_transactions": [],
            "hold_transactions":    [],
            "atm_withdrawals":      [],
            "misc_tables":          [],
        }
    }

    all_page_texts = []
    page_text_map = {}

    with pdfplumber.open(pdf_path) as pdf:
        toon["meta"]["total_pages"] = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ''
            tables    = page.extract_tables() or []

            all_page_texts.append(page_text)
            page_text_map[page_num] = page_text

            page_info = {
                "page":        page_num,
                "has_text":    bool(page_text.strip()),
                "table_count": len([t for t in tables if t and len(t) >= 2]),
            }
            toon["document_structure"].append(page_info)

            for t_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue

                t_type = detect_table_type(table)
                parsed = parse_table(table, t_type, page_num, t_idx)

                if not parsed:
                    continue

                if t_type == 'VICTIM_TRANSACTION_TABLE':
                    toon["sections"]["victim_transactions"].extend(parsed)
                elif t_type == 'LAYERED_TRANSACTION_TABLE':
                    toon["sections"]["layered_transactions"].extend(parsed)
                elif t_type == 'SUSPECT_TABLE':
                    toon["sections"]["suspect_details"].extend(parsed)
                elif t_type == 'BANK_PENDING_TABLE':
                    toon["sections"]["bank_pending_summary"].extend(parsed)
                elif t_type == 'HOLD_TABLE':
                    toon["sections"]["hold_transactions"].extend(parsed)
                elif t_type == 'ATM_TABLE':
                    toon["sections"]["atm_withdrawals"].extend(parsed)
                elif t_type not in ('ATTACHMENT_TABLE',):
                    toon["sections"]["misc_tables"].append({
                        "page": page_num, "table_index": t_idx,
                        "table_type": t_type, "rows": parsed,
                    })

    # KV extraction from first 3 pages
    full_text = '\n'.join(all_page_texts[:3])
    kv = extract_kv(full_text)
    toon["sections"]["victim_details"] = {k: v for k, v in kv.items() if k.startswith('victim_')}
    toon["sections"]["case_metadata"]  = {k: v for k, v in kv.items() if not k.startswith('victim_')}

    toon["meta"]["summary"] = {
        "victim_transactions_count":  len(toon["sections"]["victim_transactions"]),
        "layered_transactions_count": len(toon["sections"]["layered_transactions"]),
        "bank_pending_entries":       len(toon["sections"]["bank_pending_summary"]),
        "hold_entries":               len(toon["sections"]["hold_transactions"]),
        "atm_withdrawal_entries":     len(toon["sections"]["atm_withdrawals"]),
        "suspect_entries":            len(toon["sections"]["suspect_details"]),
    }
    toon["meta"]["evidence_capture"] = {
        "row_provenance_enabled": True,
        "raw_cells_enabled": True,
        "raw_row_text_enabled": True,
        "page_text_available": True,
    }
    toon["page_text"] = page_text_map

    return toon


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python phase1_toon_parser.py <input.pdf> [output.json]")
        sys.exit(1)

    input_pdf   = sys.argv[1]
    output_json = sys.argv[2] if len(sys.argv) > 2 else Path(input_pdf).stem + '_TOON.json'

    print(f"[+] Parsing: {input_pdf}")
    toon = parse_pdf(input_pdf)

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(toon, f, indent=2, ensure_ascii=False)

    print(f"[+] TOON saved: {output_json}")
    print(f"[+] Summary:")
    for k, v in toon["meta"]["summary"].items():
        print(f"    {k}: {v}")


if __name__ == '__main__':
    main()
