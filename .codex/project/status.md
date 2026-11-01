# 当前交付状态

2026-10-13，固定版本：operators-v0.1.0，提交 0e310e6。

已交付：
- 五来源原始数据获取、gzip 归档与统一解析。
- 每来源 SQLite、处理记录和修订查询。
- 细节查询与日/周/月/季/半年/年统计。
- 应用、网站、页面活动的分层展示。
- 有效数据量、上期比较与趋势。
- 服务器入库、Todo 获取、PC 上传的自动调度。

六种模式已用服务器实际数据运行。当前样本下，日报约1.6秒、年报约4.4秒。

本地 Git 工作区已实现单次 core 报告生成与 Gmail 投递：调用 interface 获取周期材料，通过 DeepSeek 生成结构化内容并渲染为 HTML。2026-10-14 使用服务器五来源材料完成 2026-10-13 日报生成和真实邮件投递。

当前 GitHub `main` 已部署到服务器 `/root/test-server`；配置、授权、原始数据、数据库和 Python 环境仍在服务器，采集服务 active。服务器日报每日 06:00（Asia/Singapore）生成昨天报告并发送邮件。

## 截图观察

2026-11-01 本地实现 `pc_screen_activity`：Windows ShareX 每 5 分钟截图，WSL 上传，服务器 `screen_analyzer.py` 调用 DeepSeek 视觉模型生成 JSON 后删除图片，parser 入库，日报优先新源、样本不足回退 `pc_screen_time`。旧 ActivityWatch 继续采集，作为并行期对照。合成图片已跑通上传、分析、入库和汇总；线上部署与 ShareX 安装待执行。

相关资源：[PC 截图活动](../sources/pc-screen-activity.md)、[部署](../operations/deployment.md)、[历史](../history/index.md)。
