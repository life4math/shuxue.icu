"""教师后台账号、上传任务、审核与发布 API。"""

import hashlib
import os
import secrets
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Blueprint, jsonify, request, session
from sqlalchemy import select
from werkzeug.utils import secure_filename

from platform_db import (
    AIJob,
    AuditLog,
    PublishedContent,
    ReviewItem,
    SessionLocal,
    UploadFile,
    User,
    KnowledgeDocument,
    init_database,
)


admin_api = Blueprint("admin_api", __name__, url_prefix="/api/v1")
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".docx", ".txt", ".md"}


def _json_error(message, status):
    return jsonify({"error": message}), status


def _current_user(db):
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        db = SessionLocal()
        try:
            user = _current_user(db)
            if not user or not user.is_active:
                return _json_error("authentication required", 401)
            request.current_user = user
            return view(db, *args, **kwargs)
        finally:
            SessionLocal.remove()

    return wrapped


def csrf_required(view):
    @wraps(view)
    def wrapped(db, *args, **kwargs):
        supplied = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not expected or not secrets.compare_digest(supplied, expected):
            return _json_error("invalid csrf token", 403)
        return view(db, *args, **kwargs)

    return wrapped


def _audit(db, user, action, target_type, target_id=None, detail=None):
    db.add(
        AuditLog(
            actor_id=user.id if user else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail or {},
        )
    )


@admin_api.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    if not email or not password:
        return _json_error("email and password are required", 400)

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == email))
        if not user or not user.is_active or not user.check_password(password):
            return _json_error("invalid credentials", 401)
        session.clear()
        session["user_id"] = user.id
        session["csrf_token"] = secrets.token_urlsafe(32)
        user.last_login_at = datetime.utcnow()
        _audit(db, user, "auth.login", "user", user.id)
        db.commit()
        return jsonify(
            {
                "user": {"id": user.id, "email": user.email, "name": user.display_name, "role": user.role},
                "csrf_token": session["csrf_token"],
            }
        )
    finally:
        SessionLocal.remove()


@admin_api.post("/auth/logout")
@login_required
@csrf_required
def logout(db):
    _audit(db, request.current_user, "auth.logout", "user", request.current_user.id)
    db.commit()
    session.clear()
    return jsonify({"success": True})


@admin_api.get("/auth/me")
@login_required
def me(db):
    user = request.current_user
    return jsonify(
        {
            "user": {"id": user.id, "email": user.email, "name": user.display_name, "role": user.role},
            "csrf_token": session.get("csrf_token"),
        }
    )


@admin_api.post("/admin/uploads")
@login_required
@csrf_required
def upload(db):
    file = request.files.get("file")
    if not file or not file.filename:
        return _json_error("file is required", 400)
    original_name = secure_filename(file.filename)
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return _json_error("unsupported file type", 400)

    content = file.read()
    if not content:
        return _json_error("empty file", 400)
    digest = hashlib.sha256(content).hexdigest()
    duplicate = db.scalar(
        select(UploadFile).where(
            UploadFile.owner_id == request.current_user.id,
            UploadFile.sha256 == digest,
        )
    )
    if duplicate:
        return jsonify({"upload": _upload_json(duplicate), "duplicate": True})

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{secrets.token_hex(16)}{ext}"
    destination = UPLOAD_DIR / stored_name
    destination.write_bytes(content)

    record = UploadFile(
        owner_id=request.current_user.id,
        original_name=original_name,
        stored_name=stored_name,
        sha256=digest,
        content_type=file.mimetype or "",
        size=len(content),
    )
    db.add(record)
    db.flush()
    _audit(db, request.current_user, "upload.create", "upload", record.id, {"name": original_name})
    db.commit()
    return jsonify({"upload": _upload_json(record), "duplicate": False}), 201


def _upload_json(item):
    return {
        "id": item.id,
        "name": item.original_name,
        "size": item.size,
        "status": item.status,
        "created_at": item.created_at.isoformat(),
    }


