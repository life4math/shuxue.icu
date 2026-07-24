"""教师后台账号、上传任务、审核与发布 API。"""

import hashlib
import json
import os
import re
import secrets
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from platform_db import (
    AIJob,
    AuditLog,
    KnowledgeAlias,
    LoginFailure,
    KnowledgeNode,
    KnowledgeNodeVersion,
    KnowledgeRelation,
    Lecture,
    LectureCourse,
    LectureVersion,
    PublishedKnowledge,
    PublishedKnowledgeNode,
    PublishedKnowledgeRelation,
    PublishedLecture,
    PublishedContent,
    PublishedQuestion,
    PublishedQuestionKnowledgeLink,
    Question,
    QuestionKnowledgeLink,
    QuestionVersion,
    ReviewItem,
    SessionLocal,
    UploadFile,
    User,
    KnowledgeDocument,
    ensure_knowledge_graph_seed,
    ensure_published_knowledge_snapshots,
    init_database,
    new_id,
    utcnow,
)


admin_api = Blueprint("admin_api", __name__, url_prefix="/api/v1")
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".docx", ".txt", ".md"}
LOGIN_COOLDOWN_START = 5
KNOWLEDGE_NODE_TYPES = {"domain", "module", "topic", "concept", "skill"}
KNOWLEDGE_TYPES = {"memory", "concept", "procedure", "design"}
KNOWLEDGE_RELATION_TYPES = {"prerequisite", "related", "often_confused", "extends"}
KNOWLEDGE_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{1,79}$")
QUESTION_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9-]{1,79}$")
QUESTION_MODULES = {"FUNC", "GEOM", "ALGE", "PROB", "CALC"}
QUESTION_TYPES = {"choice", "fill", "solve", "proof"}
LECTURE_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{2,99}$")
LECTURE_BLOCK_TYPES = {
    "text",
    "math",
    "callout",
    "example",
    "question_ref",
    "knowledge_ref",
    "image",
}


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


def admin_required(view):
    @wraps(view)
    def wrapped(db, *args, **kwargs):
        if not request.current_user or request.current_user.role != "admin":
            return _json_error("permission denied", 403)
        return view(db, *args, **kwargs)

    return wrapped


def teacher_required(view):
    @wraps(view)
    def wrapped(db, *args, **kwargs):
        if not request.current_user or request.current_user.role not in {"admin", "teacher"}:
            return _json_error("permission denied", 403)
        return view(db, *args, **kwargs)

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


def _login_key(scope, value):
    return hashlib.sha256(f"{scope}:{value}".encode("utf-8")).hexdigest()


def _client_ip():
    # Gunicorn 仅绑定回环地址，生产请求由受信任的 Nginx 写入 X-Real-IP。
    return request.headers.get("X-Real-IP", "").strip() or request.remote_addr or "unknown"


def _failure_summary(db, column, key, since):
    return db.execute(
        select(func.count(LoginFailure.id), func.min(LoginFailure.created_at), func.max(LoginFailure.created_at))
        .where(column == key, LoginFailure.created_at >= since)
    ).one()


def _retry_after_for_failures(
    count,
    first_at,
    last_at,
    now,
    hard_limit,
    window_seconds,
    progressive_cooldown,
):
    if not count:
        return 0
    if count >= hard_limit:
        expires_at = first_at + timedelta(seconds=window_seconds)
        return max(1, int((expires_at - now).total_seconds()) + 1)
    if progressive_cooldown and count >= LOGIN_COOLDOWN_START:
        cooldown = min(2 ** (count - LOGIN_COOLDOWN_START), 60)
        return max(0, int((last_at + timedelta(seconds=cooldown) - now).total_seconds()) + 1)
    return 0


def _login_retry_after(db, account_key, ip_key, now):
    window_seconds = current_app.config["LOGIN_FAILURE_WINDOW_SECONDS"]
    since = now - timedelta(seconds=window_seconds)
    account = _failure_summary(db, LoginFailure.account_key, account_key, since)
    ip = _failure_summary(db, LoginFailure.ip_key, ip_key, since)
    return max(
        _retry_after_for_failures(
            *account,
            now,
            current_app.config["LOGIN_ACCOUNT_FAILURE_LIMIT"],
            window_seconds,
            True,
        ),
        _retry_after_for_failures(
            *ip,
            now,
            current_app.config["LOGIN_IP_FAILURE_LIMIT"],
            window_seconds,
            False,
        ),
    )


def _rate_limited(retry_after):
    response = jsonify({"error": "too many login attempts", "retry_after": retry_after})
    response.status_code = 429
    response.headers["Retry-After"] = str(retry_after)
    return response


def _clear_login_failures(db, email, ip=None):
    conditions = [LoginFailure.account_key == _login_key("account", email)]
    if ip:
        conditions.append(LoginFailure.ip_key == _login_key("ip", ip))
    db.execute(delete(LoginFailure).where(or_(*conditions)))


def _user_json(user):
    return {
        "id": user.id,
        "email": user.email,
        "name": user.display_name,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }


@admin_api.post("/auth/login")
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    if not email or not password:
        return _json_error("email and password are required", 400)

    db = SessionLocal()
    try:
        now = utcnow()
        ip = _client_ip()
        account_key = _login_key("account", email)
        ip_key = _login_key("ip", ip)
        retry_after = _login_retry_after(db, account_key, ip_key, now)
        if retry_after:
            return _rate_limited(retry_after)

        user = db.scalar(select(User).where(User.email == email))
        if not user or not user.is_active or not user.check_password(password):
            db.add(
                LoginFailure(
                    account_key=account_key,
                    ip_key=ip_key,
                    user_id=user.id if user else None,
                )
            )
            _audit(
                db,
                user,
                "auth.login_failed",
                "user",
                user.id if user else None,
                {"account_key": account_key, "ip_key": ip_key},
            )
            db.commit()
            retry_after = _login_retry_after(db, account_key, ip_key, now)
            if retry_after:
                return _rate_limited(retry_after)
            return _json_error("invalid credentials", 401)

        _clear_login_failures(db, email, ip)
        session.clear()
        session.permanent = True
        session["user_id"] = user.id
        session["csrf_token"] = secrets.token_urlsafe(32)
        user.last_login_at = now
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


def _valid_user_body(body, partial=False):
    if not isinstance(body, dict):
        return None, "payload must be an object"

    payload = {}
    if "display_name" in body:
        display_name = str(body.get("display_name", "")).strip()
        if not display_name:
            return None, "display_name is required"
        if len(display_name) > 80:
            return None, "display_name is too long"
        payload["display_name"] = display_name

    if "role" in body:
        role = str(body.get("role", "")).strip().lower() or "teacher"
        if role not in {"admin", "teacher"}:
            return None, "role must be admin or teacher"
        payload["role"] = role

    if not partial and "display_name" not in payload:
        return None, "display_name is required"
    if not partial and "role" not in payload:
        payload["role"] = "teacher"

    if "is_active" in body:
        if not isinstance(body["is_active"], bool):
            return None, "is_active must be boolean"
        payload["is_active"] = body["is_active"]

    if not partial and (not payload or "email" not in payload):
        if "email" not in payload:
            email = str(body.get("email", "")).strip().lower()
            if not email or "@" not in email:
                return None, "valid email is required"
            payload["email"] = email
        password = str(body.get("password", ""))
        if len(password) < 12:
            return None, "password must be at least 12 characters"
        payload["password"] = password

    return payload, None


@admin_api.get("/admin/users")
@login_required
@admin_required
def admin_users_list(db):
    rows = db.scalars(select(User).order_by(User.created_at.asc())).all()
    return jsonify({"items": [_user_json(row) for row in rows]})


@admin_api.post("/admin/users")
@login_required
@admin_required
@csrf_required
def create_user(db):
    payload, error = _valid_user_body(request.get_json(silent=True) or {})
    if error:
        return _json_error(error, 400)
    if db.scalar(select(User).where(User.email == payload["email"])):
        return _json_error("email already exists", 409)

    user = User(email=payload["email"], display_name=payload["display_name"], role=payload["role"])
    user.set_password(payload["password"])
    db.add(user)
    db.flush()
    _audit(db, request.current_user, "user.create", "user", user.id, {"role": user.role})
    db.commit()
    return jsonify({"user": _user_json(user)}), 201


@admin_api.patch("/admin/users/<user_id>")
@login_required
@admin_required
@csrf_required
def update_user(db, user_id):
    user = db.get(User, user_id)
    if not user:
        return _json_error("user not found", 404)

    payload, error = _valid_user_body(request.get_json(silent=True) or {}, partial=True)
    if error:
        return _json_error(error, 400)
    if not payload:
        return _json_error("no valid fields to update", 400)
    if "display_name" in payload:
        user.display_name = payload["display_name"]
    if "role" in payload:
        if request.current_user.id == user.id and payload["role"] != "admin":
            return _json_error("cannot change your own role", 409)
        user.role = payload["role"]
    if "is_active" in payload:
        if request.current_user.id == user.id and payload["is_active"] is False:
            return _json_error("cannot deactivate your own account", 409)
        user.is_active = payload["is_active"]
    _audit(db, request.current_user, "user.update", "user", user.id, payload)
    db.commit()
    return jsonify({"user": _user_json(user)})


@admin_api.post("/admin/users/<user_id>/reset-password")
@login_required
@admin_required
@csrf_required
def reset_user_password(db, user_id):
    user = db.get(User, user_id)
    if not user:
        return _json_error("user not found", 404)
    body = request.get_json(silent=True) or {}
    password = str(body.get("password", ""))
    if len(password) < 12:
        return _json_error("password must be at least 12 characters", 400)
    user.set_password(password)
    _clear_login_failures(db, user.email)
    _audit(db, request.current_user, "user.reset_password", "user", user.id)
    db.commit()
    return jsonify({"success": True})


@admin_api.post("/admin/users/<user_id>/unlock-login")
@login_required
@admin_required
@csrf_required
def unlock_user_login(db, user_id):
    user = db.get(User, user_id)
    if not user:
        return _json_error("user not found", 404)
    _clear_login_failures(db, user.email)
    _audit(db, request.current_user, "user.unlock_login", "user", user.id)
    db.commit()
    return jsonify({"success": True})


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
    try:
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
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
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
        "attempt_count": job.attempt_count,
        "max_attempts": current_app.config["AI_JOB_MAX_ATTEMPTS"],
        "next_attempt_at": job.next_attempt_at.isoformat() if job.next_attempt_at else None,
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


@admin_api.post("/admin/jobs/<job_id>/retry")
@login_required
@csrf_required
def retry_job(db, job_id):
    job = db.get(AIJob, job_id)
    if not job or job.owner_id != request.current_user.id:
        return _json_error("job not found", 404)
    if job.status != "failed":
        return _json_error("only failed jobs can be retried", 409)

    now = utcnow()
    previous_attempts = job.attempt_count
    job.status = "queued"
    job.progress = 0
    job.error_message = None
    job.attempt_count = 0
    job.next_attempt_at = now
    job.heartbeat_at = None
    job.finished_at = None
    job.upload.status = "queued"
    _audit(
        db,
        request.current_user,
        "ai_job.retry",
        "ai_job",
        job.id,
        {"previous_attempts": previous_attempts},
    )
    db.commit()
    return jsonify({"job": _job_json(job)})


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
        "knowledge_node_id": item.knowledge_node_id,
        "title": item.title,
        "status": item.status,
        "version": item.version,
        "payload": item.payload,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "published_at": item.published_at.isoformat() if item.published_at else None,
    }


