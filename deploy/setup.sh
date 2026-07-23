#!/bin/bash
# ============================================================
# shuxue.icu 一键部署脚本 — Alibaba Cloud Linux 3 (等保2.0三级版)
# 用法:
#   公开仓库:  sudo bash setup.sh
#   私有仓库:  sudo GITHUB_TOKEN=ghp_xxxx bash setup.sh
# ============================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  shuxue.icu 部署脚本${NC}"
echo -e "${CYAN}  Alibaba Cloud Linux 3 (等保2.0)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR] 请使用 root 用户或 sudo 运行此脚本${NC}"
    exit 1
fi

PROJECT_DIR="/var/www/shuxue"
WEBSITE_DIR="$PROJECT_DIR/website"
VENV_DIR="$PROJECT_DIR/venv"
REPO_URL="https://github.com/life4math/shuxue.icu.git"

# 私有仓库 token 支持
if [ -n "$GITHUB_TOKEN" ]; then
    REPO_URL="https://life4math:${GITHUB_TOKEN}@github.com/life4math/shuxue.icu.git"
    echo -e "${YELLOW}  使用 GITHUB_TOKEN 进行私有仓库认证${NC}"
    echo ""
fi

# ========================================
# 第0步: 可选的系统级兼容处理
# ========================================
echo -e "${YELLOW}[0/8] 检查系统级兼容处理...${NC}"

if [ "${SHUXUE_ALLOW_SYSTEM_CHANGES:-0}" != "1" ]; then
    echo -e "${YELLOW}  默认不修改 DNF exclude 规则，也不移除 Apache/PHP。${NC}"
    echo -e "${YELLOW}  确认本机没有承载其他业务后，可设置 SHUXUE_ALLOW_SYSTEM_CHANGES=1。${NC}"
    SKIP_SYSTEM_CHANGES=1
else
    SKIP_SYSTEM_CHANGES=0
fi

# 等保2.0三级版在 dnf.conf 和 repo 文件中设置了 exclude= 行
# 阻止了 nginx/httpd/php 等包的安装和移除
# 解决方案: 注释掉所有 exclude= 和 excludepkgs= 行

CHANGED=0

# 检查并注释 dnf.conf
if [ "$SKIP_SYSTEM_CHANGES" -eq 0 ] && grep -q '^exclude=' /etc/dnf/dnf.conf 2>/dev/null; then
    echo -e "  发现 /etc/dnf/dnf.conf 中的 exclude 规则，注释掉..."
    sed -i 's/^exclude=/#exclude=/' /etc/dnf/dnf.conf
    CHANGED=1
fi

if [ "$SKIP_SYSTEM_CHANGES" -eq 0 ] && grep -q '^excludepkgs=' /etc/dnf/dnf.conf 2>/dev/null; then
    sed -i 's/^excludepkgs=/#excludepkgs=/' /etc/dnf/dnf.conf
    CHANGED=1
fi

