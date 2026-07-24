import importlib
import json
import os
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect, select, text


ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPT_DIR = os.path.join(ROOT, "website", "scripts")
sys.path.insert(0, SCRIPT_DIR)


def build_app(tmp_path):
    os.environ["SHUXUE_DATABASE_URL"] = f"sqlite:///{tmp_path / 'test.db'}"
    os.environ["SHUXUE_SESSION_SECRET"] = "test-secret-not-for-production-0123456789"
    os.environ["SHUXUE_ADMIN_TOKEN"] = "test-admin-token"
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


def test_alembic_baseline_creates_and_versions_schema(tmp_path):
    database_path = tmp_path / "migration.db"
    environment = os.environ.copy()
    environment["SHUXUE_DATABASE_URL"] = f"sqlite:///{database_path}"
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "migrate.py")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {"users", "knowledge_documents", "published_knowledge", "alembic_version"} <= tables
    ai_job_columns = {item["name"] for item in inspector.get_columns("ai_jobs")}
    assert {"next_attempt_at", "heartbeat_at"} <= ai_job_columns
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == (
            "0005_formal_question_bank"
        )
        assert connection.execute(text("SELECT COUNT(*) FROM knowledge_nodes")).scalar_one() == 71
        assert connection.execute(
            text("SELECT COUNT(*) FROM knowledge_nodes WHERE parent_id IS NULL")
        ).scalar_one() == 5
        assert connection.execute(
            text("SELECT COUNT(DISTINCT id) FROM knowledge_nodes")
        ).scalar_one() == 71
    assert {
        "knowledge_nodes",
        "knowledge_node_versions",
        "knowledge_aliases",
        "knowledge_relations",
        "published_knowledge_nodes",
        "published_knowledge_relations",
        "lecture_courses",
        "lectures",
        "lecture_versions",
        "published_lectures",
        "questions",
        "question_versions",
        "question_knowledge_links",
        "published_questions",
        "published_question_knowledge_links",
    } <= tables


def test_dynamic_graph_migration_upgrades_legacy_content_tables(tmp_path):
    database_path = tmp_path / "legacy-migration.db"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(40) PRIMARY KEY)"))
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES ('0002_ai_job_reliability')")
        )
        connection.execute(text("CREATE TABLE users (id VARCHAR(40) PRIMARY KEY)"))
        connection.execute(
            text(
                "CREATE TABLE knowledge_documents ("
                "id VARCHAR(40) PRIMARY KEY, node_id VARCHAR(40) UNIQUE, "
                "title VARCHAR(160), status VARCHAR(24), version INTEGER, payload JSON)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE published_knowledge ("
                "node_id VARCHAR(40) PRIMARY KEY, title VARCHAR(160), "
                "version INTEGER, payload JSON)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO knowledge_documents "
                "(id, node_id, title, status, version, payload) "
                "VALUES ('kdoc_legacy', 'FUNC-01-01', '集合', 'published', 1, '{}')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO published_knowledge "
                "(node_id, title, version, payload) "
                "VALUES ('FUNC-01-01', '集合', 1, '{}')"
            )
        )

    environment = os.environ.copy()
    environment["SHUXUE_DATABASE_URL"] = f"sqlite:///{database_path}"
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "migrate.py")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    inspector = inspect(engine)
    assert "knowledge_node_id" in {
        item["name"] for item in inspector.get_columns("knowledge_documents")
    }
    with engine.connect() as connection:
        expected_id = connection.execute(
            text("SELECT id FROM knowledge_nodes WHERE code = 'FUNC-01-01'")
        ).scalar_one()
        assert connection.execute(
            text(
                "SELECT knowledge_node_id FROM knowledge_documents "
                "WHERE node_id = 'FUNC-01-01'"
            )
        ).scalar_one() == expected_id
        assert connection.execute(
            text(
                "SELECT knowledge_node_id FROM published_knowledge "
                "WHERE node_id = 'FUNC-01-01'"
            )
        ).scalar_one() == expected_id


