#!/usr/bin/env python3
"""Create the demo user and give it ALL existing (unowned) expenses.

Run this once after adding auth so the seeded demo data has an owner who can
log in and see it:

    python -m scripts.seed_user

Newly registered accounts start empty; only this demo user owns the seed data.
"""
import sys
from pathlib import Path

# allow running as a plain script (python scripts/seed_user.py)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import update

from app.database import Base, SessionLocal, engine
from app.db_migrate import ensure_user_id_column
from app.models.expense import Expense
from app.models.user import User

DEMO_EMAIL = "demo@financeflow.local"
DEMO_PASSWORD = "demo12345"
DEMO_NAME = "Demo User"


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_user_id_column()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == DEMO_EMAIL).first()
        if user is None:
            user = User(email=DEMO_EMAIL, full_name=DEMO_NAME)
            user.set_password(DEMO_PASSWORD)
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"Created demo user: {DEMO_EMAIL} (id={user.id})")
        else:
            print(f"Demo user already exists: {DEMO_EMAIL} (id={user.id})")

        # Hand every unowned expense to the demo user.
        result = db.execute(
            update(Expense).where(Expense.user_id.is_(None)).values(user_id=user.id)
        )
        db.commit()
        print(f"Assigned {result.rowcount} existing expense(s) to {DEMO_EMAIL}")
        print(f"\nLogin with:  {DEMO_EMAIL}  /  {DEMO_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
