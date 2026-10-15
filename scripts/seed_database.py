import csv
import hashlib
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.governance.rollout_gates import ENTRY_CRITERIA, PHASES, REASSESSMENT
from app.models import Record
from app.services import log_event, save_record


def seed() -> None:
    if get_settings().environment == "production":
        raise SystemExit("Synthetic seeding is disabled in production")
    Base.metadata.create_all(engine)
    today = date.today()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        if db.scalar(select(Record).where(Record.tenant == "demo")):
            print("Demo tenant already exists; no records changed.")
            return

        def save(resource: str, platform: str, name: str, owner: str, **fields):
            return save_record(db, resource, {"name": name, "platform": platform, "tenant": "demo", "owner": owner, **fields}, "synthetic-seed")

        def move(resource: str, record: Record, **fields):
            return save_record(db, resource, {**record.data, **fields}, "synthetic-seed", record)

        for platform, owner in [("claude", "Maya Patel"), ("chatgpt", "Lena Ortiz"), ("copilot", "Ava Chen")]:
            items = json.loads((ROOT / "data_samples" / f"inventory_{platform}.json").read_text())
            connector = items[0]
            request = save("allowlist", platform, connector["name"], owner, kind="connector", external_id=connector["external_id"], justification="Curated enterprise knowledge retrieval")
            review = {"reviewer": "Demo Security Reviewer", "reviewed_at": str(today), "data_access_scope": "Read-only curated documents; existing permissions enforced", "publishing_identity": "shared_connection", "external_write_actions": False, "notes": "Synthetic risk review; not production authorization"}
            for status in ["security_review", "data_owner_approval", "approved", "enabled"]:
                move("allowlist", request, status=status, risk_review=review, data_owner_approval="DEMO-OWNER-APPROVAL")
            item = items[1]
            request = save("allowlist", platform, item["name"], item["owner"], kind=item["kind"], external_id=item["external_id"], workspace_agent=item["kind"] == "agent", justification="Controlled pilot with explicit security review")
            move("allowlist", request, status="security_review")
            old = save("inventory", platform, "September reviewed inventory", owner, items=items[:1], captured_at=(now - timedelta(days=40)).isoformat(), reviewer="Demo Governance Reviewer", reviewed_at=str(today - timedelta(days=40)), next_review_due=str(today - timedelta(days=10)))
            save("inventory", platform, "October inventory snapshot", owner, items=items, captured_at=now.isoformat(), next_review_due=str(today - timedelta(days=1)))
            save("skills", platform, "Policy Summary", owner, version="1.0", description="Synthetic policy summarization Skill")
            skill = save("skills", platform, "Evidence Classifier", owner, version="1.0", description="Tags governance evidence")
            move("skills", skill, version="2.1")
            save("datasources", platform, "Curated Policy Library", owner, scope="Read-only policy documents", approval_reference="DEMO-OWNER-APPROVAL", permission_verified_at=str(today - timedelta(days=5)), status="enabled")
            save("datasources", platform, "Claims Knowledge Pilot", owner, scope="Restricted claimant knowledge; no production data", status="pending")
            save("sharing", platform, "Default publishing scope", owner, setting="default_visibility", approved_value="private", observed_value="workspace" if platform == "copilot" else "private", rationale="Default private; explicit sharing approval")
            save("retention", platform, "Synthetic retention decision", owner, position="Demo only: retain normalized evidence for 365 days; do not infer vendor conversation retention", approved_by="Demo Legal Reviewer", approved_at=str(today - timedelta(days=30)), review_due=str(today + timedelta(days=335)), reference="DEMO-RETENTION-001")
            for index, phase in enumerate(PHASES):
                save("rollout", platform, phase.replace("_", " ").title(), owner, phase=phase,
                     entry_criteria={key: index < 2 for key in ENTRY_CRITERIA[phase]},
                     reassessment={key: index < 2 for key in REASSESSMENT},
                     retrospective={"use_cases": "Synthetic knowledge search pilot", "barriers": "Owner review capacity", "next_changes": "Complete access verification"} if index == 0 else {},
                     status="completed" if index == 0 else "active" if index == 1 else "planned")
        with (ROOT / "data_samples" / "baseline_settings.csv").open(newline="") as file:
            for row in csv.DictReader(file):
                baseline = save("baseline", **row)
                change = save("changes", row["platform"], f"Review {row['name'].lower()}", row["owner"], description="Align the approved sharing policy after CAB review", baseline_id=baseline.id, before_value=row["approved_value"], after_value="restricted_group", risk_level="high", privileged=True, rollback_plan=f"Restore {row['approved_value']} and verify entitlements", scheduled_start=(now + timedelta(days=1)).isoformat(), scheduled_end=(now + timedelta(days=1, hours=2)).isoformat())
                move("changes", change, status="approved", approver="Demo CAB Reviewer")
        with (ROOT / "data_samples" / "evidence_register.csv").open(newline="") as file:
            for row in csv.DictReader(file):
                save("evidence", **row)
        with (ROOT / "data_samples" / "audit_events_sample.csv").open(newline="") as file:
            for row in csv.DictReader(file):
                record = Record(resource="audit_logs", platform=row["platform"], tenant="demo", dedup_key=hashlib.sha256(f"{row['platform']}:demo:{row['external_id']}".encode()).hexdigest(), data={**row, "tenant": "demo", "name": row["action"], "owner": row["actor"]})
                db.add(record)
                db.flush()
                log_event(db, record, {}, "synthetic-seed", "ingest")
        save("aup_incidents", "chatgpt", "Synthetic employee-data incident", "Noah Kim", category="employee", severity="high", description="Simulated suspected employee data entry; no actual personal data stored", occurred_at=now.isoformat(), escalated_to="Information Security", escalation_reference="DEMO-SEC-001", status="escalated")
        db.commit()
        print("Synthetic demo tenant created across all three platforms.")


if __name__ == "__main__":
    seed()