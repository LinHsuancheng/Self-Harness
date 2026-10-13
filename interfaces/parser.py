"""Pure source parsers: input bytes -> material records, with no I/O."""
import csv
import io
import json
import math
from datetime import datetime, timedelta, timezone

VERSION = '2'


def utc(value):
    if not isinstance(value, str):
        raise ValueError('Timestamp must be a string')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return result.astimezone(timezone.utc).isoformat()


def number(value):
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('Expected a finite nonnegative number')
    return value


def record(source, key, observed, collected, data, end=None, version=None):
    observed = utc(observed)
    if end is not None and utc(end) < observed:
        raise ValueError('Interval end precedes start')
    return {'source': source, 'observed_at': observed, 'collected_at': utc(collected), 'data': data,
            '_key': str(key), '_end': utc(end) if end is not None else None,
            '_version': utc(version or collected)}


def parse(source, content, collected_at, settings):
    if source in ('sleep', 'weight', 'iphone_screen_time'):
        rows = [row for row in csv.reader(io.StringIO(content.decode('utf-8-sig'))) if row]
        if not rows:
            raise ValueError('Empty CSV')
        result = []
        apps = {}
        for row in rows:
            if source == 'weight':
                if len(row) != 2:
                    raise ValueError('Weight CSV requires timestamp,value')
                observed = utc(row[0])
                result.append(record(source, observed, observed, collected_at,
                                     {'value': number(row[1]), 'unit': settings.get('unit')}))
            elif source == 'sleep':
                if len(row) != 3 or not row[0].strip():
                    raise ValueError('Sleep CSV requires stage,start,end')
                start, end = utc(row[1]), utc(row[2])
                seconds = (datetime.fromisoformat(end)-datetime.fromisoformat(start)).total_seconds()
                result.append(record(source, start, start, collected_at,
                                     {'stage': row[0], 'start': start, 'end': end,
                                      'duration': number(seconds), 'duration_unit': 'seconds'}, end=end))
            else:
                if len(row) != 3 or not row[2].endswith('分钟'):
                    raise ValueError('App CSV requires timestamp,app,minutes分钟')
                observed = utc(row[0])
                apps.setdefault(observed, []).append({'app': row[1], 'duration': number(row[2][:-2]),
                                                      'duration_unit': 'minutes'})
        for observed, entries in apps.items():
            result.append(record(source, observed, observed, collected_at,
                                 {'apps': entries, 'aggregation_window': settings.get('aggregation_window')},
                                 version=observed))
        return result
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError('JSON must be an object')
    envelope = payload if 'source' in payload else None
    if envelope:
        if envelope['source'] != source:
            raise ValueError('Source disagrees with upload type')
        payload = envelope['data']
    if source == 'pc_screen_time':
        start, end = utc(payload['start']), utc(payload['end'])
        if end < start or payload['duration_unit'] != 'seconds':
            raise ValueError('Invalid ActivityWatch range or duration unit')
        result = []
        for bucket in payload['buckets']:
            metadata = bucket['bucket']
            for event in bucket['events']:
                observed = utc(event['timestamp'])
                duration = number(event['duration'])
                event_end = (datetime.fromisoformat(observed)+timedelta(seconds=duration)).isoformat()
                data = {'bucket_id': metadata['id'], 'bucket_type': metadata['type'], 'event_id': event['id'],
                        'start': observed, 'end': event_end, 'duration': duration, 'duration_unit': 'seconds',
                        'hostname': metadata.get('hostname'), 'details': event['data']}
                result.append(record(source, metadata['id']+'|'+str(event['id']), observed, collected_at,
                                     data, end=event_end, version=end))
        return result
    if source == 'todo':
        if payload.get('complete') is not True or not isinstance(payload.get('lists'), list):
            raise ValueError('Todo requires a complete list/task/checklist snapshot')
        for lst in payload['lists']:
            lst['list']['id']
            for task in lst['tasks']:
                task['task']['id']
                if not isinstance(task['checklist'], list):
                    raise ValueError('Incomplete Todo checklist')
        observed = utc(envelope['observed_at'] if envelope else payload['observed_at'])
        return [record(source, observed, observed, collected_at,
                       {'lists': payload['lists'], 'complete': True}, version=observed)]
    raise ValueError('Unsupported source: '+source)
