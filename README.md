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
├── index.html              # 教师端主页
├── student.html            # 学生端页面
├── pricing.html            # 订阅计划页面
├── css/
│   └── style.css           # 全局样式
├── js/
│   ├── app.js              # 主应用逻辑
│   ├── themes.js           # 三主题引擎
│   ├── charts.js           # ECharts 图表
│   └── data.js             # 题库/方法库/审核队列数据
├── scripts/
│   ├── server.py           # Flask 后端服务
│   ├── ingest.py           # 数据导入脚本
│   ├── schema.json         # 数据格式 Schema
│   └── config.example.json # API 配置示例
├── vendor/                 # 第三方库 (KaTeX, ECharts)
├── uploads/                # 用户上传文件 (gitignore)
└── ade-business-plan.md    # ADE 商业模型文档
```

## 快速开始

### 前端（纯静态）

直接用浏览器打开 `index.html`，或启动本地服务器：

```bash
# Node.js
node -e "require('http').createServer((q,r)=>{const f=require('fs'),p=require('path');r.setHeader('Content-Type',q.url.endsWith('.html')?'text/html':'text/javascript');try{r.end(f.readFileSync(p.join(__dirname,q.url==='/'?'/index.html':q.url)))}catch(e){r.statusCode=404;r.end()}}).listen(3000,()=>console.log('http://localhost:3000'))"
```

### 后端（Flask）

```bash
cd website/scripts
pip install flask pdfplumber mammoth openai
cp config.example.json config.json
# 编辑 config.json 填入你的 API Key
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

## 部署

### 阿里云 ECS (Alibaba Cloud Linux 3)

```bash
# 安装依赖
dnf install -y nginx python3 python3-pip nodejs

# 项目部署
mkdir -p /var/www/shuxue
cp -r website/ /var/www/shuxue/website/
cd /var/www/shuxue
python3 -m venv venv
source venv/bin/activate
pip install flask gunicorn pdfplumber mammoth openai

# Gunicorn 启动
gunicorn -w 2 -b 127.0.0.1:5000 server:app

# Nginx 反向代理 → 127.0.0.1:5000
```

## License

Private
