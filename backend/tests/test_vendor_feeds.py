import asyncio
import json

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.ingestion.claude_audit import normalize as normalize_claude
from app.ingestion.normalizer import NormalizedEvent
from app.ingestion.purview_audit import normalize as normalize_purview
from app.ingestion import vendor_feeds
from app.ingestion.vendor_feeds import normalize_openai_event
from app.models import Record


def test_entra_auth_mode_rejects_non_guid_tenant_id():
    with pytest.raises(ValidationError, match="ENTRA_TENANT_ID must be a valid GUID"):
        Settings(auth_mode="entra", entra_tenant_id="101626",
                 entra_spa_client_id="11111111-1111-1111-1111-111111111111",
                 entra_api_client_id="22222222-2222-2222-2222-222222222222",
                 entra_api_audience="api://22222222-2222-2222-2222-222222222222",
                 entra_api_scope="api://22222222-2222-2222-2222-222222222222/AIGovern.Access")


def test_vendor_polling_cannot_be_enabled_without_a_complete_feed():
    with pytest.raises(ValidationError, match="requires at least one complete vendor feed"):
        Settings(vendor_feeds_enabled=True)


def test_enabled_microsoft_feed_requires_guid_identifiers():
    with pytest.raises(ValidationError, match="O365_TENANT_ID must be a valid GUID"):
        Settings(vendor_feeds_enabled=True, o365_tenant_id="101626",
                 o365_client_id="33333333-3333-3333-3333-333333333333",
                 o365_client_secret="configured-in-secret-manager",
                 o365_publisher_id="44444444-4444-4444-4444-444444444444")


def test_claude_activity_feed_normalizes_minimal_audit_fields():
    normalized = NormalizedEvent.model_validate(normalize_claude({
        "id": "activity_123", "created_at": "2026-10-14T09:10:00Z", "type": "mcp_server_created",
        "actor": {"type": "user_actor", "email_address": "admin@example.test"}, "mcp_server_id": "server_1",
    }))
    assert normalized.external_id == "activity_123"
    assert normalized.actor == "admin@example.test"
    assert normalized.action == "mcp_server_created"
    assert normalized.target == "server_1"


def test_openai_compliance_log_event_gets_stable_fallback_id():
    normalized = NormalizedEvent.model_validate(normalize_openai_event({
        "timestamp": "2026-10-14T09:10:00Z", "event_type": "AUTH_LOG", "actor": {"email": "user@example.test"},
        "resource": "workspace_1", "result": "success",
    }, "log_1", 4))
    assert normalized.external_id == "log_1:4"
    assert normalized.actor == "user@example.test"
    assert normalized.action == "AUTH_LOG"


def test_o365_activity_feed_normalizes_office_audit_fields():
    normalized = NormalizedEvent.model_validate(normalize_purview({
        "Id": "event_1", "CreationTime": "2026-10-14T09:10:00Z", "UserId": "admin@example.test",
        "Operation": "FileDownloaded", "ObjectId": "file_1", "ResultStatus": "Succeeded",
    }))
    assert normalized.external_id == "event_1"
    assert normalized.action == "FileDownloaded"
    assert normalized.target == "file_1"


def test_openai_poll_persists_checkpoint_and_deduplicates(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    test_sessions = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(vendor_feeds, "SessionLocal", test_sessions)

    async def fake_request(client, method, url, *, headers, params=None, data=None, json_body=None):
        if url.endswith("/logs"):
            return httpx.Response(200, json={"data": [{"id": "log_1"}], "has_more": False,
                                              "last_end_time": "2026-10-14T10:00:00Z"},
                                  request=httpx.Request(method, url))
        event = {"timestamp": "2026-10-14T09:10:00Z", "event_type": "AUTH_LOG",
                 "actor": "user@example.test", "target": "workspace_1", "outcome": "success"}
        return httpx.Response(200, content=json.dumps([event]).encode(), request=httpx.Request(method, url))

    monkeypatch.setattr(vendor_feeds, "_request", fake_request)
    settings = Settings(openai_compliance_api_key="test-key", openai_compliance_principal_id="workspace_1",
                        vendor_sync_overlap_seconds=0)
    client = httpx.AsyncClient()
    try:
        asyncio.run(vendor_feeds._sync_openai(client, settings, "AUTH_LOG"))
        asyncio.run(vendor_feeds._sync_openai(client, settings, "AUTH_LOG"))
    finally:
        asyncio.run(client.aclose())

    with test_sessions() as db:
        records = list(db.scalars(select(Record).where(Record.resource == "audit_logs")))
        checkpoint = db.scalar(select(Record).where(Record.resource == "vendor_feed_states"))
    assert len(records) == 1
    assert records[0].data["action"] == "AUTH_LOG"
    assert checkpoint.data["status"] == "ok"
    engine.dispose()