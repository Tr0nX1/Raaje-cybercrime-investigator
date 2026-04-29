"""
SDR Mapping - CLI entry point for OSINT report processing.

Usage examples:
    # single file -> JSON
    python main.py report.pdf

    # batch folder -> JSON files
    python main.py "input/" --batch

    # force OCR mode (even if text is selectable)
    python main.py report.pdf --force-ocr

    # custom output directory
    python main.py "input/" --batch --output-dir "results/"
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SDR OSINT Report PDF -> JSON extractor"
    )
    parser.add_argument("input", help="PDF file path or folder (with --batch)")
    parser.add_argument(
        "--batch", action="store_true",
        help="Process all PDFs in the input folder"
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Directory to save output files (default: output/)"
    )
    parser.add_argument(
        "--force-ocr", action="store_true",
        help="Force OCR extraction even for text-based PDFs"
    )
    parser.add_argument(
        "--ocr-dpi", type=int, default=200,
        help="DPI for OCR processing (default: 200)"
    )
    parser.add_argument(
        "--ocr-workers", type=int, default=4,
        help="Number of OCR worker threads (default: 4)"
    )
    parser.add_argument(
        "--max-workers", type=int, default=4,
        help="Maximum parallel processing workers (default: 4)"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)

    if args.batch:
        if not input_path.is_dir():
            print(f"Error: --batch requires a directory, got file: {input_path}")
            sys.exit(1)

        print(f"Processing batch from: {input_path}")
        summary = process_batch(
            str(input_path),
            output_dir=args.output_dir,
            ocr_dpi=args.ocr_dpi,
            ocr_workers=args.ocr_workers,
            max_workers=args.max_workers
        )

        # Print summary
        print(f"\n{'='*50}")
        print("BATCH PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Total files: {summary['processed']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success rate: {(summary['successful']/summary['processed']*100):.1f}%")

    else:
        if not input_path.is_file() or input_path.suffix.lower() != '.pdf':
            print(f"Error: Input must be a PDF file (or use --batch for directory)")
            sys.exit(1)

        print(f"Processing single file: {input_path}")
        report = process_single(
            str(input_path),
            ocr_dpi=args.ocr_dpi,
            ocr_workers=args.ocr_workers
        )

        # Generate output filename
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        base_name = input_path.stem
        output_file = output_dir / f"{base_name}.json"

        # Save to JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False, default=str)

        print(f"Output saved to: {output_file}")

        # Print basic info
        print(f"\nReport Summary:")
        print(f"  Type: {report.report_type}")
        print(f"  Phone: {report.phone_number or 'N/A'}")
        print(f"  Method: {report.extraction_method}")
        if report.warnings:
            print(f"  Warnings: {len(report.warnings)}")
            for warning in report.warnings[:3]:  # Show first 3 warnings
                print(f"    - {warning}")
            if len(report.warnings) > 3:
                print(f"    ... and {len(report.warnings) - 3} more")


if __name__ == "__main__":
    main()