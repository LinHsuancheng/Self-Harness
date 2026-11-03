"""Calendar-aware source operators, using observed data as statistical denominators."""
from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
from . import periods, summary


def time(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)


def intersect(a,b,c,d):
    start,end=max(a,c),min(b,d)
    return (start,end) if start<end else None


def union(intervals):
    result=[]
    for a,b in sorted(intervals):
        if a>=b:continue
        if result and a<=result[-1][1]:result[-1]=(result[-1][0],max(result[-1][1],b))
        else:result.append((a,b))
    return result


def duration(intervals):
    return sum((b-a).total_seconds() for a,b in union(intervals))


def clip(rows,start,end):
    a,b=time(start),time(end)
    if rows and rows[0]['source'] in ('sleep','pc_screen_time'):
        return [r for r in rows if time(r['data']['end'])>a and time(r['observed_at'])<b]
    return [r for r in rows if a<=time(r['observed_at'])<b]


def coverage(source, rows, start, end):
    a,b=time(start),time(end)
    if source=='sleep':
        return union([span for r in rows if (span:=intersect(time(r['data']['start']),time(r['data']['end']),a,b))])
    if source=='pc_screen_time':
        streams=defaultdict(lambda:defaultdict(list))
        for r in rows:
            d=r['data'];kind=d['bucket_type']
            if kind in ('afkstatus','currentwindow'):
                span=intersect(time(d['start']),time(d['end']),a,b)
                if span:streams[d.get('hostname')][kind].append(span)
        spans=[]
        for kinds in streams.values():
            spans.extend(span for x,y in union(kinds['afkstatus']) for u,v in union(kinds['currentwindow'])
                         if (span:=intersect(x,y,u,v)))
        return union(spans)
    return []


def quality(source, rows, start, end, zone, completed=(), day_start_hour=0):
    daily=periods.days(start,end,zone,day_start_hour)
    intervals=coverage(source,rows,start,end)
    observed={periods.logical_date(r['observed_at'],zone,day_start_hour) for r in rows} if source not in ('sleep','pc_screen_time') else set()
    observed.update(c.get('completed_on') or periods.logical_date(c['completed_at'],zone,day_start_hour) for c in completed)
    for x,y in daily:
        if any(intersect(a,b,time(x),time(y)) for a,b in intervals):observed.add(periods.logical_date(x,zone,day_start_hour))
    dates=sorted(observed)
    points=[time(r['observed_at']) for r in rows]+[time(c['completed_at']) for c in completed if c.get('completed_at')]
    return {'record_count':len(rows),'calendar_days':len(daily),'effective_days':len(dates),
            'effective_dates':dates,'day_coverage':round(len(dates)/len(daily),4) if daily else 0,
            'time_coverage':round(duration(intervals)/(time(end)-time(start)).total_seconds(),4) if source in ('sleep','pc_screen_time') else None,
            'average_denominator':len(rows) if source=='weight' else len(dates),
            'observed_hours':round(duration(intervals)/3600,3) if source in ('sleep','pc_screen_time') else None,
            'observed_from':(min(a for a,b in intervals).isoformat() if intervals else min(points).isoformat() if points else None),
            'observed_to':(max(b for a,b in intervals).isoformat() if intervals else max(points).isoformat() if points else None)}


def sleep_sessions(rows,gap_minutes):
    sessions=[];gap=timedelta(minutes=gap_minutes)
    for row in rows:
        d=row['data'];a,b=time(d['start']),time(d['end'])
        if not sessions or a>sessions[-1]['end']+gap:
            sessions.append({'start':a,'end':b,'stages':[]})
        session=sessions[-1];session['end']=max(session['end'],b);session['stages'].append(d)
    output=[]
    for s in sessions:
        spans=[(time(d['start']),time(d['end'])) for d in s['stages'] if '清醒' not in d['stage'] and d['stage'] not in ('awake','卧床','inBed')]
        if spans:output.append({'start':s['start'].isoformat(),'end':s['end'].isoformat(),'sleep_hours':round(duration(spans)/3600,6),'_stages':s['stages']})
    return output


