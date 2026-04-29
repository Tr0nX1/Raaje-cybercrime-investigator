#!/usr/bin/env python3
"""
Test script for SDR mapping system.
Tests both Khoj OSINT and Scaninfoga report processing.
"""
import os
import sys
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ensure console can handle UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass # Older python versions

from pipeline import process_single
from analyzer.sdr_analyzer import validate_sdr_report, analyze_sdr_patterns


def test_khoj_report():
    """Test Khoj OSINT report processing."""
    print("Testing Khoj OSINT Report...")

    pdf_path = "input/9560978030 - Khoj OSINT Report.pdf"
    if not os.path.exists(pdf_path):
        print(f"  ✗ Test file not found: {pdf_path}")
        return False

    try:
        report = process_single(pdf_path)

        # Basic validation
        assert report.report_type == "khoj_osint", f"Expected khoj_osint, got {report.report_type}"
        assert report.phone_number == "9560978030", f"Phone number mismatch: {report.phone_number}"
        assert report.operator_details.operator == "Airtel", f"Operator mismatch: {report.operator_details.operator}"
        assert len(report.aliases) > 0, "No aliases extracted"
        assert len(report.email_addresses) > 0, "No emails extracted"
        assert len(report.upi_vpa_accounts) > 0, "No UPI accounts extracted"

        # Validation check
        validation = validate_sdr_report(report)
        assert validation["is_valid"], f"Validation failed: {validation['issues']}"

        print("  ✓ Khoj OSINT report processed successfully")
        print(f"    - Phone: {report.phone_number}")
        print(f"    - Aliases: {len(report.aliases)}")
        print(f"    - Emails: {len(report.email_addresses)}")
        print(f"    - UPI Accounts: {len(report.upi_vpa_accounts)}")
        return True

    except Exception as e:
        print(f"  ✗ Khoj OSINT test failed: {e}")
        return False


def test_scaninfoga_report():
    """Test Scaninfoga report processing."""
    print("\nTesting Scaninfoga Report...")

    # Try the first available Scaninfoga report
    scaninfoga_files = [
        "input/ScaninfogaReport_7290900197_2026-04-22.pdf",
        "input/ScaninfogaReport_8383907548_2026-04-22.pdf",
        "input/ScaninfogaReport_8527567093_2026-04-22.pdf"
    ]

    test_file = None
    for file in scaninfoga_files:
        if os.path.exists(file):
            test_file = file
            break

    if not test_file:
        print("  ✗ No Scaninfoga test file found")
        return False

    try:
        report = process_single(test_file)

        # Basic validation
        assert report.report_type == "scaninfoga", f"Expected scaninfoga, got {report.report_type}"
        assert report.phone_number, f"No phone number extracted"
        assert report.personal_details.full_name, f"No name extracted"

        # Check for security scores
        has_security_data = (
            report.security_scores.security_score is not None or
            report.security_scores.cibil_score is not None or
            report.detection_summary.total_accounts is not None
        )
        assert has_security_data, "No security/detection data extracted"

        # Validation check
        validation = validate_sdr_report(report)
        print(f"    - Validation score: {validation['quality_score']:.2f}")

        print("  ✓ Scaninfoga report processed successfully")
        print(f"    - Phone: {report.phone_number}")
        print(f"    - Name: {report.personal_details.full_name}")
        print(f"    - Security Score: {report.security_scores.security_score}")
        print(f"    - Total Accounts: {report.detection_summary.total_accounts}")
        return True

    except Exception as e:
        print(f"  ✗ Scaninfoga test failed: {e}")
        return False


def test_batch_processing():
    """Test batch processing functionality."""
    print("\nTesting Batch Processing...")

    try:
        from pipeline import process_batch

        summary = process_batch("input/", "output/", max_workers=2)

        assert summary["processed"] > 0, "No files processed"
        assert summary["successful"] >= 0, "Invalid success count"

        print("  ✓ Batch processing completed")
        print(f"    - Processed: {summary['processed']}")
        print(f"    - Successful: {summary['successful']}")
        print(f"    - Failed: {summary['failed']}")

        return True

    except Exception as e:
        print(f"  ✗ Batch processing test failed: {e}")
        return False


def test_analysis():
    """Test analysis functionality."""
    print("\nTesting Analysis Functions...")

    try:
        # Create a mock report for testing
        from models.schema import SDRReport, UPIVPAAccount

        mock_report = SDRReport(
            phone_number="9560978030",
            email_addresses=["test@gmail.com", "test@yahoo.com"],
            upi_vpa_accounts=[
                UPIVPAAccount(upi_id="test@paytm", app_bank="Paytm"),
                UPIVPAAccount(upi_id="test@gpay", app_bank="Google Pay")
            ]
        )

        # Test validation
        validation = validate_sdr_report(mock_report)
        assert "quality_score" in validation, "Missing quality score"

        # Test analysis
        analysis = analyze_sdr_patterns(mock_report)
        assert "email_domains" in analysis, "Missing email domain analysis"
        assert "upi_providers" in analysis, "Missing UPI provider analysis"

        print("  ✓ Analysis functions working correctly")
        print(f"    - Quality Score: {validation['quality_score']:.2f}")
        print(f"    - Email Domains: {analysis['email_domains']}")
        print(f"    - UPI Providers: {analysis['upi_providers']}")

        return True

    except Exception as e:
        print(f"  ✗ Analysis test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("SDR Mapping System Tests")
    print("=" * 40)

    tests = [
        test_khoj_report,
        test_scaninfoga_report,
        test_batch_processing,
        test_analysis
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n{'='*40}")
    print(f"Test Results: {passed}/{total} passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())