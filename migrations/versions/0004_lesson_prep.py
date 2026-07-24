"""建立在线备课与讲义发布数据模型。

Revision ID: 0004_lesson_prep
Revises: 0003_dynamic_knowledge_graph
Create Date: 2026-07-24
"""

from alembic import op

from platform_db import Base


revision = "0004_lesson_prep"
down_revision = "0003_dynamic_knowledge_graph"
branch_labels = None
depends_on = None


def upgrade():
    # Base.metadata.create_all 可兼容 SQLite 测试库与 PostgreSQL 生产库，
    # 只创建本版本新增且尚不存在的表。
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    raise RuntimeError("备课数据迁移不允许自动降级，避免丢失教师讲义")
