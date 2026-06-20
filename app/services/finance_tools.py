from typing import List, Optional

from app.repositories.expense_repo import ExpenseRepository
from app.services.forecasting import forecasting_service


class FinanceTools:
    def __init__(self, repo: ExpenseRepository):
        self.repo = repo

    # -- month helpers --------------------------------------------------- #

    def distinct_months(self) -> List[str]:
        return self.repo.get_distinct_months()

    def latest_month(self) -> Optional[str]:
        months = self.repo.get_distinct_months()
        return months[-1] if months else None

    # -- summaries (mirror /expenses/summary/* exactly) ------------------ #

    def category_summary(self, month: Optional[str] = None) -> List[dict]:
        """Per-category totals, optionally scoped to a YYYY-MM month."""
        rows = self.repo.get_category_summary(month=month)
        total = sum(r["total"] for r in rows)
        return [
            {
                "category": r["category"],
                "total": round(r["total"], 2),
                "count": r["count"],
                "percentage": round((r["total"] / total * 100) if total else 0.0, 1),
            }
            for r in rows
        ]

    def monthly_summary(self, month: str) -> dict:
        """Income/expense/net plus per-category breakdown for one month."""
        return self.repo.get_monthly_summary(month)

    def category_total(self, category: str, month: Optional[str] = None) -> Optional[dict]:
        """Single-category lookup, e.g. 'groceries this month'."""
        for r in self.category_summary(month=month):
            if r["category"].lower() == category.lower():
                return {**r, "month": month}
        return None

    # -- forecast (mirrors /forecast/) ----------------------------------- #

    def forecast(self) -> Optional[dict]:
        """Next-month per-category forecast, or None if not enough history."""
        return forecasting_service.predict(self.repo)

    # -- raw rows -------------------------------------------------------- #

    def recent_transactions(
        self,
        limit: int = 8,
        category: Optional[str] = None,
        month: Optional[str] = None,
    ) -> List[dict]:
        items = self.repo.get_all(
            limit=limit, category=category, month=month, is_income=False
        )
        return [
            {
                "date": str(e.date),
                "raw_text": e.raw_text,
                "amount": round(float(e.amount), 2),
                "category": e.category,
                "currency": e.currency,
            }
            for e in items
        ]
