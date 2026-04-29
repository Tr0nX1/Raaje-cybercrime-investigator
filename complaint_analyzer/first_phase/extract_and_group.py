import json
from collections import defaultdict

# Load the JSON file
with open('Full Details of Complaint Report Manish Tandon - Copy_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Dictionary to store grouped transactions
groups = defaultdict(lambda: {'transactions': [], 'total_amount': 0, 'total_recovered': 0})

# Process layered_transactions
for txn in data['sections'].get('layered_transactions', []):
    from_acc = txn.get('source_account', '').strip()
    to_acc = txn.get('destination_account', '').strip()
    bank = txn.get('bank', '').strip()
    txn_id = txn.get('transaction_utr', '').strip()
    
    # Parse amount (remove commas and convert to float)
    amount_str = txn.get('amount', '0').replace(',', '').strip()
    try:
        amount = float(amount_str)
    except:
        amount = 0
    
    # Parse recovered amount (disputed_amount)
    recovered_str = txn.get('disputed_amount', '0').replace(',', '').strip()
    try:
        recovered = float(recovered_str)
    except:
        recovered = 0
    
    # Skip if no transaction ID
    if not txn_id or txn_id.lower() in ('', 'na', 'rr', 'referremark'):
        continue
    
    # Create grouping key
    key = (from_acc, to_acc, bank)
    
    # Add to group
    groups[key]['transactions'].append(txn_id)
    groups[key]['total_amount'] += amount
    groups[key]['total_recovered'] += recovered

# Process victim_transactions
for txn in data['sections'].get('victim_transactions', []):
    from_acc = txn.get('wallet_id', '').strip()
    to_acc = ''  # Not explicitly provided, use wallet_entity as proxy
    bank = txn.get('bank', '').strip()
    txn_id = txn.get('transaction_id', '').strip()
    
    # Parse amount
    amount_str = txn.get('amount', '0').replace(',', '').strip()
    try:
        amount = float(amount_str)
    except:
        amount = 0
    
    # No recovered amount in victim_transactions, default to 0
    recovered = 0
    
    # Skip if no transaction ID or to_account
    if not txn_id or not from_acc:
        continue
    
    # Create grouping key
    key = (from_acc, to_acc, bank)
    
    # Add to group
    groups[key]['transactions'].append(txn_id)
    groups[key]['total_amount'] += amount
    groups[key]['total_recovered'] += recovered

# Generate output
output = []

for idx, (key, data_group) in enumerate(sorted(groups.items()), 1):
    from_acc, to_acc, bank = key
    transactions = data_group['transactions']
    total_amount = data_group['total_amount']
    total_recovered = data_group['total_recovered']
    
    # Format currency amounts
    amount_formatted = f"{total_amount:,.2f}"
    recovered_formatted = f"{total_recovered:,.2f}"
    
    # Build output
    output.append(f"From Account Number: {from_acc}")
    output.append(f"To Account Number: {to_acc}")
    output.append(f"Bank Name: {bank}")
    output.append(f"Total Amount: Rs. {amount_formatted}")
    output.append(f"Total Recovered Amount: Rs. {recovered_formatted}")
    output.append("")
    
    # Add transaction IDs
    for txn_idx, txn_id in enumerate(transactions, 1):
        output.append(f"#{txn_idx} Transaction ID: {txn_id}")
    
    output.append("")
    output.append("-" * 80)
    output.append("")

# Save and print output
with open('grouped_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print('\n'.join(output))
print(f"\n[Total groups: {len(groups)}]")
print(f"Output saved to: grouped_output.txt")
