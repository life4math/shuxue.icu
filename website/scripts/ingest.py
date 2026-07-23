#!/usr/bin/env python3
"""
shuxue.icu 入库脚本 — 从原始素材到结构化题库/方法库
===================================================

支持三种输入:
  1. 图片文件 (.png/.jpg/.jpeg) → Vision AI 识别 + LaTeX 提取
  2. PDF 文件 (.pdf) → pdfplumber 提取文本 + LLM 结构化
  3. Word 文件 (.docx) → mammoth 转 HTML + LLM 结构化
  4. 纯文本/Markdown (.txt/.md) → 直接 LLM 结构化

输出:
  - review_queue.json — AI 提取结果，需人工审核后合并到 data.js

依赖安装:
  pip install pdfplumber mammoth Pillow

Vision AI / LLM 调用需配置 API key（环境变量或 config.json）
"""

import os
import sys
import json
import re
import hashlib
import datetime
from pathlib import Path

# ─── 配置 ────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
WEBSITE_DIR = SCRIPT_DIR.parent  # website/
DATA_JS_PATH = WEBSITE_DIR / "js" / "data.js"
INGEST_DIR = SCRIPT_DIR / "ingest"  # 存放待处理的原始素材
OUTPUT_DIR = SCRIPT_DIR / "output"  # 存放审核队列 JSON

# 支持的文件类型
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
PDF_EXTS = {".pdf"}
DOC_EXTS = {".docx", ".doc"}
TEXT_EXTS = {".txt", ".md", ".markdown"}

# ─── ID 生成 ─────────────────────────────────────────────────────
_counter = {"Q": 0, "M": 0, "R": 0}

def load_existing_ids():
    """从 data.js 加载已有的题目和方法 ID"""
    if not DATA_JS_PATH.exists():
        return set()
    content = DATA_JS_PATH.read_text(encoding="utf-8")
    ids = set()
    for match in re.finditer(r'id:\s*"(Q\d+|M\d+)"', content):
        ids.add(match.group(1))
    # 找最大编号
    for id_str in ids:
        prefix = id_str[0]
        num = int(id_str[1:])
        _counter[prefix] = max(_counter[prefix], num)
    return ids

def next_id(prefix):
    _counter[prefix] += 1
    return f"{prefix}{_counter[prefix]:03d}"

# ─── LLM 调用 ────────────────────────────────────────────────────
# 两种模式:
#   A) 使用 OpenAI-compatible API（需要 OPENAI_API_KEY）
#   B) 使用本地文件模拟（测试/无 API 时）

def call_llm(prompt, image_path=None):
    """
    调用 LLM 进行结构化提取。
    如果有 image_path，使用 Vision 模式（多模态）。
    如果没有 API key，输出提示信息并返回模拟结果。
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    api_base = os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
    model = os.environ.get("SHUXUE_LLM_MODEL", "gpt-4o")

    if not api_key:
        print("[!] 未配置 OPENAI_API_KEY，将使用本地模拟模式")
        print("[!] 请设置环境变量: export OPENAI_API_KEY=sk-xxx")
        print("[!] 或创建 scripts/config.json 填入 API 配置")
        return _mock_llm_response(prompt)

    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url=api_base)

        messages = [{"role": "user", "content": []}]

        # 如果有图片，附加到消息
        if image_path and Path(image_path).exists():
            import base64
            img_data = base64.b64encode(Path(image_path).read_bytes()).decode()
            ext = Path(image_path).suffix.lower().lstrip(".")
            mime = f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{img_data}"}
            })

        messages[0]["content"].append({"type": "text", "text": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)

    except ImportError:
        print("[!] openai 库未安装，请执行: pip install openai")
        return _mock_llm_response(prompt)
    except Exception as e:
        print(f"[!] LLM 调用失败: {e}")
        return _mock_llm_response(prompt)


QUESTION_EXTRACT_PROMPT = """你是一个高考数学题目提取专家。请从以下内容中提取所有数学题目，返回 JSON 格式。

每个题目的格式:
{
  "questions": [
    {
      "module": "FUNC/GEOM/ALGE/PROB/CALC 之一",
      "knowledge_points": ["知识点ID，如 FUNC-02-02-01"],
      "difficulty": 1-5,
      "type": "choice/fill/solve/proof",
      "stem": "题干（数学公式用 LaTeX $...$ 格式）",
      "options": [{"label":"A","content":"$...$"}, ...],  // 选择题才有
      "answer": "答案（选择题给字母，填空题给值，解答题给简要结果）",
      "analysis": "解析（关键步骤，公式用 LaTeX）",
      "tags": ["标签1", "标签2"],
      "source": {"type": "真题/模拟/教案/自编", "year": 2024, "region": "全国I卷（可选）"}
    }
  ]
}

