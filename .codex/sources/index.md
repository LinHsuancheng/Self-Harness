# 五个来源与截图观察

| source | 原始输入 | 资源 |
| --- | --- | --- |
| sleep | 手机 CSV | [睡眠](sleep.md) |
| weight | 手机 CSV | [体重](weight.md) |
| iphone_screen_time | 手机 CSV | [iPhone](iphone.md) |
| pc_screen_time | ActivityWatch JSON | [PC](pc.md) |
| pc_screen_activity | ShareX 截图经服务器视觉分析生成的 JSON | [PC 截图活动](pc-screen-activity.md) |
| todo | Microsoft Graph JSON | [Todo](todo.md) |

手机三类来源按已确认的外部定时流程上传，约定见[手机上传](mobile-upload.md)。`pc_screen_activity` 与 `pc_screen_time` 并行采集；日报优先截图源，样本不足时回退 ActivityWatch。
