from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.repositories.expense_repo import ExpenseRepository
from app.services.forecasting import forecasting_service
from app.tasks.jobs import train_forecast_task
from app.schemas.forecast import (
    ForecastResponse,
    TrainResponse,
    ModelInfoResponse,
    CategoryForecast,
)

router = APIRouter(prefix="/forecast", tags=["Forecast"])


@router.get("/", response_model=ForecastResponse)
def get_forecast(db: Session = Depends(get_db)):
    """Predict next month's expenses per category (auto-trains if needed; requires ~2 months of history)."""
    repo = ExpenseRepository(db)
    result = forecasting_service.predict(repo)

    if result is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "Cannot generate forecast. Need at least 2 months of categorized expense data. "
                "Upload expenses, run /expenses/categorize/run, then retry."
            ),
        )

    categories = [
        CategoryForecast(
            category=cat,
            predicted_amount=data["predicted_amount"],
            currency="USD",
            confidence_interval_low=data["confidence_interval_low"],
            confidence_interval_high=data["confidence_interval_high"],
            trend=data["trend"],
        )
        for cat, data in result["predictions"].items()
    ]

    total = round(sum(c.predicted_amount for c in categories), 2)

    return ForecastResponse(
        forecast_month=result["forecast_month"],
        total_predicted=total,
        currency="USD",
        categories=sorted(categories, key=lambda x: -x.predicted_amount),
        model_info=result["model_info"],
        months_of_history=result["months_of_history"],
        generated_at=datetime.utcnow().isoformat() + "Z",
    )


@router.post("/train", response_model=TrainResponse)
def retrain_model(db: Session = Depends(get_db)):
    """(Re)train the forecasting model on current categorized data."""
    repo = ExpenseRepository(db)
    result = forecasting_service.retrain(repo)
    return TrainResponse(**result)


@router.post("/train/async", status_code=202)
def retrain_model_async():
    """Queue model (re)training as a background Celery job; poll GET /tasks/{task_id} for status."""
    task = train_forecast_task.delay()
    return {"task_id": task.id, "status": "queued"}


@router.get("/model-info", response_model=ModelInfoResponse)
def get_model_info():
    """Return model status, training metadata, and readiness for forecast."""
    info = forecasting_service.get_model_info()
    return ModelInfoResponse(**info)
