"""处理排队中的 AI 提取任务；可由 systemd 常驻运行。"""

import time
from pathlib import Path

from sqlalchemy import select

from platform_db import AIJob, ReviewItem, SessionLocal, UploadFile, init_database, utcnow
from server import process_file


UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"


def process_next_job():
    db = SessionLocal()
    try:
        job = db.scalar(select(AIJob).where(AIJob.status == "queued").order_by(AIJob.created_at).limit(1))
        if not job:
            return False
        job.status = "parsing"
        job.progress = 10
        job.started_at = utcnow()
        job.attempt_count += 1
        job.upload.status = "processing"
        db.commit()

        path = UPLOAD_DIR / job.upload.stored_name
        try:
            job.status = "extracting"
            job.progress = 35
            db.commit()
            extracted = process_file(str(path), job.upload.original_name)
            job.status = "validating"
            job.progress = 75
            db.commit()

            for item in extracted:
                payload = dict(item.get("data") or {})
                entity_type = "method" if payload.pop("methodType", None) == "method" else "question"
                db.add(
                    ReviewItem(
                        job_id=job.id,
                        entity_type=entity_type,
                        payload=payload,
                        ai_confidence=round(float(item.get("aiConfidence", 0)) * 100),
                    )
                )
            job.status = "pending_review"
            job.progress = 100
            job.finished_at = utcnow()
            job.upload.status = "processed"
            db.commit()
        except Exception as exc:
            db.rollback()
            job = db.get(AIJob, job.id)
            job.status = "failed"
            job.error_message = str(exc)[:2000]
            job.finished_at = utcnow()
            upload = db.get(UploadFile, job.upload_id)
            upload.status = "failed"
            db.commit()
        return True
    finally:
        SessionLocal.remove()


def main():
    init_database()
    while True:
        if not process_next_job():
            time.sleep(2)


if __name__ == "__main__":
    main()
