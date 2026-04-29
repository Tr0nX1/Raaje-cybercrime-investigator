import json

with open('Full Details of Complaint Report Manish Tandon - Copy_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

count = 0
for row in data['sections'].get('layered_transactions', []):
    bank = row.get('bank', '')
    if any(char.isdigit() for char in bank):
        print(f"SNO: {row.get('sno')} Bank: {bank}")
        count += 1
        if count >= 10:
            break
