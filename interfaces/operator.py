"""Source-independent ingestion and material access, plus source-specific comparisons."""
import csv
import hashlib
import json
from contextlib import closing
from datetime import datetime
from pathlib import Path

from . import fetcher, parser, summary
from .database import Database


def database(config, source):
    if source not in config['sources']:
        raise ValueError('Source is not configured: '+source)
    return Database(Path(config['database_dir']) / (source+'.sqlite3'))


def ingest(config, source, retry_failed=False):
    settings = config['sources'][source]
    parse_settings={k:v for k,v in settings.items() if k not in ('summary','browser_apps')}
    version = parser.VERSION+'-'+hashlib.sha256(json.dumps(parse_settings,sort_keys=True).encode()).hexdigest()[:12]
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


def summarize(config, source, start, end):
    rows=query(config,source,start,end)
    if source=='weight':
        result=summary.weight(rows,latest_before(config,source,start))
    elif source=='sleep':
        result=summary.sleep(rows,start,end)
    elif source=='iphone_screen_time':
        result=summary.iphone(rows,config.get('timezone','UTC'))
    elif source=='pc_screen_time':
        result=summary.pc(config,start,end,pc_active_time)
        result['websites']=web_activity(config,start,end)
        result['activities']=summary.activities(result,config['sources'][source])
        del result['apps'],result['websites']
        result['hourly']=[hour for hour in result['hourly'] if hour['minutes']]
    elif source=='todo':
        with closing(database(config,source)) as db:
            following=db.rows(start=end)
            following=material(source,following[0]) if following else None
        result=summary.todo(rows,latest_before(config,source,start),start,end,following)
    else:
        raise ValueError('Unsupported source: '+source)
    return {'source':source,'period':{'start':start,'end':end},'summary':result}


def context(config, start, end):
    return {source:summarize(config,source,start,end) for source in config['sources']}


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


def web_activity(config, start, end):
    """Website and page time within the active browser's foreground intervals."""
    from collections import defaultdict
    from urllib.parse import urlsplit
    rows=query(config,'pc_screen_time',start,end)
    lower,upper=datetime.fromisoformat(parser.utc(start)),datetime.fromisoformat(parser.utc(end))
    browser_apps={app.lower() for app in config['sources']['pc_screen_time'].get('browser_apps',['msedge.exe'])}
    windows=defaultdict(list);active=defaultdict(list);web=[]
    for row in rows:
        data=row['data'];kind=data['bucket_type'];details=data['details'];host=data.get('hostname')
        interval=(max(lower,datetime.fromisoformat(data['start'])),min(upper,datetime.fromisoformat(data['end'])))
        if kind=='currentwindow' and details['app'].lower() in browser_apps:
            windows[host].append(interval)
        elif kind=='afkstatus' and details['status']=='not-afk':
            active[host].append(interval)
        elif kind=='web.tab.current':
            web.append((host,interval,details))
    sites=defaultdict(float);pages=defaultdict(lambda:defaultdict(float))
    for host,(begin,finish),details in web:
        overlaps=[]
        for window_start,window_end in windows[host]:
            a,b=max(begin,window_start),min(finish,window_end)
            if a>=b:continue
            overlaps.extend((max(a,x),min(b,y)) for x,y in active[host] if max(a,x)<min(b,y))
        merged=[]
        for a,b in sorted(overlaps):
            if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(merged[-1][1],b))
            else:merged.append((a,b))
        minutes=sum((b-a).total_seconds() for a,b in merged)/60
        if not minutes:continue
        url=urlsplit(details['url'])
        domain=url.netloc if url.scheme in ('http','https') else url.scheme+'://'+url.netloc
        sites[domain]+=minutes
        pages[domain][details['title']]+=minutes
    total=sum(sites.values())
    return [{'domain':domain,'minutes':round(minutes,3),'share':round(minutes/total,4),
             'pages':[{'title':title,'minutes':round(duration,3)}
                      for title,duration in sorted(pages[domain].items(),key=lambda item:(-item[1],item[0]))]}
            for domain,minutes in sorted(sites.items(),key=lambda item:(-item[1],item[0]))]
