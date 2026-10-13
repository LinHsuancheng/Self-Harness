# 自动调度

| 机器 | 单元 | 当前周期 |
| --- | --- | --- |
| 服务器 | self-harness-ingest.timer | 60秒 |
| 服务器 | self-harness-todo.timer | 3600秒 |
| PC 用户 | self-harness-pc.timer | 3600秒 |

周期来自 schedule 配置。

```sh
.venv/bin/python schedule.py --role server --install
.venv/bin/python schedule.py --role pc --install
```

schedule.py 默认打印单元，加 --install 写入并启用。服务器单元位于 /etc/systemd/system，PC 用户单元位于 ~/.config/systemd/user。

```sh
journalctl -u self-harness-ingest.service -u self-harness-todo.service
systemctl --user status self-harness-pc.service
```

PC 采集使用该机器的 ActivityWatch 和用户 systemd 会话。手机端沿用已确认的定时上传流程。

相关资源：[采集工作流](../workflows/collection.md)、[配置](../configuration.md)。