def histogram(sessions, field, zone):
    counts=defaultdict(int)
    for session in sessions:
        hour=periods.local(session[field],zone).hour
        counts[f'{hour//6*6:02d}:00-{hour//6*6+6:02d}:00']+=1
    total=sum(counts.values())
    return [{'time_band':name,'count':count,'share':round(count/total,4)} for name,count in sorted(counts.items())]


def select_baseline(rows,start):
    return next((r for r in reversed(rows) if time(r['observed_at'])<time(start)),None)


def following(rows,end):
    return next((r for r in rows if time(r['observed_at'])>=time(end)),None)


def calculate(config,source,rows,start,end,sessions=(),level='day',pc_rows=None,as_of=None):
    from . import operator
    as_of=as_of or datetime.now(timezone.utc)
    selected=clip(rows,start,end);zone=config.get('timezone',periods.DEFAULT_TIMEZONE)
    if source=='weight':result=summary.weight(selected,select_baseline(rows,start))
    elif source=='sleep':
        lower,upper=time(start),time(end)
        owned=[s for s in sessions if lower<=time(s['start'])<upper and time(s['end'])<=as_of]
        owned_rows=[{'data':stage} for session in owned for stage in session['_stages']]
        if owned_rows:
            full_start=min(stage['data']['start'] for stage in owned_rows)
            full_end=max(stage['data']['end'] for stage in owned_rows)
            result=summary.sleep(owned_rows,full_start,full_end)
        else:
            result=summary.sleep([],start,end)
        result['stages']=[stage for stage in result['stages']
                          if '清醒' not in stage['stage'] and stage['stage'] not in ('awake','卧床','inBed')]
        ongoing=[]
        for session in sessions:
            if lower<=time(session['start'])<upper and time(session['start'])<=as_of<time(session['end']):
                cutoff=min(upper,as_of)
                if time(session['start'])>=cutoff:continue
                spans=[]
                for stage in session['_stages']:
                    if '清醒' in stage['stage'] or stage['stage'] in ('awake','卧床','inBed'):continue
                    if span:=intersect(time(stage['start']),time(stage['end']),lower,cutoff):spans.append(span)
                ongoing.append({'start':session['start'],'end':periods.local(cutoff,zone).isoformat(),
                                'sleep_hours':round(duration(spans)/3600,6),'complete':False})
        result['session_count']=len(owned)
        result['average_session_hours']=round(sum(s['sleep_hours'] for s in owned)/len(owned),3) if owned else None
        result['sessions']=[{k:v for k,v in s.items() if k!='_stages'}|{'complete':True} for s in owned]
        result['ongoing_sessions']=ongoing
        result['sleep_start_distribution']=histogram(owned,'start',zone)
        result['wake_distribution']=histogram(owned,'end',zone)
        total=sum(s['hours'] for s in result['stages'])
        for stage in result['stages']:stage['share']=round(stage['hours']/total,4) if total else 0
    elif source=='iphone_screen_time':result=summary.iphone(rows,start,end,zone,config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR))
    elif source=='pc_screen_time':
        activity=operator.pc_active_time(config,start,end,selected)
        totals=defaultdict(float)
        for app in activity['apps']:totals[app['app']]+=app['active_duration']/60
        sites=operator.web_activity(config,start,end,selected,precision=9)
        result={'total_minutes':round(sum(totals.values()),6),'apps':[{'app':name,'minutes':minutes} for name,minutes in totals.items()],'websites':sites}
    elif source=='pc_screen_activity':
        pc_selected=clip(pc_rows or [],start,end)
        pc_coverage=coverage('pc_screen_time',pc_selected,start,end) if pc_rows is not None else []
        activity_available=bool(pc_coverage)
        active_intervals=(operator.pc_active_intervals(config,start,end,pc_selected)
                          if activity_available else [])
        result=summary.screen_activity(selected,start,end,zone,
                                       config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR),
                                       config['sources'][source],include_hourly=level=='day',
                                       include_timeline=level=='day',active_intervals=active_intervals)
        classified=result['total_minutes']
        active_minutes=round(duration(active_intervals)/60,3) if activity_available else None
        result.update({'activity_time_source':'activitywatch',
                       'activity_time_available':activity_available,
                       'activitywatch_coverage_minutes':round(duration(pc_coverage)/60,3),
                       'classified_minutes':classified,
                       'unclassified_minutes':round(max(0,active_minutes-classified),3)
                                              if active_minutes is not None else None,
                       'total_minutes':active_minutes})
        if active_minutes is not None:
            for key,name in (('categories','name'),('apps','app'),('topics','topic'),('focus','focus')):
                for item in result.get(key,[]):
                    item['share']=round(item['minutes']/active_minutes,4) if active_minutes else 0
        if level=='day':
            result['hourly']=[
                {'start':a,'end':b,'minutes':round(duration(
                    [span for x,y in active_intervals if (span:=intersect(x,y,time(a),time(b)))])/60,3)}
                for a,b in periods.hourly(start,end,zone)] if activity_available else []
            daily=[]
            for day_start,day_end in periods.days(
                    start,end,zone,config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR)):
                minutes=round(duration([span for x,y in active_intervals
                                       if (span:=intersect(x,y,time(day_start),time(day_end)))])/60,3)
                if minutes:
                    daily.append({'date':periods.logical_date(day_start,zone,
                                  config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR)),
                                  'minutes':minutes})
            result['daily']=daily
    else:
        result=summary.todo(selected,select_baseline(rows,start),start,end,following(rows,end))
        initial=select_baseline(rows,start)
        if not selected:result['pending_count']=None
        result['initial_pending_count']=sum(t['task'].get('status')!='completed' for l in initial['data']['lists'] for t in l['tasks']) if initial else None
        groups=defaultdict(int)
        for task in result['completed_tasks']:groups[task['list_id']]+=1
        names={l['list']['id']:l['list'].get('displayName',l['list']['id']) for r in rows for l in r['data']['lists']}
        result['completed_by_list']=[{'list_id':name,'list_name':names[name],'count':count,'share':round(count/result['completed_count'],4)} for name,count in sorted(groups.items())]
    q=quality(source,selected,start,end,zone,result.get('completed_tasks',()),config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR))
    if source=='todo':q['completion_count']=len(result['completed_tasks'])
    if source=='sleep':
        dates=sorted({periods.logical_date(s['start'],zone,config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR)) for s in owned})
        q['observed_days']=q['effective_days']
        q['effective_days']=len(dates);q['effective_dates']=dates;q['average_denominator']=len(dates)
        q['day_coverage']=round(len(dates)/q['calendar_days'],4)
        result['attributed_sleep_hours']=round(sum(s['sleep_hours'] for s in owned),3)
    count=q['effective_days']
    if source=='pc_screen_activity' and pc_rows is not None:
        pcq=quality('pc_screen_time',clip(pc_rows,start,end),start,end,zone,
                    day_start_hour=config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR))
        for key in ('effective_days','effective_dates','average_denominator','day_coverage',
                    'observed_from','observed_to'):
            q[key]=pcq[key]
        q['activitywatch_time_coverage']=pcq['time_coverage']
        q['activitywatch_observed_hours']=pcq['observed_hours']
        count=pcq['effective_days']
    if source=='sleep':result['daily_average_hours']=round(result['attributed_sleep_hours']/count,3) if count else None
    elif source in ('iphone_screen_time','pc_screen_time','pc_screen_activity'):
        result['daily_average_minutes']=(round(result['total_minutes']/count,3)
                                         if count and result['total_minutes'] is not None else None)
    elif source=='todo':result['daily_average_completed']=round(result['completed_count']/count,3) if count else None
    has_data=(bool(owned or ongoing) if source=='sleep' else
              (bool(selected) or result.get('activity_time_available') is True)
              if source=='pc_screen_activity' else bool(count))
    if not has_data:
        result={k:[] if isinstance(v,list) else None for k,v in result.items()}
        if source=='weight':result['unit']=config['sources'][source].get('unit')
    return result,q


