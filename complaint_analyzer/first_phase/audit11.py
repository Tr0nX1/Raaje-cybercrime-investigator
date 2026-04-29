import json
import re

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

layered = data['sections']['layered_transactions']

malformed_dest = []
for row in layered:
    acct = row.get('destination_account', '')
    ifsc = row.get('destination_ifsc', '')
    if re.search(r'[A-Za-z]', acct) and not ifsc:
        malformed_dest.append(row)

print(f"Malformed dest_account (contains letters, no IFSC): {len(malformed_dest)}")
for r in malformed_dest[:5]:
    print(f"SNO {r['sno']}: Dest Acct = {r['destination_account']}")
