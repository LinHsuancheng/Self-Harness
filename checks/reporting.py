"""Synthetic checks for structured validation and static morning-report rendering."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.run import _render, _validated_output, _select_pc_context

result={"title":"专注稳定的一天","period_label":"2026-10-13","summary":"主要时间投入在工作与学习。",
        "observations":{"sleep":"睡眠约8小时。","weight":"体重稳定。","tasks":"完成项目调试。",
                        "pc_usage":"主要用于开发。","iphone_usage":"仅有累计快照。"},
        "changes":[],"recommendations":[{"action":"继续保持","reason":"节律稳定"}]}
period={"start":"2026-10-13T09:00:00+08:00","end":"2026-10-14T09:00:00+08:00"}
summary={"daily_average_hours":8,"stages":[{"stage":"核心睡眠","hours":8,"share":1}],
         "sessions":[{"start":"2026-10-13T23:00:00+08:00","end":"2026-10-14T07:00:00+08:00","sleep_hours":8,"complete":True}]}
context={"sleep":{"level":"day","period":period,"summary":summary,"comparison":{"metrics":{}}},
         "weight":{"level":"day","period":period,"summary":{"mean":None},"comparison":{"metrics":{}}},
         "todo":{"level":"day","period":period,"summary":{}},
         "pc_screen_time":{"level":"day","period":period,"summary":{"hourly":[]},"comparison":{"metrics":{}}},
         "iphone_screen_time":{"level":"day","period":period,"summary":{"daily_average_minutes":120,"total_minutes":120,
             "apps":[{"app":"阅读","minutes":90,"share":.75},{"app":"沟通","minutes":30,"share":.25}],
             "daily":[{"date":"2026-10-13","minutes":120}],"coverage":{"estimated":True,"incomplete":False,"reason":"使用09点与24点附近快照计算","covered_from":"2026-10-13T08:58:00+08:00","covered_to":"2026-10-14T08:59:00+08:00"}},"comparison":{"metrics":{}}}}

validated=_validated_output(SimpleNamespace(status="completed",output_text=json.dumps(result)))
html=_render(validated,context,"Asia/Singapore",generated_at="2026-10-14T09:00:03+08:00")
assert "2026-10-13 09:00" in html and "2026-10-14 09:00" in html
assert "Asia/Singapore" in html and "iPhone 按每日 09:00 与 24:00 附近的累计快照计算" in html
assert "120" in html and "快照约覆盖 08:58→08:59" in html
assert "<script" not in html and "overflow: hidden" not in html
assert "睡眠约8小时" in html and "{{" not in html
assert "统计范围内的活跃窗口" in html
screen_context=dict(context)
screen_context.pop("pc_screen_time")
screen_context["pc_screen_activity"]={"level":"day","period":period,"data_quality":{"record_count":120},
    "summary":{"daily_average_minutes":300,"sample_minutes":5,"activities":[
        {"kind":"category","name":"工作/开发","minutes":300,"share":1.0},
        {"kind":"category","name":"学习/阅读","minutes":120,"share":.4}],
        "hourly":[{"start":"2026-10-13T10:00:00+08:00","minutes":30}]},
    "comparison":{"metrics":{"daily_average_minutes":{"current":300,"previous":250,"change":50}}}}
screen_html=_render(validated,screen_context,"Asia/Singapore",generated_at="2026-10-14T09:00:03+08:00")
assert "每 5 分钟截图采样折算" in screen_html and "300" in screen_html
pc_config={"sources":{"pc_screen_activity":{"report_min_samples":24}}}
low=dict(context); low["pc_screen_activity"]={"summary":{"daily_average_minutes":100},"data_quality":{"record_count":10}}
_select_pc_context(low,pc_config)
assert "pc_screen_time" in low and "pc_screen_activity" not in low
high=dict(context); high["pc_screen_activity"]={"summary":{"daily_average_minutes":100},"data_quality":{"record_count":30}}
_select_pc_context(high,pc_config)
assert "pc_screen_time" not in high and "pc_screen_activity" in high
empty=dict(context); empty["pc_screen_activity"]={"summary":{"daily_average_minutes":None},"data_quality":{"record_count":0}}
_select_pc_context(empty,pc_config)
assert "pc_screen_time" in empty and "pc_screen_activity" not in empty
unsafe=dict(result,observations=dict(result["observations"],sleep="<script>"))
assert "&lt;script&gt;" in _render(unsafe,context,"Asia/Singapore",generated_at="2026-10-14T09:00:03+08:00")
if len(sys.argv)>1:
    Path(sys.argv[1]).write_text(html,encoding="utf-8")
print("PASS: current schema, escaped content, static report, explicit period metadata, screenshot PC source")
