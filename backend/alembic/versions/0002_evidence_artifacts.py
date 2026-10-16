from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("evidence_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_id", sa.String(36), sa.ForeignKey("records.id"), nullable=False),
        sa.Column("filename", sa.String(180), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("uploaded_by", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("evidence_id", "sha256", name="uq_evidence_artifact_digest"))
    op.create_index("ix_evidence_artifacts_evidence_id", "evidence_artifacts", ["evidence_id"])


def downgrade():
    op.drop_table("evidence_artifacts")