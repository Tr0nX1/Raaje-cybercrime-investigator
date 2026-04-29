from pydantic import BaseModel, Field, field_validator


class TransactionInput(BaseModel):
    source_account: str = Field(..., min_length=1)
    destination_account: str = Field(..., min_length=1)
    bank: str = Field(..., min_length=1)
    amount: str = Field(..., min_length=1)
    raw_text: str | None = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "source_account": "1234567890123456",
                "destination_account": "9988776655443322",
                "bank": "State Bank of India",
                "amount": "15000.00",
                "raw_text": "IMPS from 1234567890123456 to 9988776655443322 SBI amount 15000 ref ABC123456789",
            }
        }
    }

    @field_validator("source_account", "destination_account", "bank", "amount", mode="before")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("Field must be a string")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("raw_text", mode="before")
    @classmethod
    def strip_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("raw_text must be a string")
        cleaned = value.strip()
        return cleaned or None


class AuditTransactionRequest(BaseModel):
    transaction: TransactionInput

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction": {
                    "source_account": "1234567890123456",
                    "destination_account": "9988776655443322",
                    "bank": "State Bank of India",
                    "amount": "15000.00",
                    "raw_text": "IMPS from 1234567890123456 to 9988776655443322 SBI amount 15000 ref ABC123456789",
                }
            }
        }
    }
