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

from platform_db import KnowledgeDocument, SessionLocal, User, init_database


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
        timeout=15,
    )
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="已有管理员账号邮箱")
    parser.add_argument("--status", choices=["draft", "published"], default="published")
    args = parser.parse_args()

    init_database()
    contents = read_static_content()
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if not user:
            raise SystemExit("指定邮箱不存在，请先运行 init_platform.py")
        created = 0
        updated = 0
        for node_id, payload in contents.items():
            item = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.node_id == node_id))
            if item:
                item.title = payload["title"]
                item.payload = payload
                item.status = args.status
                item.updated_by = user.id
                if args.status == "published":
                    item.published_by = user.id
                updated += 1
                continue
            item = KnowledgeDocument(
                node_id=node_id,
                title=payload["title"],
                payload=payload,
                status=args.status,
                created_by=user.id,
                updated_by=user.id,
                published_by=user.id if args.status == "published" else None,
            )
            db.add(item)
            created += 1
        db.commit()
        print(json.dumps({"created": created, "updated": updated, "total": len(contents)}, ensure_ascii=False))
    finally:
        SessionLocal.remove()


if __name__ == "__main__":
    main()
