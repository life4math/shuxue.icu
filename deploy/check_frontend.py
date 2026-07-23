#!/usr/bin/env python3
"""校验公开前端的 HTML 结构与本地资源引用。"""

import sys
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

    def handle_starttag(self, tag, attrs):
        attr_name = RESOURCE_ATTRIBUTES.get(tag)
        if not attr_name:
            return
        value = dict(attrs).get(attr_name)
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

    if errors:
        print("[ERROR] 前端资源校验未通过：", file=sys.stderr)
        for item in errors:
            print("   -", item, file=sys.stderr)
        raise SystemExit(1)

    print(f"[OK] 前端资源校验通过：已检查 {len(html_files)} 个 HTML 页面。")


if __name__ == "__main__":
    main()
