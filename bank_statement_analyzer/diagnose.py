"""
Diagnostic tool -- dumps raw pdfplumber table / text output for a PDF.

Usage:
    python diagnose.py "input files/Statement 2011-1103.pdf"
    python diagnose.py "input files/110216608184.pdf" --pages 1,2
    python diagnose.py "input files/BOM_Statement..." --text-only
"""
import sys
import argparse
import pdfplumber

from extractor.text_extractor import (
    _detect_col_map,
    _find_header_row,
    _is_pipe_format,
    _DATE_CELL_RE,
    _DATE_ROW_RE,
    _AMOUNT_LINE_RE,
)


def diagnose(pdf_path: str, page_nums: list | None = None, text_only: bool = False):
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        pages = page_nums if page_nums else list(range(min(3, total)))
        print()
        print("=" * 70)
        print(f"FILE : {pdf_path}")
        print(f"PAGES: {total} total, showing pages {[p + 1 for p in pages]}")
        print("=" * 70)

        for pg_idx in pages:
            if pg_idx >= total:
                print(f"\n[page {pg_idx + 1} -- out of range]")
                continue

            page = pdf.pages[pg_idx]
            page_text = page.extract_text() or ""
            print()
            print("-" * 60)
            print(f"PAGE {pg_idx + 1}")
            print("-" * 60)

            if not text_only:
                tables = page.extract_tables()
                print(f"\n[Tables found: {len(tables)}]")
                for t_idx, table in enumerate(tables):
                    print(f"\n  Table {t_idx + 1} ({len(table)} rows):")
                    hdr_idx = _find_header_row(table)
                    print(f"  _find_header_row -> row {hdr_idx}")
                    if hdr_idx is not None:
                        header = [str(c).lower().strip() if c else "" for c in table[hdr_idx]]
                        col = _detect_col_map(header)
                        print(f"  _detect_col_map  -> {col}")
                        print(f"  header cells     : {table[hdr_idx]}")
                    else:
                        print("  (no header row detected)")
                    print(f"  First 6 rows:")
                    for r in table[:6]:
                        print(f"    {r}")
                    if len(table) > 6:
                        print(f"    ... ({len(table) - 6} more rows)")

            print(f"\n[Raw text ({len(page_text)} chars)]")
            if _is_pipe_format(page_text):
                print("  Format: PIPE-DELIMITED detected")
            lines = page_text.splitlines()
            date_lines = 0
            for i, ln in enumerate(lines[:60]):
                date_match = bool(_DATE_ROW_RE.match(ln.strip()))
                amt_match  = bool(_AMOUNT_LINE_RE.search(ln))
                cell_match = bool(_DATE_CELL_RE.match(ln.strip()))
                flags = []
                if date_match: flags.append("DATE_ROW")
                if amt_match:  flags.append("HAS_AMT")
                if cell_match: flags.append("DATE_CELL")
                marker = f"[{','.join(flags)}]" if flags else ""
                try:
                    print(f"  {i + 1:3d}: {marker:30s} {ln}")
                except UnicodeEncodeError:
                    safe = ln.encode("ascii", "replace").decode("ascii")
                    print(f"  {i + 1:3d}: {marker:30s} {safe}")
                if date_match:
                    date_lines += 1
            print(f"\n  Date-row matches in first 60 lines: {date_lines}")
            if len(lines) > 60:
                print(f"  (... {len(lines) - 60} more lines)")


def main():
    ap = argparse.ArgumentParser(description="Diagnostic tool for bank statement PDFs")
    ap.add_argument("pdf", help="Path to PDF file")
    ap.add_argument(
        "--pages", default=None,
        help="Comma-separated 1-based page numbers (default: first 3)",
    )
    ap.add_argument("--text-only", action="store_true", help="Skip table extraction")
    args = ap.parse_args()

    page_nums = None
    if args.pages:
        page_nums = [int(p) - 1 for p in args.pages.split(",")]

    diagnose(args.pdf, page_nums, args.text_only)


if __name__ == "__main__":
    main()
