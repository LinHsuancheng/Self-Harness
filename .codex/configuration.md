# 配置

配置样例：[config.example.json](../config.example.json)。本地配置使用 config.json，相对路径以配置文件目录为基准。

| 字段 | 用途 |
| --- | --- |
| data_dir | 原始数据根目录 |
| database_dir | 每来源 SQLite 根目录 |
| reports_dir | HTML 报告输出目录，默认 `./reports` |
| email.token_file | Gmail OAuth token JSON 路径，可使用绝对路径；文件需留在本地/部署环境并保持私密 |
| email.to | `--send-email` 的收件人地址 |
| timezone | 报告时区 |
| listen | 接收服务 host/port |
| folders | 上传 type 到来源目录的映射 |
| max_upload_bytes / max_uncompressed_bytes | 上传与解压读取大小 |
| sources.<source>.raw_dir | 来源原始目录覆盖值 |
| sources.weight.unit | 体重单位 |
| sources.iphone_screen_time.aggregation_window | iPhone 统计窗口 |
| sources.sleep.summary.session_gap_minutes | 睡眠过程连接间隔 |
| sources.pc_screen_time | 浏览器与活动展示参数 |
| sources.todo | 缓存路径、client_id、authority、Graph 地址 |
| activitywatch | 来源 URL、回看小时数、上传 URL |
| schedule | 入库、Todo、PC 的运行秒数 |
| schedule.report_time | 服务器日报触发时间（HH:MM，使用 timezone） |

服务可用 SELF_HARNESS_CONFIG 指定配置路径，CLI 使用 --config。凭据存放于配置指定的位置，Git 提交遵循项目 .gitignore。

DeepSeek 设置放在项目根目录的 `.env`：`DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com`）和 `DEEPSEEK_MODEL`（默认 `deepseek-flash`）。`.env` 已加入 `.gitignore`，不要提交真实密钥。

相关资源：[安装](operations/setup.md)、[活动参数](implementation/activities.md)。
