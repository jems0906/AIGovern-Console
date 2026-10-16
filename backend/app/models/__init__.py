from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Record(Base):
    __tablename__ = "records"
    __table_args__ = (UniqueConstraint("resource", "dedup_key", name="uq_record_dedup"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    resource: Mapped[str] = mapped_column(String(40), index=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)
    tenant: Mapped[str] = mapped_column(String(120), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    dedup_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __mapper_args__ = {"version_id_col": revision}


class GovernanceEvent(Base):
    __tablename__ = "governance_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    record_id: Mapped[str] = mapped_column(String(36), index=True)
    resource: Mapped[str] = mapped_column(String(40), index=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)
    tenant: Mapped[str] = mapped_column(String(120), index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(40))
    before: Mapped[dict] = mapped_column(JSON)
    after: Mapped[dict] = mapped_column(JSON)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"
    __table_args__ = (UniqueConstraint("evidence_id", "sha256", name="uq_evidence_artifact_digest"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("records.id"), index=True)
    filename: Mapped[str] = mapped_column(String(180))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    content: Mapped[bytes] = mapped_column(LargeBinary, deferred=True)
    uploaded_by: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)