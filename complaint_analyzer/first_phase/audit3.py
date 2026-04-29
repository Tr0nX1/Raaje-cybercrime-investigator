import json

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

layered = data['sections']['layered_transactions']

count_empty = 0
count_id = 0
for row in layered:
    bank = row.get('bank', '')
    if not bank:
        count_empty += 1
    if len(bank) >= 8 and bank.replace(' ', '').isdigit():
        count_id += 1
        
print(f"Empty bank: {count_empty}")
print(f"Bank is purely digits: {count_id}")

bank_ids = []
for row in layered:
    # the user might check if the bank doesn't match a known bank keyword
    if not any(k in row.get('bank', '').lower() for k in ["bank", "pay", "commerce", "limited", "ltd", "finance", "merchant"]):
        bank_ids.append(row.get('bank'))
print(f"Bank doesn't look like a bank: {len(bank_ids)}")
print(bank_ids[:10])
