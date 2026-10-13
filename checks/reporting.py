"""Checks for structured report validation and HTML rendering."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.run import _render, _validated_output


result = {
    "title": "专注稳定的一天",
    "period_label": "2026-10-13",
    "summary": "主要时间投入在工作与学习。",
    "observations": {
        "sleep": "睡眠约7小时。",
        "weight": "体重近期稳定。",
        "tasks": "完成课程作业和项目调试。",
        "device_usage": "主要时间投入在开发和学习。",
    },
    "changes": [
        {"area": "睡眠", "observation": "记录缺失", "trend": "暂无可比较数据"},
    ],
    "recommendations": [
        {"action": "明天记录睡眠", "reason": "本期没有睡眠材料"},
    ],
}

validated = _validated_output(SimpleNamespace(status="completed", output_text=json.dumps(result)))
assert validated == result
html = _render(validated)
assert "睡眠约7小时" in html and "暂无可比较数据" in html
assert "明天记录睡眠" in html and "本期没有睡眠材料" in html
assert "{{" not in html and "数据覆盖" not in html

empty_changes = dict(result, changes=[])
assert _validated_output(SimpleNamespace(status="completed", output_text=json.dumps(empty_changes))) == empty_changes

invalid = dict(result, changes=[{"area": "睡眠", "observation": "缺失", "trend": 2}])
try:
    _validated_output(SimpleNamespace(status="completed", output_text=json.dumps(invalid)))
except ValueError:
    pass
else:
    raise AssertionError("non-string structured report values must be rejected")

invalid = dict(result, observations=dict(result["observations"], weight=2))
try:
    _validated_output(SimpleNamespace(status="completed", output_text=json.dumps(invalid)))
except ValueError:
    pass
else:
    raise AssertionError("non-string observations must be rejected")

unsafe = dict(result, observations=dict(result["observations"], sleep="<script>"))
assert "&lt;script&gt;" in _render(unsafe)
print("Structured report checks passed")
