import io
import json
import zipfile
from datetime import datetime, timedelta, timezone

from app.security import identity
from app.main import app


COMMON = {"name": "Knowledge", "platform": "claude", "tenant": "test", "owner": "owner@example.test"}


def create(client, resource, **fields):
    response = client.post(f"/api/{resource}", json={**COMMON, **fields})
    assert response.status_code == 201, response.text
    return response.json()


def patch(client, resource, record, **fields):
    return client.patch(f"/api/{resource}/{record['id']}", json={"revision": record["revision"], **fields})


def test_source_activation_guard(client):
    source = create(client, "datasources", scope="Read only")
    assert patch(client, "datasources", source, status="enabled").status_code == 422
    response = patch(client, "datasources", source, status="enabled", approval_reference="OWNER-1", permission_verified_at="2026-01-01")
    assert response.status_code == 200


def test_request_cannot_skip_or_remove_review(client):
    request = create(client, "allowlist", kind="agent", external_id="a1", workspace_agent=True, justification="Support")
    assert request["activation_status"] == "disabled"
    assert patch(client, "allowlist", request, status="enabled").status_code == 422
    for status in ["security_review", "data_owner_approval", "approved", "enabled"]:
        response = patch(client, "allowlist", request, status=status, risk_review={"reviewer": "Security", "reviewed_at": "2026-01-01",
                         "data_access_scope": "Read only", "publishing_identity": "shared_connection", "external_write_actions": False}, data_owner_approval="OWNER-1")
        assert response.status_code == 200, response.text
        request = response.json()
    assert request["activation_status"] == "enabled"
    assert patch(client, "allowlist", request, risk_review=None).status_code == 422
    assert patch(client, "allowlist", request, external_id="another-agent").status_code == 422


def test_drift_and_revision(client):
    baseline = create(client, "baseline", setting="sharing", approved_value="private", observed_value="public", rationale="Least privilege")
    assert baseline["drift"] is True
    assert patch(client, "baseline", baseline, approved_value="public").status_code == 422
    assert patch(client, "baseline", baseline, observed_value="private").status_code == 200
    assert patch(client, "baseline", baseline, observed_value="private").status_code == 409


def test_change_applies_and_rolls_back_baseline(client):
    baseline = create(client, "baseline", setting="sharing", approved_value="private", observed_value="private", rationale="Least privilege")
    now = datetime.now(timezone.utc)
    fields = dict(description="Update sharing", baseline_id=baseline["id"], before_value="private", after_value="restricted",
                  risk_level="high", scheduled_start=(now - timedelta(hours=1)).isoformat(), scheduled_end=(now + timedelta(hours=1)).isoformat())
    assert client.post("/api/changes", json={**COMMON, **fields}).status_code == 422
    change = create(client, "changes", **fields, rollback_plan="Restore private")
    for status in ["approved", "implemented", "rolled_back"]:
        response = patch(client, "changes", change, status=status, approver="CAB" if status == "approved" else change["approver"], outcome="Verified")
        assert response.status_code == 200, response.text
        change = response.json()
    assert client.get(f"/api/baseline/{baseline['id']}").json()["approved_value"] == "private"
    history = client.get("/api/audit_logs/governance/history").json()["items"]
    assert any(item["action"] == "change_applied" and item["before"]["approved_value"] == "restricted" for item in history)


def test_shadow_diff_scoped_by_tenant(client):
    items = [{"external_id": "new-agent", "name": "New agent", "kind": "agent"}]
    snapshot = create(client, "inventory", items=items, captured_at="2026-01-01T10:00:00Z")
    result = client.get(f"/api/inventory/{snapshot['id']}/diff").json()
    assert len(result["new"]) == len(result["shadow"]) == 1
    assert patch(client, "inventory", snapshot, items=[]).status_code == 422
    assert patch(client, "inventory", snapshot, reviewer="Reviewer", reviewed_at="2026-01-02", next_review_due="2026-02-02").status_code == 200


def test_audit_ingest_deduplicates_and_packages(client):
    rows = [{"id": "event1", "created_at": "2026-01-01T10:00:00Z", "actor_email": "test@example.test", "event_type": "connector.enabled", "resource": "connector1"}]
    args = {"data": {"platform": "claude", "tenant": "test"}, "files": {"file": ("events.json", json.dumps(rows), "application/json")}}
    assert client.post("/api/audit_logs/ingest", **args).json()["imported"] == 1
    assert client.post("/api/audit_logs/ingest", **args).json()["duplicates"] == 1
    assert client.get("/api/audit_logs?q=connector&start=2026-01-01&end=2026-01-02").json()["total"] == 1
    response = client.get("/api/evidence/export/package?platform=claude&tenant=test&start=2020-01-01&end=2099-01-01&format=csv")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert "manifest.json" in archive.namelist()
        assert b"connector.enabled" in archive.read("audit_events.csv")


def test_rollout_cannot_skip_phase(client):
    response = client.post("/api/rollout", json={**COMMON, "phase": "automation_agents", "status": "active"})
    assert response.status_code == 422


def test_skill_versions_and_incident_escalation(client):
    skill = create(client, "skills", version="1.0")
    updated = patch(client, "skills", skill, version="2.0").json()
    assert [item["version"] for item in updated["versions"]] == ["1.0", "2.0"]
    assert patch(client, "skills", updated, status="retired").status_code == 422
    assert client.post("/api/aup_incidents", json={**COMMON, "category": "employee", "severity": "high", "description": "Synthetic incident", "occurred_at": "2026-01-01T00:00:00Z"}).status_code == 422


def test_viewer_cannot_write(client):
    app.dependency_overrides[identity] = lambda: {"actor": "viewer", "role": "viewer"}
    assert client.get("/api/skills").status_code == 200
    assert client.post("/api/skills", json={**COMMON, "version": "1.0"}).status_code == 403