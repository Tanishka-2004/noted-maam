"""create_meeting_domain_tables

Revision ID: 4b8c9d0e1f2a
Revises: 193a2f4f7e85
Create Date: 2026-07-10 02:35:00.000000

"""
from collections.abc import Sequence
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4b8c9d0e1f2a"
down_revision: str | None = "193a2f4f7e85"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop existing placeholder meetings table
    op.drop_table("meetings")

    # 2. Create the real meetings table
    op.create_table(
        "meetings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lifecycle_state", sa.String(length=50), nullable=False),
        sa.Column("settings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create meeting_workflows table
    op.create_table(
        "meeting_workflows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("meeting_id", sa.UUID(), nullable=False),
        sa.Column("stage", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. Create participants table
    op.create_table(
        "participants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("meeting_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("invitation_status", sa.String(length=50), nullable=False),
        sa.Column("is_external", sa.Boolean(), nullable=False),
        sa.Column("speaking_time", sa.Float(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Create recordings table
    op.create_table(
        "recordings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("meeting_id", sa.UUID(), nullable=False),
        sa.Column("s3_bucket", sa.String(length=255), nullable=False),
        sa.Column("s3_key", sa.String(length=1000), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("bitrate", sa.Integer(), nullable=False),
        sa.Column("codec", sa.String(length=50), nullable=False),
        sa.Column("sample_rate", sa.Integer(), nullable=False),
        sa.Column("channels", sa.Integer(), nullable=False),
        sa.Column("upload_status", sa.String(length=50), nullable=False),
        sa.Column("language_hint", sa.String(length=50), nullable=False),
        sa.Column("storage_provider", sa.String(length=50), nullable=False),
        sa.Column("encryption_key_id", sa.String(length=255), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. Create outbox_events table
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_uuid", sa.UUID(), nullable=False),
        sa.Column("aggregate_id", sa.UUID(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("lease_locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_uuid"),
    )
    op.create_index(
        "idx_outbox_pending_events",
        "outbox_events",
        ["status"],
        postgresql_where=sa.text("status = 'PENDING'"),
    )


def downgrade() -> None:
    op.drop_index("idx_outbox_pending_events", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_table("recordings")
    op.drop_table("participants")
    op.drop_table("meeting_workflows")
    op.drop_table("meetings")

    # Re-create the placeholder table
    op.create_table(
        "meetings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
