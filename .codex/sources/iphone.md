# iPhone 屏幕时间

输入 CSV 每行：`快照时间,App,使用分钟数`，时长文字以“分钟”结束，第一行是数据。

parser 按快照时间组合为完整 App 列表。aggregation_window 来自 `sources.iphone_screen_time.aggregation_window`。

operator 按报告时区选择每天末次快照，汇总 total_minutes、daily_average_minutes、apps 的时长和占比。日报还给出 daily。

有效日期来自实际快照日期；每个报告周期都提供 App 分布与上期变化。

相关资源：[手机上传](mobile-upload.md)、[operator](../implementation/operators.md)。
