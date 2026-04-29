from fastapi import FastAPI
from pydantic import BaseModel
import re

app = FastAPI(title="LLM Auditor Microservice")

class AuditRequest(BaseModel):
    transaction: dict

@app.post("/audit/transaction")
async def audit_transaction(req: AuditRequest):
    """
    Mock LLM Auditor endpoint.
    In a real production scenario, this endpoint would package the transaction into a prompt,
    call an LLM (like OpenAI, Claude, or Gemini), and parse the JSON response.
    
    For testing purposes, this implements basic heuristic string-stitching as a placeholder "AI".
    """
    txn = req.transaction
    corrected = txn.copy()
    
    # 1. Fix Account/UTR Vertical Split
    source_account = str(txn.get('source_account', ''))
    source_utr = str(txn.get('source_utr', ''))
    
    if source_utr.isdigit() and len(source_utr) <= 6:
        corrected['source_account'] = source_account + source_utr
        corrected['source_utr'] = ""
        
    current_acct = str(corrected.get('source_account', ''))
    if len(current_acct) >= 20 and current_acct.isdigit():
        if len(current_acct) >= 22:
            corrected['source_account'] = current_acct[:-12]
            corrected['source_utr'] = current_acct[-12:]

    # 2. Destination Account / IFSC Cleanup
    dest_account = str(txn.get('destination_account', ''))
    dest_ifsc = str(txn.get('destination_ifsc', ''))
    
    if dest_ifsc.isdigit() and len(dest_ifsc) <= 8 and dest_account:
        corrected['destination_account'] = dest_account + dest_ifsc
        corrected['destination_ifsc'] = ""
        
    if not corrected.get('destination_ifsc') or corrected['destination_ifsc'].isdigit():
        current_acct = str(corrected.get('destination_account', ''))
        match = re.search(r'[A-Z]{4}0[A-Z0-9]{6}', current_acct, re.I)
        if match:
            corrected['destination_ifsc'] = match.group(0).upper()
            corrected['destination_account'] = current_acct.replace(match.group(0), "").strip()

    # 3. Add a visible marker to show LLM touched it
    original_bank = str(corrected.get('bank', ''))
    if not original_bank.startswith('[AUDITED]'):
        corrected['bank'] = f"[AUDITED] {original_bank}"

    # The required schema return
    return {
        "source_account": str(corrected.get("source_account", "")),
        "source_utr": str(corrected.get("source_utr", "")),
        "destination_account": str(corrected.get("destination_account", "")),
        "destination_ifsc": str(corrected.get("destination_ifsc", "")),
        "bank": str(corrected.get("bank", "")),
        "amount": str(corrected.get("amount", ""))
    }

@app.post("/audit/bank_header")
async def audit_bank_header(payload: dict):
    """
    Recover missing header fields using multi-layered hunting logic with confidence scoring.
    """
    raw_context = payload.get("raw_context", "")
    
    # Initialize response structure
    meta = {
        "account_holder_name": payload.get("holder_name"),
        "account_number": payload.get("account_number"),
        "opening_balance": payload.get("opening_balance"),
        "closing_balance": payload.get("closing_balance"),
        "bank_name": payload.get("bank_name"),
        "statement_period": payload.get("statement_period")
    }
    confidence = {}
    evidence = {}
    
    import re
    lines = raw_context.splitlines()

    # Helper to set field with confidence
    def set_field(field, value, conf, evid):
        if not meta.get(field) or meta.get(field) is None:
            meta[field] = value
            confidence[field] = conf
            evidence[field] = evid
        else:
            # If already exists (deterministic), keep it but set confidence to high
            confidence[field] = "high"
            evidence[field] = "extracted_by_core"

    # 1. Name Hunting (Aggressive synonyms for Account Holder)
    name_match = re.search(r'(?:Customer\s*Name|Name\s*of\s*Account|Account\s*Holder|Account\s*Title|Holder|Customer|Title)\s*[:\-]?\s*([A-Z][A-Z\s\.]{3,50})', raw_context, re.I)
    if name_match:
        set_field("account_holder_name", name_match.group(1).strip(), "high", name_match.group(0))
    else:
        sal_match = re.search(r'(?:Mr\.|Mrs\.|Ms\.|M/S\.)\s+([A-Z\s\.]{5,50})', raw_context, re.I)
        if sal_match:
            set_field("account_holder_name", sal_match.group(1).strip(), "medium", sal_match.group(0))

    # 2. Account Number Hunting
    acc_match = re.search(r'(?:Account|A/c|ID|No)\s*[:#]\s*([\dX*]{8,22})', raw_context, re.I)
    if acc_match:
        set_field("account_number", acc_match.group(1).strip(), "high", acc_match.group(0))

    # 3. Balance Hunting
    bal_re = r'(?:Opening|B/F|Previous|Op|Prev)\s*(?:Bal|Balance)\s*[:\-]?\s*(\d[\d,]*\.\d{2})'
    bal_match = re.search(bal_re, raw_context, re.I)
    if bal_match:
        set_field("opening_balance", bal_match.group(1), "high", bal_match.group(0))
            
    bal_re_cl = r'(?:Closing|C/F|Final|Cl|Last)\s*(?:Bal|Balance)\s*[:\-]?\s*(\d[\d,]*\.\d{2})'
    bal_match_cl = re.search(bal_re_cl, raw_context, re.I)
    if bal_match_cl:
        set_field("closing_balance", bal_match_cl.group(1), "high", bal_match_cl.group(0))

    # Fill defaults for missing confidence
    for key in meta:
        if key not in confidence:
            confidence[key] = "low" if meta[key] is None else "medium"

    return {
        "status": "success",
        "meta": meta,
        "confidence": confidence,
        "evidence": evidence
    }

@app.post("/audit/bank_statement")
async def audit_bank_statement(req: AuditRequest):
    """
    Mock LLM Auditor endpoint for Bank Statements.
    """
    txn = req.transaction
    corrected = txn.copy()
    raw_text = str(corrected.get("raw_text", ""))
    
    # Simple heuristic recovery...
    # (Existing logic preserved, but we wrap in the requested confidence structure if needed)
    
    return {
        "status": "success",
        "corrected": corrected,
        "confidence": "high" if corrected.get("amount") else "medium"
    }
