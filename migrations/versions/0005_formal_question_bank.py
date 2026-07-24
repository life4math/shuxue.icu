"""建立正式题库、版本、知识关联与发布快照。

Revision ID: 0005_formal_question_bank
Revises: 0004_lesson_prep
Create Date: 2026-07-24
"""

import hashlib
import json
import re
import uuid

from alembic import op
from sqlalchemy import select
from sqlalchemy.orm import Session

from platform_db import (
    Base,
    KnowledgeNode,
    PublishedContent,
    PublishedQuestion,
    PublishedQuestionKnowledgeLink,
    Question,
    QuestionKnowledgeLink,
    QuestionVersion,
)


revision = "0005_formal_question_bank"
down_revision = "0004_lesson_prep"
branch_labels = None
depends_on = None

QUESTION_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{1,79}$")
MODULES = {"FUNC", "GEOM", "ALGE", "PROB", "CALC"}
QUESTION_TYPES = {"choice", "fill", "solve", "proof"}


def _text(value, limit):
    return str(value or "").strip()[:limit]


def _normalize_options(value):
    if not isinstance(value, list):
        return []
    options = []
    for index, item in enumerate(value[:8]):
        if isinstance(item, dict):
            label = _text(item.get("label"), 20) or chr(65 + index)
            content = _text(item.get("content"), 6000)
        else:
            label = chr(65 + index)
            content = _text(item, 6000)
        if content:
            options.append({"label": label, "content": content})
    return options


def _normalized_payload(payload):
    payload = payload if isinstance(payload, dict) else {}
    module = _text(payload.get("module"), 20).upper()
    question_type = _text(payload.get("type") or payload.get("question_type"), 20)
    try:
        difficulty = int(payload.get("difficulty", 3))
    except (TypeError, ValueError):
        difficulty = 3
    tags = payload.get("tags") if isinstance(payload.get("tags"), list) else []
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    return {
        "module": module if module in MODULES else "FUNC",
        "question_type": question_type if question_type in QUESTION_TYPES else "solve",
        "difficulty": min(5, max(1, difficulty)),
        "stem": _text(payload.get("stem"), 40000),
        "options": _normalize_options(payload.get("options")),
        "answer": _text(payload.get("answer"), 40000),
        "analysis": _text(payload.get("analysis"), 60000),
        "tags": [_text(item, 100) for item in tags[:30] if _text(item, 100)],
        "source": source,
    }


def _content_hash(payload):
    canonical = {
        "stem": " ".join(payload["stem"].split()),
        "options": payload["options"],
        "answer": " ".join(payload["answer"].split()),
    }
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _snapshot(question, knowledge_node_ids):
    return {
        "code": question.code,
        "module": question.module,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "stem": question.stem,
        "options": question.options_json or [],
        "answer": question.answer,
        "analysis": question.analysis,
        "tags": question.tags_json or [],
        "source": question.source_json or {},
        "knowledge_node_ids": knowledge_node_ids,
    }


def _backfill_published_questions(bind):
    db = Session(bind=bind)
    try:
        rows = db.scalars(
            select(PublishedContent)
            .where(
                PublishedContent.entity_type == "question",
                PublishedContent.status == "published",
            )
            .order_by(PublishedContent.created_at)
        ).all()
        known_codes = set(db.scalars(select(Question.code)).all())
        known_hashes = set(db.scalars(select(Question.content_hash)).all())
        nodes_by_ref = {}
        for node in db.scalars(select(KnowledgeNode)).all():
            nodes_by_ref[node.id] = node
            nodes_by_ref[node.code] = node

        for row in rows:
            payload = _normalized_payload(row.payload)
            if not payload["stem"]:
                continue
            content_hash = _content_hash(payload)
            if content_hash in known_hashes:
                continue

            question_id = f"qst_{uuid.uuid5(uuid.NAMESPACE_URL, row.id).hex}"
            requested_code = _text((row.payload or {}).get("id"), 80).upper()
            code = (
                requested_code
                if QUESTION_CODE_PATTERN.fullmatch(requested_code)
                and requested_code not in known_codes
                else f"Q-{question_id[-10:].upper()}"
            )
            source = dict(payload["source"])
            source["legacy_published_content_id"] = row.id
            question = Question(
                id=question_id,
                code=code,
                owner_id=row.created_by,
                module=payload["module"],
                question_type=payload["question_type"],
                difficulty=payload["difficulty"],
                stem=payload["stem"],
                options_json=payload["options"],
                answer=payload["answer"],
                analysis=payload["analysis"],
                tags_json=payload["tags"],
                source_json=source,
                content_hash=content_hash,
                status="published",
                version=1,
                source_review_id=row.source_review_id,
                created_by=row.created_by,
                updated_by=row.created_by,
                published_by=row.created_by,
                created_at=row.created_at,
                updated_at=row.updated_at,
                published_at=row.created_at,
            )
            db.add(question)
            db.flush()

            knowledge_refs = (row.payload or {}).get("knowledge_points", [])
            knowledge_nodes = []
            if isinstance(knowledge_refs, list):
                for item in knowledge_refs:
                    node = nodes_by_ref.get(str(item))
                    if node and node.id not in {entry.id for entry in knowledge_nodes}:
                        knowledge_nodes.append(node)
            node_ids = [node.id for node in knowledge_nodes]
            snapshot = _snapshot(question, node_ids)
            db.add(
                QuestionVersion(
                    question_id=question.id,
                    version=1,
                    snapshot=snapshot,
                    change_reason="迁移旧版已发布题目",
                    created_by=row.created_by,
                    created_at=row.created_at,
                )
            )
            db.add(
                PublishedQuestion(
                    question_id=question.id,
                    code=question.code,
                    module=question.module,
                    question_type=question.question_type,
                    difficulty=question.difficulty,
                    stem=question.stem,
                    options_json=question.options_json,
                    answer=question.answer,
                    analysis=question.analysis,
                    tags_json=question.tags_json,
                    source_json=question.source_json,
                    version=1,
                    published_by=row.created_by,
                    published_at=row.created_at,
                )
            )
            for index, node in enumerate(knowledge_nodes):
                db.add(
                    QuestionKnowledgeLink(
                        question_id=question.id,
                        knowledge_node_id=node.id,
                        relation_type="related",
                        sort_order=index,
                        created_by=row.created_by,
                        created_at=row.created_at,
                    )
                )
                db.add(
                    PublishedQuestionKnowledgeLink(
                        question_id=question.id,
                        knowledge_node_id=node.id,
                        relation_type="related",
                        sort_order=index,
                    )
                )
            known_codes.add(code)
            known_hashes.add(content_hash)
        db.commit()
    finally:
        db.close()


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())
    _backfill_published_questions(op.get_bind())


def downgrade():
    raise RuntimeError("正式题库迁移不允许自动降级，避免丢失题目与历史版本")
