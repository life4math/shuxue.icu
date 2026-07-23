"""初始化数据库并创建首个管理员账号。"""

import argparse
import getpass

from sqlalchemy import select

from platform_db import SessionLocal, User, init_database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="系统管理员")
    parser.add_argument("--password")
    args = parser.parse_args()

    password = args.password or getpass.getpass("管理员密码: ")
    if len(password) < 12:
        raise SystemExit("密码至少需要 12 个字符")

    init_database()
    db = SessionLocal()
    try:
        email = args.email.strip().lower()
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("该邮箱已存在")
        user = User(email=email, display_name=args.name, role="admin")
        user.set_password(password)
        db.add(user)
        db.commit()
        print(f"管理员已创建: {email}")
    finally:
        SessionLocal.remove()


if __name__ == "__main__":
    main()

