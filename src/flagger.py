"""
Rule-based fraud flagger for AI Fraud-Review Copilot.

Reads data/transactions.csv, data/customers.csv and data/merchants.csv,
walks each customer's transactions in chronological order, and fills in
the flag_reason column using four simple rules. A transaction is only
ever checked against that customer's PAST transactions — never later
ones — matching how a real flagging system would see the data live.

Run from the project root:
    python src/flagger.py
"""

import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
TRANSACTIONS_PATH = DATA_DIR / "transactions.csv"
CUSTOMERS_PATH = DATA_DIR / "customers.csv"
MERCHANTS_PATH = DATA_DIR / "merchants.csv"

VELOCITY_WINDOW = timedelta(hours=24)
VELOCITY_MIN_COUNT = 2
MIN_HISTORY_FOR_NEW_CATEGORY = 2

# Priority when more than one rule matches on the same transaction —
# strongest/rarest signal wins, noisiest (category) breaks last.
PRIORITY = ["velocity_spike", "geo_anomaly", "amount_spike", "new_merchant_category"]

FIELDNAMES = ["id", "customer_id", "merchant_id", "amount", "timestamp", "location", "flag_reason"]


def load_customers():
    customers = {}
    with open(CUSTOMERS_PATH, newline="") as f:
        for row in csv.DictReader(f):
            customers[row["id"]] = {
                "home_location": row["home_location"],
                "typical_spend_max": float(row["typical_spend_max"]),
            }
    return customers


def load_merchants():
    merchants = {}
    with open(MERCHANTS_PATH, newline="") as f:
        for row in csv.DictReader(f):
            merchants[row["id"]] = {"category": row["category"]}
    return merchants


def load_transactions():
    with open(TRANSACTIONS_PATH, newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["amount"] = float(row["amount"])
        row["_timestamp"] = datetime.fromisoformat(row["timestamp"])
    return rows


def flag_transactions(transactions, customers, merchants):
    # Process chronologically per customer so "new category" and
    # "velocity" only ever look backward.
    transactions.sort(key=lambda t: (t["customer_id"], t["_timestamp"]))

    history = defaultdict(list)  # customer_id -> past transactions seen so far
    final_counts = defaultdict(int)  # flag_reason actually assigned (post-priority)

    for txn in transactions:
        cust_id = txn["customer_id"]
        customer = customers.get(cust_id)
        past = history[cust_id]

        matched = []

        # Rule 1: velocity — this transaction plus a prior one within 24h.
        recent = [p for p in past if txn["_timestamp"] - p["_timestamp"] <= VELOCITY_WINDOW]
        if len(recent) + 1 >= VELOCITY_MIN_COUNT:
            matched.append("velocity_spike")

        # Rule 2: geo anomaly
        if customer and txn["location"] != customer["home_location"]:
            matched.append("geo_anomaly")

        # Rule 3: amount spike
        if customer and txn["amount"] > customer["typical_spend_max"]:
            matched.append("amount_spike")

        # Rule 4: new merchant category — only once there's enough history to judge
        if len(past) >= MIN_HISTORY_FOR_NEW_CATEGORY:
            past_categories = {
                merchants[p["merchant_id"]]["category"]
                for p in past if p["merchant_id"] in merchants
            }
            this_category = merchants.get(txn["merchant_id"], {}).get("category")
            if this_category and this_category not in past_categories:
                matched.append("new_merchant_category")

        # Pick one reason by priority; unflagged if nothing matched.
        chosen = next((r for r in PRIORITY if r in matched), "")
        txn["flag_reason"] = chosen
        final_counts[chosen] += 1

        history[cust_id].append(txn)

    return transactions, final_counts


def write_transactions(transactions):
    # Restore original T0001, T0002... order for the output file.
    transactions.sort(key=lambda t: t["id"])
    with open(TRANSACTIONS_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for t in transactions:
            writer.writerow({k: t[k] for k in FIELDNAMES})


def main():
    customers = load_customers()
    merchants = load_merchants()
    transactions = load_transactions()

    transactions, final_counts = flag_transactions(transactions, customers, merchants)
    write_transactions(transactions)

    total = len(transactions)
    unflagged = final_counts.get("", 0)
    flagged = total - unflagged

    print(f"Flagged {flagged} of {total} transactions.")
    for reason in PRIORITY:
        print(f"  {reason}: {final_counts.get(reason, 0)}")
    print(f"  unflagged: {unflagged}")


if __name__ == "__main__":
    main()