def test_formal_question_migration_backfills_legacy_published_content(tmp_path):
    database_path = tmp_path / "question-backfill.db"
    environment = os.environ.copy()
    environment["SHUXUE_DATABASE_URL"] = f"sqlite:///{database_path}"
    upgraded_to_prep = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            os.path.join(ROOT, "alembic.ini"),
            "upgrade",
            "0004_lesson_prep",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert upgraded_to_prep.returncode == 0, upgraded_to_prep.stderr

    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users "
                "(id, email, display_name, password_hash, role, is_active, created_at) "
                "VALUES ('usr_legacy', 'legacy@example.com', '旧教师', 'hash', "
                "'teacher', 1, '2026-07-24 00:00:00')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO published_content "
                "(id, entity_type, status, payload, source_review_id, created_by, "
                "created_at, updated_at) "
                "VALUES ('pub_legacy_question', 'question', 'published', :payload, "
                "NULL, 'usr_legacy', '2026-07-24 00:00:00', '2026-07-24 00:00:00')"
            ),
            {
                "payload": json.dumps(
                    {
                        "id": "Q-LEGACY-001",
                        "module": "FUNC",
                        "type": "solve",
                        "difficulty": 3,
                        "stem": "迁移前已经发布的题目",
                        "answer": "旧答案",
                        "analysis": "旧解析",
                        "knowledge_points": ["FUNC-01-01"],
                    },
                    ensure_ascii=False,
                )
            },
        )

    migrated = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "migrate.py")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert migrated.returncode == 0, migrated.stderr
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT q.id, q.code, q.status, p.answer "
                "FROM questions q JOIN published_questions p ON p.question_id = q.id "
                "WHERE q.code = 'Q-LEGACY-001'"
            )
        ).one()
        assert row.code == "Q-LEGACY-001"
        assert row.status == "published"
        assert row.answer == "旧答案"
        assert connection.execute(
            text(
                "SELECT COUNT(*) FROM published_question_knowledge_links "
                "WHERE question_id = :question_id"
            ),
            {"question_id": row.id},
        ).scalar_one() == 1


def test_public_demo_json_is_read_only(tmp_path):
    app, _ = build_app(tmp_path)
    client = app.test_client()

    questions = client.get("/api/questions")
    methods = client.get("/api/methods")
    assert questions.status_code == 200
    assert len(questions.get_json()["items"]) == 17
    assert methods.status_code == 200
    assert len(methods.get_json()["items"]) == 7

    removed = client.post(
        "/api/save-question",
        json={"stem": "不应写入静态文件"},
        headers={"X-Admin-Token": "test-admin-token"},
    )
    assert removed.status_code == 410
    assert removed.get_json()["replacement"].startswith("/api/v1/")


def test_cli_ingest_enqueues_database_job(tmp_path, monkeypatch):
    _, db_module = build_app(tmp_path)
    email, _ = create_user(db_module)
    sys.modules.pop("ingest", None)
    ingest = importlib.import_module("ingest")
    monkeypatch.setattr(ingest, "UPLOAD_DIR", tmp_path / "uploads")

    source = tmp_path / "sample.txt"
    source.write_text("函数与集合测试材料", encoding="utf-8")
    db = db_module.SessionLocal()
    owner = db.scalar(select(db_module.User).where(db_module.User.email == email))
    queued = ingest.enqueue_file(db, owner, source)
    db.commit()

    job = db.get(db_module.AIJob, queued["job_id"])
    upload = db.get(db_module.UploadFile, queued["upload_id"])
    assert job.status == "queued"
    assert upload.sha256
    assert (ingest.UPLOAD_DIR / upload.stored_name).read_text("utf-8") == "函数与集合测试材料"
    db_module.SessionLocal.remove()


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
    job_id = job.get_json()["job"]["id"]

    db = db_module.SessionLocal()
    stored_job = db.get(db_module.AIJob, job_id)
    stored_job.status = "failed"
    stored_job.attempt_count = 3
    stored_job.error_message = "temporary failure"
    stored_job.upload.status = "failed"
    db.commit()
    db_module.SessionLocal.remove()

    retried = client.post(f"/api/v1/admin/jobs/{job_id}/retry", headers=headers)
    assert retried.status_code == 200
    assert retried.get_json()["job"]["status"] == "queued"
    assert retried.get_json()["job"]["attempt_count"] == 0

    duplicate_retry = client.post(f"/api/v1/admin/jobs/{job_id}/retry", headers=headers)
    assert duplicate_retry.status_code == 409


def test_worker_retries_then_marks_job_failed(tmp_path, monkeypatch):
    _, db_module = build_app(tmp_path)
    email, _ = create_user(db_module)
    db = db_module.SessionLocal()
    owner = db.scalar(select(db_module.User).where(db_module.User.email == email))
    upload = db_module.UploadFile(
        owner_id=owner.id,
        original_name="retry.txt",
        stored_name="retry.txt",
        sha256="a" * 64,
        content_type="text/plain",
        size=5,
    )
    db.add(upload)
    db.flush()
    job = db_module.AIJob(upload_id=upload.id, owner_id=owner.id)
    db.add(job)
    db.commit()
    job_id = job.id
    db_module.SessionLocal.remove()

    upload_dir = tmp_path / "worker-uploads"
    upload_dir.mkdir()
    (upload_dir / "retry.txt").write_text("retry", encoding="utf-8")
    monkeypatch.setenv("SHUXUE_AI_MAX_ATTEMPTS", "3")
    monkeypatch.setenv("SHUXUE_AI_RETRY_BASE_SECONDS", "1")
    sys.modules.pop("worker", None)
    worker = importlib.import_module("worker")
    monkeypatch.setattr(worker, "UPLOAD_DIR", upload_dir)
    monkeypatch.setattr(
        worker,
        "process_file",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("temporary AI failure")),
    )

    assert worker.process_next_job() is True
    db = db_module.SessionLocal()
    stored = db.get(db_module.AIJob, job_id)
    assert stored.status == "queued"
    assert stored.attempt_count == 1
    assert stored.next_attempt_at is not None
    stored.attempt_count = 2
    stored.next_attempt_at = None
    db.commit()
    db_module.SessionLocal.remove()

    assert worker.process_next_job() is True
    db = db_module.SessionLocal()
    stored = db.get(db_module.AIJob, job_id)
    assert stored.status == "failed"
    assert stored.attempt_count == 3
    assert stored.upload.status == "failed"
    db_module.SessionLocal.remove()