@admin_api.post("/admin/jobs")
@login_required
@csrf_required
def create_job(db):
    body = request.get_json(silent=True) or {}
    upload_record = db.get(UploadFile, body.get("upload_id"))
    if not upload_record or upload_record.owner_id != request.current_user.id:
        return _json_error("upload not found", 404)
    active = db.scalar(
        select(AIJob).where(
            AIJob.upload_id == upload_record.id,
            AIJob.status.in_(["queued", "parsing", "extracting", "validating"]),
        )
    )
    if active:
        return jsonify({"job": _job_json(active), "duplicate": True})
    job = AIJob(upload_id=upload_record.id, owner_id=request.current_user.id)
    db.add(job)
    upload_record.status = "queued"
    db.flush()
    _audit(db, request.current_user, "ai_job.create", "ai_job", job.id)
    db.commit()
    return jsonify({"job": _job_json(job), "duplicate": False}), 201


def _job_json(job):
    return {
        "id": job.id,
        "upload_id": job.upload_id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error_message,
        "created_at": job.created_at.isoformat(),
    }


@admin_api.get("/admin/jobs")
@login_required
def list_jobs(db):
    jobs = db.scalars(
        select(AIJob)
        .where(AIJob.owner_id == request.current_user.id)
        .order_by(AIJob.created_at.desc())
        .limit(100)
    ).all()
    return jsonify({"items": [_job_json(item) for item in jobs]})


@admin_api.get("/admin/reviews")
@login_required
def list_reviews(db):
    rows = db.scalars(
        select(ReviewItem)
        .join(AIJob)
        .where(AIJob.owner_id == request.current_user.id)
        .order_by(ReviewItem.created_at.desc())
        .limit(200)
    ).all()
    return jsonify({"items": [_review_json(item) for item in rows]})


def _review_json(item):
    return {
        "id": item.id,
        "job_id": item.job_id,
        "entity_type": item.entity_type,
        "status": item.status,
        "payload": item.payload,
        "ai_confidence": item.ai_confidence / 100,
        "review_notes": item.review_notes,
        "created_at": item.created_at.isoformat(),
    }


def _knowledge_json(item):
    return {
        "id": item.id,
        "node_id": item.node_id,
        "title": item.title,
        "status": item.status,
        "version": item.version,
        "payload": item.payload,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "published_at": item.published_at.isoformat() if item.published_at else None,
    }


def _valid_knowledge_payload(body):
    if not isinstance(body, dict):
        return None, "payload must be an object"
    title = str(body.get("title", "")).strip()[:160]
    sections = body.get("sections")
    if not title or not isinstance(sections, list) or not sections:
        return None, "title and at least one section are required"
    normalized = []
    for section in sections[:100]:
        if not isinstance(section, dict):
            return None, "section must be an object"
        section_title = str(section.get("title", "")).strip()[:160]
        items = section.get("items")
        if not section_title or not isinstance(items, list):
            return None, "section title and items are required"
        normalized_items = []
        for item in items[:100]:
            if not isinstance(item, dict):
                return None, "item must be an object"
            clean = {}
            for key in ("text", "math", "suffixMath"):
                value = item.get(key)
                if value is not None and str(value).strip():
                    clean[key] = str(value).strip()[:4000]
            if not clean:
                return None, "each item must contain text or KaTeX"
            normalized_items.append(clean)
        if not normalized_items:
            return None, "each section needs at least one item"
        normalized.append({"title": section_title, "items": normalized_items})
    return {"title": title, "sections": normalized}, None


@admin_api.get("/public/knowledge/<node_id>")
def public_knowledge(node_id):
    db = SessionLocal()
    try:
        item = db.scalar(select(KnowledgeDocument).where(
            KnowledgeDocument.node_id == node_id,
            KnowledgeDocument.status == "published",
        ))
        if not item:
            return _json_error("knowledge document not found", 404)
        return jsonify({"knowledge": _knowledge_json(item)})
    finally:
        SessionLocal.remove()


@admin_api.get("/public/knowledge")
def public_knowledge_list():
    db = SessionLocal()
    try:
        rows = db.scalars(select(KnowledgeDocument).where(KnowledgeDocument.status == "published")).all()
        return jsonify({"items": [_knowledge_json(row) for row in rows]})
    finally:
        SessionLocal.remove()


@admin_api.get("/admin/knowledge")
@login_required
def admin_knowledge_list(db):
    rows = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.node_id)).all()
    return jsonify({"items": [_knowledge_json(row) for row in rows]})


