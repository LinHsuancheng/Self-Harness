# PC 截图活动 pc_screen_activity

每 5 分钟用 ShareX 截取当前显示器，上传到采集服务器；服务器调用 DeepSeek 视觉模型生成结构化 JSON，入库后用于日报的 PC 屏幕活动部分。

```text
Windows 任务计划（交互式用户会话，每 5 分钟）
  ShareX -silent -ActiveMonitor -autoclose
    → Pictures\SelfHarness\spool\<timestamp>.jpg
  wsl.exe → automations/upload_screenshots.py
    → POST /upload (type=screen_capture, observed_at, JPEG)
    → 2xx 后删除本地原图

服务器 raw/screen_capture/<date>/<...>.jpg.gz + .meta.json   （临时）
  screen_analyzer.py（timer，60 秒）
    → DeepSeek Chat Completions（图片 + json_object）
    → screen.validate
    → raw/pc_screen_activity/<date>/<captured>-<sha8>.json.gz + .meta.json
    → 删除临时图片
  入库 timer → parser → pc_screen_activity.sqlite3
```

## 材料

一条材料对应一次截图分析。`observed_at` 是截图时间；记录标识为 `<UTC captured_at>|<sha256>`，因此同一画面在不同时间出现仍是不同样本，同一张图重复分析会落到同一记录。

| 字段 | 内容 |
| --- | --- |
| capture.id / sha256 / bytes / format / filename | 截图来源与完整性 |
| analysis.app / window_title / url | 前台应用、窗口和可见地址 |
| analysis.category | work、study、communication、entertainment、utilities、other |
| analysis.activity | coding、writing、reading、meeting、browsing、watching、gaming、designing、communicating、idle、other |
| analysis.topics | 最多 5 个项目/主题/文档名 |
| analysis.focus | deep、light、distracted、idle |
| analysis.sensitive | 是否命中敏感内容 |
| analysis.confidence | 0–1 |
| model / prompt_version | 分析与 prompt 版本 |

`sensitive=true` 时校验器强制 `app=private`，清空窗口标题、URL 和主题，summary 固定为“敏感内容，已省略”。

## 采样口径

每个截图视为 5 分钟样本，持续时间取 `min(sample_minutes, 下一张截图间隔, 周期结束)`。`focus=idle` 或 `activity=idle` 的样本计入覆盖和空闲分钟，不计入活跃分钟；分类、应用和主题只统计活跃样本。日报的有效日沿用 point-source 的观测日期，日均活跃分钟除以有效日。

截图是**语义精度**更高，不是时间分辨率更高：两次采样之间的行为可能遗漏，边界样本按样本窗口折算。日报的 PC 区注会明确“按每 5 分钟截图采样折算”。

## Computer-use Timeline

日报将截图分析 JSON 直接整理为 `summary.timeline`，并在 PC 区域渲染行为时间线。每段包含开始、结束、折算分钟、类别、行为、主要专注状态、应用、主题、摘要、样本数和平均置信度。该过程复用已经生成的截图分析结果，不发起第二次模型调用。

时间线按观测时间排序。相邻样本间隔不超过 `sample_minutes` 时，连续空闲样本互相合并、连续敏感样本互相合并，其他样本只在 `category` 与 `activity` 同时相同时合并；语义变化、空闲/活跃转换或更长空档会开始新段。应用和主题按首次出现去重，摘要使用该段最后一个非空描述，专注状态取覆盖分钟最多的值。

敏感段只显示固定的“敏感内容，已省略”，不携带应用或主题。时间线仅进入日报；周报及以上继续使用类别、应用、主题和专注分布。日报分析 prompt 可以使用时间线判断连续投入与上下文切换，但不得逐段复述。

## 销毁与隐私

- Windows 本地原图在上传返回 2xx 后删除；失败保留重试。
- 服务器在 JSON 与 sidecar 持久化、并通过 parser 自检后删除临时图片；鉴权、网络、限流、文件系统错误不删除；模型输出连续无法通过校验时按 `max_attempts` 丢弃并写 `failed.jsonl`（只含时间、文件名、错误类型）。
- 截图和摘要会发送到 DeepSeek API；敏感内容由模型判断并在入库前脱敏，但模型判断不是保证。
- 上传使用当前部署的 HTTP 8000 明文链路（用户当前选择）；截图为全屏内容，传输与服务器暴露面高于其他来源。
- `raw/screen_capture` 是临时目录；`raw/pc_screen_activity` 是持久 JSON 归档。

## 与 pc_screen_time 并行

ActivityWatch 的 `pc_screen_time` 继续采集和入库。日报在 `pc_screen_activity` 有足够样本（`report_min_samples`，默认 24）时使用新源，否则回退 `pc_screen_time`；只向模型发送一个 PC 来源。两套历史都保留，便于对照。

## 运行

服务器：

```sh
.venv/bin/python screen_analyzer.py --config config.json
.venv/bin/python interface.py ingest pc_screen_activity
.venv/bin/python interface.py status pc_screen_activity
.venv/bin/python interface.py summarize pc_screen_activity --level day --date 2026-11-01
```

Windows/WSL（项目外自动化）：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\automations\setup_sharex.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ..\automations\install_screenshot_task.ps1
```

ShareX 配置由 `../automations/configure_sharex.py` 合并；上传器配置在 `../automations/screenshots.config.json`。任务必须以交互式用户会话运行，否则无法截取桌面。任务通过 `wscript.exe` + 生成的 `run_screenshot_hidden.vbs` 隐藏启动，避免每 5 分钟弹出 PowerShell/控制台窗口。

相关资源：[原始文件](../data/raw.md)、[统一材料](../data/material.md)、[调度](../operations/scheduling.md)、[PC ActivityWatch](pc.md)。
