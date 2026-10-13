# AGENTS.md

## 目标与工作原则

建立自动采集、周期分析和邮件反馈的个人 Self Harness。

- 围绕“做什么”组织设计、实现和文档，使用 ponytail 完成当前目标需要的最小版本。
- 按实际数据和已批准需求推进，保持实现与验证简洁。
- 采集、来源统计、报告分析和邮件投递分别承担各自职责。
- 每个来源使用 fetcher、parser、database、operator 四部分；分析端通过统一入口读取材料。
- 服务器、路径、来源地址、授权位置、时区和运行周期通过配置管理。
- 本地 Git 工作区是唯一代码源；服务器 `/root/test-server` 是运行副本。开发只改本地代码，部署时同步 Git 跟踪文件。
- 提交遵循 `.gitignore`；凭据、原始数据、数据库和本地环境保留在部署环境。
- 历史资料保留作参考，在完成对应实现后整理回收；维护线上收集服务的连续运行。

## 资源路由

按当前任务读取对应资源，细节以资源文档和实际实现共同说明。

| 当前任务 | 读取资源 |
| --- | --- |
| 理解项目目标和工作流 | [README](README.md)、[架构概览](.codex/architecture/overview.md) |
| 修改来源接口或接入来源 | [接口职责](.codex/architecture/interfaces.md)、[来源索引](.codex/sources/index.md)、对应来源文档 |
| 处理上传与原始文件 | [手机上传约定](.codex/sources/mobile-upload.md)、[原始文件](.codex/data/raw.md) |
| 修改解析和统一格式 | [材料格式](.codex/data/material.md)、对应来源文档 |
| 修改数据库或入库 | [SQLite](.codex/data/database.md)、[修订与入库](.codex/implementation/ingestion.md) |
| 修改 operator 与展示粒度 | [汇总操作](.codex/implementation/operators.md)、[活动粒度](.codex/implementation/activities.md) |
| 修改周期或有效数据统计 | [周期计算](.codex/implementation/periods.md)、[有效数据量](.codex/implementation/effective-data.md) |
| 安装、配置或运行命令 | [配置](.codex/configuration.md)、[安装](.codex/operations/setup.md)、[CLI](.codex/operations/cli.md) |
| 部署、调度或迁移 | [部署](.codex/operations/deployment.md)、[调度](.codex/operations/scheduling.md)、[迁移](.codex/operations/migration.md) |
| 开发与验证 | [文件地图](.codex/project/files.md)、[开发工作流](.codex/workflows/development.md)、[验证](.codex/operations/verification.md) |
| 建设报告分析与邮件 | [报告工作流](.codex/workflows/reporting.md)、[邮件资源](.codex/integrations/email.md) |
| 查看已交付版本与历史 | [当前状态](.codex/project/status.md)、[历史资料](.codex/history/index.md) |

全部资源见 [.codex 索引](.codex/README.md)。
