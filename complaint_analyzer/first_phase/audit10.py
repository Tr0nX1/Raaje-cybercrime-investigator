import json
import collections

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

layered = data['sections']['layered_transactions']

short_utrs = []
for row in layered:
    utr = row.get('transaction_utr', '')
    if utr and len(utr) < 10:
        short_utrs.append(row)
        
print(f"Short UTRs: {len(short_utrs)}")
if short_utrs:
    print(short_utrs[0])
