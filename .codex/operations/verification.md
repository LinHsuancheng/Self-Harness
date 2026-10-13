# 验证已实现行为

```sh
.venv/bin/python checks/interfaces.py
.venv/bin/python checks/summaries.py
.venv/bin/python checks/periods.py
```

| 检查 | 覆盖的实现 |
| --- | --- |
| interfaces | CSV 解析、入库、修订、查询与来源快照 |
| summaries | 五类汇总、浏览器网站、活动分布与总时长 |
| periods | 日历周期、有效数据量、睡眠过程与区间统计 |

这些脚本使用临时数据目录验证计算。线上验证通过 CLI 读取实际材料。

文档调整检查链接和文件路径；代码调整运行与改动相关的已有检查。

相关资源：[开发工作流](../workflows/development.md)、[固定版本](../project/status.md)。
