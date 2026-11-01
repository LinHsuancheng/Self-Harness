# 验证已实现行为

```sh
.venv/bin/python checks/interfaces.py
.venv/bin/python checks/summaries.py
.venv/bin/python checks/periods.py
.venv/bin/python checks/screen.py
```

| 检查 | 覆盖的实现 |
| --- | --- |
| interfaces | CSV 解析、入库、修订、查询与来源快照 |
| summaries | 五类汇总、浏览器网站、活动分布与总时长 |
| periods | 日历周期、有效数据量、睡眠过程与区间统计 |
| screen | 截图材料标识、去重、敏感脱敏、空闲/活跃分钟、日报集成与边界截断 |

截图分析器可用合成图片和临时目录单独验证，不写入正式 raw/database：

```sh
.venv/bin/python screen_analyzer.py --config /tmp/screen-test/config.json --dry-run --max-batch 1
```

验证真实链路时只检查计数和状态：spool 原图减少、`raw/screen_capture` 图片在分析后消失、`interface.py status pc_screen_activity` 的 success 增长。不要 `cat` 截图、生成的 JSON 或数据库内容。

这些脚本使用临时数据目录验证计算。线上验证通过 CLI 读取实际材料。

文档调整检查链接和文件路径；代码调整运行与改动相关的已有检查。

相关资源：[开发工作流](../workflows/development.md)、[固定版本](../project/status.md)。
# 日报专项

日报时间与静态渲染使用纯合成检查，不读取本地真实配置或数据：

```sh
.venv/bin/python checks/periods.py
.venv/bin/python checks/reporting.py
```

`checks/periods.py` 覆盖 09:00 左闭右开边界、完整与截止时进行中的睡眠、逻辑日和 DST 真实小时；`checks/reporting.py` 覆盖当前 schema、HTML 转义、明确区间元数据、无脚本正文、截图 PC 区块及旧源回退。
