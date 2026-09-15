"""Durable local jobs; source presence never grants permission to upload it."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import uuid


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


class WorkerLock:
    def __init__(self, path):
        self.path, self.stream = Path(path), None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open('a+b')
        if stream.seek(0, 2) == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise RuntimeError('분석기가 이미 실행 중입니다.') from exc
        self.stream = stream

    def close(self):
        if self.stream:
            self.stream.close(); self.stream = None


class FileStability:
    def __init__(self, seconds=10):
        self.seconds, self.signature, self.since = seconds, None, 0

    def ready(self, paths, now):
        signature = tuple(sorted((str(p.resolve()), p.stat().st_size, p.stat().st_mtime_ns) for p in paths))
        if signature != self.signature:
            self.signature, self.since = signature, now
        return bool(signature) and now - self.since >= self.seconds


class JobQueue:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db = self.root / 'jobs.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS checkpoints (job TEXT, stage TEXT, path TEXT, sha TEXT, PRIMARY KEY(job,stage))')

    def connect(self):
        return sqlite3.connect(self.db, timeout=15)

    def list(self):
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute('SELECT data FROM jobs ORDER BY rowid')]

    def get(self, job_id):
        with self.connect() as db:
            row = db.execute('SELECT data FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            raise ValueError('작업을 찾을 수 없습니다.')
        return json.loads(row[0])

    def enqueue(self, main, supplements, report_id=None):
        if report_id is not None and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', report_id):
            raise ValueError('안전하지 않은 보고서 식별자입니다.')
        paths = [Path(main).resolve(), *[Path(p).resolve() for p in supplements]]
        if any(not p.is_file() or p.suffix.lower() != '.pdf' or not 0 < p.stat().st_size <= 512 * 1024 * 1024 for p in paths):
            raise ValueError('512 MiB 이하의 비어 있지 않은 PDF 파일이 필요합니다.')
        hashes = [digest(p) for p in paths]
        if len(set(hashes)) != len(hashes):
            raise ValueError('동일한 PDF가 중복되거나 본문·서플 역할이 충돌합니다.')
        fingerprint = hashlib.sha256(json.dumps([hashes[0], sorted(hashes[1:])]).encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT data FROM jobs WHERE fingerprint=?', (fingerprint,)).fetchone()
            if previous:
                return json.loads(previous[0])
            job_id = uuid.uuid4().hex
            folder = self.root / 'jobs' / job_id
            if not folder.resolve().is_relative_to(self.root):
                raise ValueError('작업 저장 위치가 외부 폴더로 연결되어 있습니다.')
            folder.mkdir(parents=True)
            try:
                copies = []
                for i, (source, sha) in enumerate(zip(paths, hashes)):
                    target = folder / ('main.pdf' if i == 0 else f'supplement-{i}.pdf')
                    shutil.copyfile(source, target)
                    if digest(target) != sha or digest(source) != sha:
                        raise ValueError('복사 도중 원본이 변경되었습니다.')
                    copies.append(str(target))
                data = dict(id=job_id, fingerprint=fingerprint, folder=str(folder), main=copies[0],
                            supplements=copies[1:], source_hashes=hashes, source_names=[p.name for p in paths],
                            report_id=report_id or 'P' + fingerprint[:16], state='queued', stage='queued',
                            attempts=0, allow_model_upload=False, message='자료 추출 대기')
                db.execute('INSERT INTO jobs VALUES (?,?,?)', (job_id, fingerprint, json.dumps(data, ensure_ascii=False)))
            except Exception:
                # This newly allocated job directory is owned by this failed transaction.
                if folder.resolve().is_relative_to(self.root / 'jobs'):
                    shutil.rmtree(folder)
                raise
        return data

    def update(self, job_id, **values):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT data FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:
                raise ValueError('작업을 찾을 수 없습니다.')
            data = json.loads(row[0]); data.update(values)
            db.execute('UPDATE jobs SET data=? WHERE id=?', (json.dumps(data, ensure_ascii=False), job_id))
        return data

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            for row in db.execute('SELECT data FROM jobs ORDER BY rowid').fetchall():
                data = json.loads(row[0])
                if data['state'] == 'queued':
                    data.update(state='running', attempts=data['attempts'] + 1)
                    db.execute('UPDATE jobs SET data=? WHERE id=?', (json.dumps(data, ensure_ascii=False), data['id']))
                    return data
        return None

    def recover_interrupted(self):
        count = 0
        for data in self.list():
            if data['state'] == 'running':
                self.update(data['id'], state='interrupted', stage='waiting', message='중단된 작업 · 다시 시도하면 검증된 단계부터 이어갑니다.')
                count += 1
        return count

    def retry(self, job_id):
        if self.get(job_id)['state'] not in ('failed', 'interrupted', 'prepared', 'waiting', 'review'):
            raise ValueError('현재 상태에서는 다시 시도할 수 없습니다.')
        return self.update(job_id, state='queued', stage='queued', message='재시도 대기')

    def authorize(self, job_id):
        # Only explicit user consent from a trusted controller may call this method.
        return self.update(job_id, allow_model_upload=True)

    def checkpoint(self, job_id, stage, artifact):
        artifact = Path(artifact).resolve()
        if not artifact.is_relative_to(Path(self.get(job_id)['folder']).resolve()):
            raise ValueError('작업 폴더 밖의 결과는 저장할 수 없습니다.')
        with self.connect() as db:
            db.execute('INSERT OR REPLACE INTO checkpoints VALUES (?,?,?,?)', (job_id, stage, str(artifact), digest(artifact)))

    def completed(self, job_id, stage):
        with self.connect() as db:
            row = db.execute('SELECT path,sha FROM checkpoints WHERE job=? AND stage=?', (job_id, stage)).fetchone()
        if row is None:
            return None
        path = Path(row[0])
        if not path.resolve().is_relative_to(Path(self.get(job_id)['folder']).resolve()) or not path.is_file() or digest(path) != row[1]:
            raise ValueError('저장된 중간 결과가 변경되었거나 없어 재사용할 수 없습니다.')
        return path
