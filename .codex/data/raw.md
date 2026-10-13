# 原始文件

收集服务在 `server.py` 接收 multipart `POST /upload`，字段为 `type` 与 `file`。按配置的来源目录和接收日期保存。

```text
raw/<source>/<date>/<unique-prefix>-<filename>.gz
raw/<source>/<date>/<unique-prefix>-<filename>.gz.meta.json
```

普通文件 gzip 压缩后保存，gzip 上传原样保存。唯一前缀由接收时间与随机标识组成。sidecar 记录上传 type、原文件名和 collected_at。

文件 fetcher 读取来源目录中的 gzip 文件，使用 sidecar 中的采集时间；准备阶段文件使用文件 mtime。PC 本地还保存上传回执 `*.receipt.json`。

原始文件用于追溯、重新解析和迁移。

相关资源：[手机上传约定](../sources/mobile-upload.md)、[入库](../implementation/ingestion.md)。
