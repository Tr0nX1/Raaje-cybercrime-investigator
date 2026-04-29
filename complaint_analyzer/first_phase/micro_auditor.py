import json
import re
import logging
import llm_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

LLM_AUDIT_ENDPOINT = "http://localhost:8000/audit/transaction"


def validate_transaction(txn, txn_type="layered"):
    """
    Validates a transaction based on predefined forensic rules.
    Returns:
        dict: {"is_valid": bool, "issues": list of issue strings}
    """
    issues = []
    
    # 1. source_account must be >= 8 digits or meaningful string
    source_acc = str(txn.get("source_account", "")).strip()
    # A meaningful string is not empty and has some length
    if not source_acc:
        issues.append("Missing source_account")
    else:
        # If it's purely digits, must be >= 8
        digits_only = re.sub(r'\D', '', source_acc)
        if source_acc.isdigit() and len(source_acc) < 8:
            issues.append("source_account is numeric but less than 8 digits")
        elif not source_acc.isdigit() and len(source_acc) < 3:
            issues.append("source_account text is too short")

    # 2. source_utr must be >= 10 characters if present
    source_utr = str(txn.get("source_utr", "")).strip()
    if source_utr and len(source_utr) < 10:
        issues.append("source_utr is less than 10 characters")

    # Only apply destination rules to layered transactions
    if txn_type == "layered":
        # 3. destination_account must be >= 10 digits
        dest_acc = str(txn.get("destination_account", "")).strip()
        if not dest_acc:
            issues.append("Missing destination_account")
        else:
            dest_digits = re.sub(r'\D', '', dest_acc)
            if len(dest_digits) < 10:
                issues.append("destination_account has less than 10 digits")

        # 4. destination_ifsc must match pattern: [A-Z]{4}0[A-Z0-9]{6}
        dest_ifsc = str(txn.get("destination_ifsc", "")).strip().upper()
        if not dest_ifsc:
            issues.append("Missing destination_ifsc")
        elif not re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}', dest_ifsc):
            issues.append("destination_ifsc does not match standard 11-character format")

    # 5. bank must contain alphabets (not purely numeric)
    bank = str(txn.get("bank", "")).strip()
    if not bank:
        issues.append("Missing bank name")
    elif not re.search(r'[A-Za-z]', bank):
        issues.append("bank name is purely numeric or missing alphabets")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues
    }


def compute_quality_score(txn, txn_type="layered"):
    """
    Computes a quality score between 0.0 and 1.0 based on parameters.
    """
    score = 0
    max_score = 5.0 if txn_type == "layered" else 3.0
    
    # +1 if source_account present
    if str(txn.get("source_account", "")).strip():
        score += 1
        
    # +1 if source_utr valid
    source_utr = str(txn.get("source_utr", "")).strip()
    if not source_utr or len(source_utr) >= 10: 
        score += 1

    if txn_type == "layered":
        # +1 if destination_account valid (>= 10 digits)
        dest_acc = str(txn.get("destination_account", "")).strip()
        dest_digits = re.sub(r'\D', '', dest_acc)
        if len(dest_digits) >= 10:
            score += 1

        # +1 if destination_ifsc valid
        dest_ifsc = str(txn.get("destination_ifsc", "")).strip().upper()
        if re.fullmatch(r'[A-Z]{4}0[A-Z0-9]{6}', dest_ifsc):
            score += 1

    # +1 if bank valid (contains alphabets)
    bank = str(txn.get("bank", "")).strip()
    if re.search(r'[A-Za-z]', bank):
        score += 1

    return score / max_score


def is_fixable(txn, validation_issues):
    """
    Determines if a transaction is fixable by checking if the missing data
    actually exists somewhere within the raw unparsed text.
    """
    raw_text = str(txn.get('raw_row_text', ''))
    if not raw_text.strip():
        return False
        
    needs_numbers = any("account" in issue or "ifsc" in issue or "utr" in issue for issue in validation_issues)
    has_numbers_in_raw = bool(re.search(r'\d{10,}', raw_text))
    
    if needs_numbers and not has_numbers_in_raw:
        return False
        
    needs_letters = any("bank" in issue for issue in validation_issues)
    has_letters_in_raw = bool(re.search(r'[A-Za-z]', raw_text))
    
    if needs_letters and not has_letters_in_raw:
        return False
        
    return True

# Removed synchronous call_llm_auditor


