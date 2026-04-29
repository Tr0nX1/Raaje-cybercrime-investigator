"""
SDR report analysis and validation utilities.
"""
import re
from typing import List, Dict, Any
from models.schema import SDRReport


def validate_sdr_report(report: SDRReport) -> Dict[str, Any]:
    """
    Comprehensive validation of extracted SDR report data.
    """
    issues = []
    score = 0
    max_score = 10

    # Phone number validation
    if report.phone_number:
        if re.match(r'^\+?\d{10,15}$', report.phone_number):
            score += 2
        else:
            issues.append("Invalid phone number format")
    else:
        issues.append("Missing phone number")

    # Email validation
    valid_emails = 0
    for email in report.email_addresses:
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            valid_emails += 1
        else:
            issues.append(f"Invalid email format: {email}")

    if valid_emails > 0:
        score += min(valid_emails, 2)  # Max 2 points for emails

    # UPI validation
    valid_upi = 0
    for upi in report.upi_vpa_accounts:
        if upi.upi_id and '@' in upi.upi_id:
            valid_upi += 1
        else:
            issues.append(f"Invalid UPI format: {upi.upi_id}")

    if valid_upi > 0:
        score += min(valid_upi, 2)  # Max 2 points for UPI

    # Personal details validation
    if report.personal_details.full_name and len(report.personal_details.full_name.strip()) > 2:
        score += 1

    # Security scores validation
    if report.security_scores.security_score is not None:
        if 0 <= report.security_scores.security_score <= 100:
            score += 1
        else:
            issues.append("Invalid security score range")

    if report.security_scores.cibil_score is not None:
        if 0 <= report.security_scores.cibil_score <= 900:
            score += 1
        else:
            issues.append("Invalid CIBIL score range")

    # Report type validation
    if report.report_type in ["khoj_osint", "scaninfoga"]:
        score += 1
    else:
        issues.append("Unknown or missing report type")

    return {
        "is_valid": len(issues) == 0,
        "quality_score": score / max_score,
        "issues": issues,
        "extraction_method": report.extraction_method,
        "report_type": report.report_type
    }


def analyze_sdr_patterns(report: SDRReport) -> Dict[str, Any]:
    """
    Analyze patterns and insights from SDR report data.
    """
    insights = {}

    # Phone number analysis
    if report.phone_number:
        insights["phone_region"] = _analyze_phone_region(report.phone_number)

    # Email domain analysis
    if report.email_addresses:
        insights["email_domains"] = _analyze_email_domains(report.email_addresses)

    # UPI provider analysis
    if report.upi_vpa_accounts:
        insights["upi_providers"] = _analyze_upi_providers(report.upi_vpa_accounts)

    # Security risk assessment
    if report.security_scores.security_score is not None:
        insights["security_risk"] = _assess_security_risk(report.security_scores.security_score)

    # Data completeness
    insights["data_completeness"] = _calculate_completeness(report)

    return insights


def _analyze_phone_region(phone: str) -> str:
    """Analyze phone number region based on prefix."""
    if phone.startswith("+91"):
        return "India"
    elif phone.startswith("91"):
        return "India (local format)"
    else:
        return "Unknown"


def _analyze_email_domains(emails: List[str]) -> Dict[str, int]:
    """Analyze email domains and their frequency."""
    domains = {}
    for email in emails:
        try:
            domain = email.split('@')[1].lower()
            domains[domain] = domains.get(domain, 0) + 1
        except:
            continue
    return domains


def _analyze_upi_providers(upi_accounts: List) -> Dict[str, int]:
    """Analyze UPI providers and their frequency."""
    providers = {}
    for account in upi_accounts:
        if account.app_bank:
            provider = account.app_bank.lower()
            providers[provider] = providers.get(provider, 0) + 1
    return providers


def _assess_security_risk(score: int) -> str:
    """Assess security risk based on score."""
    if score >= 80:
        return "Low Risk"
    elif score >= 60:
        return "Medium Risk"
    elif score >= 40:
        return "High Risk"
    else:
        return "Very High Risk"


def _calculate_completeness(report: SDRReport) -> float:
    """Calculate data completeness percentage."""
    fields = [
        report.phone_number,
        report.personal_details.full_name,
        bool(report.email_addresses),
        bool(report.upi_vpa_accounts),
        report.security_scores.security_score is not None,
        bool(report.aliases),
        bool(report.locations)
    ]

    filled_fields = sum(1 for field in fields if field)
    return filled_fields / len(fields)