知识点 ID 对照:
- FUNC: 函数与导数 (FUNC-01~05)
- GEOM: 几何与向量 (GEOM-01~03)
- ALGE: 代数与不等式 (ALGE-01~03)
- PROB: 概率与统计 (PROB-01~02)
- CALC: 微积分初步 (CALC-01)

难度: 1=基础, 2=简单, 3=中等, 4=较难, 5=困难
题型: choice=选择题, fill=填空题, solve=解答题, proof=证明题

原始内容:
"""

METHOD_EXTRACT_PROMPT = """你是一个高考数学方法提炼专家。请从以下内容中提取解题方法和套路，返回 JSON 格式。

每个方法的格式:
{
  "methods": [
    {
      "name": "方法名称",
      "category": "方法分类（如：数列求和/不等式证明/圆锥曲线/...）",
      "module": "FUNC/GEOM/ALGE/PROB/CALC",
      "knowledge_points": ["关联知识点ID"],
      "applicable_types": ["适用的题型: choice/fill/solve/proof"],
      "difficulty_range": [3, 5],
      "keywords": ["关键词1", "关键词2"],
      "principle": "方法原理的一句话概括",
      "steps": ["步骤1", "步骤2", ...],
      "common_forms": ["常见形式/模板公式"],
      "pitfalls": ["易错点1", "易错点2"]
    }
  ]
}

