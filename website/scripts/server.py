#!/usr/bin/env python3
"""
shuxue.icu 后端服务 — 文件上传 + 处理管线 + 审核管理
=====================================================
Flask 轻量后端，提供 RESTful API：
  POST /api/upload        — 上传文件（图片/PDF/Word/文本）
  POST /api/process       — 已下线，改用 /api/v1/admin/jobs
  GET  /api/review        — 已下线，改用 /api/v1/admin/reviews
  GET  /api/schema        — 获取数据格式 Schema
  GET  /api/questions     — 读取公开原型的虚构演示题目
  GET  /api/methods       — 读取公开原型的虚构演示方法
"""

import os
import sys
import json
import re
import hashlib
import hmac
import datetime
import shutil
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, send_file, g
from werkzeug.utils import secure_filename

try:
    import fcntl
except ImportError:  # Windows 开发环境回退；生产 Linux 使用 flock
    fcntl = None

# ─── 配置 ─────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
WEBSITE_DIR = SCRIPT_DIR.parent
DEMO_DATA_PATH = WEBSITE_DIR / "data" / "demo-content.json"
UPLOAD_DIR = WEBSITE_DIR / "uploads"
OUTPUT_DIR = SCRIPT_DIR / "output"
SCHEMA_PATH = SCRIPT_DIR / "schema.json"
CONFIG_PATH = SCRIPT_DIR / "config.json"
DATA_LOCK_PATH = SCRIPT_DIR / ".data.lock"

ALLOWED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".webp",   # 图片
    ".pdf",                                       # PDF
    ".docx", ".doc",                              # Word
    ".txt", ".md", ".markdown",                   # 文本
}

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
_process_write_lock = threading.Lock()

from platform_api import configure_platform

configure_platform(app)


def _admin_token():
    """管理令牌只从环境变量读取，避免意外写入仓库。"""
    return os.environ.get("SHUXUE_ADMIN_TOKEN", "")


def _request_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return request.headers.get("X-Admin-Token", "").strip()


def _is_protected_api():
    if not request.path.startswith("/api/"):
        return False
    # /api/v1 使用教师账号 Session + CSRF，不再复用运维 Token。
    if request.path.startswith("/api/v1/"):
        return False
    return (
        request.method != "GET"
        or request.path == "/api/review"
        or request.path == "/api/uploads-list"
        or request.path.startswith("/api/uploads/")
    )


@app.before_request
def protect_admin_api_and_lock_writes():
    """管理 API 默认拒绝访问，并串行化所有修改请求。"""
    if not _is_protected_api():
        return None

    expected = _admin_token()
    supplied = _request_token()
    if not expected:
        return jsonify({"error": "admin API is not configured"}), 503
    if not supplied or not hmac.compare_digest(supplied, expected):
        return jsonify({"error": "unauthorized"}), 401

    if request.method != "GET":
        _process_write_lock.acquire()
        lock_handle = DATA_LOCK_PATH.open("a+")
        if fcntl is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        g.data_lock_handle = lock_handle
    return None


@app.teardown_request
def release_write_lock(_error=None):
    lock_handle = getattr(g, "data_lock_handle", None)
    if lock_handle is None:
        return
    try:
        if fcntl is not None:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
        lock_handle.close()
    finally:
        _process_write_lock.release()


def resolve_upload_path(filename):
    """只允许 uploads 目录内的单个安全文件名。"""
    if not isinstance(filename, str) or not filename:
        return None
    if filename != Path(filename).name or filename != secure_filename(filename):
        return None
    candidate = (UPLOAD_DIR / filename).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if candidate.parent != upload_root:
        return None
    return candidate

# ─── ID 生成器 ────────────────────────────────────────
_counters = {"Q": 0, "M": 0, "R": 0}

def load_counters():
    if not DEMO_DATA_PATH.exists():
        return
    data = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
    for collection in ("questions", "methods", "reviewQueue"):
        for item in data.get(collection, []):
            item_id = str(item.get("id", ""))
            if re.fullmatch(r"[QMR]\d+", item_id):
                prefix = item_id[0]
                _counters[prefix] = max(_counters[prefix], int(item_id[1:]))

def next_id(prefix):
    _counters[prefix] += 1
    return f"{prefix}{_counters[prefix]:03d}"

load_counters()

# ─── LLM 调用 ────────────────────────────────────────
def get_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}

