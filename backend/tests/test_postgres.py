import os

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Record


@pytest.mark.skipif(not os.getenv("POSTGRES_TEST_URL"), reason="PostgreSQL integration URL not configured")
def test_postgres_seed_and_json_storage():
    engine = create_engine(os.environ["POSTGRES_TEST_URL"])
    with Session(engine) as db:
        rows = list(db.scalars(select(Record).where(Record.tenant == "demo")))
        assert {row.platform for row in rows} == {"claude", "chatgpt", "copilot"}
        assert any(row.resource == "allowlist" and row.data["status"] == "enabled" for row in rows)
        assert any(row.resource == "inventory" and isinstance(row.data["items"], list) for row in rows)
    engine.dispose()