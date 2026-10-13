# Self Harness

当前完成接口层：原始文件采集与 gzip 归档 → 按来源解析 → 每来源 SQLite → 统一材料查询。报告模型和邮件属于下一阶段。

## 四部分

| 部分 | 实现 | 职责 |
| --- | --- | --- |
| fetcher | interfaces/fetcher.py | 读取配置的 raw 目录；通过 MSAL/Graph 获取 Todo；本地获取 ActivityWatch 并 gzip 上传 |
| parser | interfaces/parser.py | 纯解析五类数据，保留来源结构，校验时间和数值，不访问网络或数据库 |
| database | interfaces/database.py | 每来源一个 SQLite，保存文件处理状态、材料与修订 |
| operator | interfaces/operator.py | 入库、去重、区间查询、基线、状态、Todo 变化、PC 活跃时间 |

8000 上传服务独立运行，只接收文件、按 type 分类、gzip 保存原始内容及接收时间 sidecar，不执行解析。

## 配置和运行

需要 Python 3.10+。相对路径以配置文件目录为基准。

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp config.example.json config.json
# 文件收集服务
.venv/bin/python server.py
# 将来源目录的新文件入库；单独来源可加 sleep/weight/iphone_screen_time/pc_screen_time/todo
.venv/bin/python interface.py ingest
# 查看每个来源的处理、错误、待处理文件及最新观测状态
.venv/bin/python interface.py status
```

配置包括 raw 数据目录（data_dir）、database_dir、来源级 raw_dir、监听地址、时区、来源参数及运行周期。
手机端的 sleep time、weight、app-screen-time 定时上传属于外部约束，保持兼容。PC 使用 pc_screen_time，Todo 使用 todo。

体重单位 `sources.weight.unit` 和 iPhone 统计窗口 `sources.iphone_screen_time.aggregation_window` 当前为 null，未擅自推断。配置明确后再次 ingest 会按新解析配置重新处理。

## Todo 与 PC

```sh
# 服务器：使用缓存授权拉取列表、任务及 checklist，保存完整 raw 快照
.venv/bin/python interface.py fetch todo
# 仅首次/授权失效后的维护操作需要显式登录
.venv/bin/python interface.py fetch todo --login
# PC：读取 ActivityWatch、保存本地 gzip raw 并上传服务器
.venv/bin/python collect_activitywatch.py --config config.json
```

Todo cache_file 必须指向现有缓存，远端路径和客户端参数均通过 sources.todo 配置。失败的部分采集标记不完整，保留 raw，不能入库为有效快照。
PC 必须在能访问 ActivityWatch 的机器运行。上传失败保留本地 gzip 文件，可重新上传；不会伪装为成功。

## 查询

```sh
.venv/bin/python interface.py query sleep \
  --start 2026-10-11T00:00:00+08:00 --end 2026-10-14T00:00:00+08:00
.venv/bin/python interface.py latest-before weight --time 2026-10-13T00:00:00+08:00
# core 使用的通用入口：每来源的统计汇总
.venv/bin/python interface.py context \
  --start 2026-10-13T00:00:00+08:00 --end 2026-10-14T00:00:00+08:00
.venv/bin/python interface.py todo-changes \
  --start 2026-10-13T00:00:00+08:00 --end 2026-10-14T00:00:00+08:00
.venv/bin/python interface.py pc-active-time \
  --start 2026-10-13T00:00:00+08:00 --end 2026-10-14T00:00:00+08:00