def _published_knowledge_json(item):
    return {
        "node_id": item.node_id,
        "knowledge_node_id": item.knowledge_node_id,
        "title": item.title,
        "version": item.version,
        "payload": item.payload,
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


def _knowledge_snapshot(node):
    return {
        "id": node.id,
        "code": node.code,
        "parent_id": node.parent_id,
        "node_type": node.node_type,
        "knowledge_type": node.knowledge_type,
        "title": node.title,
        "sort_order": node.sort_order,
        "status": node.status,
        "redirect_to_id": node.redirect_to_id,
        "metadata": node.metadata_json or {},
        "version": node.version,
    }


def _knowledge_node_json(node):
    payload = _knowledge_snapshot(node)
    payload.update(
        {
            "updated_at": node.updated_at.isoformat() if node.updated_at else None,
            "published_at": node.published_at.isoformat() if node.published_at else None,
        }
    )
    return payload


def _published_node_json(node):
    metadata = node.metadata_json or {}
    return {
        "id": node.node_id,
        "code": node.code,
        "name": node.title,
        "title": node.title,
        "parent_id": node.parent_id,
        "node_type": node.node_type,
        "knowledge_type": node.knowledge_type,
        "sort_order": node.sort_order,
        "redirect_to_id": node.redirect_to_id,
        "metadata": metadata,
        "difficulty": metadata.get("difficulty"),
        "examFrequency": metadata.get("examFrequency"),
        "expanded": bool(metadata.get("expanded")),
        "version": node.version,
        "published_at": node.published_at.isoformat() if node.published_at else None,
    }


def _relation_json(item):
    return {
        "id": item.id,
        "source_node_id": item.source_node_id,
        "target_node_id": item.target_node_id,
        "relation_type": item.relation_type,
        "weight": item.weight,
        "status": item.status,
        "version": item.version,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "published_at": item.published_at.isoformat() if item.published_at else None,
    }


def _published_relation_json(item):
    return {
        "id": item.relation_id,
        "source_node_id": item.source_node_id,
        "target_node_id": item.target_node_id,
        "relation_type": item.relation_type,
        "weight": item.weight,
        "version": item.version,
    }


def _resolve_knowledge_node(db, node_ref, follow_redirect=True):
    item = db.scalar(
        select(KnowledgeNode).where(
            or_(KnowledgeNode.id == node_ref, KnowledgeNode.code == node_ref)
        )
    )
    if not item:
        alias = db.scalar(select(KnowledgeAlias).where(KnowledgeAlias.alias == node_ref))
        if alias:
            item = db.get(KnowledgeNode, alias.node_id)
    visited = set()
    while item and follow_redirect and item.redirect_to_id:
        if item.id in visited:
            return None
        visited.add(item.id)
        item = db.get(KnowledgeNode, item.redirect_to_id)
    return item


def _resolve_published_node(db, node_ref):
    item = db.scalar(
        select(PublishedKnowledgeNode).where(
            or_(
                PublishedKnowledgeNode.node_id == node_ref,
                PublishedKnowledgeNode.code == node_ref,
            )
        )
    )
    if not item:
        alias = db.scalar(select(KnowledgeAlias).where(KnowledgeAlias.alias == node_ref))
        if alias:
            item = db.get(PublishedKnowledgeNode, alias.node_id)
    visited = set()
    while item and item.redirect_to_id:
        if item.node_id in visited:
            return None
        visited.add(item.node_id)
        item = db.get(PublishedKnowledgeNode, item.redirect_to_id)
    return item


def _knowledge_document_for_node(db, node):
    return db.scalar(
        select(KnowledgeDocument).where(
            or_(
                KnowledgeDocument.knowledge_node_id == node.id,
                KnowledgeDocument.node_id == node.code,
            )
        )
    )


def _published_document_for_node(db, node):
    return db.scalar(
        select(PublishedKnowledge).where(
            or_(
                PublishedKnowledge.knowledge_node_id == node.node_id,
                PublishedKnowledge.node_id == node.code,
            )
        )
    )


def _valid_node_metadata(value):
    if value is None:
        return {}
    if not isinstance(value, dict):
        return None
    try:
        if len(json.dumps(value, ensure_ascii=False)) > 20000:
            return None
    except (TypeError, ValueError):
        return None
    difficulty = value.get("difficulty")
    if difficulty is not None:
        if (
            not isinstance(difficulty, list)
            or len(difficulty) != 2
            or any(not isinstance(item, int) or item < 1 or item > 5 for item in difficulty)
            or difficulty[0] > difficulty[1]
        ):
            return None
    frequency = value.get("examFrequency")
    if frequency is not None and frequency not in {"high", "medium", "low"}:
        return None
    return value


def _would_create_knowledge_cycle(db, node_id, parent_id):
    current_id = parent_id
    visited = set()
    while current_id:
        if current_id == node_id or current_id in visited:
            return True
        visited.add(current_id)
        parent = db.get(KnowledgeNode, current_id)
        current_id = parent.parent_id if parent else None
    return False


def _add_knowledge_version(db, node, actor_id, reason):
    db.add(
        KnowledgeNodeVersion(
            node_id=node.id,
            version=node.version,
            snapshot=_knowledge_snapshot(node),
            change_reason=reason[:240],
            created_by=actor_id,
        )
    )


def _publish_node_snapshot(db, node, actor_id):
    snapshot = db.get(PublishedKnowledgeNode, node.id)
    if not snapshot:
        snapshot = PublishedKnowledgeNode(node_id=node.id)
        db.add(snapshot)
    snapshot.code = node.code
    snapshot.parent_id = node.parent_id
    snapshot.node_type = node.node_type
    snapshot.knowledge_type = node.knowledge_type
    snapshot.title = node.title
    snapshot.sort_order = node.sort_order
    snapshot.redirect_to_id = node.redirect_to_id
    snapshot.metadata_json = node.metadata_json or {}
    snapshot.version = node.version
    snapshot.published_by = actor_id
    snapshot.published_at = utcnow()
    return snapshot


def _public_knowledge_tree(db):
    rows = db.scalars(
        select(PublishedKnowledgeNode)
        .where(PublishedKnowledgeNode.redirect_to_id.is_(None))
        .order_by(PublishedKnowledgeNode.sort_order, PublishedKnowledgeNode.code)
    ).all()
    items = {row.node_id: {**_published_node_json(row), "children": []} for row in rows}
    roots = []
    for row in rows:
        item = items[row.node_id]
        parent = items.get(row.parent_id)
        if parent:
            parent["children"].append(item)
        else:
            roots.append(item)
    return roots, rows


@admin_api.get("/public/knowledge-tree")
def public_knowledge_tree():
    db = SessionLocal()
    try:
        tree, rows = _public_knowledge_tree(db)
        relations = db.scalars(
            select(PublishedKnowledgeRelation).order_by(
                PublishedKnowledgeRelation.relation_type,
                PublishedKnowledgeRelation.relation_id,
            )
        ).all()
        response = jsonify(
            {
                "items": tree,
                "relations": [_published_relation_json(item) for item in relations],
                "node_count": len(rows),
            }
        )
        version_sum = sum(item.version for item in rows) + sum(item.version for item in relations)
        response.set_etag(f"knowledge-tree-{len(rows)}-{len(relations)}-{version_sum}")
        response.cache_control.public = True
        response.cache_control.max_age = 0
        response.cache_control.must_revalidate = True
        return response.make_conditional(request)
    finally:
        SessionLocal.remove()


@admin_api.get("/public/knowledge/<node_ref>")
def public_knowledge(node_ref):
    db = SessionLocal()
    try:
        node = _resolve_published_node(db, node_ref)
        if not node:
            return _json_error("knowledge node not found", 404)
        item = _published_document_for_node(db, node)
        if not item:
            return _json_error("knowledge document not found", 404)
        payload = _published_knowledge_json(item)
        payload["knowledge_node_id"] = node.node_id
        payload["code"] = node.code
        response = jsonify({"knowledge": payload})
        response.set_etag(f"knowledge-{node.node_id}-v{item.version}")
        response.cache_control.public = True
        response.cache_control.max_age = 0
        response.cache_control.must_revalidate = True
        return response.make_conditional(request)
    finally:
        SessionLocal.remove()


@admin_api.get("/public/knowledge")
def public_knowledge_list():
    db = SessionLocal()
    try:
        rows = db.scalars(select(PublishedKnowledge).order_by(PublishedKnowledge.node_id)).all()
        return jsonify({"items": [_published_knowledge_json(row) for row in rows]})
    finally:
        SessionLocal.remove()


@admin_api.get("/admin/knowledge/nodes")
@login_required
@teacher_required
def admin_knowledge_nodes(db):
    rows = db.scalars(
        select(KnowledgeNode).order_by(
            KnowledgeNode.parent_id,
            KnowledgeNode.sort_order,
            KnowledgeNode.code,
        )
    ).all()
    documents = {
        item.knowledge_node_id or item.node_id: item.status
        for item in db.scalars(select(KnowledgeDocument)).all()
    }
    items = []
    for row in rows:
        payload = _knowledge_node_json(row)
        payload["document_status"] = documents.get(row.id, documents.get(row.code))
        items.append(payload)
    return jsonify({"items": items})


@admin_api.post("/admin/knowledge/nodes")
@login_required
@teacher_required
@csrf_required
def create_knowledge_node(db):
    body = request.get_json(silent=True) or {}
    title = str(body.get("title", "")).strip()[:160]
    if not title:
        return _json_error("title is required", 400)

    internal_id = new_id("kn")
    requested_code = str(body.get("code", "")).strip().upper()
    code = requested_code or f"KN-{internal_id[-8:].upper()}"
    if not KNOWLEDGE_CODE_PATTERN.fullmatch(code):
        return _json_error("code must use uppercase letters, numbers, and hyphens", 400)
    if db.scalar(select(KnowledgeNode).where(KnowledgeNode.code == code)):
        return _json_error("knowledge code already exists", 409)
    if db.scalar(select(KnowledgeAlias).where(KnowledgeAlias.alias == code)):
        return _json_error("knowledge code is reserved by an alias", 409)

    node_type = str(body.get("node_type", "concept")).strip()
    knowledge_type = str(body.get("knowledge_type", "concept")).strip()
    if node_type not in KNOWLEDGE_NODE_TYPES:
        return _json_error("invalid node type", 400)
    if knowledge_type not in KNOWLEDGE_TYPES:
        return _json_error("invalid knowledge type", 400)

    parent = None
    parent_ref = body.get("parent_id")
    if parent_ref:
        parent = _resolve_knowledge_node(db, str(parent_ref))
        if not parent or parent.status in {"archived", "merged"}:
            return _json_error("parent node not found", 404)

    metadata = _valid_node_metadata(body.get("metadata"))
    if metadata is None:
        return _json_error("invalid knowledge metadata", 400)

    sort_order = body.get("sort_order")
    if sort_order is None:
        sibling_query = select(func.max(KnowledgeNode.sort_order))
        sibling_query = (
            sibling_query.where(KnowledgeNode.parent_id == parent.id)
            if parent
            else sibling_query.where(KnowledgeNode.parent_id.is_(None))
        )
        highest = db.scalar(sibling_query)
        sort_order = (highest if highest is not None else -1) + 1
    if not isinstance(sort_order, int) or sort_order < 0:
        return _json_error("sort_order must be a non-negative integer", 400)

    node = KnowledgeNode(
        id=internal_id,
        code=code,
        parent_id=parent.id if parent else None,
        node_type=node_type,
        knowledge_type=knowledge_type,
        title=title,
        sort_order=sort_order,
        status="draft",
        metadata_json=metadata,
        version=1,
        created_by=request.current_user.id,
        updated_by=request.current_user.id,
    )
    db.add(node)
    db.add(
        KnowledgeAlias(
            alias=code,
            alias_type="code",
            node_id=node.id,
            created_by=request.current_user.id,
        )
    )
    _add_knowledge_version(db, node, request.current_user.id, "创建知识节点")
    _audit(db, request.current_user, "knowledge_node.create", "knowledge_node", node.id, {"code": code})
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _json_error("knowledge node conflicts with an existing record", 409)
    return jsonify({"node": _knowledge_node_json(node)}), 201


@admin_api.patch("/admin/knowledge/nodes/<node_ref>")
@login_required
@teacher_required
@csrf_required
def update_knowledge_node(db, node_ref):
    node = _resolve_knowledge_node(db, node_ref, follow_redirect=False)
    if not node:
        return _json_error("knowledge node not found", 404)
    if node.status in {"archived", "merged"}:
        return _json_error("archived or merged nodes cannot be edited", 409)

    body = request.get_json(silent=True) or {}
    expected_version = body.get("version")
    if not isinstance(expected_version, int):
        return _json_error("version is required", 400)
    if expected_version != node.version:
        return jsonify({"error": "version conflict", "current_version": node.version}), 409

    changed = False
    if "title" in body:
        title = str(body.get("title", "")).strip()[:160]
        if not title:
            return _json_error("title is required", 400)
        if title != node.title:
            node.title = title
            changed = True
    if "node_type" in body:
        node_type = str(body.get("node_type", "")).strip()
        if node_type not in KNOWLEDGE_NODE_TYPES:
            return _json_error("invalid node type", 400)
        if node_type != node.node_type:
            node.node_type = node_type
            changed = True
    if "knowledge_type" in body:
        knowledge_type = str(body.get("knowledge_type", "")).strip()
        if knowledge_type not in KNOWLEDGE_TYPES:
            return _json_error("invalid knowledge type", 400)
        if knowledge_type != node.knowledge_type:
            node.knowledge_type = knowledge_type
            changed = True
    if "metadata" in body:
        metadata = _valid_node_metadata(body.get("metadata"))
        if metadata is None:
            return _json_error("invalid knowledge metadata", 400)
        if metadata != (node.metadata_json or {}):
            node.metadata_json = metadata
            changed = True
    if "sort_order" in body:
        sort_order = body.get("sort_order")
        if not isinstance(sort_order, int) or sort_order < 0:
            return _json_error("sort_order must be a non-negative integer", 400)
        if sort_order != node.sort_order:
            node.sort_order = sort_order
            changed = True
    if "parent_id" in body:
        parent_ref = body.get("parent_id")
        parent = _resolve_knowledge_node(db, str(parent_ref)) if parent_ref else None
        if parent_ref and (not parent or parent.status in {"archived", "merged"}):
            return _json_error("parent node not found", 404)
        parent_id = parent.id if parent else None
        if _would_create_knowledge_cycle(db, node.id, parent_id):
            return _json_error("knowledge hierarchy cannot contain a cycle", 409)
        if parent_id != node.parent_id:
            node.parent_id = parent_id
            changed = True

    if not changed:
        return jsonify({"node": _knowledge_node_json(node)})

    node.version += 1
    node.status = "draft"
    node.updated_by = request.current_user.id
    reason = str(body.get("change_reason", "更新知识节点")).strip() or "更新知识节点"
    _add_knowledge_version(db, node, request.current_user.id, reason)
    _audit(
        db,
        request.current_user,
        "knowledge_node.update",
        "knowledge_node",
        node.id,
        {"version": node.version},
    )
    db.commit()
    return jsonify({"node": _knowledge_node_json(node)})


@admin_api.post("/admin/knowledge/nodes/<node_ref>/publish")
@login_required
@teacher_required
@csrf_required
def publish_knowledge_node(db, node_ref):
    node = _resolve_knowledge_node(db, node_ref, follow_redirect=False)
    if not node:
        return _json_error("knowledge node not found", 404)
    if node.status in {"archived", "merged"}:
        return _json_error("archived or merged nodes cannot be published", 409)
    body = request.get_json(silent=True) or {}
    expected_version = body.get("version")
    if expected_version is not None and expected_version != node.version:
        return jsonify({"error": "version conflict", "current_version": node.version}), 409
    if node.parent_id and not db.get(PublishedKnowledgeNode, node.parent_id):
        return _json_error("publish the parent node first", 409)

    node.status = "published"
    node.published_by = request.current_user.id
    node.published_at = utcnow()
    node.updated_by = request.current_user.id
    _publish_node_snapshot(db, node, request.current_user.id)
    _audit(
        db,
        request.current_user,
        "knowledge_node.publish",
        "knowledge_node",
        node.id,
        {"version": node.version},
    )
    db.commit()
    return jsonify({"node": _knowledge_node_json(node)})


@admin_api.post("/admin/knowledge/nodes/<node_ref>/archive")
@login_required
@teacher_required
@csrf_required
def archive_knowledge_node(db, node_ref):
    node = _resolve_knowledge_node(db, node_ref, follow_redirect=False)
    if not node:
        return _json_error("knowledge node not found", 404)
    body = request.get_json(silent=True) or {}
    if body.get("version") != node.version:
        return jsonify({"error": "version conflict", "current_version": node.version}), 409
    child = db.scalar(
        select(KnowledgeNode).where(
            KnowledgeNode.parent_id == node.id,
            KnowledgeNode.status.notin_({"archived", "merged"}),
        )
    )
    if child:
        return _json_error("archive or move child nodes first", 409)

    node.status = "archived"
    node.version += 1
    node.updated_by = request.current_user.id
    _add_knowledge_version(db, node, request.current_user.id, "归档知识节点")
    snapshot = db.get(PublishedKnowledgeNode, node.id)
    if snapshot:
        db.delete(snapshot)
    _audit(db, request.current_user, "knowledge_node.archive", "knowledge_node", node.id)
    db.commit()
    return jsonify({"node": _knowledge_node_json(node)})


@admin_api.post("/admin/knowledge/nodes/<node_ref>/merge")
@login_required
@teacher_required
@csrf_required
def merge_knowledge_node(db, node_ref):
    source = _resolve_knowledge_node(db, node_ref, follow_redirect=False)
    body = request.get_json(silent=True) or {}
    target = _resolve_knowledge_node(db, str(body.get("target_id", "")))
    if not source or not target:
        return _json_error("source or target node not found", 404)
    if source.id == target.id:
        return _json_error("a node cannot be merged into itself", 409)
    if body.get("version") != source.version:
        return jsonify({"error": "version conflict", "current_version": source.version}), 409
    if source.status in {"archived", "merged"} or target.status != "published":
        return _json_error("source must be active and target must be published", 409)
    child = db.scalar(
        select(KnowledgeNode).where(
            KnowledgeNode.parent_id == source.id,
            KnowledgeNode.status.notin_({"archived", "merged"}),
        )
    )
    if child:
        return _json_error("move or merge child nodes first", 409)
    relation = db.scalar(
        select(KnowledgeRelation).where(
            or_(
                KnowledgeRelation.source_node_id == source.id,
                KnowledgeRelation.target_node_id == source.id,
            ),
            KnowledgeRelation.status != "archived",
        )
    )
    if relation:
        return _json_error("remove or migrate relations before merging", 409)

    source_document = _knowledge_document_for_node(db, source)
    target_document = _knowledge_document_for_node(db, target)
    source_published = db.scalar(
        select(PublishedKnowledge).where(
            or_(
                PublishedKnowledge.knowledge_node_id == source.id,
                PublishedKnowledge.node_id == source.code,
            )
        )
    )
    target_snapshot = db.get(PublishedKnowledgeNode, target.id)
    target_published = _published_document_for_node(db, target_snapshot) if target_snapshot else None
    if source_document and target_document:
        return _json_error("both nodes have editable content; merge the content first", 409)
    if source_published and target_published:
        return _json_error("both nodes have published content; merge the content first", 409)
    if source_document:
        source_document.knowledge_node_id = target.id
        source_document.node_id = target.code
    if source_published:
        source_published.knowledge_node_id = target.id
        source_published.node_id = target.code

    source.status = "merged"
    source.redirect_to_id = target.id
    source.version += 1
    source.updated_by = request.current_user.id
    _add_knowledge_version(db, source, request.current_user.id, f"合并到 {target.code}")
    _publish_node_snapshot(db, source, request.current_user.id)
    _audit(
        db,
        request.current_user,
        "knowledge_node.merge",
        "knowledge_node",
        source.id,
        {"target_id": target.id},
    )
    db.commit()
    return jsonify(
        {
            "node": _knowledge_node_json(source),
            "redirect_to": _knowledge_node_json(target),
        }
    )


@admin_api.get("/admin/knowledge/relations")
@login_required
@teacher_required
def admin_knowledge_relations(db):
    rows = db.scalars(
        select(KnowledgeRelation).order_by(
            KnowledgeRelation.relation_type,
            KnowledgeRelation.created_at,
        )
    ).all()
    return jsonify({"items": [_relation_json(item) for item in rows]})


@admin_api.post("/admin/knowledge/relations")
@login_required
@teacher_required
@csrf_required
def create_knowledge_relation(db):
    body = request.get_json(silent=True) or {}
    source = _resolve_knowledge_node(db, str(body.get("source_node_id", "")))
    target = _resolve_knowledge_node(db, str(body.get("target_node_id", "")))
    relation_type = str(body.get("relation_type", "")).strip()
    weight = body.get("weight", 100)
    if not source or not target:
        return _json_error("source or target node not found", 404)
    if source.id == target.id:
        return _json_error("a node cannot relate to itself", 409)
    if relation_type not in KNOWLEDGE_RELATION_TYPES:
        return _json_error("invalid relation type", 400)
    if not isinstance(weight, int) or weight < 1 or weight > 100:
        return _json_error("weight must be between 1 and 100", 400)
    item = KnowledgeRelation(
        source_node_id=source.id,
        target_node_id=target.id,
        relation_type=relation_type,
        weight=weight,
        status="draft",
        created_by=request.current_user.id,
        updated_by=request.current_user.id,
    )
    db.add(item)
    _audit(db, request.current_user, "knowledge_relation.create", "knowledge_relation", item.id)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _json_error("knowledge relation already exists", 409)
    return jsonify({"relation": _relation_json(item)}), 201


@admin_api.post("/admin/knowledge/relations/<relation_id>/publish")
@login_required
@teacher_required
@csrf_required
def publish_knowledge_relation(db, relation_id):
    item = db.get(KnowledgeRelation, relation_id)
    if not item:
        return _json_error("knowledge relation not found", 404)
    body = request.get_json(silent=True) or {}
    if body.get("version") is not None and body.get("version") != item.version:
        return jsonify({"error": "version conflict", "current_version": item.version}), 409
    if not db.get(PublishedKnowledgeNode, item.source_node_id) or not db.get(
        PublishedKnowledgeNode, item.target_node_id
    ):
        return _json_error("publish both relation nodes first", 409)
    item.status = "published"
    item.published_by = request.current_user.id
    item.published_at = utcnow()
    item.updated_by = request.current_user.id
    snapshot = db.get(PublishedKnowledgeRelation, item.id)
    if not snapshot:
        snapshot = PublishedKnowledgeRelation(relation_id=item.id)
        db.add(snapshot)
    snapshot.source_node_id = item.source_node_id
    snapshot.target_node_id = item.target_node_id
    snapshot.relation_type = item.relation_type
    snapshot.weight = item.weight
    snapshot.version = item.version
    snapshot.published_by = request.current_user.id
    snapshot.published_at = item.published_at
    _audit(db, request.current_user, "knowledge_relation.publish", "knowledge_relation", item.id)
    db.commit()
    return jsonify({"relation": _relation_json(item)})


@admin_api.patch("/admin/knowledge/relations/<relation_id>")
@login_required
@teacher_required
@csrf_required
def update_knowledge_relation(db, relation_id):
    item = db.get(KnowledgeRelation, relation_id)
    if not item:
        return _json_error("knowledge relation not found", 404)
    if item.status == "archived":
        return _json_error("archived relations cannot be edited", 409)
    body = request.get_json(silent=True) or {}
    if body.get("version") != item.version:
        return jsonify({"error": "version conflict", "current_version": item.version}), 409

    source = (
        _resolve_knowledge_node(db, str(body["source_node_id"]))
        if "source_node_id" in body
        else db.get(KnowledgeNode, item.source_node_id)
    )
    target = (
        _resolve_knowledge_node(db, str(body["target_node_id"]))
        if "target_node_id" in body
        else db.get(KnowledgeNode, item.target_node_id)
    )
    relation_type = str(body.get("relation_type", item.relation_type)).strip()
    weight = body.get("weight", item.weight)
    if not source or not target:
        return _json_error("source or target node not found", 404)
    if source.id == target.id:
        return _json_error("a node cannot relate to itself", 409)
    if relation_type not in KNOWLEDGE_RELATION_TYPES:
        return _json_error("invalid relation type", 400)
    if not isinstance(weight, int) or weight < 1 or weight > 100:
        return _json_error("weight must be between 1 and 100", 400)

    item.source_node_id = source.id
    item.target_node_id = target.id
    item.relation_type = relation_type
    item.weight = weight
    item.version += 1
    item.status = "draft"
    item.updated_by = request.current_user.id
    _audit(
        db,
        request.current_user,
        "knowledge_relation.update",
        "knowledge_relation",
        item.id,
        {"version": item.version},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _json_error("knowledge relation already exists", 409)
    return jsonify({"relation": _relation_json(item)})


@admin_api.post("/admin/knowledge/relations/<relation_id>/archive")
@login_required
@teacher_required
@csrf_required
def archive_knowledge_relation(db, relation_id):
    item = db.get(KnowledgeRelation, relation_id)
    if not item:
        return _json_error("knowledge relation not found", 404)
    body = request.get_json(silent=True) or {}
    if body.get("version") != item.version:
        return jsonify({"error": "version conflict", "current_version": item.version}), 409
    item.status = "archived"
    item.version += 1
    item.updated_by = request.current_user.id
    snapshot = db.get(PublishedKnowledgeRelation, item.id)
    if snapshot:
        db.delete(snapshot)
    _audit(db, request.current_user, "knowledge_relation.archive", "knowledge_relation", item.id)
    db.commit()
    return jsonify({"relation": _relation_json(item)})


@admin_api.get("/admin/knowledge")
@login_required
@teacher_required
def admin_knowledge_list(db):
    rows = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.node_id)).all()
    return jsonify({"items": [_knowledge_json(row) for row in rows]})


