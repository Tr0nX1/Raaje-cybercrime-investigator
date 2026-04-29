import json
import re

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

layered = data['sections']['layered_transactions']

for i, row in enumerate(layered):
    bank = row.get('bank', '')
    if any(char.isdigit() for char in bank):
        print(f"Row {i} SNO {row.get('sno')}: bank='{bank}'")
