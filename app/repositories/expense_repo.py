from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional
import calendar
from datetime import date
from app.models.expense import Expense, CategorizationStatus


class ExpenseRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def create_bulk(self, expenses_data: List[dict]) -> List[Expense]:
        expenses = [Expense(**d) for d in expenses_data]
        self.db.add_all(expenses)
        self.db.commit()
        for e in expenses:
            self.db.refresh(e)
        return expenses

    def update_category(
        self,
        expense_id: int,
        category: str,
        confidence: float,
        status: str = CategorizationStatus.CATEGORIZED,
    ) -> None:
        self.db.query(Expense).filter(Expense.id == expense_id).update(
            {
                "category": category,
                "category_confidence": confidence,
                "categorization_status": status,
            }
        )
        self.db.commit()

    def bulk_update_categories(self, updates: List[dict]) -> None:
        """updates: list of {id, category, confidence}"""
        for u in updates:
            self.db.query(Expense).filter(Expense.id == u["id"]).update(
                {
                    "category": u["category"],
                    "category_confidence": u["confidence"],
                    "categorization_status": CategorizationStatus.CATEGORIZED,
                }
            )
        self.db.commit()

    def update_expense(self, expense_id: int, updates: dict) -> Optional[Expense]:
        expense = self.get_by_id(expense_id)
        if expense:
            for k, v in updates.items():
                setattr(expense, k, v)
            self.db.commit()
            self.db.refresh(expense)
        return expense

    def delete_expense(self, expense_id: int) -> bool:
        expense = self.get_by_id(expense_id)
        if expense:
            self.db.delete(expense)
            self.db.commit()
            return True
        return False

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _month_bounds(month: str) -> tuple[date, date]:
        y, m = month.split("-")
        year, month_num = int(y), int(m)
        last_day = calendar.monthrange(year, month_num)[1]
        return date(year, month_num, 1), date(year, month_num, last_day)

    def get_by_id(self, expense_id: int) -> Optional[Expense]:
        return self.db.query(Expense).filter(Expense.id == expense_id).first()

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        category: Optional[str] = None,
        month: Optional[str] = None,  # YYYY-MM
        is_income: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Expense]:
        q = self.db.query(Expense)
        q = self._apply_filters(q, category, month, is_income, status, search)
        return q.order_by(Expense.date.desc()).offset(skip).limit(limit).all()

    def count(
        self,
        category: Optional[str] = None,
        month: Optional[str] = None,
        is_income: Optional[bool] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        q = self.db.query(func.count(Expense.id))
        q = self._apply_filters(q, category, month, is_income, status, search)
        return q.scalar() or 0

    def _apply_filters(self, q, category, month, is_income, status, search):
        """Shared filters for get_all and count (keeps the two in sync)."""
        if category:
            q = q.filter(Expense.category == category)
        if month:
            start, end = self._month_bounds(month)
            q = q.filter(Expense.date >= start)
            q = q.filter(Expense.date <= end)
        if is_income is not None:
            q = q.filter(Expense.is_income == is_income)
        if status:
            q = q.filter(Expense.categorization_status == status)
        if search:
            like = f"%{search.strip()}%"
            q = q.filter(or_(
                Expense.raw_text.ilike(like),
                Expense.notes.ilike(like),
                Expense.category.ilike(like),
                Expense.source.ilike(like),
            ))
        return q

    def get_pending_categorization(self, limit: int = 100) -> List[Expense]:
        return (
            self.db.query(Expense)
            .filter(Expense.categorization_status == CategorizationStatus.PENDING)
            .limit(limit)
            .all()
        )

    # ------------------------------------------------------------------ #
    # Aggregates (Python-side for SQLite/PostgreSQL portability)          #
    # ------------------------------------------------------------------ #

    def get_monthly_aggregates(self) -> List[dict]:
        """Returns per-month per-category totals for ML training."""
        rows = (
            self.db.query(Expense.date, Expense.category, Expense.amount)
            .filter(
                Expense.is_income == False,
                Expense.category.isnot(None),
                Expense.categorization_status.in_(
                    [CategorizationStatus.CATEGORIZED, CategorizationStatus.MANUAL]
                ),
            )
            .all()
        )

        agg: dict = {}
        for row in rows:
            month = row.date.strftime("%Y-%m")
            key = (month, row.category)
            if key not in agg:
                agg[key] = {"month": month, "category": row.category, "total": 0.0, "count": 0}
            agg[key]["total"] += row.amount
            agg[key]["count"] += 1

        return sorted(agg.values(), key=lambda x: (x["month"], x["category"]))

    def get_category_summary(self, month: Optional[str] = None) -> List[dict]:
        rows = (
            self.db.query(Expense.date, Expense.category, Expense.amount)
            .filter(
                Expense.is_income == False,
                Expense.category.isnot(None),
            )
            .all()
        )

        agg: dict = {}
        for row in rows:
            if month and row.date.strftime("%Y-%m") != month:
                continue
            cat = row.category
            if cat not in agg:
                agg[cat] = {"category": cat, "total": 0.0, "count": 0}
            agg[cat]["total"] += row.amount
            agg[cat]["count"] += 1

        return sorted(agg.values(), key=lambda x: -x["total"])

    def get_monthly_summary(self, month: str) -> dict:
        rows = self.db.query(Expense.date, Expense.category, Expense.amount, Expense.is_income).all()
        expenses, income = 0.0, 0.0
        cat_totals: dict = {}
        cat_counts: dict = {}

        for row in rows:
            if row.date.strftime("%Y-%m") != month:
                continue
            if row.is_income:
                income += row.amount
            else:
                expenses += row.amount
                cat = row.category or "Uncategorized"
                cat_totals[cat] = cat_totals.get(cat, 0.0) + row.amount
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

        total_expense = expenses
        categories = [
            {
                "category": c,
                "total": t,
                "count": cat_counts[c],
                "percentage": (t / total_expense * 100) if total_expense else 0,
            }
            for c, t in sorted(cat_totals.items(), key=lambda x: -x[1])
        ]
        return {
            "month": month,
            "total_expenses": round(expenses, 2),
            "total_income": round(income, 2),
            "net": round(income - expenses, 2),
            "categories": categories,
        }

    def dataset_signature(self) -> dict:
        """Cheap fingerprint of expense-table state for RAG index caching.

        Portable across SQLite/PostgreSQL (plain aggregates).
        """
        count = self.db.query(func.count(Expense.id)).scalar() or 0
        max_id = self.db.query(func.max(Expense.id)).scalar() or 0
        max_updated = self.db.query(func.max(Expense.updated_at)).scalar()
        max_created = self.db.query(func.max(Expense.created_at)).scalar()
        return {
            "count": int(count),
            "max_id": int(max_id),
            "max_updated": str(max_updated),
            "max_created": str(max_created),
        }

    def get_distinct_months(self) -> List[str]:
        rows = (
            self.db.query(Expense.date)
            .filter(Expense.is_income == False)
            .all()
        )
        months = sorted({r.date.strftime("%Y-%m") for r in rows})
        return months