def test_worker_recovers_interrupted_job(tmp_path, monkeypatch):
    _, db_module = build_app(tmp_path)
    email, _ = create_user(db_module)
    db = db_module.SessionLocal()
    owner = db.scalar(select(db_module.User).where(db_module.User.email == email))
    upload = db_module.UploadFile(
        owner_id=owner.id,
        original_name="recover.txt",
        stored_name="recover.txt",
        sha256="b" * 64,
        content_type="text/plain",
        size=7,
        status="processing",
    )
    db.add(upload)
    db.flush()
    job = db_module.AIJob(
        upload_id=upload.id,
        owner_id=owner.id,
        status="extracting",
        progress=35,
        attempt_count=1,
    )
    db.add(job)
    db.commit()
    job_id = job.id
    db_module.SessionLocal.remove()

    monkeypatch.setenv("SHUXUE_AI_MAX_ATTEMPTS", "3")
    sys.modules.pop("worker", None)
    worker = importlib.import_module("worker")
    assert worker.recover_interrupted_jobs() == 1

    db = db_module.SessionLocal()
    stored = db.get(db_module.AIJob, job_id)
    assert stored.status == "queued"
    assert stored.progress == 0
    assert stored.next_attempt_at is not None
    assert stored.upload.status == "queued"
    db_module.SessionLocal.remove()


