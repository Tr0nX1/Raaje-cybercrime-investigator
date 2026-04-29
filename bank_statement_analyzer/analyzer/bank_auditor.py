import logging
import re
import sys
import os
import asyncio

# Ensure we can import llm_service from the other module for now
# Ideally, llm_service should be in a shared location
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../complaint_analyzer/first_phase')))
import llm_service

logger = logging.getLogger(__name__)

# Update the endpoint for bank statements
llm_service.LLM_AUDIT_ENDPOINT = "http://localhost:8000/audit/bank_statement"

def validate_transaction(txn):
    """
    Validates a bank statement transaction.
    """
    issues = []
    if txn.date is None:
        issues.append("Missing date")
    if not txn.description or not txn.description.strip():
        issues.append("Missing description")
    if txn.amount is None or txn.amount <= 0:
        issues.append("Missing or zero amount")
    if txn.balance is None:
        issues.append("Missing balance")
        
    return {
        "is_valid": len(issues) == 0,
        "issues": issues
    }

def compute_quality_score(txn):
    """
    Computes a quality score between 0.0 and 1.0.
    """
    score = 0
    if txn.date is not None:
        score += 1
    if txn.description and txn.description.strip():
        score += 1
    if txn.amount is not None and txn.amount > 0:
        score += 1
    if txn.balance is not None:
        score += 1
    return score / 4.0

def is_fixable(txn, issues):
    """
    Determines if a transaction is fixable via LLM.
    """
    raw_text = getattr(txn, 'raw_text', '') or ""
    if not raw_text.strip():
        return False
        
    needs_numbers = any("amount" in i or "balance" in i for i in issues)
    has_numbers = bool(re.search(r'\d', raw_text))
    if needs_numbers and not has_numbers:
        return False
        
    needs_letters = any("description" in i for i in issues)
    has_letters = bool(re.search(r'[A-Za-z]', raw_text))
    if needs_letters and not has_letters:
        return False
        
    return True

def run_audit_batch(transactions):
    """
    Synchronous entry point to audit a list of Transaction objects.
    """
    to_audit = []
    results_map = {} # txn_id -> result
    
    # Identify which transactions need auditing
    for idx, txn in enumerate(transactions):
        validation = validate_transaction(txn)
        score = compute_quality_score(txn)
        
        # Threshold for auditing
        if score < 0.99:
            if not is_fixable(txn, validation['issues']):
                txn.audit = {"score": score, "fixable": False, "llm_used": False, "status": "invalid"}
            else:
                # Track original object for later update
                txn._temp_id = id(txn)
                txn._temp_score = score
                to_audit.append(txn)
        else:
            txn.audit = {"score": score, "fixable": True, "llm_used": False, "status": "clean"}

    if to_audit:
        logger.info(f"Sending {len(to_audit)} Bank Statement transactions to LLM concurrently...")
        
        # Convert Pydantic models to dicts for transport
        payloads = [t.model_dump(mode="json") for t in to_audit]
        
        # Run async batch
        audit_results = llm_service.run_llm_audit_batch(payloads)
        
        for i, result in enumerate(audit_results):
            orig_txn = to_audit[i]
            corrected_dict = result["corrected"]
            score = getattr(orig_txn, '_temp_score', 0)
            
            if result["status"] == "success" and corrected_dict:
                # Update original object safely
                if "description" in corrected_dict:
                    orig_txn.description = corrected_dict["description"]
                if "amount" in corrected_dict and corrected_dict["amount"] is not None:
                    orig_txn.amount = float(corrected_dict["amount"])
                if "balance" in corrected_dict and corrected_dict["balance"] is not None:
                    orig_txn.balance = float(corrected_dict["balance"])
                if "type" in corrected_dict:
                    orig_txn.type = corrected_dict["type"]
                
                orig_txn.audit = {"score": score, "fixable": True, "llm_used": True, "status": "audited"}

            # FORENSIC FALLBACK (Run if LLM failed OR if LLM succeeded but still missing balance)
            if orig_txn.balance is None:
                raw = getattr(orig_txn, 'raw_text', '') or ""
                # Match number at the end of raw_text before optional CR/DR
                match = re.search(r'\|\s*([\d,]+\.\d{2})\s*(?:CR|DR)?$', raw)
                if match:
                    try:
                        val = float(match.group(1).replace(',', ''))
                        orig_txn.balance = val
                        prev_status = orig_txn.audit.get("status") if hasattr(orig_txn, 'audit') else "none"
                        orig_txn.audit = {
                            "score": score, 
                            "fixable": True, 
                            "llm_used": (prev_status == "audited"), 
                            "status": "forensic_recovered"
                        }
                    except:
                        if not hasattr(orig_txn, 'audit'):
                            orig_txn.audit = {"score": score, "fixable": True, "llm_used": False, "status": "fallback_failed"}
                else:
                    if not hasattr(orig_txn, 'audit'):
                        orig_txn.audit = {"score": score, "fixable": True, "llm_used": False, "status": "fallback_failed"}

    # Cleanup temp attributes
    for txn in transactions:
        if hasattr(txn, '_temp_id'): del txn._temp_id
        if hasattr(txn, '_temp_score'): del txn._temp_score
        
    return transactions

