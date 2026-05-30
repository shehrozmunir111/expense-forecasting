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
