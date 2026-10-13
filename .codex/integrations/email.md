# 邮件与 Google OAuth

邮件通过 Gmail API `users/me/messages/send` 投递，授权 scope 为 `https://www.googleapis.com/auth/gmail.send`。报告 HTML 是邮件正文，并带有纯文本备用内容。

本地授权文件 `/home/victor/codefields/gmail-oauth/token-self-harness.json` 已通过 refresh 验证，文件权限为 `0600`。使用 `config.json` 的 `email.token_file` 指向 token，`email.to` 设置收件人。token 和 OAuth 客户端凭据不得提交 Git 或随普通代码同步。

邮件默认不发送。仅当运行报告命令时显式添加 `--send-email` 才会投递。先完成本地真实收件人验证，再安排服务器部署与周期运行。

相关资源：[报告工作流](../workflows/reporting.md)、[当前状态](../project/status.md)。
