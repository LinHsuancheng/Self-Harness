"""Shared screenshot-analysis schema, prompt and validation; no I/O."""

PROMPT_VERSION = '1'
CATEGORIES = ('work', 'study', 'communication', 'entertainment', 'utilities', 'other')
ACTIVITIES = ('coding', 'writing', 'reading', 'meeting', 'browsing', 'watching',
              'gaming', 'designing', 'communicating', 'idle', 'other')
FOCUS = ('deep', 'light', 'distracted', 'idle')
FIELDS = ('app', 'window_title', 'url', 'category', 'activity', 'topics',
          'summary', 'focus', 'sensitive', 'confidence')
SENSITIVE_SUMMARY = '敏感内容，已省略'

PROMPT = '''你是 Self Harness 的屏幕观察分析器。你只看到一张自动截取的桌面截图。
判断用户此刻在做什么，只输出一个 json 对象，不要 markdown、不要解释。

字段与取值：
- app: 前台应用名（字符串，无法判断用 "unknown"）
- window_title: 窗口标题（字符串，无法判断用空字符串）
- url: 浏览器地址（字符串，仅当清晰可见；否则空字符串）
- category: work|study|communication|entertainment|utilities|other
- activity: coding|writing|reading|meeting|browsing|watching|gaming|designing|communicating|idle|other
- topics: 最多 5 个项目/主题/文档名（字符串数组，不要泛化词）
- summary: 一句中文描述正在做什么（不超过 80 字）
- focus: deep|light|distracted|idle
- sensitive: 是否包含密码、私信、财务、医疗、证件等敏感内容（布尔）
- confidence: 0 到 1 的数字

规则：
- 只根据截图中的可见证据判断，不确定时降低 confidence。
- 不要把大段屏幕文字抄进 json。
- 如果 sensitive 为 true：app 用 "private"，window_title/url 用空字符串，topics 用空数组，
  summary 固定为 "敏感内容，已省略"。
'''

SCHEMA = {
    'type': 'object',
    'properties': {
        'app': {'type': 'string'},
        'window_title': {'type': 'string'},
        'url': {'type': 'string'},
        'category': {'type': 'string', 'enum': list(CATEGORIES)},
        'activity': {'type': 'string', 'enum': list(ACTIVITIES)},
        'topics': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 5},
        'summary': {'type': 'string'},
        'focus': {'type': 'string', 'enum': list(FOCUS)},
        'sensitive': {'type': 'boolean'},
        'confidence': {'type': 'number'},
    },
    'required': list(FIELDS),
    'additionalProperties': False,
}


def _text(value, name, limit, default=''):
    if value is None:
        value = default
    if not isinstance(value, str):
        raise ValueError(f'{name} must be a string')
    return value.strip()[:limit]


def validate(value, redact_sensitive=True):
    """Return a normalized analysis dict or raise ValueError."""
    if not isinstance(value, dict):
        raise ValueError('Analysis must be an object')
    category = _text(value.get('category'), 'category', 40).lower()
    activity = _text(value.get('activity'), 'activity', 40).lower()
    focus = _text(value.get('focus'), 'focus', 40).lower()
    if category not in CATEGORIES:
        raise ValueError('Invalid category')
    if activity not in ACTIVITIES:
        raise ValueError('Invalid activity')
    if focus not in FOCUS:
        raise ValueError('Invalid focus')
    topics = value.get('topics')
    if not isinstance(topics, list):
        raise ValueError('topics must be a list')
    normalized_topics = []
    for topic in topics:
        if not isinstance(topic, str):
            raise ValueError('topics must contain strings')
        topic = topic.strip()[:80]
        if topic and topic not in normalized_topics:
            normalized_topics.append(topic)
    sensitive = value.get('sensitive')
    if not isinstance(sensitive, bool):
        raise ValueError('sensitive must be a boolean')
    confidence = value.get('confidence')
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError('confidence must be a number')
    confidence = float(confidence)
    if not 0 <= confidence <= 1:
        raise ValueError('confidence must be between 0 and 1')
    result = {
        'app': _text(value.get('app'), 'app', 120, 'unknown') or 'unknown',
        'window_title': _text(value.get('window_title'), 'window_title', 300),
        'url': _text(value.get('url'), 'url', 500),
        'category': category,
        'activity': activity,
        'topics': normalized_topics[:5],
        'summary': _text(value.get('summary'), 'summary', 200),
        'focus': focus,
        'sensitive': sensitive,
        'confidence': round(confidence, 4),
    }
    if sensitive and redact_sensitive:
        result.update({'app': 'private', 'window_title': '', 'url': '', 'topics': [],
                       'summary': SENSITIVE_SUMMARY})
    return result
