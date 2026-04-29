import json

with open('Full Details of Complaint Report Manish Tandon - Copy_phase1_test.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for table in data['sections'].get('misc_tables', []):
    print(f"Misc Table Page {table['page']} Type: {table['table_type']} Rows: {len(table['rows'])}")
    if len(table['rows']) > 0:
        for k, v in table['rows'][0].items():
            if k.startswith('col_'):
                print(f"  {k}: {v}")
