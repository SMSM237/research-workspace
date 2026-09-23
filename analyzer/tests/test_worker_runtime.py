import json
from pathlib import Path
import threading
import time
import pymupdf
import pytest
from figure_reports.worker_runtime import LocalWorker, atomic_json
from figure_reports.worker_queue import WorkerLock


def pdf(path, text='Synthetic test. Figure 1. A test figure. NEWGENE42.'):
    path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as doc:
        page=doc.new_page();page.insert_text((72,72),text);doc.save(path)
    return path


def worker(tmp_path):
    vault=tmp_path/'vault';vault.mkdir()
    return LocalWorker(vault,tmp_path/'state',interval=.03,stable_seconds=2)


def test_portable_status_changes_only_with_progress_and_omits_private_data(tmp_path):
    w=worker(tmp_path);job=w.queue.enqueue(pdf(tmp_path/'main.pdf'),[])
    w.set_status(stage='figure_analysis',figures_done=1,figures_total=7,message='PRIVATE PATH / token')
    path=w.control/'shared-status.json';first=path.read_bytes()
    record=json.loads(first)
    assert record['transport']=='git_snapshot' and record['figures_done']==1
    assert set(record)=={'version','transport','stage','figures_done','figures_total','jobs','updated_at'}
    assert set(record['jobs'][0])=={'id','report_id','state','stage'}
    assert record['jobs'][0]['id']==job['id']
    assert b'PRIVATE' not in first and b'pid' not in first
    w.heartbeat();assert path.read_bytes()==first
    w.set_status(stage='figure_analysis',figures_done=2,figures_total=7)
    assert json.loads(path.read_bytes())['figures_done']==2
    assert path.read_bytes()!=first
    before=path.read_bytes();w.heartbeat('disconnected');assert path.read_bytes()==before


@pytest.mark.parametrize('bad',['not-json','[]','null'])
def test_invalid_portable_status_is_repaired_without_stopping_worker(tmp_path,bad):
    w=worker(tmp_path);path=w.control/'shared-status.json';path.write_text(bad)
    w.heartbeat();assert json.loads(path.read_bytes())['stage']=='waiting'


def test_whole_inbox_bundle_waits_for_ready_and_stability(tmp_path):
    w=worker(tmp_path);folder=w.vault/'Inbox'/'paper'
    pdf(folder/'main.pdf');pdf(folder/'supplement.pdf','Synthetic supplemental text.')
    assert w.scan_inbox(0)==[]
    (folder/'READY').touch()
    assert w.scan_inbox(1)==[]
    jobs=w.scan_inbox(3);assert len(jobs)==1 and len(jobs[0]['supplements'])==1
    assert w.scan_inbox(5)==[] and len(w.queue.list())==1
    assert (folder/'main.pdf').exists() and (folder/'READY').exists()

def test_loose_pdfs_are_stable_queued_once_in_order_and_keep_originals(tmp_path):
    w=worker(tmp_path)
    paths=[pdf(w.vault/'Inbox'/'A paper.pdf','Paper A'),pdf(w.vault/'Inbox'/'B 논문.PDF','Paper B')]
    before={p:p.read_bytes() for p in paths}
    assert w.scan_inbox(0)==[]
    jobs=w.scan_inbox(2)
    assert len(jobs)==2
    assert [j['source_names'][0] for j in w.queue.list()]==[p.name for p in paths]
    assert all(not j['allow_model_upload'] for j in jobs)
    assert w.scan_inbox(4)==[]
    assert all(p.read_bytes()==content for p,content in before.items())
    duplicate=w.vault/'Inbox'/'duplicate.pdf';duplicate.write_bytes(paths[0].read_bytes())
    w.scan_inbox(5);assert w.scan_inbox(7)==[] and len(w.queue.list())==2
    restarted=LocalWorker(w.vault,w.state,stable_seconds=2)
    restarted.scan_inbox(0);assert restarted.scan_inbox(2)==[] and len(restarted.queue.list())==2

def test_changed_loose_pdf_waits_again_until_copy_stops(tmp_path):
    w=worker(tmp_path);path=pdf(w.vault/'Inbox'/'copy.pdf')
    assert w.scan_inbox(0)==[]
    path.write_bytes(path.read_bytes()+b'\n')
    assert w.scan_inbox(2)==[]
    assert len(w.scan_inbox(4))==1

def test_idle_status_distinguishes_prepared_jobs_from_old_completed_report(tmp_path):
    w=worker(tmp_path);old=w.queue.enqueue(pdf(tmp_path/'old.pdf','old'),[])
    w.queue.update(old['id'],state='complete',stage='complete',message='old complete')
    w.status=dict(stage='complete',message='old complete');w.tick()
    assert w.status['stage']=='waiting'
    job=w.queue.enqueue(pdf(tmp_path/'next.pdf','next'),[])
    w.queue.update(job['id'],state='prepared',stage='prepared');w.tick()
    assert w.status['stage']=='prepared' and '1건' in w.status['message'] and 'AI' in w.status['message']


