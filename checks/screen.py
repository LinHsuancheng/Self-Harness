"""Synthetic checks for screenshot analysis parsing, identity and aggregation."""
import gzip
import json
import sys
import tempfile
from datetime import datetime
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
              'sources': {'pc_screen_activity': SETTINGS, 'pc_screen_time': {}}}

    def put(name, value, source='pc_screen_activity'):
        path = root/'raw'/source/'2026-10-13'/name
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

    activitywatch = {
        'start': '2026-10-13T09:00:00+08:00', 'end': '2026-10-14T09:00:00+08:00',
        'duration_unit': 'seconds', 'buckets': [
            {'bucket': {'id': 'afk', 'type': 'afkstatus', 'hostname': 'pc'}, 'events': [
                {'id': 1, 'timestamp': '2026-10-13T10:02:00+08:00', 'duration': 300,
                 'data': {'status': 'not-afk'}}]},
            {'bucket': {'id': 'window', 'type': 'currentwindow', 'hostname': 'pc'}, 'events': [
                {'id': 2, 'timestamp': '2026-10-13T10:02:00+08:00', 'duration': 300,
                 'data': {'app': 'Code.exe', 'title': 'self-harness'}}]},
        ]}
    put('aw.json.gz', activitywatch, source='pc_screen_time')
    ingest(config, 'pc_screen_time')

    report = summarize(config, 'pc_screen_activity', '2026-10-13T09:00:00+08:00',
                       '2026-10-14T09:00:00+08:00')
    assert report['data_quality']['effective_days'] == 1
    assert report['summary']['daily_average_minutes'] == 5
    assert report['summary']['activity_time_source'] == 'activitywatch'
    assert report['summary']['classified_minutes'] == 5
    assert report['summary']['unclassified_minutes'] == 0
    assert report['summary']['daily'] == [{'date': '2026-10-13', 'minutes': 5}]
    assert report['summary']['activities'][0]['name'] == '工作/开发'
    assert report['summary']['sample_minutes'] == 5
    assert len(report['summary']['timeline']) == 1
    assert report['summary']['timeline'][0]['start'] == '2026-10-13T10:02:00+08:00'
    assert report['summary']['timeline'][0]['end'] == '2026-10-13T10:07:00+08:00'
    assert report['comparison']['metrics']['daily_average_minutes']['current'] == 5
    weekly = summarize(config, 'pc_screen_activity', '2026-10-13T09:00:00+08:00',
                       '2026-10-14T09:00:00+08:00', level='week')
    assert 'timeline' not in weekly['summary']

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

    active_rows = [
        {'source': 'pc_screen_activity', 'observed_at': f'2026-10-13T10:{minute:02d}:00+08:00',
         'data': {'analysis': analysis()}}
        for minute in (0, 5, 10)
    ]
    filtered = screen_activity(
        active_rows, '2026-10-13T10:00:00+08:00', '2026-10-13T10:15:00+08:00',
        'Asia/Singapore', 9, SETTINGS, include_timeline=True,
        active_intervals=[(datetime.fromisoformat('2026-10-13T10:02:00+08:00'),
                           datetime.fromisoformat('2026-10-13T10:07:00+08:00'))])
    assert filtered['total_minutes'] == 5
    assert filtered['timeline'] == [{
        'start': '2026-10-13T10:02:00+08:00', 'end': '2026-10-13T10:07:00+08:00',
        'minutes': 5, 'category': '工作/开发', 'activity': 'coding', 'focus': '深度',
        'apps': ['Visual Studio Code'], 'topics': ['parser.py'],
        'summary': '正在编辑解析器。', 'sample_count': 2, 'average_confidence': .9}]
    split = screen_activity(
        active_rows[:1], '2026-10-13T10:00:00+08:00', '2026-10-13T10:05:00+08:00',
        'Asia/Singapore', 9, SETTINGS, include_timeline=True,
        active_intervals=[
            (datetime.fromisoformat('2026-10-13T10:00:00+08:00'),
             datetime.fromisoformat('2026-10-13T10:01:00+08:00')),
            (datetime.fromisoformat('2026-10-13T10:04:00+08:00'),
             datetime.fromisoformat('2026-10-13T10:05:00+08:00'))])
    assert [(item['start'], item['end'], item['minutes']) for item in split['timeline']] == [
        ('2026-10-13T10:00:00+08:00', '2026-10-13T10:01:00+08:00', 1),
        ('2026-10-13T10:04:00+08:00', '2026-10-13T10:05:00+08:00', 1)]
    micro_gap = screen_activity(
        active_rows[:1], '2026-10-13T10:00:00+08:00', '2026-10-13T10:05:00+08:00',
        'Asia/Singapore', 9, SETTINGS, include_timeline=True,
        active_intervals=[
            (datetime.fromisoformat('2026-10-13T10:00:00+08:00'),
             datetime.fromisoformat('2026-10-13T10:01:00+08:00')),
            (datetime.fromisoformat('2026-10-13T10:01:03+08:00'),
             datetime.fromisoformat('2026-10-13T10:02:00+08:00'))])
    assert len(micro_gap['timeline']) == 1
    assert micro_gap['timeline'][0]['minutes'] == 1.95
    assert micro_gap['timeline'][0]['sample_count'] == 1
    assert micro_gap['timeline'][0]['average_confidence'] == .9

    timeline_rows = [
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:00:00+08:00',
         'data': {'analysis': analysis(topics=['self-harness'], summary='编辑截图分析器。',
                                       confidence=.9)}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:05:00+08:00',
         'data': {'analysis': analysis(app='Terminal', topics=['checks'], summary='运行合成检查。',
                                       focus='light', confidence=.7)}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:10:00+08:00',
         'data': {'analysis': analysis(app='LockScreen', category='other', activity='idle',
                                       focus='idle', topics=[], summary='空闲。')}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:15:00+08:00',
         'data': {'analysis': analysis(app='LockScreen', category='other', activity='idle',
                                       focus='idle', topics=[], summary='空闲。')}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:20:00+08:00',
         'data': {'analysis': analysis(app='Bank', topics=['account'], summary='余额 1234',
                                       sensitive=True)}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:25:00+08:00',
         'data': {'analysis': analysis(app='Reader', category='study', activity='reading',
                                       topics=['paper'], summary='阅读论文。', focus='light')}},
        {'source': 'pc_screen_activity', 'observed_at': '2026-10-13T10:45:00+08:00',
         'data': {'analysis': analysis(app='Reader', category='study', activity='reading',
                                       topics=['paper'], summary='继续阅读论文。', focus='light')}},
    ]
    timeline = screen_activity(
        timeline_rows, '2026-10-13T10:00:00+08:00', '2026-10-13T10:50:00+08:00',
        'Asia/Singapore', 9, SETTINGS, include_timeline=True)['timeline']
    assert len(timeline) == 5
    assert timeline[0] == {
        'start': '2026-10-13T10:00:00+08:00', 'end': '2026-10-13T10:10:00+08:00',
        'minutes': 10, 'category': '工作/开发', 'activity': 'coding', 'focus': '深度',
        'apps': ['Visual Studio Code', 'Terminal'], 'topics': ['self-harness', 'checks'],
        'summary': '运行合成检查。', 'sample_count': 2, 'average_confidence': .8}
    assert timeline[1]['activity'] == 'idle' and timeline[1]['minutes'] == 10
    assert timeline[2]['apps'] == [] and timeline[2]['topics'] == []
    assert timeline[2]['summary'] == screen.SENSITIVE_SUMMARY
    assert timeline[3]['start'] == '2026-10-13T10:25:00+08:00'
    assert timeline[3]['end'] == '2026-10-13T10:30:00+08:00'
    assert timeline[4]['start'] == '2026-10-13T10:45:00+08:00'

    tail = screen_activity(rows, '2026-10-13T10:00:00+08:00', '2026-10-13T10:12:00+08:00',
                           'Asia/Singapore', 9, SETTINGS, include_timeline=True)
    assert tail['total_minutes'] == 7, 'the last sample must be capped at the period end'
    assert tail['timeline'][-1]['end'] == '2026-10-13T10:12:00+08:00'

    put('no-aw.json.gz', envelope('2026-10-14T10:00:00+08:00', 'd'*64))
    ingest(config, 'pc_screen_activity')
    uncovered = summarize(config, 'pc_screen_activity', '2026-10-14T09:00:00+08:00',
                          '2026-10-15T09:00:00+08:00')
    assert uncovered['summary']['daily_average_minutes'] is None
    assert uncovered['summary']['activity_time_available'] is False, uncovered['summary']
    assert uncovered['summary']['timeline'] == []

    aw_only = dict(activitywatch)
    aw_only['start'] = '2026-10-15T09:00:00+08:00'
    aw_only['end'] = '2026-10-16T09:00:00+08:00'
    for bucket in aw_only['buckets']:
        bucket['events'][0]['timestamp'] = '2026-10-15T10:00:00+08:00'
        bucket['events'][0]['duration'] = 600
        bucket['events'][0]['id'] += 10
    put('aw-only.json.gz', aw_only, source='pc_screen_time')
    ingest(config, 'pc_screen_time')
    no_screenshots = summarize(config, 'pc_screen_activity', '2026-10-15T09:00:00+08:00',
                               '2026-10-16T09:00:00+08:00')
    assert no_screenshots['summary']['daily_average_minutes'] == 10
    assert no_screenshots['summary']['classified_minutes'] == 0
    assert no_screenshots['summary']['unclassified_minutes'] == 10
    assert no_screenshots['summary']['daily'] == [{'date': '2026-10-15', 'minutes': 10}]
    assert no_screenshots['trend'][0]['summary']['daily_average_minutes'] == 10

    two_days = {
        'start': '2026-10-16T09:00:00+08:00', 'end': '2026-10-18T09:00:00+08:00',
        'duration_unit': 'seconds', 'buckets': [
            {'bucket': {'id': 'afk-2d', 'type': 'afkstatus', 'hostname': 'pc'}, 'events': [
                {'id': 21, 'timestamp': '2026-10-16T10:00:00+08:00', 'duration': 3600,
                 'data': {'status': 'not-afk'}},
                {'id': 22, 'timestamp': '2026-10-17T10:00:00+08:00', 'duration': 3600,
                 'data': {'status': 'not-afk'}}]},
            {'bucket': {'id': 'window-2d', 'type': 'currentwindow', 'hostname': 'pc'}, 'events': [
                {'id': 23, 'timestamp': '2026-10-16T10:00:00+08:00', 'duration': 3600,
                 'data': {'app': 'Code.exe'}},
                {'id': 24, 'timestamp': '2026-10-17T10:00:00+08:00', 'duration': 3600,
                 'data': {'app': 'Code.exe'}}]},
        ]}
    put('two-days.json.gz', two_days, source='pc_screen_time')
    ingest(config, 'pc_screen_time')
    multi = summarize(config, 'pc_screen_activity', '2026-10-16T09:00:00+08:00',
                      '2026-10-18T09:00:00+08:00', level='day')
    assert multi['summary']['daily_average_minutes'] == 60
    assert multi['summary']['daily'] == [
        {'date': '2026-10-16', 'minutes': 60},
        {'date': '2026-10-17', 'minutes': 60}]

print('PASS: screenshot identity, redaction, ActivityWatch fusion, timeline and boundary cap')
