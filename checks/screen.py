"""Synthetic checks for screenshot analysis parsing, identity and aggregation."""
import gzip
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from interfaces import parser, screen
from interfaces.operator import ingest, query, status, summarize
from interfaces.summary import screen_activity

SETTINGS = {'sample_minutes': 5,
            'category_names': {'work': '工作/开发', 'study': '学习/阅读', 'idle': '空闲'},
            'focus_names': {'deep': '深度', 'light': '轻度', 'idle': '空闲'}}


def analysis(**overrides):
    value = {'app': 'Visual Studio Code', 'window_title': 'parser.py', 'url': '',
             'category': 'work', 'activity': 'coding', 'topics': ['parser.py'],
             'summary': '正在编辑解析器。', 'focus': 'deep', 'sensitive': False,
             'confidence': 0.9}
    value.update(overrides)
    return value


def envelope(captured, digest, value=None, filename='shot.jpg'):
    value = value or analysis()
    captured = parser.utc(captured)
    return {'source': 'pc_screen_activity', 'observed_at': captured, 'collected_at': captured,
            'data': {'captured_at': captured,
                     'capture': {'id': captured+'|'+digest, 'sha256': digest, 'bytes': 1234,
                                 'format': 'jpeg', 'filename': filename},
                     'model': 'test-model', 'prompt_version': screen.PROMPT_VERSION,
                     'analysis': value}}


with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config = {'raw_dir': str(root/'raw'), 'database_dir': str(root/'db'),
              'timezone': 'Asia/Singapore', 'day_start_hour': 9,
              'sources': {'pc_screen_activity': SETTINGS}}

    def put(name, value):
        path = root/'raw'/'pc_screen_activity'/'2026-10-13'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(json.dumps(value).encode()))

    digest_a, digest_b = 'a'*64, 'b'*64
    put('a.json.gz', envelope('2026-10-13T10:00:00+08:00', digest_a))
    put('b.json.gz', envelope('2026-10-13T10:05:00+08:00', digest_a))
    ingest(config, 'pc_screen_activity')
    rows = query(config, 'pc_screen_activity', '2026-10-13T00:00:00+08:00',
                 '2026-10-14T00:00:00+08:00')
    assert len(rows) == 2, 'identical pixels at different times must remain distinct samples'
    assert rows[0]['data']['capture']['id'].endswith('|'+digest_a)

    put('b-copy.json.gz', envelope('2026-10-13T10:05:00+08:00', digest_a))
    ingest(config, 'pc_screen_activity')
    assert len(query(config, 'pc_screen_activity', '2026-10-13T00:00:00+08:00',
                     '2026-10-14T00:00:00+08:00')) == 2, 'same capture must not duplicate'

    put('c.json.gz', envelope('2026-10-13T10:10:00+08:00', digest_b,
                              analysis(app='Bank', window_title='Account 123', url='https://bank.test',
                                       topics=['account'], summary='余额 1234', sensitive=True)))
    ingest(config, 'pc_screen_activity')
    sensitive = [row for row in query(config, 'pc_screen_activity', '2026-10-13T10:09:00+08:00',
                                      '2026-10-13T10:11:00+08:00')][0]['data']['analysis']
    assert sensitive['app'] == 'private' and sensitive['topics'] == []
    assert sensitive['window_title'] == '' and sensitive['url'] == ''
    assert sensitive['summary'] == screen.SENSITIVE_SUMMARY

    put('bad.json.gz', envelope('2026-10-13T10:15:00+08:00', 'c'*64,
                                analysis(category='not-a-category')))
    ingest(config, 'pc_screen_activity')
    assert status(config, 'pc_screen_activity')['failed_files'] == 1
    assert status(config, 'pc_screen_activity')['successful_files'] >= 3

    report = summarize(config, 'pc_screen_activity', '2026-10-13T09:00:00+08:00',
                       '2026-10-14T09:00:00+08:00')
    assert report['data_quality']['effective_days'] == 1
    assert report['summary']['daily_average_minutes'] == 15
    assert report['summary']['activities'][0]['name'] == '工作/开发'
    assert report['summary']['sample_minutes'] == 5
    assert report['comparison']['metrics']['daily_average_minutes']['current'] == 15

    rows = [
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:00:00+08:00',
         'data': {'analysis': analysis()}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:05:00+08:00',
         'data': {'analysis': analysis(app='LockScreen', category='other', activity='idle',
                                       focus='idle', topics=[], summary='空闲')}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:10:00+08:00',
         'data': {'analysis': analysis(app='Reader', category='study', activity='reading',
                                       focus='light', topics=['paper'], summary='阅读')}},
    ]
    result = screen_activity(rows, '2026-10-13T10:00:00+08:00', '2026-10-13T10:20:00+08:00',
                             'Asia/Singapore', 9, SETTINGS, include_hourly=True)
    assert result['captures'] == 3 and result['active_captures'] == 2
    assert result['total_minutes'] == 10 and result['idle_minutes'] == 5
    assert {item['name']: item['minutes'] for item in result['categories']} == {
        '工作/开发': 5, '学习/阅读': 5}
    assert result['apps'][0]['app'] in ('Reader', 'Visual Studio Code')
    assert result['focus'][0]['minutes'] == 5
    assert result['daily'] == [{'date': '2026-10-13', 'minutes': 10}]
    assert len(result['hourly']) == 1 and result['hourly'][0]['minutes'] == 10

    tail = screen_activity(rows, '2026-10-13T10:00:00+08:00', '2026-10-13T10:12:00+08:00',
                           'Asia/Singapore', 9, SETTINGS)
    assert tail['total_minutes'] == 7, 'the last sample must be capped at the period end'

print('PASS: screenshot identity, duplicate capture, sensitive redaction, aggregation and boundary cap')
