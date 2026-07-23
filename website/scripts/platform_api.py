"""教师后台账号、上传任务、审核与发布 API。"""

import hashlib
import os
import secrets
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import delete, func, or_, select, text
from werkzeug.utils import secure_filename

from platform_db import (
    AIJob,
    AuditLog,
    LoginFailure,
    PublishedKnowledge,
    PublishedContent,
    ReviewItem,
    SessionLocal,
    UploadFile,
    User,
    KnowledgeDocument,
    ensure_published_knowledge_snapshots,
    init_database,
    utcnow,
)


admin_api = Blueprint("admin_api", __name__, url_prefix="/api/v1")
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".docx", ".txt", ".md"}
LOGIN_COOLDOWN_START = 5


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


def _published_knowledge_json(item):
    return {
        "node_id": item.node_id,
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


@admin_api.get("/public/knowledge/<node_id>")
def public_knowledge(node_id):
    db = SessionLocal()
    try:
        item = db.get(PublishedKnowledge, node_id)
        if not item:
            return _json_error("knowledge document not found", 404)
        response = jsonify({"knowledge": _published_knowledge_json(item)})
        response.set_etag(f"knowledge-{item.node_id}-v{item.version}")
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
    item.published_at = utcnow()
    item.updated_by = request.current_user.id
    snapshot = db.get(PublishedKnowledge, node_id)
    if not snapshot:
        snapshot = PublishedKnowledge(node_id=node_id)
        db.add(snapshot)
    snapshot.title = item.title
    snapshot.version = item.version
    snapshot.payload = item.payload
    snapshot.published_by = request.current_user.id
    snapshot.published_at = item.published_at
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
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )
    app.register_blueprint(admin_api)
