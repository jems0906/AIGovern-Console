from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("records",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("resource", sa.String(40), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False), sa.Column("tenant", sa.String(120), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False), sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("dedup_key", sa.String(64), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("resource", "dedup_key", name="uq_record_dedup"))
    for column in ["resource", "platform", "tenant"]:
        op.create_index(f"ix_records_{column}", "records", [column])
    op.create_table("governance_events",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("record_id", sa.String(36), nullable=False),
        sa.Column("resource", sa.String(40), nullable=False), sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("tenant", sa.String(120), nullable=False), sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("action", sa.String(40), nullable=False), sa.Column("before", sa.JSON(), nullable=False),
        sa.Column("after", sa.JSON(), nullable=False), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False))
    for column in ["record_id", "resource", "platform", "tenant", "timestamp"]:
        op.create_index(f"ix_governance_events_{column}", "governance_events", [column])


def downgrade():
    op.drop_table("governance_events")
    op.drop_table("records")