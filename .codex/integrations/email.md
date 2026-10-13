# 邮件与 Google OAuth 资源

准备阶段已找到 Gmail OAuth 发送实现：

- ../stream-sieve/stream_sieve/delivery/gmail_api.py
- /home/victor/codefields/gmail-oauth/auth.py
- /home/victor/codefields/gmail-oauth/send_test.py

实际授权缓存位于 /home/victor/codefields/gmail-oauth/token.json。发送 scope 为 gmail.send，发送路径为 Gmail API users/me/messages/send。

2026-10-13 的刷新尝试返回 invalid_grant；邮件阶段先恢复现有授权，再复用发送能力。

../noise-gate/noise_gate/delivery.py 提供 SMTP 发送参考。Google OAuth 的已确认资源位于 stream-sieve 与 gmail-oauth 项目。

报告模型、prompt、授权位置、收件人和运行周期在后续集成中通过配置提供。

相关资源：[报告工作流](../workflows/reporting.md)、[当前状态](../project/status.md)。
