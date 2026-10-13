# 来源接口四部分

| 部分 | 职责 | 实现 |
| --- | --- | --- |
| fetcher | 从配置的位置获取数据并归档 | interfaces/fetcher.py |
| parser | 将原始内容转换为统一材料 | interfaces/parser.py |
| database | 保存来源材料、处理记录和修订 | interfaces/database.py |
| operator | 提供入库、细节查询和周期统计 | interfaces/operator.py |

parser 以输入内容计算结果；fetcher 承担来源访问；operator 封装数据操作，供分析端使用。

每个来源一个 SQLite 文件。共享工具实现文件读取、连接和事务等通用操作，来源保留自己的字段和统计含义。

接入来源时增加获取与解析逻辑、来源配置和来源统计，统一 context 入口按配置汇集来源结果。

相关资源：[材料](../data/material.md)、[来源索引](../sources/index.md)、[operator](../implementation/operators.md)。
