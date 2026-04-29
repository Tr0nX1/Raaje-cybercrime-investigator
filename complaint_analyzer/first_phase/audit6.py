import json

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for row in data['sections']['layered_transactions']:
    if row['sno'] == '6':
        print(json.dumps(row['raw_cells'], indent=2))
        break