@admin_api.put("/admin/knowledge/<node_id>")
@login_required
@teacher_required
@csrf_required
def save_knowledge(db, node_id):
    payload, error = _valid_knowledge_payload(request.get_json(silent=True) or {})
    if error:
        return _json_error(error, 400)
    node = _resolve_knowledge_node(db, node_id)
    if not node or node.status in {"archived", "merged"}:
        return _json_error("knowledge node not found", 404)
    item = _knowledge_document_for_node(db, node)
    if not item:
        item = KnowledgeDocument(
            node_id=node.code,
            knowledge_node_id=node.id,
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
        item.node_id = node.code
        item.knowledge_node_id = node.id
        item.payload = payload
        item.version += 1
        item.status = "draft"
        item.updated_by = request.current_user.id
    _audit(db, request.current_user, "knowledge.save", "knowledge", node.id, {"version": item.version})
    db.commit()
    return jsonify({"knowledge": _knowledge_json(item)})


@admin_api.post("/admin/knowledge/<node_id>/submit")
@login_required
@teacher_required
@csrf_required
def submit_knowledge(db, node_id):
    node = _resolve_knowledge_node(db, node_id)
    item = _knowledge_document_for_node(db, node) if node else None
    if not item:
        return _json_error("knowledge document not found", 404)
    if item.status not in {"draft", "rejected"}:
        return _json_error("only draft or rejected documents can be submitted", 409)
    item.status = "pending_review"
    item.updated_by = request.current_user.id
    _audit(db, request.current_user, "knowledge.submit", "knowledge", node.id)
    db.commit()
    return jsonify({"knowledge": _knowledge_json(item)})


@admin_api.post("/admin/knowledge/<node_id>/publish")
@login_required
@teacher_required
@csrf_required
def publish_knowledge(db, node_id):
    node = _resolve_knowledge_node(db, node_id)
    item = _knowledge_document_for_node(db, node) if node else None
    if not item:
        return _json_error("knowledge document not found", 404)
    if item.status not in {"pending_review", "draft"}:
        return _json_error("only draft or pending documents can be published", 409)
    item.status = "published"
    item.published_by = request.current_user.id
    item.published_at = utcnow()
    item.updated_by = request.current_user.id
    snapshot = db.scalar(
        select(PublishedKnowledge).where(
            or_(
                PublishedKnowledge.knowledge_node_id == node.id,
                PublishedKnowledge.node_id == node.code,
            )
        )
    )
    if not snapshot:
        snapshot = PublishedKnowledge(node_id=node.code, knowledge_node_id=node.id)
        db.add(snapshot)
    snapshot.node_id = node.code
    snapshot.knowledge_node_id = node.id
    snapshot.title = item.title
    snapshot.version = item.version
    snapshot.payload = item.payload
    snapshot.published_by = request.current_user.id
    snapshot.published_at = item.published_at
    _audit(db, request.current_user, "knowledge.publish", "knowledge", node.id, {"version": item.version})
    db.commit()
    return jsonify({"knowledge": _knowledge_json(item)})


def _question_content_hash(data):
    canonical = {
        "stem": " ".join(data["stem"].split()),
        "options": data["options"],
        "answer": " ".join(data["answer"].split()),
    }
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_question_data(value):
    if not isinstance(value, dict):
        return None, "question payload must be an object"
    try:
        module = _short_text(value.get("module"), 20, "module").upper() or "FUNC"
        if module not in QUESTION_MODULES:
            raise ValueError("invalid question module")
        question_type = (
            _short_text(
                value.get("question_type") or value.get("type"),
                20,
                "question type",
            )
            or "solve"
        )
        if question_type not in QUESTION_TYPES:
            raise ValueError("invalid question type")
        difficulty = int(value.get("difficulty", 3))
        if difficulty < 1 or difficulty > 5:
            raise ValueError("difficulty must be between 1 and 5")
        stem = _short_text(value.get("stem"), 40000, "stem", required=True)
        answer = _short_text(value.get("answer"), 40000, "answer", required=True)
        analysis = _short_text(value.get("analysis"), 60000, "analysis")

        raw_options = value.get("options", [])
        if raw_options is None:
            raw_options = []
        if not isinstance(raw_options, list) or len(raw_options) > 8:
            raise ValueError("options must be an array with at most 8 items")
        options = []
        for index, item in enumerate(raw_options):
            if isinstance(item, dict):
                label = _short_text(item.get("label"), 20, "option label") or chr(65 + index)
                content = _short_text(
                    item.get("content"), 6000, "option content", required=True
                )
            else:
                label = chr(65 + index)
                content = _short_text(item, 6000, "option content", required=True)
            options.append({"label": label, "content": content})
        if question_type == "choice" and len(options) < 2:
            raise ValueError("choice questions require at least two options")

        raw_tags = value.get("tags", [])
        if raw_tags is None:
            raw_tags = []
        if not isinstance(raw_tags, list) or len(raw_tags) > 30:
            raise ValueError("tags must be an array with at most 30 items")
        tags = []
        for item in raw_tags:
            tag = _short_text(item, 100, "tag")
            if tag and tag not in tags:
                tags.append(tag)

        source = value.get("source") or {}
        if not isinstance(source, dict):
            raise ValueError("source must be an object")
        if len(json.dumps(source, ensure_ascii=False)) > 64 * 1024:
            raise ValueError("source exceeds 64 KB")

        raw_knowledge_refs = value.get("knowledge_node_ids")
        if raw_knowledge_refs is None:
            raw_knowledge_refs = value.get("knowledge_points", [])
        if not isinstance(raw_knowledge_refs, list) or len(raw_knowledge_refs) > 40:
            raise ValueError("knowledge_node_ids must be an array with at most 40 items")
        knowledge_refs = []
        for item in raw_knowledge_refs:
            node_ref = _short_text(item, 80, "knowledge node id")
            if node_ref and node_ref not in knowledge_refs:
                knowledge_refs.append(node_ref)
    except (TypeError, ValueError) as exc:
        return None, str(exc)

    return (
        {
            "module": module,
            "question_type": question_type,
            "difficulty": difficulty,
            "stem": stem,
            "options": options,
            "answer": answer,
            "analysis": analysis,
            "tags": tags,
            "source": source,
            "knowledge_refs": knowledge_refs,
        },
        None,
    )


def _question_knowledge_nodes(db, refs):
    nodes = []
    for node_ref in refs:
        node = _resolve_knowledge_node(db, node_ref)
        if not node or node.status in {"archived", "merged"}:
            return None, f"knowledge node not found: {node_ref}"
        if node.id not in {item.id for item in nodes}:
            nodes.append(node)
    return nodes, None


def _question_link_node_ids(db, question_id, published=False):
    model = PublishedQuestionKnowledgeLink if published else QuestionKnowledgeLink
    return list(
        db.scalars(
            select(model.knowledge_node_id)
            .where(model.question_id == question_id)
            .order_by(model.sort_order, model.knowledge_node_id)
        ).all()
    )


def _question_snapshot(question, knowledge_node_ids):
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
        "knowledge_node_ids": list(knowledge_node_ids),
    }