async def _audit_header_async(payload):
    """Internal async helper for header audit."""
    endpoint = "http://localhost:8000/audit/bank_header"
    return await llm_service.post_async(endpoint, payload)

def run_header_audit(statement):
    """
    Check for missing header fields and attempt to recover them via LLM.
    This is a synchronous wrapper for the async header audit.
    """
    acc = statement.account
    summ = statement.summary
    
    needs_audit = (
        not acc.holder_name or 
        not acc.account_number or 
        summ.opening_balance is None or 
        summ.closing_balance is None
    )
    
    if not needs_audit:
        return statement

    # Gather context from the first 2 pages of transactions (raw_text contains headers usually)
    context_text = ""
    for txn in statement.transactions[:50]: # First 50 txns usually cover first 1-2 pages
        context_text += (getattr(txn, 'raw_text', '') or "") + "\n"
    
    if not context_text.strip():
        return statement

    logger.info(f"Header fields missing for {statement.source_file}. Attempting LLM recovery...")
    
    system_prompt = """
    You are a forensic financial data extraction AI.
    Your task is to analyze raw bank statement text and extract structured information with maximum accuracy.
    STRICT RULES:
    1. Do NOT hallucinate any data.
    2. If a field is not clearly present, return null.
    3. Extract data exactly as seen (no assumptions).
    4. Preserve original formatting where possible.
    5. Output MUST be valid JSON only.
    """
    
    payload = {
        "system_prompt": system_prompt.strip(),
        "holder_name": acc.holder_name,
        "account_number": acc.account_number,
        "opening_balance": summ.opening_balance,
        "closing_balance": summ.closing_balance,
        "raw_context": context_text[:4000] # Cap context size
    }
    
    try:
        # Run the async post in a sync manner
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = None
            
        if loop and loop.is_running():
            result = asyncio.run_coroutine_threadsafe(_audit_header_async(payload), loop).result()
        else:
            result = asyncio.run(_audit_header_async(payload))
            
        if isinstance(result, dict) and result.get("status") == "success":
            corrected_meta = result.get("meta", {})
            conf = result.get("confidence", {})
            
            # Implementation of USER logic:
            # if deterministic != null -> use deterministic
            # else if ai_confidence == high -> use AI
            # else -> mark as "needs_review"
            
            def resolve(field_name, current_val, ai_key):
                ai_val = corrected_meta.get(ai_key)
                ai_conf = conf.get(ai_key, "low")
                
                if current_val is not None and str(current_val).strip():
                    return current_val, "deterministic"
                elif ai_val is not None and ai_conf == "high":
                    return ai_val, "ai_high_confidence"
                else:
                    return current_val, "needs_review"

            acc.holder_name, _ = resolve("holder", acc.holder_name, "account_holder_name")
            acc.account_number, _ = resolve("acc_num", acc.account_number, "account_number")
            
            # Opening balance needs numeric conversion
            op_val, op_status = resolve("open_bal", summ.opening_balance, "opening_balance")
            if op_status == "ai_high_confidence":
                try: 
                    summ.opening_balance = float(str(op_val).replace(',', ''))
                    op_status = "healed"
                except: pass
            
            # Closing balance
            cl_val, cl_status = resolve("close_bal", summ.closing_balance, "closing_balance")
            if cl_status == "ai_high_confidence":
                try: 
                    summ.closing_balance = float(str(cl_val).replace(',', ''))
                    cl_status = "healed"
                except: pass

            # Track metadata about the healing
            statement.warnings.append(f"AI Audit complete. Header Status: {op_status}/{cl_status}")
            logger.info(f"Header fields resolved. Holder: {acc.holder_name}, Acc: {acc.account_number}")
    except Exception as e:
        logger.error(f"Header audit failed: {e}")
        
    # FINAL FALLBACK: Infer balances from transactions if still null
    if summ.opening_balance is None and statement.transactions:
        first = statement.transactions[0]
        if first.balance is not None and first.amount is not None:
            if first.type == "credit":
                summ.opening_balance = round(first.balance - first.amount, 2)
            elif first.type == "debit":
                summ.opening_balance = round(first.balance + first.amount, 2)
            logger.info(f"Inferred opening balance: {summ.opening_balance}")

    if summ.closing_balance is None and statement.transactions:
        last = statement.transactions[-1]
        if last.balance is not None:
            summ.closing_balance = last.balance
            logger.info(f"Inferred closing balance: {summ.closing_balance}")

    # NEW: Propagation of Account Identity to all transactions
    # This ensures every row in JSON/TOON has the forensic identity
    for txn in statement.transactions:
        if not txn.holder_name:
            txn.holder_name = acc.holder_name
        if not txn.account_number:
            txn.account_number = acc.account_number
            
    return statement
