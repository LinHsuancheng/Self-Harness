# 手机端上传约定

用户已确认：睡眠、体重和 iPhone 屏幕时间由外部自动化定时发送到采集服务器 8000 端口。

接口：`POST /upload`，multipart 表单字段为 type 和 CSV file。

| 来源 | type | 默认来源目录 |
| --- | --- | --- |
| 体重 | weight | weight |
| iPhone 使用 | app-screen-time | iphone_screen_time |
| 睡眠 | sleep time | sleep |

这些 type 的空格和连字符属于实际上传约定。来源目录映射由 folders 配置提供。

2026-10-13 已实际确认三类上传返回 200，文件分类保存并通过 gzip 解压检查。项目承接接收、归档和后续处理，手机端调度沿用现有外部流程。

相关资源：[原始文件](../data/raw.md)、[部署](../operations/deployment.md)。