def _question_json(db, question, include_content=True):
    node_ids = _question_link_node_ids(db, question.id)
    payload = {
        "id": question.id,
        "code": question.code,
        "owner_id": question.owner_id,
        "module": question.module,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "status": question.status,
        "redirect_to_id": question.redirect_to_id,
        "version": question.version,
        "knowledge_node_ids": node_ids,
        "source_review_id": question.source_review_id,
        "created_at": question.created_at.isoformat(),
        "updated_at": question.updated_at.isoformat(),
        "published_at": question.published_at.isoformat() if question.published_at else None,
    }
    if include_content:
        payload.update(
            {
                "stem": question.stem,
                "options": question.options_json or [],
                "answer": question.answer,
                "analysis": question.analysis,
                "tags": question.tags_json or [],
                "source": question.source_json or {},
            }
        )
    return payload


def _published_question_json(db, question, include_answers=True):
    node_ids = _question_link_node_ids(db, question.question_id, published=True)
    nodes = []
    if node_ids:
        rows = db.scalars(
            select(KnowledgeNode).where(KnowledgeNode.id.in_(node_ids))
        ).all()
        by_id = {row.id: row for row in rows}
        nodes = [
            {"id": node_id, "code": by_id[node_id].code, "title": by_id[node_id].title}
            for node_id in node_ids
            if node_id in by_id
        ]
    source = question.source_json or {}
    public_source_keys = {"type", "year", "region", "page_number"}
    visible_source = (
        source
        if include_answers
        else {key: value for key, value in source.items() if key in public_source_keys}
    )
    payload = {
        "id": question.question_id,
        "code": question.code,
        "module": question.module,
        "question_type": question.question_type,
        "type": question.question_type,
        "difficulty": question.difficulty,
        "stem": question.stem,
        "options": question.options_json or [],
        "tags": question.tags_json or [],
        "source": visible_source,
        "knowledge_node_ids": node_ids,
        "knowledge_nodes": nodes,
        "version": question.version,
        "published_at": question.published_at.isoformat(),
    }
    if include_answers:
        payload["answer"] = question.answer
        payload["analysis"] = question.analysis
    return payload


