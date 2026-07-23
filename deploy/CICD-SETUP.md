# 自动部署闭环 · 安装配置指南

目标：**push 到 `main` → 阿里云 ECS 自动更新项目**，含部署前完整性校验、部署后健康检查、失败自动回滚。

采用 **GitHub 自托管 Runner** 方案：部署动作在你自己的 ECS 上本地执行，**无需对公网开放任何入站端口**，适合等保2.0环境。

---

## 组成部分

本次新增/改动的文件（都在仓库里）：

| 文件 | 作用 |
|------|------|
| `.github/workflows/deploy.yml` | GitHub Actions 工作流：push 到 main 触发，先校验+测试，再部署 |
| `deploy/deploy.sh` | 服务器端部署脚本：拉代码→校验→装依赖→优雅重启→健康检查→失败回滚 |
| `deploy/check_integrity.py` | 部署前完整性校验：拦截被写坏/含乱码的源码文件（正是这次三个前端文件损坏那类问题） |

此外，三个损坏的前端文件（`index.html`、`app.js`、`style.css`）已恢复到最后正常版本。

---

## 一次性配置（在 ECS 上操作，约 10 分钟）

> 下面用 `deploy` 代称执行 Runner 的系统用户。为安全起见**不要用 root 跑 Runner**；
> 用现有的普通用户，或新建一个 `deploy` 用户均可。

### 第 1 步：确认生产目录是 Git 仓库且有 venv

```bash
# 若 /var/www/shuxue 已按 deploy/setup.sh 部署过，通常已满足；确认一下：
cd /var/www/shuxue
git remote -v                 # 应指向 github.com/life4math/shuxue.icu
git rev-parse --abbrev-ref HEAD   # 应为 main
ls venv/bin/activate          # venv 应存在
```

### 第 2 步：安装 GitHub 自托管 Runner

在 GitHub 仓库页面：**Settings → Actions → Runners → New self-hosted runner**，选 Linux x64，
页面会给出带**一次性注册令牌**的命令。在 ECS 上执行（示例，实际命令以页面为准）：

```bash
sudo mkdir -p /opt/actions-runner && sudo chown "$USER" /opt/actions-runner
cd /opt/actions-runner
curl -o actions-runner-linux-x64.tar.gz -L \
  https://github.com/actions/runner/releases/latest/download/actions-runner-linux-x64.tar.gz
tar xzf actions-runner-linux-x64.tar.gz

# 用页面上的 URL 和 token 注册；关键是加上 shuxue 这个标签（labels）
./config.sh --url https://github.com/life4math/shuxue.icu \
            --token <页面上的注册令牌> \
            --labels shuxue \
            --name shuxue-ecs --unattended
```

> 工作流里 `runs-on: [self-hosted, shuxue]` 就是靠 `shuxue` 这个标签来匹配这台 Runner。

### 第 3 步：把 Runner 装成常驻服务（开机自启）

```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status     # 显示 active (running) 即成功
```

### 第 4 步：给 Runner 用户授予"仅部署所需"的 sudo 权限

部署要重启 systemd 服务、写入 nginx 拥有的目录，需要有限的 sudo。**只放行部署脚本，不给全量 sudo**：

```bash
# 假设 Runner 用户名为 deploy；用 visudo 编辑，避免语法错误锁死 sudo
sudo visudo -f /etc/sudoers.d/shuxue-deploy
```

写入（把 `deploy` 换成实际的 Runner 用户名）：

```
deploy ALL=(root) NOPASSWD: /var/www/shuxue/deploy/deploy.sh
```

### 第 5 步：确保 Runner 用户能操作生产目录

```bash
# 让 Runner 用户对 /var/www/shuxue 有读写（用于 git reset / 装依赖）
sudo chown -R deploy:nginx /var/www/shuxue
sudo chmod -R g+w /var/www/shuxue
# git 安全目录（避免 dubious ownership 报错）
sudo -u deploy git config --global --add safe.directory /var/www/shuxue
```

---

## 完成后如何工作

1. 你（或我）把代码 push 到 `main`。
2. GitHub Actions 自动触发 `deploy.yml`：
   - **verify 阶段**：完整性校验 + 后端 `pytest`。任一失败，**不会部署**。
   - **deploy 阶段**：在 ECS 上执行 `deploy.sh` → `git reset --hard origin/main` → 再次完整性校验 → 装依赖 → 重启 `shuxue` / `shuxue-worker` → `curl` 健康检查。
   - 健康检查失败 → **自动回滚**到上一版本并重启。
3. 在 GitHub 仓库 **Actions** 页可看到每次部署的实时日志与成败。

之后你就只管改代码 + push，上线全自动。

---

## 健康检查地址说明

`deploy.sh` 默认检查 `http://127.0.0.1:8000/api/questions`（Gunicorn 本地端口）。
如果你想让它走 Nginx（校验整条链路），可在服务器上设置环境变量后再由脚本读取，或直接改脚本里的
`HEALTH_URL` 默认值为 `https://shuxue.icu/api/questions`。

## 手动应急部署

Runner 出问题时，仍可手动一键部署（与自动流程同逻辑）：

```bash
sudo /var/www/shuxue/deploy/deploy.sh
```

## 常见问题

- **工作流一直 queued 不动**：Runner 没启动或标签不对。查 `sudo ./svc.sh status`，确认标签含 `shuxue`。
- **deploy.sh 报 permission denied**：第 4 步 sudoers 未配好，或路径不符。
- **健康检查总失败但服务其实正常**：确认 `HEALTH_URL` 端口/路径正确，且 `/api/questions` 在未配管理令牌时也能匿名 200（本项目公开 GET 接口是允许匿名的）。
