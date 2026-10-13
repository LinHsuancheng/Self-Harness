"""Receive files, classify by type, gzip and save. No content parsing."""
import gzip
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

config_path = Path(os.environ.get('SELF_HARNESS_CONFIG', 'config.json')).resolve()
config = json.loads(config_path.read_text())
root = (config_path.parent / config['data_dir']).resolve()
app = FastAPI()


@app.get('/')
def health():
    return {'status': 'ok'}


@app.post('/upload')
async def upload(type: str = Form(...), file: UploadFile = File(...)):
    folder = config['folders'].get(type)
    if folder is None:
        raise HTTPException(400, 'Unknown upload type')
    content = await file.read(config['max_upload_bytes'] + 1)
    await file.close()
    if len(content) > config['max_upload_bytes']:
        raise HTTPException(413, 'File too large')
    filename = (file.filename or 'unnamed').strip().replace('\\', '/').split('/')[-1] or 'unnamed'
    if len(filename.encode()) > 180:
        raise HTTPException(400, 'Filename too long')
    now = datetime.now(ZoneInfo(config['timezone']))
    directory = root / folder / now.strftime('%Y-%m-%d')
    directory.mkdir(parents=True, exist_ok=True)
    name = now.strftime('%H%M%S-%f-') + uuid.uuid4().hex[:8] + '-' + filename
    is_gzip = content.startswith(b'\x1f\x8b')
    if not name.endswith('.gz'):
        name += '.gz'
    path = directory / name
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_bytes(content if is_gzip else gzip.compress(content, mtime=0))
    temporary.replace(path)
    return {'status': 'success', 'type': type, 'file': path.relative_to(root).as_posix(),
            'uploaded_bytes': len(content), 'stored_bytes': path.stat().st_size}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host=config['listen']['host'], port=config['listen']['port'])
