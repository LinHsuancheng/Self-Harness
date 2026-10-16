# 自动调度

| 机器 | 单元 | 当前周期 |
| --- | --- | --- |
| 服务器 | self-harness-ingest.timer | 60秒 |
| 服务器 | self-harness-todo.timer | 3600秒 |
| 服务器 | self-harness-report.timer | 每天 06:00（配置时区） |
| Windows PC | Self Harness ActivityWatch 任务 | 每小时 |

服务器入库与 Todo 周期来自 schedule 配置；日报使用 `schedule.report_time` 和顶层 `timezone`，按该时区计算昨天并将 HTML 正文通过 Gmail 发送。

```sh
# install/update all server timers
.venv/bin/python schedule.py --role server --install
# install/update only the report timer
.venv/bin/python schedule.py --role server --report-only --install
```

schedule.py 默认打印服务器单元，加 --install 写入并启用，文件位于 /etc/systemd/system。
`--report-only` 只安装日报 timer，不改写采集和 Todo timer。

PC 采集由 Windows 任务计划程序按小时执行，在 Windows PowerShell 中安装：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\automations\install_activitywatch_task.ps1
```

任务调用 `wsl.exe` 启动 `Ubuntu-24.04`，运行 `../automations/collect_activitywatch.py`；无需让 WSL 常驻。

```sh
journalctl -u self-harness-ingest.service -u self-harness-todo.service
journalctl -u self-harness-report.service
systemctl list-timers self-harness-report.timer
```

服务器定时器由 Linux systemd 管理。PC 的 ActivityWatch 采集使用 Windows 任务计划程序；手机端沿用已确认的定时上传流程。

相关资源：[采集工作流](../workflows/collection.md)、[配置](../configuration.md)。