def load(config,source,start,end):
    from . import operator
    with closing(operator.database(config,source)) as db:
        rows=[operator.material(source,r) for r in db.rows(start=start,end=end)]
        if source in ('weight','todo','iphone_screen_time'):
            earlier=db.rows(before=start)
            later=db.rows(start=end) if source=='todo' else []
            rows=([operator.material(source,earlier[-1])] if earlier else [])+rows+([operator.material(source,later[0])] if later else [])
        if source=='sleep':
            previous=db.rows(before=start)
            if previous and previous[-1]['end_at']==time(start).isoformat():
                rows=[operator.material(source,previous[-1])]+rows
        if source=='sleep' and rows:
            gap=timedelta(minutes=config['sources'][source].get('summary',{}).get('session_gap_minutes',30))
            while True:
                before=[operator.material(source,r) for r in db.rows(start=(time(rows[0]['observed_at'])-gap).isoformat(),end=rows[0]['observed_at'])]
                if not before:break
                known={r['observed_at'] for r in rows}
                before=[r for r in before if r['observed_at'] not in known]
                if not before:break
                rows=before+rows
            while True:
                last=max(time(r['data']['end']) for r in rows)
                after=[operator.material(source,r) for r in db.rows(start=last.isoformat(),end=(last+gap+timedelta(microseconds=1)).isoformat())]
                known={r['observed_at'] for r in rows};after=[r for r in after if r['observed_at'] not in known]
                if not after:break
                rows+=after
    return rows


