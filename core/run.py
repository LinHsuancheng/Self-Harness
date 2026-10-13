"""Generate one HTML report from the interface's period context."""

import argparse
from datetime import date as CalendarDate, datetime, timedelta
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from openai import OpenAI
from .mail import send_report


ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
LEVELS = ("day", "week", "month", "quarter", "half-year", "year")
PROMPTS = {
    "day": "day.md",
    "week": "week.md",
    "month": "month.md",
    "quarter": "quarter.md",
    "half-year": "half-year.md",
    "year": "year.md",
}
FIELDS = ("title", "period_label", "summary", "observations", "changes", "recommendations")
OBSERVATION_FIELDS = ("sleep", "weight", "tasks", "device_usage")
CHANGE_FIELDS = ("area", "observation", "trend")
RECOMMENDATION_FIELDS = ("action", "reason")
SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "period_label": {"type": "string"},
        "summary": {"type": "string"},
        "observations": {
            "type": "object",
            "properties": {field: {"type": "string"} for field in OBSERVATION_FIELDS},
            "required": list(OBSERVATION_FIELDS),
            "additionalProperties": False,
        },
        "changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"area": {"type": "string"}, "observation": {"type": "string"},
                               "trend": {"type": "string"}},
                "required": list(CHANGE_FIELDS),
                "additionalProperties": False,
            },
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"action": {"type": "string"}, "reason": {"type": "string"}},
                "required": list(RECOMMENDATION_FIELDS),
                "additionalProperties": False,
            },
        },
    },
    "required": list(FIELDS),
    "additionalProperties": False,
}
def _change_items(changes):
    if not changes:
        return "<li>本期没有足够可比数据，暂无明确变化。</li>"
    return "".join(
        "<li><strong>{}</strong>：{} <span>{}</span></li>".format(
            escape(item["area"], quote=True), escape(item["observation"], quote=True),
            escape(item["trend"], quote=True),
        )
        for item in changes
    )


def _recommendation_items(recommendations):
    if not recommendations:
        return "<li>本期暂无需要尝试的调整。</li>"
    return "".join(
        "<li>{} <span>{}</span></li>".format(
            escape(item["action"], quote=True), escape(item["reason"], quote=True),
        )
        for item in recommendations
    )


def _observation_items(observations):
    labels = {"sleep": "睡眠", "weight": "体重", "tasks": "任务", "device_usage": "设备使用"}
    return "".join(
        "<li><strong>{}</strong>：{}</li>".format(
            labels[field], escape(observations[field], quote=True),
        )
        for field in OBSERVATION_FIELDS
    )


def _render(result):
    template = (HERE / "templates" / "report.html").read_text(encoding="utf-8")
    values = {
        "TITLE": escape(result["title"], quote=True),
        "PERIOD_LABEL": escape(result["period_label"], quote=True),
        "SUMMARY": escape(result["summary"], quote=True),
        "OBSERVATIONS": _observation_items(result["observations"]),
        "CHANGES": _change_items(result["changes"]),
        "RECOMMENDATIONS": _recommendation_items(result["recommendations"]),
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
    if any(not isinstance(result[key], str) for key in FIELDS[:3]):
        raise ValueError("DeepSeek 返回的报告字段类型无效")
    observations = result["observations"]
    if (not isinstance(observations, dict) or set(observations) != set(OBSERVATION_FIELDS)
            or any(not isinstance(observations[field], str) for field in OBSERVATION_FIELDS)):
        raise ValueError("DeepSeek 返回的观察字段类型无效")
    if any(not isinstance(result[key], list) for key in FIELDS[4:]):
        raise ValueError("DeepSeek 返回的报告字段类型无效")
    if any(not isinstance(item, dict) or set(item) != set(CHANGE_FIELDS)
           or any(not isinstance(item[field], str) for field in CHANGE_FIELDS)
           for item in result["changes"]):
        raise ValueError("DeepSeek 返回的变化字段类型无效")
    if any(not isinstance(item, dict) or set(item) != set(RECOMMENDATION_FIELDS)
           or any(not isinstance(item[field], str) for field in RECOMMENDATION_FIELDS)
           for item in result["recommendations"]):
        raise ValueError("DeepSeek 返回的建议字段类型无效")
    return result


def run(config_path, level, date) -> Path:
    """Generate and atomically save one period's report."""
    if level not in LEVELS:
        raise ValueError(f"不支持的报告周期：{level}")
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if date == "yesterday":
        date = (datetime.now(ZoneInfo(config.get("timezone", "UTC"))).date()
                - timedelta(days=1)).isoformat()
    if CalendarDate.fromisoformat(date).isoformat() != date:
        raise ValueError("日期必须使用 YYYY-MM-DD 格式")
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
            instructions=(HERE / "prompts" / PROMPTS[level]).read_text(encoding="utf-8"),
            input=json.dumps(context, ensure_ascii=False),
            text={"format": {"type": "json_schema", "name": "self_harness_report", "strict": True, "schema": SCHEMA}},
        )
        result = _validated_output(response)
    except Exception as exc:
        raise RuntimeError(f"DeepSeek 报告生成失败：{str(exc).replace(key, '[REDACTED]')}") from exc

    html = _render(result)
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
    parser.add_argument("--date", required=True, help="YYYY-MM-DD or yesterday in the configured timezone")
    parser.add_argument("--send-email", action="store_true", help="生成报告后通过 Gmail 投递")
    args = parser.parse_args()
    try:
        output = run(args.config, args.level, args.date)
    except Exception as exc:
        print(f"报告生成失败：{exc}", file=sys.stderr)
        return 1
    print(output)
    if args.send_email:
        try:
            config_path = Path(args.config).resolve()
            config = json.loads(config_path.read_text(encoding="utf-8"))
            message_id = send_report(config, output, config_path.parent)
            print(f"邮件已投递，Gmail message id: {message_id}")
        except Exception as exc:
            print(f"邮件投递失败：{exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
