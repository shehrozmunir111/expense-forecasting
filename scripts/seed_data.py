#!/usr/bin/env python3
import argparse
import random
from datetime import date, timedelta

import httpx

TEMPLATES = {
    "Food & Dining":  [("ATB", 200, 700), ("Silpo", 300, 900), ("Novus", 150, 600), ("McDonald's", 80, 250), ("KFC", 100, 280), ("Cafe delivery", 150, 400)],
    "Transportation": [("WOG", 500, 1500), ("OKKO", 600, 1800), ("Shell", 400, 1200), ("Uber", 50, 200), ("Bolt taxi", 80, 250), ("Metro", 20, 60)],
    "Utilities":      [("Kyivenergo", 400, 700), ("Internet Lanet", 200, 300), ("Vodafone", 100, 200)],
    "Entertainment":  [("Steam", 200, 800), ("Cinema", 150, 400), ("Books", 100, 350)],
    "Healthcare":     [("Apteka", 100, 500), ("Clinic", 300, 1500)],
    "Subscriptions":  [("Netflix", 149, 149), ("Spotify", 99, 99), ("ChatGPT Plus", 800, 800)],
    "Shopping":       [("Rozetka", 300, 2000), ("H&M", 500, 2500), ("Prom.ua", 200, 1500)],
    "Housing":        [("Rent Payment", 8000, 15000)],
    "Travel":         [("Airbnb", 1500, 4000), ("WizzAir", 1200, 3000)],
    "Insurance":      [("TAS Insurance", 500, 1200)],
    "Education":      [("Udemy", 300, 800), ("Coursera", 1000, 2000)],
}


def generate_month(year: int, month: int):
    """Generate realistic transactions for one month."""
    transactions = []
    # Expenses
    for category, vendors in TEMPLATES.items():
        n_transactions = random.randint(1, 5)
        for _ in range(n_transactions):
            vendor, lo, hi = random.choice(vendors)
            amount = round(random.uniform(lo, hi), 2)
            day = random.randint(1, 28)
            transactions.append({
                "raw_text": f"{vendor} {int(amount)} USD",
                "amount": amount,
                "currency": "USD",
                "date": str(date(year, month, day)),
                "source": "PrivatBank",
                "is_income": False,
            })

    # One salary payment
    transactions.append({
        "raw_text": "Salary transfer",
        "amount": round(random.uniform(25000, 45000), 2),
        "currency": "USD",
        "date": str(date(year, month, 5)),
        "source": "PrivatBank",
        "is_income": True,
    })

    return transactions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=4, help="How many past months to seed")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--categorize", action="store_true", help="Trigger categorization after upload")
    args = parser.parse_args()

    today = date.today()
    client = httpx.Client(base_url=args.url, timeout=60)

    total_uploaded = 0
    for i in range(args.months, 0, -1):
        # Go back i months
        d = today.replace(day=1)
        for _ in range(i - 1):
            if d.month == 1:
                d = d.replace(year=d.year - 1, month=12)
            else:
                d = d.replace(month=d.month - 1)

        year, month = d.year, d.month
        transactions = generate_month(year, month)

        payload = {"expenses": transactions, "auto_categorize": False}
        resp = client.post("/expenses/upload", json=payload)
        resp.raise_for_status()
        stored = resp.json()["stored"]
        total_uploaded += stored
        print(f"  {year}-{month:02d}: uploaded {stored} transactions")

    print(f"\nTotal uploaded: {total_uploaded} transactions")

    if args.categorize:
        print("Running LLM categorization (this may take a moment)...")
        resp = client.post("/expenses/categorize/run")
        resp.raise_for_status()
        result = resp.json()
        print(f"Categorized: {result}")

        print("Training forecast model...")
        resp = client.post("/forecast/train")
        resp.raise_for_status()
        result = resp.json()
        print(f"Training result: {result}")

    print("\nDone. Visit http://localhost:8000/docs to explore the API.")


if __name__ == "__main__":
    main()
