"""Shared test helpers. ``pythonpath = ["src"]`` in pyproject puts ``research`` on path."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from research.models import Market


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point the DB layer at a throwaway sqlite file and create the schema.

    ``db._db_path()`` reads RESEARCH_DB_PATH at call time, so every db call in the test
    (and any route handler) hits this temp file — no real data is touched.
    """
    monkeypatch.setenv("RESEARCH_DB_PATH", str(tmp_path / "test.db"))
    from research import db
    db.init_db()
    return db


@pytest.fixture
def client(temp_db):
    """Flask test client wired to the temp DB (imported after RESEARCH_DB_PATH is set)."""
    from research import app as appmod
    appmod.app.config["TESTING"] = True
    with appmod.app.test_client() as c:
        yield c


def make_market(
    *,
    market_prob: float | None = 0.50,
    days_to_close: float | None = 30.0,
    **overrides: object,
) -> Market:
    """A minimal valid Market for pure-logic tests.

    ``days_to_close`` is converted to an absolute ``end_date`` (None to omit).
    """
    end_date = (
        datetime.now(timezone.utc) + timedelta(days=days_to_close)
        if days_to_close is not None
        else None
    )
    fields: dict = {
        "id": "mkt-1",
        "slug": "test-market",
        "question": "Will it happen?",
        "market_prob": market_prob,
        "volume_24h": 10_000.0,
        "end_date": end_date,
        "tags": [],
        "description": "",
    }
    fields.update(overrides)
    return Market(**fields)
