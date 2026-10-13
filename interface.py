"""CLI for independent acquisition, ingestion and material queries."""
import argparse
import json
import sys
from pathlib import Path

from interfaces import fetcher, operator


def load_config(filename):
    path = Path(filename).resolve()
    config = json.loads(path.read_text())
    config['raw_dir'] = str((path.parent / config.get('raw_dir',config.get('data_dir','raw'))).resolve())
    config['database_dir'] = str((path.parent / config['database_dir']).resolve())
    for settings in config['sources'].values():
        for key in ('raw_dir','cache_file'):
            if key in settings:
                settings[key] = str((path.parent / settings[key]).resolve())
    return config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',default='config.json')
    commands = parser.add_subparsers(dest='command',required=True)
    fetch = commands.add_parser('fetch'); fetch.add_argument('source',choices=['todo','pc_screen_time']); fetch.add_argument('--login',action='store_true')
    ingest = commands.add_parser('ingest'); ingest.add_argument('source',nargs='?',default='all'); ingest.add_argument('--retry-failed',action='store_true')
    stat = commands.add_parser('status'); stat.add_argument('source',nargs='?',default='all')
    for name in ('query','summarize','latest-before'):
        command=commands.add_parser(name); command.add_argument('source')
        if name in ('query','summarize'):
            command.add_argument('--start',required=True); command.add_argument('--end',required=True)
        else:
            command.add_argument('--time',required=True)
    for name in ('context','todo-changes','pc-active-time'):
        command=commands.add_parser(name); command.add_argument('--start',required=True); command.add_argument('--end',required=True)
    args = parser.parse_args(); config=load_config(args.config)
    failed=False
    if args.command=='fetch':
        output={'raw':str(fetcher.todo(config,args.login) if args.source=='todo' else fetcher.activitywatch(config))}
    elif args.command in ('ingest','status'):
        sources=config['sources'] if args.source=='all' else [args.source]
        output={}
        for source in sources:
            try:
                output[source]=operator.ingest(config,source,args.retry_failed) if args.command=='ingest' else operator.status(config,source)
                failed=failed or bool(output[source].get('failed',0))
            except Exception as exc:
                output[source]={'error':str(exc)}; failed=True
    elif args.command in ('query','summarize'):
        operation=operator.query if args.command=='query' else operator.summarize
        output=operation(config,args.source,args.start,args.end)
    elif args.command=='latest-before':
        output=operator.latest_before(config,args.source,args.time)
    else:
        operation={'context':operator.context,'todo-changes':operator.todo_changes,'pc-active-time':operator.pc_active_time}[args.command]
        output=operation(config,args.start,args.end)
    print(json.dumps(output,ensure_ascii=False,indent=2))
    return 1 if failed else 0


if __name__=='__main__':
    sys.exit(main())
