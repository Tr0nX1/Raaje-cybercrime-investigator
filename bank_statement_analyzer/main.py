"""
Bank Statement Analyzer - CLI entry point.

Usage examples:
    # single file -> JSON
    python main.py statement.pdf

    # single file -> TOON
    python main.py statement.pdf --format toon

    # batch folder -> both formats + full analysis report
    python main.py "input files/" --batch --format both --report

    # force OCR mode (even if text is selectable)
    python main.py statement.pdf --force-ocr
"""
import argparse
import json
import os
import sys
from pathlib import Path

# ensure console can handle UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from pipeline import process_single, process_batch
from analyzer.calculations import full_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bank Statement PDF -> JSON / TOON extractor and analyzer"
    )
    parser.add_argument("input", help="PDF file path or folder (with --batch)")
    parser.add_argument(
        "--batch", action="store_true",
        help="Process all PDFs in the input folder"
    )
    parser.add_argument(
        "--format", choices=["json", "toon", "both"], default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Directory to save output files (default: output/)"
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Generate full financial analysis report"
    )
    parser.add_argument(
        "--force-ocr", action="store_true",
        help="Force OCR mode even for text-based PDFs"
    )
    parser.add_argument(
        "--parallel", type=int, default=2,
        help="Number of PDFs to process in parallel for batch mode (default: 2)"
    )
    parser.add_argument(
        "--dpi", type=int, default=200,
        help="DPI for OCR rendering (higher = more accurate, slower, default: 200)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    if args.batch:
        # ── Batch mode ────────────────────────────────────────────────────────
        folder = args.input
        if not os.path.isdir(folder):
            print(f"ERROR: '{folder}' is not a directory. Use --batch with a folder.")
            sys.exit(1)

        pdf_paths = [
            str(p) for p in Path(folder).glob("**/*.pdf")
        ]
        if not pdf_paths:
            print(f"No PDFs found in '{folder}'")
            sys.exit(0)

        print(f"Found {len(pdf_paths)} PDF(s) - processing with {args.parallel} parallel workers...")
        statements = process_batch(
            pdf_paths=pdf_paths,
            output_dir=args.output_dir,
            max_parallel_pdfs=args.parallel,
            ocr_dpi=args.dpi,
            output_format=args.format,
        )

        if args.report:
            for stmt in statements:
                stem = Path(stmt.source_file).stem
                report = full_report(stmt)
                report_path = os.path.join(args.output_dir, f"{stem}_report.json")
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"  report -> {report_path}")

    else:
        # ── Single file mode ──────────────────────────────────────────────────
        pdf_path = args.input
        if not os.path.isfile(pdf_path):
            print(f"ERROR: '{pdf_path}' not found.")
            sys.exit(1)

        if args.force_ocr:
            from extractor.ocr_extractor import extract_ocr_pdf
            print(f"[ocr-forced] {os.path.basename(pdf_path)}")
            statement = extract_ocr_pdf(pdf_path, dpi=args.dpi)
        else:
            statement = process_single(pdf_path, ocr_dpi=args.dpi)

        stem = Path(pdf_path).stem

        if args.format in ("json", "both"):
            out_path = os.path.join(args.output_dir, f"{stem}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(statement.model_dump(mode="json"), f, indent=2, default=str)
            print(f"saved -> {out_path}")

        if args.format in ("toon", "both"):
            out_path = os.path.join(args.output_dir, f"{stem}.toon")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(statement.to_toon())
            print(f"saved -> {out_path}")

        if args.report:
            report = full_report(statement)
            report_path = os.path.join(args.output_dir, f"{stem}_report.json")
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            print(f"report -> {report_path}")

            # print summary to console
            print("\n── Analysis Summary ─────────────────────────────────────")
            bv = report["balance_verification"]
            print(f"  Balance verified : {'YES' if bv['verified'] else 'NO (diff: ' + str(bv['difference']) + ')'}")
            print(f"  Total income     : {report['income_summary']['total_income']}")
            print(f"  Avg daily balance: {report['average_daily_balance']}")
            print(f"  Anomalies found  : {len(report['anomalies'])}")
            print(f"  EMI candidates   : {len(report['emi_candidates'])}")
            print(f"  Transactions     : {report['total_transactions']}")
            print("─────────────────────────────────────────────────────────")


if __name__ == "__main__":
    main()