def call_llm(prompt, image_path=None):
    config = get_config()
    api_key = config.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
    api_base = config.get("openai_api_base", os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1"))
    model = config.get("model", os.environ.get("SHUXUE_LLM_MODEL", "gpt-4o"))

    if not api_key:
        return _mock_response(prompt)

    try:
        import openai
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
        messages = [{"role": "user", "content": []}]

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
            model=model, messages=messages,
            response_format={"type": "json_object"}, temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[!] LLM 调用失败: {e}")
        return _mock_response(prompt)


QUESTION_PROMPT = """你是高考数学题目提取专家。请从以下内容中提取所有数学题目，返回 JSON 格式。

每个题目格式:
{
  "questions": [{
    "module": "FUNC/GEOM/ALGE/PROB/CALC",
    "knowledge_points": ["知识点ID如FUNC-02-02-01"],
    "difficulty": 1-5,
    "type": "choice/fill/solve/proof",
    "stem": "题干（公式用LaTeX $...$）",
    "options": [{"label":"A","content":"$...$"}],
    "answer": "答案",
    "analysis": "解析",
    "tags": ["标签"],
    "source": {"type":"真题/模拟/教案/自编","year":2024,"region":"全国I卷"}
  }]
}

知识点ID: FUNC=函数与导数, GEOM=几何与向量, ALGE=代数与不等式, PROB=概率与统计, CALC=微积分初步
难度: 1=基础, 2=简单, 3=中等, 4=较难, 5=困难
原始内容:\n"""

METHOD_PROMPT = """你是高考数学方法提炼专家。请从以下内容中提取解题方法，返回 JSON 格式。

每个方法格式:
{
  "methods": [{
    "name": "方法名称",
    "category": "分类",
    "module": "FUNC/GEOM/ALGE/PROB/CALC",
    "knowledge_points": ["关联知识点ID"],
    "applicable_types": ["choice/fill/solve/proof"],
    "difficulty_range": [3,5],
    "keywords": ["关键词"],
    "principle": "原理一句话",
    "steps": ["步骤1","步骤2",...],
    "common_forms": ["公式模板"],
    "pitfalls": ["易错点"]
  }]
}

原始内容:\n"""


def _mock_response(prompt):
    """模拟模式：无 API key 时返回模板数据"""
    if "题目提取" in prompt or "question" in prompt.lower():
        return {
            "questions": [{
                "module": "FUNC", "knowledge_points": ["FUNC-02-02-01"],
                "difficulty": 3, "type": "choice",
                "stem": "[模拟] 已知函数 $f(x) = x^2 - 2ax + 3$ 在 $x=1$ 处取极小值，求 $a$",
                "options": [{"label":"A","content":"$1$"}, {"label":"B","content":"$2$"},
                            {"label":"C","content":"$3$"}, {"label":"D","content":"$4$"}],
                "answer": "A", "analysis": "模拟解析",
                "tags": ["模拟", "二次函数"], "source": {"type": "自编"}
            }]
        }
    elif "方法提炼" in prompt or "method" in prompt.lower():
        return {
            "methods": [{
                "name": "[模拟] 配方法", "category": "二次函数",
                "module": "FUNC", "knowledge_points": ["FUNC-01-01-01"],
                "applicable_types": ["fill", "solve"],
                "difficulty_range": [2, 4], "keywords": ["二次函数", "配方"],
                "principle": "将 $ax^2+bx+c$ 化为 $a(x-h)^2+k$ 形式",
                "steps": ["提取 $a$", "配中项 $\\frac{b}{2a}$", "加减平衡", "写出顶点式"],
                "common_forms": ["$ax^2+bx+c = a(x+\\frac{b}{2a})^2 + c-\\frac{b^2}{4a}$"],
                "pitfalls": ["配方时忘记提取系数 $a$"]
            }]
        }
    return {"error": "unknown prompt type"}

# ─── 文件解析 ─────────────────────────────────────────
def parse_pdf(filepath):
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(filepath) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    parts.append(f"[PAGE {i+1}]\n{text}")
        return "\n\n".join(parts)
    except Exception as e:
        return f"[PDF解析失败: {e}]"

def parse_docx(filepath):
    try:
        import mammoth
        with open(filepath, "rb") as f:
            result = mammoth.convert_to_html(f)
            html = result.value
        text = re.sub(r'<[^>]+>', '', html)
        text = re.sub(r'&nbsp;', ' ', text)
        return text
    except Exception as e:
        return f"[Word解析失败: {e}]"

def parse_text(filepath):
    try:
        return Path(filepath).read_text(encoding="utf-8")
    except Exception as e:
        return f"[文本读取失败: {e}]"

# ─── 处理管线 ─────────────────────────────────────────
def process_file(filepath, filename):
    """处理单个文件，返回审核条目"""
    ext = Path(filepath).suffix.lower()
    items = []

    if ext in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
        # 图片：Vision AI 直接识别
        q_prompt = QUESTION_PROMPT + f"[图片文件: {filename}]"
        q_result = call_llm(q_prompt, image_path=str(filepath))
        if "questions" in q_result:
            for q in q_result["questions"]:
                rid = next_id("R")
                items.append({
                    "id": rid, "status": "pending", "source": "image_ocr",
                    "sourceFile": filename,
                    "extractedAt": datetime.datetime.now().isoformat(),
                    "data": q, "aiConfidence": 0.85, "reviewNotes": ""
                })

        m_prompt = METHOD_PROMPT + f"[图片文件: {filename}]"
        m_result = call_llm(m_prompt, image_path=str(filepath))
        if "methods" in m_result:
            for m in m_result["methods"]:
                rid = next_id("R")
                items.append({
                    "id": rid, "status": "pending", "source": "image_ocr",
                    "sourceFile": filename,
                    "extractedAt": datetime.datetime.now().isoformat(),
                    "data": {"methodType": "method", **m},
                    "aiConfidence": 0.80, "reviewNotes": ""
                })

    elif ext == ".pdf":
        content = parse_pdf(filepath)
        if content.strip() and "[PDF解析失败" not in content:
            chunks = _split_content(content, 2000)
            for chunk in chunks:
                q_result = call_llm(QUESTION_PROMPT + chunk)
                if "questions" in q_result:
                    for q in q_result["questions"]:
                        rid = next_id("R")
                        items.append({
                            "id": rid, "status": "pending", "source": "pdf_parse",
                            "sourceFile": filename,
                            "extractedAt": datetime.datetime.now().isoformat(),
                            "data": q, "aiConfidence": 0.88, "reviewNotes": ""
                        })
                m_result = call_llm(METHOD_PROMPT + chunk)
                if "methods" in m_result:
                    for m in m_result["methods"]:
                        rid = next_id("R")
                        items.append({
                            "id": rid, "status": "pending", "source": "pdf_parse",
                            "sourceFile": filename,
                            "extractedAt": datetime.datetime.now().isoformat(),
                            "data": {"methodType": "method", **m},
                            "aiConfidence": 0.82, "reviewNotes": ""
                        })

    elif ext in {".docx", ".doc"}:
        content = parse_docx(filepath)
        if content.strip() and "[Word解析失败" not in content:
            q_result = call_llm(QUESTION_PROMPT + content[:3000])
            if "questions" in q_result:
                for q in q_result["questions"]:
                    rid = next_id("R")
                    items.append({
                        "id": rid, "status": "pending", "source": "docx_parse",
                        "sourceFile": filename,
                        "extractedAt": datetime.datetime.now().isoformat(),
                        "data": q, "aiConfidence": 0.90, "reviewNotes": ""
                    })
            m_result = call_llm(METHOD_PROMPT + content[:3000])
            if "methods" in m_result:
                for m in m_result["methods"]:
                    rid = next_id("R")
                    items.append({
                        "id": rid, "status": "pending", "source": "docx_parse",
                        "sourceFile": filename,
                        "extractedAt": datetime.datetime.now().isoformat(),
                        "data": {"methodType": "method", **m},
                        "aiConfidence": 0.85, "reviewNotes": ""
                    })

    elif ext in {".txt", ".md", ".markdown"}:
        content = parse_text(filepath)
        q_result = call_llm(QUESTION_PROMPT + content[:4000])
        if "questions" in q_result:
            for q in q_result["questions"]:
                rid = next_id("R")
                items.append({
                    "id": rid, "status": "pending", "source": "text_parse",
                    "sourceFile": filename,
                    "extractedAt": datetime.datetime.now().isoformat(),
                    "data": q, "aiConfidence": 0.93, "reviewNotes": ""
                })

    return items

def _split_content(content, max_chars=2000):
    paragraphs = content.split("\n\n")
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) > max_chars:
            if current: chunks.append(current)
            current = p
        else:
            current += "\n\n" + p
    if current: chunks.append(current)
    return chunks or [content[:max_chars]]

