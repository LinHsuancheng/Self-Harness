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

所有命令可在 interface.py 后添加 --config。另外提供 todo-changes 与 pc-active-time，使用 --start/--end。

相关资源：[周期含义](../implementation/periods.md)、[operator](../implementation/operators.md)。
