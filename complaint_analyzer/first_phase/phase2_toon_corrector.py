import json
import re

BANK_REGISTRY = [
    "Central Bank of India",
    "Jammu and Kashmir Bank",
    "Union Bank of India",
    "Utkarsh Small Finance Bank Limited",
    "State Bank of India",
    "HDFC Bank",
    "ICICI Bank",
    "Axis Bank",
    "Kotak Mahindra Bank",
    "Punjab National Bank",
    "Bank of Baroda",
    "Canara Bank",
    "Bank of India",
    "Indian Bank",
    "UCO Bank",
    "Bank of Maharashtra",
    "IDBI Bank",
    "Yes Bank",
    "Standard Chartered Bank",
    "Airtel Payments Bank",
    "Paytm Payments Bank"
]

def forensic_normalize_bank(partial_name):
    if not partial_name or len(partial_name) < 3:
        return partial_name
    
    # Try exact prefix match
    for full_name in BANK_REGISTRY:
        if full_name.lower().startswith(partial_name.lower()):
            return full_name
        # Also try "contains" if prefix fails
        if partial_name.lower() in full_name.lower() and len(partial_name) > 10:
             return full_name
    return partial_name

def correct_layered_transactions(transactions):
    corrected = []
    for txn in transactions:
        # Clone to avoid mutating original
        new_txn = txn.copy()
        
        # 1. Fix Account/UTR Vertical Split
        # Problem: Account is 15 digits. Line 1 (10 digits) -> source_account. Line 2 (5 digits) -> source_utr.
        # If source_utr is all digits and short, it's likely a fragment of the account.
        source_account = str(txn.get('source_account', ''))
        source_utr = str(txn.get('source_utr', ''))
        
        if source_utr.isdigit() and len(source_utr) <= 6:
            # Check if this node is Layered (starts with PHI or is Account)
            # Rebind
            new_txn['source_account'] = source_account + source_utr
            new_txn['source_utr'] = "" # Will be filled from transaction_utr if empty
        
        # 1b. Anomaly: Merged Account + UTR (Case SNo 29)
        # If source_account is > 18 digits, it likely swallowed the UTR.
        current_acct = str(new_txn.get('source_account', ''))
        if len(current_acct) >= 20 and current_acct.isdigit():
             # PNB Pattern: 16 digits account + 12 digits UTR
             if current_acct.startswith('0130') and len(current_acct) >= 28:
                  new_txn['source_account'] = current_acct[:16]
                  new_txn['source_utr'] = current_acct[16:]
             elif len(current_acct) >= 22:
                  # General heuristic: take first 11-16 digits as account
                  new_txn['source_account'] = current_acct[:-12]
                  new_txn['source_utr'] = current_acct[-12:]
        
        # 2. Normalize Bank Name
        new_txn['bank'] = forensic_normalize_bank(txn.get('bank', ''))
        
        # 3. Destination Account / IFSC Cleanup
        dest_account = str(txn.get('destination_account', ''))
        dest_ifsc = str(txn.get('destination_ifsc', ''))
        
        # If destination_ifsc is purely numeric and short, it's a split fragment
        if dest_ifsc.isdigit() and len(dest_ifsc) <= 8 and dest_account:
            new_txn['destination_account'] = dest_account + dest_ifsc
            new_txn['destination_ifsc'] = ""
        
        # Now re-check for a valid IFSC in the account or other fields
        if 'destination_account' in new_txn:
            if not new_txn.get('destination_ifsc') or new_txn['destination_ifsc'].isdigit():
                 current_acct = new_txn['destination_account']
                 # Look for 11-char IFSC signature
                 match = re.search(r'[A-Z]{4}0[A-Z0-9]{6}', current_acct, re.I)
                 if match:
                      new_txn['destination_ifsc'] = match.group(0).upper()
                      new_txn['destination_account'] = current_acct.replace(match.group(0), "").strip()

        # 4. Final Field Assignment
        # If source_utr is empty, move transaction_utr there for consistency
        if not new_txn.get('source_utr') and txn.get('transaction_utr'):
            new_txn['source_utr'] = txn.get('transaction_utr')

        corrected.append(new_txn)
    
    return corrected

def run_correction(input_path, output_path):
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Correct Layered Transactions
    layered = data['sections'].get('layered_transactions', [])
    data['sections']['layered_transactions'] = correct_layered_transactions(layered)
    
    # Correct Victim Transactions
    victim = data['sections'].get('victim_transactions', [])
    data['sections']['victim_transactions'] = correct_layered_transactions(victim)

    data['meta']['parser_phase'] = "Phase 2 - Forensic Correction & Pattern Stitching"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"Correction complete. Saved to {output_path}")

if __name__ == "__main__":
    run_correction('Refined_TOON_Report.json', 'Consolidated_Investigation_TOON.json')