# ─── 公开原型演示数据（只读）──────────────────────────
def read_demo_content():
    """读取纯 JSON 演示数据；生产写操作统一走 /api/v1 与数据库。"""
    empty = {"questions": [], "methods": [], "reviewQueue": []}
    if not DEMO_DATA_PATH.exists():
        return empty
    data = json.loads(DEMO_DATA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("demo-content.json 顶层必须是对象")
    return {
        key: data.get(key, []) if isinstance(data.get(key, []), list) else []
        for key in empty
    }


def legacy_write_removed():
    return jsonify(
        {
            "error": "legacy write API has been removed",
            "replacement": "/api/v1/admin/uploads",
        }
    ), 410

# ─── API 路由 ─────────────────────────────────────────

@app.route("/")
def serve_index():
    """直接服务前端页面"""
    return send_from_directory(str(WEBSITE_DIR), "index.html")

@app.route("/<path:path>")
def serve_static(path):
    """服务所有静态文件"""
    if path == "uploads" or path.startswith("uploads/"):
        return jsonify({"error": "not found"}), 404
    file_path = WEBSITE_DIR / path
    if file_path.exists():
        return send_from_directory(str(WEBSITE_DIR), path)
    return jsonify({"error": "not found"}), 404

@app.route("/api/upload", methods=["POST"])
def upload_file():
    """文件上传 API"""
    if "file" not in request.files:
        return jsonify({"error": "no file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "empty filename"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"unsupported format: {ext}", "supported": sorted(ALLOWED_EXTENSIONS)}), 400

    # 创建上传目录
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    filename = secure_filename(file.filename)
    # 防重名：加时间戳
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    safe_name = f"{ts}_{filename}"
    filepath = UPLOAD_DIR / safe_name
    file.save(str(filepath))

    return jsonify({
        "success": True,
        "filename": safe_name,
        "original_name": filename,
        "size": filepath.stat().st_size,
        "ext": ext,
        "path": str(filepath.relative_to(WEBSITE_DIR))
    })

@app.route("/api/upload-batch", methods=["POST"])
def upload_batch():
    """批量上传"""
    files = request.files.getlist("files")
    results = []
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    for file in files:
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            results.append({"filename": file.filename, "error": f"unsupported: {ext}"})
            continue

        filename = secure_filename(file.filename)
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        safe_name = f"{ts}_{filename}"
        filepath = UPLOAD_DIR / safe_name
        file.save(str(filepath))
        results.append({
            "success": True, "filename": safe_name,
            "original_name": filename, "size": filepath.stat().st_size, "ext": ext
        })

    return jsonify({"results": results, "total": len(results)})

@app.route("/api/process", methods=["POST"])
def process_uploaded():
    """旧同步处理入口已下线；正式 AI 任务统一由数据库队列处理。"""
    return legacy_write_removed()

@app.route("/api/review")
def get_review_queue():
    """旧文件审核队列已下线。"""
    return legacy_write_removed()

@app.route("/api/approve/<item_id>", methods=["POST"])
def approve_item(item_id):
    """旧文件审核入口已下线。"""
    return legacy_write_removed()

@app.route("/api/reject/<item_id>", methods=["POST"])
def reject_item(item_id):
    """旧文件审核入口已下线。"""
    return legacy_write_removed()

@app.route("/api/questions")
def get_questions():
    data = read_demo_content()
    return jsonify({"items": data.get("questions", [])})

@app.route("/api/methods")
def get_methods():
    data = read_demo_content()
    return jsonify({"items": data.get("methods", [])})

@app.route("/api/schema")
def get_schema():
    if SCHEMA_PATH.exists():
        return send_file(str(SCHEMA_PATH), mimetype="application/json")
    return jsonify({"error": "schema not found"}), 404

@app.route("/api/save-question", methods=["POST"])
def save_question():
    """旧文件写入入口已下线。"""
    return legacy_write_removed()

@app.route("/api/save-method", methods=["POST"])
def save_method():
    """旧文件写入入口已下线。"""
    return legacy_write_removed()

@app.route("/api/uploads-list")
def list_uploads():
    """列出已上传文件"""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    files = []
    for f in sorted(UPLOAD_DIR.iterdir()):
        if f.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "ext": f.suffix.lower(),
                "modified": datetime.datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
    return jsonify({"files": files, "total": len(files)})

@app.route("/api/uploads/<filename>")
def serve_upload(filename):
    """访问已上传的文件（用于前端预览图片）"""
    return send_from_directory(str(UPLOAD_DIR), filename)

@app.route("/api/validate", methods=["POST"])
def validate_item():
    """验证数据是否符合 Schema"""
    item = request.get_json()
    if not item:
        return jsonify({"error": "no data"}), 400

    # 基础验证
    errors = []
    entity_type = "method" if item.get("methodType") == "method" else "question"

    if entity_type == "question":
        required = ["module", "difficulty", "type", "stem", "answer"]
        for field in required:
            if not item.get(field):
                errors.append(f"missing required field: {field}")
        if item.get("difficulty") and not (1 <= item["difficulty"] <= 5):
            errors.append("difficulty must be 1-5")
        if item.get("type") and item["type"] not in ["choice", "fill", "solve", "proof"]:
            errors.append("invalid type")
        if item.get("module") and item["module"] not in ["FUNC", "GEOM", "ALGE", "PROB", "CALC"]:
            errors.append("invalid module")

    elif entity_type == "method":
        required = ["name", "module", "principle", "steps"]
        for field in required:
            if not item.get(field):
                errors.append(f"missing required field: {field}")

    return jsonify({"valid": len(errors) == 0, "errors": errors})

# ─── 启动 ─────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("shuxue.icu backend server")
    print(f"  website dir: {WEBSITE_DIR}")
    print(f"  upload dir:  {UPLOAD_DIR}")
    print(f"  demo data:   {DEMO_DATA_PATH}")
    print(f"  schema:      {SCHEMA_PATH}")
    print("=" * 50)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    port = int(os.environ.get("SHUXUE_PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

