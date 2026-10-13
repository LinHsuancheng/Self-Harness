"""Source-independent ingestion and material access, plus source-specific comparisons."""
import csv
import hashlib
import json
from contextlib import closing
from datetime import datetime
from pathlib import Path

from . import fetcher, parser
from .database import Database


def database(config, source):
    if source not in config['sources']:
        raise ValueError('Source is not configured: '+source)
    return Database(Path(config['database_dir']) / (source+'.sqlite3'))


def ingest(config, source, retry_failed=False):
    settings = config['sources'][source]
    version = parser.VERSION+'-'+hashlib.sha256(json.dumps(settings,sort_keys=True).encode()).hexdigest()[:12]
    counts = {'success':0,'duplicate':0,'failed':0,'skipped':0}
    with closing(database(config, source)) as db:
        for path, collected_at in fetcher.files(config, source):
            path_string = str(path.resolve())
            previous = db.file(path_string)
            if previous and previous['parser_version'] == version:
                if previous['status'] != 'failed' or not retry_failed:
                    counts['skipped'] += 1
                    continue
            content_hash = None
            try:
                content = fetcher.read(path, config.get('max_uncompressed_bytes', 52428800))
                content_hash = hashlib.sha256(content).hexdigest()
                duplicate = db.seen_content(content_hash, version)
                # A repeat capture can advance the version watermark without adding a revision.
                records = parser.parse(source,content,collected_at,settings)
                db.save(path_string,content_hash,version,parser.utc(collected_at),records,duplicate=duplicate)
                counts['duplicate' if duplicate else 'success'] += 1
            except (csv.Error,ValueError,KeyError,TypeError,IndexError,AttributeError,OSError,EOFError,OverflowError) as exc:
                db.save(path_string,content_hash,version,parser.utc(collected_at),[],error=str(exc))
                counts['failed'] += 1
    return counts


def material(source, row):
    return {'source':source,'observed_at':row['observed_at'], 'collected_at':row['collected_at'],
            'data':json.loads(row['data'])}


def query(config, source, start, end):
    if parser.utc(start) >= parser.utc(end):
        raise ValueError('Start must precede end')
    with closing(database(config, source)) as db:
        return [material(source,row) for row in db.rows(start=start,end=end)]


def latest_before(config, source, time):
    with closing(database(config, source)) as db:
        rows = db.rows(before=time)
        return material(source,rows[-1]) if rows else None


def status(config, source):
    with closing(database(config, source)) as db:
        result = db.status()
        result['pending_files'] = sum(db.file(str(p.resolve())) is None for p,_ in fetcher.files(config,source))
        return result


def context(config, start, end):
    return {source: {'materials':query(config,source,start,end),
                     'baseline':latest_before(config,source,start), 'status':status(config,source)}
            for source in config['sources']}


def todo_changes(config, start, end):
    snapshots = query(config,'todo',start,end)
    previous = latest_before(config,'todo',start)
    changes = []
    def tasks(snapshot):
        return {(lst['list']['id'],t['task']['id']):t for lst in snapshot['data']['lists'] for t in lst['tasks']}
    for current in snapshots:
        if previous is None:
            changes.append({'observed_at':current['observed_at'],'baseline_missing':True})
        else:
            a,b = tasks(previous),tasks(current)
            la = {x['list']['id']:x['list'] for x in previous['data']['lists']}
            lb = {x['list']['id']:x['list'] for x in current['data']['lists']}
            changes.append({'start':previous['observed_at'],'end':current['observed_at'],
                            'appeared':[{'list_id':k[0],'task_id':k[1]} for k in b.keys()-a.keys()],
                            'disappeared':[{'list_id':k[0],'task_id':k[1]} for k in a.keys()-b.keys()],
                            'changed':[{'list_id':k[0],'task_id':k[1],'before':a[k],'after':b[k]} for k in a.keys()&b.keys() if a[k]!=b[k]],
                            'lists_appeared':sorted(lb.keys()-la.keys()),'lists_disappeared':sorted(la.keys()-lb.keys()),
                            'lists_changed':[{'before':la[k],'after':lb[k]} for k in la.keys()&lb.keys() if la[k]!=lb[k]]})
        previous = current
    return changes


def pc_active_time(config, start, end):
    rows = query(config,'pc_screen_time',start,end)
    lower,upper = datetime.fromisoformat(parser.utc(start)),datetime.fromisoformat(parser.utc(end))
    active = {}
    for row in rows:
        data = row['data']
        if data['bucket_type']=='afkstatus' and data['details'].get('status')=='not-afk':
            active.setdefault(data.get('hostname'),[]).append((datetime.fromisoformat(data['start']),datetime.fromisoformat(data['end'])))
    totals = {}
    for row in rows:
        data = row['data']
        if data['bucket_type']!='currentwindow':
            continue
        begin,finish = datetime.fromisoformat(data['start']),datetime.fromisoformat(data['end'])
        intervals = sorted((max(begin,a,lower),min(finish,b,upper)) for a,b in active.get(data.get('hostname'),[]) if max(begin,a,lower)<min(finish,b,upper))
        merged = []
        for a,b in intervals:
            if merged and a<=merged[-1][1]:
                merged[-1] = (merged[-1][0],max(merged[-1][1],b))
            else:
                merged.append((a,b))
        seconds = sum((b-a).total_seconds() for a,b in merged)
        if seconds:
            key=(data.get('hostname'),data['details'].get('app'))
            totals[key]=totals.get(key,0)+seconds
    return {'duration_unit':'seconds', 'apps':[{'hostname':host,'app':app,'active_duration':seconds} for (host,app),seconds in totals.items()],
            'afk_data_present':any(r['data']['bucket_type']=='afkstatus' for r in rows)}