```

细节 query 返回 source、observed_at、collected_at、data。比较时间为 UTC，范围左闭右开；区间按相交筛选，持续时间为零的事件不计入区间。
PC 活跃应用时长使用同主机 AFK 的 not-afk 区间与窗口区间相交，不能直接累加窗口或浏览器时间。多个主机分别输出。
Todo 的出现、消失、状态变化只代表相邻完整快照的差异，不证明准确事件时间或确定删除。缺失基线时明确标记。

## 数据与重放

```text
raw/<source>/<接收日期>/*.gz
raw/<source>/<接收日期>/*.gz.meta.json  # 新上传文件的实际接收时间
raw/pc_screen_time/.../*.receipt.json  # PC 本地上传回执
database/<source>.sqlite3
```

原始文件和凭据不提交 Git。旧接收文件没有 sidecar 时使用文件 mtime 作为采集时间，观测时间始终从内容读取。
已处理文件跳过；新到达的重复内容推进版本水位，不重复生成同值业务记录；变化保留修订。睡眠以分期开始时间识别记录；PC 以 bucket+event ID 识别，以快照结束时间选当前版本。数据库保留修订，普通查询返回当前版本。
解析失败记录错误并保留 raw，不影响其他来源和上传。修复后用 `ingest --retry-failed` 重试；解析版本或来源配置变化会重新处理旧文件。
数据库可从 raw 重建，迁移时同时搬运 raw、数据库、授权缓存并更新配置。只应通过本项目流程写入 raw，已处理文件不原地修改。

## 自动运行

```sh
# 在采集中心安装入库和 Todo 两个 systemd timer
.venv/bin/python schedule.py --role server --install
# 在 PC 当前用户安装 ActivityWatch timer
.venv/bin/python schedule.py --role pc --install
```

不加 --install 只打印单元。周期来自 schedule 配置，默认入库 60 秒、Todo/PC 3600 秒；修改配置后重新安装单元。
服务使用各自机器的当前项目路径与 Python，配置不依赖固定 IP。接收服务部署文件 collector.service 中路径按目标环境修改。

当前部署：服务器 /root/test-server，self-harness-collector 接收服务；self-harness-ingest.timer、self-harness-todo.timer；PC 用户 self-harness-pc.timer。PC 用户 timer 依赖该用户的 systemd 会话和 ActivityWatch 正在运行，机器离线时不能采集上传。

```sh
systemctl status self-harness-collector.service
systemctl list-timers 'self-harness-*'
journalctl -u self-harness-ingest.service -u self-harness-todo.service
systemctl --user status self-harness-pc.service
```

## 验证

`.venv/bin/python checks/interfaces.py` 使用临时目录和标准库，验证 CSV 首行、重复文件、修订回退、跨日区间、失败隔离、PC 乱序水位与 AFK 时间、Todo 完整性和快照基线、iPhone 快照保留。不发送邮件，不访问外部来源。

## 汇总 operator

```sh
.venv/bin/python interface.py summarize weight \
  --start 2026-10-13T00:00:00+08:00 --end 2026-10-14T00:00:00+08:00
.venv/bin/python interface.py context \
  --start 2026-10-13T00:00:00+08:00 --end 2026-10-14T00:00:00+08:00
```

`summarize` 返回单个来源的 `source`、`period` 和 `summary`；`context` 返回全部来源的汇总，供 core 直接读取。细节继续由 query 查询。

| 来源 | summary |
| --- | --- |
| 体重 | min、max、mean、last、change、measurement_count、unit |
| 睡眠 | sleep_hours、awake_hours、start、end、stages |
| iPhone | total_minutes、按时长排序的 apps（minutes/share）、daily |
| PC | total_minutes、统一 activities（应用/网站、minutes/share/topics）、有活动的 hourly |
| Todo | completed_count、completed_tasks、pending_count、appeared_count、disappeared_count、changed_count |

iPhone 取报告时区每天末次快照计算分布。睡眠按查询区间统计各阶段时长。PC 汇总复用现有活跃应用计算，按小时输出使用分布。Todo 按实际完成时间统计，并读取期末之后第一份快照捕获跨日采集的完成任务；期末状态使用区间内最新快照。

运行 `.venv/bin/python checks/summaries.py` 可验证五类汇总和精简 context 的计算结果。

PC 的 activities 将浏览器展开为网站，与其他应用使用统一的时长和全天占比分布，浏览器容器不重复计入。扩展 URL 和标题按网站归并，主要页面标题通过 topics 返回。sources.pc_screen_time.summary 配置 min_activity_minutes（默认1分钟）、page_titles_per_site（默认3）和 website_names（域名归并名称）；短活动合并为其他零散活动，浏览器未匹配到网页的时长一并保留。默认浏览器为 msedge.exe，可通过 browser_apps 配置。完整网站及页面分布仍可通过 operator.web_activity 获取，原始 URL 保留在细节 query 中。

## 多周期统计（固定版）

```sh
# 月报：自动计算10月完整日期范围
.venv/bin/python interface.py context --level month --date 2026-10-13
# 单来源周报
.venv/bin/python interface.py summarize sleep --level week --date 2026-10-13
# 自定义范围与展示周期
.venv/bin/python interface.py context --level year \
  --start 2026-01-01T00:00:00+08:00 --end 2027-01-01T00:00:00+08:00
```

level 支持 day/week/month/quarter/halfyear/year。day/week 趋势按日、month 按自然周、quarter/halfyear/year 按月；所有模式都提供五来源的 summary、trend、comparison、highlights 和 data_quality。

有效数据量：record_count 为区间有效记录数，calendar_days 为报告日数，effective_days 为有统计依据的日数，average_denominator 为实际均值分母。区间来源还有 observed_hours/time_coverage；缺失分桶返回 null，真实观测到的零值保留为零。日均指标使用有效日，体重均值使用实际测量数。睡眠有效日按完整睡眠的结束日期计算，observed_days 另外记录分期实际覆盖的日期数。

睡眠 sleep_hours 统计与报告区间相交的时长，attributed_sleep_hours 统计在区间内结束的完整睡眠；daily_average_hours 使用后者除以有效日。任意时间入睡和一天多次睡眠都支持。session_gap_minutes 控制连续睡眠过程的连接间隔，默认30分钟。

上期比较返回同类周期边界及其有效数据量。统计和比较均使用完整结构化记录；展示层收敛长周期的活动与标题数量。各来源独立计算，没有每日缓存层。

验证：`checks/interfaces.py`、`checks/summaries.py`、`checks/periods.py`。报告模型和邮件仍是后续阶段。
