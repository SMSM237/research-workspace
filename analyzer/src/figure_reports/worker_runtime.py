"""One Windows worker: honest heartbeat, durable intake, verified checkpoints.

Approved jobs can use Codex with ChatGPT subscription login for source-grounded
Figure findings. Final report integration and publication remain separate.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
import time
import uuid
from .intake import ingest_bundle
from .worker_queue import JobQueue, WorkerLock, FileStability, digest


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.resolve().is_relative_to(path.parent.resolve()):
        raise ValueError('외부로 연결된 상태 파일입니다.')
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.flush(); os.fsync(stream.fileno())
        # Windows readers/antivirus can briefly hold a destination without delete sharing.
        for attempt in range(20):
            try:
                os.replace(temp, path)
                break
            except PermissionError:
                if attempt == 19:
                    raise
                time.sleep(.025)
    finally:
        temp.unlink(missing_ok=True)


class LocalWorker:
    def __init__(self, vault, state, interval=5, stable_seconds=10, model_executable=None, analysis_model='gpt-5.6-sol', auto_publish=False):
        self.vault, self.state = Path(vault).resolve(), Path(state).resolve()
        if not self.vault.is_dir():
            raise ValueError('Vault 폴더가 없습니다.')
        self.control = self.vault / '.figure-reports'
        self.control.mkdir(exist_ok=True)
        if not self.control.resolve().is_relative_to(self.vault):
            raise ValueError('Vault 외부로 연결된 제어 폴더입니다.')
        self.queue = JobQueue(self.state)
        # Lock belongs to the Vault: two state directories cannot share one UI heartbeat.
        self.lock = WorkerLock(self.control / 'worker.lock')
        self.stop = threading.Event()
        self.interval, self.stable_seconds = interval, stable_seconds
        self.model_executable = model_executable
        self.analysis_model = analysis_model
        self.auto_publish = auto_publish
        self._guard = threading.Lock()
        self.status = dict(stage='waiting', message='Inbox에서 자료를 기다리고 있습니다.')
        self.stability, self.seen = {}, {}
        self.inbox_pending = 0
        self.inbox_errors = []

    def set_status(self, **fields):
        active=next((j for j in self.queue.list() if j['state']=='running'),None)
        if active and fields.get('message'):
            title=(active.get('source_names') or [active['report_id']])[0]
            if not fields['message'].startswith(title[:70]):fields['message']=title[:70]+' · '+fields['message']
        with self._guard:
            self.status = fields
        self.heartbeat()

    def heartbeat(self, connection='connected'):
        with self._guard:
            record = dict(self.status)
            record.update(version=1, connection=connection, updated_at=datetime.now(timezone.utc).isoformat(), pid=os.getpid())
            atomic_json(self.control / 'worker-status.json', record)
            jobs = self.queue.list()
            atomic_json(self.control / 'queue-status.json', dict(version=1, jobs=[{**{k:j.get(k) for k in ('id','report_id','state','stage','message','attempts')},'source_name':(j.get('source_names') or [''])[0]} for j in jobs]))
            # Portable stage snapshots contain no machine paths, PID, error text or
            # commands. Update only on a stage/count/job-state change, not each pulse.
            portable={k:v for k,v in record.items() if k in ('stage','figures_done','figures_total','supplements_done','supplements_total')}
            portable.update(version=1,transport='git_snapshot',jobs=[{k:j.get(k) for k in ('id','report_id','state','stage')} for j in jobs][-2000:])
            shared=self.control/'shared-status.json'
            try:
                previous=json.loads(shared.read_text(encoding='utf-8'))
                if isinstance(previous,dict):previous.pop('updated_at',None)
                else:previous=None
            except (OSError,ValueError):previous=None
            if portable!=previous:
                atomic_json(shared,{**portable,'updated_at':record['updated_at']})

    def _pulse(self):
        while not self.stop.wait(self.interval):
            if (self.control / 'stop-request.json').exists():
                self.stop.set()
                break
            try:
                self.heartbeat()
            except OSError:
                self.stop.set()
                break

    def scan_inbox(self, now=None):
        now = time.monotonic() if now is None else now
        self.inbox_pending, self.inbox_errors = 0, []
        inbox = self.vault / 'Inbox'
        if not inbox.exists():
            return []
        if not inbox.resolve().is_relative_to(self.vault):
            raise ValueError('Inbox가 Vault 외부로 연결되어 있습니다.')
        added = []
        known = {job['id'] for job in self.queue.list()}
        for folder in sorted(inbox.iterdir()):
            if folder.is_file() and folder.suffix.lower() == '.pdf':
                if not folder.resolve().is_relative_to(inbox.resolve()):
                    continue
                tracker = self.stability.setdefault(str(folder), FileStability(self.stable_seconds))
                try:
                    if not tracker.ready([folder], now):
                        self.inbox_pending += 1
                        continue
                    if self.seen.get(str(folder)) == tracker.signature:
                        continue
                    self.set_status(stage='queued', message=f'PDF 접수 확인 중 · {folder.name}')
                    job = self.queue.enqueue(folder, [])
                    self.seen[str(folder)] = tracker.signature
                    if job['id'] not in known:
                        added.append(job)
                        known.add(job['id'])
                except (ValueError, OSError) as exc:
                    self.inbox_errors.append(f'{folder.name}: {exc}')
                continue
            if not folder.is_dir() or not (folder / 'READY').is_file():
                continue
            if not folder.resolve().is_relative_to(inbox.resolve()):
                continue
            paths = sorted(folder.glob('*.pdf'))
            main = folder / 'main.pdf'
            if not main.is_file() or any(p != main and not p.name.startswith('supplement') for p in paths):
                self.set_status(stage='waiting', message=f'{folder.name}: main.pdf와 supplement 이름의 PDF를 확인해 주세요.')
                continue
            if any(not p.resolve().is_relative_to(folder.resolve()) for p in paths):
                continue
            tracker = self.stability.setdefault(str(folder), FileStability(self.stable_seconds))
            try:
                if not tracker.ready(paths + [folder / 'READY'], now):
                    self.inbox_pending += 1
                    continue
            except OSError:
                # Copying, renaming or removing an Inbox file is a normal transient state.
                self.set_status(stage='waiting', message=f'{folder.name}: 파일 복사가 끝나기를 기다립니다.')
                continue
            if self.seen.get(str(folder)) == tracker.signature:
                continue
            try:
                job = self.queue.enqueue(main, [p for p in paths if p != main])
                if job['id'] not in known:
                    added.append(job)
                    known.add(job['id'])
                self.seen[str(folder)] = tracker.signature
            except (ValueError, OSError) as exc:
                self.set_status(stage='failed', message=f'{folder.name}: {exc}')
        return added

    def idle_status(self):
        jobs = self.queue.list()
        prepared = sum(j['state']=='prepared' for j in jobs)
        failed = sum(j['state'] in ('failed','interrupted') for j in jobs)
        review = sum(j['state']=='review' for j in jobs)
        if self.inbox_pending:
            self.set_status(stage='waiting', message=f'새 PDF {self.inbox_pending}건 · 복사가 끝나는지 확인 중')
        elif self.inbox_errors:
            self.set_status(stage='failed', message=self.inbox_errors[0][:300])
        elif prepared:
            self.set_status(stage='prepared', message=f'자료 준비 {prepared}건 · AI 분석 실행 전 확인 대기'+(f' · 오류/중단 {failed}건' if failed else ''))
        elif review:
            self.set_status(stage='review', message=f'Figure 분석 결과 {review}건 · 통합 리포트 검토 대기')
        elif failed:
            self.set_status(stage='failed', message=f'오류/중단 {failed}건 · 작업 내역에서 원인을 확인해 주세요.')
        else:
            self.set_status(stage='waiting', message='Inbox에 PDF를 넣으면 자동 접수합니다. 새 자료를 기다리고 있습니다.')

    def prepare(self, job):
        job_id = job['id']
        self.queue.update(job_id, stage='parsing', message='PDF 자료 추출 중')
        label = (job.get('source_names') or [job['report_id']])[0]
        self.set_status(stage='parsing', message=f"{label} · 본문과 서플을 준비하고 있습니다.")
        paths = [Path(job['main']), *map(Path, job['supplements'])]
        if [digest(p) for p in paths] != job['source_hashes']:
            raise ValueError('보관 입력의 식별값이 달라졌습니다. 원본을 확인해 주세요.')
        checkpoint = self.queue.completed(job_id, 'parsing')
        if checkpoint:
            saved = json.loads(checkpoint.read_text(encoding='utf-8'))
            bundle = Path(saved['bundle']).resolve()
            if not bundle.is_relative_to(Path(job['folder']).resolve()):
                raise ValueError('중간 결과의 경로가 작업 폴더를 벗어났습니다.')
            for relative, sha in saved['files'].items():
                path = (bundle / relative).resolve()
                if not path.is_relative_to(bundle) or not path.is_file() or digest(path) != sha:
                    raise ValueError('추출된 자료가 변경되어 중간 결과를 재사용할 수 없습니다.')
            result = json.loads((bundle / 'inventory.json').read_text(encoding='utf-8'))
        else:
            # Each attempt has a fresh destination; never delete or adopt an unverified crash remnant.
            out = Path(job['folder']) / ('attempt-' + uuid.uuid4().hex)
            def progress(doc_id, page, total):
                if self.stop.is_set():
                    raise InterruptedError('사용자가 분석기를 중지했습니다.')
                self.set_status(stage='parsing', message=f"{label} · {doc_id} {page}/{total}쪽 추출")
            result = ingest_bundle(paths[0], paths[1:], out, job['report_id'], on_page=progress)
            bundle = out / job['report_id']
            saved = dict(bundle=str(bundle), files={p.relative_to(bundle).as_posix():digest(p) for p in bundle.rglob('*') if p.is_file()})
            checkpoint = Path(job['folder']) / 'parsing-checkpoint.json'
            atomic_json(checkpoint, saved)
            self.queue.checkpoint(job_id, 'parsing', checkpoint)
        pages = sum(d['page_count'] for d in result['documents'])
        message = f'{pages}쪽 자료 준비 완료 · 시각·과학 분석은 아직 시작하지 않았습니다.'
        self.queue.update(job_id, state='prepared', stage='prepared', bundle=str(bundle), pages=pages, message=message)
        self.set_status(stage='prepared', message=f"{job['report_id']} · {message}")
        return result

    def tick(self):
        self.scan_inbox()
        command_dir = self.control / 'commands'
        if command_dir.exists():
            if not command_dir.resolve().is_relative_to(self.control.resolve()):
                raise ValueError('명령 폴더 경로가 잘못되었습니다.')
            for path in command_dir.glob('*.json'):
                try:
                    if path.stat().st_size > 2000:
                        raise ValueError('명령이 너무 큽니다.')
                    command = json.loads(path.read_text(encoding='utf-8'))
                    if command.get('action') != 'retry':
                        raise ValueError('지원하지 않는 명령입니다.')
                    self.queue.retry(command['job_id'])
                except (ValueError, KeyError, OSError) as exc:
                    self.set_status(stage='failed', message=f'재시도 요청을 처리하지 못했습니다: {exc}')
                finally:
                    path.unlink(missing_ok=True)
        if self.stop.is_set():
            return
        hold=self.state/'analysis-hold.json'
        if hold.exists():
            value=json.loads(hold.read_text('utf-8'))
            self.set_status(stage='waiting',message=str(value.get('message','분석 방식 확인 대기'))[:250])
            return
        if self.auto_publish and self.model_executable:
            # Explicit local controller policy, never inferred from PDF instructions.
            for pending in self.queue.list():
                if pending['state']=='failed' and pending.get('retry_at',0)>0 and pending['retry_at']<=time.time():
                    self.queue.retry(pending['id']);self.queue.update(pending['id'],retry_at=0)
                    pending=self.queue.get(pending['id'])
                if pending['state'] in ('queued','prepared','review','interrupted'):
                    consent=dict(destination='codex-openai-chatgpt',auth_method='chatgpt',user_approved=True,
                        policy='user-authorized automatic Inbox analysis and publication',fingerprint=pending['fingerprint'],source_hashes=pending['source_hashes'])
                    atomic_json(Path(pending['folder'])/'consent.json',consent)
                    self.queue.authorize(pending['id'])
                    if pending['state']!='queued':self.queue.retry(pending['id']);self.queue.update(pending['id'],message='자동 분석 대기')
        pause_path=self.state/'subscription-pause.json'
        if pause_path.exists():
            pause=json.loads(pause_path.read_text('utf-8'))
            if time.time()<pause.get('retry_at',0):
                when=datetime.fromtimestamp(pause['retry_at']).strftime('%m월 %d일 %H:%M')
                label={'auth':'구독 로그인 확인 대기','capacity':'모델 서버 혼잡 대기'}.get(pause.get('reason'),'구독 한도 대기')
                self.set_status(stage='waiting',message=label+' · '+when+' 자동 재확인 · 기존 결과와 대기열 보존')
                return
            if pause.get('reason')=='auth':
                from .model_adapter import CodexSubscription,SubscriptionAuthError
                try:CodexSubscription(self.model_executable,model=self.analysis_model).authenticate()
                except (SubscriptionAuthError,OSError,TimeoutError):
                    atomic_json(pause_path,dict(retry_at=time.time()+60,reason='auth',auth_method='chatgpt'))
                    self.set_status(stage='waiting',message='구독 로그인 확인 대기 · 1분 뒤 재확인 · 대기열 보존')
                    return
            pause_path.unlink()
        job = self.queue.claim()
        if job:
            try:
                self.prepare(job)
                job = self.queue.get(job['id'])
                if self.model_executable and job['allow_model_upload']:
                    from .analysis_pipeline import FigurePipeline
                    from .model_adapter import CodexSubscription
                    self.queue.update(job['id'],state='running',stage='figure_analysis')
                    FigurePipeline(self,CodexSubscription(self.model_executable,model=self.analysis_model,timeout=1200)).run(job)
            except InterruptedError:
                self.queue.update(job['id'], state='interrupted', stage='waiting', message='중지됨 · 재시도 가능')
            except Exception as exc:
                from .model_adapter import SubscriptionLimitError,SubscriptionAuthError,ProviderCapacityError
                if isinstance(exc,(SubscriptionAuthError,ProviderCapacityError)):
                    reason='auth' if isinstance(exc,SubscriptionAuthError) else 'capacity'
                    atomic_json(self.state/'subscription-pause.json',dict(retry_at=time.time()+(60 if reason=='auth' else 300),reason=reason,auth_method='chatgpt'))
                    self.queue.update(job['id'],state='queued',stage='waiting',message=str(exc),retry_at=0)
                    self.set_status(stage='waiting',message=str(exc))
                    return
                if isinstance(exc,SubscriptionLimitError):
                    retry_at=time.time()+900
                    policy=self.state/'subscription-limit-policy.json'
                    if policy.exists() and exc.account_window:
                        known=json.loads(policy.read_text('utf-8')).get('known_reset_at',0)
                        if time.time()<known<time.time()+8*86400:retry_at=known+60
                    atomic_json(self.state/'subscription-pause.json',dict(retry_at=retry_at,reason='subscription_limit',auth_method='chatgpt'))
                    self.queue.update(job['id'],state='queued',stage='waiting',message=str(exc))
                    self.set_status(stage='waiting',message=str(exc))
                    return
                self.queue.update(job['id'], state='failed', stage='failed', message=str(exc)[:300])
                self.set_status(stage='failed', message=str(exc)[:300])
                import traceback
                atomic_json(Path(job['folder'])/'last-error.json',dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
                # Only transient provider/time-out errors retry. Unsupported claims,
                # local edits and authentication failures never become blind retries.
                retries=job.get('model_retries',0)
                if self.auto_publish and isinstance(exc,(TimeoutError,RuntimeError)) and retries<2:
                    self.queue.update(job['id'],model_retries=retries+1,retry_at=time.time()+60*(2**retries),message=str(exc)[:220]+' · 자동 재시도 예정')
        else:
            self.idle_status()

    def run(self):
        self.lock.acquire()
        pulse = None
        try:
            (self.control / 'stop-request.json').unlink(missing_ok=True)
            self.queue.recover_interrupted()
            last = self.queue.list()
            if last:
                self.status = dict(stage=last[-1]['stage'], message=last[-1]['message'])
            self.heartbeat('connecting')
            pulse = threading.Thread(target=self._pulse, daemon=True)
            pulse.start()
            self.heartbeat()
            while not self.stop.is_set():
                self.tick()
                self.stop.wait(1)
        finally:
            self.stop.set()
            if pulse:
                pulse.join(timeout=self.interval + 1)
            try:
                self.heartbeat('disconnected')
            finally:
                self.lock.close()
