# 架构与数据流

```text
数据源 → interface → observation → core → email
```

- interface 获取来源数据、解析、入库并生成统计材料。
- observation 保存 gzip 原始文件和每来源 SQLite 数据库。
- core 读取统一入口生成的周期材料，使用独立 prompt 分析并保存报告。
- email 将报告投递给配置的收件人。

五来源采集、保存与周期统计，以及 core 分析与 Gmail 邮件投递均已完成并在服务器运行。截图观察 `pc_screen_activity` 作为新的 PC 语义来源，与 ActivityWatch 并行采集；日报在样本足够时优先使用截图分析，否则回退旧源。

本地来源在可访问来源的机器采集并上传，服务器来源由采集中心定时获取。上传、入库和报告分别调度。截图上传后由服务器销毁式分析器转换为 JSON，再进入同一 raw→parser→SQLite→report 链路。

相关资源：[接口职责](interfaces.md)、[采集工作流](../workflows/collection.md)、[PC 截图活动](../sources/pc-screen-activity.md)、[报告工作流](../workflows/reporting.md)。
