from datetime import datetime, timezone

from fastapi import Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.crud import resource_router
from app.database import get_db
from app.governance.inventory_diff import inventory_diff
from app.ingestion.normalizer import load_upload
from app.schemas import Platform
from app.security import identity, require_write
from app.services import find_record, records_for, save_record, serialize

router = resource_router("inventory")


@router.post("/import/snapshot", status_code=201)
async def import_snapshot(platform: Platform = Form(...), tenant: str = Form(...), owner: str = Form(...),
                          file: UploadFile = File(...), db: Session = Depends(get_db), user: dict = Depends(identity)):
    require_write(user)
    items = await load_upload(file)
    record = save_record(db, "inventory", {"name": file.filename, "platform": platform, "tenant": tenant,
                         "owner": owner, "items": items, "captured_at": datetime.now(timezone.utc).isoformat()}, user["actor"])
    db.commit()
    return serialize(record)


@router.get("/{record_id}/diff")
def diff(record_id: str, db: Session = Depends(get_db), user: dict = Depends(identity)):
    current = find_record(db, "inventory", record_id)
    previous = next((item for item in records_for(db, "inventory", current.platform, current.tenant)
                     if item.id != current.id and item.created_at < current.created_at and item.data.get("reviewed_at")), None)
    approvals = [item.data for item in records_for(db, "allowlist", current.platform, current.tenant)]
    return {**inventory_diff(current.data["items"], previous.data["items"] if previous else [], approvals),
            "compared_to": previous.id if previous else None}