def _resolve_question(db, question_ref, follow_redirect=True):
    question = db.scalar(
        select(Question).where(
            or_(Question.id == question_ref, Question.code == str(question_ref).upper())
        )
    )
    visited = set()
    while question and follow_redirect and question.redirect_to_id:
        if question.id in visited:
            return None
        visited.add(question.id)
        question = db.get(Question, question.redirect_to_id)
    return question


def _question_for_user(db, question_ref, editable=False):
    question = _resolve_question(db, question_ref, follow_redirect=not editable)
    if not question:
        return None
    if request.current_user.role == "admin":
        return question
    if question.owner_id == request.current_user.id:
        return question
    if not editable and question.status == "published":
        return question
    return None


def _next_question_code(db):
    while True:
        question_id = new_id("qst")
        code = f"Q-{question_id[-10:].upper()}"
        if not db.scalar(select(Question).where(Question.code == code)):
            return question_id, code


def _replace_question_links(db, question, nodes, actor_id):
    db.execute(delete(QuestionKnowledgeLink).where(QuestionKnowledgeLink.question_id == question.id))
    for index, node in enumerate(nodes):
        db.add(
            QuestionKnowledgeLink(
                question_id=question.id,
                knowledge_node_id=node.id,
                relation_type="primary" if index == 0 else "related",
                sort_order=index,
                created_by=actor_id,
            )
        )


def _add_question_version(db, question, actor_id, reason, node_ids=None):
    if node_ids is None:
        node_ids = _question_link_node_ids(db, question.id)
    db.add(
        QuestionVersion(
            question_id=question.id,
            version=question.version,
            snapshot=_question_snapshot(question, node_ids),
            change_reason=reason[:240],
            created_by=actor_id,
        )
    )


def _publish_question_snapshot(db, question, actor_id):
    now = utcnow()
    snapshot = db.get(PublishedQuestion, question.id)
    if not snapshot:
        snapshot = PublishedQuestion(question_id=question.id)
        db.add(snapshot)
    snapshot.code = question.code
    snapshot.module = question.module
    snapshot.question_type = question.question_type
    snapshot.difficulty = question.difficulty
    snapshot.stem = question.stem
    snapshot.options_json = question.options_json or []
    snapshot.answer = question.answer
    snapshot.analysis = question.analysis
    snapshot.tags_json = question.tags_json or []
    snapshot.source_json = question.source_json or {}
    snapshot.version = question.version
    snapshot.published_by = actor_id
    snapshot.published_at = now
    db.execute(
        delete(PublishedQuestionKnowledgeLink).where(
            PublishedQuestionKnowledgeLink.question_id == question.id
        )
    )
    # 会话关闭了 autoflush；AI 审核入库与首次发布可能在同一事务内，
    # 先落当前知识关联，再生成对应的发布关联快照。
    db.flush()
    links = db.scalars(
        select(QuestionKnowledgeLink)
        .where(QuestionKnowledgeLink.question_id == question.id)
        .order_by(QuestionKnowledgeLink.sort_order)
    ).all()
    for link in links:
        db.add(
            PublishedQuestionKnowledgeLink(
                question_id=question.id,
                knowledge_node_id=link.knowledge_node_id,
                relation_type=link.relation_type,
                sort_order=link.sort_order,
            )
        )
    question.status = "published"
    question.published_by = actor_id
    question.published_at = now
    question.updated_by = actor_id
    return snapshot


@admin_api.get("/admin/questions")
@login_required
@teacher_required
def admin_questions(db):
    query = select(Question)
    if request.current_user.role != "admin":
        query = query.where(
            or_(
                Question.owner_id == request.current_user.id,
                Question.status == "published",
            )
        )
    status = str(request.args.get("status", "")).strip()
    module = str(request.args.get("module", "")).strip().upper()
    question_type = str(request.args.get("question_type", "")).strip()
    knowledge_ref = str(request.args.get("knowledge_node_id", "")).strip()
    search = str(request.args.get("query", "")).strip()
    try:
        difficulty = int(request.args["difficulty"]) if request.args.get("difficulty") else None
        limit = min(200, max(1, int(request.args.get("limit", 100))))
    except ValueError:
        return _json_error("invalid numeric filter", 400)
    if status:
        query = query.where(Question.status == status)
    if module:
        query = query.where(Question.module == module)
    if question_type:
        query = query.where(Question.question_type == question_type)
    if difficulty:
        query = query.where(Question.difficulty == difficulty)
    if knowledge_ref:
        node = _resolve_knowledge_node(db, knowledge_ref)
        if not node:
            return _json_error("knowledge node not found", 404)
        query = query.join(
            QuestionKnowledgeLink,
            QuestionKnowledgeLink.question_id == Question.id,
        ).where(QuestionKnowledgeLink.knowledge_node_id == node.id)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Question.code.ilike(pattern), Question.stem.ilike(pattern)))
    rows = db.scalars(query.order_by(Question.updated_at.desc()).limit(limit)).all()
    return jsonify({"items": [_question_json(db, row) for row in rows]})


@admin_api.post("/admin/questions")
@login_required
@teacher_required
@csrf_required
def create_question(db):
    body = request.get_json(silent=True) or {}
    data, error = _valid_question_data(body)
    if error:
        return _json_error(error, 400)
    nodes, error = _question_knowledge_nodes(db, data["knowledge_refs"])
    if error:
        return _json_error(error, 400)
    content_hash = _question_content_hash(data)
    duplicate = db.scalar(
        select(Question).where(
            Question.content_hash == content_hash,
            Question.status.notin_({"archived", "merged"}),
        )
    )
    if duplicate:
        return jsonify({"error": "duplicate question", "duplicate_id": duplicate.id}), 409

    question_id, generated_code = _next_question_code(db)
    requested_code = str(body.get("code", "")).strip().upper()
    code = requested_code or generated_code
    if not QUESTION_CODE_PATTERN.fullmatch(code):
        return _json_error("invalid question code", 400)
    if db.scalar(select(Question).where(Question.code == code)):
        return _json_error("question code already exists", 409)
    question = Question(
        id=question_id,
        code=code,
        owner_id=request.current_user.id,
        module=data["module"],
        question_type=data["question_type"],
        difficulty=data["difficulty"],
        stem=data["stem"],
        options_json=data["options"],
        answer=data["answer"],
        analysis=data["analysis"],
        tags_json=data["tags"],
        source_json=data["source"],
        content_hash=content_hash,
        status="draft",
        version=1,
        created_by=request.current_user.id,
        updated_by=request.current_user.id,
    )
    db.add(question)
    db.flush()
    _replace_question_links(db, question, nodes, request.current_user.id)
    _add_question_version(
        db,
        question,
        request.current_user.id,
        "创建题目",
        [node.id for node in nodes],
    )
    _audit(db, request.current_user, "question.create", "question", question.id)
    db.commit()
    return jsonify({"question": _question_json(db, question)}), 201


@admin_api.get("/admin/questions/<question_ref>")
@login_required
@teacher_required
def question_detail(db, question_ref):
    question = _question_for_user(db, question_ref)
    if not question:
        return _json_error("question not found", 404)
    return jsonify({"question": _question_json(db, question)})


@admin_api.patch("/admin/questions/<question_ref>")
@login_required
@teacher_required
@csrf_required
def update_question(db, question_ref):
    question = _question_for_user(db, question_ref, editable=True)
    if not question:
        return _json_error("question not found", 404)
    if question.status in {"archived", "merged"}:
        return _json_error("archived or merged questions cannot be edited", 409)
    if question.status == "pending_review":
        return _json_error("pending questions must be published or returned before editing", 409)
    body = request.get_json(silent=True) or {}
    if not isinstance(body.get("version"), int):
        return _json_error("version is required", 400)
    if body["version"] != question.version:
        return jsonify({"error": "version conflict", "current_version": question.version}), 409
    current_node_ids = _question_link_node_ids(db, question.id)
    merged = {
        "module": body.get("module", question.module),
        "question_type": body.get("question_type", question.question_type),
        "difficulty": body.get("difficulty", question.difficulty),
        "stem": body.get("stem", question.stem),
        "options": body.get("options", question.options_json or []),
        "answer": body.get("answer", question.answer),
        "analysis": body.get("analysis", question.analysis),
        "tags": body.get("tags", question.tags_json or []),
        "source": body.get("source", question.source_json or {}),
        "knowledge_node_ids": body.get("knowledge_node_ids", current_node_ids),
    }
    data, error = _valid_question_data(merged)
    if error:
        return _json_error(error, 400)
    nodes, error = _question_knowledge_nodes(db, data["knowledge_refs"])
    if error:
        return _json_error(error, 400)
    content_hash = _question_content_hash(data)
    duplicate = db.scalar(
        select(Question).where(
            Question.content_hash == content_hash,
            Question.id != question.id,
            Question.status.notin_({"archived", "merged"}),
        )
    )
    if duplicate:
        return jsonify({"error": "duplicate question", "duplicate_id": duplicate.id}), 409

    question.module = data["module"]
    question.question_type = data["question_type"]
    question.difficulty = data["difficulty"]
    question.stem = data["stem"]
    question.options_json = data["options"]
    question.answer = data["answer"]
    question.analysis = data["analysis"]
    question.tags_json = data["tags"]
    question.source_json = data["source"]
    question.content_hash = content_hash
    question.version += 1
    question.status = "draft"
    question.updated_by = request.current_user.id
    _replace_question_links(db, question, nodes, request.current_user.id)
    _add_question_version(
        db,
        question,
        request.current_user.id,
        str(body.get("change_reason", "保存题目草稿")).strip() or "保存题目草稿",
        [node.id for node in nodes],
    )
    _audit(
        db,
        request.current_user,
        "question.update",
        "question",
        question.id,
        {"version": question.version},
    )
    db.commit()
    return jsonify({"question": _question_json(db, question)})


@admin_api.post("/admin/questions/<question_ref>/submit")
@login_required
@teacher_required
@csrf_required
def submit_question(db, question_ref):
    question = _question_for_user(db, question_ref, editable=True)
    if not question:
        return _json_error("question not found", 404)
    if question.status != "draft":
        return _json_error("only draft questions can be submitted", 409)
    question.status = "pending_review"
    question.updated_by = request.current_user.id
    _audit(db, request.current_user, "question.submit", "question", question.id)
    db.commit()
    return jsonify({"question": _question_json(db, question)})


@admin_api.post("/admin/questions/<question_ref>/publish")
@login_required
@teacher_required
@csrf_required
def publish_question(db, question_ref):
    question = _question_for_user(db, question_ref, editable=True)
    if not question:
        return _json_error("question not found", 404)
    if question.status not in {"draft", "pending_review", "published"}:
        return _json_error("question cannot be published from its current status", 409)
    _publish_question_snapshot(db, question, request.current_user.id)
    _audit(
        db,
        request.current_user,
        "question.publish",
        "question",
        question.id,
        {"version": question.version},
    )
    db.commit()
    return jsonify({"question": _question_json(db, question)})


