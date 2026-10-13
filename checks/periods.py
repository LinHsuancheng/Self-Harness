"""Acceptance check for calendar periods, effective data and interval boundaries."""
import gzip
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from interfaces.periods import bounds, previous, buckets
from interfaces.operator import ingest, summarize, context

assert bounds('month','2024-02-20','Asia/Singapore')==('2024-02-01T00:00:00+08:00','2024-03-01T00:00:00+08:00')
assert previous('2024-03-01T00:00:00+08:00','2024-04-01T00:00:00+08:00','month','Asia/Singapore')==('2024-02-01T00:00:00+08:00','2024-03-01T00:00:00+08:00')
assert len(buckets('2026-01-01T00:00:00+08:00','2027-01-01T00:00:00+08:00','year','Asia/Singapore'))==12
assert len(buckets('2026-10-01T00:00:00+08:00','2026-11-01T00:00:00+08:00','month','Asia/Singapore'))==5
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    config={'raw_dir':str(root/'raw'),'database_dir':str(root/'db'),'timezone':'Asia/Singapore',
            'sources':{s:{} for s in ('weight','sleep','iphone_screen_time','pc_screen_time','todo')}}
    def put(source,name,value):
        path=root/'raw'/source/'2026-10-13'/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(gzip.compress(value.encode()))
    put('weight','w.gz','2026-10-02T08:00:00+08:00,77\n2026-10-05T08:00:00+08:00,79\n')
    put('sleep','s.gz','核心睡眠,2026-10-02T14:00:00+08:00,2026-10-02T18:00:00+08:00\n深度睡眠,2026-10-02T18:00:00+08:00,2026-10-02T20:00:00+08:00\n核心睡眠,2026-10-03T23:00:00+08:00,2026-10-04T02:00:00+08:00\n')
    for source in ('weight','sleep'):ingest(config,source)
    start,end='2026-10-01T00:00:00+08:00','2026-11-01T00:00:00+08:00'
    weight=summarize(config,'weight',start,end,level='month')
    assert weight['data_quality']['effective_days']==2
    assert weight['data_quality']['calendar_days']==31
    assert weight['summary']['mean']==78
    assert weight['comparison']['metrics']['mean']['change'] is None
    assert len(weight['trend'])==5
    assert any(t['summary']['mean'] is None for t in weight['trend'])
    sleep=summarize(config,'sleep',start,end,level='month')
    assert sleep['summary']['sleep_hours']==9
    assert sleep['data_quality']['effective_days']==2
    assert sleep['summary']['daily_average_hours']==4.5
    assert sleep['summary']['session_count']==2
    assert sleep['summary']['average_session_hours']==4.5
    left=summarize(config,'sleep','2026-10-03T00:00:00+08:00','2026-10-04T00:00:00+08:00')
    right=summarize(config,'sleep','2026-10-04T00:00:00+08:00','2026-10-05T00:00:00+08:00')
    assert left['summary']['sleep_hours']+right['summary']['sleep_hours']==3
    assert right['summary']['sessions'][0]['sleep_hours']==3
    put('sleep','midnight.gz','核心睡眠,2026-10-05T18:00:00+08:00,2026-10-06T00:00:00+08:00\n')
    ingest(config,'sleep')
    midnight=summarize(config,'sleep','2026-10-06T00:00:00+08:00','2026-10-07T00:00:00+08:00')
    assert midnight['summary']['session_count']==1
    assert midnight['summary']['daily_average_hours']==6
    result=context(config,start,end,level='month')
    assert len(result)==5 and result['iphone_screen_time']['summary']['total_minutes'] is None
    assert result['todo']['summary']['completed_count'] is None
print('PASS: leap months, calendar buckets, effective days, missing comparisons, daytime and cross-boundary sleep')
