# 统一材料

| 字段 | 含义 |
| --- | --- |
| source | sleep、weight、iphone_screen_time、pc_screen_time 或 todo |
| observed_at | 实际观测时间，包含时区 |
| collected_at | 采集时间，包含时区 |
| data | 来源结构化内容与数值单位 |

睡眠和 PC 区间使用开始时间作为 observed_at，data 保存 start/end。数据库比较时间统一为 UTC。

| 来源 | 一条材料的粒度 |
| --- | --- |
| 睡眠 | 一段分期 |
| 体重 | 一次测量 |
| iPhone | 一次完整 App 使用快照 |
| PC | 一个 ActivityWatch 事件 |
| Todo | 一次完整列表、任务和 checklist 快照 |

parser 的内部记录另外携带记录标识、结束时间和版本时间，供数据库保存与修订选择。

相关资源：[数据库](database.md)、[来源](../sources/index.md)。