def test_public_questions_hide_answer_and_analysis(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}
    created = client.post(
        "/api/v1/admin/questions",
        json={
            "code": "Q-TEST-PUBLIC",
            "module": "ALGE",
            "question_type": "solve",
            "difficulty": 1,
            "stem": "1+1=?",
            "answer": "2",
            "analysis": "直接计算",
            "source": {
                "type": "teacher_manual",
                "page_number": 3,
                "upload_id": "upl_private",
                "review_id": "rev_private",
                "original_file": "教师内部资料.pdf",
            },
            "knowledge_node_ids": ["ALGE-01-01"],
        },
        headers=headers,
    )
    assert created.status_code == 201
    question = created.get_json()["question"]
    assert client.post(
        f"/api/v1/admin/questions/{question['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200

    payload = client.get("/api/v1/public/questions").get_json()["items"][0]
    assert payload["stem"] == "1+1=?"
    assert "answer" not in payload
    assert "analysis" not in payload
    assert payload["source"] == {"type": "teacher_manual", "page_number": 3}


def test_formal_question_crud_publish_deduplicate_and_version(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}
    payload = {
        "code": "Q-FUNC-001",
        "module": "FUNC",
        "question_type": "choice",
        "difficulty": 3,
        "stem": "函数 $f(x)=x^2$ 的最小值是？",
        "options": [
            {"label": "A", "content": "$0$"},
            {"label": "B", "content": "$1$"},
        ],
        "answer": "A",
        "analysis": "配方或观察平方的非负性。",
        "tags": ["函数", "最值"],
        "source": {"type": "teacher_manual"},
        "knowledge_node_ids": ["FUNC-01-02"],
    }
    created = client.post("/api/v1/admin/questions", json=payload, headers=headers)
    assert created.status_code == 201
    question = created.get_json()["question"]
    assert question["status"] == "draft"
    assert question["knowledge_node_ids"]

    duplicate = client.post(
        "/api/v1/admin/questions",
        json={**payload, "code": "Q-FUNC-002"},
        headers=headers,
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json()["duplicate_id"] == question["id"]
    assert client.get("/api/v1/public/questions").get_json()["items"] == []

    published = client.post(
        f"/api/v1/admin/questions/{question['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    )
    assert published.status_code == 200
    picker = client.get("/api/v1/admin/question-picker?query=Q-FUNC-001")
    assert picker.status_code == 200
    assert picker.get_json()["items"][0]["answer"] == "A"

    updated = client.patch(
        f"/api/v1/admin/questions/{question['id']}",
        json={
            "version": 1,
            "answer": "A，最小值为 0",
            "change_reason": "补充答案文字",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.get_json()["question"]["version"] == 2
    assert updated.get_json()["question"]["status"] == "draft"
    assert client.get("/api/v1/admin/question-picker?query=Q-FUNC-001").get_json()[
        "items"
    ][0]["answer"] == "A"

    assert client.post(
        f"/api/v1/admin/questions/{question['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    assert client.get("/api/v1/admin/question-picker?query=Q-FUNC-001").get_json()[
        "items"
    ][0]["answer"] == "A，最小值为 0"
    versions = client.get(
        f"/api/v1/admin/questions/{question['id']}/versions"
    ).get_json()["items"]
    assert [item["version"] for item in versions] == [2, 1]


def test_review_approval_writes_formal_question_and_deduplicates(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    db = db_module.SessionLocal()
    owner = db.scalar(select(db_module.User).where(db_module.User.email == email))
    upload = db_module.UploadFile(
        owner_id=owner.id,
        original_name="source.pdf",
        stored_name="source.pdf",
        sha256="c" * 64,
        content_type="application/pdf",
        size=100,
    )
    db.add(upload)
    db.flush()
    job = db_module.AIJob(upload_id=upload.id, owner_id=owner.id, status="review")
    db.add(job)
    db.flush()
    question_payload = {
        "id": "Q-AI-001",
        "module": "GEOM",
        "type": "proof",
        "difficulty": 4,
        "stem": "证明两直线平行。",
        "answer": "利用平行判定定理。",
        "analysis": "先寻找同位角。",
        "knowledge_points": ["GEOM-01-01"],
        "source": {"page_number": 12},
    }
    first = db_module.ReviewItem(
        job_id=job.id,
        entity_type="question",
        payload=question_payload,
    )
    second = db_module.ReviewItem(
        job_id=job.id,
        entity_type="question",
        payload={**question_payload, "id": "Q-AI-002"},
    )
    db.add_all([first, second])
    db.commit()
    first_id = first.id
    second_id = second.id
    db_module.SessionLocal.remove()

    client = app.test_client()
    csrf = login(client, email, password)
    first_result = client.post(
        f"/api/v1/admin/reviews/{first_id}/approve",
        headers={"X-CSRF-Token": csrf},
    )
    assert first_result.status_code == 200
    assert first_result.get_json()["duplicate"] is False
    question_id = first_result.get_json()["question_id"]

    db = db_module.SessionLocal()
    stored = db.get(db_module.Question, question_id)
    assert stored.code == "Q-AI-001"
    assert stored.status == "published"
    assert stored.source_json["original_file"] == "source.pdf"
    assert db.get(db_module.PublishedQuestion, question_id).answer == "利用平行判定定理。"
    assert db.scalar(
        select(db_module.PublishedContent).where(
            db_module.PublishedContent.entity_type == "question"
        )
    ) is None
    db_module.SessionLocal.remove()

    duplicate_result = client.post(
        f"/api/v1/admin/reviews/{second_id}/approve",
        headers={"X-CSRF-Token": csrf},
    )
    assert duplicate_result.status_code == 200
    assert duplicate_result.get_json() == {
        "success": True,
        "question_id": question_id,
        "duplicate": True,
    }


def test_published_lecture_freezes_formal_question_snapshot(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}
    created_question = client.post(
        "/api/v1/admin/questions",
        json={
            "code": "Q-FREEZE-001",
            "module": "FUNC",
            "question_type": "solve",
            "difficulty": 2,
            "stem": "第一版题干 $x+1=2$。",
            "answer": "$x=1$",
            "analysis": "移项。",
            "knowledge_node_ids": ["FUNC-01-01"],
        },
        headers=headers,
    ).get_json()["question"]
    assert client.post(
        f"/api/v1/admin/questions/{created_question['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200

    course = client.post(
        "/api/v1/admin/lecture-courses",
        json={"title": "快照测试课程"},
        headers=headers,
    ).get_json()["course"]
    lecture = client.post(
        "/api/v1/admin/lectures",
        json={"course_id": course["id"], "title": "题目快照", "slug": "question-freeze"},
        headers=headers,
    ).get_json()["lecture"]
    saved = client.put(
        f"/api/v1/admin/lectures/{lecture['id']}/draft",
        json={
            "version": 1,
            "title": "题目快照",
            "summary": "",
            "payload": {
                "sections": [
                    {
                        "id": "sec_question",
                        "title": "正式题目",
                        "blocks": [
                            {
                                "id": "blk_question",
                                "type": "question_ref",
                                "question_id": created_question["id"],
                                "title": "课堂练习",
                                "stem": "错误的临时题干",
                            }
                        ],
                    }
                ]
            },
        },
        headers=headers,
    )
    assert saved.status_code == 200
    assert client.post(
        f"/api/v1/admin/lectures/{lecture['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    public_before = client.get("/api/v1/public/lectures/question-freeze").get_json()[
        "lecture"
    ]["payload"]["sections"][0]["blocks"][0]
    assert public_before["stem"] == "第一版题干 $x+1=2$。"
    assert public_before["answer"] == "$x=1$"
    assert public_before["code"] == "Q-FREEZE-001"

    updated = client.patch(
        f"/api/v1/admin/questions/{created_question['id']}",
        json={"version": 1, "stem": "第二版题干。", "answer": "第二版答案。"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert client.post(
        f"/api/v1/admin/questions/{created_question['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    public_after = client.get("/api/v1/public/lectures/question-freeze").get_json()[
        "lecture"
    ]["payload"]["sections"][0]["blocks"][0]
    assert public_after["stem"] == "第一版题干 $x+1=2$。"
    assert public_after["answer"] == "$x=1$"


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
    first_etag = public.headers["ETag"]
    assert client.get(
        "/api/v1/public/knowledge/FUNC-01-01",
        headers={"If-None-Match": first_etag},
    ).status_code == 304

    draft_payload = {
        "title": "集合（修订中）",
        "sections": [{"title": "定义", "items": [{"text": "尚未发布的新草稿。", "math": "b\\in B"}]}],
    }
    draft = client.put("/api/v1/admin/knowledge/FUNC-01-01", json=draft_payload, headers=headers)
    assert draft.status_code == 200
    assert draft.get_json()["knowledge"]["status"] == "draft"

    still_public = client.get("/api/v1/public/knowledge/FUNC-01-01")
    assert still_public.status_code == 200
    assert still_public.get_json()["knowledge"]["payload"]["sections"][0]["items"][0]["math"] == "a\\in A"
    assert still_public.headers["ETag"] == first_etag

    republished = client.post(
        "/api/v1/admin/knowledge/FUNC-01-01/publish",
        headers={"X-CSRF-Token": csrf},
    )
    assert republished.status_code == 200
    updated_public = client.get("/api/v1/public/knowledge/FUNC-01-01")
    assert updated_public.get_json()["knowledge"]["payload"]["sections"][0]["items"][0]["math"] == "b\\in B"
    assert updated_public.headers["ETag"] != first_etag


def test_dynamic_knowledge_node_create_move_publish_and_archive(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}

    initial_tree = client.get("/api/v1/public/knowledge-tree")
    assert initial_tree.status_code == 200
    assert initial_tree.get_json()["node_count"] == 71
    assert [item["code"] for item in initial_tree.get_json()["items"]] == [
        "FUNC",
        "GEOM",
        "ALGE",
        "PROB",
        "CALC",
    ]

    created = client.post(
        "/api/v1/admin/knowledge/nodes",
        json={
            "title": "新增动态知识点",
            "parent_id": "FUNC-01",
            "node_type": "concept",
            "knowledge_type": "procedure",
            "metadata": {"difficulty": [2, 4], "examFrequency": "medium"},
        },
        headers=headers,
    )
    assert created.status_code == 201
    node = created.get_json()["node"]
    assert node["id"].startswith("kn_")
    assert node["code"].startswith("KN-")
    assert node["status"] == "draft"
    assert client.get("/api/v1/public/knowledge-tree").get_json()["node_count"] == 71

    moved = client.patch(
        f"/api/v1/admin/knowledge/nodes/{node['id']}",
        json={
            "version": node["version"],
            "title": "移动后的知识点",
            "parent_id": "GEOM-01",
            "sort_order": 9,
        },
        headers=headers,
    )
    assert moved.status_code == 200
    moved_node = moved.get_json()["node"]
    assert moved_node["code"] == node["code"]
    assert moved_node["version"] == 2
    assert moved_node["status"] == "draft"

    stale = client.patch(
        f"/api/v1/admin/knowledge/nodes/{node['id']}",
        json={"version": 1, "title": "冲突更新"},
        headers=headers,
    )
    assert stale.status_code == 409
    assert stale.get_json()["current_version"] == 2

    cycle = client.patch(
        "/api/v1/admin/knowledge/nodes/FUNC",
        json={"version": 1, "parent_id": "FUNC-01"},
        headers=headers,
    )
    assert cycle.status_code == 409

    published = client.post(
        f"/api/v1/admin/knowledge/nodes/{node['id']}/publish",
        json={"version": 2},
        headers=headers,
    )
    assert published.status_code == 200
    public_tree = client.get("/api/v1/public/knowledge-tree").get_json()
    assert public_tree["node_count"] == 72

    body = {
        "title": "移动后的知识点",
        "sections": [{"title": "定义", "items": [{"text": "动态正文", "math": "x>0"}]}],
    }
    assert client.put(
        f"/api/v1/admin/knowledge/{node['id']}",
        json=body,
        headers=headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/admin/knowledge/{node['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200
    detail = client.get(f"/api/v1/public/knowledge/{node['code']}")
    assert detail.status_code == 200
    assert detail.get_json()["knowledge"]["knowledge_node_id"] == node["id"]

    archived = client.post(
        f"/api/v1/admin/knowledge/nodes/{node['id']}/archive",
        json={"version": 2},
        headers=headers,
    )
    assert archived.status_code == 200
    assert client.get("/api/v1/public/knowledge-tree").get_json()["node_count"] == 71
    assert client.get(f"/api/v1/public/knowledge/{node['code']}").status_code == 404


def test_knowledge_relation_draft_publish_and_republish(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}

    created = client.post(
        "/api/v1/admin/knowledge/relations",
        json={
            "source_node_id": "FUNC-01-01",
            "target_node_id": "FUNC-02-01",
            "relation_type": "prerequisite",
            "weight": 80,
        },
        headers=headers,
    )
    assert created.status_code == 201
    relation = created.get_json()["relation"]
    assert relation["status"] == "draft"
    assert client.get("/api/v1/public/knowledge-tree").get_json()["relations"] == []

    published = client.post(
        f"/api/v1/admin/knowledge/relations/{relation['id']}/publish",
        json={"version": 1},
        headers=headers,
    )
    assert published.status_code == 200
    public_relation = client.get("/api/v1/public/knowledge-tree").get_json()["relations"][0]
    assert public_relation["weight"] == 80

    updated = client.patch(
        f"/api/v1/admin/knowledge/relations/{relation['id']}",
        json={"version": 1, "weight": 95},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.get_json()["relation"]["version"] == 2
    assert client.get("/api/v1/public/knowledge-tree").get_json()["relations"][0]["weight"] == 80

    republished = client.post(
        f"/api/v1/admin/knowledge/relations/{relation['id']}/publish",
        json={"version": 2},
        headers=headers,
    )
    assert republished.status_code == 200
    assert client.get("/api/v1/public/knowledge-tree").get_json()["relations"][0]["weight"] == 95


def test_merged_knowledge_code_redirects_to_published_target(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}

    created_nodes = []
    for code, title in (("TEST-SOURCE", "待合并节点"), ("TEST-TARGET", "目标节点")):
        response = client.post(
            "/api/v1/admin/knowledge/nodes",
            json={"code": code, "title": title, "node_type": "concept"},
            headers=headers,
        )
        assert response.status_code == 201
        node = response.get_json()["node"]
        assert client.post(
            f"/api/v1/admin/knowledge/nodes/{node['id']}/publish",
            json={"version": 1},
            headers=headers,
        ).status_code == 200
        created_nodes.append(node)
    source, target = created_nodes

    payload = {
        "title": "目标节点",
        "sections": [{"title": "说明", "items": [{"text": "合并后继续保留的正式正文"}]}],
    }
    assert client.put(
        f"/api/v1/admin/knowledge/{target['id']}",
        json=payload,
        headers=headers,
    ).status_code == 200
    assert client.post(
        f"/api/v1/admin/knowledge/{target['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    ).status_code == 200

    merged = client.post(
        f"/api/v1/admin/knowledge/nodes/{source['id']}/merge",
        json={"version": 1, "target_id": target["id"]},
        headers=headers,
    )
    assert merged.status_code == 200
    assert merged.get_json()["node"]["status"] == "merged"
    public = client.get("/api/v1/public/knowledge/TEST-SOURCE")
    assert public.status_code == 200
    assert public.get_json()["knowledge"]["code"] == "TEST-TARGET"
    assert public.get_json()["knowledge"]["payload"]["sections"][0]["items"][0]["text"] == (
        "合并后继续保留的正式正文"
    )


def test_existing_published_knowledge_is_backfilled_on_upgrade(tmp_path):
    app, db_module = build_app(tmp_path)
    email, _ = create_user(db_module)
    db = db_module.SessionLocal()
    user = db.scalar(select(db_module.User).where(db_module.User.email == email))
    db.add(
        db_module.KnowledgeDocument(
            node_id="GEOM-01-01",
            title="向量",
            status="published",
            version=3,
            payload={
                "title": "向量",
                "sections": [{"title": "定义", "items": [{"text": "旧版本已发布正文"}]}],
            },
            created_by=user.id,
            updated_by=user.id,
            published_by=user.id,
        )
    )
    db.commit()
    db_module.SessionLocal.remove()

    db_module.ensure_published_knowledge_snapshots()
    public = app.test_client().get("/api/v1/public/knowledge/GEOM-01-01")
    assert public.status_code == 200
    assert public.get_json()["knowledge"]["version"] == 3
    assert public.get_json()["knowledge"]["payload"]["sections"][0]["items"][0]["text"] == "旧版本已发布正文"


def test_lesson_prep_draft_publish_version_and_public_snapshot(tmp_path):
    app, db_module = build_app(tmp_path)
    email, password = create_user(db_module)
    client = app.test_client()
    csrf = login(client, email, password)
    headers = {"X-CSRF-Token": csrf, "Content-Type": "application/json"}

    course_response = client.post(
        "/api/v1/admin/lecture-courses",
        json={
            "title": "函数专题",
            "grade_label": "高三一轮",
            "description": "公开讲义测试课程",
        },
        headers=headers,
    )
    assert course_response.status_code == 201
    course = course_response.get_json()["course"]

    created_response = client.post(
        "/api/v1/admin/lectures",
        json={
            "course_id": course["id"],
            "title": "函数的单调性",
            "slug": "function-monotonicity",
        },
        headers=headers,
    )
    assert created_response.status_code == 201
    lecture = created_response.get_json()["lecture"]
    assert lecture["version"] == 1
    assert lecture["status"] == "draft"

    payload_v2 = {
        "sections": [
            {
                "id": "sec_intro",
                "title": "概念与判定",
                "sort_order": 0,
                "blocks": [
                    {
                        "id": "blk_text",
                        "type": "text",
                        "text": "先观察函数在区间上的变化。",
                    },
                    {
                        "id": "blk_math",
                        "type": "math",
                        "latex": "f'(x)>0",
                        "caption": "单调递增的充分条件",
                    },
                    {
                        "id": "blk_example",
                        "type": "example",
                        "title": "例题",
                        "stem": "判断函数的单调区间。",
                        "answer": "求导并讨论导数符号。",
                    },
                ],
            }
        ]
    }
    saved_response = client.put(
        f"/api/v1/admin/lectures/{lecture['id']}/draft",
        json={
            "version": 1,
            "title": "函数的单调性",
            "summary": "从图像直观过渡到导数判定。",
            "payload": payload_v2,
        },
        headers=headers,
    )
    assert saved_response.status_code == 200
    lecture = saved_response.get_json()["lecture"]
    assert lecture["version"] == 2

    stale_response = client.put(
        f"/api/v1/admin/lectures/{lecture['id']}/draft",
        json={
            "version": 1,
            "title": "冲突版本",
            "summary": "",
            "payload": payload_v2,
        },
        headers=headers,
    )
    assert stale_response.status_code == 409
    assert stale_response.get_json()["current_version"] == 2

    assert client.get("/api/v1/public/lectures/function-monotonicity").status_code == 404
    published_response = client.post(
        f"/api/v1/admin/lectures/{lecture['id']}/publish",
        headers={"X-CSRF-Token": csrf},
    )
    assert published_response.status_code == 200
    public_v2 = client.get("/api/v1/public/lectures/function-monotonicity")
    assert public_v2.status_code == 200
    assert public_v2.get_json()["lecture"]["payload"]["sections"][0]["blocks"][1]["latex"] == "f'(x)>0"
    public_etag = public_v2.headers["ETag"]
    assert client.get(
        "/api/v1/public/lectures/function-monotonicity",
        headers={"If-None-Match": public_etag},
    ).status_code == 304

    payload_v3 = {
        "sections": [
            {
                "id": "sec_intro",
                "title": "概念与判定（修订）",
                "sort_order": 0,
                "blocks": [{"id": "blk_text", "type": "text", "text": "尚未发布的修订。"}],
            }
        ]
    }
    draft_response = client.put(
        f"/api/v1/admin/lectures/{lecture['id']}/draft",
        json={
            "version": 2,
            "title": "函数的单调性（修订中）",
            "summary": "草稿不影响公开快照。",
            "payload": payload_v3,
        },
        headers=headers,
    )
    assert draft_response.status_code == 200
    assert draft_response.get_json()["lecture"]["version"] == 3
    still_public = client.get("/api/v1/public/lectures/function-monotonicity")
    assert still_public.get_json()["lecture"]["version"] == 2
    assert still_public.headers["ETag"] == public_etag

    versions = client.get(f"/api/v1/admin/lectures/{lecture['id']}/versions")
    assert [item["version"] for item in versions.get_json()["items"]] == [3, 2, 1]
    rolled_back = client.post(
        f"/api/v1/admin/lectures/{lecture['id']}/rollback",
        json={"version": 1},
        headers=headers,
    )
    assert rolled_back.status_code == 200
    assert rolled_back.get_json()["lecture"]["version"] == 4
    assert rolled_back.get_json()["lecture"]["status"] == "draft"

    unpublished = client.post(
        f"/api/v1/admin/lectures/{lecture['id']}/unpublish",
        headers={"X-CSRF-Token": csrf},
    )
    assert unpublished.status_code == 200
    assert client.get("/api/v1/public/lectures/function-monotonicity").status_code == 404


def test_lesson_prep_isolated_by_teacher_and_rejects_unsafe_blocks(tmp_path):
    app, db_module = build_app(tmp_path)
    first_email, first_password = create_user(
        db_module,
        "first@example.com",
        "correct-first-password",
    )
    second_email, second_password = create_user(
        db_module,
        "second@example.com",
        "correct-second-password",
    )
    first_client = app.test_client()
    first_csrf = login(first_client, first_email, first_password)
    first_headers = {"X-CSRF-Token": first_csrf, "Content-Type": "application/json"}
    course = first_client.post(
        "/api/v1/admin/lecture-courses",
        json={"title": "教师一的课程"},
        headers=first_headers,
    ).get_json()["course"]
    lecture = first_client.post(
        "/api/v1/admin/lectures",
        json={"course_id": course["id"], "title": "安全校验课次"},
        headers=first_headers,
    ).get_json()["lecture"]

    unsafe = first_client.put(
        f"/api/v1/admin/lectures/{lecture['id']}/draft",
        json={
            "version": 1,
            "title": "安全校验课次",
            "summary": "",
            "payload": {
                "sections": [
                    {
                        "id": "sec_one",
                        "title": "图片",
                        "blocks": [
                            {
                                "id": "blk_image",
                                "type": "image",
                                "url": "javascript:alert(1)",
                            }
                        ],
                    }
                ]
            },
        },
        headers=first_headers,
    )
    assert unsafe.status_code == 400

    second_client = app.test_client()
    second_csrf = login(second_client, second_email, second_password)
    assert second_client.get("/api/v1/admin/lecture-courses").get_json()["items"] == []
    assert second_client.get(f"/api/v1/admin/lectures/{lecture['id']}").status_code == 404
    assert second_client.patch(
        f"/api/v1/admin/lecture-courses/{course['id']}",
        json={"title": "越权修改"},
        headers={"X-CSRF-Token": second_csrf, "Content-Type": "application/json"},
    ).status_code == 404


def test_static_knowledge_seed_parser_is_utf8_safe():
    sys.modules.pop("seed_knowledge", None)
    seed_knowledge = importlib.import_module("seed_knowledge")
    contents = seed_knowledge.read_static_content()
    assert len(contents) == 51
    assert contents["FUNC-01-01"]["title"] == "集合的概念与运算"
    assert contents["CALC-01-02"]["sections"]


def test_bootstrap_seed_only_fills_missing_content(tmp_path):
    app, db_module = build_app(tmp_path)
    email, _ = create_user(db_module, "admin@example.com", "correct-admin-password", role="admin")
    sys.modules.pop("seed_knowledge", None)
    seed_knowledge = importlib.import_module("seed_knowledge")
    db = db_module.SessionLocal()
    user = db.scalar(select(db_module.User).where(db_module.User.email == email))
    contents = {
        "FUNC-01-01": {
            "title": "集合",
            "sections": [{"title": "定义", "items": [{"text": "首次引导内容"}]}],
        }
    }
    first = seed_knowledge.seed_contents(db, user, contents, bootstrap_missing=True)
    db.commit()
    assert first == {"created": 1, "updated": 0, "skipped": 0, "total": 1}

    snapshot = db.get(db_module.PublishedKnowledge, "FUNC-01-01")
    snapshot.payload = {
        "title": "集合",
        "sections": [{"title": "定义", "items": [{"text": "教师修改后的正式内容"}]}],
    }
    db.commit()
    second = seed_knowledge.seed_contents(db, user, contents, bootstrap_missing=True)
    db.commit()
    assert second == {"created": 0, "updated": 0, "skipped": 1, "total": 1}
    assert db.get(db_module.PublishedKnowledge, "FUNC-01-01").payload["sections"][0]["items"][0]["text"] == "教师修改后的正式内容"
    db_module.SessionLocal.remove()

    public = app.test_client().get("/api/v1/public/knowledge/FUNC-01-01")
    assert public.status_code == 200
    assert public.get_json()["knowledge"]["payload"]["sections"][0]["items"][0]["text"] == "教师修改后的正式内容"


def test_health_and_readiness(tmp_path):
    app, _ = build_app(tmp_path)
    client = app.test_client()

    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok", "service": "shuxue-api"}

    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    assert ready.get_json() == {"status": "ready", "database": "ok"}


def test_admin_nginx_allows_lesson_prep_question_bank_and_local_vendor_assets():
    config_path = os.path.join(ROOT, "deploy", "admin.shuxue.icu.conf.example")
    with open(config_path, encoding="utf-8") as handle:
        config = handle.read()
    assert "location = /prep.html" in config
    assert "try_files /prep.html =404;" in config
    assert "location = /questions.html" in config
    assert "try_files /questions.html =404;" in config
    assert "location /vendor/" in config

    public_config_path = os.path.join(ROOT, "deploy", "shuxue.icu.conf")
    with open(public_config_path, encoding="utf-8") as handle:
        public_config = handle.read()
    assert "location = /prep.html { return 301 https://admin.shuxue.icu/prep.html; }" in public_config
    assert (
        "location = /questions.html { return 301 https://admin.shuxue.icu/questions.html; }"
        in public_config
    )


def bytes_io(content):
    from io import BytesIO

    return BytesIO(content)
