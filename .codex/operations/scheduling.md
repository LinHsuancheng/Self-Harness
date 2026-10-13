# 自动调度

| 机器 | 单元 | 当前周期 |
| --- | --- | --- |
| 服务器 | self-harness-ingest.timer | 60秒 |
| 服务器 | self-harness-todo.timer | 3600秒 |
| 服务器 | self-harness-report.timer | 每天 06:00（配置时区） |
| PC 用户 | self-harness-pc.timer | 3600秒 |

周期来自 schedule 配置；日报使用 `schedule.report_time`，时区使用顶层 `timezone`。日报按该时区计算昨天，并将 HTML 正文通过 Gmail 发送。

```sh
# install/update all server timers
.venv/bin/python schedule.py --role server --install
# install/update only the report timer
.venv/bin/python schedule.py --role server --report-only --install
.venv/bin/python schedule.py --role pc --install
```

schedule.py 默认打印单元，加 --install 写入并启用。服务器单元位于 /etc/systemd/system，PC 用户单元位于 ~/.config/systemd/user。
`--report-only` 只安装日报 timer，不改写采集和 Todo timer。

```sh
journalctl -u self-harness-ingest.service -u self-harness-todo.service
journalctl -u self-harness-report.service
systemctl list-timers self-harness-report.timer
systemctl --user status self-harness-pc.service
```

PC 采集使用该机器的 ActivityWatch 和用户 systemd 会话。手机端沿用已确认的定时上传流程。

相关资源：[采集工作流](../workflows/collection.md)、[配置](../configuration.md)。
