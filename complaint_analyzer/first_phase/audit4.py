import json
import re

def _looks_like_transaction_id(value):
    text = str(value or '').replace(" ", "")
    if not text:
        return False
    return bool(re.fullmatch(r'[A-Z0-9\-\/]{8,25}', text, re.I))

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

layered = data['sections']['layered_transactions']

count = sum(1 for row in layered if _looks_like_transaction_id(row.get('bank')))
print(f"bank_looks_like_id count: {count}")
