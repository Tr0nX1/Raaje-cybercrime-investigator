import json

def compare_files(old_file, new_file, output_file):
    with open(old_file, 'r', encoding='utf-8') as f:
        old_data = json.load(f)
        
    with open(new_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    # Convert to dictionaries for easy lookup by SNO
    old_txns = {}
    if 'sections' in old_data:
        for t in old_data['sections'].get('layered_transactions', []):
            old_txns[f"layered_{t.get('sno')}"] = t
        for t in old_data['sections'].get('victim_transactions', []):
            old_txns[f"victim_{t.get('sno')}"] = t

    new_txns = {}
    for t in new_data['transactions'].get('layered_transactions', []):
        new_txns[f"layered_{t.get('sno')}"] = t
    for t in new_data['transactions'].get('victim_transactions', []):
        new_txns[f"victim_{t.get('sno')}"] = t

    differences = []
    
    fields_to_check = ['source_account', 'source_utr', 'destination_account', 'destination_ifsc', 'bank', 'amount']
    
    for key, new_t in new_txns.items():
        old_t = old_txns.get(key)
        if not old_t:
            continue
            
        diffs = {}
        for field in fields_to_check:
            old_val = str(old_t.get(field, ''))
            new_val = str(new_t.get(field, ''))
            if old_val != new_val:
                diffs[field] = {'old': old_val, 'new': new_val}
                
        if diffs:
            differences.append({
                'sno': new_t.get('sno'),
                'type': key.split('_')[0],
                'diffs': diffs
            })

    # Write to report
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Comparing {old_file} vs {new_file}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total Transactions Audited: {len(new_txns)}\n")
        f.write(f"Transactions Changed: {len(differences)}\n\n")
        
        for d in differences:
            f.write(f"--- SNO: {d['sno']} ({d['type'].upper()}) ---\n")
            for field, vals in d['diffs'].items():
                f.write(f"  Field: {field}\n")
                f.write(f"    - OLD: {vals['old']}\n")
                f.write(f"    + NEW: {vals['new']}\n")
            f.write("\n")

if __name__ == "__main__":
    compare_files(
        'Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json',
        'Audited_Transactions.json',
        'comparison_report.txt'
    )
    print("Comparison complete. See comparison_report.txt")
