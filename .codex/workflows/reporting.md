# 报告与反馈工作流

流程：读取周期材料 → 使用独立 prompt 分析 → 保存 HTML 报告 → （后续）邮件投递。

`python -m core.run` 调用 `interface.py context` 读取五来源周期材料、有效数据量和上期变化，再通过 DeepSeek Responses API 生成结构化报告内容，由本地 HTML 模板渲染并保存。报告输出目录由 `reports_dir` 配置，默认为 `./reports`。

报告围绕四个问题组织：

1. 这段时间发生了什么？
2. 相比过去有什么变化？
3. 哪些观察值得关注，依据是什么？
4. 下一步可以尝试什么调整？

DeepSeek API key、base URL 和 model 从项目根目录的 `.env` 读取，示例见 `.env.example`。首次使用需复制示例并设置 `DEEPSEEK_API_KEY`。

下一阶段接入 Google OAuth 邮件投递；周期调度待邮件流程确定后再配置。

相关资源：[operator](../implementation/operators.md)、[邮件资源](../integrations/email.md)。
