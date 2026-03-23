"""user extensions: email/last_login/webauthn, passkey credentials

Revision ID: c3d4e5f6a1b2
Revises: b2c3d4e5f6a1
Create Date: 2026-03-23 02:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a1b2"
down_revision: str | None = "b2c3d4e5f6a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- users 表新增字段 ---
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("email", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("webauthn_challenge", sa.String(length=512), nullable=True))
        batch_op.create_index(batch_op.f("ix_users_email"), ["email"], unique=True)

    # --- 新表 webauthn_credentials ---
    op.create_table(
        "webauthn_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False),
        sa.Column("device_name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("credential_id"),
    )
    with op.batch_alter_table("webauthn_credentials", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_webauthn_credentials_credential_id"), ["credential_id"], unique=True
        )
        batch_op.create_index(
            batch_op.f("ix_webauthn_credentials_user_id"), ["user_id"], unique=False
        )

    # --- artworks 表新增 imported_by_id ---
    with op.batch_alter_table("artworks", schema=None) as batch_op:
        batch_op.add_column(sa.Column("imported_by_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_artworks_imported_by_id"), ["imported_by_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_artworks_imported_by_id",
            "users",
            ["imported_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # --- bot_post_logs 表新增 posted_by_user_id ---
    with op.batch_alter_table("bot_post_logs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("posted_by_user_id", sa.Integer(), nullable=True))
        batch_op.create_index(
            batch_op.f("ix_bot_post_logs_posted_by_user_id"), ["posted_by_user_id"], unique=False
        )
        batch_op.create_foreign_key(
            "fk_bot_post_logs_posted_by_user_id",
            "users",
            ["posted_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("bot_post_logs", schema=None) as batch_op:
        batch_op.drop_constraint("fk_bot_post_logs_posted_by_user_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_bot_post_logs_posted_by_user_id"))
        batch_op.drop_column("posted_by_user_id")

    with op.batch_alter_table("artworks", schema=None) as batch_op:
        batch_op.drop_constraint("fk_artworks_imported_by_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_artworks_imported_by_id"))
        batch_op.drop_column("imported_by_id")

    with op.batch_alter_table("webauthn_credentials", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_webauthn_credentials_user_id"))
        batch_op.drop_index(batch_op.f("ix_webauthn_credentials_credential_id"))
    op.drop_table("webauthn_credentials")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_users_email"))
        batch_op.drop_column("webauthn_challenge")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("email")
