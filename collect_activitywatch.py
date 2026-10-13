"""Local ActivityWatch fetcher plus gzip upload to the collection center."""
import argparse
import json
from interface import load_config
from interfaces import fetcher

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',default='config.json')
    args=parser.parse_args()
    config=load_config(args.config)
    path=fetcher.activitywatch(config)
    receipt=fetcher.upload(config,'pc_screen_time',path)
    print(json.dumps({'raw':str(path),'gzip_bytes':path.stat().st_size,'upload':receipt},ensure_ascii=False))
