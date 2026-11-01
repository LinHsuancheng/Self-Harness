# 当前部署

2026-10-14 部署位置：

| 项目 | 当前值 |
| --- | --- |
| 采集服务器 | 45.32.47.93 |
| 项目目录 | /root/test-server |
| Git 仓库 | git@github.com:LinHsuancheng/Self-Harness.git |
| 上传服务 | 8000 /upload |
| 接收服务 | self-harness-collector.service |
| 原始数据 | /root/test-server/raw |
| SQLite | /root/test-server/database |
| 报告时区 | Asia/Singapore |

SSH 使用对应私钥或 agent，当前已验证 ~/.ssh/agent_ed25519。连接信息和运行位置随部署配置调整。

本地 Git 工作区是唯一代码源，服务器目录是 GitHub `main` 的运行工作区。所有代码和文档在本地修改、提交并推送，再在服务器快进拉取。服务器上的 `config.json`、`.env`、`raw/`、`database/`、`auth/`、`reports/` 和 `.venv/` 属于运行环境，保留在服务器并由 `.gitignore` 排除。

例行部署已提交的代码：

```sh
git push origin HEAD:main
ssh -i ~/.ssh/agent_ed25519 root@45.32.47.93 'git -C /root/test-server pull --ff-only origin main'
```

修改 `server.py` 后重启采集服务；只更新分析 CLI 或文档时无需重启。

## 截图分析部署

部署顺序必须是先代码、后配置、最后 Windows 任务，避免旧代码把新来源当成 Todo 处理。

1. 本地提交并推送，服务器快进拉取。
2. 服务器 `.venv/bin/pip install -r requirements.txt`（新增 Pillow；分析器本身只依赖已有的 openai）。
3. 合并服务器 `config.json`：`folders.screen_capture`、`sources.pc_screen_activity`、`schedule.screen_analysis_seconds`。保留 `pc_screen_time` 和现有凭据；不要覆盖 `.env`。
4. 重启 collector（`server.py` 新增 `observed_at`/`sha256` sidecar）：
   `systemctl restart self-harness-collector.service`
5. 安装 timer：`.venv/bin/python schedule.py --role server --install`；确认 `self-harness-screen-analysis.timer`。
6. Windows 执行 `setup_sharex.ps1` 和 `install_screenshot_task.ps1`，然后手动触发一次 `Start-ScheduledTask`。

上传仍使用 8000 明文端口（当前部署选择）。`screen_capture` 不能加入 `sources`，`pc_screen_activity` 不能加入 `folders`；否则分别会导致 context 统计错误或允许客户端伪造分析 JSON。

collector.service 提供接收服务单元，安装时填写目标项目和 Python 路径。schedule.py 按当前 Python、项目位置和配置生成采集与入库单元。

```sh
systemctl status self-harness-collector.service
systemctl list-timers 'self-harness-*'
```

相关资源：[调度](scheduling.md)、[迁移](migration.md)。
