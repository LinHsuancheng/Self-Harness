"""One check for the five report-facing operators using stored materials."""
import gzip
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from interfaces.operator import ingest, summarize, context

with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    config={'raw_dir':str(root/'raw'),'database_dir':str(root/'db'),'timezone':'Asia/Singapore',
            'sources':{s:{} for s in ('weight','sleep','iphone_screen_time','pc_screen_time','todo')}}
    start,end='2026-10-13T00:00:00+08:00','2026-10-14T00:00:00+08:00'
    def put(source,name,value):
        path=root/'raw'/source/'2026-10-13'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(gzip.compress(value.encode()))
    put('weight','w.gz','2026-10-13T08:00:00+08:00,77\n2026-10-13T20:00:00+08:00,78\n')
    put('sleep','s.gz','核心睡眠,2026-10-13T00:00:00+08:00,2026-10-13T06:00:00+08:00\n清醒时间,2026-10-13T06:00:00+08:00,2026-10-13T06:30:00+08:00\n')
    put('iphone_screen_time','i1.gz','2026-10-13T12:00:00+08:00,App,30分钟\n')
    put('iphone_screen_time','i2.gz','2026-10-13T20:00:00+08:00,App,90分钟\n2026-10-13T20:00:00+08:00,Browser,30分钟\n')
    buckets=[{'bucket':{'id':'afk','type':'afkstatus','hostname':'pc'},'events':[
        {'id':1,'timestamp':'2026-10-13T08:00:00+08:00','duration':3600,'data':{'status':'not-afk'}}]},
        {'bucket':{'id':'window','type':'currentwindow','hostname':'pc'},'events':[
        {'id':2,'timestamp':'2026-10-13T08:00:00+08:00','duration':3600,'data':{'app':'msedge.exe'}}]}]
    buckets.append({'bucket':{'id':'web','type':'web.tab.current','hostname':'pc'},'events':[
        {'id':3,'timestamp':'2026-10-13T08:00:00+08:00','duration':1800,'data':{'url':'https://example.com/read','title':'Reading'}},
        {'id':5,'timestamp':'2026-10-13T10:00:00+08:00','duration':3600,'data':{'url':'https://background.test','title':'Background'}},
        {'id':4,'timestamp':'2026-10-13T08:30:00+08:00','duration':1800,'data':{'url':'https://example.org/work','title':'Working'}}]})
    put('pc_screen_time','p.gz',json.dumps({'start':start,'end':end,'duration_unit':'seconds','buckets':buckets}))
    for i,observed in enumerate(('2026-10-12T23:00:00+08:00','2026-10-13T20:00:00+08:00')):
        task={'id':'t','title':'Ship operator','status':'notStarted' if i==0 else 'completed'}
        if i:task['completedDateTime']={'dateTime':'2026-10-13T10:00:00.0000000','timeZone':'UTC'}
        put('todo',str(i)+'.gz',json.dumps({'complete':True,'observed_at':observed,'lists':[{'list':{'id':'l'},'tasks':[{'task':task,'checklist':[]}]}]}))
    for source in config['sources']:ingest(config,source)
    weight=summarize(config,'weight',start,end)['summary']
    assert (weight['min'],weight['max'],weight['mean'])==(77,78,77.5)
    assert summarize(config,'sleep',start,end)['summary']['sleep_hours']==6
    phone=summarize(config,'iphone_screen_time',start,end)['summary']
    assert phone['total_minutes']==120 and phone['apps'][0]['share']==0.75
    pc=summarize(config,'pc_screen_time',start,end)['summary']
    assert pc['total_minutes']==60 and sum(h['minutes'] for h in pc['hourly'])==60
    assert len(pc['activities'])==2 and sum(site['minutes'] for site in pc['activities'])==60
    assert pc['activities'][0]['topics']==['Reading']
    todo=summarize(config,'todo',start,end)['summary']
    assert todo['completed_count']==1 and todo['pending_count']==0
    result=context(config,start,end)
    assert all('summary' in item and 'materials' not in item for item in result.values())
    assert len(json.dumps(result))<10000
    later={'complete':True,'observed_at':'2026-10-14T00:00:00+08:00','lists':[{'list':{'id':'l'},'tasks':[
        {'task':{'id':'late','title':'Late completion','status':'completed','completedDateTime':{'dateTime':'2026-10-13T15:30:00','timeZone':'UTC'}},'checklist':[]}]}]}
    put('todo','later.gz',json.dumps(later))
    ingest(config,'todo')
    later_summary=summarize(config,'todo',start,end)['summary']
    assert later_summary['completed_count']==2
    assert later_summary['pending_count']==0
print('PASS: weight range, sleep hours, app distributions, hourly PC usage, completed tasks, compact context')

from interfaces.summary import activities
report={'total_minutes':12,'apps':[{'app':'msedge.exe','minutes':10},{'app':'Editor','minutes':1.5},{'app':'Helper','minutes':0.5}],
        'websites':[{'domain':'a.test','minutes':6,'pages':[{'title':'Read','minutes':6}]},
                    {'domain':'b.test','minutes':3,'pages':[{'title':'Work','minutes':3}]}]}
items=activities(report,{'browser_apps':['msedge.exe'],'summary':{'min_activity_minutes':1,'page_titles_per_site':3}})
assert not any(item['name']=='msedge.exe' for item in items)
assert sum(item['minutes'] for item in items)==12
assert next(item for item in items if item['name']=='a.test')['topics']==['Read']
assert any(item['kind']=='other' for item in items)
print('PASS: browser replaced by sites, minor activities grouped, total duration retained')
