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

collector.service 提供接收服务单元，安装时填写目标项目和 Python 路径。schedule.py 按当前 Python、项目位置和配置生成采集与入库单元。

```sh
systemctl status self-harness-collector.service
systemctl list-timers 'self-harness-*'
```

相关资源：[调度](scheduling.md)、[迁移](migration.md)。
