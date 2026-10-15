import hashlib
import json
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.ingestion import chatgpt_compliance, claude_audit, purview_audit
from app.ingestion.normalizer import NormalizedEvent, load_upload
from app.models import GovernanceEvent, Record
from app.schemas import Platform
from app.security import identity, require_write
from app.services import log_event, records_for, serialize

router = APIRouter(prefix="/audit_logs", tags=["audit logs"])
NORMALIZERS = {"claude": claude_audit.normalize, "chatgpt": chatgpt_compliance.normalize, "copilot": purview_audit.normalize}


@router.post("/ingest", status_code=201)
async def ingest(platform: Platform = Form(...), tenant: str = Form(..., min_length=1),
                 file: UploadFile = File(...), db: Session = Depends(get_db), user: dict = Depends(identity)):
    require_write(user)
    rows = await load_upload(file)
    events = []
    for index, row in enumerate(rows):
        try:
            if row.get("platform") and row["platform"] != platform:
                raise ValueError("Row platform differs from the selected import platform; split mixed-platform files first")
            events.append(NormalizedEvent.model_validate(NORMALIZERS[platform](row)).model_dump(mode="json"))
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, f"Row {index + 1}: {exc}") from exc
    inserted = 0
    for event in events:
        dedup = hashlib.sha256(f"{platform}:{tenant}:{event['external_id']}".encode()).hexdigest()
        if db.scalar(select(Record).where(Record.resource == "audit_logs", Record.dedup_key == dedup)):
            continue
        record = Record(resource="audit_logs", platform=platform, tenant=tenant, dedup_key=dedup,
                        data={**event, "platform": platform, "tenant": tenant, "name": event["action"], "owner": event["actor"]})
        try:
            with db.begin_nested():
                db.add(record)
                db.flush()
                log_event(db, record, {}, user["actor"], "ingest")
            inserted += 1
        except IntegrityError:
            continue
    db.commit()
    return {"imported": inserted, "duplicates": len(events) - inserted}


@router.get("")
def search(platform: Platform | None = None, tenant: str | None = None, q: str = "", action: str = "",
           start: date | None = None, end: date | None = None, limit: int = Query(200, ge=1, le=1000),
           offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: dict = Depends(identity)):
    if start and end and start > end:
        raise HTTPException(422, "Start date must not follow end date")
    rows = [serialize(item) for item in records_for(db, "audit_logs", platform, tenant)]
    rows = [item for item in rows if (not q or q.casefold() in str(item).casefold()) and (not action or item["action"] == action)
            and (not start or date.fromisoformat(item["timestamp"][:10]) >= start)
            and (not end or date.fromisoformat(item["timestamp"][:10]) <= end)]
    rows.sort(key=lambda item: item["timestamp"], reverse=True)
    return {"items": rows[offset:offset + limit], "total": len(rows)}


@router.get("/governance/history")
def history(platform: str | None = None, tenant: str | None = None, record_id: str | None = None,
            db: Session = Depends(get_db), user: dict = Depends(identity)):
    query = select(GovernanceEvent).order_by(GovernanceEvent.timestamp.desc())
    if platform:
        query = query.where(GovernanceEvent.platform == platform)
    if tenant:
        query = query.where(GovernanceEvent.tenant == tenant)
    if record_id:
        query = query.where(GovernanceEvent.record_id == record_id)
    return {"items": [{"id": item.id, "record_id": item.record_id, "resource": item.resource, "platform": item.platform,
                       "tenant": item.tenant, "actor": item.actor, "action": item.action, "before": item.before,
                       "after": item.after, "timestamp": item.timestamp.isoformat()} for item in db.scalars(query.limit(1000))]}