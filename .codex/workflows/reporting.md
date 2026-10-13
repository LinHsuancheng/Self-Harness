# 报告与反馈工作流

目标流程：读取周期材料与历史 → 使用独立 prompt 分析 → 保存报告 → 邮件投递。

operator.context 已提供五来源的周期材料、有效数据量和上期变化，作为 core 的输入。

报告围绕四个问题组织：

1. 这段时间发生了什么？
2. 相比过去有什么变化？
3. 哪些观察值得关注，依据是什么？
4. 下一步可以尝试什么调整？

下一阶段实现 core 单次运行入口、报告 prompt、磁盘报告保存与 Google OAuth 邮件投递，并由系统任务周期运行。

相关资源：[operator](../implementation/operators.md)、[邮件资源](../integrations/email.md)。
