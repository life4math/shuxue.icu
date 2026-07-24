"""可靠处理排队中的 AI 提取任务；由 systemd 常驻运行。"""

import os
import logging
import signal
import time
from datetime import timedelta
from pathlib import Path

from sqlalchemy import or_, select

from platform_db import AIJob, ReviewItem, SessionLocal, UploadFile, init_database, utcnow
from server import process_file


UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
ACTIVE_STATUSES = ("parsing", "extracting", "validating")
LOGGER = logging.getLogger("shuxue.worker")
stop_requested = False


def positive_env_int(name, default):
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except ValueError:
        LOGGER.warning("环境变量 %s 不是正整数，使用默认值 %s", name, default)
        return default


MAX_ATTEMPTS = positive_env_int("SHUXUE_AI_MAX_ATTEMPTS", 3)
RETRY_BASE_SECONDS = positive_env_int("SHUXUE_AI_RETRY_BASE_SECONDS", 30)
POLL_SECONDS = positive_env_int("SHUXUE_AI_POLL_SECONDS", 2)


def request_stop(_signum, _frame):
    global stop_requested
    stop_requested = True


def recover_interrupted_jobs():
    """单实例 Worker 重启后，恢复上次被中断的任务。"""
    db = SessionLocal()
    try:
        rows = db.scalars(select(AIJob).where(AIJob.status.in_(ACTIVE_STATUSES))).all()
        now = utcnow()
        for job in rows:
            upload = db.get(UploadFile, job.upload_id)
            if job.attempt_count >= MAX_ATTEMPTS:
                job.status = "failed"
                job.finished_at = now
                if upload:
                    upload.status = "failed"
            else:
                job.status = "queued"
                job.progress = 0
                job.next_attempt_at = now
                job.finished_at = None
                if upload:
                    upload.status = "queued"
            job.heartbeat_at = None
            job.error_message = "Worker 重启，任务已自动恢复"
        if rows:
            db.commit()
            LOGGER.warning("Worker 启动时恢复了 %s 个中断任务", len(rows))
        return len(rows)
    finally:
        SessionLocal.remove()


def claim_next_job(db):
    now = utcnow()
    job = db.scalar(
        select(AIJob)
        .where(
            AIJob.status == "queued",
            or_(AIJob.next_attempt_at.is_(None), AIJob.next_attempt_at <= now),
        )
        .order_by(AIJob.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not job:
        return None
    job.status = "parsing"
    job.progress = 10
    job.started_at = now
    job.heartbeat_at = now
    job.next_attempt_at = None
    job.attempt_count += 1
    job.upload.status = "processing"
    db.commit()
    LOGGER.info("开始处理任务 %s，第 %s 次尝试", job.id, job.attempt_count)
    return job


def set_progress(db, job, status, progress):
    job.status = status
    job.progress = progress
    job.heartbeat_at = utcnow()
    db.commit()


def schedule_failure(db, job_id, message):
    job = db.get(AIJob, job_id)
    if not job:
        return
    now = utcnow()
    job.error_message = message[:2000]
    job.heartbeat_at = None
    upload = db.get(UploadFile, job.upload_id)
    if job.attempt_count < MAX_ATTEMPTS:
        delay = RETRY_BASE_SECONDS * (2 ** max(0, job.attempt_count - 1))
        job.status = "queued"
        job.progress = 0
        job.next_attempt_at = now + timedelta(seconds=delay)
        job.finished_at = None
        if upload:
            upload.status = "queued"
        LOGGER.warning("任务 %s 处理失败，%s 秒后自动重试：%s", job.id, delay, message)
    else:
        job.status = "failed"
        job.finished_at = now
        job.next_attempt_at = None
        if upload:
            upload.status = "failed"
        LOGGER.error("任务 %s 已达到最大尝试次数，处理失败：%s", job.id, message)
    db.commit()


def process_next_job():
    db = SessionLocal()
    try:
        job = claim_next_job(db)
        if not job:
            return False
        job_id = job.id
        path = UPLOAD_DIR / job.upload.stored_name
        try:
            if not path.is_file():
                raise FileNotFoundError(f"上传文件不存在: {job.upload.original_name}")
            set_progress(db, job, "extracting", 35)
            extracted = process_file(str(path), job.upload.original_name)
            if not isinstance(extracted, list) or not extracted:
                raise ValueError("AI 未返回可审核内容")
            set_progress(db, job, "validating", 75)

            for item in extracted:
                payload = dict(item.get("data") or {})
                if not payload:
                    raise ValueError("AI 返回了空内容")
                entity_type = "method" if payload.pop("methodType", None) == "method" else "question"
                confidence = round(float(item.get("aiConfidence", 0)) * 100)
                db.add(
                    ReviewItem(
                        job_id=job.id,
                        entity_type=entity_type,
                        payload=payload,
                        ai_confidence=max(0, min(100, confidence)),
                    )
                )
            job.status = "pending_review"
            job.progress = 100
            job.heartbeat_at = None
            job.next_attempt_at = None
            job.finished_at = utcnow()
            job.error_message = None
            job.upload.status = "processed"
            db.commit()
            LOGGER.info("任务 %s 已完成，生成 %s 条待审核内容", job.id, len(extracted))
        except Exception as exc:
            db.rollback()
            schedule_failure(db, job_id, str(exc))
        return True
    finally:
        SessionLocal.remove()


def main():
    logging.basicConfig(
        level=os.environ.get("SHUXUE_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    init_database()
    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    recover_interrupted_jobs()
    while not stop_requested:
        if not process_next_job():
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