def display(config,source,result,level):
    result=dict(result)
    if source=='pc_screen_time' and result.get('total_minutes') is not None:
        settings=dict(config['sources'][source]);settings['summary']=dict(settings.get('summary',{}))
        if level!='day':settings['summary']['page_titles_per_site']=1 if level=='week' else 0
        result['activities']=summary.activities(result,settings)
        del result['apps'],result['websites']
        if level!='day':
            major=result['activities'][:10];rest=result['activities'][10:]
            if rest:major.append({'kind':'other','name':'其他活动','minutes':round(sum(x['minutes'] for x in rest),3),'share':round(sum(x['share'] for x in rest),4)})
            result['activities']=major
    elif source=='pc_screen_time':
        result.pop('apps',None);result.pop('websites',None);result['activities']=[]
    elif source=='pc_screen_activity':
        result['activities']=[dict(item,kind='category') for item in result.get('categories',[])]
        if result.get('unclassified_minutes'):
            result['activities'].append({'kind':'other','name':'未分类活跃',
                                         'minutes':result['unclassified_minutes'],
                                         'share':round(result['unclassified_minutes']/result['total_minutes'],4)
                                                 if result.get('total_minutes') else 0})
        if level!='day':
            major=result['activities'][:10];rest=result['activities'][10:]
            if rest:major.append({'kind':'other','name':'其他活动','minutes':round(sum(x['minutes'] for x in rest),3),'share':round(sum(x['share'] for x in rest),4)})
            result['activities']=major
    if level!='day':
        for key in ('sessions','daily','hourly','timeline'):result.pop(key,None)
    return result


def comparison(source,current,prior,quality_current,quality_prior,start,end):
    metrics={}
    for key,value in current.items():
        if isinstance(value,(int,float)) or value is None:
            previous=prior.get(key)
            change=round(value-previous,6) if isinstance(value,(int,float)) and isinstance(previous,(int,float)) else None
            metrics[key]={'current':value,'previous':previous,'change':change}
    distributions={'pc_screen_time':[('activities','name')],'iphone_screen_time':[('apps','app')],
                   'pc_screen_activity':[('categories','name'),('apps','app'),('focus','focus')],
                   'sleep':[('stages','stage'),('sleep_start_distribution','time_band'),('wake_distribution','time_band')],
                   'todo':[('completed_by_list','list_name')]}.get(source,[])
    changes=[]
    if quality_current['effective_days'] and quality_prior['effective_days']:
        for key,name in distributions:
            a={x[name]:x for x in current.get(key,[])};b={x[name]:x for x in prior.get(key,[])}
            for n in a.keys()|b.keys():
                changes.append({'distribution':key,'name':n,'share_change':round(a.get(n,{}).get('share',0)-b.get(n,{}).get('share',0),4)})
        changes.sort(key=lambda x:-abs(x['share_change']))
    return {'period':{'start':start,'end':end},'data_quality':quality_prior,'metrics':metrics,'distribution_changes':changes[:10]}


