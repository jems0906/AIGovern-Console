import hashlib
import io
import json
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest

from app.api.routes.evidence import csv_bytes
from app.governance.inventory_diff import inventory_diff
from app.governance.rollout_gates import ENTRY_CRITERIA, PHASES, REASSESSMENT
from tests.test_api import COMMON, create, patch


@pytest.mark.parametrize("platform,rows", [
    ("claude", [{"id": "1", "created_at": "2026-01-01T00:00:00Z", "actor_email": "a@example.test", "event_type": "read", "resource": "doc"}]),
    ("chatgpt", [{"event_id": "1", "occurred_at": "2026-01-01T00:00:00Z", "user_email": "a@example.test", "event_type": "read", "resource_id": "doc"}]),
    ("copilot", [{"AuditData": json.dumps({"Id": "1", "CreationTime": "2026-01-01T00:00:00Z", "UserId": "a@example.test", "Operation": "read", "ObjectId": "doc"})}]),
])
def test_vendor_normalizers(client, platform, rows):
    response = client.post("/api/audit_logs/ingest", data={"platform": platform, "tenant": "test"}, files={"file": ("events.json", json.dumps(rows))})
    assert response.status_code == 201, response.text
    assert client.get(f"/api/audit_logs?platform={platform}").json()["items"][0]["action"] == "read"


def test_import_is_atomic_and_rejects_mixed_platforms(client):
    event = {"external_id": "1", "timestamp": "2026-01-01T00:00:00Z", "actor": "a", "action": "read", "target": "doc"}
    for bad in [{**event, "timestamp": "invalid"}, {**event, "platform": "copilot"}]:
        response = client.post("/api/audit_logs/ingest", data={"platform": "claude", "tenant": "test"}, files={"file": ("events.json", json.dumps([event, bad]))})
        assert response.status_code == 422
    assert client.get("/api/audit_logs").json()["total"] == 0


def test_csv_snapshot_and_signoff_dates(client):
    response = client.post("/api/inventory/import/snapshot", data={"platform": "claude", "tenant": "test", "owner": "Reviewer"}, files={"file": ("snapshot.csv", "external_id,name,kind\na1,Agent,agent\n")})
    assert response.status_code == 201, response.text
    record = response.json()
    assert len(record["items"]) == 1
    assert patch(client, "inventory", record, reviewed_at="2026-01-01").status_code == 422
    assert patch(client, "inventory", record, reviewed_at="2026-01-01", reviewer="Reviewer", next_review_due="2025-01-01").status_code == 422


def test_diff_matches_kind_and_approval_not_only_id():
    current = [{"kind": "agent", "external_id": "same", "name": "Agent"}]
    assert inventory_diff(current, [], [{"kind": "connector", "external_id": "same", "status": "approved"}])["shadow"] == current
    assert inventory_diff(current, [], [{"kind": "agent", "external_id": "same", "status": "approved"}])["shadow"] == []


def test_rollout_all_four_gates_and_retrospective(client):
    for phase in PHASES:
        record = create(client, "rollout", name=phase, phase=phase)
        assert patch(client, "rollout", record, status="active").status_code == 422
        response = patch(client, "rollout", record, status="active", entry_criteria={key: True for key in ENTRY_CRITERIA[phase]}, reassessment={key: True for key in REASSESSMENT})
        assert response.status_code == 200, response.text
        record = response.json()
        assert patch(client, "rollout", record, status="completed").status_code == 422
        response = patch(client, "rollout", record, status="completed", retrospective={"use_cases": "Search", "barriers": "Capacity", "next_changes": "Training"})
        assert response.status_code == 200, response.text


def test_expired_evidence_and_baa_requirements(client):
    artifact = create(client, "evidence", artifact_type="certification", reference="DEMO-CERT", expires_at="2020-01-01")
    assert artifact["expired"] is True
    assert client.post("/api/evidence", json={**COMMON, "artifact_type": "baa", "reference": "DEMO-BAA"}).status_code == 422
    assert client.post("/api/evidence", json={**COMMON, "artifact_type": "vendor_control_change", "reference": "DEMO-CHANGE"}).status_code == 422


def test_package_checksums_and_tenant_isolation(client):
    create(client, "baseline", setting="scope", approved_value="private", observed_value="private", rationale="Safety")
    params = {"platform": "claude", "tenant": "test", "start": "2020-01-01", "end": "2099-01-01"}
    response = client.get("/api/evidence/export/package", params=params)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for name, digest in manifest["sha256"].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        assert len(json.loads(archive.read("configuration.json"))) == 1
    response = client.get("/api/evidence/export/package", params={**params, "tenant": "other"})
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert json.loads(archive.read("configuration.json")) == []


def test_spreadsheet_formula_injection_is_escaped():
    assert b"'=HYPERLINK" in csv_bytes([{"name": '=HYPERLINK("example")'}])


def test_production_keys_are_enforced(monkeypatch):
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app import security

    monkeypatch.setattr(security, "get_settings", lambda: SimpleNamespace(environment="production", admin_api_key="admin-test", reviewer_api_key="review-test", viewer_api_key="view-test"))
    assert security.identity("Bearer view-test")["role"] == "viewer"
    with pytest.raises(HTTPException) as exc:
        security.identity("Bearer invalid")
    assert exc.value.status_code == 401