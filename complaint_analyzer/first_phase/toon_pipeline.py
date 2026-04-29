import subprocess
import sys
import os
from pathlib import Path

def run_pipeline(input_pdf):
    pdf_path = Path(input_pdf)
    if not pdf_path.exists():
        print(f"Error: File {input_pdf} not found.")
        return

    basename = pdf_path.stem
    raw_json = f"{basename}_raw.json"
    final_json = f"{basename}_forensic.json"

    print(f"[Step 1/2] Parsing PDF: {input_pdf}...")
    try:
        subprocess.run([sys.executable, "phase1_toon_parser.py", str(input_pdf), raw_json], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during parsing: {e}")
        return

    print(f"[Step 2/2] Applying Forensic Correction...")
    try:
        import phase2_toon_corrector
        phase2_toon_corrector.run_correction(raw_json, final_json)
    except Exception as e:
        print(f"Error during correction: {e}")
        return

    print(f"[Success] Generated forensic report: {final_json}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python toon_pipeline.py <input.pdf>")
    else:
        run_pipeline(sys.argv[1])
