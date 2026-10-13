"""Collect a configurable ActivityWatch interval and upload gzip JSON."""
import argparse
import gzip
import json
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote
from zoneinfo import ZoneInfo

import requests



def collect(config):
    settings = config['activitywatch']
    end = datetime.now(ZoneInfo(config['timezone']))
    start = end - timedelta(hours=settings['hours'])
    base = settings['url'].rstrip('/') + '/api/0'
    response = requests.get(base + '/buckets/', timeout=30)
    response.raise_for_status()
    buckets = []
    for bucket_id, metadata in response.json().items():
        if metadata['type'] not in ('afkstatus', 'currentwindow', 'web.tab.current'):
            continue
        response = requests.get(base + '/buckets/' + quote(bucket_id, safe='') + '/events',
                                params={'start': start.isoformat(), 'end': end.isoformat(), 'limit': -1}, timeout=60)
        response.raise_for_status()
        events = response.json()
        if not isinstance(events, list):
            raise ValueError('ActivityWatch events must be a list')
        buckets.append({'bucket': metadata, 'events': events})
    if not any(bucket['events'] for bucket in buckets):
        raise RuntimeError('No ActivityWatch events; nothing uploaded')
    payload = {'source': 'pc_screen_time', 'observed_at': end.isoformat(),
               'collected_at': end.isoformat(), 'data': {
                   'start': start.isoformat(), 'end': end.isoformat(),
                   'duration_unit': 'seconds', 'buckets': buckets}}
    content = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode()
    compressed = gzip.compress(content, mtime=0)
    filename = 'pc-screen-time-' + end.strftime('%Y%m%dT%H%M%S-%f%z') + '.json.gz'
    path = Path(config['data_dir']) / 'outbox' / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compressed)
    response = requests.post(settings['upload_url'], data={'type': 'pc_screen_time'},
                             files={'file': (filename, compressed, 'application/gzip')}, timeout=120)
    response.raise_for_status()
    result = response.json()
    if result.get('status') != 'success':
        raise RuntimeError('Upload failed: ' + json.dumps(result, ensure_ascii=False))
    path.with_suffix('.receipt.json').write_text(json.dumps(result, ensure_ascii=False))
    print(json.dumps({'json_bytes': len(content), 'gzip_bytes': len(compressed),
                      'event_counts': {b['bucket']['type']: len(b['events']) for b in buckets},
                      'receipt': result}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text())
    config['data_dir'] = str(config_path.parent / 'observation')
    collect(config)
