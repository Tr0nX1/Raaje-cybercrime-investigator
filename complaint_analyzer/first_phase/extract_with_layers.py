import json
from collections import defaultdict
from datetime import datetime

# Load the JSON file
with open('Full Details of Complaint Report Manish Tandon - Copy_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Create a lookup dictionary for all transactions by ID
txn_lookup = {}

# Index layered_transactions
for txn in data['sections'].get('layered_transactions', []):
    txn_id = txn.get('transaction_utr', '').strip()
    if txn_id and txn_id.lower() not in ('', 'na', 'rr', 'referremark'):
        txn_lookup[txn_id] = {
            'source_account': txn.get('source_account', ''),
            'destination_account': txn.get('destination_account', ''),
            'bank': txn.get('bank', ''),
            'layer': txn.get('layer', ''),
            'amount': txn.get('amount', '0'),
            'disputed_amount': txn.get('disputed_amount', '0'),
            'datetime': txn.get('datetime', ''),
            'source_type': txn.get('source_type', ''),
            'transaction_type': 'Layered',
        }

# Index victim_transactions
for txn in data['sections'].get('victim_transactions', []):
    txn_id = txn.get('transaction_id', '').strip()
    if txn_id and txn_id.lower() not in ('', 'na', 'rr', 'referremark'):
        txn_lookup[txn_id] = {
            'source_account': txn.get('wallet_id', ''),
            'destination_account': '',
            'bank': txn.get('bank', ''),
            'layer': '',  # Victim transactions don't have layer
            'amount': txn.get('amount', '0'),
            'disputed_amount': '0',  # Not available
            'datetime': txn.get('transaction_datetime', ''),
            'source_type': 'wallet',
            'transaction_type': txn.get('transaction_type', 'NEFT/IMPS'),
        }

# Dictionary to store grouped transactions
groups = defaultdict(lambda: {'transactions': [], 'layers': set(), 'details': []})

# Process layered_transactions
for txn in data['sections'].get('layered_transactions', []):
    from_acc = txn.get('source_account', '').strip()
    to_acc = txn.get('destination_account', '').strip()
    bank = txn.get('bank', '').strip()
    txn_id = txn.get('transaction_utr', '').strip()
    layer = txn.get('layer', '').strip()
    
    if not txn_id or txn_id.lower() in ('', 'na', 'rr', 'referremark'):
        continue
    
    key = (from_acc, to_acc, bank)
    groups[key]['transactions'].append(txn_id)
    if layer:
        groups[key]['layers'].add(layer)
    groups[key]['details'].append({
        'txn_id': txn_id,
        'layer': layer,
        'amount': txn.get('amount', '0'),
        'disputed_amount': txn.get('disputed_amount', '0'),
        'datetime': txn.get('datetime', ''),
        'source_type': txn.get('source_type', ''),
        'transaction_type': 'Layered',
    })

# Process victim_transactions
for txn in data['sections'].get('victim_transactions', []):
    from_acc = txn.get('wallet_id', '').strip()
    to_acc = ''
    bank = txn.get('bank', '').strip()
    txn_id = txn.get('transaction_id', '').strip()
    
    if not txn_id or not from_acc:
        continue
    
    key = (from_acc, to_acc, bank)
    groups[key]['transactions'].append(txn_id)
    groups[key]['layers'].add('')  # Victim transactions have no layer
    groups[key]['details'].append({
        'txn_id': txn_id,
        'layer': '',
        'amount': txn.get('amount', '0'),
        'disputed_amount': '0',
        'datetime': txn.get('transaction_datetime', ''),
        'source_type': 'wallet',
        'transaction_type': txn.get('transaction_type', 'NEFT/IMPS'),
    })

# Generate output
output = []

for idx, (key, group_data) in enumerate(sorted(groups.items()), 1):
    from_acc, to_acc, bank = key
    transactions = group_data['transactions']
    layers_set = group_data['layers']
    details_list = group_data['details']
    
    # Determine layer assignment
    layers_list = list(layers_set)
    if len(layers_list) == 1:
        assigned_layer = layers_list[0] if layers_list[0] else "N/A"
        layer_status = assigned_layer
    else:
        assigned_layer = "INCONSISTENT"
        layer_status = f"INCONSISTENT ({', '.join(layers_list)})"
    
    # Calculate totals
    total_amount = 0
    total_recovered = 0
    
    for detail in details_list:
        amount_str = detail['amount'].replace(',', '').strip()
        try:
            total_amount += float(amount_str)
        except:
            pass
        
        disputed_str = detail['disputed_amount'].replace(',', '').strip()
        try:
            total_recovered += float(disputed_str)
        except:
            pass
    
    amount_formatted = f"{total_amount:,.2f}"
    recovered_formatted = f"{total_recovered:,.2f}"
    
    # Build output
    output.append(f"Layer: {layer_status}")
    output.append(f"")
    output.append(f"From Account Number: {from_acc}")
    output.append(f"To Account Number: {to_acc}")
    output.append(f"Bank Name: {bank}")
    output.append(f"Total Amount: Rs. {amount_formatted}")
    output.append(f"Total Recovered Amount: Rs. {recovered_formatted}")
    output.append(f"")
    
    # Add transaction details
    for txn_idx, detail in enumerate(details_list, 1):
        output.append(f"#{txn_idx} Transaction ID: {detail['txn_id']}")
        output.append(f"Transaction Type: {detail['transaction_type']}")
        output.append(f"Transaction Amount: Rs. {detail['amount']}")
        output.append(f"Disputed Amount: Rs. {detail['disputed_amount']}")
        output.append(f"Transaction Date: {detail['datetime']}")
        output.append(f"")
    
    output.append("=" * 100)
    output.append("")

# Save and print output
with open('layered_grouped_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('\n'.join(output[:100]))  # Print first 100 lines
print("\n... (output truncated for display)")
print(f"\n[Total groups: {len(groups)}]")
print(f"Output saved to: layered_grouped_output.txt")
