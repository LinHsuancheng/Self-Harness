# 自动调度

| 机器 | 单元 | 当前周期 |
| --- | --- | --- |
| 服务器 | self-harness-ingest.timer | 60秒 |
| 服务器 | self-harness-todo.timer | 3600秒 |
| 服务器 | self-harness-screen-analysis.timer | 60秒 |
| 服务器 | self-harness-report.timer | 每天 09:00（配置时区，示例/代码缺省） |
| Windows PC | Self Harness ActivityWatch 任务 | 每小时（并行期保留） |
| Windows PC | Self Harness Screenshot 任务 | 每 5 分钟 |

服务器入库与 Todo 周期来自 schedule 配置；日报使用 `schedule.report_time` 和顶层 `timezone`。缺省在新加坡时间 09:00 触发，`--date yesterday` 生成昨日 09:00 至今日 09:00 的报告并发送。09:00 是触发时刻，生成、模型响应与邮件投递耗时意味着不能保证 09:00:00 到达。

手动执行时，显式 `--date YYYY-MM-DD` 始终以该日期作为区间起始标签；`--date yesterday` 始终按进程启动时的配置时区取昨日，不会因 09:00 前后再次偏移。修改既有部署的 `timezone`、`day_start_hour` 或 `schedule.report_time` 后，需要重新安装 report timer；本文不表示线上配置已经更新。

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

## 截图观察

服务器截图分析由 `self-harness-screen-analysis.timer` 每 60 秒触发，service 的 `TimeoutStartSec=600` 允许批量处理积压；分析结果由 ingest timer 在下一分钟入库。

Windows 截图任务每 5 分钟运行 `capture_screenshot.ps1`：先触发 ShareX `-silent -nohotkeys -ActiveMonitor -autoclose`，等待 spool 出现稳定图片，再调用 `wsl.exe` 运行 `upload_screenshots.py`。任务必须使用当前用户的**交互式**会话，否则无法截取桌面；执行上限 4 分钟，`MultipleInstances IgnoreNew` 防止重叠。积压超过 `max_pending_files` 时跳过新截图，只清积压。

任务动作不是直接启动 `powershell.exe`，而是 `wscript.exe //B //Nologo run_screenshot_hidden.vbs`；VBS 用窗口样式 0 启动 PowerShell，避免每 5 分钟闪出控制台，PowerShell 再调用 `wsl.exe`。VBS 由 `install_screenshot_task.ps1` 按当前脚本路径和发行版生成。

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\automations\setup_sharex.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\automations\install_screenshot_task.ps1
Start-ScheduledTask -TaskName 'Self Harness Screenshot'
Get-ScheduledTaskInfo -TaskName 'Self Harness Screenshot'
```

ShareX 设置由 `setup_sharex.ps1` 合并，包括自定义截图目录、JPEG、只保存文件、关闭剪贴板/编辑器/提示音/托盘通知和文件名时间戳。卸载任务：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\automations\install_screenshot_task.ps1 -Unregister
```

```sh
journalctl -u self-harness-ingest.service -u self-harness-todo.service
journalctl -u self-harness-report.service
systemctl list-timers self-harness-report.timer
```

服务器定时器由 Linux systemd 管理。PC 的 ActivityWatch 采集使用 Windows 任务计划程序；手机端沿用已确认的定时上传流程。

相关资源：[采集工作流](../workflows/collection.md)、[配置](../configuration.md)。
