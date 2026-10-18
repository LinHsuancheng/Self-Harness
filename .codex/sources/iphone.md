# iPhone 屏幕时间

输入 CSV 每行：`快照时间,App,使用分钟数`，时长文字以“分钟”结束，第一行是数据。

parser 按快照时间组合为完整 App 列表。aggregation_window 来自 `sources.iphone_screen_time.aggregation_window`。

operator 按 App 对自然日累计快照做差分，再拼接逻辑日区间。对于报告 `[D 09:00,D+1 09:00)`，iPhone 使用 `D日24点附近累计 - D日09点附近累计 + D+1日09点附近累计`；每 App 的负差值收敛为 0。手机每日在 09:00 与 24:00 附近上传，快照公式与报告逻辑日一致。

结果提供 total_minutes、daily_average_minutes、App 分布和 `coverage`。缺少任一关键快照时标记 `incomplete`，使用可计算部分或返回无数据，并给出缺失原因与实际覆盖起止。报告以普通口径文字说明快照计算，不解释成逐小时活动。

有效日期来自实际快照日期；多日周期逐自然日片段计算，避免跨午夜累计重置造成重复计数。每个报告周期都提供 App 分布与上期变化。

相关资源：[手机上传](mobile-upload.md)、[operator](../implementation/operators.md)。
