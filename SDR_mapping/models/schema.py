from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class OperatorDetails(BaseModel):
    operator: Optional[str] = None
    circle: Optional[str] = None


class UPIVPAAccount(BaseModel):
    upi_id: Optional[str] = None
    app_bank: Optional[str] = None


class SocialMediaAccount(BaseModel):
    platform: Optional[str] = None
    identifier: Optional[str] = None
    compromised_data: Optional[List[str]] = []


class CompromisedService(BaseModel):
    service_name: Optional[str] = None
    compromised_data: Optional[List[str]] = []


class SecurityScores(BaseModel):
    security_score: Optional[int] = None
    cibil_score: Optional[int] = None


class DetectionSummary(BaseModel):
    total_accounts: Optional[int] = None
    upi_platforms: Optional[int] = None
    verified_checks: Optional[int] = None
    suspected_detections: Optional[int] = None


class TelecomInfo(BaseModel):
    number_active: Optional[bool] = None
    country: Optional[str] = None
    country_prefix: Optional[str] = None
    is_roaming: Optional[bool] = None
    subscriber_status: Optional[str] = None
    connection_type: Optional[str] = None


class PersonalDetails(BaseModel):
    full_name: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    age: Optional[int] = None
    father_or_husband: Optional[str] = None
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    alternate_number: Optional[str] = None
    pan_link_email: Optional[str] = None
    other_email: Optional[str] = None
    income: Optional[float] = None
    is_sole_proprietor: Optional[bool] = None
    is_director: Optional[bool] = None


class SDRReport(BaseModel):
    source_file: str = ""
    report_type: str = ""  # "khoj_osint" or "scaninfoga"
    extraction_method: str = ""  # "text" or "ocr"

    # Common fields
    phone_number: Optional[str] = None
    report_generated_by: Optional[str] = None
    report_generation_datetime: Optional[datetime] = None

    # Khoj OSINT specific fields
    operator_details: OperatorDetails = OperatorDetails()
    aliases: List[str] = []
    email_addresses: List[str] = []
    upi_vpa_accounts: List[UPIVPAAccount] = []
    locations: List[str] = []
    social_media_accounts: List[SocialMediaAccount] = []
    compromised_services: List[CompromisedService] = []

    # Scaninfoga specific fields
    personal_details: PersonalDetails = PersonalDetails()
    security_scores: SecurityScores = SecurityScores()
    detection_summary: DetectionSummary = DetectionSummary()
    telecom_info: TelecomInfo = TelecomInfo()

    # Metadata
    warnings: List[str] = []

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return self.model_dump()