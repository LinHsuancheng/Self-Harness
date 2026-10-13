# SQLite 存储

路径：`database_dir/<source>.sqlite3`。实现：`interfaces/database.py`。

| 表 | 保存内容 |
| --- | --- |
| files | 原始路径、内容哈希、解析版本、采集时间、处理状态和错误 |
| materials | 记录标识、版本时间、观测时间、结束时间、内容、原始文件关联和解析版本 |

materials 的 version_at 表示修订时间依据，last_seen_at 表示该值已被观测到的最新版本。普通查询按记录标识选择 last_seen_at 最新的值。

材料与文件处理结果在同一事务保存。原始文件通过路径关联，内容保存在 gzip 归档中。

相关资源：[入库与修订](../implementation/ingestion.md)、[原始文件](raw.md)。
