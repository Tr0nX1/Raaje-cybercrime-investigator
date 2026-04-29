from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date as DateType


class StatementPeriod(BaseModel):
    from_date: Optional[DateType] = None
    to_date: Optional[DateType] = None


class AccountInfo(BaseModel):
    holder_name: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    statement_period: StatementPeriod = StatementPeriod()


class Summary(BaseModel):
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    total_credits: float = 0.0
    total_debits: float = 0.0


class Transaction(BaseModel):
    date: Optional[DateType] = None
    description: str = ""
    type: str = "unknown"           # "credit" | "debit" | "unknown"
    amount: Optional[float] = None  # None = not yet resolved; filled by balance recovery
    balance: Optional[float] = None
    category: Optional[str] = None
    
    # Forensic Identification - New fields requested
    holder_name: Optional[str] = None
    account_number: Optional[str] = None

    # Validation context — set during extraction to enable enhanced balance validation
    has_debit_col: Optional[bool] = None  # whether debit column was present in source
    has_credit_col: Optional[bool] = None # whether credit column was present in source
    validation_warning: Optional[str] = None  # set if balance validation catches an inconsistency
    
    # Audit and Auto-Healing Metadata
    raw_text: Optional[str] = None
    audit: Optional[dict] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("credit", "debit", "unknown"):
            return "unknown"
        return v


class BankStatement(BaseModel):
    source_file: str = ""
    extraction_method: str = ""     # "text" | "ocr"
    account: AccountInfo = AccountInfo()
    summary: Summary = Summary()
    transactions: list[Transaction] = []
    warnings: list[str] = []        # Rule 9 — page completeness flags

    def to_toon(self) -> str:
        """
        TOON = Tab-Oriented Output Notation — simple TSV-like flat format.
        Header lines start with #, data rows are tab-separated.
        """
        lines = [
            "# BANK STATEMENT",
            f"# source: {self.source_file}",
            f"# method: {self.extraction_method}",
            f"# holder: {self.account.holder_name}",
            f"# account: {self.account.account_number}",
            f"# bank: {self.account.bank_name}",
            f"# period: {self.account.statement_period.from_date} to {self.account.statement_period.to_date}",
            f"# opening_balance: {self.summary.opening_balance}",
            f"# closing_balance: {self.summary.closing_balance}",
            f"# total_credits: {self.summary.total_credits}",
            f"# total_debits: {self.summary.total_debits}",
        ]
        for w in self.warnings:
            lines.append(f"# WARNING: {w}")
        lines += [
            "",
            "DATE\tHOLDER\tACCOUNT\tDESCRIPTION\tTYPE\tAMOUNT\tBALANCE\tCATEGORY",
        ]
        for tx in self.transactions:
            lines.append(
                f"{tx.date}\t{tx.holder_name}\t{tx.account_number}\t{tx.description}\t{tx.type}"
                f"\t{tx.amount}\t{tx.balance}\t{tx.category}"
            )
        return "\n".join(lines)
