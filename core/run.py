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
OBSERVATION_FIELDS = ("sleep", "weight", "tasks", "pc_usage", "iphone_usage")
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
        return '<p class="empty">本期无明确变化。</p>'
    return "".join(
        '<div class="change-item">'
        '<p class="change-area">{}</p>'
        '<p class="change-obs">{}</p>'
        '<p class="change-trend">{}</p>'
        '</div>'.format(
            escape(item["area"]), escape(item["observation"]), escape(item["trend"]),
        )
        for item in changes
    )


def _recommendation_items(recommendations):
    if not recommendations:
        return '<p class="empty">本期暂无建议调整。</p>'
    return "".join(
        '<div class="rec-item">'
        '<p class="rec-action">{}</p>'
        '<p class="rec-reason">{}</p>'
        '</div>'.format(
            escape(item["action"]), escape(item["reason"]),
        )
        for item in recommendations
    )


def _context_blocks(context, zone):
    """Generate HTML data visualization blocks from raw interface context."""

    def _local(iso):
        try:
            return datetime.fromisoformat(iso).astimezone(ZoneInfo(zone)).strftime('%H:%M')
        except Exception:
            return iso[:5] if iso else "—"

    def _bar_chart(items, unit, max_items=8):
        items = [(n, v, s) for n, v, s in items if v and v > 0][:max_items]
        if not items:
            return '<p class="empty">无数据</p>'
        max_s = max(s for _, _, s in items) or 1
        rows = []
        for name, value, share in items:
            pct = share / max_s * 100
            rows.append(
                f'<div class="bar-row">'
                f'<span class="bar-name">{escape(str(name))}</span>'
                f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>'
                f'<span class="bar-val">{value:.0f}{unit}</span>'
                f'<span class="bar-pct">{share*100:.0f}%</span>'
                f'</div>'
            )
        return '\n'.join(rows)

    blocks: dict = {}

    # ── SLEEP ──────────────────────────────────────────────────────────────
    sl = context.get('sleep', {})
    ss = sl.get('summary', {})
    sc = sl.get('comparison', {}).get('metrics', {})

    hours = ss.get('daily_average_hours')
    blocks['SLEEP_STAT'] = f"{hours:.1f} h" if hours is not None else "—"

    prev = sc.get('daily_average_hours', {}).get('previous')
    chg  = sc.get('daily_average_hours', {}).get('change')
    if chg is not None and prev is not None:
        sign = "↑" if chg > 0 else "↓"
        blocks['SLEEP_CHANGE'] = f"{sign} {abs(chg):.1f}h  ·  前日 {prev:.1f}h"
    else:
        blocks['SLEEP_CHANGE'] = "无前日对比"

    stages = ss.get('stages') or []
    total_h = sum(st.get('hours', 0) for st in stages) or 1
    stage_items = [
        (st['stage'], st.get('hours', 0), st.get('hours', 0) / total_h)
        for st in stages if st.get('hours', 0) > 0
    ]
    blocks['SLEEP_STAGES'] = _bar_chart(stage_items, 'h', max_items=6)

    sessions = ss.get('sessions') or []
    if sessions:
        tags = []
        for s in sessions:
            st_t = _local(s.get('start', ''))
            en_t = _local(s.get('end', ''))
            sh = s.get('sleep_hours', 0)
            tags.append(f'<span class="session-tag">{st_t}–{en_t} · {sh:.1f}h</span>')
        blocks['SLEEP_SESSIONS'] = '\n'.join(tags)
    else:
        blocks['SLEEP_SESSIONS'] = '<span class="empty">无记录</span>'

    # ── PC ─────────────────────────────────────────────────────────────────
    pc  = context.get('pc_screen_time', {})
    ps  = pc.get('summary', {})
    pcc = pc.get('comparison', {}).get('metrics', {})

    pc_min = ps.get('daily_average_minutes')
    if pc_min is not None:
        h, m = int(pc_min // 60), int(pc_min % 60)
        blocks['PC_STAT']  = f"{pc_min:.0f}"
        blocks['PC_HOURS'] = f"{h}h {m}min" if h else f"{m}min"
    else:
        blocks['PC_STAT']  = "—"
        blocks['PC_HOURS'] = ""

    pc_chg  = pcc.get('daily_average_minutes', {}).get('change')
    pc_prev = pcc.get('daily_average_minutes', {}).get('previous')
    if pc_chg is not None and pc_prev is not None:
        sign = "↑" if pc_chg > 0 else "↓"
        blocks['PC_CHANGE'] = f"{sign} {abs(pc_chg):.0f}min  ·  前日 {pc_prev:.0f}min"
    else:
        blocks['PC_CHANGE'] = ""

    acts = ps.get('activities') or []
    blocks['PC_BARS'] = _bar_chart(
        [(a['name'], a.get('minutes', 0), a.get('share', 0)) for a in acts], 'min'
    )

    # ── IPHONE ─────────────────────────────────────────────────────────────
    ip  = context.get('iphone_screen_time', {})
    ips = ip.get('summary', {})
    ipc = ip.get('comparison', {}).get('metrics', {})

    ip_min = ips.get('daily_average_minutes')
    if ip_min is not None:
        h, m = int(ip_min // 60), int(ip_min % 60)
        blocks['IPHONE_STAT']  = f"{ip_min:.0f}"
        blocks['IPHONE_HOURS'] = f"{h}h {m}min" if h else f"{m}min"
    else:
        blocks['IPHONE_STAT']  = "—"
        blocks['IPHONE_HOURS'] = ""

    ip_chg  = ipc.get('daily_average_minutes', {}).get('change')
    ip_prev = ipc.get('daily_average_minutes', {}).get('previous')
    if ip_chg is not None and ip_prev is not None:
        sign = "↑" if ip_chg > 0 else "↓"
        blocks['IPHONE_CHANGE'] = f"{sign} {abs(ip_chg):.0f}min  ·  前日 {ip_prev:.0f}min"
    else:
        blocks['IPHONE_CHANGE'] = ""

    apps = ips.get('apps') or []
    blocks['IPHONE_BARS'] = _bar_chart(
        [(a.get('app', '?'), a.get('minutes', 0), a.get('share', 0)) for a in apps], 'min'
    )

    # ── WEIGHT ─────────────────────────────────────────────────────────────
    wt  = context.get('weight', {})
    ws  = wt.get('summary', {})
    wtc = wt.get('comparison', {}).get('metrics', {})

    mean = ws.get('mean')
    unit = ws.get('unit') or 'kg'
    blocks['WEIGHT_STAT'] = f"{mean:.1f}" if mean is not None else "—"

    wt_chg = wtc.get('mean', {}).get('change')
    if wt_chg is not None:
        sign = "↑" if wt_chg > 0 else "↓"
        blocks['WEIGHT_CHANGE'] = f"{sign} {abs(wt_chg):.2f} {unit}"
    else:
        blocks['WEIGHT_CHANGE'] = "无前日对比" if mean is not None else ""

    mn, mx = ws.get('min'), ws.get('max')
    if mn is not None and mx is not None and mn != mx:
        blocks['WEIGHT_RANGE'] = f"范围 {mn:.1f} – {mx:.1f} {unit}"
    else:
        blocks['WEIGHT_RANGE'] = unit if mean is not None else "今日无记录"

    # ── TODO ───────────────────────────────────────────────────────────────
    td = context.get('todo', {})
    ts = td.get('summary', {})

    completed_count = ts.get('completed_count') or 0
    pending_count   = ts.get('pending_count') or 0
    appeared_count  = ts.get('appeared_count') or 0
    initial_pending = ts.get('initial_pending_count')
    stalled = (initial_pending - completed_count) if initial_pending is not None else None

    blocks['TODO_COMPLETED_COUNT'] = str(completed_count)
    blocks['TODO_PENDING_COUNT']   = str(pending_count)
    blocks['TODO_APPEARED_COUNT']  = f"+{appeared_count}" if appeared_count else "0"
    blocks['TODO_STALLED_COUNT']   = str(stalled) if stalled is not None else "—"

    completed_tasks = ts.get('completed_tasks') or []
    if completed_tasks:
        rows = []
        for task in completed_tasks[:20]:
            title = task.get('title') or '未命名任务'
            rows.append(
                f'<div class="task-item">'
                f'<span class="task-dash">—</span>'
                f'<span class="task-name">{escape(title)}</span>'
                f'</div>'
            )
        blocks['TODO_COMPLETED'] = '\n'.join(rows)
    else:
        blocks['TODO_COMPLETED'] = '<p class="empty">今日无完成任务</p>'

    return blocks


def _render(result, context, zone):
    template = (HERE / "templates" / "report.html").read_text(encoding="utf-8")
    obs = result["observations"]
    values: dict = {
        "TITLE":          escape(result["title"]),
        "PERIOD_LABEL":   escape(result["period_label"]),
        "SUMMARY":        escape(result["summary"]),
        "INSIGHT_SLEEP":  escape(obs["sleep"]),
        "INSIGHT_WEIGHT": escape(obs["weight"]),
        "INSIGHT_TASKS":  escape(obs["tasks"]),
        "INSIGHT_PC":     escape(obs["pc_usage"]),
        "INSIGHT_IPHONE": escape(obs["iphone_usage"]),
        "CHANGES":        _change_items(result["changes"]),
        "RECOMMENDATIONS": _recommendation_items(result["recommendations"]),
    }
    values.update(_context_blocks(context, zone))
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values.get(m.group(1), ""), template)


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
    client = OpenAI(
        api_key=key,
        base_url=os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
    )
    call_kwargs = dict(
        model=os.getenv("DEEPSEEK_MODEL") or "deepseek-flash",
        instructions=(HERE / "prompts" / PROMPTS[level]).read_text(encoding="utf-8"),
        input=json.dumps(context, ensure_ascii=False),
        text={"format": {"type": "json_schema", "name": "self_harness_report", "strict": True, "schema": SCHEMA}},
    )
    last_exc = None
    for attempt in range(3):
        try:
            result = _validated_output(client.responses.create(**call_kwargs))
            break
        except Exception as exc:
            last_exc = exc
    else:
        raise RuntimeError(f"DeepSeek 报告生成失败（3次重试）：{str(last_exc).replace(key, '[REDACTED]')}") from last_exc

    html = _render(result, context, config.get('timezone', 'UTC'))
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
