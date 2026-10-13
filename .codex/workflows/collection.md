# 采集工作流

```text
手机定时上传 CSV ───────────┐
PC 采集 ActivityWatch → gzip ┴→ 接收服务 → raw 来源目录
服务器定时采集 Todo ─────────→ raw 来源目录
raw → 文件 fetcher → parser → SQLite
SQLite → operator → 周期统计材料
```

手机上传服务持续接收文件。服务器按分钟入库，Todo 与 PC 按配置周期采集。

采集、入库和统计各自运行，文件与处理记录连接这些步骤。原始文件保存采样内容，SQLite 保存材料和修订，operator 提供周期统计。

相关资源：[手机约定](../sources/mobile-upload.md)、[调度](../operations/scheduling.md)、[原始文件](../data/raw.md)。