# 检查并注释所有 repo 文件
for f in /etc/yum.repos.d/*.repo; do
    [ "$SKIP_SYSTEM_CHANGES" -eq 1 ] && break
    if [ -f "$f" ] && grep -q '^exclude=' "$f" 2>/dev/null; then
        echo -e "  发现 $f 中的 exclude 规则，注释掉..."
        sed -i 's/^exclude=/#exclude=/' "$f"
        CHANGED=1
    fi
    if [ -f "$f" ] && grep -q '^excludepkgs=' "$f" 2>/dev/null; then
        sed -i 's/^excludepkgs=/#excludepkgs=/' "$f"
        CHANGED=1
    fi
done

if [ "$CHANGED" -eq 1 ]; then
    echo -e "${GREEN}  -> exclude 规则已注释，刷新 dnf 缓存...${NC}"
    dnf clean all
    dnf makecache
else
    echo -e "${GREEN}  -> 未发现 exclude 规则，跳过${NC}"
fi
echo ""

# ========================================
# 第0b步: 移除冲突的 Apache/httpd (我们用 Nginx)
# ========================================
echo -e "${YELLOW}[0b/8] 移除 Apache/httpd...${NC}"

if [ "$SKIP_SYSTEM_CHANGES" -eq 1 ]; then
    echo -e "${GREEN}  -> 跳过 Apache/PHP 移除${NC}"
elif rpm -q httpd >/dev/null 2>&1; then
    echo -e "  检测到 httpd (Apache)，停止并移除..."
    systemctl stop httpd 2>/dev/null || true
    systemctl disable httpd 2>/dev/null || true

    # 现在 exclude 已移除，dnf remove 应该能工作
    dnf remove -y httpd httpd-filesystem httpd-tools php php-cli php-common

    if rpm -q httpd >/dev/null 2>&1; then
        echo -e "${YELLOW}  httpd 仍存在 (已停止服务，不影响 Nginx)${NC}"
    else
        echo -e "${GREEN}  -> httpd/php 已移除${NC}"
    fi
else
    echo -e "${GREEN}  -> httpd 未安装，跳过${NC}"
fi
echo ""

# ========================================
# 第1步: 安全更新 + 安装系统依赖
# ========================================
echo -e "${YELLOW}[1/8] 安装系统依赖...${NC}"

# 安全更新 (现在 exclude 已移除，应该不再冲突)
dnf upgrade-minimal --security -y --skip-broken 2>/dev/null || {
    echo -e "${YELLOW}  安全更新部分跳过，不影响部署${NC}"
}

# 使用 python38 (python39 模块在等保2.0系统上不存在，只有 python27/36/38)
dnf install -y epel-release 2>/dev/null || true
dnf module enable -y python38:3.8 2>/dev/null || true
dnf install -y nginx python38 python38-pip git

echo -e "${GREEN}  -> 系统依赖安装完成${NC}"
echo -e "  Python: $(python3.8 --version 2>&1)"
echo -e "  Nginx:  $(nginx -v 2>&1)"
echo ""

# ========================================
# 第2步: 克隆项目 (或更新)
# ========================================
echo -e "${YELLOW}[2/8] 获取项目代码...${NC}"

if [ -d "$PROJECT_DIR/.git" ]; then
    echo -e "  项目已存在，执行 git pull 更新..."
    cd "$PROJECT_DIR"
    if [ -n "$GITHUB_TOKEN" ]; then
        git remote set-url origin "https://life4math:${GITHUB_TOKEN}@github.com/life4math/shuxue.icu.git"
        git pull origin main 2>/dev/null || true
        git remote set-url origin https://github.com/life4math/shuxue.icu.git
    else
        git pull origin main || true
    fi
else
    echo -e "  首次部署，从 GitHub 克隆..."
    if [ -e "$PROJECT_DIR" ]; then
        echo -e "${RED}[ERROR] $PROJECT_DIR 已存在但不是 Git 仓库；请先人工检查并迁移该目录。${NC}"
        exit 1
    fi
    git clone "$REPO_URL" "$PROJECT_DIR"
    # 清理 token (安全)
    cd "$PROJECT_DIR"
    git remote set-url origin https://github.com/life4math/shuxue.icu.git
    echo -e "${GREEN}  -> token 已从 remote URL 中清除${NC}"
fi

echo -e "${GREEN}  -> 项目代码就绪: $PROJECT_DIR${NC}"
echo -e "  Web 文件: $WEBSITE_DIR"
echo ""

# ========================================
# 第3步: 创建 Python 3.8 虚拟环境
# ========================================
echo -e "${YELLOW}[3/8] 创建 Python 3.8 虚拟环境...${NC}"

# 使用 python3.8 创建 venv (python39 模块不存在，系统只有 27/36/38)
python3.8 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$PROJECT_DIR/requirements.txt" -q || {
    echo -e "${YELLOW}  requirements.txt 安装失败，尝试手动安装...${NC}"
    pip install flask gunicorn pdfplumber mammoth openai SQLAlchemy psycopg2-binary pytest
}

echo -e "${GREEN}  -> Python 依赖安装完成${NC}"
python -c "import flask; print(f'  Flask {flask.__version__}')"
echo ""

# ========================================
# 第4步: 创建 config.json
# ========================================
echo -e "${YELLOW}[4/8] 配置 API...${NC}"

CONFIG_FILE="$WEBSITE_DIR/scripts/config.json"
if [ -f "$CONFIG_FILE" ]; then
    echo -e "  config.json 已存在，跳过"
else
    cp "$WEBSITE_DIR/scripts/config.example.json" "$CONFIG_FILE"
    echo -e "${YELLOW}  已从模板创建 config.json${NC}"
    echo -e "${YELLOW}  如需 LLM 功能，请编辑 $CONFIG_FILE 填入 API Key${NC}"
    echo -e "${YELLOW}  无 API Key 时将使用 mock 模式${NC}"
fi
echo ""

# ========================================
# 第5步: 创建必要目录 + 设置权限
# ========================================
echo -e "${YELLOW}[5/8] 设置目录权限...${NC}"

mkdir -p "$WEBSITE_DIR/uploads"
mkdir -p "$WEBSITE_DIR/scripts/output"

# 代码由 root 持有；仅运行时目录和兼容数据文件允许 nginx 写入。
chown -R root:root "$PROJECT_DIR"
chmod 755 "$PROJECT_DIR"
find "$WEBSITE_DIR" -type d -exec chmod 755 {} +
find "$WEBSITE_DIR" -type f -exec chmod 644 {} +
chown -R nginx:nginx "$WEBSITE_DIR/uploads" "$WEBSITE_DIR/scripts/output"
chmod -R 775 "$WEBSITE_DIR/uploads" "$WEBSITE_DIR/scripts/output"
chown nginx:nginx "$WEBSITE_DIR/js/data.js" 2>/dev/null || true
chmod 664 "$WEBSITE_DIR/js/data.js" 2>/dev/null || true
if [ -f "$WEBSITE_DIR/scripts/platform.db" ]; then
    chown nginx:nginx "$WEBSITE_DIR/scripts/platform.db"
    chmod 660 "$WEBSITE_DIR/scripts/platform.db"
fi
chown root:nginx "$WEBSITE_DIR/scripts/config.json" 2>/dev/null || true
chmod 640 "$WEBSITE_DIR/scripts/config.json" 2>/dev/null || true

echo -e "${GREEN}  -> 权限设置完成${NC}"
echo ""

# ========================================
# 第6步: 配置 systemd 服务
# ========================================
echo -e "${YELLOW}[6/8] 配置 systemd 服务...${NC}"

SERVICE_SRC="$PROJECT_DIR/deploy/shuxue.service"
SERVICE_DST="/etc/systemd/system/shuxue.service"
ENV_DIR="/etc/shuxue"
ENV_FILE="$ENV_DIR/shuxue.env"

install -d -m 700 "$ENV_DIR"
if [ ! -f "$ENV_FILE" ]; then
    ADMIN_TOKEN="$(python3.8 -c 'import secrets; print(secrets.token_hex(32))')"
    SESSION_SECRET="$(python3.8 -c 'import secrets; print(secrets.token_hex(48))')"
    printf 'SHUXUE_ADMIN_TOKEN=%s\nSHUXUE_SESSION_SECRET=%s\n' \
        "$ADMIN_TOKEN" "$SESSION_SECRET" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo -e "${GREEN}  -> 已生成管理 API 令牌: $ENV_FILE${NC}"
else
    if ! grep -q '^SHUXUE_SESSION_SECRET=' "$ENV_FILE"; then
        SESSION_SECRET="$(python3.8 -c 'import secrets; print(secrets.token_hex(48))')"
        printf 'SHUXUE_SESSION_SECRET=%s\n' "$SESSION_SECRET" >> "$ENV_FILE"
    fi
    chmod 600 "$ENV_FILE"
    echo -e "${GREEN}  -> 保留现有管理 API 令牌并确认 Session 密钥: $ENV_FILE${NC}"
fi

if [ -f "$SERVICE_SRC" ]; then
    cp "$SERVICE_SRC" "$SERVICE_DST"
else
    echo -e "${YELLOW}  deploy/shuxue.service 未找到，创建默认配置...${NC}"
    cat > "$SERVICE_DST" << 'EOF'
[Unit]
Description=shuxue.icu Flask Application
After=network.target

[Service]
User=nginx
Group=nginx
WorkingDirectory=/var/www/shuxue/website/scripts
Environment="PATH=/var/www/shuxue/venv/bin:/usr/bin"
Environment="SHUXUE_PORT=8000"
Environment="SHUXUE_NODE_PATH=/usr/bin/node"
Environment="SHUXUE_ENV=production"
EnvironmentFile=-/etc/shuxue/shuxue.env
ExecStart=/var/www/shuxue/venv/bin/gunicorn -w 2 -b 127.0.0.1:8000 server:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
fi

install -m 644 "$PROJECT_DIR/deploy/shuxue-worker.service" /etc/systemd/system/shuxue-worker.service
systemctl daemon-reload
systemctl enable shuxue shuxue-worker
systemctl restart shuxue shuxue-worker

sleep 2
if systemctl is-active --quiet shuxue && systemctl is-active --quiet shuxue-worker; then
    echo -e "${GREEN}  -> Web 与 Worker 服务均已启动${NC}"
else
    echo -e "${RED}  -> Web 或 Worker 服务启动失败！${NC}"
    echo -e "${YELLOW}  查看日志: journalctl -u shuxue -u shuxue-worker -n 40${NC}"
    exit 1
fi
echo ""

# ========================================
# 第7步: 配置 Nginx
# ========================================
echo -e "${YELLOW}[7/8] 配置 Nginx...${NC}"

# 修复: 阿里云等保2.0定制版 nginx.conf 默认缺少 conf.d include
if ! grep -q 'include.*conf.d' /etc/nginx/nginx.conf; then
    echo -e "${YELLOW}  nginx.conf 缺少 conf.d include，添加中...${NC}"
    sed -i '/^http {/a\    include /etc/nginx/conf.d/*.conf;' /etc/nginx/nginx.conf
    echo -e "${GREEN}  -> 已添加 include /etc/nginx/conf.d/*.conf${NC}"
fi

# 禁用可能冲突的默认配置
mv /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf.bak 2>/dev/null || true
mv /etc/nginx/conf.d/nextjs.conf /etc/nginx/conf.d/nextjs.conf.bak 2>/dev/null || true

NGINX_CONF_DST="/etc/nginx/conf.d/shuxue.icu.conf"
SSL_DIR="/etc/nginx/ssl"

if [ -d "$SSL_DIR" ] && [ -f "$SSL_DIR/shuxue.icu.pem" ] && [ -f "$SSL_DIR/shuxue.icu.key" ]; then
    echo -e "${GREEN}  SSL 证书存在，使用 HTTPS 配置${NC}"
    NGINX_CONF_SRC="$PROJECT_DIR/deploy/shuxue.icu.conf"
    if [ -f "$NGINX_CONF_SRC" ]; then
        cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
    fi
    if [ -f "$SSL_DIR/admin.shuxue.icu.pem" ] && [ -f "$SSL_DIR/admin.shuxue.icu.key" ]; then
        install -m 644 "$PROJECT_DIR/deploy/admin.shuxue.icu.conf.example" \
            /etc/nginx/conf.d/admin.shuxue.icu.conf
        echo -e "${GREEN}  -> 已启用 admin.shuxue.icu 独立后台配置${NC}"
    fi
else
    echo -e "${YELLOW}  SSL 证书不存在，创建 HTTP 配置...${NC}"
    cat > "$NGINX_CONF_DST" << 'NGINXEOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name shuxue.icu www.shuxue.icu _;

    root /var/www/shuxue/website;
    index index.html;

    location /css/      { expires 7d; }
    location /js/       { expires 7d; }
    location /vendor/   { expires 30d; }
    # 后端代码和密钥配置禁止静态访问
    location ^~ /scripts/ { return 404; }
    # 禁止直接公开用户上传内容
    location ^~ /uploads/ { return 404; }

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 代理到 Flask (8000端口，不用5000 — 阿里云 RemoteManage 占用)
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 50M;
    }
}
NGINXEOF
    echo -e "${YELLOW}  已创建 HTTP 配置 (证书就绪后重新运行此脚本切换 HTTPS)${NC}"
fi

# 测试 Nginx 配置
if nginx -t 2>&1; then
    systemctl enable nginx
    systemctl restart nginx
    echo -e "${GREEN}  -> Nginx 已启动${NC}"
else
    echo -e "${RED}  Nginx 配置测试失败！${NC}"
    exit 1
fi
echo ""

# ========================================
# 第8步: 防火墙
# ========================================
echo -e "${YELLOW}[8/8] 配置防火墙...${NC}"

if systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
    echo -e "${GREEN}  -> firewalld 已放行 80/443${NC}"
else
    echo -e "${YELLOW}  firewalld 未运行，跳过${NC}"
    echo -e "${YELLOW}  请确保阿里云安全组已放行 80/443 端口${NC}"
fi
echo ""

# ========================================
# 验证
# ========================================
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "验证步骤:"
echo -e "  1. 本地测试:  ${GREEN}curl http://127.0.0.1:8000/api/questions${NC}"
echo -e "  2. Nginx测试: ${GREEN}curl http://127.0.0.1/api/questions${NC}"
echo -e "  3. 外部访问:  ${GREEN}http://你的ECS公网IP/${NC}"
echo -e "  4. 域名访问:  ${GREEN}http://shuxue.icu/${NC}"
echo ""
echo -e "服务管理:"
echo -e "  查看状态:  ${CYAN}systemctl status shuxue${NC}"
echo -e "  查看日志:  ${CYAN}journalctl -u shuxue -f${NC}"
echo -e "  重启服务:  ${CYAN}systemctl restart shuxue${NC}"
echo -e "  重启Nginx: ${CYAN}systemctl restart nginx${NC}"
echo ""
echo -e "更新代码后:"
echo -e "  cd $PROJECT_DIR && git pull"
echo -e "  systemctl restart shuxue"
echo ""
echo -e "${YELLOW}待完成:${NC}"
echo -e "  - DNS 解析: 添加 A 记录 shuxue.icu -> ECS公网IP"
echo -e "  - SSL 证书: 申请后放到 /etc/nginx/ssl/ 并重新运行此脚本"
echo -e "  - ICP 备案号: 在页面底部添加"

