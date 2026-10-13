# 日历周期

start/end 控制统计范围，level 控制展示粒度。level/date 通过报告时区生成自然周期。

| level | 自然周期 | 趋势分桶 |
| --- | --- | --- |
| day | 自然日 | 日 |
| week | 周一至下一周一 | 日 |
| month | 自然月 | 自然周，首尾按范围截取 |
| quarter | 1/4/7/10月起的三个月 | 月 |
| halfyear | 1月或7月起的六个月 | 月 |
| year | 自然年 | 月 |

上期使用同类日历周期。范围为左闭右开，持续记录按实际相交部分计算时长。完整睡眠过程按结束时间归属。

periods.py 提供 bounds、previous、buckets，report.py 将这些边界应用到五个来源。日报 PC 另外提供小时统计。

相关资源：[CLI](../operations/cli.md)、[睡眠](../sources/sleep.md)。
