from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any


class CategoryForecast(BaseModel):
    category: str
    predicted_amount: float
    currency: str
    confidence_interval_low: Optional[float]
    confidence_interval_high: Optional[float]
    trend: str  # "increasing" | "decreasing" | "stable"


class ForecastResponse(BaseModel):
    forecast_month: str  # YYYY-MM
    total_predicted: float
    currency: str
    categories: List[CategoryForecast]
    model_info: Dict[str, Any]
    months_of_history: int
    generated_at: str

    model_config = {"protected_namespaces": ()}

    @field_validator("categories")
    @classmethod
    def sort_categories(cls, v):
        return sorted(v, key=lambda item: item.predicted_amount, reverse=True)


class TrainResponse(BaseModel):
    status: str
    message: Optional[str] = None
    months_of_history: Optional[int] = None
    categories_trained: Optional[List[str]] = None
    forecast_month: Optional[str] = None


class ModelInfoResponse(BaseModel):
    status: str
    ready_for_forecast: bool
    months_of_history: int
    categories_tracked: List[str]
    last_trained: Optional[str]
    min_months_required: int
    next_forecast_month: Optional[str]
