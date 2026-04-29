import json

files = [
    'Full Details of Complaint Report Manish Tandon - Copy_raw.json',
    'Full Details of Complaint Report Manish Tandon - Copy_forensic.json',
    'Refined_TOON_Report.json',
    'toon_output.json'
]

for filename in files:
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        layered = []
        if 'sections' in data and 'layered_transactions' in data['sections']:
            layered = data['sections']['layered_transactions']
        elif isinstance(data, list):
            layered = data
            
        bank_has_digits = 0
        for row in layered:
            bank = row.get('bank', '')
            if any(char.isdigit() for char in bank):
                bank_has_digits += 1
                
        print(f"{filename}: {len(layered)} layered transactions, {bank_has_digits} banks with digits")
    except Exception as e:
        print(f"Error reading {filename}: {e}")
