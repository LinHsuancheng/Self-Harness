# PC ActivityWatch

本地 fetcher 从配置的 ActivityWatch 地址读取 AFK、窗口、浏览器三个事件流。collect_activitywatch.py 保存 gzip JSON 并以 `type=pc_screen_time` 上传。

| 事件流 | 主要字段 |
| --- | --- |
| afkstatus | status |
| currentwindow | app、title |
| web.tab.current | url、title、audible、incognito、tabCount |

每个事件保存 bucket、事件 ID、实际起止、秒数和来源字段。记录标识为 bucket + event ID，版本依据为原始快照结束时间。

应用活跃时长由同主机窗口与 not-afk 区间相交计算。网站活动进一步结合前台浏览器区间，按域名和页面标题汇总。

有效覆盖由窗口与 AFK 记录的时间交集计算。统计材料使用统一 activities，详见[活动粒度](../implementation/activities.md)。

相关资源：[本地采集](../workflows/collection.md)、[配置](../configuration.md)。
