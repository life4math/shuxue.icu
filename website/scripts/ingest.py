#!/usr/bin/env python3
"""把本地文件安全加入正式 AI 数据库队列。

旧版脚本会解析并重写公开 JavaScript 数据；该路径已经停用。现在所有
可写任务都进入 SQLAlchemy 数据库，由 ``shuxue-worker`` 统一处理。

用法：
  python ingest.py --email teacher@example.com /path/a.pdf /path/b.docx
"""

import argparse
import hashlib
import json
import mimetypes
import shutil
import uuid
from pathlib import Path

from sqlalchemy import select

from platform_db import AIJob, SessionLocal, UploadFile, User, init_database


UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_user(db, email):
    if email:
        return db.scalar(
            select(User).where(
                User.email == email.strip().lower(),
                User.is_active.is_(True),
            )
        )
    return db.scalar(
        select(User)
        .where(User.is_active.is_(True), User.role.in_(("admin", "teacher")))
        .order_by(User.created_at)
    )


def enqueue_file(db, owner, source):
    source = source.resolve()
    if not source.is_file():
        raise ValueError(f"文件不存在: {source}")
    suffix = source.suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件类型: {source.name}")
    size = source.stat().st_size
    if size <= 0 or size > MAX_FILE_SIZE:
        raise ValueError(f"文件大小必须在 1 字节到 50MB 之间: {source.name}")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / stored_name
    shutil.copy2(source, destination)

    try:
        upload = UploadFile(
            owner_id=owner.id,
            original_name=source.name[:255],
            stored_name=stored_name,
            sha256=sha256_file(destination),
            content_type=mimetypes.guess_type(source.name)[0] or "application/octet-stream",
            size=size,
        )
        db.add(upload)
        db.flush()
        job = AIJob(upload_id=upload.id, owner_id=owner.id)
        db.add(job)
        db.flush()
        return {
            "upload_id": upload.id,
            "job_id": job.id,
            "name": source.name,
            "stored_name": stored_name,
        }
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="将文件加入 shuxue AI 数据库队列")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--email", help="任务所属的启用教师或管理员账号")
    args = parser.parse_args()

    init_database()
    db = SessionLocal()
    copied = []
    try:
        owner = choose_user(db, args.email)
        if not owner:
            raise SystemExit("没有可用账号，请先创建启用的教师或管理员")
        for source in args.files:
            copied.append(enqueue_file(db, owner, source))
        db.commit()
        print(json.dumps({"queued": copied}, ensure_ascii=False))
    except Exception:
        db.rollback()
        for item in copied:
            (UPLOAD_DIR / item["stored_name"]).unlink(missing_ok=True)
        raise
    finally:
        SessionLocal.remove()


if __name__ == "__main__":
    main()
