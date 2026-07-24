# shuxue.icu

> MATH RESEARCH PLATFORM — 高考数学研究平台

## 项目简介

shuxue.icu 是一个面向高考数学教学与研究的 Web 平台，集题库管理、学情分析、AI 辅助审题和订阅制商业模式于一体。

### 核心功能

- **学习方案 (LEARNING)**：当前公开页只展示可动态维护的知识图谱与知识正文
- **学情分析 (ANALYTICS)**：学生选择器、雷达图/趋势图、薄弱项诊断、推荐学习路径
- **DASHBOARD**：概览统计、高频错题、文件上传管线、AI 审核队列
- **订阅计划 (PRICING)**：四层级订阅体系（FREE / PRO / TEAM / API）
- **关于我们 (ABOUT)**：博客、设计系统（三主题切换）

### 三主题系统

| 主题 | 名称 | 主色 |
|------|------|------|
| PKU | 北大红 | `#B91C1C` |
| TSINGHUA | 清华紫 | `#7B2FA0` |
| CYAN | 赛博青 | `#00d4ff` |

默认主题为 CYAN。鼠标悬停导航栏 `shuxue.icu` 品牌文字即可切换主题，选择会持久化到 localStorage 并跨标签页同步。

### 商业模式 (ADE)

- **A (Acquisition)**：Freemium 免费获客，FREE 层级零门槛使用基础功能
- **D (Development)**：SaaS 订阅转化，PRO/TEAM 层级提供高级分析与管理
- **E (Earnings)**：Data API 利润池，API 层级提供数据接口变现

## 技术栈

| 层面 | 技术 |
|------|------|
| 前端 | HTML / CSS / JavaScript / KaTeX / ECharts |
| 主题引擎 | CSS 变量动态覆盖 + localStorage 持久化 |
| 后端 | Python Flask + LLM (OpenAI API) |
| 正式数据 | SQLAlchemy + Alembic + PostgreSQL（测试环境兼容 SQLite） |
| 演示数据 | `data.js` / JSON，仅用于公开原型中的虚构题目与学情 |

> 当前公开页面使用的 `data.js` 仅包含虚构演示数据。教师后台的正式数据使用
> SQLAlchemy 数据模型；生产环境目标数据库为 PostgreSQL。

## 教师后台

公开站点中的教师功能已迁移到 `/admin.html`。后台使用服务端 Session、HttpOnly
Cookie 和 CSRF Token，不在浏览器代码中保存管理员令牌。

在线备课工作台位于 `/prep.html`，公开讲义目录位于 `/lectures.html`。当前阶段与
后续开发顺序见 `DEVELOPMENT_PLAN.md`。

知识图谱使用永久内部 ID、稳定业务代码、父节点排序、版本快照和发布快照。
教师可在后台独立创建、移动、编辑、发布、归档或合并知识节点；公开页只读取
`/api/v1/public/knowledge-tree` 和已发布正文。旧静态目录暂时只作为网络异常时的
应急快照，不再是正式数据源。

生产环境需要设置：

```bash
SHUXUE_SESSION_SECRET=<随机长密钥>
SHUXUE_DATABASE_URL=postgresql+psycopg2://user:password@127.0.0.1/shuxue
```

初始化管理员：

```bash
cd website/scripts
python init_platform.py --email admin@example.com
```

重置已有管理员密码（例如 `87707817@qq.com`）：

```bash
cd website/scripts
python init_platform.py --email 87707817@qq.com --reset
```

AI 任务 Worker：

```bash
cd website/scripts
python worker.py
```

`deploy/admin.shuxue.icu.conf.example` 是独立教师子域名的配置模板。只有在 DNS 和
证书准备完成后才应启用。

## 目录结构

```
shuxue.icu/
├── website/
│   ├── index.html              # 公开展示原型
│   ├── admin.html              # 独立教师后台
│   ├── student.html            # 学生端页面
│   ├── pricing.html            # 订阅计划页面
│   ├── css/style.css           # 全局样式
│   ├── js/                     # 应用、主题、图表和数据
│   ├── scripts/                # Flask 服务、Schema 和配置模板
│   ├── vendor/                 # KaTeX、ECharts 等第三方资源
│   └── uploads/                # 用户上传文件（gitignore，不公开）
├── deploy/                     # Nginx、systemd 和部署脚本
├── requirements.txt
└── ade-business-plan.md        # ADE 商业模型文档
```

## 快速开始

### 前端（纯静态）

正式知识树需要 Flask API。仅检查静态布局时可以启动普通文件服务器：

```bash
cd website
python -m http.server 3000
```

### 后端（Flask）

