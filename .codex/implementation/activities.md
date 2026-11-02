# 屏幕活动展示粒度

PC 的 activities 将浏览器展开为网站，与其他应用同表展示。每项提供 kind、name、minutes、share，网站另给主要页面 topics。

| 配置 | 默认值 | 用途 |
| --- | --- | --- |
| browser_apps | msedge.exe | 浏览器进程名 |
| summary.website_names | 示例配置中的域名映射 | 将同站域名归并为活动名称 |
| summary.min_activity_minutes | 1 | 将短活动汇入其他零散活动 |
| summary.page_titles_per_site | 3 | 日报主要标题数 |

share 使用 PC 总活跃时长作为分母。浏览器时长分配到网站与其余浏览器活动，形成统一分布。

周报每站展示1个主要标题，月报及以上侧重活动分布。长周期展示前10项活动并合并其余时长；完整数据先完成计算，再收敛展示。

operator.web_activity 提供完整网站和页面统计；query 提供事件详情。

`pc_screen_activity` 的 activities 来自截图分析类别（工作/开发、学习/阅读等），但分钟只计算截图候选区间与 ActivityWatch 活跃区间的交集。每项提供 kind、name、minutes、share；share 以 ActivityWatch 总活跃分钟为分母。没有截图语义覆盖的 ActivityWatch 时间显示为“未分类活跃”。截图的应用、主题和视觉 focus 保留在 summary 的 apps/topics/focus 中。

日报另外保留 `summary.timeline`，把连续的截图分析合并成 Computer-use Timeline，并直接显示行为摘要、应用和主题。周/月以上不携带 timeline，继续收敛为类别分布。

相关资源：[PC](../sources/pc.md)、[PC 截图活动](../sources/pc-screen-activity.md)、[周期](periods.md)。
