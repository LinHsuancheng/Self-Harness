"""Acceptance: data fidelity, revisions, interval queries and durable failure status."""
import gzip
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from interfaces.operator import ingest, query, latest_before, status, pc_active_time, todo_changes

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config = {'raw_dir': str(root/'raw'), 'database_dir': str(root/'db'),
              'sources': {'weight': {'unit': None}, 'sleep': {}, 'pc_screen_time': {}, 'iphone_screen_time': {}, 'todo': {}}}
    def write(source, name, value):
        path = root/'raw'/source/'2026-10-13'/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(gzip.compress(value.encode()))
        return path
    weight = '2026-10-13T12:00:00+08:00,77.45\n'
    write('weight', 'a.csv.gz', weight)
    write('weight', 'b.csv.gz', weight)
    ingest(config, 'weight')
    rows = query(config, 'weight', '2026-10-13T00:00:00+08:00', '2026-10-14T00:00:00+08:00')
    assert len(rows) == 1 and rows[0]['data']['value'] == 77.45
    assert rows[0]['data']['unit'] is None
    assert latest_before(config, 'weight', '2026-10-14T00:00:00+08:00')['data']['value'] == 77.45
    write('weight', 'c.csv.gz', '2026-10-13T12:00:00+08:00,77.6\n')
    ingest(config, 'weight')
    assert query(config, 'weight', '2026-10-13T00:00:00Z','2026-10-14T00:00:00Z')[0]['data']['value'] == 77.6
    write('weight', 'revert.csv.gz', weight)
    ingest(config, 'weight')
    assert query(config,'weight','2026-10-13T00:00:00Z','2026-10-14T00:00:00Z')[0]['data']['value'] == 77.45
    write('weight', 'd.csv.gz', 'bad,row,extra\n')
    ingest(config, 'weight')
    assert status(config, 'weight')['failed_files'] == 1
    write('sleep','s.csv.gz','核心睡眠,2026-10-12T23:00:00+08:00,2026-10-13T02:00:00+08:00\n')
    ingest(config,'sleep')
    assert len(query(config,'sleep','2026-10-13T00:00:00+08:00','2026-10-13T01:00:00+08:00')) == 1
    assert not query(config,'sleep','2026-10-13T02:00:00+08:00','2026-10-13T03:00:00+08:00')
    write('sleep','s2.csv.gz','核心睡眠,2026-10-12T23:00:00+08:00,2026-10-13T03:00:00+08:00\n')
    ingest(config,'sleep')
    assert len(query(config,'sleep','2026-10-13T00:00:00+08:00','2026-10-13T04:00:00+08:00'))==1
    def pc_snapshot(end, duration):
        return json.dumps({'start':'2026-10-13T00:00:00Z','end':end,'duration_unit':'seconds','buckets':[
            {'bucket':{'id':'afk','type':'afkstatus','hostname':'pc'},'events':[
                {'id':1,'timestamp':'2026-10-13T00:00:00Z','duration':20,'data':{'status':'not-afk'}}]},
            {'bucket':{'id':'window','type':'currentwindow','hostname':'pc'},'events':[
                {'id':7,'timestamp':'2026-10-13T00:00:00Z','duration':duration,'data':{'app':'editor'}}]}]})
    write('pc_screen_time','p1.json.gz',pc_snapshot('2026-10-13T00:00:30Z',10))
    ingest(config,'pc_screen_time')
    write('pc_screen_time','p2.json.gz',pc_snapshot('2026-10-13T00:01:00Z',30))
    ingest(config,'pc_screen_time')
    write('pc_screen_time','late.json.gz',pc_snapshot('2026-10-13T00:00:30Z',10))
    ingest(config,'pc_screen_time')
    result=pc_active_time(config,'2026-10-13T00:00:05Z','2026-10-13T00:00:25Z')
    assert result['apps'][0]['active_duration']==15
    assert len(query(config,'pc_screen_time','2026-10-13T00:00:00Z','2026-10-13T00:02:00Z'))==2
    write('pc_screen_time','new-same.json.gz',pc_snapshot('2026-10-13T00:03:00Z',30))
    ingest(config,'pc_screen_time')
    write('pc_screen_time','middle.json.gz',pc_snapshot('2026-10-13T00:02:00Z',15))
    ingest(config,'pc_screen_time')
    current=query(config,'pc_screen_time','2026-10-13T00:00:00Z','2026-10-13T00:05:00Z')
    assert next(r for r in current if r['data']['bucket_type']=='currentwindow')['data']['duration']==30
    for index, observed in enumerate(('2026-10-13T01:00:00Z','2026-10-13T02:00:00Z')):
        snapshot={'complete':True,'observed_at':observed,'lists':[{'list':{'id':'l'},'tasks':[
            {'task':{'id':'t','status':'notStarted' if index==0 else 'completed'},'checklist':[]}]}]}
        write('todo',str(index)+'.json.gz',json.dumps(snapshot))
    ingest(config,'todo')
    changes=todo_changes(config,'2026-10-13T01:30:00Z','2026-10-13T03:00:00Z')
    assert len(changes)==1 and len(changes[0]['changed'])==1
    write('todo','partial.json.gz',json.dumps({'complete':False,'lists':[]}))
    ingest(config,'todo')
    assert status(config,'todo')['failed_files']==1
    for index,observed in enumerate(('2026-10-13T01:00:00Z','2026-10-13T02:00:00Z')):
        write('iphone_screen_time',str(index)+'.csv.gz',observed+',App,12.5分钟\n')
    ingest(config,'iphone_screen_time')
    assert len(query(config,'iphone_screen_time','2026-10-13T00:00:00Z','2026-10-13T03:00:00Z'))==2
print('PASS: first row, repeat files, event revisions, unknown unit, history baseline, parse failure, overlapping intervals')
