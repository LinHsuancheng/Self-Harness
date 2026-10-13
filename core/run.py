"""Generate one HTML report from the interface's period context."""

import argparse
from datetime import date as CalendarDate
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
LEVELS = ("day", "week", "month", "quarter", "half-year", "year")
FIELDS = ("title", "period_label", "summary", "observations", "changes", "recommendations")
SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "period_label": {"type": "string"},
        "summary": {"type": "string"},
        "observations": {"type": "array", "items": {"type": "string"}},
        "changes": {"type": "array", "items": {"type": "string"}},
        "recommendations": {"type": "array", "items": {"type": "string"}},
    },
    "required": list(FIELDS),
    "additionalProperties": False,
}
SOURCE_LABELS = {
    "weight": "体重", "sleep": "睡眠", "iphone_screen_time": "手机屏幕时间",
    "pc_screen_time": "电脑屏幕时间", "todo": "待办事项",
}


def _items(values):
    return "".join(f"<li>{escape(value, quote=True)}</li>" for value in values) or "<li>暂无可据实列出的内容。</li>"


def _coverage(context):
    rows = []
    for source, material in sorted(context.items()):
        quality = material["data_quality"]
        name = escape(SOURCE_LABELS.get(source, source), quote=True)
        days = quality["effective_days"]
        total = quality["calendar_days"]
        records = quality["record_count"]
        rows.append(f"<tr><th scope=\"row\">{name}</th><td>{days} / {total} 天</td><td>{records} 条</td></tr>")
    return "".join(rows)


def _render(result, context):
    template = (HERE / "templates" / "report.html").read_text(encoding="utf-8")
    values = {
        "TITLE": escape(result["title"], quote=True),
        "PERIOD_LABEL": escape(result["period_label"], quote=True),
        "SUMMARY": escape(result["summary"], quote=True),
        "OBSERVATIONS": _items(result["observations"]),
        "CHANGES": _items(result["changes"]),
        "RECOMMENDATIONS": _items(result["recommendations"]),
        "COVERAGE": _coverage(context),
    }
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda match: values[match.group(1)], template)


def _validated_output(response):
    if response.status != "completed":
        raise ValueError(f"DeepSeek 响应未完成：{response.status}")
    if not response.output_text or not response.output_text.strip():
        raise ValueError("DeepSeek 返回了空报告")
    result = json.loads(response.output_text)
    if not isinstance(result, dict) or set(result) != set(FIELDS):
        raise ValueError("DeepSeek 返回的报告字段不完整或包含额外字段")
    if any(not isinstance(result[key], str) for key in FIELDS[:3]) or any(
        not isinstance(result[key], list) or any(not isinstance(item, str) for item in result[key])
        for key in FIELDS[3:]
    ):
        raise ValueError("DeepSeek 返回的报告字段类型无效")
    return result


def run(config_path, level, date) -> Path:
    """Generate and atomically save one period's report."""
    if level not in LEVELS:
        raise ValueError(f"不支持的报告周期：{level}")
    if CalendarDate.fromisoformat(date).isoformat() != date:
        raise ValueError("日期必须使用 YYYY-MM-DD 格式")
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    interface_level = "halfyear" if level == "half-year" else level
    command = [sys.executable, str(ROOT / "interface.py"), "--config", str(config_path),
               "context", "--level", interface_level, "--date", date]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"interface context 失败：{exc.stderr.strip() or exc}") from exc
    context = json.loads(completed.stdout)
    if not isinstance(context, dict):
        raise ValueError("interface context 未返回来源对象")

    load_dotenv(ROOT / ".env")
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("缺少 DEEPSEEK_API_KEY；请在仓库根目录 .env 中配置")
    try:
        response = OpenAI(
            api_key=key,
            base_url=os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
        ).responses.create(
            model=os.getenv("DEEPSEEK_MODEL") or "deepseek-flash",
            instructions=(HERE / "prompts" / "report.md").read_text(encoding="utf-8"),
            input=json.dumps(context, ensure_ascii=False),
            text={"format": {"type": "json_schema", "name": "self_harness_report", "strict": True, "schema": SCHEMA}},
        )
        result = _validated_output(response)
    except Exception as exc:
        raise RuntimeError(f"DeepSeek 报告生成失败：{str(exc).replace(key, '[REDACTED]')}") from exc

    html = _render(result, context)
    reports_dir = Path(config.get("reports_dir", "./reports"))
    if not reports_dir.is_absolute():
        reports_dir = config_path.parent / reports_dir
    reports_dir.mkdir(parents=True, exist_ok=True)
    output = reports_dir / f"{level}-{date}.html"
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=reports_dir,
                                         prefix=f".{output.name}.", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(html)
        os.replace(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output


def main():
    parser = argparse.ArgumentParser(description="生成单个周期的中文 HTML 报告")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--level", choices=LEVELS, required=True)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()
    try:
        print(run(args.config, args.level, args.date))
    except Exception as exc:
        print(f"报告生成失败：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
