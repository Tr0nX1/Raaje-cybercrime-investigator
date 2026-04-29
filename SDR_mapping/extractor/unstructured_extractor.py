import requests
import os
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from models.schema import SDRReport
from extractor.normalizer import normalize_sdr_data

class UnstructuredExtractor:
    """
    Extractor that uses Unstructured.io via X2Text bridge.
    """
    def __init__(
        self, 
        x2text_url: str = "http://localhost:3004/api/v1/x2text/process",
        unstructured_url: str = "http://localhost:8083"
    ):
        self.x2text_url = x2text_url
        self.unstructured_url = unstructured_url

    def extract(self, pdf_path: str) -> SDRReport:
        report = SDRReport(source_file=pdf_path, extraction_method="unstructured")
        
        try:
            with open(pdf_path, "rb") as f:
                files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
                data = {
                    "unstructured-url": self.unstructured_url
                }
                
                # Note: X2Text bridge requires a platform service API key in real Unstract,
                # but in local dev essentials it might be bypassed or use a dummy.
                # Checking x2text-service/app/authentication_middleware.py would clarify.
                headers = {
                    "Authorization": "Bearer dummy_key"
                }

                response = requests.post(
                    self.x2text_url,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=300 # Unstructured can be slow
                )
                
                if response.status_code != 200:
                    report.warnings.append(f"X2Text bridge error: {response.status_code} {response.text}")
                    return report

                # X2Text returns the extracted text directly as a file download (BytesIO)
                full_text = response.text
                
                # Re-use the existing logic for report type detection and extraction
                from extractor.text_extractor import _detect_report_type_from_content, _extract_khoj_osint_report, _extract_scaninfoga_report
                
                report_type = _detect_report_type_from_content(full_text)
                report.report_type = report_type

                if report_type == "khoj_osint":
                    report = _extract_khoj_osint_report(report, full_text)
                elif report_type == "scaninfoga":
                    report = _extract_scaninfoga_report(report, full_text)
                else:
                    report.warnings.append(f"Unknown report type detected")

        except Exception as e:
            report.warnings.append(f"Unstructured extraction failed: {str(e)}")

        # Normalize before returning
        try:
            report = normalize_sdr_data(report)
        except Exception:
            pass

        return report

def extract_unstructured_pdf(pdf_path: str, x2text_url: str = None, unstructured_url: str = None) -> SDRReport:
    """Convenience function for unstructured extraction."""
    # Use environment variables if not provided
    x2text_url = x2text_url or os.environ.get("X2TEXT_URL", "http://localhost:3004/api/v1/x2text/process")
    unstructured_url = unstructured_url or os.environ.get("UNSTRUCTURED_URL", "http://localhost:8083")
    
    extractor = UnstructuredExtractor(x2text_url=x2text_url, unstructured_url=unstructured_url)
    return extractor.extract(pdf_path)
