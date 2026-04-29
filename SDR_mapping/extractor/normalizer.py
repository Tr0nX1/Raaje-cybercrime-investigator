from models.schema import SDRReport

def normalize_sdr_data(report: SDRReport) -> SDRReport:
    """Basic normalization and cleanup for SDRReport fields.

    - strip strings
    - deduplicate lists
    - ensure consistent phone formatting
    """
    try:
        # PersonalDetails fields
        if getattr(report, 'personal_details', None):
            for k, v in report.personal_details.model_dump().items():
                if isinstance(v, str) and v:
                    setattr(report.personal_details, k, v.strip())

        # Email addresses
        if getattr(report, 'email_addresses', None):
            cleaned = []
            seen = set()
            for e in report.email_addresses:
                if not e:
                    continue
                e2 = e.strip()
                key = e2.lower()
                if key not in seen:
                    seen.add(key)
                    cleaned.append(e2)
            report.email_addresses = cleaned

        # Aliases
        if getattr(report, 'aliases', None):
            report.aliases = list(dict.fromkeys([a.strip() for a in report.aliases if a and a.strip()]))

        # Locations
        if getattr(report, 'locations', None):
            report.locations = [l.strip() for l in report.locations if l and l.strip()]

        # Phone number: keep last 10 digits
        pn = getattr(report, 'phone_number', None)
        if pn:
            import re as _re
            digits = _re.sub(r'\D', '', str(pn))
            if len(digits) >= 10:
                report.phone_number = digits[-10:]
            else:
                report.phone_number = digits
    except Exception:
        pass

    return report