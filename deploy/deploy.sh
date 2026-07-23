#!/usr/bin/env bash
# shuxue.icu 生产部署脚本（在 ECS 上执行）
# 流程：备份本地差异 → 更新代码 → 校验 → 安装运行配置 → 健康检查 → 失败回滚
#
# 由 GitHub Actions 自托管 Runner 调用，也可手动执行：
#   sudo /var/www/shuxue/deploy/deploy.sh
#
# 退出码：0 = 部署成功且健康；非 0 = 失败（已尝试回滚）

set -euo pipefail

PROJECT_DIR="${SHUXUE_PROJECT_DIR:-/var/www/shuxue}"
VENV_DIR="${SHUXUE_VENV_DIR:-$PROJECT_DIR/venv}"
HEALTH_URL="${SHUXUE_HEALTH_URL:-http://127.0.0.1:8000/api/v1/ready}"
LEGACY_HEALTH_URL="${SHUXUE_LEGACY_HEALTH_URL:-http://127.0.0.1:8000/api/questions}"
ADMIN_HEALTH_URL="${SHUXUE_ADMIN_HEALTH_URL:-https://admin.shuxue.icu/admin.html}"
BRANCH="${SHUXUE_BRANCH:-main}"
HEALTH_RETRIES="${SHUXUE_HEALTH_RETRIES:-10}"
HEALTH_INTERVAL="${SHUXUE_HEALTH_INTERVAL:-2}"
BACKUP_ROOT="${SHUXUE_BACKUP_ROOT:-/var/backups/shuxue}"
PUBLIC_NGINX_CONF="/etc/nginx/conf.d/shuxue.icu.conf"
ADMIN_NGINX_CONF="/etc/nginx/conf.d/admin.shuxue.icu.conf"

log() { echo -e "[deploy] $*"; }

cd "$PROJECT_DIR"
git config --global --add safe.directory "$PROJECT_DIR" 2>/dev/null || true

# ── 记录当前版本用于回滚 ──────────────────────────────
PREV="$(git rev-parse HEAD)"
log "当前版本: $PREV"

# 部署脚本会以远程 main 为准。覆盖服务器上的跟踪文件前，先保存差异。
BACKUP_DIR="$BACKUP_ROOT/$(date +%Y%m%d%H%M%S)-$(git rev-parse --short HEAD)"
install -d -m 700 "$BACKUP_DIR"
git status --short > "$BACKUP_DIR/status.txt"
chmod 600 "$BACKUP_DIR/status.txt"
if ! git diff --quiet; then
    git diff --binary > "$BACKUP_DIR/tracked-changes.patch"
    chmod 600 "$BACKUP_DIR/tracked-changes.patch"
    log "服务器本地差异已备份到: $BACKUP_DIR"
fi

# ── 拉取目标版本 ─────────────────────────────────────
git fetch --prune origin "$BRANCH"
git reset --hard "origin/$BRANCH"
NEW="$(git rev-parse HEAD)"
log "目标版本: $NEW"

sync_deps() {
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    pip install -q -r requirements.txt
    deactivate 2>/dev/null || true
}

ensure_environment_secrets() {
    local environment_dir="/etc/shuxue"
    local environment_file="$environment_dir/shuxue.env"
    local generated=""

    install -d -m 700 "$environment_dir"
    touch "$environment_file"
    chmod 600 "$environment_file"

    if ! grep -q '^SHUXUE_ADMIN_TOKEN=' "$environment_file"; then
        generated="$(python3.8 -c 'import secrets; print(secrets.token_hex(32))')"
        printf 'SHUXUE_ADMIN_TOKEN=%s\n' "$generated" >> "$environment_file"
    fi
    if ! grep -q '^SHUXUE_SESSION_SECRET=' "$environment_file"; then
        generated="$(python3.8 -c 'import secrets; print(secrets.token_hex(48))')"
        printf 'SHUXUE_SESSION_SECRET=%s\n' "$generated" >> "$environment_file"
    fi
}

secure_permissions() {
    chown root:root "$PROJECT_DIR"
    chmod 755 "$PROJECT_DIR"
    chown -R root:root "$PROJECT_DIR/.git" "$PROJECT_DIR/deploy" "$PROJECT_DIR/website"
    find "$PROJECT_DIR/website" -type d -exec chmod 755 {} +
    find "$PROJECT_DIR/website" -type f -exec chmod 644 {} +

    install -d -o nginx -g nginx -m 775 "$PROJECT_DIR/website/uploads"
    install -d -o nginx -g nginx -m 775 "$PROJECT_DIR/website/scripts/output"
    chown -R nginx:nginx "$PROJECT_DIR/website/uploads" "$PROJECT_DIR/website/scripts/output"

    if [ -f "$PROJECT_DIR/website/scripts/config.json" ]; then
        chown root:nginx "$PROJECT_DIR/website/scripts/config.json"
        chmod 640 "$PROJECT_DIR/website/scripts/config.json"
    fi
    if [ -f "$PROJECT_DIR/website/scripts/platform.db" ]; then
        chown nginx:nginx "$PROJECT_DIR/website/scripts/platform.db"
        chmod 660 "$PROJECT_DIR/website/scripts/platform.db"
    fi
    if [ -f "$PROJECT_DIR/website/js/data.js" ]; then
        chown nginx:nginx "$PROJECT_DIR/website/js/data.js"
        chmod 664 "$PROJECT_DIR/website/js/data.js"
    fi
}

