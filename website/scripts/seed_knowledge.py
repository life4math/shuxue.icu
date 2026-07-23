"""将前端知识正文一次性导入正式数据库。

用法：
  python seed_knowledge.py --email 87707817@qq.com

默认以 published 导入现有静态正文，后续修改应通过教师后台完成。
"""

import argparse
import json
import subprocess
from pathlib import Path

from sqlalchemy import select

from platform_db import KnowledgeDocument, PublishedKnowledge, SessionLocal, User, init_database, utcnow


SCRIPT_DIR = Path(__file__).resolve().parent
CONTENT_PATH = SCRIPT_DIR.parent / "js" / "knowledge-content.js"


def read_static_content():
    source = CONTENT_PATH.read_text(encoding="utf-8")
    source = source.replace("const knowledgeDetails =", "var knowledgeDetails =", 1)
    node_script = (
        "const vm=require('vm');const s={};"
        "vm.runInNewContext(process.argv[1],s);"
        "process.stdout.write(JSON.stringify(s.knowledgeDetails));"
    )
    result = subprocess.run(
        ["node", "-e", node_script, source],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=15,
    )
    return json.loads(result.stdout)


def seed_contents(db, user, contents, status="published", bootstrap_missing=False):
    created = 0
    updated = 0
    skipped = 0
    for node_id, payload in contents.items():
        item = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.node_id == node_id))
        snapshot = db.get(PublishedKnowledge, node_id)
        if bootstrap_missing and item:
            if item.status == "published" and not snapshot:
                snapshot = PublishedKnowledge(
                    node_id=node_id,
                    title=item.title,
                    version=item.version,
                    payload=item.payload,
                    published_by=item.published_by,
                    published_at=item.published_at or item.updated_at or item.created_at,
                )
                db.add(snapshot)
                updated += 1
            else:
                skipped += 1
            continue

        if item:
            item.title = payload["title"]
            item.payload = payload
            item.status = status
            item.updated_by = user.id
            if status == "published":
                item.published_by = user.id
                item.published_at = utcnow()
            updated += 1
        else:
            item = KnowledgeDocument(
                node_id=node_id,
                title=payload["title"],
                payload=payload,
                status=status,
                version=1,
                created_by=user.id,
                updated_by=user.id,
                published_by=user.id if status == "published" else None,
                published_at=utcnow() if status == "published" else None,
            )
            db.add(item)
            created += 1
        if status == "published":
            if not snapshot:
                snapshot = PublishedKnowledge(node_id=node_id)
                db.add(snapshot)
            snapshot.title = payload["title"]
            snapshot.version = item.version or 1
            snapshot.payload = payload
            snapshot.published_by = user.id
            snapshot.published_at = item.published_at or utcnow()
    return {"created": created, "updated": updated, "skipped": skipped, "total": len(contents)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", help="已有管理员账号邮箱；省略时自动选择首个启用的管理员")
    parser.add_argument("--status", choices=["draft", "published"], default="published")
    parser.add_argument(
        "--bootstrap-missing",
        action="store_true",
        help="只补齐不存在的知识点和发布快照，绝不覆盖已有内容",
    )
    args = parser.parse_args()

    init_database()
    contents = read_static_content()
    db = SessionLocal()
    try:
        user = None
        if args.email:
            user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        else:
            user = db.scalar(
                select(User)
                .where(User.role == "admin", User.is_active.is_(True))
                .order_by(User.created_at)
            )
        if not user:
            if args.bootstrap_missing:
                print(json.dumps({"created": 0, "updated": 0, "skipped": len(contents), "reason": "no active admin"}))
                return
            raise SystemExit("指定邮箱不存在或没有启用的管理员，请先运行 init_platform.py")
        result = seed_contents(db, user, contents, args.status, args.bootstrap_missing)
        db.commit()
        print(json.dumps(result, ensure_ascii=False))
    finally:
        SessionLocal.remove()


if __name__ == "__main__":
    main()
