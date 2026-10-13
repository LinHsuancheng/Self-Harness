# 架构与数据流

```text
数据源 → interface → observation → core → email
```

- interface 获取来源数据、解析、入库并生成统计材料。
- observation 保存 gzip 原始文件和每来源 SQLite 数据库。
- core 读取统一入口生成的周期材料，使用独立 prompt 分析并保存报告。
- email 将报告投递给配置的收件人。

当前交付覆盖数据采集、保存及周期统计，下一阶段建设 core 与 email。

本地来源在可访问来源的机器采集并上传，服务器来源由采集中心定时获取。上传、入库和报告分别调度。

相关资源：[接口职责](interfaces.md)、[采集工作流](../workflows/collection.md)、[报告工作流](../workflows/reporting.md)。