@admin_api.post("/admin/questions/<question_ref>/archive")
@login_required
@teacher_required
@csrf_required
def archive_question(db, question_ref):
    question = _question_for_user(db, question_ref, editable=True)
    if not question:
        return _json_error("question not found", 404)
    if question.status == "merged":
        return _json_error("merged question cannot be archived", 409)
    db.execute(
        delete(PublishedQuestionKnowledgeLink).where(
            PublishedQuestionKnowledgeLink.question_id == question.id
        )
    )
    snapshot = db.get(PublishedQuestion, question.id)
    if snapshot:
        db.delete(snapshot)
    question.status = "archived"
    question.updated_by = request.current_user.id
    _audit(db, request.current_user, "question.archive", "question", question.id)
    db.commit()
    return jsonify({"question": _question_json(db, question)})


@admin_api.post("/admin/questions/<question_ref>/merge")
@login_required
@admin_required
@csrf_required
def merge_question(db, question_ref):
    source = _resolve_question(db, question_ref, follow_redirect=False)
    body = request.get_json(silent=True) or {}
    target = _resolve_question(db, str(body.get("target_id", "")))
    if not source or not target:
        return _json_error("question not found", 404)
    if source.id == target.id:
        return _json_error("question cannot be merged into itself", 409)
    if source.status == "merged" or target.status in {"archived", "merged"}:
        return _json_error("invalid question merge target", 409)
    db.execute(
        delete(PublishedQuestionKnowledgeLink).where(
            PublishedQuestionKnowledgeLink.question_id == source.id
        )
    )
    source_snapshot = db.get(PublishedQuestion, source.id)
    if source_snapshot:
        db.delete(source_snapshot)
    source.status = "merged"
    source.redirect_to_id = target.id
    source.updated_by = request.current_user.id
    _audit(
        db,
        request.current_user,
        "question.merge",
        "question",
        source.id,
        {"target_id": target.id},
    )
    db.commit()
    return jsonify({"question": _question_json(db, source)})


