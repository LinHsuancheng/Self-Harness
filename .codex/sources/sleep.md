# 睡眠来源

输入 CSV 每行：`阶段,开始时间,结束时间`，第一行是数据。解析保存阶段、实际区间和秒数。

记录标识使用分期开始时间，阶段与结束时间变化保存为修订。

operator 将实际连续分期组合为睡眠过程，支持任意时段入睡和多次睡眠。连接间隔由 `sources.sleep.summary.session_gap_minutes` 提供，默认30分钟。

| 指标 | 含义 |
| --- | --- |
| sleep_hours | 与报告范围相交的睡眠时长 |
| attributed_sleep_hours | 在报告范围内结束的完整睡眠时长 |
| daily_average_hours | 完整睡眠时长 / 有完整睡眠结束的日期数 |
| session_count / average_session_hours | 完整睡眠次数与每次平均长度 |
| stages | 分期时长与占比 |
| sleep_start_distribution / wake_distribution | 入睡与起床的六小时时段分布 |

日报还给出完整 sessions。period 起止控制统计范围，睡眠过程按实际区间连接。

相关资源：[周期](../implementation/periods.md)、[有效数据量](../implementation/effective-data.md)。
