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


def iphone(rows, start, end, report_timezone, day_start_hour=9):
    """Build a logical day from near-boundary and near-midnight cumulative snapshots."""
    zone=ZoneInfo(report_timezone);lower=datetime.fromisoformat(start).astimezone(zone);upper=datetime.fromisoformat(end).astimezone(zone)
    snapshots=sorted((datetime.fromisoformat(r['observed_at']).astimezone(zone),r) for r in rows)
    totals=defaultdict(float);daily=defaultdict(float);reasons=[];coverage_starts=[];coverage_ends=[]
    cursor=lower
    while cursor<upper:
        day=cursor.date()
        midnight=datetime.combine(day,datetime.min.time(),zone);morning=midnight+timedelta(hours=day_start_hour);night=midnight+timedelta(days=1)
        next_morning=night+timedelta(hours=day_start_hour)
        def latest(a,b):
            found=[x for x in snapshots if a<=x[0]<=b]
            return found[-1] if found else None
        base=latest(midnight,morning);end_day=latest(morning,night-timedelta(microseconds=1));end_morning=latest(night,next_morning)
        label=day.isoformat()
        for name,value in ((f'D日{day_start_hour:02d}点',base),('D日24点',end_day),(f'D+1日{day_start_hour:02d}点',end_morning)):
            if value is None:reasons.append(f'{label} 缺少{name}附近快照')
        if base and end_day:
            a={x['app']:x['duration'] for x in base[1]['data']['apps']};b={x['app']:x['duration'] for x in end_day[1]['data']['apps']}
            for app in a.keys()|b.keys():daily[label]+=max(0,b.get(app,0)-a.get(app,0));totals[app]+=max(0,b.get(app,0)-a.get(app,0))
            coverage_starts.append(base[0]);coverage_ends.append(end_day[0])
        if end_morning:
            for item in end_morning[1]['data']['apps']:daily[label]+=max(0,item['duration']);totals[item['app']]+=max(0,item['duration'])
            coverage_ends.append(end_morning[0])
        cursor+=timedelta(days=1)
    days=[{'date':day,'minutes':round(minutes,3)} for day,minutes in sorted(daily.items())]
    coverage={'estimated':True,'incomplete':bool(reasons),'reason':'；'.join(dict.fromkeys(reasons)) or '使用09点与24点附近快照计算',
              'covered_from':min(coverage_starts).isoformat() if coverage_starts else None,
              'covered_to':max(coverage_ends).isoformat() if coverage_ends else None}
    return {'total_minutes':round(sum(totals.values()),3),'apps':distribution(totals),'daily':days,'coverage':coverage}


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


def completion(task):
    """Return (instant, date_only); To Do drops the clock, leaving midnight stamps."""
    value=task.get('completedDateTime')
    if not isinstance(value,dict) or not value.get('dateTime'):return None,False
    stamp=datetime.fromisoformat(value['dateTime'].replace('Z','+00:00'))
    date_only=stamp.time()==datetime.min.time()
    if stamp.tzinfo is None:
        zone={'China Standard Time':'Asia/Shanghai','Singapore Standard Time':'Asia/Singapore'}.get(value.get('timeZone'),value.get('timeZone'))
        stamp=stamp.replace(tzinfo=ZoneInfo(zone))
    return stamp,date_only


def todo(rows, baseline, start, end, following=None):
    lower,upper=datetime.fromisoformat(start),datetime.fromisoformat(end)
    snapshots=([baseline] if baseline else [])+rows
    last=snapshots[-1] if snapshots else None
    pending=0
    pending_tasks=[]
    if last:
        for lst in last['data']['lists']:
            for entry in lst['tasks']:
                task=entry['task']
                if task.get('status')=='completed':continue
                pending+=1
                pending_tasks.append({'list_id':lst['list']['id'],
                                      'list_name':lst['list'].get('displayName',lst['list']['id']),
                                      'title':task.get('title'),
                                      'status':task.get('status'),
                                      'importance':task.get('importance'),
                                      'due':(task.get('dueDateTime') or {}).get('dateTime')})
    snapshots += [following] if following else []
    completed={};created={};appeared=set();disappeared=set();changed=set()
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
            created_at=task.get('createdDateTime')
            if isinstance(created_at,dict):created_at=created_at.get('dateTime')
            if created_at:
                created_time=datetime.fromisoformat(created_at.replace('Z','+00:00'))
                if lower<=created_time<upper:
                    created[key]={'list_id':key[0],'task_id':key[1],'title':task.get('title'),
                                  'created_at':created_time.isoformat()}
            if task.get('status')!='completed':continue
            stamp,date_only=completion(task)
            if stamp is None:
                if key not in previous or previous[key].get('status')=='completed':continue
                stamp,date_only=observed,False
            inside=lower.date()<=stamp.date()<upper.date() if date_only else lower<=stamp<upper
            if inside:
                completed[key]={'list_id':key[0],'task_id':key[1],'title':task.get('title'),
                                'created_at':created_at,'completed_at':None if date_only else stamp.isoformat(),
                                'completed_on':stamp.date().isoformat() if date_only else None,
                                'date_only':date_only}
        previous=tasks
    return {'created_count':len(created),'created_tasks':list(created.values()),
            'completed_count':len(completed),'completed_tasks':list(completed.values()),
            'pending_count':pending,'pending_tasks':pending_tasks,
            'appeared_count':len(appeared),'disappeared_count':len(disappeared),'changed_count':len(changed)}