@admin_api.get("/admin/questions/<question_ref>/versions")
@login_required
@teacher_required
def question_versions(db, question_ref):
    question = _question_for_user(db, question_ref)
    if not question:
        return _json_error("question not found", 404)
    rows = db.scalars(
        select(QuestionVersion)
        .where(QuestionVersion.question_id == question.id)
        .order_by(QuestionVersion.version.desc())
    ).all()
    return jsonify(
        {
            "items": [
                {
                    "version": row.version,
                    "change_reason": row.change_reason,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


@admin_api.post("/admin/questions/<question_ref>/rollback")
@login_required
@teacher_required
@csrf_required
def rollback_question(db, question_ref):
    question = _question_for_user(db, question_ref, editable=True)
    if not question:
        return _json_error("question not found", 404)
    body = request.get_json(silent=True) or {}
    try:
        target_version = int(body.get("version"))
    except (TypeError, ValueError):
        return _json_error("version is required", 400)
    historical = db.scalar(
        select(QuestionVersion).where(
            QuestionVersion.question_id == question.id,
            QuestionVersion.version == target_version,
        )
    )
    if not historical:
        return _json_error("question version not found", 404)
    data, error = _valid_question_data(historical.snapshot)
    if error:
        return _json_error("stored question version is invalid", 500)
    nodes, error = _question_knowledge_nodes(db, data["knowledge_refs"])
    if error:
        return _json_error(error, 409)
    question.module = data["module"]
    question.question_type = data["question_type"]
    question.difficulty = data["difficulty"]
    question.stem = data["stem"]
    question.options_json = data["options"]
    question.answer = data["answer"]
    question.analysis = data["analysis"]
    question.tags_json = data["tags"]
    question.source_json = data["source"]
    question.content_hash = _question_content_hash(data)
    question.version += 1
    question.status = "draft"
    question.updated_by = request.current_user.id
    _replace_question_links(db, question, nodes, request.current_user.id)
    _add_question_version(
        db,
        question,
        request.current_user.id,
        f"回滚到版本 {target_version}",
        [node.id for node in nodes],
    )
    _audit(
        db,
        request.current_user,
        "question.rollback",
        "question",
        question.id,
        {"from_version": target_version, "new_version": question.version},
    )
    db.commit()
    return jsonify({"question": _question_json(db, question)})


@admin_api.get("/admin/question-picker")
@login_required
@teacher_required
def question_picker(db):
    query = select(PublishedQuestion)
    search = str(request.args.get("query", "")).strip()
    module = str(request.args.get("module", "")).strip().upper()
    question_type = str(request.args.get("question_type", "")).strip()
    knowledge_ref = str(request.args.get("knowledge_node_id", "")).strip()
    try:
        difficulty = int(request.args["difficulty"]) if request.args.get("difficulty") else None
        limit = min(100, max(1, int(request.args.get("limit", 30))))
    except ValueError:
        return _json_error("invalid numeric filter", 400)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(PublishedQuestion.code.ilike(pattern), PublishedQuestion.stem.ilike(pattern))
        )
    if module:
        query = query.where(PublishedQuestion.module == module)
    if question_type:
        query = query.where(PublishedQuestion.question_type == question_type)
    if difficulty:
        query = query.where(PublishedQuestion.difficulty == difficulty)
    if knowledge_ref:
        node = _resolve_knowledge_node(db, knowledge_ref)
        if not node:
            return _json_error("knowledge node not found", 404)
        query = query.join(
            PublishedQuestionKnowledgeLink,
            PublishedQuestionKnowledgeLink.question_id == PublishedQuestion.question_id,
        ).where(PublishedQuestionKnowledgeLink.knowledge_node_id == node.id)
    rows = db.scalars(
        query.order_by(PublishedQuestion.published_at.desc()).limit(limit)
    ).all()
    return jsonify({"items": [_published_question_json(db, row) for row in rows]})


def _course_for_user(db, course_id):
    course = db.get(LectureCourse, course_id)
    if not course:
        return None
    if request.current_user.role != "admin" and course.owner_id != request.current_user.id:
        return None
    return course


def _lecture_for_user(db, lecture_id):
    lecture = db.get(Lecture, lecture_id)
    if not lecture:
        return None
    if request.current_user.role != "admin" and lecture.owner_id != request.current_user.id:
        return None
    return lecture


def _course_json(course, lecture_count=None):
    payload = {
        "id": course.id,
        "owner_id": course.owner_id,
        "title": course.title,
        "grade_label": course.grade_label,
        "description": course.description,
        "status": course.status,
        "sort_order": course.sort_order,
        "created_at": course.created_at.isoformat(),
        "updated_at": course.updated_at.isoformat(),
    }
    if lecture_count is not None:
        payload["lecture_count"] = lecture_count
    return payload


def _lecture_json(lecture, course=None, include_payload=True):
    payload = {
        "id": lecture.id,
        "course_id": lecture.course_id,
        "owner_id": lecture.owner_id,
        "title": lecture.title,
        "slug": lecture.slug,
        "summary": lecture.summary,
        "status": lecture.status,
        "sort_order": lecture.sort_order,
        "version": lecture.version,
        "created_at": lecture.created_at.isoformat(),
        "updated_at": lecture.updated_at.isoformat(),
        "published_at": lecture.published_at.isoformat() if lecture.published_at else None,
    }
    if include_payload:
        payload["payload"] = lecture.payload
    if course:
        payload["course"] = _course_json(course)
    return payload


def _published_lecture_json(item, include_payload=True):
    payload = {
        "id": item.lecture_id,
        "course_id": item.course_id,
        "course_title": item.course_title,
        "course_grade_label": item.course_grade_label,
        "title": item.title,
        "slug": item.slug,
        "summary": item.summary,
        "sort_order": item.sort_order,
        "version": item.version,
        "published_at": item.published_at.isoformat(),
    }
    if include_payload:
        payload["payload"] = item.payload
    return payload


def _short_text(value, limit, field, required=False):
    text_value = str(value or "").strip()
    if required and not text_value:
        raise ValueError(f"{field} is required")
    if len(text_value) > limit:
        raise ValueError(f"{field} is too long")
    return text_value


def _valid_lecture_payload(value):
    if not isinstance(value, dict):
        return None, "lecture payload must be an object"
    sections = value.get("sections")
    if not isinstance(sections, list) or not sections:
        return None, "lecture must contain at least one section"
    if len(sections) > 80:
        return None, "lecture contains too many sections"

    normalized_sections = []
    block_count = 0
    used_ids = set()
    try:
        for section_index, section in enumerate(sections):
            if not isinstance(section, dict):
                raise ValueError("section must be an object")
            section_id = _short_text(section.get("id"), 80, "section id") or new_id("sec")
            if section_id in used_ids:
                raise ValueError("section and block ids must be unique")
            used_ids.add(section_id)
            title = _short_text(section.get("title"), 180, "section title", required=True)
            blocks = section.get("blocks", [])
            if not isinstance(blocks, list):
                raise ValueError("section blocks must be an array")
            normalized_blocks = []
            for block in blocks:
                if not isinstance(block, dict):
                    raise ValueError("block must be an object")
                block_count += 1
                if block_count > 500:
                    raise ValueError("lecture contains too many blocks")
                block_id = _short_text(block.get("id"), 80, "block id") or new_id("blk")
                if block_id in used_ids:
                    raise ValueError("section and block ids must be unique")
                used_ids.add(block_id)
                block_type = _short_text(block.get("type"), 32, "block type", required=True)
                if block_type not in LECTURE_BLOCK_TYPES:
                    raise ValueError("unsupported lecture block type")
                normalized = {"id": block_id, "type": block_type}
                if block_type == "text":
                    normalized["text"] = _short_text(block.get("text"), 20000, "text")
                elif block_type == "math":
                    normalized["latex"] = _short_text(
                        block.get("latex"), 10000, "latex", required=True
                    )
                    normalized["caption"] = _short_text(block.get("caption"), 500, "caption")
                elif block_type == "callout":
                    normalized["title"] = _short_text(block.get("title"), 200, "callout title")
                    normalized["text"] = _short_text(block.get("text"), 12000, "callout text")
                    tone = _short_text(block.get("tone"), 20, "callout tone") or "note"
                    normalized["tone"] = tone if tone in {"note", "key", "warning"} else "note"
                elif block_type == "example":
                    normalized["title"] = _short_text(block.get("title"), 200, "example title")
                    normalized["stem"] = _short_text(block.get("stem"), 12000, "example stem")
                    normalized["answer"] = _short_text(block.get("answer"), 12000, "example answer")
                elif block_type == "question_ref":
                    normalized["question_id"] = _short_text(
                        block.get("question_id"), 80, "question id"
                    )
                    normalized["code"] = _short_text(block.get("code"), 80, "question code")
                    normalized["title"] = _short_text(block.get("title"), 200, "question title")
                    normalized["stem"] = _short_text(block.get("stem"), 12000, "question stem")
                    raw_options = block.get("options", [])
                    if not isinstance(raw_options, list) or len(raw_options) > 8:
                        raise ValueError("question reference options must be an array")
                    normalized_options = []
                    for option_index, option in enumerate(raw_options):
                        if isinstance(option, dict):
                            label = (
                                _short_text(option.get("label"), 20, "option label")
                                or chr(65 + option_index)
                            )
                            content = _short_text(
                                option.get("content"), 6000, "option content"
                            )
                        else:
                            label = chr(65 + option_index)
                            content = _short_text(option, 6000, "option content")
                        if content:
                            normalized_options.append({"label": label, "content": content})
                    normalized["options"] = normalized_options
                    normalized["answer"] = _short_text(
                        block.get("answer"), 12000, "question answer"
                    )
                    normalized["analysis"] = _short_text(
                        block.get("analysis"), 20000, "question analysis"
                    )
                    normalized["question_type"] = _short_text(
                        block.get("question_type"), 20, "question type"
                    )
                    try:
                        normalized["difficulty"] = min(
                            5, max(1, int(block.get("difficulty", 3)))
                        )
                    except (TypeError, ValueError):
                        normalized["difficulty"] = 3
                elif block_type == "knowledge_ref":
                    normalized["node_id"] = _short_text(
                        block.get("node_id"), 80, "knowledge node id"
                    )
                    normalized["title"] = _short_text(block.get("title"), 200, "knowledge title")
                    normalized["note"] = _short_text(block.get("note"), 6000, "knowledge note")
                elif block_type == "image":
                    url = _short_text(block.get("url"), 2048, "image url", required=True)
                    if not (
                        url.startswith("https://")
                        or (not url.startswith(("//", "\\")) and ":" not in url.split("/")[0])
                    ):
                        raise ValueError("image url must use HTTPS or a relative path")
                    normalized["url"] = url
                    normalized["alt"] = _short_text(block.get("alt"), 300, "image alt")
                    normalized["caption"] = _short_text(block.get("caption"), 500, "image caption")
                normalized_blocks.append(normalized)
            normalized_sections.append(
                {
                    "id": section_id,
                    "title": title,
                    "sort_order": int(section.get("sort_order", section_index)),
                    "blocks": normalized_blocks,
                }
            )
    except (TypeError, ValueError) as exc:
        return None, str(exc)

    normalized_payload = {"sections": normalized_sections}
    if len(json.dumps(normalized_payload, ensure_ascii=False)) > 1024 * 1024:
        return None, "lecture payload exceeds 1 MB"
    return normalized_payload, None


def _freeze_lecture_question_refs(db, payload):
    """发布讲义时用当前题库快照补齐题目块，之后题目编辑不影响历史讲义。"""
    frozen = json.loads(json.dumps(payload, ensure_ascii=False))
    for section in frozen.get("sections", []):
        for block in section.get("blocks", []):
            if block.get("type") != "question_ref":
                continue
            question_ref = str(block.get("question_id") or block.get("code") or "").strip()
            if not question_ref:
                continue
            snapshot = db.scalar(
                select(PublishedQuestion).where(
                    or_(
                        PublishedQuestion.question_id == question_ref,
                        PublishedQuestion.code == question_ref.upper(),
                    )
                )
            )
            if not snapshot:
                return None, f"published question not found: {question_ref}"
            block.update(
                {
                    "question_id": snapshot.question_id,
                    "code": snapshot.code,
                    "title": block.get("title") or snapshot.code,
                    "stem": snapshot.stem,
                    "options": snapshot.options_json or [],
                    "answer": snapshot.answer,
                    "analysis": snapshot.analysis,
                    "question_type": snapshot.question_type,
                    "difficulty": snapshot.difficulty,
                }
            )
    return frozen, None


def _lecture_version_snapshot(lecture):
    return {
        "title": lecture.title,
        "slug": lecture.slug,
        "summary": lecture.summary,
        "sort_order": lecture.sort_order,
        "payload": lecture.payload,
    }


def _add_lecture_version(db, lecture, actor_id, reason):
    db.add(
        LectureVersion(
            lecture_id=lecture.id,
            version=lecture.version,
            snapshot=_lecture_version_snapshot(lecture),
            change_reason=reason,
            created_by=actor_id,
        )
    )


@admin_api.get("/admin/lecture-courses")
@login_required
@teacher_required
def lecture_courses_list(db):
    query = select(LectureCourse)
    if request.current_user.role != "admin":
        query = query.where(LectureCourse.owner_id == request.current_user.id)
    rows = db.scalars(
        query.order_by(LectureCourse.sort_order, LectureCourse.created_at)
    ).all()
    counts = dict(
        db.execute(
            select(Lecture.course_id, func.count(Lecture.id))
            .where(Lecture.course_id.in_([row.id for row in rows]))
            .group_by(Lecture.course_id)
        ).all()
    ) if rows else {}
    return jsonify({"items": [_course_json(row, counts.get(row.id, 0)) for row in rows]})


@admin_api.post("/admin/lecture-courses")
@login_required
@teacher_required
@csrf_required
def create_lecture_course(db):
    body = request.get_json(silent=True) or {}
    try:
        title = _short_text(body.get("title"), 160, "course title", required=True)
        grade_label = _short_text(body.get("grade_label"), 80, "grade label")
        description = _short_text(body.get("description"), 4000, "description")
        sort_order = int(body.get("sort_order", 0))
    except (TypeError, ValueError) as exc:
        return _json_error(str(exc), 400)
    item = LectureCourse(
        owner_id=request.current_user.id,
        title=title,
        grade_label=grade_label,
        description=description,
        sort_order=sort_order,
    )
    db.add(item)
    db.flush()
    _audit(db, request.current_user, "lecture_course.create", "lecture_course", item.id)
    db.commit()
    return jsonify({"course": _course_json(item, 0)}), 201


@admin_api.patch("/admin/lecture-courses/<course_id>")
@login_required
@teacher_required
@csrf_required
def update_lecture_course(db, course_id):
    item = _course_for_user(db, course_id)
    if not item:
        return _json_error("lecture course not found", 404)
    body = request.get_json(silent=True) or {}
    try:
        if "title" in body:
            item.title = _short_text(body.get("title"), 160, "course title", required=True)
        if "grade_label" in body:
            item.grade_label = _short_text(body.get("grade_label"), 80, "grade label")
        if "description" in body:
            item.description = _short_text(body.get("description"), 4000, "description")
        if "sort_order" in body:
            item.sort_order = int(body["sort_order"])
        if "status" in body:
            status = _short_text(body.get("status"), 24, "course status")
            if status not in {"active", "archived"}:
                raise ValueError("invalid course status")
            item.status = status
    except (TypeError, ValueError) as exc:
        return _json_error(str(exc), 400)
    _audit(db, request.current_user, "lecture_course.update", "lecture_course", item.id)
    db.commit()
    return jsonify({"course": _course_json(item)})


@admin_api.get("/admin/lectures")
@login_required
@teacher_required
def lectures_list(db):
    course_id = str(request.args.get("course_id", "")).strip()
    query = select(Lecture)
    if request.current_user.role != "admin":
        query = query.where(Lecture.owner_id == request.current_user.id)
    if course_id:
        if not _course_for_user(db, course_id):
            return _json_error("lecture course not found", 404)
        query = query.where(Lecture.course_id == course_id)
    rows = db.scalars(query.order_by(Lecture.sort_order, Lecture.created_at)).all()
    return jsonify({"items": [_lecture_json(row, include_payload=False) for row in rows]})


@admin_api.post("/admin/lectures")
@login_required
@teacher_required
@csrf_required
def create_lecture(db):
    body = request.get_json(silent=True) or {}
    course = _course_for_user(db, str(body.get("course_id", "")))
    if not course or course.status != "active":
        return _json_error("active lecture course not found", 404)
    try:
        title = _short_text(body.get("title"), 180, "lecture title", required=True)
        summary = _short_text(body.get("summary"), 4000, "summary")
        sort_order = int(body.get("sort_order", 0))
        requested_slug = _short_text(body.get("slug"), 100, "slug").lower()
    except (TypeError, ValueError) as exc:
        return _json_error(str(exc), 400)
    slug = requested_slug or f"lecture-{secrets.token_hex(5)}"
    if not LECTURE_SLUG_PATTERN.fullmatch(slug):
        return _json_error("slug must contain lowercase letters, numbers, and hyphens", 400)
    if db.scalar(select(Lecture).where(Lecture.slug == slug)):
        return _json_error("lecture slug already exists", 409)
    payload, error = _valid_lecture_payload(
        body.get(
            "payload",
            {
                "sections": [
                    {
                        "id": new_id("sec"),
                        "title": "第一部分",
                        "sort_order": 0,
                        "blocks": [],
                    }
                ]
            },
        )
    )
    if error:
        return _json_error(error, 400)
    item = Lecture(
        course_id=course.id,
        owner_id=course.owner_id,
        title=title,
        slug=slug,
        summary=summary,
        sort_order=sort_order,
        payload=payload,
        created_by=request.current_user.id,
        updated_by=request.current_user.id,
    )
    db.add(item)
    db.flush()
    _add_lecture_version(db, item, request.current_user.id, "创建讲义")
    _audit(db, request.current_user, "lecture.create", "lecture", item.id)
    db.commit()
    return jsonify({"lecture": _lecture_json(item, course)}), 201


@admin_api.get("/admin/lectures/<lecture_id>")
@login_required
@teacher_required
def lecture_detail(db, lecture_id):
    item = _lecture_for_user(db, lecture_id)
    if not item:
        return _json_error("lecture not found", 404)
    return jsonify({"lecture": _lecture_json(item, db.get(LectureCourse, item.course_id))})


@admin_api.put("/admin/lectures/<lecture_id>/draft")
@login_required
@teacher_required
@csrf_required
def save_lecture_draft(db, lecture_id):
    item = _lecture_for_user(db, lecture_id)
    if not item:
        return _json_error("lecture not found", 404)
    body = request.get_json(silent=True) or {}
    try:
        expected_version = int(body.get("version"))
    except (TypeError, ValueError):
        return _json_error("version is required", 400)
    if expected_version != item.version:
        return jsonify(
            {
                "error": "lecture version conflict",
                "current_version": item.version,
                "lecture": _lecture_json(item, db.get(LectureCourse, item.course_id)),
            }
        ), 409
    payload, error = _valid_lecture_payload(body.get("payload"))
    if error:
        return _json_error(error, 400)
    try:
        title = _short_text(body.get("title"), 180, "lecture title", required=True)
        summary = _short_text(body.get("summary"), 4000, "summary")
        sort_order = int(body.get("sort_order", item.sort_order))
    except (TypeError, ValueError) as exc:
        return _json_error(str(exc), 400)
    if item.status == "pending_review":
        return _json_error("pending lecture must be published or returned before editing", 409)
    item.title = title
    item.summary = summary
    item.sort_order = sort_order
    item.payload = payload
    item.version += 1
    item.status = "draft"
    item.updated_by = request.current_user.id
    _add_lecture_version(db, item, request.current_user.id, "保存讲义草稿")
    _audit(
        db,
        request.current_user,
        "lecture.save",
        "lecture",
        item.id,
        {"version": item.version},
    )
    db.commit()
    return jsonify({"lecture": _lecture_json(item, db.get(LectureCourse, item.course_id))})


@admin_api.post("/admin/lectures/<lecture_id>/submit")
@login_required
@teacher_required
@csrf_required
def submit_lecture(db, lecture_id):
    item = _lecture_for_user(db, lecture_id)
    if not item:
        return _json_error("lecture not found", 404)
    if item.status != "draft":
        return _json_error("only draft lectures can be submitted", 409)
    item.status = "pending_review"
    item.updated_by = request.current_user.id
    _audit(db, request.current_user, "lecture.submit", "lecture", item.id)
    db.commit()
    return jsonify({"lecture": _lecture_json(item, db.get(LectureCourse, item.course_id))})


@admin_api.post("/admin/lectures/<lecture_id>/publish")
@login_required
@teacher_required
@csrf_required
def publish_lecture(db, lecture_id):
    item = _lecture_for_user(db, lecture_id)
    if not item:
        return _json_error("lecture not found", 404)
    if item.status not in {"draft", "pending_review", "published"}:
        return _json_error("lecture cannot be published from its current status", 409)
    course = db.get(LectureCourse, item.course_id)
    if not course or course.status != "active":
        return _json_error("lecture course is archived", 409)
    frozen_payload, freeze_error = _freeze_lecture_question_refs(db, item.payload)
    if freeze_error:
        return _json_error(freeze_error, 409)
    now = utcnow()
    snapshot = db.get(PublishedLecture, item.id)
    if not snapshot:
        snapshot = PublishedLecture(lecture_id=item.id, course_id=course.id)
        db.add(snapshot)
    snapshot.course_id = course.id
    snapshot.course_title = course.title
    snapshot.course_grade_label = course.grade_label
    snapshot.title = item.title
    snapshot.slug = item.slug
    snapshot.summary = item.summary
    snapshot.sort_order = item.sort_order
    snapshot.version = item.version
    snapshot.payload = frozen_payload
    snapshot.published_by = request.current_user.id
    snapshot.published_at = now
    item.status = "published"
    item.published_by = request.current_user.id
    item.published_at = now
    item.updated_by = request.current_user.id
    _audit(
        db,
        request.current_user,
        "lecture.publish",
        "lecture",
        item.id,
        {"version": item.version},
    )
    db.commit()
    return jsonify({"lecture": _lecture_json(item, course)})


@admin_api.post("/admin/lectures/<lecture_id>/unpublish")
@login_required
@teacher_required
@csrf_required
def unpublish_lecture(db, lecture_id):
    item = _lecture_for_user(db, lecture_id)
    if not item:
        return _json_error("lecture not found", 404)
    snapshot = db.get(PublishedLecture, item.id)
    if snapshot:
        db.delete(snapshot)
    item.status = "draft"
    item.published_by = None
    item.published_at = None
    item.updated_by = request.current_user.id
    _audit(db, request.current_user, "lecture.unpublish", "lecture", item.id)
    db.commit()
    return jsonify({"lecture": _lecture_json(item, db.get(LectureCourse, item.course_id))})


@admin_api.get("/admin/lectures/<lecture_id>/versions")
@login_required
@teacher_required
def lecture_versions(db, lecture_id):
    item = _lecture_for_user(db, lecture_id)
    if not item:
        return _json_error("lecture not found", 404)
    rows = db.scalars(
        select(LectureVersion)
        .where(LectureVersion.lecture_id == item.id)
        .order_by(LectureVersion.version.desc())
    ).all()
    return jsonify(
        {
            "items": [
                {
                    "version": row.version,
                    "change_reason": row.change_reason,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


@admin_api.post("/admin/lectures/<lecture_id>/rollback")
@login_required
@teacher_required
@csrf_required
def rollback_lecture(db, lecture_id):
    item = _lecture_for_user(db, lecture_id)
    if not item:
        return _json_error("lecture not found", 404)
    body = request.get_json(silent=True) or {}
    try:
        target_version = int(body.get("version"))
    except (TypeError, ValueError):
        return _json_error("version is required", 400)
    historical = db.scalar(
        select(LectureVersion).where(
            LectureVersion.lecture_id == item.id,
            LectureVersion.version == target_version,
        )
    )
    if not historical:
        return _json_error("lecture version not found", 404)
    snapshot = historical.snapshot
    item.title = snapshot["title"]
    item.summary = snapshot.get("summary", "")
    item.sort_order = int(snapshot.get("sort_order", item.sort_order))
    item.payload = snapshot["payload"]
    item.version += 1
    item.status = "draft"
    item.updated_by = request.current_user.id
    _add_lecture_version(
        db,
        item,
        request.current_user.id,
        f"回滚到版本 {target_version}",
    )
    _audit(
        db,
        request.current_user,
        "lecture.rollback",
        "lecture",
        item.id,
        {"from_version": target_version, "new_version": item.version},
    )
    db.commit()
    return jsonify({"lecture": _lecture_json(item, db.get(LectureCourse, item.course_id))})


@admin_api.get("/public/lectures")
def public_lectures():
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(PublishedLecture).order_by(
                PublishedLecture.course_title,
                PublishedLecture.sort_order,
                PublishedLecture.published_at,
            )
        ).all()
        response = jsonify(
            {"items": [_published_lecture_json(row, include_payload=False) for row in rows]}
        )
        version_sum = sum(row.version for row in rows)
        response.set_etag(f"lectures-{len(rows)}-{version_sum}")
        return response.make_conditional(request)
    finally:
        SessionLocal.remove()


@admin_api.get("/public/lectures/<lecture_ref>")
def public_lecture(lecture_ref):
    db = SessionLocal()
    try:
        item = db.scalar(
            select(PublishedLecture).where(
                or_(
                    PublishedLecture.lecture_id == lecture_ref,
                    PublishedLecture.slug == lecture_ref,
                )
            )
        )
        if not item:
            return _json_error("published lecture not found", 404)
        response = jsonify({"lecture": _published_lecture_json(item)})
        response.set_etag(f"lecture-{item.lecture_id}-v{item.version}")
        return response.make_conditional(request)
    finally:
        SessionLocal.remove()


@admin_api.post("/admin/reviews/<review_id>/approve")
@login_required
@csrf_required
def approve_review(db, review_id):
    item = db.get(ReviewItem, review_id)
    if not item or item.job.owner_id != request.current_user.id:
        return _json_error("review item not found", 404)
    if item.status != "pending_review":
        return _json_error("review item is not pending", 409)

    if item.entity_type == "question":
        data, error = _valid_question_data(item.payload)
        if error:
            return _json_error(f"invalid question payload: {error}", 400)
        nodes, error = _question_knowledge_nodes(db, data["knowledge_refs"])
        if error:
            return _json_error(error, 400)
        content_hash = _question_content_hash(data)
        duplicate = db.scalar(
            select(Question).where(
                Question.content_hash == content_hash,
                Question.status.notin_({"archived", "merged"}),
            )
        )
        item.status = "approved"
        item.reviewed_by = request.current_user.id
        item.reviewed_at = utcnow()
        if duplicate:
            _audit(
                db,
                request.current_user,
                "review.approve_duplicate",
                "review_item",
                item.id,
                {"question_id": duplicate.id},
            )
            db.commit()
            return jsonify(
                {
                    "success": True,
                    "question_id": duplicate.id,
                    "duplicate": True,
                }
            )

        question_id, generated_code = _next_question_code(db)
        requested_code = str((item.payload or {}).get("id", "")).strip().upper()
        code = (
            requested_code
            if QUESTION_CODE_PATTERN.fullmatch(requested_code)
            and not db.scalar(select(Question).where(Question.code == requested_code))
            else generated_code
        )
        source = dict(data["source"])
        source.update(
            {
                "review_id": item.id,
                "upload_id": item.job.upload_id,
                "original_file": item.job.upload.original_name,
            }
        )
        question = Question(
            id=question_id,
            code=code,
            owner_id=request.current_user.id,
            module=data["module"],
            question_type=data["question_type"],
            difficulty=data["difficulty"],
            stem=data["stem"],
            options_json=data["options"],
            answer=data["answer"],
            analysis=data["analysis"],
            tags_json=data["tags"],
            source_json=source,
            content_hash=content_hash,
            status="published",
            version=1,
            source_review_id=item.id,
            created_by=request.current_user.id,
            updated_by=request.current_user.id,
            published_by=request.current_user.id,
            published_at=utcnow(),
        )
        db.add(question)
        db.flush()
        _replace_question_links(db, question, nodes, request.current_user.id)
        _add_question_version(
            db,
            question,
            request.current_user.id,
            "AI 审核通过并建立正式题目",
            [node.id for node in nodes],
        )
        _publish_question_snapshot(db, question, request.current_user.id)
        _audit(
            db,
            request.current_user,
            "review.approve_question",
            "review_item",
            item.id,
            {"question_id": question.id},
        )
        db.commit()
        return jsonify({"success": True, "question_id": question.id, "duplicate": False})

    published = PublishedContent(
        entity_type=item.entity_type,
        payload=item.payload,
        source_review_id=item.id,
        created_by=request.current_user.id,
    )
    item.status = "approved"
    item.reviewed_by = request.current_user.id
    item.reviewed_at = utcnow()
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
    item.reviewed_at = utcnow()
    _audit(db, request.current_user, "review.reject", "review_item", item.id)
    db.commit()
    return jsonify({"success": True})


@admin_api.get("/public/questions")
def public_questions():
    db = SessionLocal()
    try:
        rows = db.scalars(
            select(PublishedQuestion).order_by(PublishedQuestion.published_at.desc())
        ).all()
        response = jsonify(
            {"items": [_published_question_json(db, row, include_answers=False) for row in rows]}
        )
        version_sum = sum(row.version for row in rows)
        response.set_etag(f"questions-{len(rows)}-{version_sum}")
        return response.make_conditional(request)
    finally:
        SessionLocal.remove()


@admin_api.get("/health")
def health():
    """进程存活检查，不访问数据库。"""
    return jsonify({"status": "ok", "service": "shuxue-api"})


@admin_api.get("/ready")
def ready():
    """就绪检查：确认应用可以访问正式数据存储。"""
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return jsonify({"status": "ready", "database": "ok"})
    except Exception:
        return jsonify({"status": "not_ready", "database": "unavailable"}), 503
    finally:
        SessionLocal.remove()


def configure_platform(app):
    environment = os.environ.get("SHUXUE_ENV", "production").strip().lower()
    if environment != "production" or os.environ.get("SHUXUE_AUTO_CREATE_SCHEMA") == "1":
        init_database()
    session_secret = os.environ.get("SHUXUE_SESSION_SECRET", "").strip()
    if not session_secret:
        raise RuntimeError("SHUXUE_SESSION_SECRET must be configured")
    if environment == "production" and len(session_secret) < 32:
        raise RuntimeError("SHUXUE_SESSION_SECRET must contain at least 32 characters in production")
    ensure_knowledge_graph_seed()
    ensure_published_knowledge_snapshots()

    app.config.update(
        SECRET_KEY=session_secret,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=environment == "production",
        SESSION_COOKIE_SAMESITE="Strict",
        SESSION_COOKIE_NAME="shuxue_admin_session",
        PERMANENT_SESSION_LIFETIME=timedelta(
            hours=max(1, int(os.environ.get("SHUXUE_SESSION_HOURS", "8")))
        ),
        SESSION_REFRESH_EACH_REQUEST=False,
        LOGIN_FAILURE_WINDOW_SECONDS=max(
            60, int(os.environ.get("SHUXUE_LOGIN_WINDOW_SECONDS", "900"))
        ),
        LOGIN_ACCOUNT_FAILURE_LIMIT=max(
            LOGIN_COOLDOWN_START, int(os.environ.get("SHUXUE_LOGIN_ACCOUNT_LIMIT", "10"))
        ),
        LOGIN_IP_FAILURE_LIMIT=max(
            LOGIN_COOLDOWN_START, int(os.environ.get("SHUXUE_LOGIN_IP_LIMIT", "30"))
        ),
        AI_JOB_MAX_ATTEMPTS=max(
            1, int(os.environ.get("SHUXUE_AI_MAX_ATTEMPTS", "3"))
        ),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )
    app.register_blueprint(admin_api)
