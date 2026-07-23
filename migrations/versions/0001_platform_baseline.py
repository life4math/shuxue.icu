"""建立教师平台数据库基线。

Revision ID: 0001_platform_baseline
Revises:
Create Date: 2026-07-23
"""

from alembic import op

from platform_db import Base


revision = "0001_platform_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """兼容已有生产库：只创建尚不存在的表，并记录迁移版本。"""
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    raise RuntimeError("数据库基线不允许自动降级，避免误删生产数据")