def screen_activity(rows, start, end, report_timezone, day_start_hour=9, settings=None,
                    include_hourly=False, include_timeline=False):
    """Aggregate 5-minute screenshot samples; idle samples are coverage, not active time."""
    from . import periods, screen
    settings = settings or {}
    sample = float(settings.get('sample_minutes', 5))
    names = settings.get('category_names', {})
    focus_names = settings.get('focus_names', {})
    lower, upper = datetime.fromisoformat(start), datetime.fromisoformat(end)
    ordered = sorted(rows, key=lambda row: row['observed_at'])
    categories = defaultdict(float)
    apps = defaultdict(float)
    topics = defaultdict(float)
    focus = defaultdict(float)
    daily = defaultdict(float)
    hours = []
    if include_hourly:
        for a, b in periods.hourly(start, end, report_timezone):
            hours.append({'start': a, 'end': b, 'minutes': 0.0})
    hourly = {item['start']: item for item in hours}
    timeline = []
    session = None

    def finish_session():
        nonlocal session
        if session is None:
            return
        focus_name = max(session['_focus'], key=session['_focus'].get)
        timeline.append({
            'start': session['start'], 'end': session['end'],
            'minutes': round(session['_seconds']/60, 3),
            'category': session['category'], 'activity': session['activity'],
            'focus': focus_name, 'apps': session['apps'], 'topics': session['topics'],
            'summary': session['summary'], 'sample_count': session['sample_count'],
            'average_confidence': round(session['_confidence']/session['sample_count'], 4),
        })
        session = None

    total = observed = idle = 0.0
    captures = active_captures = sensitive_captures = 0
    for index, row in enumerate(ordered):
        analysis = row.get('data', {}).get('analysis')
        if not isinstance(analysis, dict):
            continue
        current = datetime.fromisoformat(row['observed_at'])
        following = (datetime.fromisoformat(ordered[index+1]['observed_at'])
                     if index+1 < len(ordered) else None)
        seconds = sample*60
        if following is not None:
            seconds = min(seconds, (following-current).total_seconds())
        seconds = max(0.0, min(seconds, (upper-current).total_seconds()))
        if not seconds:
            continue
        captures += 1
        observed += seconds
        is_idle = analysis.get('focus') == 'idle' or analysis.get('activity') == 'idle'
        is_sensitive = bool(analysis.get('sensitive'))
        if include_timeline:
            session_key = (('sensitive',) if is_sensitive else ('idle',) if is_idle else
                           ('active', analysis.get('category'), analysis.get('activity')))
            contiguous = (session is not None and session['_key'] == session_key and
                          (current-session['_last_observed']).total_seconds() <= sample*60)
            if not contiguous:
                finish_session()
                session = {
                    '_key': session_key, '_last_observed': current, '_seconds': 0.0,
                    '_confidence': 0.0, '_focus': defaultdict(float),
                    'start': current.isoformat(), 'end': current.isoformat(),
                    'category': names.get(analysis.get('category'), analysis.get('category') or 'other'),
                    'activity': analysis.get('activity') or 'other', 'apps': [], 'topics': [],
                    'summary': '', 'sample_count': 0,
                }
            session['_last_observed'] = current
            session['_seconds'] += seconds
            session['end'] = (current+timedelta(seconds=seconds)).isoformat()
            session['sample_count'] += 1
            confidence = analysis.get('confidence', 0)
            session['_confidence'] += confidence if isinstance(confidence, (int, float)) else 0
            focus_name = focus_names.get(analysis.get('focus'), analysis.get('focus') or 'other')
            session['_focus'][focus_name] += seconds
            if is_sensitive:
                session['apps'] = []
                session['topics'] = []
                session['summary'] = screen.SENSITIVE_SUMMARY
            else:
                app = analysis.get('app') or 'unknown'
                if app not in session['apps']:
                    session['apps'].append(app)
                for topic in analysis.get('topics', []):
                    if isinstance(topic, str) and topic and topic not in session['topics']:
                        session['topics'].append(topic)
                if analysis.get('summary'):
                    session['summary'] = analysis['summary']
        if is_idle:
            idle += seconds
        else:
            total += seconds
            active_captures += 1
            minutes = seconds/60
            categories[names.get(analysis.get('category'), analysis.get('category') or 'other')] += minutes
            apps[analysis.get('app') or 'unknown'] += minutes
            for topic in analysis.get('topics', []):
                if isinstance(topic, str) and topic:
                    topics[topic] += minutes
        focus[focus_names.get(analysis.get('focus'), analysis.get('focus') or 'other')] += seconds/60
        if analysis.get('sensitive'):
            sensitive_captures += 1
        day = periods.logical_date(row['observed_at'], report_timezone, day_start_hour)
        if not is_idle:
            daily[day] += seconds/60
        if include_hourly:
            key = periods.local(row['observed_at'], report_timezone).replace(
                minute=0, second=0, microsecond=0).isoformat()
            if key in hourly:
                hourly[key]['minutes'] += 0 if is_idle else seconds/60

    finish_session()

    def distribution(counter, key):
        amount = sum(counter.values())
        return [{key: name, 'minutes': round(value, 3),
                 'share': round(value/amount, 4) if amount else 0}
                for name, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:10]]

    return {'total_minutes': round(total/60, 3),
            'observed_minutes': round(observed/60, 3),
            'idle_minutes': round(idle/60, 3),
            'captures': captures,
            'active_captures': active_captures,
            'sensitive_captures': sensitive_captures,
            'sample_minutes': sample,
            'categories': distribution(categories, 'name'),
            'apps': distribution(apps, 'app'),
            'topics': distribution(topics, 'topic'),
            'focus': distribution(focus, 'focus'),
            'daily': [{'date': day, 'minutes': round(minutes, 3)} for day, minutes in sorted(daily.items())],
            'timeline': timeline,
            'hourly': [{'start': item['start'], 'end': item['end'], 'minutes': round(item['minutes'], 3)}
                       for item in hours]}


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
