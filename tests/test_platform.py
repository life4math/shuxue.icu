import importlib
import os
import sys


ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPT_DIR = os.path.join(ROOT, "website", "scripts")
sys.path.insert(0, SCRIPT_DIR)


def build_app(tmp_path):
    os.environ["SHUXUE_DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    os.environ["SHUXUE_SESSION_SECRET"] = "test-secret-not-for-production"
    for name in ["server", "platform_api", "platform_db"]:
        sys.modules.pop(name, None)
    server = importlib.import_module("server")
    server.app.config.update(TESTING=True, SESSION_COOKIE_SECURE=False)
    sys.modules["platform_api"].UPLOAD_DIR = tmp_path / "uploads"
    return server.app, sys.modules["platform_db"]


def create_user(db_module, email="teacher@example.com", password="correct-horse-battery"):
    user = db_module.User(email=email, display_name="测试教师", role="teacher")
    user.set_password(password)
    db = db_module.SessionLocal()
    db.add(user)
    db.commit()
    db_module.SessionLocal.remove()
    return email, password


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


def bytes_io(content):
    from io import BytesIO

    return BytesIO(content)
