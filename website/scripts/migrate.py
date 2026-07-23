#!/usr/bin/env python3
"""执行正式数据库迁移。"""

from pathlib import Path
import sys

from alembic import command
from alembic.config import Config


ROOT = Path(__file__).resolve().parents[2]


def main():
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    command.upgrade(config, "head")
    print("[OK] 数据库迁移已升级到 head")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] 数据库迁移失败: {exc}", file=sys.stderr)
        raise
