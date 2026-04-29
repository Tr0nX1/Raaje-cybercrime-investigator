import json
from collections import defaultdict, Counter

# Load the JSON file
with open('Full Details of Complaint Report Manish Tandon - Copy_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Dictionary to store grouped transactions
groups = defaultdict(lambda: {'layers': set()})

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
    if layer:
        groups[key]['layers'].add(layer)

# Process victim_transactions
for txn in data['sections'].get('victim_transactions', []):
    from_acc = txn.get('wallet_id', '').strip()
    to_acc = ''
    bank = txn.get('bank', '').strip()
    txn_id = txn.get('transaction_id', '').strip()
    
    if not txn_id or not from_acc:
        continue
    
    key = (from_acc, to_acc, bank)
    groups[key]['layers'].add('')  # Victim transactions have no layer

# Analysis
consistent_groups = {}
inconsistent_groups = []
victim_groups = []
layer_counts = Counter()

for key, group_data in groups.items():
    layers_set = group_data['layers']
    layers_list = list(layers_set)
    
    if len(layers_list) == 0:
        victim_groups.append(key)
    elif len(layers_list) == 1:
        layer = layers_list[0] if layers_list[0] else "N/A"
        if layer not in consistent_groups:
            consistent_groups[layer] = []
        consistent_groups[layer].append(key)
        if layer:
            layer_counts[layer] += 1
    else:
        inconsistent_groups.append((key, layers_list))

# Print summary
output = []
output.append("=" * 100)
output.append("LAYER ANALYSIS SUMMARY")
output.append("=" * 100)
output.append("")

output.append(f"Total Groups: {len(groups)}")
output.append(f"")
output.append(f"✓ Consistent Layer Groups: {sum(len(v) for v in consistent_groups.values())}")
output.append(f"✗ Inconsistent Layer Groups: {len(inconsistent_groups)}")
output.append(f"○ Victim Transaction Groups: {len(victim_groups)}")
output.append(f"")

output.append("=" * 100)
output.append("LAYER DISTRIBUTION (Consistent Groups Only)")
output.append("=" * 100)
output.append("")

if consistent_groups:
    for layer in sorted(consistent_groups.keys(), key=lambda x: (x == 'N/A', x)):
        count = len(consistent_groups[layer])
        percentage = (count / sum(len(v) for v in consistent_groups.values())) * 100
        output.append(f"Layer {layer}: {count} groups ({percentage:.1f}%)")
else:
    output.append("No consistent groups found.")

output.append("")
output.append("=" * 100)
output.append("INCONSISTENT GROUPS (Multiple Layers Per Group)")
output.append("=" * 100)
output.append("")

if inconsistent_groups:
    output.append(f"Total: {len(inconsistent_groups)}")
    output.append("")
    for idx, (key, layers) in enumerate(inconsistent_groups[:20], 1):
        from_acc, to_acc, bank = key
        output.append(f"{idx}. {from_acc[:30]:<30} → {to_acc[:30]:<30} | {bank[:30]:<30}")
        output.append(f"   Layers: {', '.join(sorted(layers, key=lambda x: (x == '', x)))}")
        output.append("")
    
    if len(inconsistent_groups) > 20:
        output.append(f"... and {len(inconsistent_groups) - 20} more inconsistent groups")
else:
    output.append("No inconsistent groups found.")

output.append("")
output.append("=" * 100)
output.append("LAYER STATISTICS")
output.append("=" * 100)
output.append("")

if layer_counts:
    total_txns = sum(layer_counts.values())
    for layer in sorted(layer_counts.keys(), key=lambda x: -layer_counts[x]):
        count = layer_counts[layer]
        percentage = (count / total_txns) * 100
        output.append(f"Layer {layer}: {count} transactions ({percentage:.1f}%)")
else:
    output.append("No layer statistics available.")

# Save output
with open('layer_analysis_summary.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

# Print to console
print('\n'.join(output))
