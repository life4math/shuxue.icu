# shuxue.icu — AI Agent Instructions

## Project Overview

shuxue.icu is a math research platform for Chinese high school (高考) exam preparation. It provides question banks, analytics dashboards, subscription tiers, and a student study interface. The project uses a pure frontend stack (HTML/CSS/JS) with a Python Flask backend for API endpoints.

**Live deployment**: Alibaba Cloud ECS (HTTPS, Nginx + Gunicorn + Flask)
**Repository**: https://github.com/life4math/shuxue.icu

## Repository Layout

```
website/               # Frontend — all static files served by Nginx
  index.html           # Main SPA (5-tab navigation: LEARNING/ANALYTICS/DASHBOARD/PRICING/ABOUT)
  student.html         # Student-specific interface
  pricing.html         # Subscription pricing page
  css/style.css        # All styles (CSS variables for theme system)
  js/app.js            # Main app logic, navigation, tab switching
  js/data.js           # 仅供公开原型使用的虚构演示数据
  admin.html           # 教师后台入口（生产使用独立子域名）
  js/themes.js         # Theme engine (3 themes: PKU/TSINGHUA/CYAN)
  js/charts.js         # ECharts radar/trend chart rendering
  scripts/server.py    # Flask backend (legacy/demo API + v1 blueprint)
  scripts/platform_db.py   # SQLAlchemy 正式数据模型
  scripts/platform_api.py  # 教师账号、任务、审核和发布 API
  scripts/worker.py        # AI 异步任务 Worker
  scripts/config.json  # ⚠️ SENSITIVE — OpenAI API key (gitignored, only config.example.json in repo)
  scripts/schema.json  # Data schema definition
  vendor/              # KaTeX, ECharts, Space Grotesk font (static assets)
  uploads/             # User-uploaded files (gitignored)

deploy/                # Production deployment configs
  setup.sh             # One-click deployment script (Alibaba Cloud Linux 3)
  shuxue.icu.conf      # Nginx config (HTTPS + HTTP→HTTPS redirect + API proxy)
  shuxue.service       # systemd service file (Gunicorn on port 8000)

requirements.txt       # Python dependencies (Flask, Gunicorn, pdfplumber, mammoth, OpenAI)
```

## Architecture

- **Frontend**: Pure HTML/CSS/JS SPA (no build step, no framework)
  - KaTeX for math rendering, ECharts for charts, Space Grotesk font
  - Three-theme system: PKU (北大红) / TSINGHUA (清华紫) / CYAN (赛博青)
  - Theme engine in `js/themes.js` using CSS custom properties
- **Backend**: Python Flask (`website/scripts/server.py`)
  - `/api/questions` — question bank
  - `/api/methods` — method library
  - `/api/upload` — file upload + AI analysis
  - `/api/analyze` — student analytics
  - Config in `config.json` (OpenAI API key, ⚠️ never commit)
  - Admin API authentication uses `SHUXUE_ADMIN_TOKEN` from the environment
- **Production**: Nginx (443/SSL → 8000/Gunicorn → Flask)
  - Nginx serves static files directly, proxies `/api/` to Flask
  - HTTP port 80 redirects to HTTPS with HSTS

## Build & Run

**No build step required** — this is a pure static frontend project.

### Local development (frontend only)
```bash
# Open website/index.html in any browser — no server needed for static pages
# Or use a simple static server:
cd website && python -m http.server 8080
```

### Local development (with Flask backend)
```bash
cd website/scripts
pip install -r ../../requirements.txt
# Create config.json from config.example.json (add your OpenAI API key)
python server.py  # Flask runs on port 5000 by default
```

### Production deployment
```bash
# On Alibaba Cloud ECS — run the one-click script:
bash deploy/setup.sh
```

## Design System Rules (CRITICAL)

### Three-Theme System
- **PKU**: accent=#B91C1C, warn=#DC2626, difficulty=#450a0a→#F87171
- **TSINGHUA**: accent=#7B2FA0, warn=#A855F7, difficulty=#3b0764→#C084FC
- **CYAN**: accent=#00d4ff, warn=#0ea5e9, difficulty=#003d5c→#7dd3fc (DEFAULT)