install_services() {
    install -m 644 "$PROJECT_DIR/deploy/shuxue.service" /etc/systemd/system/shuxue.service
    install -m 644 "$PROJECT_DIR/deploy/shuxue-worker.service" /etc/systemd/system/shuxue-worker.service
    systemctl daemon-reload
    systemctl enable shuxue shuxue-worker >/dev/null
}

render_admin_nginx_config() {
    local template="$PROJECT_DIR/deploy/admin.shuxue.icu.conf.example"
    local certificate=""
    local certificate_key=""
    local temporary=""

    if [ -f /etc/nginx/ssl/admin.shuxue.icu.pem ] && [ -f /etc/nginx/ssl/admin.shuxue.icu.key ]; then
        certificate="/etc/nginx/ssl/admin.shuxue.icu.pem"
        certificate_key="/etc/nginx/ssl/admin.shuxue.icu.key"
    elif [ -f /etc/letsencrypt/live/admin.shuxue.icu/fullchain.pem ] && [ -f /etc/letsencrypt/live/admin.shuxue.icu/privkey.pem ]; then
        certificate="/etc/letsencrypt/live/admin.shuxue.icu/fullchain.pem"
        certificate_key="/etc/letsencrypt/live/admin.shuxue.icu/privkey.pem"
    elif [ -f /etc/nginx/ssl/shuxue.icu.pem ] && [ -f /etc/nginx/ssl/shuxue.icu.key ] \
        && openssl x509 -in /etc/nginx/ssl/shuxue.icu.pem -noout -checkhost admin.shuxue.icu >/dev/null 2>&1; then
        certificate="/etc/nginx/ssl/shuxue.icu.pem"
        certificate_key="/etc/nginx/ssl/shuxue.icu.key"
    elif [ -f "$ADMIN_NGINX_CONF" ]; then
        certificate="$(awk '$1 == "ssl_certificate" {gsub(/;/, "", $2); print $2; exit}' "$ADMIN_NGINX_CONF")"
        certificate_key="$(awk '$1 == "ssl_certificate_key" {gsub(/;/, "", $2); print $2; exit}' "$ADMIN_NGINX_CONF")"
        if [ ! -f "$certificate" ] || [ ! -f "$certificate_key" ]; then
            certificate=""
            certificate_key=""
        fi
    fi

    if [ -z "$certificate" ] || [ -z "$certificate_key" ]; then
        log "未找到 admin.shuxue.icu 可用证书，拒绝安装不完整的后台配置。"
        return 1
    fi

    temporary="$(mktemp /tmp/shuxue-admin-nginx.XXXXXX)"
    sed \
        -e "s#ssl_certificate .*;#ssl_certificate $certificate;#" \
        -e "s#ssl_certificate_key .*;#ssl_certificate_key $certificate_key;#" \
        "$template" > "$temporary"
    install -m 644 "$temporary" "$ADMIN_NGINX_CONF"
    rm -f "$temporary"
}

install_nginx_config() {
    install -m 644 "$PROJECT_DIR/deploy/shuxue.icu.conf" "$PUBLIC_NGINX_CONF"
    render_admin_nginx_config
    nginx -t
    systemctl reload nginx
}

restart_services() {
    systemctl restart shuxue
    systemctl restart shuxue-worker
}

health_ok() {
    local allow_legacy="${1:-0}"
    local code=""
    local admin_code=""
    for _ in $(seq 1 "$HEALTH_RETRIES"); do
        if ! systemctl is-active --quiet shuxue || ! systemctl is-active --quiet shuxue-worker; then
            sleep "$HEALTH_INTERVAL"
            continue
        fi
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$HEALTH_URL" || true)"
        admin_code="$(curl -ks -o /dev/null -w '%{http_code}' --max-time 5 \
            --resolve admin.shuxue.icu:443:127.0.0.1 "$ADMIN_HEALTH_URL" || true)"
        if [ "$code" = "200" ] && [ "$admin_code" = "200" ]; then
            return 0
        fi
        if [ "$allow_legacy" = "1" ]; then
            code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$LEGACY_HEALTH_URL" || true)"
            if [ "$code" = "200" ]; then
                return 0
            fi
        fi
        sleep "$HEALTH_INTERVAL"
    done
    return 1
}

rollback() {
    log "部署失败，回滚到上一版本: $PREV"
    git reset --hard "$PREV"
    sync_deps || true
    secure_permissions || true
    install_services || true
    install_nginx_config || true
    restart_services || true
    if health_ok 1; then
        log "已回滚到 $PREV，服务恢复正常。"
    else
        log "回滚后健康检查仍失败，需要人工介入。"
    fi
}

# ── 部署前完整性校验（拦截损坏文件）────────────────────
if ! python3.8 deploy/check_integrity.py; then
    log "完整性校验未通过，恢复到部署前版本 $PREV，中止部署。"
    git reset --hard "$PREV"
    exit 1
fi

# ── 同步依赖、运行配置并重启 ─────────────────────────
if ! sync_deps || ! ensure_environment_secrets || ! secure_permissions \
    || ! install_services || ! install_nginx_config || ! restart_services; then
    rollback
    exit 1
fi

# ── 部署后健康检查 ───────────────────────────────────
if health_ok 0; then
    log "部署成功，API、数据库、后台页面和 Worker 均通过检查: $NEW"
    exit 0
else
    rollback
    exit 1
fi
