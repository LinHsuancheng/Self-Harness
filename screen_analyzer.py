"""Destructive screenshot analyzer: image -> validated JSON raw material."""
import argparse
import base64
import fcntl
import gzip
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import openai
from dotenv import load_dotenv
from openai import OpenAI

from interface import load_config
from interfaces import fetcher, parser, periods, screen

ROOT = Path(__file__).resolve().parent
FATAL = (openai.AuthenticationError, openai.PermissionDeniedError, openai.BadRequestError,
         openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError,
         openai.InternalServerError, openai.NotFoundError)


def emit(event, **fields):
    print(json.dumps({'event': event, **fields}, ensure_ascii=False), flush=True)


def read_metadata(path):
    meta_path = path.with_name(path.name+'.meta.json')
    try:
        value = json.loads(meta_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def capture_time(metadata, path, zone):
    value = metadata.get('observed_at') or metadata.get('collected_at')
    if isinstance(value, str):
        try:
            return parser.utc(value)
        except (ValueError, TypeError):
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def image_kind(content):
    if content.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if content.startswith(b'RIFF') and content[8:12] == b'WEBP':
        return 'webp'
    return None


def attempt_path(path):
    return path.with_name(path.name+'.attempts')


def read_attempts(path):
    try:
        return int(attempt_path(path).read_text().strip())
    except (OSError, ValueError):
        return 0


def write_attempts(path, count):
    attempt_path(path).write_text(str(count), encoding='utf-8')


def append_failure_log(directory, record):
    with (directory/'failed.jsonl').open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(record, ensure_ascii=False)+'\n')


def retire(path):
    """Delete the capture; if deletion fails, rename so it is not analyzed twice."""
    for candidate in (path, path.with_name(path.name+'.meta.json'), attempt_path(path)):
        try:
            candidate.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            try:
                os.replace(candidate, candidate.with_name(candidate.name+'.done'))
            except OSError:
                pass


def analyze(client, model, prompt, content, kind, detail, max_tokens):
    data_url = f'data:image/{kind};base64,' + base64.b64encode(content).decode()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': [
                {'type': 'text', 'text': '分析这张截图，输出 json。'},
                {'type': 'image_url', 'image_url': {'url': data_url, 'detail': detail}},
            ]},
        ],
        response_format={'type': 'json_object'},
        max_tokens=max_tokens,
    )
    text = response.choices[0].message.content
    if not text or not text.strip():
        raise ValueError('Empty model output')
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
    return screen.validate(json.loads(text))


def mark_failure(path, capture_dir, maximum_attempts, counts, error):
    count = read_attempts(path)+1
    if count >= maximum_attempts:
        append_failure_log(capture_dir, {'time': datetime.now(timezone.utc).isoformat(),
                                         'file': path.name, 'attempts': count,
                                         'error': error[:200]})
        retire(path)
        counts['discarded'] += 1
        emit('discarded', file=path.name, attempts=count)
    else:
        write_attempts(path, count)
        counts['failed'] += 1
        emit('retry', file=path.name, attempts=count)


