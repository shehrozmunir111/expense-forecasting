"""
Tests for ExpenseForecaster in isolation - no LLM calls, no HTTP.
Uses synthetic monthly data to verify train/predict logic.
"""
import os
import pytest
from app.ml.forecaster import ExpenseForecaster
from app.schemas.forecast import CategoryForecast, ForecastResponse
from app.services.categorization import CategorizationService
from app.services.forecasting import ForecastingService


def _make_monthly_data(n_months: int):
    """Generate n_months of synthetic categorized data."""
    data = []
    categories = ["Groceries", "Car/Fuel", "Utilities"]
    base = {"Groceries": 3000.0, "Car/Fuel": 1500.0, "Utilities": 800.0}

    for i in range(n_months):
        year = 2024 + i // 12
        month = (i % 12) + 1
        month_str = f"{year}-{month:02d}"
        for cat in categories:
            data.append({
                "month": month_str,
                "category": cat,
                "total": base[cat] + i * 50.0,
                "count": 10,
            })
    return data


@pytest.fixture
def forecaster(tmp_path, monkeypatch):
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", str(tmp_path / "model.joblib"))
    monkeypatch.setattr("app.ml.forecaster.META_FILE", str(tmp_path / "meta.json"))
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))
    return ExpenseForecaster()


def test_train_insufficient_data(forecaster):
    result = forecaster.train(_make_monthly_data(1))
    assert result["status"] == "insufficient_data"
    assert not forecaster.is_trained


def test_train_no_data(forecaster):
    result = forecaster.train([])
    assert result["status"] == "no_data"


def test_train_success(forecaster):
    result = forecaster.train(_make_monthly_data(4))
    assert result["status"] == "trained"
    assert forecaster.is_trained
    assert result["months_of_history"] == 4
    assert len(result["categories_trained"]) > 0


def test_predict_returns_all_categories(forecaster):
    forecaster.train(_make_monthly_data(4))
    pred = forecaster.predict()
    assert pred is not None
    assert "forecast_month" in pred
    assert "predictions" in pred
    preds = pred["predictions"]
    for cat in ["Groceries", "Car/Fuel", "Utilities"]:
        assert cat in preds
        assert preds[cat]["predicted_amount"] >= 0


def test_predict_ci_is_symmetric(forecaster):
    forecaster.train(_make_monthly_data(4))
    pred = forecaster.predict()
    for cat, data in pred["predictions"].items():
        assert data["confidence_interval_low"] <= data["predicted_amount"]
        assert data["confidence_interval_high"] >= data["predicted_amount"]


def test_predict_trend_field(forecaster):
    forecaster.train(_make_monthly_data(4))
    pred = forecaster.predict()
    valid_trends = {"increasing", "decreasing", "stable"}
    for cat, data in pred["predictions"].items():
        assert data["trend"] in valid_trends


def test_model_persists_and_reloads(forecaster, tmp_path, monkeypatch):
    """Train, then create a new forecaster instance - it should load from disk."""
    model_file = str(tmp_path / "model.joblib")
    meta_file = str(tmp_path / "meta.json")
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", model_file)
    monkeypatch.setattr("app.ml.forecaster.META_FILE", meta_file)
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))

    forecaster.train(_make_monthly_data(3))
    assert os.path.exists(model_file)

    forecaster2 = ExpenseForecaster()
    assert forecaster2.is_trained
    pred = forecaster2.predict()
    assert pred is not None


def test_missing_category_month_uses_zero_last_month_total(forecaster):
    forecaster.train([
        {"month": "2024-01", "category": "Groceries", "total": 100.0, "count": 1},
        {"month": "2024-02", "category": "Utilities", "total": 200.0, "count": 1},
    ])
    assert forecaster.meta["last_month_totals"]["Groceries"] == 0.0
    assert forecaster.meta["last_month_totals"]["Utilities"] == 200.0


def test_forecast_response_sorts_categories():
    response = ForecastResponse(
        forecast_month="2024-03",
        total_predicted=30.0,
        currency="UAH",
        categories=[
            CategoryForecast(
                category="Utilities",
                predicted_amount=10.0,
                currency="UAH",
                confidence_interval_low=8.5,
                confidence_interval_high=11.5,
                trend="stable",
            ),
            CategoryForecast(
                category="Groceries",
                predicted_amount=20.0,
                currency="UAH",
                confidence_interval_low=17.0,
                confidence_interval_high=23.0,
                trend="stable",
            ),
        ],
        model_info={},
        months_of_history=2,
        generated_at="2024-02-01T00:00:00Z",
    )
    assert [c.category for c in response.categories] == ["Groceries", "Utilities"]


def test_categorization_parse_falls_back_for_malformed_items():
    service = CategorizationService()
    result = service._parse_response(
        '[{"category": "Groceries", "confidence": 0.9}, {"id": 2, "category": "Bad"}]',
        fallback_ids=[1, 2],
    )
    assert result == [
        {"id": 1, "category": "Other", "confidence": 0.0},
        {"id": 2, "category": "Other", "confidence": 0.5},
    ]


def test_forecasting_service_handles_repo_exception(tmp_path, monkeypatch):
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", str(tmp_path / "model.joblib"))
    monkeypatch.setattr("app.ml.forecaster.META_FILE", str(tmp_path / "meta.json"))
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))

    class BrokenRepo:
        def get_monthly_aggregates(self):
            raise RuntimeError("database unavailable")

    service = ForecastingService()
    result = service.train(BrokenRepo())
    assert result["status"] == "error"
    assert service.predict(BrokenRepo()) is None


def test_next_month_calculation(forecaster):
    forecaster.train(_make_monthly_data(3))  # 2024-01 to 2024-03
    pred = forecaster.predict()
    assert pred["forecast_month"] == "2024-04"


def test_next_month_year_rollover(forecaster):
    # 12 months starting from 2024-01 - last = 2024-12 - forecast = 2025-01
    forecaster.train(_make_monthly_data(12))
    pred = forecaster.predict()
    assert pred["forecast_month"] == "2025-01"
