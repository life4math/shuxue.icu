import importlib
import os
import sys

import pytest
from sqlalchemy import select


ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPT_DIR = os.path.join(ROOT, "website", "scripts")
sys.path.insert(0, SCRIPT_DIR)


def build_app(tmp_path):
    os.environ["SHUXUE_DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    os.environ["SHUXUE_SESSION_SECRET"] = "test-secret-not-for-production-0123456789"
    os.environ["SHUXUE_ENV"] = "test"
    os.environ["SHUXUE_LOGIN_ACCOUNT_LIMIT"] = "5"
    os.environ["SHUXUE_LOGIN_IP_LIMIT"] = "8"
    os.environ["SHUXUE_LOGIN_WINDOW_SECONDS"] = "300"
    for name in ["server", "platform_api", "platform_db"]:
        sys.modules.pop(name, None)
    server = importlib.import_module("server")
    server.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    sys.modules["platform_api"].UPLOAD_DIR = tmp_path / "uploads"
    return server.app, sys.modules["platform_db"]


def create_user(db_module, email="teacher@example.com", password="correct-horse-battery", role="teacher"):
    user = db_module.User(email=email, display_name="测试教师", role=role)
    user.set_password(password)
    db = db_module.SessionLocal()
    db.add(user)
    db.commit()
    db_module.SessionLocal.remove()
    return email, password


def test_admin_only_user_management(tmp_path):
    app, db_module = build_app(tmp_path)
    admin_email, admin_password = create_user(db_module, "admin@example.com", "correct-admin-password", role="admin")
    teacher_email, teacher_password = create_user(db_module, "teacher@example.com", "correct-teacher-password", role="teacher")

    admin_client = app.test_client()
    teacher_client = app.test_client()
    admin_csrf = login(admin_client, admin_email, admin_password)
    headers = {"X-CSRF-Token": admin_csrf, "Content-Type": "application/json"}

    teacher_headers = {"X-CSRF-Token": login(teacher_client, teacher_email, teacher_password), "Content-Type": "application/json"}
    blocked = teacher_client.post(
        "/api/v1/admin/users",
        json={"email": "blocked@example.com", "display_name": "非法用户", "password": "correct-blocked-password", "role": "teacher"},
        headers=teacher_headers,
    )
    assert blocked.status_code == 403

    created = admin_client.post(
        "/api/v1/admin/users",
        json={"email": "newteacher@example.com", "display_name": "新教师", "password": "correct-new-teacher", "role": "teacher"},
        headers=headers,
    )
    assert created.status_code == 201
    user_id = created.get_json()["user"]["id"]

    list_result = admin_client.get("/api/v1/admin/users")
    assert any(item["email"] == "newteacher@example.com" for item in list_result.get_json()["items"])

    updated = admin_client.patch(
        f"/api/v1/admin/users/{user_id}",
        json={"display_name": "更新教师", "is_active": False},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.get_json()["user"]["is_active"] is False

    reset = admin_client.post(
        f"/api/v1/admin/users/{user_id}/reset-password",
        json={"password": "new-correct-password"},
        headers=headers,
    )
    assert reset.status_code == 200


def test_admin_cannot_disable_self(tmp_path):
    app, db_module = build_app(tmp_path)
    admin_email, admin_password = create_user(db_module, "admin@example.com", "correct-admin-password", role="admin")
    client = app.test_client()
    csrf = login(client, admin_email, admin_password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}

    from sqlalchemy import select

    db = db_module.SessionLocal()
    admin_user_id = db.scalar(
        select(db_module.User).where(db_module.User.email == admin_email)
    ).id
    db_module.SessionLocal.remove()

    response = client.patch(f"/api/v1/admin/users/{admin_user_id}", json={"is_active": False}, headers=headers)
    assert response.status_code == 409


def login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def test_login_requires_valid_credentials(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()

    assert client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"}).status_code == 401
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "teacher"
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Strict"
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is False


def test_login_rate_limit_and_admin_unlock(tmp_path):
    app, db_module = build_app(tmp_path)
    teacher_email, teacher_password = create_user(db_module)
    admin_email, admin_password = create_user(
        db_module,
        "admin@example.com",
        "correct-admin-password",
        role="admin",
    )
    client = app.test_client()

    for _ in range(4):
        assert client.post(
            "/api/v1/auth/login",
            json={"email": teacher_email, "password": "wrong-password"},
        ).status_code == 401
    limited = client.post(
        "/api/v1/auth/login",
        json={"email": teacher_email, "password": "wrong-password"},
    )
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
    assert client.post(
        "/api/v1/auth/login",
        json={"email": teacher_email, "password": teacher_password},
    ).status_code == 429

    admin_client = app.test_client()
    csrf = login(admin_client, admin_email, admin_password)
    db = db_module.SessionLocal()
    teacher = db.scalar(select(db_module.User).where(db_module.User.email == teacher_email))
    teacher_id = teacher.id
    failed_audits = db.scalars(
        select(db_module.AuditLog).where(db_module.AuditLog.action == "auth.login_failed")
    ).all()
    db_module.SessionLocal.remove()
    assert len(failed_audits) == 5

    unlocked = admin_client.post(
        f"/api/v1/admin/users/{teacher_id}/unlock-login",
        headers={"X-CSRF-Token": csrf},
    )
    assert unlocked.status_code == 200
    assert client.post(
        "/api/v1/auth/login",
        json={"email": teacher_email, "password": teacher_password},
    ).status_code == 200


def test_session_secret_never_falls_back_to_admin_token(tmp_path, monkeypatch):
    monkeypatch.setenv("SHUXUE_DATABASE_URL", f"sqlite:///{tmp_path / 'missing-secret.db'}")
    monkeypatch.delenv("SHUXUE_SESSION_SECRET", raising=False)
    monkeypatch.setenv("SHUXUE_ADMIN_TOKEN", "admin-token-must-not-be-a-session-secret")
    monkeypatch.setenv("SHUXUE_ENV", "test")
    for name in ["server", "platform_api", "platform_db"]:
        sys.modules.pop(name, None)

    with pytest.raises(RuntimeError, match="SHUXUE_SESSION_SECRET must be configured"):
        importlib.import_module("server")

    for name in ["server", "platform_api", "platform_db"]:
        sys.modules.pop(name, None)


def test_mutation_requires_csrf(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    login(client, email, password)

    response = client.post(
        "/api/v1/admin/uploads",
        data={"file": (bytes_io(b"question"), "question.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 403


def test_upload_deduplicates_and_creates_job(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf}

    first = client.post(
        "/api/v1/admin/uploads",
        data={"file": (bytes_io(b"same-content"), "lesson.txt")},
        headers=headers,
        content_type="multipart/form-data",
    )
    assert first.status_code == 201
    upload_id = first.get_json()["upload"]["id"]

    duplicate = client.post(
        "/api/v1/admin/uploads",
        data={"file": (bytes_io(b"same-content"), "lesson-copy.txt")},
        headers=headers,
        content_type="multipart/form-data",
    )
    assert duplicate.status_code == 200
    assert duplicate.get_json()["duplicate"] is True
    assert duplicate.get_json()["upload"]["id"] == upload_id

    job = client.post("/api/v1/admin/jobs", json={"upload_id": upload_id}, headers=headers)
    assert job.status_code == 201
    assert job.get_json()["job"]["status"] == "queued"


def test_public_questions_hide_answer_and_analysis(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    db = db_module.SessionLocal()
    from sqlalchemy import select

    user = db.scalar(select(db_module.User).where(db_module.User.email == email))
    db.add(
        db_module.PublishedContent(
            entity_type="question",
            payload={"stem": "1+1=?", "answer": "2", "analysis": "直接计算"},
            created_by=user.id,
        )
    )
    db.commit()
    db_module.SessionLocal.remove()

    payload = app.test_client().get("/api/v1/public/questions").get_json()["items"][0]
    assert payload["stem"] == "1+1=?"
    assert "answer" not in payload
    assert "analysis" not in payload


def test_knowledge_document_draft_submit_publish_and_public_read(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}
    payload = {
        "title": "集合",
        "sections": [{"title": "定义", "items": [{"text": "集合是确定对象的总体。", "math": "a\\in A"}]}],
    }

    saved = client.put("/api/v1/admin/knowledge/FUNC-01-01", json=payload, headers=headers)
    assert saved.status_code == 200
    assert saved.get_json()["knowledge"]["status"] == "draft"
    assert client.get("/api/v1/public/knowledge/FUNC-01-01").status_code == 404

    submitted = client.post("/api/v1/admin/knowledge/FUNC-01-01/submit", headers={"X-CSRF-Token": csrf})
    assert submitted.status_code == 200
    assert submitted.get_json()["knowledge"]["status"] == "pending_review"

    published = client.post("/api/v1/admin/knowledge/FUNC-01-01/publish", headers={"X-CSRF-Token": csrf})
    assert published.status_code == 200
    public = client.get("/api/v1/public/knowledge/FUNC-01-01")
    assert public.status_code == 200
    assert public.get_json()["knowledge"]["payload"]["sections"][0]["items"][0]["math"] == "a\\in A"


def test_health_and_readiness(tmp_path):
    app, _ = build_app(tmp_path)
    client = app.test_client()

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok", "service": "shuxue-api"}

    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    assert ready.get_json() == {"status": "ready", "database": "ok"}


def bytes_io(content):
    from io import BytesIO

    return BytesIO(content)
