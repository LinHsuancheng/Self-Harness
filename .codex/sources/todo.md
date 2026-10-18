# Microsoft To Do

fetcher 通过 MSAL 缓存授权调用 Microsoft Graph，读取列表、任务和 checklist，支持 Graph 分页。

一次采集形成完整 JSON 快照，包含 observed_at、complete 和 lists。缓存授权路径与客户端参数位于 sources.todo。

operator 返回完成数量及任务、列表完成分布、期初期末待办数量、待办任务明细（含标题、清单、优先级、状态与截止时间），以及出现、消失和变化数量。

完成统计按 completedDateTime 归属周期，额外读取报告期末之后第一份快照。任务状态变化使用相邻快照比较。

```sh
.venv/bin/python interface.py fetch todo
.venv/bin/python interface.py fetch todo --login
```

日常采集使用缓存授权；显式 login 用于维护授权。2026-10-13 已在采集服务器验证缓存授权采集与入库。

相关资源：[调度](../operations/scheduling.md)、[有效数据量](../implementation/effective-data.md)。