```bash
cd website/scripts
python -m pip install --require-hashes -r ../../requirements-py311.lock
cp config.example.json config.json
# 编辑 config.json 填入你的 API Key
export SHUXUE_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export SHUXUE_SESSION_SECRET="$(python -c 'import secrets; print(secrets.token_hex(48))')"
python migrate.py
python server.py
# 服务运行在 http://localhost:5000
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/public/knowledge-tree` | 获取已发布知识树与关系 |
| GET | `/api/v1/public/knowledge/:node` | 按内部 ID、代码或别名获取已发布正文 |
| GET/POST/PATCH | `/api/v1/admin/knowledge/nodes` | 管理知识节点 |
| GET/POST/PATCH | `/api/v1/admin/knowledge/relations` | 管理知识关系 |
| PUT/POST | `/api/v1/admin/knowledge/:node` | 保存、提交和发布知识正文 |
| POST | `/api/v1/admin/uploads` | 上传教师资料 |
| POST | `/api/v1/admin/jobs` | 创建 AI 处理任务 |
| GET | `/api/v1/health` | 进程存活检查 |
| GET | `/api/v1/ready` | 数据库就绪检查 |

`/api/v1/admin/*` 使用教师账号 Session 和 CSRF Token。`SHUXUE_ADMIN_TOKEN`
只保留给尚未迁移的旧运维接口，不能替代教师登录。

## 部署

### 阿里云 ECS (Alibaba Cloud Linux 3)

推送到 `main` 会自动执行完整性校验和测试。只有提交信息包含 `[deploy]`
（例如 `git commit -m "[deploy] 完成阶段升级"`），或在 GitHub Actions 页面手动
触发工作流时，才会更新生产环境。部署过程会备份服务器上的跟踪文件差异，安装
Web/Worker/Nginx 配置，并检查：

- `/api/v1/health`：API 进程存活。
- `/api/v1/ready`：API 与数据库就绪。
- `admin.shuxue.icu/admin.html`：教师后台可访问。
- `shuxue` 与 `shuxue-worker`：两个 systemd 服务均正常运行。

项目内置一键部署脚本，SSH 登录服务器后执行：

```bash
# 1. 下载部署脚本（或直接 clone 整个仓库后运行 deploy/setup.sh）
curl -o setup.sh https://raw.githubusercontent.com/life4math/shuxue.icu/main/deploy/setup.sh
chmod +x setup.sh
sudo bash setup.sh
```

脚本会自动完成：安装系统依赖 → git clone 项目 → 创建 Python venv → 安装依赖 → 配置 config.json → 生成管理令牌 → 设置权限 → 配置 systemd 服务 → 配置 Nginx → 防火墙放行。

脚本默认不会修改 DNF exclude 规则，也不会移除 Apache/PHP。如果确认服务器
未承载其他业务且确实需要兼容处理，可显式执行
`sudo SHUXUE_ALLOW_SYSTEM_CHANGES=1 bash setup.sh`。

部署完成后还需手动完成：
1. **DNS 解析**：阿里云 DNS 添加 A 记录 `shuxue.icu` → ECS 公网 IP
2. **SSL 证书**：申请后放到 `/etc/nginx/ssl/`，重新运行 `sudo bash setup.sh` 即可切换 HTTPS
3. **ICP 备案号**：在页面底部添加备案号

### 手动部署

如需手动部署，参考以下步骤：

```bash
# 安装系统依赖
dnf install -y nginx python3.11 python3.11-pip nodejs git

# 克隆项目
git clone https://github.com/life4math/shuxue.icu.git /var/www/shuxue

# 创建虚拟环境 + 安装依赖
cd /var/www/shuxue
python3.11 -m venv venv311
source venv311/bin/activate
python -m pip install --require-hashes -r requirements-py311.lock

# 配置 API
cp website/scripts/config.example.json website/scripts/config.json
install -d -m 700 /etc/shuxue
printf 'SHUXUE_ADMIN_TOKEN=%s\nSHUXUE_SESSION_SECRET=%s\n' \
  "$(python3.11 -c 'import secrets; print(secrets.token_hex(32))')" \
  "$(python3.11 -c 'import secrets; print(secrets.token_hex(48))')" \
  > /etc/shuxue/shuxue.env
chmod 600 /etc/shuxue/shuxue.env

# 设置权限
chown -R nginx:nginx /var/www/shuxue
chmod -R 775 /var/www/shuxue/website/uploads

# 配置 systemd
cp deploy/shuxue.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now shuxue

# 配置 Nginx
cp deploy/shuxue.icu.conf /etc/nginx/conf.d/
nginx -t && systemctl restart nginx

# 防火墙
firewall-cmd --permanent --add-service={http,https}
firewall-cmd --reload
```

## License

Copyright (c) life4math. All rights reserved.

本仓库当前未授予开源许可证。公开可见不代表允许复制、修改、分发或商业使用。

