import json
import re

def forensic_audit(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    audit_report = {}
    summary = {"total_fields": 0, "fixed": 0, "needs_review": 0}
    
    # 1. Audit Account Holder
    original_holder = data['account']['holder_name']
    if original_holder:
        audit_report['account_holder_name'] = {
            "original": original_holder,
            "suggested": original_holder,
            "final": original_holder,
            "source": "deterministic",
            "confidence": "high",
            "reason": "Deterministic value present and valid."
        }
    summary['total_fields'] += 1

    # 2. Audit Account Number
    original_acc = data['account']['account_number']
    if original_acc and len(str(original_acc)) >= 10:
        audit_report['account_number'] = {
            "original": original_acc,
            "suggested": original_acc,
            "final": original_acc,
            "source": "deterministic",
            "confidence": "high",
            "reason": "Deterministic value matches forensic length rule (>= 10 digits)."
        }
    summary['total_fields'] += 1

    # 3. Repair Transaction Balances
    tx_fixed = 0
    for i, tx in enumerate(data['transactions']):
        if tx.get('balance') is None:
            raw = tx.get('raw_text', '')
            # Match number at the end of raw_text before CR/DR
            match = re.search(r'\|\s*([\d,]+\.\d{2})\s*(?:CR|DR)?$', raw)
            if match:
                val = float(match.group(1).replace(',', ''))
                tx['balance'] = val
                tx_fixed += 1
    
    # 4. Forensic Derivation of Summary Balances
    # Opening Balance
    if data['summary']['opening_balance'] is None and data['transactions']:
        first = data['transactions'][0]
        if first['balance'] is not None and first['amount'] is not None:
            if first['type'] == 'credit':
                op_bal = round(first['balance'] - first['amount'], 2)
            else:
                op_bal = round(first['balance'] + first['amount'], 2)
            
            data['summary']['opening_balance'] = op_bal
            audit_report['opening_balance'] = {
                "original": None,
                "suggested": op_bal,
                "final": op_bal,
                "source": "derived",
                "confidence": "high",
                "reason": f"Derived from first transaction: balance ({first['balance']}) - {first['type']} ({first['amount']})"
            }
            summary['fixed'] += 1
    summary['total_fields'] += 1

    # Closing Balance
    if data['summary']['closing_balance'] is None and data['transactions']:
        last = data['transactions'][-1]
        if last['balance'] is not None:
            data['summary']['closing_balance'] = last['balance']
            audit_report['closing_balance'] = {
                "original": None,
                "suggested": last['balance'],
                "final": last['balance'],
                "source": "derived",
                "confidence": "high",
                "reason": "Derived from last transaction balance."
            }
            summary['fixed'] += 1
    summary['total_fields'] += 1

    # Final Output
    output = {
        "final_data": data,
        "audit_report": audit_report,
        "summary": summary
    }
    
    return output

if __name__ == "__main__":
    result = forensic_audit("D:/develop/ffa/bank_statement_analyzer/output/AccountStmt_2007XXXXXX3121.json")
    print(json.dumps(result, indent=2))