def test_real_pdf_preparation_and_verified_resume(tmp_path):
    w=worker(tmp_path);job=w.queue.enqueue(pdf(tmp_path/'main.pdf'),[])
    w.tick();saved=w.queue.get(job['id'])
    assert saved['state']=='prepared' and saved['pages']==1
    inventory=Path(saved['bundle'])/'inventory.json'
    assert json.loads(inventory.read_text())['analysis_status']=='not_started'
    assert not (w.vault/'Paper reports').exists()
    w.queue.retry(job['id']);w.tick()
    assert w.queue.get(job['id'])['bundle']==saved['bundle']
    image=next(Path(saved['bundle']).rglob('*.png'));image.write_bytes(b'tampered')
    w.queue.retry(job['id']);w.tick()
    assert w.queue.get(job['id'])['state']=='failed'


def test_invalid_pdf_has_visible_error_and_valid_next_job_proceeds(tmp_path):
    w=worker(tmp_path);bad=tmp_path/'bad.pdf';bad.write_bytes(b'not a PDF')
    badjob=w.queue.enqueue(bad,[]);good=w.queue.enqueue(pdf(tmp_path/'good.pdf'),[])
    w.tick();assert w.queue.get(badjob['id'])['state']=='failed'
    assert json.loads((w.control/'worker-status.json').read_text(encoding='utf-8'))['stage']=='failed'
    w.tick();assert w.queue.get(good['id'])['state']=='prepared'


def test_actual_worker_heartbeat_stop_and_restart(tmp_path):
    w=worker(tmp_path)
    thread=threading.Thread(target=w.run);thread.start()
    status=w.control/'worker-status.json'
    deadline=time.monotonic()+3
    while time.monotonic()<deadline:
        if status.exists() and json.loads(status.read_text(encoding='utf-8'))['connection']=='connected':break
        time.sleep(.01)
    first=json.loads(status.read_text(encoding='utf-8'))
    time.sleep(.07)
    assert json.loads(status.read_text(encoding='utf-8'))['updated_at']!=first['updated_at']
    with pytest.raises(RuntimeError):WorkerLock(w.control/'worker.lock').acquire()
    atomic_json(w.control/'stop-request.json',{'action':'stop'})
    thread.join(3);assert not thread.is_alive()
    assert json.loads(status.read_text(encoding='utf-8'))['connection']=='disconnected'
    lock=WorkerLock(w.control/'worker.lock');lock.acquire();lock.close()


def test_retry_command_and_unknown_action_never_authorizes_upload(tmp_path):
    w=worker(tmp_path);job=w.queue.enqueue(pdf(tmp_path/'main.pdf'),[]);w.tick()
    atomic_json(w.control/'commands/retry.json',{'action':'retry','job_id':job['id']});w.tick()
    assert w.queue.get(job['id'])['attempts']==2
    atomic_json(w.control/'commands/bad.json',{'action':'authorize','job_id':job['id']});w.tick()
    assert not w.queue.get(job['id'])['allow_model_upload']


def test_changed_input_is_rejected_before_parsing(tmp_path):
    w=worker(tmp_path);job=w.queue.enqueue(pdf(tmp_path/'main.pdf'),[])
    Path(job['main']).write_bytes(b'changed');w.tick()
    assert w.queue.get(job['id'])['state']=='failed'


def test_interrupted_parse_is_retriable_without_claiming_completion(tmp_path):
    w=worker(tmp_path);job=w.queue.enqueue(pdf(tmp_path/'main.pdf'),[]);w.stop.set()
    with pytest.raises(InterruptedError):w.prepare(w.queue.claim())
    assert w.queue.completed(job['id'],'parsing') is None
    w.stop.clear();w.queue.recover_interrupted();w.queue.retry(job['id']);w.tick()
    assert w.queue.get(job['id'])['state']=='prepared'


def test_inbox_file_removed_during_scan_does_not_stop_worker(tmp_path,monkeypatch):
    from figure_reports.worker_queue import FileStability
    w=worker(tmp_path);folder=w.vault/'Inbox'/'paper';pdf(folder/'main.pdf');(folder/'READY').touch()
    with monkeypatch.context() as m:
        def vanished(*args):raise FileNotFoundError('file removed while scanning')
        m.setattr(FileStability,'ready',vanished)
        assert w.scan_inbox(0)==[] and not w.stop.is_set()
    assert w.scan_inbox(1)==[] and len(w.scan_inbox(3))==1

