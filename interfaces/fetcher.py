"""Raw file acquisition and Graph collection; no material parsing."""
import gzip
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit


def files(config, source):
    settings = config['sources'][source]
    root = Path(settings.get('raw_dir', Path(config['raw_dir']) / source))
    for path in sorted(root.rglob('*.gz'), key=lambda p: (p.stat().st_mtime_ns, str(p))):
        metadata_path = path.with_name(path.name+'.meta.json')
        if metadata_path.exists():
            collected = json.loads(metadata_path.read_text())['collected_at']
        else:
            collected = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        yield path, collected


def read(path, maximum):
    with gzip.open(path, 'rb') as handle:
        content = handle.read(maximum+1)
    if len(content)>maximum:
        raise ValueError('Raw file exceeds uncompressed size limit')
    return content


def archive(config, source, content):
    now = datetime.now(timezone.utc)
    root = Path(config['sources'][source].get('raw_dir', Path(config['raw_dir']) / source))
    path = root / now.strftime('%Y-%m-%d') / (now.strftime('%H%M%S-%f-')+uuid.uuid4().hex[:8]+'.json.gz')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_bytes(gzip.compress(content, mtime=0))
    temporary.replace(path)
    return path


def todo(config, login=False):
    import msal
    import requests
    settings = config['sources']['todo']
    cache_path = Path(settings['cache_file'])
    cache = msal.SerializableTokenCache()
    if cache_path.exists():
        cache.deserialize(cache_path.read_text())
    app = msal.PublicClientApplication(settings['client_id'], authority=settings['authority'], token_cache=cache)
    accounts = app.get_accounts()
    scopes = ['Tasks.Read']
    try:
        result = app.acquire_token_silent(scopes, account=accounts[0]) if accounts else None
        if (not result or 'access_token' not in result) and login:
            flow = app.initiate_device_flow(scopes=scopes)
            if 'user_code' not in flow:
                raise RuntimeError('Microsoft device flow failed')
            print(flow['message'], flush=True)
            result = app.acquire_token_by_device_flow(flow)
        if not result or 'access_token' not in result:
            raise RuntimeError('Microsoft authorization expired; maintenance requires fetch todo --login')
    finally:
        if cache.has_state_changed:
            cache_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            temporary = cache_path.with_suffix('.tmp')
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as handle:
                handle.write(cache.serialize())
            temporary.replace(cache_path)
    payload = {'observed_at': datetime.now(timezone.utc).isoformat(), 'complete': False, 'lists': []}
    with requests.Session() as session:
        session.headers['Authorization'] = 'Bearer '+result['access_token']
        base = settings['graph_url'].rstrip('/')
        def fetch(path):
            url = base+path
            output = []
            while url:
                if urlsplit(url).netloc != urlsplit(base).netloc or urlsplit(url).scheme != 'https':
                    raise ValueError('Graph pagination URL outside configured HTTPS host')
                response = session.get(url, timeout=30)
                response.raise_for_status()
                data = response.json()
                output.extend(data['value'])
                url = data.get('@odata.nextLink')
            return output
        try:
            for lst in fetch('/me/todo/lists'):
                entry = {'list': lst, 'tasks': []}
                payload['lists'].append(entry)
                prefix = '/me/todo/lists/'+quote(lst['id'],safe='')+'/tasks'
                for task in fetch(prefix):
                    checklist = fetch(prefix+'/'+quote(task['id'],safe='')+'/checklistItems')
                    entry['tasks'].append({'task': task, 'checklist': checklist})
            payload['complete'] = True
            payload['observed_at'] = datetime.now(timezone.utc).isoformat()
        except Exception:
            archive(config, 'todo', json.dumps(payload, ensure_ascii=False).encode())
            raise
    return archive(config, 'todo', json.dumps(payload, ensure_ascii=False).encode())


def activitywatch(config):
    import requests
    from datetime import timedelta
    settings = config['activitywatch']
    end = datetime.now(timezone.utc)
    start = end-timedelta(hours=settings['hours'])
    base = settings['url'].rstrip('/')+'/api/0'
    response = requests.get(base+'/buckets/',timeout=30)
    response.raise_for_status()
    buckets=[]
    for bucket_id, metadata in response.json().items():
        if metadata['type'] not in ('afkstatus','currentwindow','web.tab.current'):
            continue
        response=requests.get(base+'/buckets/'+quote(bucket_id,safe='')+'/events',
                              params={'start':start.isoformat(),'end':end.isoformat(),'limit':-1},timeout=60)
        response.raise_for_status()
        events=response.json()
        if not isinstance(events,list):
            raise ValueError('ActivityWatch events must be a list')
        buckets.append({'bucket':metadata,'events':events})
    if not any(bucket['events'] for bucket in buckets):
        raise RuntimeError('No ActivityWatch events; no snapshot created')
    payload={'source':'pc_screen_time','observed_at':end.isoformat(),'collected_at':end.isoformat(),
             'data':{'start':start.isoformat(),'end':end.isoformat(),'duration_unit':'seconds','buckets':buckets}}
    return archive(config,'pc_screen_time',json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode())


def upload(config, source, path):
    import requests
    with Path(path).open('rb') as handle:
        response=requests.post(config['activitywatch']['upload_url'], data={'type':source},
                               files={'file':(Path(path).name,handle,'application/gzip')},timeout=120)
    response.raise_for_status()
    result=response.json()
    if result.get('status')!='success':
        raise RuntimeError('Server did not confirm upload')
    Path(str(path)+'.receipt.json').write_text(json.dumps(result,ensure_ascii=False))
    return result
