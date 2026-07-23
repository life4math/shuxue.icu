#!/bin/bash
# ============================================================
# shuxue.icu 一键部署脚本 — Alibaba Cloud Linux 3
# 用法: sudo bash setup.sh
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
echo -e "${CYAN}  Alibaba Cloud Linux 3${NC}"
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

# ========================================
# 第1步: 安全更新 + 安装系统依赖
# ========================================
echo -e "${YELLOW}[1/8] 安装系统依赖...${NC}"

dnf install -y epel-release 2>/dev/null || true
dnf install -y nginx python3 python3-pip nodejs git 2>/dev/null || {
    echo -e "${RED}  安装失败，尝试更新 dnf 缓存...${NC}"
    dnf clean all
    dnf makecache
    dnf install -y nginx python3 python3-pip nodejs git
}

echo -e "${GREEN}  -> nginx, python3, nodejs, git 已安装${NC}"
echo -e "  Python: $(python3 --version 2>&1)"
echo -e "  Node:   $(node --version 2>&1)"
echo -e "  Nginx:  $(nginx -v 2>&1)"
echo ""

# ========================================
# 第2步: 克隆项目 (或更新)
# ========================================
echo -e "${YELLOW}[2/8] 获取项目代码...${NC}"

mkdir -p "$PROJECT_DIR"

if [ -d "$WEBSITE_DIR/.git" ]; then
    echo -e "  项目已存在，执行 git pull 更新..."
    cd "$WEBSITE_DIR"
    git pull origin main || true
else
    echo -e "  首次部署，从 GitHub 克隆..."
    rm -rf "$WEBSITE_DIR"
    git clone "$REPO_URL" "$WEBSITE_DIR"
fi

echo -e "${GREEN}  -> 项目代码就绪: $WEBSITE_DIR${NC}"
echo ""

# ========================================
# 第3步: 创建 Python 虚拟环境
# ========================================
echo -e "${YELLOW}[3/8] 创建 Python 虚拟环境...${NC}"

python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$WEBSITE_DIR/../requirements.txt" -q || {
    echo -e "${YELLOW}  requirements.txt 未找到，手动安装...${NC}"
    pip install flask gunicorn pdfplumber mammoth openai
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
    echo -e "${YELLOW}  无 API Key 时将使用 mock 模式（不影响基础功能）${NC}"
fi
echo ""

# ========================================
# 第5步: 创建必要目录 + 设置权限
# ========================================
echo -e "${YELLOW}[5/8] 设置目录权限...${NC}"

mkdir -p "$WEBSITE_DIR/uploads"
mkdir -p "$WEBSITE_DIR/scripts/output"

# Nginx 用户需要读取权限 + uploads/data.js 写权限
chown -R nginx:nginx "$PROJECT_DIR"
chmod -R 755 "$WEBSITE_DIR"
chmod -R 775 "$WEBSITE_DIR/uploads"
chmod 664 "$WEBSITE_DIR/js/data.js" 2>/dev/null || true

echo -e "${GREEN}  -> 权限设置完成${NC}"
echo ""

# ========================================
# 第6步: 配置 systemd 服务
# ========================================
echo -e "${YELLOW}[6/8] 配置 systemd 服务...${NC}"

SERVICE_SRC="$WEBSITE_DIR/deploy/shuxue.service"
SERVICE_DST="/etc/systemd/system/shuxue.service"

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
Environment="SHUXUE_PORT=5000"
Environment="SHUXUE_NODE_PATH=/usr/bin/node"
ExecStart=/var/www/shuxue/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 server:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
fi

systemctl daemon-reload
systemctl enable shuxue
systemctl restart shuxue

sleep 2
if systemctl is-active --quiet shuxue; then
    echo -e "${GREEN}  -> shuxue 服务已启动${NC}"
else
    echo -e "${RED}  -> shuxue 服务启动失败！${NC}"
    echo -e "${YELLOW}  查看日志: journalctl -u shuxue -n 20${NC}"
    exit 1
fi
echo ""

# ========================================
# 第7步: 配置 Nginx
# ========================================
echo -e "${YELLOW}[7/8] 配置 Nginx...${NC}"

NGINX_CONF_SRC="$WEBSITE_DIR/deploy/shuxue.icu.conf"
NGINX_CONF_DST="/etc/nginx/conf.d/shuxue.icu.conf"

if [ -f "$NGINX_CONF_SRC" ]; then
    cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
else
    echo -e "${RED}  deploy/shuxue.icu.conf 未找到！${NC}"
    exit 1
fi

# 检查 SSL 证书是否存在
SSL_DIR="/etc/nginx/ssl"
if [ ! -d "$SSL_DIR" ]; then
    echo -e "${YELLOW}  SSL 证书目录不存在，创建临时 HTTP 配置...${NC}"
    # 临时使用 HTTP (无 SSL)，等证书就绪后再切换
    cat > "$NGINX_CONF_DST" << 'NGINXEOF'
server {
    listen 80;
    server_name shuxue.icu www.shuxue.icu;

    location /css/      { root /var/www/shuxue/website; expires 7d; }
    location /js/       { root /var/www/shuxue/website; expires 7d; }
    location /vendor/   { root /var/www/shuxue/website; expires 30d; }
    location /uploads/  { root /var/www/shuxue/website; expires 1d; }

    location = /               { root /var/www/shuxue/website; try_files /index.html =404; }
    location = /index.html     { root /var/www/shuxue/website; }
    location = /student.html   { root /var/www/shuxue/website; }
    location = /pricing.html   { root /var/www/shuxue/website; }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 50M;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINXEOF
    echo -e "${YELLOW}  已创建 HTTP 临时配置 (证书就绪后重新运行此脚本即可切换 HTTPS)${NC}"
else
    echo -e "${GREEN}  SSL 证书目录存在，使用 HTTPS 配置${NC}"
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
echo -e "  1. 本地测试:  ${GREEN}curl http://127.0.0.1:5000/api/questions${NC}"
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
echo -e "  cd $WEBSITE_DIR && git pull"
echo -e "  systemctl restart shuxue"
echo ""
echo -e "${YELLOW}待完成:${NC}"
echo -e "  - DNS 解析: 添加 A 记录 shuxue.icu -> ECS公网IP"
echo -e "  - SSL 证书: 申请后放到 /etc/nginx/ssl/ 并重新运行此脚本"
echo -e "  - ICP 备案号: 在页面底部添加"
