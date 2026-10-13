# 当前部署

2026-10-13 已验证的部署位置：

| 项目 | 当前值 |
| --- | --- |
| 采集服务器 | 45.32.47.93 |
| 项目目录 | /root/test-server |
| 上传服务 | 8000 /upload |
| 接收服务 | self-harness-collector.service |
| 原始数据 | /root/test-server/raw |
| SQLite | /root/test-server/database |
| 报告时区 | Asia/Singapore |

SSH 使用对应私钥或 agent，当前已验证 ~/.ssh/agent_ed25519。连接信息和运行位置随部署配置调整。

本地 Git 工作区是唯一代码源，服务器目录是部署副本。所有代码和文档在本地修改、提交，再将 Git 跟踪文件同步到服务器。服务器上的 `config.json`、`raw/`、`database/`、`auth/` 和 `.venv/` 属于运行环境，保留在服务器。

从项目根目录部署已提交的文件：

```sh
git ls-files -z | rsync -av --from0 --files-from=- -e 'ssh -i ~/.ssh/agent_ed25519' ./ root@45.32.47.93:/root/test-server/
```

该命令只覆盖 Git 跟踪的路径，不删除服务器上的其他文件。修改 `server.py` 后重启采集服务；只更新分析 CLI 或文档时无需重启。

collector.service 提供接收服务单元，安装时填写目标项目和 Python 路径。schedule.py 按当前 Python、项目位置和配置生成采集与入库单元。

```sh
systemctl status self-harness-collector.service
systemctl list-timers 'self-harness-*'
```

相关资源：[调度](scheduling.md)、[迁移](migration.md)。
