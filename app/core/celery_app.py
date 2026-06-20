"""Celery application for expense-forecasting background jobs.

Two real jobs run here (not busywork):
  - forecast model (re)training — CPU-bound scikit-learn work, slow on big data
  - bulk LLM categorization of pending expenses — I/O-bound, many LLM calls

A nightly beat schedule retrains the model so forecasts stay fresh.
Broker + result backend are both Redis (REDIS_URL).
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "expense_forecasting",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,
    # Tiny-instance friendly: release worker memory periodically.
    worker_max_tasks_per_child=25,
    worker_prefetch_multiplier=1,
)

# Beat: retrain the forecasting model every night at 02:00 UTC.
celery_app.conf.beat_schedule = {
    "nightly-retrain-forecast": {
        "task": "app.tasks.jobs.train_forecast_task",
        "schedule": crontab(hour=2, minute=0),
    },
}
