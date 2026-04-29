import json

with open('Full Details of Complaint Report Manish Tandon - Copy_raw.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"raw.json victim: {len(data['sections'].get('victim_transactions', []))}")
print(f"raw.json layered: {len(data['sections'].get('layered_transactions', []))}")
