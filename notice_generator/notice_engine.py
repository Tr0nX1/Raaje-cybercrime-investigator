import json
import os
from datetime import datetime
from core.filters import filter_transactions_by_layer
from core.grouper import group_by_bank
from core.templates import TemplateEngine
from core.generator import NoticeGenerator

def run_notice_generation(data_path, output_format='txt', layers=None, template_name='formal_notice', 
                          officer_details=None, letterhead_path=None, style_config=None):
    """
    Main orchestrator for notice generation with Letterhead and Style support.
    """
    if officer_details is None:
        officer_details = {
            'officer_name': 'Inspector John Doe',
            'officer_designation': 'Cyber Cell In-Charge',
            'police_station': 'Electronic City Cyber PS'
        }

    # 1. Load Data
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 2. Extract and Filter
    all_transactions = data.get('sections', {}).get('layered_transactions', [])
    filtered_txns = filter_transactions_by_layer(all_transactions, layers)
    
    if not filtered_txns:
        print("No transactions found for the specified layers.")
        return

    # 3. Group by Bank
    bank_groups = group_by_bank(filtered_txns)
    
    # 4. Initialize Components
    engine = TemplateEngine(os.path.join(os.path.dirname(__file__), 'templates'))
    
    # Initialize Generator with Letterhead and Style Config
    output_dir = os.path.join(os.path.dirname(__file__), 'output')
    generator = NoticeGenerator(output_dir, letterhead_path=letterhead_path, style_config=style_config)
    
    # 5. Generate Notices per Bank
    case_meta = data.get('sections', {}).get('case_metadata', {})
    generated_files = []

    for bank_name, bank_data in bank_groups.items():
        # Prepare Context
        transaction_summary = ""
        for t in bank_data['transactions']:
            transaction_summary += f"- Acct: {t['account']} | Date: {t['date']} | Amt: {t['amount']} | UTR: {t['utr']}\n"
        
        context = {
            'bank_name': bank_name,
            'account_numbers': ", ".join(bank_data['accounts']),
            'total_amount': f"{bank_data['total_amount']:,.2f}",
            'acknowledgement_no': case_meta.get('acknowledgement_no', 'N/A'),
            'incident_date': case_meta.get('incident_datetime', 'N/A'),
            'transaction_summary': transaction_summary,
            'current_date': datetime.now().strftime("%d/%m/%Y"),
            **officer_details
        }
        
        # Render
        template_content = engine.get_template_content(template_name)
        rendered_content = engine.render(template_content, context)
        
        # Save
        filename = generator.create_filename(bank_name)
        if output_format == 'docx':
            path = generator.generate_docx(filename, rendered_content)
        else:
            path = generator.generate_txt(filename, rendered_content)
            
        generated_files.append(path)
        print(f"Generated: {path}")

    return generated_files

if __name__ == "__main__":
    # Example Usage with Custom Style
    DATA_PATH = r"d:\developer\FFA\Refined_TOON_Report.json"
    
    # Custom Word Settings
    my_style = {
        'alignment': 'CENTER',
        'font_name': 'Times New Roman',
        'font_size': 12,
        'letterhead_width': 2.5 # Inches
    }
    
    # Optional: Path to a letterhead image (replace with real path if testing)
    # letterhead = "d:/developer/FFA/notice_generator/assets/police_logo.png"
    letterhead = None 

    targets = ["1"]
    template = "formal_notice"
    fmt = "docx"
    
    print(f"Starting Styled Notice Generation...")
    run_notice_generation(
        DATA_PATH, 
        output_format=fmt, 
        layers=targets, 
        template_name=template,
        letterhead_path=letterhead,
        style_config=my_style
    )
