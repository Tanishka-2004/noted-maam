"""Initial authentication schema

Revision ID: 193a2f4f7e85
Revises:
Create Date: 2026-07-10 01:58:13.155847

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "193a2f4f7e85"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column('mfa_secret', sa.String(length=255), nullable=True),
        sa.Column('oauth_provider', sa.String(length=50), nullable=True),
        sa.Column('oauth_id', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. Workspaces table
    op.create_table(
        "workspaces",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Memberships table
    op.create_table(
        "memberships",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "workspace_id", name="uq_user_workspace_membership"
        ),
    )

    # 4. Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("family_id", sa.String(length=255), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_sessions_refresh_token_hash"),
        "sessions",
        ["refresh_token_hash"],
        unique=True,
    )
    op.create_index(
        op.f("ix_sessions_family_id"), "sessions", ["family_id"], unique=False
    )

    # 5. Devices table
    op.create_table(
        "devices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("browser", sa.String(length=100), nullable=True),
        sa.Column("operating_system", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("geographic_location", sa.String(length=255), nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )

    # 6. Invitations table
    op.create_table(
        "invitations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("is_accepted", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invitations_token_hash"), "invitations", ["token_hash"], unique=True
    )

    # 7. Meetings table
    op.create_table(
        'meetings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. Audit Logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("workspace_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_audit_logs_event_type"), "audit_logs", ["event_type"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_event_type"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_invitations_token_hash"), table_name="invitations")
    op.drop_table("invitations")
    op.drop_table("devices")
    op.drop_table("meetings")
    op.drop_index(op.f("ix_sessions_family_id"), table_name="sessions")
    op.drop_index(op.f("ix_sessions_refresh_token_hash"), table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("memberships")
    op.drop_table("workspaces")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
