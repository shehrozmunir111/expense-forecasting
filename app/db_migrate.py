"""Tiny idempotent schema patch.

This project creates tables with ``Base.metadata.create_all`` (no Alembic), which
will NOT add a new column to a table that already exists. Adding ``user_id`` to an
existing ``expenses`` table therefore needs an explicit ALTER. Safe to run on every
startup: it checks first and does nothing if the column is already present.
"""
import logging

from sqlalchemy import inspect, text

from app.database import engine

logger = logging.getLogger(__name__)


def ensure_user_id_column() -> None:
    inspector = inspect(engine)
    if "expenses" not in inspector.get_table_names():
        return  # create_all will build it with the column already present
    columns = {col["name"] for col in inspector.get_columns("expenses")}
    if "user_id" in columns:
        return
    logger.info("Adding missing expenses.user_id column")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE expenses ADD COLUMN user_id INTEGER"))
