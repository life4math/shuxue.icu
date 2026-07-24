"""建立动态知识图谱并迁移 71 个旧目录节点。

Revision ID: 0003_dynamic_knowledge_graph
Revises: 0002_ai_job_reliability
Create Date: 2026-07-24
"""

import uuid

import sqlalchemy as sa
from alembic import op

from knowledge_catalog import legacy_catalog_nodes
from platform_db import (
    Base,
    KnowledgeAlias,
    KnowledgeNode,
    KnowledgeNodeVersion,
    PublishedKnowledgeNode,
    utcnow,
)


revision = "0003_dynamic_knowledge_graph"
down_revision = "0002_ai_job_reliability"
branch_labels = None
depends_on = None


def _stable_id(prefix, value):
    generated = uuid.uuid5(uuid.NAMESPACE_URL, f"https://shuxue.icu/migration/{prefix}/{value}")
    return f"{prefix}_{generated.hex}"


def _ensure_legacy_link(table_name):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    column_items = {item["name"]: item for item in inspector.get_columns(table_name)}
    columns = set(column_items)
    node_id_column = column_items.get("node_id")
    node_id_type = node_id_column["type"] if node_id_column else None
    if (
        isinstance(node_id_type, sa.String)
        and node_id_type.length
        and node_id_type.length < 80
    ):
        with op.batch_alter_table(table_name) as batch:
            batch.alter_column(
                "node_id",
                existing_type=node_id_type,
                type_=sa.String(80),
                existing_nullable=node_id_column["nullable"],
            )
    if "knowledge_node_id" not in columns:
        with op.batch_alter_table(table_name) as batch:
            batch.add_column(sa.Column("knowledge_node_id", sa.String(40), nullable=True))
            batch.create_foreign_key(
                f"fk_{table_name}_knowledge_node_id",
                "knowledge_nodes",
                ["knowledge_node_id"],
                ["id"],
            )
            batch.create_unique_constraint(
                f"uq_{table_name}_knowledge_node_id",
                ["knowledge_node_id"],
            )

    inspector = sa.inspect(bind)
    indexes = {item["name"] for item in inspector.get_indexes(table_name)}
    index_name = f"ix_{table_name}_knowledge_node_id"
    if index_name not in indexes:
        op.create_index(index_name, table_name, ["knowledge_node_id"])


def _seed_legacy_catalog():
    bind = op.get_bind()
    now = utcnow()
    rows = legacy_catalog_nodes()
    existing_codes = set(bind.execute(sa.select(KnowledgeNode.code)).scalars())
    new_rows = []
    for row in rows:
        if row["code"] in existing_codes:
            continue
        new_rows.append(
            {
                **row,
                "created_by": None,
                "updated_by": None,
                "published_by": None,
                "created_at": now,
                "updated_at": now,
                "published_at": now,
            }
        )
    if new_rows:
        bind.execute(sa.insert(KnowledgeNode.__table__), new_rows)

    existing_aliases = set(bind.execute(sa.select(KnowledgeAlias.alias)).scalars())
    aliases = [
        {
            "id": _stable_id("kna", row["code"]),
            "alias": row["code"],
            "alias_type": "legacy_code",
            "node_id": row["id"],
            "created_by": None,
            "created_at": now,
        }
        for row in rows
        if row["code"] not in existing_aliases
    ]
    if aliases:
        bind.execute(sa.insert(KnowledgeAlias.__table__), aliases)

    existing_versions = set(
        bind.execute(
            sa.select(KnowledgeNodeVersion.node_id, KnowledgeNodeVersion.version)
        ).all()
    )
    versions = [
        {
            "id": _stable_id("knv", f"{row['id']}:1"),
            "node_id": row["id"],
            "version": 1,
            "snapshot": row,
            "change_reason": "迁移旧知识目录",
            "created_by": None,
            "created_at": now,
        }
        for row in rows
        if (row["id"], 1) not in existing_versions
    ]
    if versions:
        bind.execute(sa.insert(KnowledgeNodeVersion.__table__), versions)

    existing_published = set(
        bind.execute(sa.select(PublishedKnowledgeNode.node_id)).scalars()
    )
    snapshots = [
        {
            "node_id": row["id"],
            "code": row["code"],
            "parent_id": row["parent_id"],
            "node_type": row["node_type"],
            "knowledge_type": row["knowledge_type"],
            "title": row["title"],
            "sort_order": row["sort_order"],
            "redirect_to_id": None,
            "metadata": row["metadata"],
            "version": 1,
            "published_by": None,
            "published_at": now,
            "updated_at": now,
        }
        for row in rows
        if row["id"] not in existing_published
    ]
    if snapshots:
        bind.execute(sa.insert(PublishedKnowledgeNode.__table__), snapshots)


def _backfill_content_links():
    bind = op.get_bind()
    for table_name in ("knowledge_documents", "published_knowledge"):
        table = sa.table(
            table_name,
            sa.column("node_id", sa.String),
            sa.column("knowledge_node_id", sa.String),
        )
        nodes = sa.table(
            "knowledge_nodes",
            sa.column("id", sa.String),
            sa.column("code", sa.String),
        )
        node_id_query = (
            sa.select(nodes.c.id)
            .where(nodes.c.code == table.c.node_id)
            .scalar_subquery()
        )
        bind.execute(
            sa.update(table)
            .where(table.c.knowledge_node_id.is_(None))
            .where(sa.exists(sa.select(1).where(nodes.c.code == table.c.node_id)))
            .values(knowledge_node_id=node_id_query)
        )


def upgrade():
    bind = op.get_bind()
    # 兼容生产库已执行旧基线、测试库从空库执行最新 Base 的两种路径。
    Base.metadata.create_all(bind=bind)
    _ensure_legacy_link("knowledge_documents")
    _ensure_legacy_link("published_knowledge")
    _seed_legacy_catalog()
    _backfill_content_links()


def downgrade():
    raise RuntimeError("动态知识图谱迁移不允许自动降级，避免丢失教师编辑的数据")
