from datetime import date, datetime, timezone

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.governance.request_workflow import activation_status, validate_transition
from app.governance.rollout_gates import validate_gate
from app.models import GovernanceEvent, Record, utcnow
from app.schemas import SCHEMAS


def serialize(record: Record) -> dict:
    data = {**record.data, "id": record.id, "revision": record.revision,
            "created_at": record.created_at.isoformat(), "updated_at": record.updated_at.isoformat()}
    if record.resource == "allowlist":
        data["activation_status"] = activation_status(record.data)
    if record.resource in {"baseline", "sharing"}:
        data["drift"] = record.data["approved_value"] != record.data["observed_value"]
    if record.resource == "inventory":
        due = record.data.get("next_review_due")
        data["overdue"] = bool(due and date.fromisoformat(due) < date.today())
    if record.resource == "evidence":
        expiry = record.data.get("expires_at")
        data["expired"] = bool(expiry and date.fromisoformat(expiry) < date.today())
    return data


def find_record(db: Session, resource: str, record_id: str) -> Record:
    record = db.get(Record, record_id)
    if not record or record.resource != resource:
        raise HTTPException(404, "Record not found")
    return record


def records_for(db: Session, resource: str, platform: str | None = None, tenant: str | None = None) -> list[Record]:
    query = select(Record).where(Record.resource == resource)
    if platform:
        query = query.where(Record.platform == platform)
    if tenant:
        query = query.where(Record.tenant == tenant)
    return list(db.scalars(query.order_by(Record.created_at.desc())))


