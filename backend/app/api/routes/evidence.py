import csv
import hashlib
import io
import json
import zipfile
from datetime import date, datetime, time, timezone

from fastapi import Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.crud import resource_router
from app.database import get_db
from app.models import GovernanceEvent
from app.schemas import Platform
from app.security import identity

router = resource_router("evidence")


def csv_bytes(rows: list[dict]) -> bytes:
    output = io.StringIO(newline="")
    keys = sorted({key for row in rows for key in row}) or ["id"]
    writer = csv.DictWriter(output, fieldnames=keys)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value) if isinstance(value, (dict, list)) else
                         ("'" + value if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")) else value)
                         for key, value in row.items()})
    return output.getvalue().encode("utf-8")


@router.get("/export/package")
def package(platform: Platform, tenant: str, start: date, end: date, format: str = "json",
            db: Session = Depends(get_db), user: dict = Depends(identity)):
    if start > end or format not in {"json", "csv"}:
        raise HTTPException(422, "Choose a valid date range and json or csv format")
    end_time = datetime.combine(end, time.max, timezone.utc)
    events = list(db.scalars(select(GovernanceEvent).where(GovernanceEvent.platform == platform,
                       GovernanceEvent.tenant == tenant, GovernanceEvent.timestamp <= end_time)
                       .order_by(GovernanceEvent.timestamp, GovernanceEvent.id)))
    states = {}
    activity = []
    for event in events:
        states[event.record_id] = {**event.after, "id": event.record_id, "resource": event.resource}
        if event.timestamp.date() >= start:
            activity.append({"id": event.id, "record_id": event.record_id, "resource": event.resource,
                             "actor": event.actor, "action": event.action, "timestamp": event.timestamp.isoformat(),
                             "before": event.before, "after": event.after})
    groups = {
        "configuration": [item for item in states.values() if item["resource"] in {"baseline", "sharing", "retention"}],
        "entitlements": [item for item in states.values() if item["resource"] in {"allowlist", "datasources", "skills", "inventory"}],
        "changes": [item for item in states.values() if item["resource"] == "changes"],
        "evidence": [item for item in states.values() if item["resource"] == "evidence"],
        "governance_activity": activity,
        "audit_events": [item for item in states.values() if item["resource"] == "audit_logs" and start.isoformat() <= item["timestamp"][:10] <= end.isoformat()],
    }
    files = {f"{key}.{format}": csv_bytes(rows) if format == "csv" else json.dumps(rows, indent=2).encode() for key, rows in groups.items()}
    manifest = {"platform": platform, "tenant": tenant, "start": str(start), "end": str(end),
                "generated_by": user["actor"], "generated_at": datetime.now(timezone.utc).isoformat(),
                "semantics": "Configuration and entitlement state as of end; activity within inclusive UTC date range. Synthetic imports are not vendor attestations.",
                "sha256": {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}}
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    return Response(output.getvalue(), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="aigovern-{platform}-{end}.zip"'})