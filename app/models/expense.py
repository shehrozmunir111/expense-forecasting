from sqlalchemy import (
    Column, Integer, String, Float, Numeric, Date, DateTime, Text, Boolean, Index,
    ForeignKey,
)
from sqlalchemy.sql import func
from app.database import Base


class CategorizationStatus:
    PENDING = "pending"
    CATEGORIZED = "categorized"
    FAILED = "failed"
    MANUAL = "manual"


EXPENSE_CATEGORIES = [
    "Housing",
    "Transportation",
    "Food & Dining",
    "Utilities",
    "Insurance",
    "Healthcare",
    "Entertainment",
    "Shopping",
    "Education",
    "Travel",
    "Subscriptions",
    "Salary",
    "Freelance",
    "Investment",
    "Other Income",
    "Other Expense",
]


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    # Owner: each expense belongs to one user (nullable for legacy rows / background jobs).
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    raw_text = Column(String(500), nullable=False)
    amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    currency = Column(String(10), default="USD")
    date = Column(Date, nullable=False, index=True)

    # Categorization
    category = Column(String(50), nullable=True, index=True)
    category_confidence = Column(Float, nullable=True)
    categorization_status = Column(
        String(20), default=CategorizationStatus.PENDING, index=True
    )

    # Metadata
    source = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    is_income = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index("ix_expenses_date_category", "date", "category"),
    )


class ForecastCache(Base):
    __tablename__ = "forecast_cache"

    id = Column(Integer, primary_key=True, index=True)
    forecast_month = Column(String(7), nullable=False)  # YYYY-MM
    category = Column(String(50), nullable=False)
    predicted_amount = Column(Numeric(12, 2, asdecimal=False), nullable=False)
    model_version = Column(String(50), nullable=True)
    confidence_interval_low = Column(Float, nullable=True)
    confidence_interval_high = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_forecast_month_category", "forecast_month", "category"),
    )
