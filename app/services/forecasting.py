import logging
from typing import Dict, Optional
from app.ml.forecaster import ExpenseForecaster
from app.repositories.expense_repo import ExpenseRepository

logger = logging.getLogger(__name__)


class ForecastingService:
    def __init__(self):
        self.forecaster = ExpenseForecaster()

    def load_model(self) -> None:
        """Reload persisted model state during application startup."""
        self.forecaster = ExpenseForecaster()

    def train(self, repo: ExpenseRepository) -> Dict:
        try:
            monthly_data = repo.get_monthly_aggregates()
            result = self.forecaster.train(monthly_data)
            return result
        except Exception as exc:
            logger.exception("Forecast training failed: %s", exc)
            return {"status": "error", "message": "Forecast training failed."}

    def predict(self, repo: ExpenseRepository) -> Optional[Dict]:
        try:
            if not self.forecaster.is_trained:
                train_result = self.train(repo)
                if train_result.get("status") != "trained":
                    return None
            return self.forecaster.predict()
        except Exception as exc:
            logger.exception("Forecast prediction failed: %s", exc)
            return None

    def retrain(self, repo: ExpenseRepository) -> Dict:
        """Force a fresh training run regardless of current state."""
        return self.train(repo)

    def get_model_info(self) -> Dict:
        if not self.forecaster.is_trained:
            return {
                "status": "not_trained",
                "ready_for_forecast": False,
                "months_of_history": 0,
                "categories_tracked": [],
                "last_trained": None,
                "min_months_required": 2,
                "next_forecast_month": None,
            }
        meta = self.forecaster.meta
        return {
            "status": "trained",
            "ready_for_forecast": True,
            "months_of_history": meta.get("months_of_history", 0),
            "categories_tracked": meta.get("categories", []),
            "last_trained": meta.get("trained_at"),
            "min_months_required": 2,
            "next_forecast_month": meta.get("next_month"),
        }


# Module-level singleton - loaded once at startup with persisted model
forecasting_service = ForecastingService()
