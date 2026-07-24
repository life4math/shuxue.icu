#!/usr/bin/env bash
# shuxue.icu 生产部署脚本（在 ECS 上执行）
# 流程：备份本地差异 → 更新代码 → 校验 → 安装运行配置 → 健康检查 → 失败回滚
#
# 由 GitHub Actions 自托管 Runner 调用，也可手动执行：
#   sudo /var/www/shuxue/deploy/deploy.sh
#   sudo /var/www/shuxue/deploy/deploy.sh --bundle /path/to/shuxue-release.bundle
#
# 退出码：0 = 部署成功且健康；非 0 = 失败（已尝试回滚）

set -euo pipefail

RELEASE_BUNDLE=""
if [ "${1:-}" = "--bundle" ]; then
    if [ -z "${2:-}" ] || [ ! -f "$2" ]; then
        echo "[deploy] 离线部署包不存在: ${2:-<empty>}" >&2
        exit 2
    fi
    RELEASE_BUNDLE="$(readlink -f "$2")"
    shift 2
fi
if [ "$#" -ne 0 ]; then
    echo "[deploy] 未知参数: $*" >&2
    exit 2
fi

PROJECT_DIR="${SHUXUE_PROJECT_DIR:-/var/www/shuxue}"
PYTHON_BIN="${SHUXUE_PYTHON_BIN:-python3.11}"
VENV_DIR="${SHUXUE_VENV_DIR:-$PROJECT_DIR/venv311}"
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

# 切换 Git 版本后重新载入目标版本中的部署脚本，确保本次发布立即采用
# 新的运行时、迁移和回滚逻辑。PREV 通过环境保留，避免把目标版本当成回滚点。
if [ "${SHUXUE_DEPLOY_RESUMED:-0}" = "1" ]; then
    PREV="${SHUXUE_PREV_COMMIT:?missing previous commit for resumed deployment}"
    log "已载入目标版本部署入口，回滚版本: $PREV"
else
    # ── 记录当前版本用于回滚 ──────────────────────────
    PREV="$(git rev-parse HEAD)"
    log "当前版本: $PREV"

    # 覆盖服务器上的跟踪文件前，先保存本地差异。
    BACKUP_DIR="$BACKUP_ROOT/$(date +%Y%m%d%H%M%S)-$(git rev-parse --short HEAD)"
    install -d -m 700 "$BACKUP_DIR"
    git status --short > "$BACKUP_DIR/status.txt"
    chmod 600 "$BACKUP_DIR/status.txt"
    if ! git diff --quiet; then
        git diff --binary > "$BACKUP_DIR/tracked-changes.patch"
        chmod 600 "$BACKUP_DIR/tracked-changes.patch"
        log "服务器本地差异已备份到: $BACKUP_DIR"
    fi

    # ── 导入目标版本 ─────────────────────────────────
    # CI 优先传入已校验的 Git bundle，避免生产 ECS 必须直连 github.com。
    if [ -n "$RELEASE_BUNDLE" ]; then
        log "从 CI 离线部署包导入目标版本。"
        git fetch --no-tags "$RELEASE_BUNDLE" HEAD
        git reset --hard FETCH_HEAD
    else
        git fetch --prune origin "$BRANCH"
        git reset --hard "origin/$BRANCH"
    fi

    export SHUXUE_DEPLOY_RESUMED=1
    export SHUXUE_PREV_COMMIT="$PREV"
    if [ -n "$RELEASE_BUNDLE" ]; then
        exec "$PROJECT_DIR/deploy/deploy.sh" --bundle "$RELEASE_BUNDLE"
    else
        exec "$PROJECT_DIR/deploy/deploy.sh"
    fi
fi
NEW="$(git rev-parse HEAD)"
log "目标版本: $NEW"

sync_deps() {
    "$VENV_DIR/bin/python" -m pip install -q \
        --require-hashes -r requirements-py311.lock
}

ensure_runtime() {
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        log "安装受支持的 Python 3.11 运行时。"
        dnf install -y python3.11 python3.11-pip
    fi
    if [ ! -x "$VENV_DIR/bin/python" ]; then
        log "创建 Python 3.11 虚拟环境: $VENV_DIR"
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi
    "$VENV_DIR/bin/python" -c \
        'import sys; assert sys.version_info[:2] == (3, 11), sys.version'
    "$VENV_DIR/bin/python" -m pip install -q --upgrade "pip<27"
    # systemd 以 nginx 用户启动应用。无论 root 的 umask 如何，都确保
    # nginx 可以遍历并读取虚拟环境，同时保持环境归 root 管理。
    chown -R root:root "$VENV_DIR"
    chmod -R a+rX "$VENV_DIR"
}

sync_rollback_deps() {
    local rollback_venv="$PROJECT_DIR/venv"
    local rollback_lock="requirements-py38.lock"
    if grep -q '/venv311/' deploy/shuxue.service 2>/dev/null; then
        rollback_venv="$PROJECT_DIR/venv311"
        rollback_lock="requirements-py311.lock"
    fi
    if [ ! -x "$rollback_venv/bin/python" ]; then
        log "回滚版本的虚拟环境不存在，跳过依赖同步。"
        return 0
    fi
    if [ -f "$rollback_lock" ]; then
        "$rollback_venv/bin/python" -m pip install -q \
            --require-hashes -r "$rollback_lock"
    else
        "$rollback_venv/bin/python" -m pip install -q -r requirements.txt
    fi
}

ensure_environment_secrets() {
    local environment_dir="/etc/shuxue"
    local environment_file="$environment_dir/shuxue.env"
    local generated=""

    install -d -m 700 "$environment_dir"
    touch "$environment_file"
    chmod 600 "$environment_file"

    if ! grep -q '^SHUXUE_ADMIN_TOKEN=' "$environment_file"; then
        generated="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_hex(32))')"
        printf 'SHUXUE_ADMIN_TOKEN=%s\n' "$generated" >> "$environment_file"
    fi
    if ! grep -q '^SHUXUE_SESSION_SECRET=' "$environment_file"; then
        generated="$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_hex(48))')"
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
    local main_pid=""
    local running_python=""
    local desired_python=""

    if systemctl is-active --quiet shuxue; then
        main_pid="$(systemctl show shuxue -p MainPID --value)"
        running_python="$(readlink -f "/proc/$main_pid/exe" 2>/dev/null || true)"
        desired_python="$(readlink -f "$VENV_DIR/bin/python" 2>/dev/null || true)"
    fi

    if [ -n "$running_python" ] && [ "$running_python" = "$desired_python" ]; then
        log "Web 服务使用兼容运行时，执行 Gunicorn 优雅重载。"
        systemctl reload shuxue || systemctl restart shuxue
    else
        log "Web 服务运行时发生变化，执行一次完整重启。"
        systemctl restart shuxue
    fi
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
    sync_rollback_deps || true
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
if ! python3.8 deploy/check_integrity.py \
    || ! python3.8 deploy/check_frontend.py \
    || ! find website/js -maxdepth 1 -name '*.js' ! -name '*.min.js' -print0 \
        | xargs -0 -n1 node --check; then
    log "完整性校验未通过，恢复到部署前版本 $PREV，中止部署。"
    git reset --hard "$PREV"
    exit 1
fi

# ── 同步依赖、运行配置并重启 ─────────────────────────
if ! ensure_runtime || ! sync_deps || ! ensure_environment_secrets || ! secure_permissions \
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
