# 报告与反馈工作流

流程：读取周期材料 → 使用独立 prompt 分析 → 保存 HTML 报告 → （可选）通过 Gmail 投递。

`python -m core.run` 调用 `interface.py context` 读取五来源周期材料、有效数据量和上期变化，再通过 DeepSeek Responses API 生成结构化报告内容，由本地 HTML 模板渲染并保存。报告输出目录由 `reports_dir` 配置，默认为 `./reports`。模板是无脚本的静态纵向晨报，明确显示统计起止、时区与生成时间；生成时间不属于活动统计范围。

六个周期 prompt 共享同一结构化输出：标题、周期、简要总结、睡眠/体重/任务/设备使用四类观察对象、变化对象数组和建议对象数组。日报 prompt 提供共同的观察字段与分析原则；其他周期保留自己的时间尺度。变化只在存在有效比较基准时输出，没有可比数据时返回空数组，不要求模型凑出变化。建议同样允许为空。

本地渲染器按结构化字段安全转义并生成 HTML，不展示原始数据覆盖表或逐条活动日志。新增或修改输出字段时，需同步更新 `core/run.py` 的 JSON Schema、校验、报告模板和 `checks/reporting.py`。

DeepSeek API key、base URL 和 model 从项目根目录的 `.env` 读取，示例见 `.env.example`。首次使用需复制示例并设置 `DEEPSEEK_API_KEY`。

手动运行时邮件默认关闭；显式添加 `--send-email` 后，使用 `config.json` 的 `email.token_file` 与 `email.to` 通过 Gmail API 投递 HTML 报告。服务器日报 timer 每天按配置时区生成昨天的报告并自动投递。示例缺省为新加坡时间 09:00，对应昨日 09:00 至今日 09:00；iPhone 只标示累计快照口径，PC 才展示真实小时汇总。OAuth token 留在本地/部署环境，不进 Git。

相关资源：[operator](../implementation/operators.md)、[邮件资源](../integrations/email.md)。
