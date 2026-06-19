from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import datetime as dt
from app.models.expense import EXPENSE_CATEGORIES


class ExpenseInput(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=500, description="Raw bank transaction text")
    amount: float = Field(..., gt=0, description="Transaction amount (positive)")
    currency: str = Field(default="USD", max_length=10)
    date: dt.date = Field(..., description="Transaction date")
    source: Optional[str] = Field(None, max_length=100, description="Bank or import source")
    notes: Optional[str] = Field(None, max_length=1000)
    is_income: bool = Field(default=False, description="True = income, False = expense")

    model_config = {
        "json_schema_extra": {
            "example": {
                "raw_text": "Walmart grocery 450 USD",
                "amount": 450.0,
                "currency": "USD",
                "date": "2024-01-15",
                "source": "Chase Bank",
            }
        }
    }


class ExpenseBulkUpload(BaseModel):
    expenses: List[ExpenseInput] = Field(..., min_length=1, max_length=1000)
    auto_categorize: bool = Field(
        default=True,
        description="Queue LLM categorization immediately after upload",
    )


class ExpenseOut(BaseModel):
    id: int
    raw_text: str
    amount: float
    currency: str
    date: dt.date
    category: Optional[str]
    category_confidence: Optional[float]
    categorization_status: str
    source: Optional[str]
    notes: Optional[str]
    is_income: bool
    created_at: dt.datetime

    model_config = {"from_attributes": True}


class ExpenseUpdate(BaseModel):
    category: Optional[str] = None
    notes: Optional[str] = None
    is_income: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v is not None and v not in EXPENSE_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(EXPENSE_CATEGORIES)}")
        return v


class BulkUploadResponse(BaseModel):
    total_received: int
    stored: int
    categorization_status: str
    expense_ids: List[int]
    message: str


class CategorySummary(BaseModel):
    category: str
    total_amount: float
    transaction_count: int
    currency: str
    percentage: float


class MonthlySummary(BaseModel):
    month: str
    total_expenses: float
    total_income: float
    net: float
    currency: str
    categories: List[CategorySummary]
    transaction_count: int


class PaginatedExpenses(BaseModel):
    items: List[ExpenseOut]
    total: int
    skip: int
    limit: int
