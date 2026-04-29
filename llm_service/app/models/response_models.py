from typing import Literal

from pydantic import BaseModel, Field


ConfidenceLevel = Literal["high", "medium", "low"]


class AuditResponse(BaseModel):
    source_account: str = Field(default="")
    source_utr: str = Field(default="")
    destination_account: str = Field(default="")
    destination_ifsc: str = Field(default="")
    bank: str = Field(default="")
    amount: str = Field(default="")
    confidence: ConfidenceLevel

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_account": "1234567890123456",
                "source_utr": "ABC123456789",
                "destination_account": "9988776655443322",
                "destination_ifsc": "SBIN0001234",
                "bank": "State Bank of India",
                "amount": "15000.00",
                "confidence": "high",
            }
        }
    }


class OllamaHealthStatus(BaseModel):
    connected: bool
    status: str


class AuditHealthResponse(BaseModel):
    service: str
    status: str
    default_model: str
    ollama: OllamaHealthStatus
    request_id: str = ""


class ModelsResponse(BaseModel):
    default_model: str
    configured_base_url: str
    installed_models: list[str]
    request_id: str = ""
