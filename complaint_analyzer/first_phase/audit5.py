import json

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

layered = data['sections']['layered_transactions']

with open('banks_dump.txt', 'w', encoding='utf-8') as f:
    for row in layered:
        f.write(f"SNO: {row.get('sno')} | Bank: {row.get('bank')} | raw_text: {row.get('raw_row_text')}\n")
