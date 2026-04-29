import pdfplumber
import os

pdf_path = "input/9560978030 - Khoj OSINT Report.pdf"
if os.path.exists(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
        
        print("--- EXTRACTED TEXT ---")
        print(full_text)
        print("--- END TEXT ---")
else:
    print(f"File not found: {pdf_path}")
