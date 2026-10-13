# 有效数据量

每份来源材料通过 data_quality 描述实际计算依据。

| 字段 | 含义 |
| --- | --- |
| record_count | 范围内结构化记录数 |
| calendar_days | 范围触及的日历日期数 |
| effective_days | 有统计依据的日期数 |
| average_denominator | 实际采用的均值分母 |
| day_coverage | 有效日期 / 日历日期 |
| observed_from / observed_to | 实际观测范围 |
| observed_hours / time_coverage | 区间来源的覆盖小时与覆盖比例 |

体重均值采用测量数。iPhone 使用实际快照日期。PC 使用窗口与 AFK 共同覆盖的日期。Todo 使用快照及实际完成证据的日期，另给 completion_count。

睡眠日均采用完整睡眠结束日期数，observed_days 另外表示分期覆盖的日期数。完整过程与区间时长分别由 attributed_sleep_hours 和 sleep_hours 表达。

统计值为 null 表示该项缺少有效依据；观测到的零值保留为零。上期比较携带上期 data_quality，缺少比较依据的差值为 null。

相关资源：[operator](operators.md)、[来源](../sources/index.md)。
