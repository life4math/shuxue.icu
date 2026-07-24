#!/usr/bin/env python3
"""部署前完整性校验。

目的：拦截"文件被写坏"这一类问题（例如源码文件被截断、填入乱码二进制、
或含 NUL 空字节），避免损坏的文件被自动部署到生产站点。

检查项：
  1. 所有受 Git 跟踪的源码文本文件均为合法 UTF-8，且不含 NUL 空字节。
  2. 关键前端文件结构完整（包含预期的结构标记，未被截断）。

任一检查失败即以非零码退出，供 CI / 部署脚本据此中止部署。
用法： python3 deploy/check_integrity.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 需要校验的源码文本类型
TEXT_SUFFIXES = {
    ".html", ".js", ".css", ".py", ".json",
    ".md", ".conf", ".service", ".sh", ".txt", ".yml", ".yaml",
    ".ini", ".mako", ".lock",
}
# 第三方压缩资源跳过（本身即最小化文本，不在维护范围）
SKIP_NAME_SUFFIXES = (".min.js", ".min.css")

# 关键文件必须包含的结构标记（缺失说明可能被截断/损坏）
STRUCTURE_CHECKS = {
    "website/index.html": ["<!DOCTYPE html", "</html>", 'src="js/app.js'],
    "website/js/app.js": ["function initPage"],
    "website/css/style.css": [":root"],
    "requirements-py38.lock": ["--hash=sha256:"],
    "requirements-py311.lock": ["--hash=sha256:"],
    "website/data/demo-content.json": ['"questions"', '"methods"'],
    "website/data/knowledge-content.json": ['"FUNC-01-01"'],
}

FORBIDDEN_RUNTIME_PATTERNS = {
    "website/scripts/server.py": ["runInNewContext", "write_data_js"],
    "website/scripts/seed_knowledge.py": ["runInNewContext", "subprocess"],
    "website/scripts/ingest.py": ["data.js", "write_text("],
}


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def main():
    errors = []

    for rel in tracked_files():
        name = rel.rsplit("/", 1)[-1]
        if name.endswith(SKIP_NAME_SUFFIXES):
            continue
        suffix = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
        if suffix not in TEXT_SUFFIXES:
            continue
        path = ROOT / rel
        if not path.exists():
            continue
        data = path.read_bytes()
        if b"\x00" in data:
            errors.append(f"{rel}: 含 NUL 空字节（疑似文件损坏）")
            continue
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{rel}: 非法 UTF-8 @字节 {exc.start}（疑似文件损坏）")

    for rel, needles in STRUCTURE_CHECKS.items():
        path = ROOT / rel
        if not path.exists():
            errors.append(f"{rel}: 关键文件缺失")
            continue
        try:
            text = path.read_text("utf-8")
        except UnicodeDecodeError:
            # 上面已报过 UTF-8 错误，这里不重复
            continue
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel}: 缺少预期结构标记 {needle!r}（可能被截断或损坏）")

    for rel, forbidden in FORBIDDEN_RUNTIME_PATTERNS.items():
        text = (ROOT / rel).read_text("utf-8")
        for needle in forbidden:
            if needle in text:
                errors.append(f"{rel}: 仍含已停用的可执行静态数据路径 {needle!r}")

    if errors:
        print("[ERROR] 完整性校验未通过：", file=sys.stderr)
        for item in errors:
            print("   -", item, file=sys.stderr)
        sys.exit(1)

    print("[OK] 完整性校验通过：所有源码文本文件为合法 UTF-8，关键前端文件结构完整。")


if __name__ == "__main__":
    main()
