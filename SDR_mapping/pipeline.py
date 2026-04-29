"""
Main pipeline — routes each PDF through text or OCR extraction,
supports processing multiple SDR PDFs in parallel.
"""
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from extractor.detector import detect_pdf_type, detect_report_type
from extractor.ocr_extractor import extract_ocr_pdf
from extractor.unstructured_extractor import extract_unstructured_pdf
from models.schema import SDRReport
from analyzer.sdr_analyzer import validate_sdr_report, analyze_sdr_patterns


def process_single(
    pdf_path: str, 
    ocr_dpi: int = 200, 
    ocr_workers: int = 4,
    method: str = "auto"
) -> SDRReport:
    """
    Extract SDR report accordingly based on method.
    Returns an SDRReport object.
    """
    try:
        if method == "auto":
            pdf_type = detect_pdf_type(pdf_path)
            if pdf_type == "text":
                method = "text"
            else:
                method = "ocr"

        if method == "text":
            print(f"[text]  {os.path.basename(pdf_path)}")
            report = extract_text_pdf(pdf_path)
        elif method == "unstructured":
            print(f"[unstructured] {os.path.basename(pdf_path)}")
            report = extract_unstructured_pdf(pdf_path)
        else:  # ocr
            print(f"[ocr]   {os.path.basename(pdf_path)}")
            report = extract_ocr_pdf(pdf_path, dpi=ocr_dpi, max_workers=ocr_workers)

        # Apply analysis and validation
        try:
            validation_result = validate_sdr_report(report)
            report.warnings.extend([f"Validation: {issue}" for issue in validation_result["issues"]])

            # Add analysis insights as metadata
            analysis = analyze_sdr_patterns(report)
            # Store analysis in warnings for now (could be extended to a separate field)
            report.warnings.append(f"Analysis: {json.dumps(analysis, indent=2)}")

        except Exception as analysis_err:
            import traceback
            print(f"[warn] Analysis failed for {os.path.basename(pdf_path)}: {analysis_err}")
            traceback.print_exc()

        return report
    except Exception as e:
        err_str = str(type(e).__name__)
        print(f"[error] Failed to process {os.path.basename(pdf_path)}: {err_str}")

        # Return a minimal error report
        error_report = SDRReport(
            source_file=pdf_path,
            extraction_method="failed",
            warnings=[f"Processing failed: {err_str}"]
        )
        return error_report


def process_batch(
    pdf_dir: str, 
    output_dir: str = "output", 
    ocr_dpi: int = 200, 
    ocr_workers: int = 4, 
    max_workers: int = 4,
    method: str = "auto"
) -> dict:
    """
    Process all PDFs in a directory and save results to JSON files.
    """
    pdf_dir = Path(pdf_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Find all PDF files
    pdf_files = list(pdf_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}")
        return {"processed": 0, "successful": 0, "failed": 0}

    print(f"Found {len(pdf_files)} PDF files to process")

    results = []
    successful = 0
    failed = 0

    # Process PDFs in parallel
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        future_to_pdf = {
            executor.submit(process_single, str(pdf_path), ocr_dpi, ocr_workers, method): pdf_path
            for pdf_path in pdf_files
        }

        for future in as_completed(future_to_pdf):
            pdf_path = future_to_pdf[future]
            try:
                report = future.result()

                # Generate output filename
                base_name = pdf_path.stem
                output_file = output_dir / f"{base_name}.json"

                # Save to JSON
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(report.to_dict(), f, indent=2, ensure_ascii=False, default=str)

                results.append({
                    "file": str(pdf_path),
                    "output": str(output_file),
                    "success": len(report.warnings) == 0 or not any("failed" in w.lower() for w in report.warnings),
                    "report_type": report.report_type,
                    "phone_number": report.phone_number
                })

                if len(report.warnings) == 0 or not any("failed" in w.lower() for w in report.warnings):
                    successful += 1
                    print(f"[✓] {base_name} -> {output_file.name}")
                else:
                    failed += 1
                    print(f"[✗] {base_name} -> {output_file.name} (warnings: {len(report.warnings)})")

            except Exception as exc:
                failed += 1
                print(f"[error] {pdf_path.name} failed: {exc}")
                results.append({
                    "file": str(pdf_path),
                    "error": str(exc),
                    "success": False
                })

    summary = {
        "processed": len(pdf_files),
        "successful": successful,
        "failed": failed,
        "results": results
    }

    # Save summary
    summary_file = output_dir / "processing_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nProcessing complete: {successful}/{len(pdf_files)} successful")
    print(f"Summary saved to: {summary_file}")

    return summary