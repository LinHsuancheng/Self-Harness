# CLI 操作

```sh
# Todo 原始采集、文件入库、来源状态
.venv/bin/python interface.py fetch todo
.venv/bin/python interface.py ingest
.venv/bin/python interface.py status

# PC 原始采集与上传
.venv/bin/python collect_activitywatch.py --config config.json

# 月度五来源材料
.venv/bin/python interface.py context --level month --date 2026-10-13

# 生成月报 HTML（先配置 .env 中的 DEEPSEEK_API_KEY）
.venv/bin/python -m core.run --config config.json --level month --date 2026-10-13

# 明确开启时，将生成的 HTML 报告通过 Gmail 发送给 config.json 的 email.to
.venv/bin/python -m core.run --config config.json --level month --date 2026-10-13 --send-email

# 按配置时区生成昨天的日报并邮件投递
.venv/bin/python -m core.run --config config.json --level day --date yesterday --send-email

# 单来源周期材料
.venv/bin/python interface.py summarize sleep --level week --date 2026-10-13

# 明确指定范围
.venv/bin/python interface.py context --level year \
  --start 2026-01-01T00:00:00+08:00 --end 2027-01-01T00:00:00+08:00

# 细节与基线
.venv/bin/python interface.py query weight \
  --start 2026-10-12T00:00:00+08:00 --end 2026-10-14T00:00:00+08:00
.venv/bin/python interface.py latest-before weight --time 2026-10-13T00:00:00+08:00
```

core 报告支持 day、week、month、quarter、half-year、year，输出到配置的 `reports_dir`（默认 `./reports`）。interface 命令可使用 `--config` 指定配置；另外提供 todo-changes 与 pc-active-time，使用 --start/--end。

相关资源：[周期含义](../implementation/periods.md)、[operator](../implementation/operators.md)。
