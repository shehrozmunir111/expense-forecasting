import os
import json
import logging
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from app.config import settings

logger = logging.getLogger(__name__)

MODEL_FILE = os.path.join(settings.MODEL_PATH, "expense_model.joblib")
META_FILE = os.path.join(settings.MODEL_PATH, "model_meta.json")


def _next_month(month_str: str) -> str:
    """Return YYYY-MM string for the month following month_str."""
    dt = datetime.strptime(month_str + "-01", "%Y-%m-%d")
    if dt.month == 12:
        return f"{dt.year + 1}-01"
    return f"{dt.year}-{dt.month + 1:02d}"


class ExpenseForecaster:
    def __init__(self):
        self.models: Dict[str, object] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.meta: Dict = {}
        self.is_trained: bool = False
        self._load_if_exists()

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load_if_exists(self):
        if os.path.exists(MODEL_FILE) and os.path.exists(META_FILE):
            try:
                saved = joblib.load(MODEL_FILE)
                self.models = saved["models"]
                self.scalers = saved["scalers"]
                with open(META_FILE) as f:
                    self.meta = json.load(f)
                self.is_trained = True
                logger.info(
                    "Loaded persisted model - %d months of history",
                    self.meta.get("months_of_history", 0),
                )
            except Exception as exc:
                logger.warning("Could not load persisted model: %s", exc)

    def _save(self):
        os.makedirs(settings.MODEL_PATH, exist_ok=True)
        joblib.dump({"models": self.models, "scalers": self.scalers}, MODEL_FILE)
        with open(META_FILE, "w") as f:
            json.dump(self.meta, f, indent=2, default=str)

    # ------------------------------------------------------------------ #
    # Training                                                             #
    # ------------------------------------------------------------------ #

    def train(self, monthly_data: List[Dict]) -> Dict:
        """
        monthly_data: [{month: "2024-01", category: "Groceries", total: 4500.0, count: 12}]
        """
        if not monthly_data:
            return {"status": "no_data", "message": "No categorized expense data found."}

        df = pd.DataFrame(monthly_data)
        df["month_dt"] = pd.to_datetime(df["month"] + "-01")
        df = df.sort_values("month_dt").reset_index(drop=True)

        sorted_months = sorted(df["month"].unique())
        n_months = len(sorted_months)

        if n_months < settings.MIN_MONTHS_FOR_FORECAST:
            return {
                "status": "insufficient_data",
                "message": (
                    f"Need at least {settings.MIN_MONTHS_FOR_FORECAST} months of data. "
                    f"Currently have {n_months}."
                ),
                "months_available": n_months,
            }

        # Ordinal encoding: first month = 0
        month_to_ord = {m: i for i, m in enumerate(sorted_months)}
        categories = sorted(df["category"].unique().tolist())
        observed_totals = {
            (row.month, row.category): float(row.total)
            for row in df.itertuples(index=False)
        }

        grid_rows = []
        for month in sorted_months:
            month_dt = datetime.strptime(month + "-01", "%Y-%m-%d")
            for category in categories:
                grid_rows.append(
                    {
                        "month": month,
                        "category": category,
                        "total": observed_totals.get((month, category), 0.0),
                        "month_dt": month_dt,
                        "month_ord": month_to_ord[month],
                        "month_num": month_dt.month,
                        "quarter": (month_dt.month - 1) // 3 + 1,
                    }
                )
        df = pd.DataFrame(grid_rows)
        trained_categories = []
        category_averages: Dict[str, float] = {}

        self.models = {}
        self.scalers = {}

        for category in categories:
            cat_df = df[df["category"] == category].sort_values("month_ord").copy()
            category_averages[category] = float(cat_df["total"].mean())

            if len(cat_df) < 2:
                logger.debug("Skipping %s - only 1 data point, will use average.", category)
                continue

            # Add lag-1 feature (previous month's spending - most predictive signal)
            cat_df["lag1"] = cat_df["total"].shift(1).fillna(cat_df["total"].mean())

            features = ["month_ord", "month_num", "quarter", "lag1"]
            X = cat_df[features].values
            y = cat_df["total"].values

            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # GradientBoosting for -6 points, LinearRegression otherwise
            if len(cat_df) >= 6:
                model = GradientBoostingRegressor(
                    n_estimators=100, max_depth=2, learning_rate=0.1,
                    subsample=0.8, random_state=42,
                )
            else:
                model = LinearRegression()

            model.fit(X_scaled, y)
            self.models[category] = model
            self.scalers[category] = scaler
            trained_categories.append(category)

        next_month_str = _next_month(sorted_months[-1])

        self.meta = {
            "trained_at": datetime.utcnow().isoformat(),
            "months_of_history": n_months,
            "sorted_months": sorted_months,
            "month_to_ord": month_to_ord,
            "categories": categories,
            "trained_categories": trained_categories,
            "category_averages": category_averages,
            "last_month": sorted_months[-1],
            "next_month": next_month_str,
            # Store last-month totals per category for lag-1 prediction
            "last_month_totals": {
                cat: float(
                    df[(df["category"] == cat) & (df["month"] == sorted_months[-1])]["total"].sum()
                )
                for cat in categories
            },
        }

        self.is_trained = True
        self._save()
        logger.info("Model trained on %d months, %d categories.", n_months, len(trained_categories))

        return {
            "status": "trained",
            "months_of_history": n_months,
            "categories_trained": trained_categories,
            "forecast_month": next_month_str,
        }

    # ------------------------------------------------------------------ #
    # Prediction                                                           #
    # ------------------------------------------------------------------ #

    def predict(self) -> Optional[Dict]:
        if not self.is_trained:
            return None

        next_month_str = self.meta["next_month"]
        next_month_dt = datetime.strptime(next_month_str + "-01", "%Y-%m-%d")

        # Next ordinal = last_ord + 1
        last_ord = max(self.meta["month_to_ord"].values())
        next_ord = last_ord + 1
        next_month_num = next_month_dt.month
        next_quarter = (next_month_num - 1) // 3 + 1

        predictions: Dict[str, Dict] = {}
        category_averages = self.meta.get("category_averages", {})
        last_month_totals = self.meta.get("last_month_totals", {})

        for category in self.meta["categories"]:
            avg = category_averages.get(category, 0.0)

            if category in self.models:
                lag1 = last_month_totals.get(category, avg)
                X = np.array([[next_ord, next_month_num, next_quarter, lag1]])
                scaler = self.scalers[category]
                model = self.models[category]
                pred = float(model.predict(scaler.transform(X))[0])
                pred = max(0.0, pred)  # no negative spending
            else:
                # Fallback: use historical average
                pred = avg

            ci_low = round(pred * 0.85, 2)
            ci_high = round(pred * 1.15, 2)

            if pred > avg * 1.10:
                trend = "increasing"
            elif pred < avg * 0.90:
                trend = "decreasing"
            else:
                trend = "stable"

            predictions[category] = {
                "predicted_amount": round(pred, 2),
                "confidence_interval_low": ci_low,
                "confidence_interval_high": ci_high,
                "trend": trend,
            }

        return {
            "forecast_month": next_month_str,
            "predictions": predictions,
            "months_of_history": self.meta["months_of_history"],
            "model_info": {
                "trained_at": self.meta["trained_at"],
                "algorithm": "GradientBoosting / LinearRegression (per-category)",
                "version": "1.0.0",
                "features": ["month_ordinal", "month_number", "quarter", "lag_1_month"],
            },
        }
