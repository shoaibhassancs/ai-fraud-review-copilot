"""
Tool-call functions for AI Fraud-Review Copilot.

Two plain Python functions the agent calls to pull real context before
drafting a case note — lookup_customer_history and lookup_merchant_info.
Native function calling (no MCP server): same two tools, same data, same
end result, with no server/client wiring to build on top of Day 3's
already-full schedule.

Deterministic and boring on purpose — these simulate backend systems the
model queries, not model logic. CSVs are loaded once at module level since
the data never changes mid-run; no point re-reading from disk on every call.

Run directly for a quick manual check:
    python src/tools.py
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
CUSTOMERS_PATH = DATA_DIR / "customers.csv"
MERCHANTS_PATH = DATA_DIR / "merchants.csv"
TRANSACTIONS_PATH = DATA_DIR / "transactions.csv"

RECENT_TRANSACTIONS_LIMIT = 10


def _load_customers():
    customers = {}
    with open(CUSTOMERS_PATH, newline="") as f:
        for row in csv.DictReader(f):
            customers[row["id"]] = row
    return customers


def _load_merchants():
    merchants = {}
    with open(MERCHANTS_PATH, newline="") as f:
        for row in csv.DictReader(f):
            merchants[row["id"]] = row
    return merchants


def _load_transactions():
    with open(TRANSACTIONS_PATH, newline="") as f:
        return list(csv.DictReader(f))


# Loaded once at import time — 150 rows is nothing, but no reason to
# re-read from disk on every tool call the agent makes during a run.
_CUSTOMERS = _load_customers()
_MERCHANTS = _load_merchants()
_TRANSACTIONS = _load_transactions()


def lookup_customer_history(customer_id):
    """
    Return a customer's profile plus their most recent transactions, so the
    agent can judge whether the flagged transaction actually looks unusual
    for THIS customer, not just restate flagger output.

    Returns a dict on success, or {"error": "..."} if the id doesn't exist —
    never raises, so a missing id is something the agent can reason about
    as part of its normal flow rather than a crashed request.
    """
    customer = _CUSTOMERS.get(customer_id)
    if customer is None:
        return {"error": f"customer not found: {customer_id}"}

    past_transactions = [
        t for t in _TRANSACTIONS if t["customer_id"] == customer_id
    ]
    past_transactions.sort(key=lambda t: t["timestamp"], reverse=True)
    recent = past_transactions[:RECENT_TRANSACTIONS_LIMIT]

    return {
        "customer_id": customer_id,
        "name": customer["name"],
        "home_location": customer["home_location"],
        "typical_spend_min": float(customer["typical_spend_min"]),
        "typical_spend_max": float(customer["typical_spend_max"]),
        "account_age_days": int(customer["account_age_days"]),
        "recent_transactions": [
            {
                "id": t["id"],
                "merchant_id": t["merchant_id"],
                "amount": float(t["amount"]),
                "timestamp": t["timestamp"],
                "location": t["location"],
            }
            for t in recent
        ],
    }


def lookup_merchant_info(merchant_id):
    """
    Return a merchant's name, category, and risk tier.

    Returns a dict on success, or {"error": "..."} if the id doesn't exist.
    """
    merchant = _MERCHANTS.get(merchant_id)
    if merchant is None:
        return {"error": f"merchant not found: {merchant_id}"}

    return {
        "merchant_id": merchant_id,
        "name": merchant["name"],
        "category": merchant["category"],
        "risk_tier": merchant["risk_tier"],
    }


if __name__ == "__main__":
    import json

    print("lookup_customer_history('C001'):")
    print(json.dumps(lookup_customer_history("C001"), indent=2))

    print("\nlookup_customer_history('C999') [missing id]:")
    print(json.dumps(lookup_customer_history("C999"), indent=2))

    print("\nlookup_merchant_info('M001'):")
    print(json.dumps(lookup_merchant_info("M001"), indent=2))

    print("\nlookup_merchant_info('M999') [missing id]:")
    print(json.dumps(lookup_merchant_info("M999"), indent=2))