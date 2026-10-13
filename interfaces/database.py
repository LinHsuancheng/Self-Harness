"""One SQLite file per source; retain revisions and raw processing results."""
import json
import sqlite3
from pathlib import Path
from .parser import utc


class Database:
    def __init__(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY, content_hash TEXT, parser_version TEXT,
                collected_at TEXT NOT NULL, status TEXT NOT NULL, error TEXT
            );
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY, record_key TEXT NOT NULL, version_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
                observed_at TEXT NOT NULL, end_at TEXT, collected_at TEXT NOT NULL,
                data TEXT NOT NULL, raw_path TEXT NOT NULL REFERENCES files(path),
                parser_version TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS material_key ON materials(record_key, version_at DESC, id DESC);
            CREATE INDEX IF NOT EXISTS material_time ON materials(observed_at);
        ''')

        columns = {r['name'] for r in self.conn.execute('PRAGMA table_info(materials)')}
        if 'last_seen_at' not in columns:
            self.conn.execute("ALTER TABLE materials ADD COLUMN last_seen_at TEXT NOT NULL DEFAULT ''")
            self.conn.execute('UPDATE materials SET last_seen_at=version_at')
            self.conn.commit()

    def close(self):
        self.conn.close()

    def file(self, path):
        return self.conn.execute('SELECT * FROM files WHERE path=?', (path,)).fetchone()

    def seen_content(self, content_hash, version):
        # Only skip consecutive identical captures: A -> B -> A may be a real correction.
        previous = self.conn.execute("SELECT content_hash,parser_version FROM files WHERE status!='failed' ORDER BY collected_at DESC,rowid DESC LIMIT 1").fetchone()
        return bool(previous and previous['content_hash'] == content_hash and previous['parser_version'] == version)

    def save(self, path, content_hash, version, collected, records, error=None, duplicate=False):
        state = 'failed' if error else ('duplicate' if duplicate else 'success')
        with self.conn:
            self.conn.execute('''INSERT INTO files VALUES (?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET
                content_hash=excluded.content_hash, parser_version=excluded.parser_version,
                collected_at=excluded.collected_at, status=excluded.status, error=excluded.error''',
                (path, content_hash, version, collected, state, error))
            if not error:
                self.conn.execute('DELETE FROM materials WHERE raw_path=? AND parser_version!=?', (path, version))
            for row in records:
                data = json.dumps(row['data'], ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
                # Compare with the revision at this observation time, including out-of-order snapshots.
                previous = self.conn.execute('''SELECT * FROM materials WHERE record_key=? AND version_at<=?
                    ORDER BY version_at DESC,id DESC LIMIT 1''', (row['_key'], row['_version'])).fetchone()
                if previous and previous['data'] == data and previous['parser_version'] == version:
                    self.conn.execute('UPDATE materials SET last_seen_at=max(last_seen_at,?) WHERE id=?',
                                      (row['_version'], previous['id']))
                    continue
                self.conn.execute('''INSERT INTO materials
                    (record_key,version_at,last_seen_at,observed_at,end_at,collected_at,data,raw_path,parser_version)
                    VALUES (?,?,?,?,?,?,?,?,?)''', (row['_key'], row['_version'], row['_version'], row['observed_at'], row['_end'],
                                               row['collected_at'], data, path, version))

    def rows(self, start=None, end=None, before=None):
        sql = '''WITH latest AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY record_key ORDER BY last_seen_at DESC,id DESC) AS n
            FROM materials
        ) SELECT * FROM latest WHERE n=1'''
        params = []
        if start is not None:
            sql += ' AND ((end_at IS NULL AND observed_at>=?) OR (end_at IS NOT NULL AND end_at>observed_at AND end_at>?))'
            params.extend([utc(start), utc(start)])
        if end is not None:
            sql += ' AND observed_at<?'
            params.append(utc(end))
        if before is not None:
            sql += ' AND observed_at<?'
            params.append(utc(before))
        sql += ' ORDER BY observed_at,id'
        return self.conn.execute(sql, params).fetchall()

    def status(self):
        counts = {r['status']:r['n'] for r in self.conn.execute('SELECT status,count(*) AS n FROM files GROUP BY status')}
        return {'processed_files': sum(counts.values()), 'successful_files': counts.get('success',0),
                'duplicate_files': counts.get('duplicate',0), 'failed_files': counts.get('failed',0),
                'last_collected_at': self.conn.execute('SELECT max(collected_at) FROM files').fetchone()[0],
                'last_observed_at': self.conn.execute('SELECT max(observed_at) FROM materials').fetchone()[0],
                'revisions': self.conn.execute('SELECT count(*) FROM materials').fetchone()[0],
                'errors': [dict(r) for r in self.conn.execute("SELECT path,error FROM files WHERE status='failed'")]}
