"""
Financial calculation functions — operate on a BankStatement object.
All functions return plain Python dicts or primitives for easy JSON serialization.
"""
from collections import defaultdict
from datetime import date
from models.schema import BankStatement, Transaction


def monthly_cashflow(statement: BankStatement) -> dict:
    """Credits vs debits grouped by YYYY-MM."""
    flow: dict[str, dict] = defaultdict(lambda: {"credits": 0.0, "debits": 0.0, "net": 0.0})

    for tx in statement.transactions:
        if not tx.date:
            continue
        key = tx.date.strftime("%Y-%m")
        if tx.type == "credit":
            flow[key]["credits"] += tx.amount
        elif tx.type == "debit":
            flow[key]["debits"] += tx.amount

    for key in flow:
        flow[key]["net"] = flow[key]["credits"] - flow[key]["debits"]

    return dict(sorted(flow.items()))


def average_daily_balance(statement: BankStatement) -> float:
    """
    Weighted average daily balance.
    Uses the statement period end date as the upper bound for the last transaction.
    Falls back to last transaction date + 1 day if period end is unavailable.
    """
    txns = [t for t in statement.transactions if t.date and t.balance is not None]
    if not txns:
        return statement.summary.opening_balance or 0.0

    txns = sorted(txns, key=lambda t: t.date)
    period_end = statement.account.statement_period.to_date or (
        txns[-1].date.__class__(
            txns[-1].date.year, txns[-1].date.month, txns[-1].date.day
        )
    )

    total_weighted = 0.0
    total_days = 0

    for i, tx in enumerate(txns):
        if i + 1 < len(txns):
            next_date = txns[i + 1].date
        else:
            next_date = period_end  # use statement end date, not tx.date
        days = max((next_date - tx.date).days, 1)
        total_weighted += tx.balance * days
        total_days += days

    return round(total_weighted / total_days, 2) if total_days else 0.0


def spending_by_category(statement: BankStatement) -> dict[str, float]:
    """Total debit amount grouped by category."""
    totals: dict[str, float] = defaultdict(float)
    for tx in statement.transactions:
        if tx.type == "debit" and tx.category:
            totals[tx.category] += tx.amount
    return dict(sorted(totals.items(), key=lambda x: x[1], reverse=True))


def income_summary(statement: BankStatement) -> dict:
    """Detect and summarize recurring income (salary, large credits)."""
    credits = [t for t in statement.transactions if t.type == "credit"]
    salary_txns = [t for t in credits if t.category == "salary"]
    other_credits = [t for t in credits if t.category != "salary"]

    return {
        "total_income": round(sum(t.amount for t in credits), 2),
        "salary_total": round(sum(t.amount for t in salary_txns), 2),
        "salary_count": len(salary_txns),
        "other_credits_total": round(sum(t.amount for t in other_credits), 2),
        "other_credits_count": len(other_credits),
    }


def balance_verification(statement: BankStatement) -> dict:
    """
    Re-compute closing balance from opening + credits - debits.
    Flags mismatch which may indicate extraction errors.
    """
    opening = statement.summary.opening_balance or 0.0
    expected_closing = opening + statement.summary.total_credits - statement.summary.total_debits
    reported_closing = statement.summary.closing_balance or 0.0
    diff = round(reported_closing - expected_closing, 2)

    return {
        "opening_balance": opening,
        "total_credits": round(statement.summary.total_credits, 2),
        "total_debits": round(statement.summary.total_debits, 2),
        "expected_closing": round(expected_closing, 2),
        "reported_closing": reported_closing,
        "difference": diff,
        "verified": abs(diff) < 1.0,  # within ₹1 tolerance
    }


def anomaly_detection(statement: BankStatement, z_threshold: float = 2.5) -> list[dict]:
    """
    Flag transactions whose amount is more than z_threshold standard deviations
    above the mean for their type. Returns list of flagged transactions.
    """
    import math

    def stats(amounts: list[float]) -> tuple[float, float]:
        if not amounts:
            return 0.0, 0.0
        mean = sum(amounts) / len(amounts)
        variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
        return mean, math.sqrt(variance)

    debit_amounts = [t.amount for t in statement.transactions if t.type == "debit"]
    credit_amounts = [t.amount for t in statement.transactions if t.type == "credit"]

    d_mean, d_std = stats(debit_amounts)
    c_mean, c_std = stats(credit_amounts)

    flagged = []
    for tx in statement.transactions:
        if tx.type == "debit" and d_std > 0:
            z = (tx.amount - d_mean) / d_std
            if z > z_threshold:
                flagged.append({**tx.model_dump(mode="json"), "z_score": round(z, 2), "flag": "high_debit"})
        elif tx.type == "credit" and c_std > 0:
            z = (tx.amount - c_mean) / c_std
            if z > z_threshold:
                flagged.append({**tx.model_dump(mode="json"), "z_score": round(z, 2), "flag": "high_credit"})

    return sorted(flagged, key=lambda x: x["z_score"], reverse=True)


def emi_detection(statement: BankStatement, tolerance: float = 0.05) -> list[dict]:
    """
    Detect recurring fixed debits (likely EMIs) — same amount ±tolerance% repeated monthly.
    """
    from itertools import groupby

    debit_txns = [t for t in statement.transactions if t.type == "debit" and t.date]

    # group by amount bucket — round to nearest (tolerance * amount) to absorb small fee variations
    amount_groups: dict[int, list[Transaction]] = defaultdict(list)
    for tx in debit_txns:
        if tx.amount <= 0:
            continue
        bucket = round(tx.amount / (tx.amount * tolerance + 1))
        amount_groups[bucket].append(tx)

    emis = []
    for _bucket, txns in amount_groups.items():
        if len(txns) >= 2:
            months = {t.date.strftime("%Y-%m") for t in txns if t.date}
            if len(months) >= 2:
                avg_amount = round(sum(t.amount for t in txns) / len(txns), 2)
                emis.append({
                    "amount": avg_amount,
                    "occurrences": len(txns),
                    "months": sorted(months),
                    "likely_emi": True,
                    "sample_description": txns[0].description,
                })

    return sorted(emis, key=lambda x: x["occurrences"], reverse=True)


def full_report(statement: BankStatement) -> dict:
    """Generate a complete analysis report from a BankStatement."""
    return {
        "account": statement.account.model_dump(mode="json"),
        "balance_verification": balance_verification(statement),
        "income_summary": income_summary(statement),
        "monthly_cashflow": monthly_cashflow(statement),
        "spending_by_category": spending_by_category(statement),
        "average_daily_balance": average_daily_balance(statement),
        "anomalies": anomaly_detection(statement),
        "emi_candidates": emi_detection(statement),
        "total_transactions": len(statement.transactions),
    }
