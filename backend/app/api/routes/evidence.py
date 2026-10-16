import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime, time, timezone
from pathlib import PurePosixPath

from fastapi import Depends, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.crud import resource_router
from app.database import get_db
from app.models import EvidenceArtifact, GovernanceEvent, Record
from app.schemas import Platform
from app.security import identity, require_write
from app.services import find_record

router = resource_router("evidence")


def artifact_metadata(artifact: EvidenceArtifact) -> dict:
    return {"id": artifact.id, "evidence_id": artifact.evidence_id, "filename": artifact.filename,
            "sha256": artifact.sha256, "size_bytes": artifact.size_bytes, "uploaded_by": artifact.uploaded_by,
            "created_at": artifact.created_at.isoformat()}


def artifact_content(artifact: EvidenceArtifact) -> bytes:
    if hashlib.sha256(artifact.content).hexdigest() != artifact.sha256:
        raise HTTPException(500, "Evidence artifact integrity check failed")
    return artifact.content


@router.get("/{record_id}/artifacts")
def list_artifacts(record_id: str, db: Session = Depends(get_db), user: dict = Depends(identity)):
    find_record(db, "evidence", record_id)
    rows = db.scalars(select(EvidenceArtifact).where(EvidenceArtifact.evidence_id == record_id)
                      .order_by(EvidenceArtifact.created_at.desc()))
    return {"items": [artifact_metadata(item) for item in rows]}


@router.post("/{record_id}/artifacts", status_code=201)
async def upload_artifact(record_id: str, file: UploadFile = File(...), db: Session = Depends(get_db), user: dict = Depends(identity)):
    require_write(user)
    evidence = find_record(db, "evidence", record_id)
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", PurePosixPath((file.filename or "").replace("\\", "/")).name)
    if PurePosixPath(filename).suffix.lower() not in {".pdf", ".txt", ".json", ".csv", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(422, "Allowed artifact types: PDF, TXT, JSON, CSV, PNG, JPG, JPEG")
    content = await file.read(5_000_001)
    if not content:
        raise HTTPException(422, "Evidence file must not be empty")
    if len(content) > 5_000_000:
        raise HTTPException(413, "Evidence file exceeds the 5 MB limit")
    artifact = EvidenceArtifact(evidence_id=evidence.id, filename=filename[:180], content=content,
                                sha256=hashlib.sha256(content).hexdigest(), size_bytes=len(content), uploaded_by=user["actor"])
    db.add(artifact)
    try:
        db.flush()
        db.add(GovernanceEvent(record_id=artifact.id, resource="evidence_artifacts", platform=evidence.platform,
                               tenant=evidence.tenant, actor=user["actor"], action="artifact_uploaded", before={},
                               after=artifact_metadata(artifact)))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This file is already attached to the evidence record") from exc
    return artifact_metadata(artifact)


@router.get("/{record_id}/artifacts/{artifact_id}")
def download_artifact(record_id: str, artifact_id: str, db: Session = Depends(get_db), user: dict = Depends(identity)):
    find_record(db, "evidence", record_id)
    artifact = db.get(EvidenceArtifact, artifact_id)
    if not artifact or artifact.evidence_id != record_id:
        raise HTTPException(404, "Evidence file not found")
    return Response(artifact_content(artifact), media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"', "X-Content-SHA256": artifact.sha256})


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
    artifacts = list(db.scalars(select(EvidenceArtifact).join(Record, Record.id == EvidenceArtifact.evidence_id)
                     .where(Record.resource == "evidence", Record.platform == platform, Record.tenant == tenant,
                            EvidenceArtifact.created_at <= end_time)))
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
        "evidence_files": [artifact_metadata(item) for item in artifacts],
        "governance_activity": activity,
        "audit_events": [item for item in states.values() if item["resource"] == "audit_logs" and start.isoformat() <= item["timestamp"][:10] <= end.isoformat()],
    }
    files = {f"{key}.{format}": csv_bytes(rows) if format == "csv" else json.dumps(rows, indent=2).encode() for key, rows in groups.items()}
    files.update({f"artifacts/{item.id}-{item.filename}": artifact_content(item) for item in artifacts})
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