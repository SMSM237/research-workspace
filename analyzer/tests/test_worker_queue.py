from pathlib import Path
import pytest
from figure_reports.worker_queue import JobQueue,FileStability,WorkerLock

def inputs(tmp_path):
    p=tmp_path/'input.pdf';p.write_bytes(b'%PDF-1.7 fixture bytes');return p

def test_job_snapshot_dedup_and_restart(tmp_path):
    pdf=inputs(tmp_path);q=JobQueue(tmp_path/'state');j=q.enqueue(pdf,[]);assert j['state']=='queued'
    assert q.enqueue(pdf,[])['id']==j['id']
    pdf.write_bytes(b'changed');assert Path(j['main']).read_bytes()==b'%PDF-1.7 fixture bytes'
    assert JobQueue(tmp_path/'state').get(j['id'])['fingerprint']==j['fingerprint']

def test_roles_and_id_are_validated_before_copy(tmp_path):
    pdf=inputs(tmp_path);q=JobQueue(tmp_path/'state')
    with pytest.raises(ValueError):q.enqueue(pdf,[pdf])
    with pytest.raises(ValueError):q.enqueue(pdf,[],report_id='../out')
    assert q.list()==[]

def test_claim_is_atomic_and_interruption_is_visible(tmp_path):
    q=JobQueue(tmp_path/'state');j=q.enqueue(inputs(tmp_path),[])
    assert q.claim()['id']==j['id'];assert JobQueue(tmp_path/'state').claim() is None
    assert q.recover_interrupted()==1 and q.get(j['id'])['state']=='interrupted'
    q.retry(j['id']);assert q.claim()['attempts']==2

def test_checkpoint_reuse_rejects_changed_output(tmp_path):
    q=JobQueue(tmp_path/'state');j=q.enqueue(inputs(tmp_path),[]);p=Path(j['folder'])/'result.json';p.write_text('{"ok":true}')
    q.checkpoint(j['id'],'parsing',p);assert q.completed(j['id'],'parsing')==p
    p.write_text('broken')
    with pytest.raises(ValueError):q.completed(j['id'],'parsing')

def test_checkpoint_cannot_escape_job_folder(tmp_path):
    q=JobQueue(tmp_path/'state');j=q.enqueue(inputs(tmp_path),[]);outside=tmp_path/'outside';outside.write_text('x')
    with pytest.raises(ValueError):q.checkpoint(j['id'],'parsing',outside)

def test_file_copy_stability_tracks_whole_bundle(tmp_path):
    p=inputs(tmp_path);s=FileStability(3)
    assert not s.ready([p],0);assert not s.ready([p],2);assert s.ready([p],3)
    supplement=tmp_path/'supplement.pdf';supplement.write_bytes(b'new')
    assert not s.ready([p,supplement],4);assert not s.ready([p,supplement],6);assert s.ready([p,supplement],7)
    p.write_bytes(b'new content');assert not s.ready([p,supplement],8)

def test_worker_lock_released_by_close(tmp_path):
    a=WorkerLock(tmp_path/'guard');b=WorkerLock(tmp_path/'guard');a.acquire()
    try:
        with pytest.raises(RuntimeError):b.acquire()
    finally:a.close()
    b.acquire();b.close()

def test_per_job_model_permission_is_not_inferred_from_pdf(tmp_path):
    q=JobQueue(tmp_path/'state');j=q.enqueue(inputs(tmp_path),[]);assert not j['allow_model_upload']
    q.authorize(j['id']);assert q.get(j['id'])['allow_model_upload']

def test_finished_job_cannot_be_retried_implicitly(tmp_path):
    q=JobQueue(tmp_path/'state');j=q.enqueue(inputs(tmp_path),[]);q.update(j['id'],state='complete',stage='complete')
    with pytest.raises(ValueError):q.retry(j['id'])
