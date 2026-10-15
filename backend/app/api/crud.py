from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app.database import get_db
from app.security import identity, require_write
from app.services import find_record, records_for, save_record, serialize
from app.schemas import SCHEMAS


def resource_router(resource: str) -> APIRouter:
    router = APIRouter(prefix=f"/{resource}", tags=[resource])
    schema = SCHEMAS[resource]

    @router.get("")
    def listing(platform: str | None = None, tenant: str | None = None, q: str = "",
                status: str | None = None, limit: int = Query(200, ge=1, le=1000),
                offset: int = Query(0, ge=0), db: Session = Depends(get_db), user: dict = Depends(identity)):
        rows = [serialize(item) for item in records_for(db, resource, platform, tenant)]
        if q:
            rows = [item for item in rows if q.casefold() in str(item).casefold()]
        if status:
            rows = [item for item in rows if item.get("status") == status]
        return {"items": rows[offset:offset + limit], "total": len(rows)}

    @router.post("", status_code=201)
    def create(body: schema, db: Session = Depends(get_db), user: dict = Depends(identity)):
        require_write(user)
        record = save_record(db, resource, body.model_dump(mode="json"), user["actor"])
        db.commit()
        return serialize(record)

    @router.get("/{record_id}")
    def detail(record_id: str, db: Session = Depends(get_db), user: dict = Depends(identity)):
        return serialize(find_record(db, resource, record_id))

    @router.patch("/{record_id}")
    def update(record_id: str, body: dict = Body(...), db: Session = Depends(get_db), user: dict = Depends(identity)):
        require_write(user, review=True)
        record = find_record(db, resource, record_id)
        expected = body.pop("revision", None)
        if expected != record.revision:
            raise HTTPException(409, "Stale or missing revision; refresh the record before saving")
        record = save_record(db, resource, {**record.data, **body}, user["actor"], record)
        try:
            db.commit()
        except StaleDataError as exc:
            db.rollback()
            raise HTTPException(409, "Record changed concurrently; refresh and retry") from exc
        return serialize(record)

    return router