### Immutable Design Rules
- Background (`#0a0a0f`), text (`#e5e5e5`), and border (`#1e1e2e`) colors NEVER change with theme
- Navigation text colors: inactive=#d1d1d6, active=#ffffff, indicator=var(--accent)
- Theme switching via: (1) brand hover dropdown in navbar, (2) About > Design System section
- All accent-dependent colors use CSS custom properties (`var(--accent)`, `var(--warn)`, etc.)
- Brand identifier: `shuxue.icu` (no suffix like "terminal")

### Subscription Tier System
- Four tiers: FREE(¥0) / PRO(¥49) / TEAM(¥199·5 seats) / API(¥500+)
- Feature locking via `data-tier-lock` attribute on DOM elements
- Tier badge in nav-user area
- Usage tracking: daily/monthly limits for browsing, analysis, upload
- ADE business model: D(Freemium acquisition) → A(SaaS conversion) → E(Data API profit)

## Code Style & Conventions

- **Language**: Chinese for all UI text, comments, and documentation; English for code identifiers
- **CSS**: Use CSS custom properties (variables) for all theme-dependent values; never hardcode accent colors
- **JS**: No framework — vanilla JS only; ES6+ features allowed; no module bundler
- **Demo data**: 公开展示数据位于 `js/data.js`，必须保持虚构且不得混入真实学生信息
- **Production data**: 教师后台正式数据使用 SQLAlchemy；生产数据库为 PostgreSQL
- **Fonts**: Space Grotesk for headings/body, KaTeX for math
- **No emoji in production code** unless user explicitly requests

## Security Rules

- **config.json is SENSITIVE** — contains OpenAI API key; always gitignored, never commit
- **config.example.json** is the safe template — always use this as reference
- **.gitignore** must always exclude: `.workbuddy/`, `uploads/`, `config.json`, `__pycache__`, `venv`, `node_modules`
- **SSL certificates** on server are private — never include in repo
- **Admin token** is stored in `/etc/shuxue/shuxue.env` in production — never commit it
- All mutating `/api/*` requests must use `Authorization: Bearer <token>` or `X-Admin-Token`
- Uploaded files must never be served directly from `/uploads/`
- When adding new secrets/API keys, always add to .gitignore first

## Testing & Verification

- 运行自动测试：
  - `pytest -q`
- 同时执行以下人工验证：
  - Open `index.html` in browser, check all 5 tabs load correctly
  - Verify theme switching works (brand hover dropdown + About page)
  - Check subscription tier badge display and feature locking
  - Public API: `curl https://shuxue.icu/api/questions` should return JSON
  - Admin API: send the token from `/etc/shuxue/shuxue.env`; unauthenticated requests must return 401
- After any frontend change, verify: math rendering (KaTeX), charts (ECharts), responsive layout

## Common Tasks

- **Add a question**: Edit `js/data.js`, add to the `questions` array following existing format (id, module, difficulty, knowledge_points, analysis, answer)
- **Add a theme**: Edit `js/themes.js`, add entry to `THEMES` object with accent/warn/difficulty colors, update dropdown builder
- **Add an API endpoint**: Edit `website/scripts/server.py`, add Flask route under `/api/`
- **Deploy update**: Push to GitHub, then on ECS: `cd /var/www/shuxue && git pull && systemctl restart shuxue`
- **Renew SSL cert**: Replace files in `/etc/nginx/ssl/`, then `systemctl reload nginx`

## Production Server Notes

- Server: Alibaba Cloud Linux 3.2104 LTS (等保2.0三级版)
- Python 3.8 (no python39 available on this system)
- Gunicorn on port 8000 (port 5000 occupied by RemoteManage/.NET)
- nginx.conf must include `include /etc/nginx/conf.d/*.conf;` (missing by default on 等保2.0)
- Nginx config needs `default_server` + `server_name _;` to override built-in default server block

## Do Not

- Do not add React/Vue/Angular or any frontend framework
- Do not add a build step (webpack/vite/etc.) — project is intentionally pure static
- Do not hardcode colors that should use CSS variables
- Do not commit config.json, uploads/, or any secrets
- Do not change background/text/border colors based on theme
- Do not use python39 on the production server (only python38 available)