@admin_api.put("/admin/knowledge/<node_id>")
@login_required
@csrf_required
def save_knowledge(db, node_id):
    payload, error = _valid_knowledge_payload(request.get_json(silent=True) or {})
    if error:
        return _json_error(error, 400)
    item = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.node_id == node_id))
    if not item:
        item = KnowledgeDocument(
            node_id=node_id,
            title=payload["title"],
            payload=payload,
            status="draft",
            created_by=request.current_user.id,
            updated_by=request.current_user.id,
        )
        db.add(item)
    else:
        if item.status == "pending_review":
            return _json_error("pending document must be reviewed before editing", 409)
        item.title = payload["title"]
        item.payload = payload
        item.version += 1
        item.status = "draft"
        item.updated_by = request.current_user.id
    _audit(db, request.current_user, "knowledge.save", "knowledge", node_id, {"version": item.version})
    db.commit()
    return jsonify({"knowledge": _knowledge_json(item)})


@admin_api.post("/admin/knowledge/<node_id>/submit")
@login_required
@csrf_required
def submit_knowledge(db, node_id):
    item = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.node_id == node_id))
    if not item:
        return _json_error("knowledge document not found", 404)
    if item.status not in {"draft", "rejected"}:
        return _json_error("only draft or rejected documents can be submitted", 409)
    item.status = "pending_review"
    item.updated_by = request.current_user.id
    _audit(db, request.current_user, "knowledge.submit", "knowledge", node_id)
    db.commit()
    return jsonify({"knowledge": _knowledge_json(item)})


@admin_api.post("/admin/knowledge/<node_id>/publish")
@login_required
@csrf_required
def publish_knowledge(db, node_id):
    item = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.node_id == node_id))
    if not item:
        return _json_error("knowledge document not found", 404)
    if item.status not in {"pending_review", "draft"}:
        return _json_error("only draft or pending documents can be published", 409)
    item.status = "published"
    item.published_by = request.current_user.id
    item.published_at = datetime.utcnow()
    item.updated_by = request.current_user.id
    _audit(db, request.current_user, "knowledge.publish", "knowledge", node_id, {"version": item.version})
    db.commit()
    return jsonify({"knowledge": _knowledge_json(item)})


@admin_api.post("/admin/reviews/<review_id>/approve")
@login_required
@csrf_required
def approve_review(db, review_id):
    item = db.get(ReviewItem, review_id)
    if not item or item.job.owner_id != request.current_user.id:
        return _json_error("review item not found", 404)
    if item.status != "pending_review":
        return _json_error("review item is not pending", 409)

    published = PublishedContent(
        entity_type=item.entity_type,
        payload=item.payload,
        source_review_id=item.id,
        created_by=request.current_user.id,
    )
    item.status = "approved"
    item.reviewed_by = request.current_user.id
    item.reviewed_at = datetime.utcnow()
    db.add(published)
    db.flush()
    _audit(db, request.current_user, "review.approve", "review_item", item.id, {"published_id": published.id})
    db.commit()
    return jsonify({"success": True, "published_id": published.id})


@admin_api.post("/admin/reviews/<review_id>/reject")
@login_required
@csrf_required
def reject_review(db, review_id):
    item = db.get(ReviewItem, review_id)
    if not item or item.job.owner_id != request.current_user.id:
        return _json_error("review item not found", 404)
    if item.status != "pending_review":
        return _json_error("review item is not pending", 409)
    body = request.get_json(silent=True) or {}
    item.status = "rejected"
    item.review_notes = str(body.get("notes", ""))[:2000]
    item.reviewed_by = request.current_user.id
    item.reviewed_at = datetime.utcnow()
    _audit(db, request.current_user, "review.reject", "review_item", item.id)
    db.commit()
    return jsonify({"success": True})


@admin_api.get("/public/questions")
def public_questions():
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(PublishedContent)
            .where(PublishedContent.entity_type == "question", PublishedContent.status == "published")
            .order_by(PublishedContent.created_at.desc())
        ).all()
        items = []
        for row in rows:
            payload = dict(row.payload)
            payload.pop("answer", None)
            payload.pop("analysis", None)
            payload["id"] = row.id
            items.append(payload)
        return jsonify({"items": items})
    finally:
        SessionLocal.remove()


def configure_platform(app):
    init_database()
    app.config.update(
        SECRET_KEY=os.environ.get("SHUXUE_SESSION_SECRET") or os.environ.get("SHUXUE_ADMIN_TOKEN"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=not app.debug,
        SESSION_COOKIE_SAMESITE="Strict",
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SHUXUE_SESSION_SECRET or SHUXUE_ADMIN_TOKEN must be configured")
    app.register_blueprint(admin_api)
