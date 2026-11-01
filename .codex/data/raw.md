# 原始文件

收集服务在 `server.py` 接收 multipart `POST /upload`，字段为 `type` 与 `file`。按配置的来源目录和接收日期保存。

```text
raw/<source>/<date>/<unique-prefix>-<filename>.gz
raw/<source>/<date>/<unique-prefix>-<filename>.gz.meta.json
```

普通文件 gzip 压缩后保存，gzip 上传原样保存。唯一前缀由接收时间与随机标识组成。sidecar 记录上传 type、原文件名和 collected_at。

文件 fetcher 读取来源目录中的 gzip 文件，使用 sidecar 中的采集时间；准备阶段文件使用文件 mtime。PC 本地还保存上传回执 `*.receipt.json`。

## 截图临时目录

`screen_capture` 上传类型写入 `raw/screen_capture/<date>/`，文件为 gzip 压缩的 JPEG/PNG/WebP，sidecar 额外记录 `observed_at`、`sha256` 和 `bytes`。`screen_analyzer.py` 读取图片、调用视觉模型，然后把分析结果写成持久材料到 `raw/pc_screen_activity/<date>/`，最后删除临时图片和 sidecar。该临时目录不应被配置成 `sources`。

捕获侧（Windows/WSL）在 spool 中保留原图，上传返回 2xx 后删除；失败保留重试。

原始文件用于追溯、重新解析和迁移。

相关资源：[手机上传约定](../sources/mobile-upload.md)、[入库](../implementation/ingestion.md)。
