#!/usr/bin/env bash
# shuxue.icu 生产部署脚本（在 ECS 上执行）
# 流程：更新代码 → 完整性校验 → 同步依赖 → 优雅重启 → 健康检查 → 失败自动回滚
#
# 由 GitHub Actions 自托管 Runner 调用，也可手动执行：
#   sudo /var/www/shuxue/deploy/deploy.sh
#
# 退出码：0 = 部署成功且健康；非 0 = 失败（已尝试回滚）

set -euo pipefail

PROJECT_DIR="${SHUXUE_PROJECT_DIR:-/var/www/shuxue}"
VENV_DIR="${SHUXUE_VENV_DIR:-$PROJECT_DIR/venv}"
HEALTH_URL="${SHUXUE_HEALTH_URL:-http://127.0.0.1:8000/api/questions}"
BRANCH="${SHUXUE_BRANCH:-main}"
HEALTH_RETRIES="${SHUXUE_HEALTH_RETRIES:-10}"
HEALTH_INTERVAL="${SHUXUE_HEALTH_INTERVAL:-2}"

log() { echo -e "[deploy] $*"; }

cd "$PROJECT_DIR"

# ── 记录当前版本用于回滚 ──────────────────────────────
PREV="$(git rev-parse HEAD)"
log "当前版本: $PREV"

# ── 拉取目标版本 ─────────────────────────────────────
git fetch --prune origin "$BRANCH"
git reset --hard "origin/$BRANCH"
NEW="$(git rev-parse HEAD)"
log "目标版本: $NEW"

if [ "$PREV" = "$NEW" ]; then
    log "版本无变化，仍执行校验与健康检查以确保服务正常。"
fi

restart_services() {
    systemctl restart shuxue
    systemctl restart shuxue-worker 2>/dev/null || true
}

sync_deps() {
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    pip install -q -r requirements.txt
    deactivate 2>/dev/null || true
}

health_ok() {
    local code
    for _ in $(seq 1 "$HEALTH_RETRIES"); do
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$HEALTH_URL" || true)"
        if [ "$code" = "200" ]; then
            return 0
        fi
        sleep "$HEALTH_INTERVAL"
    done
    return 1
}

rollback() {
    log "❌ 健康检查失败，回滚到上一版本: $PREV"
    git reset --hard "$PREV"
    sync_deps || true
    restart_services
    if health_ok; then
        log "↩️  已回滚到 $PREV，服务恢复正常。"
    else
        log "⚠️  回滚后健康检查仍失败，需要人工介入！"
    fi
}

# ── 部署前完整性校验（拦截损坏文件）────────────────────
if ! python3 deploy/check_integrity.py; then
    log "完整性校验未通过，恢复到部署前版本 $PREV，中止部署。"
    git reset --hard "$PREV"
    exit 1
fi

# ── 同步依赖并优雅重启 ───────────────────────────────
sync_deps
restart_services

# ── 部署后健康检查 ───────────────────────────────────
if health_ok; then
    log "✅ 部署成功，健康检查通过: $NEW"
    exit 0
else
    rollback
    exit 1
fi
