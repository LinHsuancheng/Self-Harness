# 体重来源

输入 CSV 每行：`测量时间,数值`，第一行是数据。解析保存实际测量及 `sources.weight.unit` 中的单位。

记录标识使用测量时间；同一测量的数值变化保存为修订。

operator 返回 measurement_count、min、max、mean、last、change 和 unit。mean 的分母是实际测量数，change 比较末次值与期初基线。

周期趋势使用相应时间桶里的测量；data_quality 给出测量记录数和有效测量日期数。

相关资源：[材料](../data/material.md)、[有效数据量](../implementation/effective-data.md)。