def process_transactions(transactions, stats, txn_type="layered"):
    """
    Processes a list of transactions through the validation and LLM pipeline.
    """
    final_transactions = []
    to_audit = []
    clean_txns = []
    
    for idx, txn in enumerate(transactions):
        stats["total_transactions"] += 1
        
        # Validate and Score
        validation = validate_transaction(txn, txn_type)
        score = compute_quality_score(txn, txn_type)
        
        txn['_temp_score'] = score
        txn['_temp_idx'] = idx
        txn['_temp_issues'] = validation['issues']
        
        if score < 0.7:
            # Check Triage Rules: Fixable vs Non-Fixable
            fixable = is_fixable(txn, validation['issues'])
            if not fixable:
                logger.warning(f"Row {idx} (SNO: {txn.get('sno')}) scored {score:.2f} but lacks raw data. Marking INVALID.")
                txn['status'] = "invalid"
                txn["audit"] = {"score": score, "fixable": False, "llm_used": False}
                stats.setdefault("invalid_rejected", 0)
                stats["invalid_rejected"] += 1
                clean_txns.append(txn)
            else:
                to_audit.append(txn)
        else:
            stats["high_quality"] += 1
            txn['status'] = "clean"
            txn["audit"] = {"score": score, "fixable": True, "llm_used": False}
            clean_txns.append(txn)
            
    # Process all fixable transactions concurrently
    if to_audit:
        logger.info(f"Sending {len(to_audit)} transactions to LLM concurrently...")
        audit_results = llm_service.run_llm_audit_batch(to_audit)
        
        for result in audit_results:
            orig_txn = result["original"]
            corrected_txn = result["corrected"]
            
            idx = orig_txn.pop('_temp_idx', 'Unknown')
            score = orig_txn.pop('_temp_score', 0)
            orig_txn.pop('_temp_issues', None)
            
            if result["status"] == "success" and corrected_txn and isinstance(corrected_txn, dict):
                safe_txn = orig_txn.copy()
                for key in ["source_account", "source_utr", "destination_account", "destination_ifsc", "bank", "amount"]:
                    if key in corrected_txn:
                        safe_txn[key] = corrected_txn[key]
                
                safe_txn['status'] = "audited"
                safe_txn["audit"] = {"score": score, "fixable": True, "llm_used": True}
                clean_txns.append(safe_txn)
                stats["llm_used"] += 1
                logger.info(f"Row {idx} successfully audited by LLM.")
            else:
                logger.warning(f"Row {idx} LLM audit failed ({result['status']}). Falling back to original.")
                orig_txn['status'] = "fallback_failed"
                orig_txn["audit"] = {"score": score, "fixable": True, "llm_used": False}
                clean_txns.append(orig_txn)
                
    # Cleanup temp fields from clean_txns
    for txn in clean_txns:
        txn.pop('_temp_score', None)
        txn.pop('_temp_idx', None)
        txn.pop('_temp_issues', None)

    # Sort back to original order by SNO
    def get_sort_key(t):
        try:
            return int(t.get('sno', 0))
        except ValueError:
            return 999999
            
    final_transactions = sorted(clean_txns, key=get_sort_key)
    return final_transactions


def main(input_file, output_file):
    logger.info(f"Loading data from {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stats = {
        "total_transactions": 0,
        "llm_used": 0,
        "high_quality": 0
    }

    # Process Layered Transactions
    if 'sections' in data and 'layered_transactions' in data['sections']:
        logger.info("Processing layered_transactions...")
        data['sections']['layered_transactions'] = process_transactions(
            data['sections']['layered_transactions'], 
            stats,
            txn_type="layered"
        )

    # Process Victim Transactions
    if 'sections' in data and 'victim_transactions' in data['sections']:
        logger.info("Processing victim_transactions...")
        data['sections']['victim_transactions'] = process_transactions(
            data['sections']['victim_transactions'], 
            stats,
            txn_type="victim"
        )

    # Compile Final Output Structure
    final_output = {
        "meta": stats,
        "transactions": {
            "layered_transactions": data.get('sections', {}).get('layered_transactions', []),
            "victim_transactions": data.get('sections', {}).get('victim_transactions', [])
        }
    }

    # Optionally preserve other metadata or structure if needed by the downstream
    # We will output precisely the format requested in the prompt
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    logger.info(f"Processing complete. Saved to {output_file}")
    logger.info(f"Final Stats: {stats}")


if __name__ == "__main__":
    import sys
    
    in_file = sys.argv[1] if len(sys.argv) > 1 else 'Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json'
    out_file = sys.argv[2] if len(sys.argv) > 2 else 'Audited_Transactions.json'
    
    main(in_file, out_file)
