"""
Main pipeline — routes each PDF through text or OCR extraction,
supports processing multiple PDFs in parallel.
"""
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from extractor.detector import is_text_based, detect_pdf_type
from extractor.text_extractor import extract_text_pdf, extract_mixed_pdf
from extractor.ocr_extractor import extract_ocr_pdf
from models.schema import BankStatement
from analyzer import bank_auditor


def process_single(pdf_path: str, ocr_dpi: int = 200, ocr_workers: int = 4) -> BankStatement:
    """
    Auto-detect PDF type and extract accordingly.
    Returns a BankStatement object.
    FIX-01: Password-protected PDFs return a BankStatement with a warning instead of crashing.
    """
    try:
        pdf_type = detect_pdf_type(pdf_path)

        if pdf_type == "text":
            print(f"[text]  {os.path.basename(pdf_path)}")
            stmt = extract_text_pdf(pdf_path)
        elif pdf_type == "mixed":
            print(f"[mixed] {os.path.basename(pdf_path)}")
            stmt = extract_mixed_pdf(pdf_path, ocr_dpi=ocr_dpi, ocr_workers=ocr_workers)
        else:  # scanned
            print(f"[ocr]   {os.path.basename(pdf_path)}")
            stmt = extract_ocr_pdf(pdf_path, dpi=ocr_dpi, max_workers=ocr_workers)
        
        # Apply LLM Audit and Auto-Healing
        try:
            if stmt.transactions:
                stmt.transactions = bank_auditor.run_audit_batch(stmt.transactions)
            
            # Header Audit (Holder, Account #, Balances)
            stmt = bank_auditor.run_header_audit(stmt)
        except Exception as audit_err:
            import traceback
            print(f"[warn] Audit layer failed for {os.path.basename(pdf_path)}: {audit_err}")
            traceback.print_exc()
            
        return stmt
    except Exception as e:
        err_str = str(type(e).__name__)
        if "Password" in err_str or "password" in str(e).lower() or "encrypted" in str(e).lower():
            print(f"[skip]  {os.path.basename(pdf_path)} — password-protected")
            stmt = BankStatement(source_file=pdf_path, extraction_method="failed")
            stmt.warnings = [f"PDF is password-protected — provide password to extract ({type(e).__name__})"]
            return stmt
        raise


def _worker(args: tuple) -> dict:
    """ProcessPoolExecutor worker — returns serializable dict."""
    pdf_path, ocr_dpi, ocr_workers = args
    statement = process_single(pdf_path, ocr_dpi, ocr_workers)
    return statement.model_dump(mode="json")


def process_batch(
    pdf_paths: list[str],
    output_dir: str = "output",
    max_parallel_pdfs: int = 2,
    ocr_dpi: int = 200,
    ocr_workers: int = 4,
    output_format: str = "json",   # "json" | "toon" | "both"
) -> list[BankStatement]:
    """
    Process multiple PDFs in parallel.
    Saves output files to output_dir.
    Returns list of BankStatement objects.
    """
    os.makedirs(output_dir, exist_ok=True)
    results: list[BankStatement] = []

    args_list = [(p, ocr_dpi, ocr_workers) for p in pdf_paths]

    with ProcessPoolExecutor(max_workers=max_parallel_pdfs) as executor:
        future_map = {executor.submit(_worker, args): args[0] for args in args_list}

        for future in as_completed(future_map):
            pdf_path = future_map[future]
            stem = Path(pdf_path).stem

            try:
                data = future.result()
                statement = BankStatement(**data)
                results.append(statement)

                if output_format in ("json", "both"):
                    out_path = os.path.join(output_dir, f"{stem}.json")
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, default=str)
                    print(f"  saved -> {out_path}")

                if output_format in ("toon", "both"):
                    out_path = os.path.join(output_dir, f"{stem}.toon")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(statement.to_toon())
                    print(f"  saved -> {out_path}")

            except Exception as e:
                print(f"  ERROR processing {pdf_path}: {e}")

    return results
