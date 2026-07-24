"""教师后台的正式数据模型与数据库连接。"""

import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash


def utcnow():
    """返回数据库兼容的无时区 UTC；避免 datetime.utcnow() 弃用。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def new_id(prefix):
    return f"{prefix}_{uuid.uuid4().hex}"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("usr"))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="teacher", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class LoginFailure(Base):
    """登录失败事件；只保存账号和 IP 的哈希，供多进程共享限流状态。"""

    __tablename__ = "login_failures"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("lfail"))
    account_key: Mapped[str] = mapped_column(String(64), index=True)
    ip_key: Mapped[str] = mapped_column(String(64), index=True)
    user_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class UploadFile(Base):
    __tablename__ = "upload_files"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("upl"))
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_type: Mapped[str] = mapped_column(String(120), default="")
    size: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="uploaded", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    jobs = relationship("AIJob", back_populates="upload")


class AIJob(Base):
    __tablename__ = "ai_jobs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("job"))
    upload_id: Mapped[str] = mapped_column(ForeignKey("upload_files.id"), index=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    heartbeat_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    upload = relationship("UploadFile", back_populates="jobs")
    review_items = relationship("ReviewItem", back_populates="job")


class ReviewItem(Base):
    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("rev"))
    job_id: Mapped[str] = mapped_column(ForeignKey("ai_jobs.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), default="pending_review", index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    ai_confidence: Mapped[int] = mapped_column(Integer, default=0)
    review_notes: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    job = relationship("AIJob", back_populates="review_items")


class PublishedContent(Base):
    __tablename__ = "published_content"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("pub"))
    entity_type: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    source_review_id: Mapped[Optional[str]] = mapped_column(ForeignKey("review_items.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class KnowledgeNode(Base):
    """知识图谱的可编辑节点；移动节点不会改变永久 ID 或业务代码。"""

    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kn"))
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("knowledge_nodes.id"), nullable=True, index=True
    )
    node_type: Mapped[str] = mapped_column(String(24), default="concept", index=True)
    knowledge_type: Mapped[str] = mapped_column(String(24), default="concept", index=True)
    title: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    redirect_to_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("knowledge_nodes.id"), nullable=True, index=True
    )
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class KnowledgeNodeVersion(Base):
    """知识节点每次结构变更后的不可变版本快照。"""

    __tablename__ = "knowledge_node_versions"
    __table_args__ = (UniqueConstraint("node_id", "version", name="uq_knowledge_node_version"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("knv"))
    node_id: Mapped[str] = mapped_column(ForeignKey("knowledge_nodes.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    change_reason: Mapped[str] = mapped_column(String(240), default="")
    created_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeAlias(Base):
    """历史代码或旧名称到当前节点的解析入口。"""

    __tablename__ = "knowledge_aliases"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kna"))
    alias: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    alias_type: Mapped[str] = mapped_column(String(24), default="legacy_code")
    node_id: Mapped[str] = mapped_column(ForeignKey("knowledge_nodes.id"), index=True)
    created_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeRelation(Base):
    """知识节点之间的先修、关联、易混淆和扩展关系。"""

    __tablename__ = "knowledge_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "relation_type",
            name="uq_knowledge_relation",
        ),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("knr"))
    source_node_id: Mapped[str] = mapped_column(ForeignKey("knowledge_nodes.id"), index=True)
    target_node_id: Mapped[str] = mapped_column(ForeignKey("knowledge_nodes.id"), index=True)
    relation_type: Mapped[str] = mapped_column(String(32), index=True)
    weight: Mapped[int] = mapped_column(Integer, default=100)
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PublishedKnowledgeNode(Base):
    """公开知识树读取的节点发布快照。"""

    __tablename__ = "published_knowledge_nodes"

    node_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True, index=True)
    node_type: Mapped[str] = mapped_column(String(24))
    knowledge_type: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(160))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    redirect_to_id: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer)
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class PublishedKnowledgeRelation(Base):
    """公开知识图谱读取的关系发布快照。"""

    __tablename__ = "published_knowledge_relations"

    relation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    source_node_id: Mapped[str] = mapped_column(String(40), index=True)
    target_node_id: Mapped[str] = mapped_column(String(40), index=True)
    relation_type: Mapped[str] = mapped_column(String(32), index=True)
    weight: Mapped[int] = mapped_column(Integer, default=100)
    version: Mapped[int] = mapped_column(Integer)
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class KnowledgeDocument(Base):
    """知识点的可编辑版本；正文结构保存在 payload JSON 中。"""

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("kdoc"))
    node_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    knowledge_node_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("knowledge_nodes.id"), nullable=True, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class PublishedKnowledge(Base):
    """公开站点读取的不可变发布快照；后台草稿不会覆盖该表。"""

    __tablename__ = "published_knowledge"

    node_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    knowledge_node_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("knowledge_nodes.id"), nullable=True, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(160))
    version: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    published_by: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("aud"))
    actor_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


DATABASE_URL = os.environ.get(
    "SHUXUE_DATABASE_URL",
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'platform.db')}",
)
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite:"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))


def init_database():
    Base.metadata.create_all(engine)


def ensure_knowledge_graph_seed():
    """仅在知识节点表为空时导入冻结目录，并补齐旧正文的内部 ID 关联。"""

    from knowledge_catalog import legacy_catalog_nodes

    db = SessionLocal()
    try:
        seeded = False
        if db.query(KnowledgeNode).count() == 0:
            now = utcnow()
            for row in legacy_catalog_nodes():
                node = KnowledgeNode(
                    id=row["id"],
                    code=row["code"],
                    parent_id=row["parent_id"],
                    node_type=row["node_type"],
                    knowledge_type=row["knowledge_type"],
                    title=row["title"],
                    sort_order=row["sort_order"],
                    status="published",
                    metadata_json=row["metadata"],
                    version=1,
                    published_at=now,
                )
                db.add(node)
                db.add(
                    KnowledgeAlias(
                        alias=row["code"],
                        alias_type="legacy_code",
                        node_id=row["id"],
                    )
                )
                db.add(
                    KnowledgeNodeVersion(
                        node_id=row["id"],
                        version=1,
                        snapshot=row,
                        change_reason="空数据库引导旧知识目录",
                    )
                )
                db.add(
                    PublishedKnowledgeNode(
                        node_id=row["id"],
                        code=row["code"],
                        parent_id=row["parent_id"],
                        node_type=row["node_type"],
                        knowledge_type=row["knowledge_type"],
                        title=row["title"],
                        sort_order=row["sort_order"],
                        metadata_json=row["metadata"],
                        version=1,
                        published_at=now,
                    )
                )
            db.flush()
            seeded = True

        nodes_by_code = {
            item.code: item.id
            for item in db.query(KnowledgeNode).all()
        }
        changed = False
        for item in db.query(KnowledgeDocument).filter(
            KnowledgeDocument.knowledge_node_id.is_(None)
        ):
            internal_id = nodes_by_code.get(item.node_id)
            if internal_id:
                item.knowledge_node_id = internal_id
                changed = True
        for item in db.query(PublishedKnowledge).filter(
            PublishedKnowledge.knowledge_node_id.is_(None)
        ):
            internal_id = nodes_by_code.get(item.node_id)
            if internal_id:
                item.knowledge_node_id = internal_id
                changed = True
        if changed or seeded:
            db.commit()
    finally:
        SessionLocal.remove()


def ensure_published_knowledge_snapshots():
    """首次升级时把旧的 published 文档回填为公开快照。"""

    db = SessionLocal()
    try:
        rows = db.query(KnowledgeDocument).filter(KnowledgeDocument.status == "published").all()
        changed = False
        for item in rows:
            if db.get(PublishedKnowledge, item.node_id):
                continue
            db.add(
                PublishedKnowledge(
                    node_id=item.node_id,
                    knowledge_node_id=item.knowledge_node_id,
                    title=item.title,
                    version=item.version,
                    payload=item.payload,
                    published_by=item.published_by,
                    published_at=item.published_at or item.updated_at or item.created_at,
                )
            )
            changed = True
        if changed:
            db.commit()
    finally:
        SessionLocal.remove()
