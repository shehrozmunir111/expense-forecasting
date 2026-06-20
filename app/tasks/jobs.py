import logging

from app.core.celery_app import celery_app
from app.database import SessionLocal
from app.repositories.expense_repo import ExpenseRepository
from app.services.categorization import CategorizationService
from app.services.forecasting import forecasting_service

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.jobs.categorize_pending_task", bind=True)
def categorize_pending_task(self):
    """Categorize all pending expenses via the LLM, in the background."""
    db = SessionLocal()
    try:
        repo = ExpenseRepository(db)
        result = CategorizationService().categorize_all_pending(repo)
        logger.info("Celery categorization finished: %s", result)
        return result
    except Exception as exc:
        logger.exception("Categorization task failed")
        raise self.retry(exc=exc, countdown=30, max_retries=2)
    finally:
        db.close()


@celery_app.task(name="app.tasks.jobs.train_forecast_task", bind=True)
def train_forecast_task(self):
    """(Re)train the forecasting model on the current categorized data."""
    db = SessionLocal()
    try:
        repo = ExpenseRepository(db)
        result = forecasting_service.retrain(repo)
        logger.info("Celery forecast retrain finished: %s", result)
        return result
    except Exception as exc:
        logger.exception("Forecast training task failed")
        raise self.retry(exc=exc, countdown=60, max_retries=2)
    finally:
        db.close()
