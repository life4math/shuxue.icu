#!/usr/bin/env python3
"""校验公开前端的 HTML 结构与本地资源引用。"""

import sys
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent.parent
WEBSITE = ROOT / "website"
RESOURCE_ATTRIBUTES = {
    "script": "src",
    "link": "href",
    "img": "src",
    "source": "src",
}


class ResourceParser(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.resources = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.ids.append(element_id)
        attr_name = RESOURCE_ATTRIBUTES.get(tag)
        if not attr_name:
            return
        value = attributes.get(attr_name)
        if value:
            self.resources.append((tag, value))


def local_target(source, reference):
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or reference.startswith("//") or reference.startswith("#"):
        return None
    if parsed.path.startswith("/api/") or not parsed.path:
        return None
    if parsed.path.startswith("/"):
        candidate = WEBSITE / parsed.path.lstrip("/")
    else:
        candidate = source.parent / parsed.path
    return candidate.resolve()


def main():
    errors = []
    html_files = sorted(WEBSITE.glob("*.html"))
    if not html_files:
        errors.append("website/: 未找到 HTML 页面")

    website_root = WEBSITE.resolve()
    for source in html_files:
        parser = ResourceParser(source)
        try:
            parser.feed(source.read_text("utf-8"))
            parser.close()
        except Exception as exc:
            errors.append(f"{source.relative_to(ROOT)}: HTML 无法解析: {exc}")
            continue

        duplicate_ids = [item for item, count in Counter(parser.ids).items() if count > 1]
        for element_id in duplicate_ids:
            errors.append(
                f"{source.relative_to(ROOT)}: id 重复: {element_id}"
            )

        for tag, reference in parser.resources:
            target = local_target(source, reference)
            if target is None:
                continue
            try:
                target.relative_to(website_root)
            except ValueError:
                errors.append(
                    f"{source.relative_to(ROOT)}: <{tag}> 引用越出 website/: {reference}"
                )
                continue
            if not target.is_file():
                errors.append(
                    f"{source.relative_to(ROOT)}: <{tag}> 本地资源不存在: {reference}"
                )

        if source.name == "admin.html":
            admin_js = WEBSITE / "js" / "admin.js"
            referenced_ids = set(
                re.findall(
                    r"""document\.getElementById\(\s*['"]([^'"]+)['"]\s*\)""",
                    admin_js.read_text("utf-8"),
                )
            )
            missing_ids = sorted(referenced_ids - set(parser.ids))
            for element_id in missing_ids:
                errors.append(
                    f"{source.relative_to(ROOT)}: admin.js 引用了不存在的 id: {element_id}"
                )

    if errors:
        print("[ERROR] 前端资源校验未通过：", file=sys.stderr)
        for item in errors:
            print("   -", item, file=sys.stderr)
        raise SystemExit(1)

    print(f"[OK] 前端资源校验通过：已检查 {len(html_files)} 个 HTML 页面。")


if __name__ == "__main__":
    main()
