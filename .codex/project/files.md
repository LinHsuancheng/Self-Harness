# 文件地图

| 文件 | 职责 |
| --- | --- |
| server.py | 上传接收、分类、gzip 归档与接收信息 |
| ../automations/collect_activitywatch.py | PC 采集上传自动化脚本（项目外） |
| ../automations/install_activitywatch_task.ps1 | 注册 Windows 每小时任务（项目外） |
| interface.py | 获取、入库、查询与周期统计 CLI |
| core/run.py | 获取周期材料、调用 DeepSeek、校验结构化报告并生成 HTML |
| core/mail.py | 通过 Gmail OAuth 投递已保存的 HTML 报告 |
| core/prompts/{day,week,month,quarter,half-year,year}.md | 按周期组织分析的独立 prompt；共享 day.md 的输出契约 |
| core/templates/report.html | 本地渲染的独立 HTML 报告模板 |
| schedule.py | systemd 单元生成与安装 |
| collector.service | 接收服务单元 |
| config.example.json | 配置示例 |
| .env.example | DeepSeek 环境变量示例（真实 `.env` 不提交） |
| reports/ | 默认 HTML 报告输出目录；可通过 `reports_dir` 修改。自定义输出目录若位于仓库内，需单独加入 Git 忽略规则 |
| requirements.txt | Python 依赖 |
| interfaces/fetcher.py | 文件、Graph 和 ActivityWatch 获取 |
| interfaces/parser.py | 五来源纯解析 |
| interfaces/database.py | SQLite、处理状态与修订 |
| interfaces/operator.py | 统一操作与应用/网页时长计算 |
| interfaces/summary.py | 来源基础统计与活动展示 |
| interfaces/periods.py | 日历范围、上期和趋势分桶 |
| interfaces/report.py | 多周期材料与有效数据量 |
| checks/ | 已实现行为的可运行检查 |
| .codex/ | 架构、实现、来源和操作资源 |

README 介绍项目，AGENTS.md 路由工作资源。config.json、raw、database、auth 与 .venv 随部署环境管理。
