"""
Synthetic data generator for AI Fraud-Review Copilot.

Generates three CSVs into data/:
  - customers.csv
  - merchants.csv
  - transactions.csv

Seeded for reproducibility — re-running this script always produces
the exact same rows, so eval labels stay tied to the same data forever.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from faker import Faker

# ---- Seeding: locks the output so every re-run is identical ----
random.seed(42)
np.random.seed(42)
Faker.seed(42)
fake = Faker()

# ---- Config ----
N_CUSTOMERS = 30
N_MERCHANTS = 20
N_TRANSACTIONS = 150
OUTPUT_DIR = Path(__file__).parent  # data/

MERCHANT_CATEGORIES = [
    "groceries", "electronics", "travel", "dining",
    "entertainment", "utilities", "clothing", "healthcare",
]
RISK_TIERS = ["low", "medium", "high"]
RISK_TIER_WEIGHTS = [0.6, 0.3, 0.1]  # most merchants are low risk


def generate_customers(n):
    customers = []
    preferred_categories = {}  # customer_id -> list of 1-2 categories they mostly shop in
    for i in range(1, n + 1):
        # Vary spend profiles so transaction amounts aren't one flat range —
        # some customers are naturally low spenders, some high.
        profile = random.choice(["low", "mid", "high"])
        if profile == "low":
            spend_min, spend_max = round(random.uniform(10, 40), 2), round(random.uniform(60, 120), 2)
        elif profile == "mid":
            spend_min, spend_max = round(random.uniform(40, 100), 2), round(random.uniform(150, 350), 2)
        else:
            spend_min, spend_max = round(random.uniform(100, 250), 2), round(random.uniform(400, 900), 2)

        cust_id = f"C{i:03d}"
        customers.append({
            "id": cust_id,
            "name": fake.name(),
            "home_location": fake.city(),
            "typical_spend_min": spend_min,
            "typical_spend_max": spend_max,
            # Skew toward older accounts but keep a handful very new —
            # those are the gray-area "new account, ordinary purchase" cases.
            "account_age_days": random.randint(1, 60) if random.random() < 0.15 else random.randint(61, 2500),
        })

        # Category affinity: each customer mostly shops in 1-2 categories.
        # Internal generation detail only — not written to customers.csv,
        # since it's not one of the spec's Data Design fields. flagger.py
        # derives "new merchant category" from actual transaction history,
        # not from this.
        k = random.choice([1, 2])
        preferred_categories[cust_id] = random.sample(MERCHANT_CATEGORIES, k=k)

    return customers, preferred_categories


def generate_merchants(n):
    merchants = []
    for i in range(1, n + 1):
        merchants.append({
            "id": f"M{i:03d}",
            "name": fake.company(),
            "category": random.choice(MERCHANT_CATEGORIES),
            "risk_tier": random.choices(RISK_TIERS, weights=RISK_TIER_WEIGHTS, k=1)[0],
        })
    return merchants


def generate_transactions(n, customers, merchants, preferred_categories):
    transactions = []
    now = datetime.now()

    merchants_by_category = {}
    for m in merchants:
        merchants_by_category.setdefault(m["category"], []).append(m)

    for i in range(1, n + 1):
        customer = random.choice(customers)

        # Merchant selection: ~85% within the customer's preferred
        # categories, ~15% any merchant — same mostly-normal/occasionally-not
        # shape used for amount and location, so "new merchant category"
        # means something real once flagger.py checks for it.
        cust_prefs = preferred_categories[customer["id"]]
        candidate_categories = [c for c in cust_prefs if c in merchants_by_category]
        if candidate_categories and random.random() < 0.85:
            chosen_category = random.choice(candidate_categories)
            merchant = random.choice(merchants_by_category[chosen_category])
        else:
            merchant = random.choice(merchants)

        spend_min = customer["typical_spend_min"]
        spend_max = customer["typical_spend_max"]

        # Amount: mostly within the customer's normal range (with jitter),
        # a slice of believable gray-area cases a bit above range,
        # and a small tail of clearly unusual amounts — a smooth spread,
        # not two obvious clusters.
        roll = random.random()
        if roll < 0.80:
            amount = np.random.uniform(spend_min, spend_max)
        elif roll < 0.93:
            # gray area: somewhat above normal, not extreme
            amount = np.random.uniform(spend_max * 1.1, spend_max * 2.0)
        else:
            # genuinely unusual
            amount = np.random.uniform(spend_max * 2.5, spend_max * 6.0)
        amount = round(float(amount), 2)

        # Location: usually home, sometimes elsewhere — geo-anomaly
        # detection logic belongs to flagger.py, not here.
        location = customer["home_location"] if random.random() < 0.8 else fake.city()

        timestamp = now - timedelta(
            days=random.randint(0, 90),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )

        transactions.append({
            "id": f"T{i:04d}",
            "customer_id": customer["id"],
            "merchant_id": merchant["id"],
            "amount": amount,
            "timestamp": timestamp.isoformat(timespec="seconds"),
            "location": location,
            "flag_reason": "",  # left blank — Action 6 (flagger.py) fills this in
        })
    return transactions


def write_csv(rows, filename, fieldnames):
    path = OUTPUT_DIR / filename
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {path}")


def main():
    customers, preferred_categories = generate_customers(N_CUSTOMERS)
    merchants = generate_merchants(N_MERCHANTS)
    transactions = generate_transactions(N_TRANSACTIONS, customers, merchants, preferred_categories)

    write_csv(customers, "customers.csv",
              ["id", "name", "home_location", "typical_spend_min", "typical_spend_max", "account_age_days"])
    write_csv(merchants, "merchants.csv",
              ["id", "name", "category", "risk_tier"])
    write_csv(transactions, "transactions.csv",
              ["id", "customer_id", "merchant_id", "amount", "timestamp", "location", "flag_reason"])


if __name__ == "__main__":
    main()