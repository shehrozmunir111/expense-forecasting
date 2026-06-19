import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.expense import CategorizationStatus
from app.repositories.expense_repo import ExpenseRepository
from app.services.categorization import CategorizationService
from app.schemas.expense import (
    ExpenseBulkUpload,
    BulkUploadResponse,
    ExpenseOut,
    ExpenseUpdate,
    CategorySummary,
    MonthlySummary,
    PaginatedExpenses,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/expenses", tags=["Expenses"])
MonthQuery = Annotated[Optional[str], Query(pattern=r"^\d{4}-\d{2}$", description="YYYY-MM")]
StatusQuery = Annotated[
    Optional[str],
    Query(
        pattern=f"^({CategorizationStatus.PENDING}|{CategorizationStatus.CATEGORIZED}|"
        f"{CategorizationStatus.FAILED}|{CategorizationStatus.MANUAL})$",
        description="pending|categorized|failed|manual",
    ),
]

# One categorization service instance (lazy LLM client init)
_categorization_service = CategorizationService()


# ------------------------------------------------------------------ #
# Background task helper                                               #
# ------------------------------------------------------------------ #

def _bg_categorize():
    """Run categorization in a background task with its own DB session."""
    db = SessionLocal()
    try:
        repo = ExpenseRepository(db)
        result = _categorization_service.categorize_all_pending(repo)
        logger.info("Background categorization finished: %s", result)
    except Exception as exc:
        logger.error("Background categorization error: %s", exc)
    finally:
        db.close()


# ------------------------------------------------------------------ #
# Routes                                                               #
# ------------------------------------------------------------------ #

@router.post("/upload", response_model=BulkUploadResponse, status_code=201)
def upload_expenses(
    payload: ExpenseBulkUpload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Upload one or many expense/income records.
    Set `auto_categorize=true` to queue LLM categorization immediately.
    """
    repo = ExpenseRepository(db)

    expenses_data = [
        {
            "raw_text": e.raw_text,
            "amount": e.amount,
            "currency": e.currency,
            "date": e.date,
            "source": e.source,
            "notes": e.notes,
            "is_income": e.is_income,
        }
        for e in payload.expenses
    ]

    stored = repo.create_bulk(expenses_data)
    expense_ids = [e.id for e in stored]

    cat_status = "skipped"
    if payload.auto_categorize:
        background_tasks.add_task(_bg_categorize)
        cat_status = "queued"

    return BulkUploadResponse(
        total_received=len(payload.expenses),
        stored=len(stored),
        categorization_status=cat_status,
        expense_ids=expense_ids,
        message=(
            f"Stored {len(stored)} records. "
            f"Categorization: {cat_status}."
        ),
    )


@router.get("/", response_model=PaginatedExpenses)
def list_expenses(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=500),
    category: Optional[str] = None,
    month: MonthQuery = None,
    is_income: Optional[bool] = None,
    status: StatusQuery = None,
    db: Session = Depends(get_db),
):
    repo = ExpenseRepository(db)
    items = repo.get_all(skip=skip, limit=limit, category=category, month=month, is_income=is_income, status=status)
    total = repo.count(category=category, month=month, is_income=is_income, status=status)
    return PaginatedExpenses(items=items, total=total, skip=skip, limit=limit)


@router.get("/summary/by-category", response_model=List[CategorySummary])
def category_summary(
    month: MonthQuery = None,
    db: Session = Depends(get_db),
):
    """Totals per category, sorted by amount descending."""
    repo = ExpenseRepository(db)
    raw = repo.get_category_summary(month=month)
    total = sum(r["total"] for r in raw)

    return [
        CategorySummary(
            category=r["category"],
            total_amount=round(r["total"], 2),
            transaction_count=r["count"],
            currency="USD",
            percentage=round((r["total"] / total * 100) if total else 0, 2),
        )
        for r in raw
    ]


@router.get("/summary/monthly", response_model=MonthlySummary)
def monthly_summary(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$", description="YYYY-MM"),
    db: Session = Depends(get_db),
):
    repo = ExpenseRepository(db)
    data = repo.get_monthly_summary(month)

    categories = [
        CategorySummary(
            category=c["category"],
            total_amount=round(c["total"], 2),
            transaction_count=c["count"],
            currency="USD",
            percentage=round(c["percentage"], 2),
        )
        for c in data["categories"]
    ]

    tx_count = sum(c.transaction_count for c in categories)

    return MonthlySummary(
        month=month,
        total_expenses=data["total_expenses"],
        total_income=data["total_income"],
        net=data["net"],
        currency="USD",
        categories=categories,
        transaction_count=tx_count,
    )


@router.post("/categorize/run")
def trigger_categorization(db: Session = Depends(get_db)):
    """Synchronously categorize all pending expenses (use for small batches)."""
    repo = ExpenseRepository(db)
    result = _categorization_service.categorize_all_pending(repo)
    return {"message": "Categorization complete", **result}


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: Session = Depends(get_db)):
    repo = ExpenseRepository(db)
    expense = repo.get_by_id(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, updates: ExpenseUpdate, db: Session = Depends(get_db)):
    """Partial update - manually set category, notes, or income flag."""
    repo = ExpenseRepository(db)
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}

    if "category" in update_data:
        update_data["categorization_status"] = "manual"
        update_data["category_confidence"] = 1.0

    expense = repo.update_expense(expense_id, update_data)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    repo = ExpenseRepository(db)
    if not repo.delete_expense(expense_id):
        raise HTTPException(status_code=404, detail="Expense not found")
