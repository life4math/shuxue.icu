"""增加 AI 任务重试与心跳字段。

Revision ID: 0002_ai_job_reliability
Revises: 0001_platform_baseline
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_ai_job_reliability"
down_revision = "0001_platform_baseline"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {item["name"] for item in inspector.get_columns("ai_jobs")}
    with op.batch_alter_table("ai_jobs") as batch:
        if "next_attempt_at" not in columns:
            batch.add_column(sa.Column("next_attempt_at", sa.DateTime(), nullable=True))
        if "heartbeat_at" not in columns:
            batch.add_column(sa.Column("heartbeat_at", sa.DateTime(), nullable=True))

    inspector = sa.inspect(bind)
    indexes = {item["name"] for item in inspector.get_indexes("ai_jobs")}
    if "ix_ai_jobs_next_attempt_at" not in indexes:
        op.create_index("ix_ai_jobs_next_attempt_at", "ai_jobs", ["next_attempt_at"])
    if "ix_ai_jobs_heartbeat_at" not in indexes:
        op.create_index("ix_ai_jobs_heartbeat_at", "ai_jobs", ["heartbeat_at"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {item["name"] for item in inspector.get_indexes("ai_jobs")}
    if "ix_ai_jobs_heartbeat_at" in indexes:
        op.drop_index("ix_ai_jobs_heartbeat_at", table_name="ai_jobs")
    if "ix_ai_jobs_next_attempt_at" in indexes:
        op.drop_index("ix_ai_jobs_next_attempt_at", table_name="ai_jobs")
    columns = {item["name"] for item in sa.inspect(bind).get_columns("ai_jobs")}
    with op.batch_alter_table("ai_jobs") as batch:
        if "heartbeat_at" in columns:
            batch.drop_column("heartbeat_at")
        if "next_attempt_at" in columns:
            batch.drop_column("next_attempt_at")