def report(config,source,start,end,level,as_of=None):
    zone=config.get('timezone',periods.DEFAULT_TIMEZONE)
    day_start_hour=config.get('day_start_hour',periods.DEFAULT_DAY_START_HOUR)
    if as_of is None:as_of=datetime.now(timezone.utc)
    elif isinstance(as_of,str):as_of=time(as_of)
    else:
        if as_of.tzinfo is None:as_of=as_of.replace(tzinfo=ZoneInfo(zone))
        as_of=as_of.astimezone(timezone.utc)
    start,end=periods.local(start,zone).isoformat(),periods.local(end,zone).isoformat()
    if time(start)>=time(end):raise ValueError('Start must precede end')
    prior_start,prior_end=periods.previous(start,end,level,zone)
    rows=load(config,source,min(prior_start,start),max(prior_end,end))
    pc_rows=(load(config,'pc_screen_time',min(prior_start,start),max(prior_end,end))
             if source=='pc_screen_activity' and 'pc_screen_time' in config['sources'] else None)
    sessions=sleep_sessions(rows,config['sources'][source].get('summary',{}).get('session_gap_minutes',30)) if source=='sleep' else []
    def compute(a,b):
        return calculate(config,source,rows,a,b,sessions,level=level,pc_rows=pc_rows,as_of=as_of)
    current,q=compute(start,end)
    prior,pq=compute(prior_start,prior_end)
    trend=[]
    for a,b in periods.buckets(start,end,level,zone,day_start_hour):
        item,iq=compute(a,b)
        compact={k:v for k,v in item.items() if not isinstance(v,list)}
        trend.append({'period':{'start':a,'end':b},'summary':compact,'data_quality':iq})
    comparison_current,comparison_prior=dict(current),dict(prior)
    if source=='pc_screen_time':
        settings=dict(config['sources'][source]);settings['summary']=dict(settings.get('summary',{}),min_activity_minutes=0,page_titles_per_site=0)
        for result in (comparison_current,comparison_prior):
            result['activities']=summary.activities(result,settings) if result['total_minutes'] is not None else []
    compared=comparison(source,comparison_current,comparison_prior,q,pq,prior_start,prior_end)
    current=display(config,source,current,level)
    if source=='pc_screen_time' and level=='day':
        hourly=[]
        for hour_start,hour_end in periods.hourly(start,end,zone):
            item,iq=compute(hour_start,hour_end)
            if iq['effective_days']:hourly.append({'start':hour_start,'end':hour_end,'minutes':item['total_minutes'],'observed_hours':iq['observed_hours']})
        current['hourly']=hourly
    focus={'weight':'mean','sleep':'daily_average_hours','iphone_screen_time':'daily_average_minutes','pc_screen_time':'daily_average_minutes','pc_screen_activity':'daily_average_minutes','todo':'daily_average_completed'}[source]
    valid=[t for t in trend if t['summary'].get(focus) is not None]
    highlights=[]
    if valid:
        peak=max(valid,key=lambda t:t['summary'][focus])
        highlights.append({'metric':focus,'period':peak['period'],'value':peak['summary'][focus]})
    if level not in ('day','week'):
        q.pop('effective_dates',None);compared['data_quality'].pop('effective_dates',None)
        for item in trend:item['data_quality'].pop('effective_dates',None)
    return {'source':source,'level':level,'period':{'start':start,'end':end},'data_quality':q,
            'summary':current,'trend':trend,'comparison':compared,'highlights':highlights}
