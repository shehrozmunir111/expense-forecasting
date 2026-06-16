import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.ml.forecaster import ExpenseForecaster
from app.services.forecasting import forecasting_service

TEST_DB_URL = "sqlite:///./data/test_expense.db"

test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=False)
def db():
    Base.metadata.create_all(bind=test_engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db, tmp_path, monkeypatch):
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", str(tmp_path / "model.joblib"))
    monkeypatch.setattr("app.ml.forecaster.META_FILE", str(tmp_path / "meta.json"))
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))
    monkeypatch.setattr("app.routers.expenses.SessionLocal", TestSession)
    # Default HTTP tests to the ephemeral retriever (no on-disk Chroma writes);
    # the persistent-RAG test enables it explicitly with a tmp dir.
    monkeypatch.setattr("app.config.settings.RAG_PERSISTENT", False)
    # Long-term memory also writes to disk; off by default in tests.
    monkeypatch.setattr("app.config.settings.LONG_TERM_MEMORY", False)
    forecasting_service.forecaster = ExpenseForecaster()

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Shared fixtures for the chat / agent / eval suites                           #
# --------------------------------------------------------------------------- #
from datetime import date

from sqlalchemy.pool import StaticPool

from app.models.expense import Expense
from app.repositories.expense_repo import ExpenseRepository
from app.services.finance_tools import FinanceTools

# Groceries: Jan 800 (500+300), Feb 700, Mar 200  -> all-time 1700
# Car/Fuel:  Jan 1200, Feb 1100, Mar 1300          -> all-time 3600 (biggest)
# Dining:    Jan 200, Feb 250, Mar 180             -> all-time 630
SEED_CATEGORIZED = {
    "2024-01": {"Groceries": [500.0, 300.0], "Car/Fuel": [1200.0], "Dining": [200.0]},
    "2024-02": {"Groceries": [700.0], "Car/Fuel": [1100.0], "Dining": [250.0]},
    "2024-03": {"Groceries": [200.0], "Car/Fuel": [1300.0], "Dining": [180.0]},
}


def seed_categorized(session):
    rows = []
    for month, cats in SEED_CATEGORIZED.items():
        year, mm = (int(x) for x in month.split("-"))
        for category, amounts in cats.items():
            for amt in amounts:
                rows.append(Expense(
                    raw_text=f"{category} tx", amount=amt, currency="UAH",
                    date=date(year, mm, 10), category=category,
                    categorization_status="categorized",
                ))
    session.add_all(rows)
    session.commit()


@pytest.fixture
def seeded_tools(tmp_path, monkeypatch):
    """FinanceTools over an isolated in-memory DB with categorized data.

    Forecast model persistence is redirected to tmp_path so tests don't touch
    ./data/models.
    """
    monkeypatch.setattr("app.ml.forecaster.MODEL_FILE", str(tmp_path / "model.joblib"))
    monkeypatch.setattr("app.ml.forecaster.META_FILE", str(tmp_path / "meta.json"))
    monkeypatch.setattr("app.config.settings.MODEL_PATH", str(tmp_path))
    forecasting_service.forecaster = ExpenseForecaster()

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    seed_categorized(session)
    try:
        yield FinanceTools(ExpenseRepository(session))
    finally:
        session.close()