def write_output(raw_dir, captured, sha, envelope, zone, now):
    local = periods.local(captured, zone)
    directory = raw_dir / local.strftime('%Y-%m-%d')
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{local.strftime('%Y%m%dT%H%M%S')}-{sha[:8]}.json.gz"
    path = directory / name
    content = json.dumps(envelope, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    compressed = gzip.compress(content, mtime=0)
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('wb') as handle:
        handle.write(compressed)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    try:
        descriptor = os.open(directory, os.O_RDONLY)
        os.fsync(descriptor)
        os.close(descriptor)
    except OSError:
        pass
    metadata = {'type': 'pc_screen_activity', 'filename': name,
                'collected_at': now, 'observed_at': captured}
    meta_path = path.with_name(path.name+'.meta.json')
    meta_temporary = meta_path.with_name(meta_path.name+'.tmp')
    with meta_temporary.open('w', encoding='utf-8') as handle:
        json.dump(metadata, handle, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(meta_temporary, meta_path)
    return path


def main():
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument('--config', default='config.json')
    argument_parser.add_argument('--max-batch', type=int)
    argument_parser.add_argument('--dry-run', action='store_true')
    args = argument_parser.parse_args()

    config = load_config(args.config)
    settings = config.get('sources', {}).get('pc_screen_activity')
    if not isinstance(settings, dict):
        emit('fatal', error='sources.pc_screen_activity is not configured')
        return 1
    zone = config.get('timezone', periods.DEFAULT_TIMEZONE)
    raw_dir = Path(settings.get('raw_dir', Path(config['raw_dir'])/'pc_screen_activity'))
    capture_dir = Path(settings.get('capture_dir', Path(config['raw_dir'])/'screen_capture'))
    analysis_settings = settings.get('analysis') or {}
    maximum_attempts = max(1, int(analysis_settings.get('max_attempts', 3)))
    batch_size = args.max_batch or int(analysis_settings.get('batch_size', 20))
    detail = analysis_settings.get('detail', 'high')
    max_tokens = int(analysis_settings.get('max_output_tokens', 600))
    minimum_age = float(analysis_settings.get('min_age_seconds', 5))

    lock_path = Path(config['database_dir'])/'screen_analyzer.lock'
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = lock_path.open('w')
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        emit('busy')
        return 0

    load_dotenv(ROOT/'.env')
    key = os.getenv('DEEPSEEK_API_KEY')
    if not key:
        emit('fatal', error='DEEPSEEK_API_KEY is missing')
        return 1
    client = OpenAI(api_key=key,
                    base_url=os.getenv('DEEPSEEK_BASE_URL') or 'https://api.deepseek.com',
                    timeout=60)
    model = analysis_settings.get('model') or os.getenv('DEEPSEEK_MODEL') or 'deepseek-flash'
    prompt = screen.PROMPT

    captures = []
    if capture_dir.exists():
        now_epoch = time.time()
        captures = sorted((path for path in capture_dir.rglob('*.gz')
                           if now_epoch-path.stat().st_mtime >= minimum_age),
                          key=lambda path: (path.stat().st_mtime_ns, str(path)))[:batch_size]
    counts = {'success': 0, 'failed': 0, 'discarded': 0, 'dry_run': 0}
    fatal = None
    for path in captures:
        metadata = read_metadata(path)
        try:
            captured = capture_time(metadata, path, zone)
            content = fetcher.read(path, config.get('max_uncompressed_bytes', 52428800))
        except (OSError, EOFError, ValueError) as exc:
            mark_failure(path, capture_dir, maximum_attempts, counts, str(exc))
            continue
        kind = image_kind(content)
        if kind is None:
            mark_failure(path, capture_dir, maximum_attempts, counts, 'unsupported image format')
            continue
        result = None
        last_error = None
        try:
            for _ in range(3):
                try:
                    result = analyze(client, model, prompt, content, kind, detail, max_tokens)
                    break
                except ValueError as exc:
                    last_error = exc
        except FATAL as exc:
            fatal = exc
            break
        except Exception as exc:
            fatal = exc
            break
        if result is None:
            mark_failure(path, capture_dir, maximum_attempts, counts,
                         type(last_error).__name__ if last_error else 'invalid analysis')
            continue

        sha = metadata.get('sha256')
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
            sha = hashlib.sha256(content).hexdigest()
        size = metadata.get('bytes')
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            size = len(content)
        filename = metadata.get('filename')
        if not isinstance(filename, str):
            filename = path.name
        now = datetime.now(timezone.utc).isoformat()
        envelope = {
            'source': 'pc_screen_activity',
            'observed_at': captured,
            'collected_at': now,
            'data': {
                'captured_at': captured,
                'capture': {'id': captured+'|'+sha, 'sha256': sha, 'bytes': size,
                            'format': kind, 'filename': filename},
                'model': model,
                'prompt_version': screen.PROMPT_VERSION,
                'analysis': result,
            },
        }
        content_bytes = json.dumps(envelope, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        try:
            parser.parse('pc_screen_activity', content_bytes, now, settings)
        except Exception as exc:
            fatal = exc
            break
        if args.dry_run:
            counts['dry_run'] += 1
            emit('dry_run', file=path.name, captured_at=captured)
            continue
        try:
            write_output(raw_dir, captured, sha, envelope, zone, now)
        except OSError as exc:
            fatal = exc
            break
        retire(path)
        counts['success'] += 1
        emit('analyzed', file=path.name, captured_at=captured)

    emit('summary', pending=len(captures), **counts)
    if fatal is not None:
        message = str(fatal)
        if key:
            message = message.replace(key, '[REDACTED]')
        emit('fatal', error=message[:500])
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