def validate_record(db: Session, resource: str, data: dict, old: Record | None) -> dict:
    try:
        data = SCHEMAS[resource].model_validate(data).model_dump(mode="json")
        previous = old.data if old else {}
        if old and any(data[key] != previous[key] for key in ("platform", "tenant")):
            raise ValueError("Platform and tenant are immutable; create a new record")
        if resource == "allowlist":
            if not old and data["status"] != "submitted":
                raise ValueError("New requests must start as submitted and disabled")
            if data["risk_review"] and date.fromisoformat(data["risk_review"]["reviewed_at"]) > date.today():
                raise ValueError("Security risk review cannot be future-dated")
            if old and any(data[key] != previous[key] for key in ("kind", "external_id", "workspace_agent")):
                raise ValueError("Capability identity is immutable; submit a new request")
            if old and previous["status"] in {"approved", "enabled", "retired", "denied"}:
                if any(data[key] != previous[key] for key in ("risk_review", "data_owner_approval")):
                    raise ValueError("Final approval evidence is immutable; submit a new request for scope changes")
            if old and data["status"] != previous["status"]:
                validate_transition(previous["status"], data["status"], data)
            if data["status"] in {"approved", "enabled"}:
                validate_transition("data_owner_approval", "approved", data)
        elif resource == "datasources" and data["status"] in {"approved", "enabled"}:
            if not data["approval_reference"] or not data["permission_verified_at"]:
                raise ValueError("Source activation requires owner approval reference and permission verification date")
            if date.fromisoformat(data["permission_verified_at"]) > date.today():
                raise ValueError("Permission verification date cannot be in the future")
        elif resource == "inventory":
            if old and any(data[key] != previous[key] for key in ("items", "captured_at")):
                raise ValueError("Snapshot contents are immutable; import a new snapshot")
            if data["reviewed_at"]:
                if not data["reviewer"] or not data["next_review_due"]:
                    raise ValueError("Review sign-off requires reviewer and next review date")
                if date.fromisoformat(data["reviewed_at"]) > date.today():
                    raise ValueError("Review sign-off cannot be future-dated")
                if data["next_review_due"] <= data["reviewed_at"]:
                    raise ValueError("Next review must follow sign-off")
        elif resource == "skills":
            if data["status"] == "retired" and not data["retirement_date"]:
                raise ValueError("Retired Skills require a retirement date")
            if data["superseded"] and not data["retirement_date"]:
                raise ValueError("Superseded Skills require a retirement date")
            versions = list(previous.get("versions", []))
            if data["version"] != previous.get("version"):
                if any(item["version"] == data["version"] for item in versions):
                    raise ValueError("A Skill version cannot be reused")
                versions.append({"version": data["version"], "recorded_at": utcnow().isoformat(), "owner": data["owner"]})
            data["versions"] = versions
        elif resource == "rollout":
            siblings = [item.data for item in records_for(db, resource, data["platform"], data["tenant"]) if not old or item.id != old.id]
            if any(item["phase"] == data["phase"] for item in siblings):
                raise ValueError("Only one record per phase, platform, and tenant is allowed")
            if old and data["phase"] != previous["phase"]:
                raise ValueError("Phase identity is immutable")
            if old and previous["status"] == "completed" and data != previous:
                raise ValueError("Completed phase records are immutable")
            validate_gate(data, siblings)
        elif resource == "changes":
            baseline = find_record(db, "baseline", data["baseline_id"])
            if (baseline.platform, baseline.tenant) != (data["platform"], data["tenant"]):
                raise ValueError("The baseline must belong to the same platform and tenant")
            if not old and data["status"] != "draft":
                raise ValueError("Changes must be created as drafts")
            transitions = {"draft": {"approved"}, "approved": {"implemented", "failed"}, "implemented": {"rolled_back"}, "failed": {"rolled_back"}, "rolled_back": set()}
            if old and data["status"] != previous["status"] and data["status"] not in transitions[previous["status"]]:
                raise ValueError("Invalid change-control transition")
            if old and previous["status"] != "draft":
                mutable = {"status", "outcome"}
                if any(data[key] != previous[key] for key in data if key not in mutable):
                    raise ValueError("Approved change details are locked; create another change")
            if data["status"] != "draft" and not data["approver"]:
                raise ValueError("Change approval requires a named approver")
            if (data["privileged"] or data["risk_level"] in {"high", "critical"}) and not data["rollback_plan"]:
                raise ValueError("Privileged or high-impact changes require a rollback plan")
            start = datetime.fromisoformat(data["scheduled_start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(data["scheduled_end"].replace("Z", "+00:00"))
            if not start.tzinfo or not end.tzinfo or end <= start:
                raise ValueError("A valid timezone-aware scheduled window is required")
            if data["status"] in {"implemented", "failed", "rolled_back"} and not data["outcome"]:
                raise ValueError("A change outcome is required")
            if old and previous["status"] == "approved" and data["status"] == "implemented":
                if not start <= utcnow() <= end:
                    raise ValueError("Implementation must occur within the approved change window")
                if baseline.data["approved_value"] != data["before_value"]:
                    raise ValueError("Baseline changed since this request was prepared")
            if old and data["status"] == "rolled_back" and previous["status"] == "implemented":
                if baseline.data["approved_value"] != data["after_value"]:
                    raise ValueError("Baseline changed; prepare a separate rollback change")
        elif resource == "baseline" and old:
            if data["setting"] != previous["setting"]:
                raise ValueError("Baseline setting identity is immutable")
            if data["approved_value"] != previous["approved_value"]:
                raise ValueError("Approved baseline values can only change through an implemented change request")
        elif resource == "evidence":
            if data["artifact_type"] == "vendor_control_change" and not (data["control_change"] and data["posture_impact"]):
                raise ValueError("Vendor changes require change details and posture impact")
            if data["artifact_type"] == "baa" and not data["obligations"]:
                raise ValueError("BAA evidence must document obligations")
        elif resource == "aup_incidents":
            if data["status"] in {"escalated", "resolved"} or data["severity"] in {"high", "critical"}:
                if not data["escalated_to"] or not data["escalation_reference"]:
                    raise ValueError("This incident requires an Information Security escalation and reference")
            if data["status"] == "resolved" and not data["resolution"]:
                raise ValueError("Resolution notes are required")
        elif resource == "retention":
            if data["review_due"] <= data["approved_at"]:
                raise ValueError("Retention review due date must follow approval")
        return data
    except ValidationError as exc:
        raise HTTPException(422, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def log_event(db: Session, record: Record, before: dict, actor: str, action: str = "update") -> None:
    db.add(GovernanceEvent(record_id=record.id, resource=record.resource, platform=record.platform,
                           tenant=record.tenant, actor=actor, action=action, before=before, after=dict(record.data)))


def save_record(db: Session, resource: str, data: dict, actor: str, old: Record | None = None) -> Record:
    clean = validate_record(db, resource, data, old)
    before = dict(old.data) if old else {}
    record = old or Record(resource=resource, platform=clean["platform"], tenant=clean["tenant"])
    record.data = clean
    record.updated_at = utcnow()
    db.add(record)
    db.flush()
    log_event(db, record, before, actor, "update" if old else "create")
    if resource == "changes" and old and before["status"] != clean["status"]:
        if clean["status"] == "implemented" or (clean["status"] == "rolled_back" and before["status"] == "implemented"):
            baseline = find_record(db, "baseline", clean["baseline_id"])
            baseline_before = dict(baseline.data)
            value = clean["after_value"] if clean["status"] == "implemented" else clean["before_value"]
            baseline.data = {**baseline.data, "approved_value": value, "observed_value": value}
            baseline.updated_at = utcnow()
            log_event(db, baseline, baseline_before, actor, "change_applied")
    return record