def test_transient_failure_retries_automatically_but_source_errors_do_not(tmp_path,monkeypatch):
    from figure_reports.analysis_pipeline import FigurePipeline
    w=worker(tmp_path);w.auto_publish=True;w.model_executable='test';j=w.queue.enqueue(pdf(tmp_path/'retry.pdf'),[])
    calls=[]
    def run(self,job):
        calls.append(job['id'])
        if len(calls)==1:raise TimeoutError('temporary provider timeout')
        w.queue.update(job['id'],state='complete',stage='complete')
    monkeypatch.setattr(FigurePipeline,'run',run);w.tick()
    assert w.queue.get(j['id'])['model_retries']==1
    w.tick();assert len(calls)==1
    w.queue.update(j['id'],retry_at=time.time()-1);w.tick()
    assert len(calls)==2 and w.queue.get(j['id'])['state']=='complete'
    other=w.queue.enqueue(pdf(tmp_path/'bad-source.pdf','Other source'),[])
    monkeypatch.setattr(FigurePipeline,'run',lambda *a:(_ for _ in ()).throw(ValueError('unsupported claim')))
    w.tick();assert not w.queue.get(other['id']).get('retry_at')

def test_subscription_limit_pauses_whole_queue_and_preserves_next_paper(tmp_path,monkeypatch):
    from figure_reports.analysis_pipeline import FigurePipeline
    from figure_reports.model_adapter import SubscriptionLimitError
    w=worker(tmp_path);w.auto_publish=True;w.model_executable='test';first=w.queue.enqueue(pdf(tmp_path/'first.pdf','first'),[]);second=w.queue.enqueue(pdf(tmp_path/'second.pdf','second'),[])
    calls=[]
    def run(self,job):calls.append(job['id']);raise SubscriptionLimitError('usage limit')
    monkeypatch.setattr(FigurePipeline,'run',run);w.tick();w.tick()
    assert calls==[first['id']]
    assert w.queue.get(first['id'])['state']=='queued' and w.queue.get(second['id'])['attempts']==0
    assert w.status['stage']=='waiting'
    atomic_json(w.state/'subscription-pause.json',dict(retry_at=time.time()-1));w.tick()
    assert calls==[first['id'],first['id']]


@pytest.mark.parametrize('kind',['auth','capacity'])
def test_provider_block_preserves_entire_queue_and_auth_probe_does_not_claim(tmp_path,monkeypatch,kind):
    from figure_reports.analysis_pipeline import FigurePipeline
    from figure_reports.model_adapter import SubscriptionAuthError,ProviderCapacityError,CodexSubscription
    w=worker(tmp_path);w.auto_publish=True;w.model_executable='test'
    first=w.queue.enqueue(pdf(tmp_path/'first.pdf','first'),[]);second=w.queue.enqueue(pdf(tmp_path/'second.pdf','second'),[])
    calls=[];error=SubscriptionAuthError('login unavailable') if kind=='auth' else ProviderCapacityError('model busy')
    def run(self,job):calls.append(job['id']);raise error
    monkeypatch.setattr(FigurePipeline,'run',run);w.tick();w.tick()
    assert calls==[first['id']]
    assert w.queue.get(first['id'])['state']=='queued'
    assert w.queue.get(second['id'])['attempts']==0
    assert w.status['stage']=='waiting'
    pause=json.loads((w.state/'subscription-pause.json').read_text());assert pause['reason']==kind
    if kind=='auth':
        before=w.queue.get(first['id'])['attempts'];pause['retry_at']=time.time()-1;atomic_json(w.state/'subscription-pause.json',pause)
        monkeypatch.setattr(CodexSubscription,'authenticate',lambda self:(_ for _ in ()).throw(SubscriptionAuthError('still unavailable')))
        w.tick();assert w.queue.get(first['id'])['attempts']==before;assert calls==[first['id']]
        pause['retry_at']=time.time()-1;atomic_json(w.state/'subscription-pause.json',pause)
        monkeypatch.setattr(CodexSubscription,'authenticate',lambda self:None)
        monkeypatch.setattr(FigurePipeline,'run',lambda self,job:w.queue.update(job['id'],state='complete',stage='complete'))
        w.tick();assert w.queue.get(first['id'])['state']=='complete';assert w.queue.get(second['id'])['attempts']==0


def test_explicit_backend_hold_preserves_queue_until_released(tmp_path):
    w=worker(tmp_path);j=w.queue.enqueue(pdf(tmp_path/'hold.pdf'),[])
    atomic_json(w.state/'analysis-hold.json',{'message':'Chat 분석 방식 전환 확인 중'})
    w.tick();assert w.queue.get(j['id'])['attempts']==0;assert w.status['stage']=='waiting'
    (w.state/'analysis-hold.json').unlink();w.tick();assert w.queue.get(j['id'])['state']=='prepared'
