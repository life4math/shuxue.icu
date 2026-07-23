# shuxue.icu

> MATH RESEARCH PLATFORM — 高考数学研究平台

## 项目简介

shuxue.icu 是一个面向高考数学教学与研究的 Web 平台，集题库管理、学情分析、AI 辅助审题和订阅制商业模式于一体。

### 核心功能

- **学习方案 (LEARNING)**：题库浏览、知识图谱可视化、方法库
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
| 数据 | JS 对象语法 (data.js) + JSON Schema |

## 目录结构

```
shuxue.icu/
├── website/
│   ├── index.html              # 教师端主页
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

直接用浏览器打开 `website/index.html`，或启动本地服务器：

```bash
cd website
python -m http.server 3000
```

### 后端（Flask）

```bash
cd website/scripts
pip install flask pdfplumber mammoth openai
cp config.example.json config.json
# 编辑 config.json 填入你的 API Key
export SHUXUE_ADMIN_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python server.py
# 服务运行在 http://localhost:5000
```

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/questions` | 获取题库 |
| GET | `/api/methods` | 获取方法库 |
| GET | `/api/review` | 获取审核队列 |
| POST | `/api/upload` | 上传文件 |
| POST | `/api/process` | 触发 AI 处理 |
| POST | `/api/approve/:id` | 审核通过 |
| POST | `/api/reject/:id` | 审核拒绝 |

除 `GET /api/questions`、`GET /api/methods` 和 `GET /api/schema` 外，管理 API
必须携带 `Authorization: Bearer <SHUXUE_ADMIN_TOKEN>` 或
`X-Admin-Token: <SHUXUE_ADMIN_TOKEN>`。未配置令牌时，管理 API 会安全地返回
`503`，不会匿名开放。生产部署令牌保存在 `/etc/shuxue/shuxue.env`。

## 部署

### 阿里云 ECS (Alibaba Cloud Linux 3)

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
dnf install -y nginx python3 python3-pip nodejs git

# 克隆项目
git clone https://github.com/life4math/shuxue.icu.git /var/www/shuxue

# 创建虚拟环境 + 安装依赖
cd /var/www/shuxue
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 配置 API
cp website/scripts/config.example.json website/scripts/config.json
install -d -m 700 /etc/shuxue
printf 'SHUXUE_ADMIN_TOKEN=%s\n' "$(python3 -c 'import secrets; print(secrets.token_hex(32))')" \
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

