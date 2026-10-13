# Operator 与周期材料

| 操作 | 返回 |
| --- | --- |
| ingest | 来源文件处理结果 |
| query(start,end) | 统一格式的细节材料 |
| latest_before(time) | 此前最近记录或快照 |
| status | 处理数量、观测时间和待处理情况 |
| summarize(start,end,level) | 单来源周期材料 |
| context(start,end,level) | 五来源周期材料 |

周期材料统一包含 source、level、period、data_quality、summary、trend、comparison、highlights。

- summary 汇总本期具体指标，含义见各来源文档。
- trend 按周期策略展示时间序列。
- comparison 给出上期边界、有效数据量、数值和分布变化。
- highlights 给出趋势中的主要数值重点。

数据访问位于 operator.py，周期组织与有效量计算位于 report.py，来源基础统计位于 summary.py，日历计算位于 periods.py。

当前固定实现使用来源独立计算，边界、统计和存储各自组织。

相关资源：[周期](periods.md)、[有效数据](effective-data.md)、[活动粒度](activities.md)。
