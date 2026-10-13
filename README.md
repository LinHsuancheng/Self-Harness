# Self Harness：文件收集

当前只做一件事：接收 `POST /upload` multipart 表单中的 `type` 和 `file`，按来源分类，用 gzip 保存原文件。不解析内容，不生成 material，不做分析或邮件。

| type | 文件夹 |
| --- | --- |
| weight | weight |
| sleep time | sleep |
| app-screen-time | iphone_screen_time |
| pc_screen_time | pc_screen_time |
| todo | todo |

目录为 `raw/来源/接收日期/唯一前缀-原文件名.gz`。原文件名经过路径清理，同名上传不覆盖。已压缩文件原样保存，其他文件压缩后保存。对应关系和数据目录由 config.json 配置。

服务器：`/root/test-server`，服务：`self-harness-collector.service`。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp config.example.json config.json
.venv/bin/python server.py
# PC 单次采集并 gzip 上传
.venv/bin/python collect_activitywatch.py --config config.json
```

手机端保持原有定时上传方式。PC 定时采集和 Todo 定时拉取尚未安装。
原有项目与历史数据已归档，新目录不自动导入旧数据。
