"""Report-sized summaries for sources with different native granularities."""
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def distribution(totals):
    total=sum(totals.values())
    return [{'app':app,'minutes':round(minutes,3),'share':round(minutes/total,4) if total else 0}
            for app,minutes in sorted(totals.items(),key=lambda item:(-item[1],item[0]))]


def weight(rows, baseline):
    values=[row['data']['value'] for row in rows]
    last=values[-1] if values else None
    previous=baseline['data']['value'] if baseline else (values[0] if values else None)
    return {'measurement_count':len(values),'min':min(values,default=None),'max':max(values,default=None),
            'mean':round(sum(values)/len(values),3) if values else None,'last':last,
            'change':round(last-previous,3) if last is not None and previous is not None else None,
            'unit':rows[-1]['data']['unit'] if rows else None}


def sleep(rows, start, end):
    lower,upper=datetime.fromisoformat(start),datetime.fromisoformat(end)
    stages=defaultdict(float)
    intervals=[]
    for row in rows:
        data=row['data']
        begin=max(lower,datetime.fromisoformat(data['start']))
        finish=min(upper,datetime.fromisoformat(data['end']))
        stages[data['stage']]+=(finish-begin).total_seconds()/3600
        intervals.append((begin,finish))
    awake=sum(hours for stage,hours in stages.items() if '清醒' in stage or stage.lower()=='awake')
    in_bed=sum(hours for stage,hours in stages.items() if stage in ('卧床','inBed'))
    return {'sleep_hours':round(sum(stages.values())-awake-in_bed,3),'awake_hours':round(awake,3),
            'start':min((a for a,b in intervals),default=None).isoformat() if intervals else None,
            'end':max((b for a,b in intervals),default=None).isoformat() if intervals else None,
            'stages':[{'stage':stage,'hours':round(hours,3)} for stage,hours in stages.items()]}


def iphone(rows, report_timezone):
    daily={}
    for row in rows:
        day=datetime.fromisoformat(row['observed_at']).astimezone(ZoneInfo(report_timezone)).date().isoformat()
        daily[day]=row
    totals=defaultdict(float)
    days=[]
    for day,row in sorted(daily.items()):
        apps=row['data']['apps']
        for app in apps:totals[app['app']]+=app['duration']
        days.append({'date':day,'minutes':round(sum(a['duration'] for a in apps),3)})
    return {'total_minutes':round(sum(totals.values()),3),'apps':distribution(totals),'daily':days}


def pc(config, start, end, active_time):
    activity=active_time(config,start,end)
    totals=defaultdict(float)
    for app in activity['apps']:totals[app['app']]+=app['active_duration']/60
    hourly=[]
    current,upper=datetime.fromisoformat(start),datetime.fromisoformat(end)
    while current<upper:
        following=min(current.replace(minute=0,second=0,microsecond=0)+timedelta(hours=1),upper)
        activity=active_time(config,current.isoformat(),following.isoformat())
        minutes=sum(app['active_duration'] for app in activity['apps'])/60
        hourly.append({'start':current.isoformat(),'end':following.isoformat(),'minutes':round(minutes,3)})
        current=following
    return {'total_minutes':round(sum(totals.values()),3),'apps':distribution(totals),'hourly':hourly}


def todo(rows, baseline, start, end, following=None):
    lower,upper=datetime.fromisoformat(start),datetime.fromisoformat(end)
    snapshots=([baseline] if baseline else [])+rows
    last=snapshots[-1] if snapshots else None
    pending=sum(entry['task'].get('status')!='completed' for lst in last['data']['lists'] for entry in lst['tasks']) if last else 0
    snapshots += [following] if following else []
    completed={};appeared=set();disappeared=set();changed=set()
    previous={}
    for index,snapshot in enumerate(snapshots):
        tasks={(lst['list']['id'],entry['task']['id']):entry['task']
               for lst in snapshot['data']['lists'] for entry in lst['tasks']}
        observed=datetime.fromisoformat(snapshot['observed_at'])
        if index and lower<=observed<upper:
            appeared.update(tasks.keys()-previous.keys())
            disappeared.update(previous.keys()-tasks.keys())
            changed.update(key for key in tasks.keys()&previous.keys() if tasks[key]!=previous[key])
        for key,task in tasks.items():
            if task.get('status')!='completed':continue
            completion=task.get('completedDateTime')
            if completion:
                time=datetime.fromisoformat(completion['dateTime'].replace('Z','+00:00'))
                if time.tzinfo is None:
                    zone={'China Standard Time':'Asia/Shanghai','Singapore Standard Time':'Asia/Singapore'}.get(completion['timeZone'],completion['timeZone'])
                    time=time.replace(tzinfo=ZoneInfo(zone))
            elif key in previous and previous[key].get('status')!='completed':
                time=observed
            else:
                continue
            if lower<=time<upper:
                completed[key]={'list_id':key[0],'task_id':key[1],'title':task.get('title'),
                                'completed_at':time.isoformat()}
        previous=tasks
    return {'completed_count':len(completed),'completed_tasks':list(completed.values()),
            'pending_count':pending,
            'appeared_count':len(appeared),'disappeared_count':len(disappeared),'changed_count':len(changed)}


def activities(report, settings):
    """Use websites as browser activities and applications as other activities."""
    options=settings.get('summary',{})
    minimum=options.get('min_activity_minutes',1)
    titles=options.get('page_titles_per_site',3)
    aliases=options.get('website_names',{})
    browsers={app.lower() for app in settings.get('browser_apps',['msedge.exe'])}
    items=[];sites={}
    browser_minutes=sum(app['minutes'] for app in report['apps'] if app['app'].lower() in browsers)
    for site in report['websites']:
        name=aliases.get(site['domain'],site['domain'])
        group=sites.setdefault(name,{'minutes':0,'pages':defaultdict(float)})
        group['minutes']+=site['minutes']
        for page in site['pages']:group['pages'][page['title']]+=page['minutes']
    for name,site in sites.items():
        items.append({'kind':'website','name':name,'minutes':site['minutes'],
                      'topics':[title for title,_ in sorted(site['pages'].items(),key=lambda p:(-p[1],p[0]))[:titles]]})
    items.extend({'kind':'application','name':app['app'],'minutes':app['minutes']}
                 for app in report['apps'] if app['app'].lower() not in browsers)
    remainder=browser_minutes-sum(site['minutes'] for site in sites.values())
    if remainder>0:
        items.append({'kind':'browser','name':'其他浏览器活动','minutes':remainder})
    other=sum(item['minutes'] for item in items if item['minutes']<minimum)
    items=[item for item in items if item['minutes']>=minimum]
    if other:items.append({'kind':'other','name':'其他零散活动','minutes':other})
    for item in items:
        item['share']=round(item['minutes']/report['total_minutes'],4) if report['total_minutes'] else 0
        item['minutes']=round(item['minutes'],3)
    return sorted(items,key=lambda item:(-item['minutes'],item['name']))