原始内容:
"""


def _mock_llm_response(prompt):
    """无 API 时返回模拟数据，便于测试流程"""
    if "题目提取" in prompt or "question" in prompt.lower():
        return {
            "questions": [{
                "module": "FUNC",
                "knowledge_points": ["FUNC-02-02-01"],
                "difficulty": 3,
                "type": "choice",
                "stem": "[模拟数据] 请配置 OPENAI_API_KEY 后重新运行",
                "options": [{"label": "A", "content": "$1$"}, {"label": "B", "content": "$2$"}],
                "answer": "A",
                "analysis": "模拟解析",
                "tags": ["模拟"],
                "source": {"type": "自编"}
            }]
        }
    elif "方法提炼" in prompt or "method" in prompt.lower():
        return {
            "methods": [{
                "name": "[模拟] 裂项相消法",
                "category": "数列求和",
                "module": "FUNC",
                "knowledge_points": ["FUNC-04-04"],
                "applicable_types": ["fill", "solve"],
                "difficulty_range": [3, 5],
                "keywords": ["数列", "求和"],
                "principle": "通项拆分为两项之差，中间项抵消",
                "steps": ["识别结构", "拆分", "展开", "抵消", "写结果"],
                "common_forms": ["$\\frac{1}{n(n+1)} = \\frac{1}{n} - \\frac{1}{n+1}$"],
                "pitfalls": ["系数遗漏"]
            }]
        }
    return {"error": "unknown prompt type"}

# ─── 文档解析 ────────────────────────────────────────────────────

def parse_pdf(pdf_path):
    """从 PDF 提取文本段落"""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts)
    except ImportError:
        print("[!] pdfplumber 未安装，请执行: pip install pdfplumber")
        # fallback: 尝试读取原始文本
        return Path(pdf_path).read_text(encoding="utf-8", errors="ignore")

def parse_docx(docx_path):
    """从 Word 文档提取 HTML，再转为纯文本"""
    try:
        import mammoth
        with open(docx_path, "rb") as f:
            result = mammoth.convert_to_html(f)
            html = result.value
        # 简易 HTML → text（保留公式标记）
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'&nbsp;', ' ', text)
        return text
    except ImportError:
        print("[!] mammoth 未安装，请执行: pip install mammoth")
        return f"[无法解析 {docx_path}]"

def parse_text(text_path):
    """直接读取纯文本/Markdown"""
    return Path(text_path).read_text(encoding="utf-8")

# ─── 入库流程 ────────────────────────────────────────────────────

def process_file(filepath):
    """
    处理单个文件，返回审核队列条目列表
    """
    path = Path(filepath)
    ext = path.suffix.lower()
    print(f"\n> PROCESSING: {path.name}")
    print(f"  TYPE: {ext}")

    review_items = []

    if ext in IMAGE_EXTS:
        # 图片 → Vision AI 直接识别
        content = ""  # 图片由 Vision 模式直接处理
        prompt = QUESTION_EXTRACT_PROMPT + f"[图片文件: {path.name}]"
        result = call_llm(prompt, image_path=str(path))

        if "questions" in result:
            for q in result["questions"]:
                rid = next_id("R")
                review_items.append({
                    "id": rid,
                    "status": "pending",
                    "source": "image_ocr",
                    "sourceFile": path.name,
                    "extractedAt": datetime.datetime.now().isoformat(),
                    "data": q,
                    "aiConfidence": 0.85,  # 默认置信度
                    "reviewNotes": ""
                })
                print(f"  + QUESTION {rid}: {q.get('stem', '')[:50]}...")

        # 同时尝试提取方法
        method_prompt = METHOD_EXTRACT_PROMPT + f"[图片文件: {path.name}]"
        method_result = call_llm(method_prompt, image_path=str(path))
        if "methods" in method_result:
            for m in method_result["methods"]:
                rid = next_id("R")
                review_items.append({
                    "id": rid,
                    "status": "pending",
                    "source": "image_ocr",
                    "sourceFile": path.name,
                    "extractedAt": datetime.datetime.now().isoformat(),
                    "data": {"methodType": "method", **m},
                    "aiConfidence": 0.80,
                    "reviewNotes": ""
                })
                print(f"  + METHOD {rid}: {m.get('name', '')}")

    elif ext in PDF_EXTS:
        content = parse_pdf(str(path))
        if content.strip():
            # 分段送 LLM（避免过长）
            chunks = _split_content(content, max_chars=2000)
            for chunk in chunks:
                prompt = QUESTION_EXTRACT_PROMPT + chunk
                result = call_llm(prompt)
                if "questions" in result:
                    for q in result["questions"]:
                        rid = next_id("R")
                        review_items.append({
                            "id": rid, "status": "pending",
                            "source": "pdf_parse",
                            "sourceFile": path.name,
                            "extractedAt": datetime.datetime.now().isoformat(),
                            "data": q, "aiConfidence": 0.88,
                            "reviewNotes": ""
                        })
                        print(f"  + QUESTION {rid}: {q.get('stem', '')[:50]}...")

                # 方法提取
                m_prompt = METHOD_EXTRACT_PROMPT + chunk
                m_result = call_llm(m_prompt)
                if "methods" in m_result:
                    for m in m_result["methods"]:
                        rid = next_id("R")
                        review_items.append({
                            "id": rid, "status": "pending",
                            "source": "pdf_parse",
                            "sourceFile": path.name,
                            "extractedAt": datetime.datetime.now().isoformat(),
                            "data": {"methodType": "method", **m},
                            "aiConfidence": 0.82,
                            "reviewNotes": ""
                        })

    elif ext in DOC_EXTS:
        content = parse_docx(str(path))
        if content.strip():
            prompt = QUESTION_EXTRACT_PROMPT + content[:3000]
            result = call_llm(prompt)
            if "questions" in result:
                for q in result["questions"]:
                    rid = next_id("R")
                    review_items.append({
                        "id": rid, "status": "pending",
                        "source": "docx_parse",
                        "sourceFile": path.name,
                        "extractedAt": datetime.datetime.now().isoformat(),
                        "data": q, "aiConfidence": 0.90,
                        "reviewNotes": ""
                    })

            m_prompt = METHOD_EXTRACT_PROMPT + content[:3000]
            m_result = call_llm(m_prompt)
            if "methods" in m_result:
                for m in m_result["methods"]:
                    rid = next_id("R")
                    review_items.append({
                        "id": rid, "status": "pending",
                        "source": "docx_parse",
                        "sourceFile": path.name,
                        "extractedAt": datetime.datetime.now().isoformat(),
                        "data": {"methodType": "method", **m},
                        "aiConfidence": 0.85,
                        "reviewNotes": ""
                    })

    elif ext in TEXT_EXTS:
        content = parse_text(str(path))
        prompt = QUESTION_EXTRACT_PROMPT + content[:4000]
        result = call_llm(prompt)
        if "questions" in result:
            for q in result["questions"]:
                rid = next_id("R")
                review_items.append({
                    "id": rid, "status": "pending",
                    "source": "text_parse",
                    "sourceFile": path.name,
                    "extractedAt": datetime.datetime.now().isoformat(),
                    "data": q, "aiConfidence": 0.93,
                    "reviewNotes": ""
                })

    else:
        print(f"  [!] 不支持的文件类型: {ext}")

    return review_items


def _split_content(content, max_chars=2000):
    """按段落分割长文本，避免超出 LLM 上下文"""
    paragraphs = content.split("\n\n")
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) > max_chars:
            if current:
                chunks.append(current)
            current = p
        else:
            current += "\n\n" + p
    if current:
        chunks.append(current)
    return chunks

# ─── 批量处理 ────────────────────────────────────────────────────

def batch_process(input_dir=None):
    """
    扫描输入目录，处理所有文件，输出审核队列 JSON
    """
    load_existing_ids()

    if input_dir:
        scan_dir = Path(input_dir)
    else:
        scan_dir = INGEST_DIR
        if not scan_dir.exists():
            scan_dir.mkdir(parents=True)
            print(f"[+] 创建素材目录: {scan_dir}")
            print(f"[+] 请将待处理的文件放入该目录后重新运行")
            # 创建示例配置文件
            config_path = SCRIPT_DIR / "config.json"
            if not config_path.exists():
                config_path.write_text(json.dumps({
                    "openai_api_key": "",
                    "openai_api_base": "https://api.openai.com/v1",
                    "model": "gpt-4o",
                    "max_chunk_chars": 2000
                }, indent=2, ensure_ascii=False))
                print(f"[+] 创建配置文件: {config_path}")
                print(f"[+] 请在 config.json 中填入 API key")
            return []

    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True)

    all_review_items = []

    # 加载已有的审核队列（追加模式）
    existing_queue_path = OUTPUT_DIR / "review_queue.json"
    if existing_queue_path.exists():
        existing = json.loads(existing_queue_path.read_text(encoding="utf-8"))
        all_review_items.extend(existing)
        print(f"[+] 加载已有审核队列: {len(existing)} 条")

    # 扫描文件
    files = sorted(scan_dir.iterdir())
    supported = [f for f in files if f.suffix.lower() in (IMAGE_EXTS | PDF_EXTS | DOC_EXTS | TEXT_EXTS)]

    if not supported:
        print("[!] 素材目录中没有可处理的文件")
        print(f"[!] 支持的格式: {', '.join(sorted(IMAGE_EXTS | PDF_EXTS | DOC_EXTS | TEXT_EXTS))}")
        return []

    print(f"[+] 发现 {len(supported)} 个可处理文件")

    for filepath in supported:
        items = process_file(filepath)
        all_review_items.extend(items)

    # 写入审核队列
    existing_queue_path.write_text(
        json.dumps(all_review_items, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n[+] 审核队列已写入: {existing_queue_path}")
    print(f"[+] 共 {len(all_review_items)} 条待审核")

    # 同步到 data.js 的 reviewQueue
    _sync_review_queue_to_data_js(all_review_items)

    return all_review_items


def _sync_review_queue_to_data_js(review_items):
    """
    将审核队列数据同步写入 data.js 的 reviewQueue 数组
    """
    if not DATA_JS_PATH.exists():
        print("[!] data.js 不存在，跳过同步")
        return

    content = DATA_JS_PATH.read_text(encoding="utf-8")

    # 生成新的 reviewQueue 数组文本
    js_entries = []
    for item in review_items:
        js_entries.append(json.dumps(item, indent=2, ensure_ascii=False))

    new_review_text = "const reviewQueue = [\n" + ",\n".join(js_entries) + "\n];"

    # 替换现有的 reviewQueue
    pattern = r"const reviewQueue\s*=\s*\[.*?\];"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new_review_text + content[match.end():]
    else:
        # 如果没有 reviewQueue，在 methods 后面插入
        methods_end = content.find("// --- 工具函数 ---")
        if methods_end > 0:
            content = content[:methods_end] + new_review_text + "\n\n" + content[methods_end:]
        else:
            content += "\n\n" + new_review_text

    DATA_JS_PATH.write_text(content, encoding="utf-8")
    print(f"[+] reviewQueue 已同步到 data.js")


def approve_review_item(item_id):
    """审核通过：将审核队列条目合并到正式题库/方法库"""
    load_existing_ids()

    existing_queue_path = OUTPUT_DIR / "review_queue.json"
    if not existing_queue_path.exists():
        print("[!] 审核队列不存在")
        return

    queue = json.loads(existing_queue_path.read_text(encoding="utf-8"))
    target = None
    for item in queue:
        if item["id"] == item_id and item["status"] == "pending":
            target = item
            break

    if not target:
        print(f"[!] 未找到待审核条目: {item_id}")
        return

    data = target["data"]
    is_method = data.get("methodType") == "method"

    if is_method:
        # 合入方法库
        mid = next_id("M")
        method_entry = {k: v for k, v in data.items() if k != "methodType"}
        method_entry["id"] = mid
        if not method_entry.get("examples"):
            method_entry["examples"] = []

        content = DATA_JS_PATH.read_text(encoding="utf-8")
        # 在 methods 数组末尾插入
        methods_end_pattern = r"(const methods\s*=\s*\[.*?\];)"
        match = re.search(methods_end_pattern, content, re.DOTALL)
        if match:
            # 找到数组最后的 ]
            arr_text = match.group(1)
            insert_pos = arr_text.rfind("]")
            new_entry_js = json.dumps(method_entry, indent=2, ensure_ascii=False)
            new_arr = arr_text[:insert_pos] + ",\n  " + new_entry_js + arr_text[insert_pos:]
            content = content[:match.start()] + new_arr + content[match.end():]
    else:
        # 合入题目库
        qid = next_id("Q")
        data["id"] = qid
        data["status"] = "approved"
        if not data.get("stats"):
            data["stats"] = {"total": 0, "correct": 0, "accuracy": 0}

        content = DATA_JS_PATH.read_text(encoding="utf-8")
        questions_end_pattern = r"(const questions\s*=\s*\[.*?\];)"
        match = re.search(questions_end_pattern, content, re.DOTALL)
        if match:
            arr_text = match.group(1)
            insert_pos = arr_text.rfind("]")
            new_entry_js = json.dumps(data, indent=2, ensure_ascii=False)
            new_arr = arr_text[:insert_pos] + ",\n  " + new_entry_js + arr_text[insert_pos:]
            content = content[:match.start()] + new_arr + content[match.end():]

    # 更新审核状态
    target["status"] = "approved"
    target["approvedAt"] = datetime.datetime.now().isoformat()
    queue_path_text = json.dumps(queue, indent=2, ensure_ascii=False)
    existing_queue_path.write_text(queue_path_text, encoding="utf-8")

    # 写回 data.js
    DATA_JS_PATH.write_text(content, encoding="utf-8")
    # 同步 reviewQueue
    _sync_review_queue_to_data_js(queue)

    print(f"[+] 审核通过: {item_id} → {'M'+str(_counter['M']) if is_method else 'Q'+str(_counter['Q'])}")

# ─── CLI 入口 ────────────────────────────────────────────────────

def main():
    """命令行入口"""
    import argparse
    parser = argparse.ArgumentParser(description="shuxue.icu 入库脚本")
    parser.add_argument("action", nargs="?", default="process",
                        help="操作: process=批量入库, approve ID=审核通过, status=查看队列状态")
    parser.add_argument("--dir", "-d", help="素材目录路径（默认 scripts/ingest/）")
    parser.add_argument("--file", "-f", help="处理单个文件")

    args = parser.parse_args()

    if args.action == "process":
        if args.file:
            items = process_file(args.file)
            if items:
                output_path = OUTPUT_DIR / "review_queue.json"
                if not OUTPUT_DIR.exists():
                    OUTPUT_DIR.mkdir(parents=True)
                output_path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
                print(f"\n[+] 输出: {output_path}")
                _sync_review_queue_to_data_js(items)
        else:
            batch_process(args.dir)

    elif args.action == "approve":
        if len(sys.argv) < 3:
            print("[!] 请指定审核条目 ID，如: ingest.py approve R001")
            return
        approve_review_item(sys.argv[2])

    elif args.action == "status":
        existing = OUTPUT_DIR / "review_queue.json"
        if existing.exists():
            queue = json.loads(existing.read_text(encoding="utf-8"))
            pending = [i for i in queue if i["status"] == "pending"]
            approved = [i for i in queue if i["status"] == "approved"]
            print(f"审核队列: {len(queue)} 条")
            print(f"  待审核: {len(pending)}")
            print(f"  已通过: {len(approved)}")
            for item in pending[:10]:
                dtype = "METHOD" if item["data"].get("methodType") == "method" else "QUESTION"
                stem = item["data"].get("stem", item["data"].get("name", ""))[:40]
                print(f"  > {item['id']} [{dtype}] {stem}... (confidence: {item['aiConfidence']})")
        else:
            print("[!] 审核队列不存在，请先运行 process")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
