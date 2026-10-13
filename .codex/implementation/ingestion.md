# 入库与修订

入口：`operator.ingest`。文件获取、纯解析、SQLite 保存依次执行。

1. 扫描来源 gzip 文件，读取采集时间。
2. 计算内容哈希与解析配置版本。
3. 将来源内容转换为材料。
4. 在事务中保存材料和文件处理结果。

已处理文件直接跳过。新到达的同值记录更新观测版本水位；变化保存为修订。查询通过 last_seen_at 选择当前值。

同源快照保留不同采样时刻。睡眠以分期开始时间、体重以测量时间、PC 以 bucket/event ID、iPhone/Todo 以快照时间识别记录。

files 的状态包括 success、duplicate、failed。原始文件保留，`ingest --retry-failed` 执行重新处理；解析版本或来源解析配置变化触发重放。operator 展示配置单独参与汇总。

相关资源：[SQLite](../data/database.md)、[验证](../operations/verification.md)。
