"""Generate/install native systemd timers from the configured intervals."""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from interface import load_config

parser=argparse.ArgumentParser()
parser.add_argument('--config',default='config.json')
parser.add_argument('--role',choices=['server','pc'],required=True)
parser.add_argument('--install',action='store_true')
args=parser.parse_args()
config_path=Path(args.config).resolve()
config=load_config(config_path)
project=Path(__file__).resolve().parent
user=args.role=='pc'
unit_dir=Path.home()/'.config/systemd/user' if user else Path('/etc/systemd/system')
jobs=[('pc','collect_activitywatch.py','',config['schedule']['pc_seconds'])] if user else [
    ('ingest','interface.py',' ingest',config['schedule']['ingest_seconds']),
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
if args.install:
    command=['systemctl']+(['--user'] if user else [])
    subprocess.run(command+['daemon-reload'],check=True)
    subprocess.run(command+['enable','--now']+units,check=True)
    print('Installed: '+', '.join(units))
