import json

from app.models.request_models import TransactionInput


def build_transaction_audit_prompt(transaction: TransactionInput) -> str:
    input_payload = {
        "source_account": transaction.source_account,
        "destination_account": transaction.destination_account,
        "bank": transaction.bank,
        "amount": transaction.amount,
        "raw_text": transaction.raw_text or "",
    }
    schema = {
        "source_account": "string",
        "source_utr": "string",
        "destination_account": "string",
        "destination_ifsc": "string",
        "bank": "string",
        "amount": "string",
        "confidence": "high | medium | low",
    }
    return (
        "You are a transaction audit assistant.\n"
        "Your job is to clean and correct transaction data using only the given input.\n"
        "Rules:\n"
        "1. Return exactly one JSON object and no other text.\n"
        "2. Do not hallucinate, infer unsupported facts, or invent missing values.\n"
        "3. Only preserve, rearrange, or correct values that are clearly supported by the input.\n"
        "4. If a value is unavailable, use an empty string.\n"
        "5. Keep amount as a string. Do not change numeric formatting unless the input clearly supports it.\n"
        "6. confidence must be one of: high, medium, low.\n"
        "7. If the source data is weak or ambiguous, lower the confidence instead of guessing.\n\n"
        f"Input transaction:\n{json.dumps(input_payload, ensure_ascii=True, indent=2)}\n\n"
        f"Output schema:\n{json.dumps(schema, ensure_ascii=True, indent=2)}"
    )
