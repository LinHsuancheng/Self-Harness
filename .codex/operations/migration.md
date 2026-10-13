# 迁移与数据重建

1. 复制项目、raw 原始文件、SQLite 数据库和授权缓存。
2. 更新配置中的服务器地址、数据路径、来源 URL 与授权位置。
3. 安装目标 Python 环境并生成目标调度单元。
4. 运行 status、context，确认材料输出。

SQLite 可通过原始文件重新入库生成。原始数据和授权文件按各自目录搬运。

文件处理状态记录在各来源 files 表中。解析版本或来源解析配置变化后，ingest 会重放对应文件；已记录的处理失败可用 `ingest --retry-failed` 执行重试。

相关资源：[原始文件](../data/raw.md)、[入库](../implementation/ingestion.md)。
