"""初始化数据库并创建首个管理员账号。"""

import argparse
import getpass

from sqlalchemy import select

from platform_db import SessionLocal, User, init_database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name")
    parser.add_argument("--password")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="邮箱已存在时更新密码（用于重置密码）",
    )
    args = parser.parse_args()

    password = args.password or getpass.getpass("管理员密码: ")
    if len(password) < 12:
        raise SystemExit("密码至少需要 12 个字符")

    init_database()
    db = SessionLocal()
    try:
        email = args.email.strip().lower()
        user = db.scalar(select(User).where(User.email == email))
        if user and not args.reset:
            raise SystemExit("该邮箱已存在。若需重置密码请加 --reset。")

        if user:
            user.set_password(password)
            if args.name:
                user.display_name = args.name
        else:
            display_name = args.name or "系统管理员"
            user = User(email=email, display_name=display_name, role="admin")
            user.set_password(password)
            db.add(user)
        db.commit()
        if args.reset:
            print(f"管理员口令已重置: {email}")
        else:
            print(f"管理员已创建: {email}")
    finally:
        SessionLocal.remove()


if __name__ == "__main__":
    main()
