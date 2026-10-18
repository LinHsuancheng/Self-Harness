"""Generate/install native systemd units from configuration."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo
from interface import load_config
from interfaces.periods import DEFAULT_TIMEZONE

parser=argparse.ArgumentParser()
parser.add_argument('--config',default='config.json')
parser.add_argument('--role',choices=['server'],required=True)
parser.add_argument('--report-only',action='store_true',help='install only the server daily report timer')
parser.add_argument('--install',action='store_true')
args=parser.parse_args()
config_path=Path(args.config).resolve()
config=load_config(config_path)
project=Path(__file__).resolve().parent
unit_dir=Path('/etc/systemd/system')

# --- collector service (persistent, not a timer) ---
if not args.report_only:
    collector_command=f'{json.dumps(sys.executable)} {json.dumps(str(project/"server.py"))}'
    collector_service=f'''[Unit]
Description=Self Harness raw material collector
After=network.target

[Service]
Type=simple
WorkingDirectory={project}
Environment=SELF_HARNESS_CONFIG={config_path}
ExecStart={collector_command}
Restart=on-failure
RestartSec=3
UMask=0077

[Install]
WantedBy=multi-user.target
'''
    if args.install:
        unit_dir.mkdir(parents=True,exist_ok=True)
        (unit_dir/'self-harness-collector.service').write_text(collector_service)
    else:
        print('self-harness-collector.service\n'+collector_service)

# --- periodic timers ---
if args.report_only:
    jobs=[]
else:
    jobs=[('ingest','interface.py',' ingest',config['schedule']['ingest_seconds']),
          ('todo','interface.py',' fetch todo',config['schedule']['todo_seconds'])]
units=[]
for name,script,extra,seconds in jobs:
    if not isinstance(seconds,int) or seconds<1:
        raise ValueError('Schedule seconds must be positive integers')
    unit='self-harness-'+name
    command=f'{json.dumps(sys.executable)} {json.dumps(str(project/script))} --config {json.dumps(str(config_path))}{extra}'
    service=f'''[Unit]
Description=Self Harness {name}

[Service]
Type=oneshot
WorkingDirectory={project}
ExecStart={command}
UMask=0077
'''
    timer=f'''[Unit]
Description=Self Harness {name} timer

[Timer]
OnBootSec=30
OnUnitInactiveSec={seconds}s
Unit={unit}.service

[Install]
WantedBy={'timers.target'}
'''
    if args.install:
        unit_dir.mkdir(parents=True,exist_ok=True)
        (unit_dir/(unit+'.service')).write_text(service)
        (unit_dir/(unit+'.timer')).write_text(timer)
    else:
        print(unit+'.service\n'+service+'\n'+unit+'.timer\n'+timer)
    units.append(unit+'.timer')

# --- daily report timer ---
report_time=config.get('schedule',{}).get('report_time','09:00')
if not isinstance(report_time,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',report_time):
    raise ValueError('schedule.report_time must use HH:MM')
timezone=config.get('timezone',DEFAULT_TIMEZONE)
if not isinstance(timezone,str):
    raise ValueError('timezone must be an IANA timezone name')
ZoneInfo(timezone)
unit='self-harness-report'
command=f'{json.dumps(sys.executable)} -m core.run --config {json.dumps(str(config_path))} --level day --date yesterday --send-email'
service=f'''[Unit]
Description=Self Harness daily report

[Service]
Type=oneshot
WorkingDirectory={project}
ExecStart={command}
UMask=0077
'''
timer=f'''[Unit]
Description=Self Harness daily report timer

[Timer]
OnCalendar=*-*-* {report_time}:00 {timezone}
AccuracySec=1s
Persistent=true
Unit={unit}.service

[Install]
WantedBy=timers.target
'''
if args.install:
    unit_dir.mkdir(parents=True,exist_ok=True)
    (unit_dir/(unit+'.service')).write_text(service)
    (unit_dir/(unit+'.timer')).write_text(timer)
else:
    print(unit+'.service\n'+service+'\n'+unit+'.timer\n'+timer)
units.append(unit+'.timer')

if args.install:
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now']+units,check=True)
    # collector is a service, not a timer — enable separately if newly written
    subprocess.run(['systemctl','enable','self-harness-collector.service'],check=True)
    print('Installed: '+', '.join(units)+', self-harness-collector.service')
