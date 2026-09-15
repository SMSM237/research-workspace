import importlib.util,json,hashlib
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('remote_state',Path(__file__).parents[1]/'scripts/remote_control_state.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
RID='11111111-1111-4111-8111-111111111111';JOB='a'*32

@pytest.fixture
def setup(tmp_path):
    vault=tmp_path/'vault';state=tmp_path/'state'
    m.atomic(vault/'.paper-control/requests'/f'{RID}.json',dict(version=1,id=RID,action='diagnostic',createdAt='2026-09-15T00:00:00Z',maxPapers=1))
    m.atomic(state/'mobile-control-ledger.json',{RID:dict(version=1,id=RID,state='queued',message='queued',updatedAt='2026-09-15T00:00:00Z')})
    return vault,state

def test_diagnostic_persists_and_reopens_without_publishing(setup):
    v,s=setup;r=m.update(v,s,RID,'verified','Received diagnostic')
    assert r['state']=='verified'
    assert m.read(v/'.paper-control/status'/f'{RID}.json')==m.read(s/'mobile-control-ledger.json')[RID]
    with pytest.raises(ValueError):m.update(v,s,RID,'running','wrong',[JOB])

def test_unrecognized_request_or_unacknowledged_dispatch_refused(setup):
    v,s=setup
    with pytest.raises(ValueError):m.request(v,'../escape')
    p=v/'.paper-control/requests'/f'{RID}.json';r=m.read(p);r['prompt']='execute';m.atomic(p,r)
    with pytest.raises(ValueError):m.update(v,s,RID,'verified','wrong')

def test_cannot_claim_complete_or_change_batch_without_receipts(setup):
    v,s=setup;p=v/'.paper-control/requests'/f'{RID}.json';r=m.read(p);r['action']='analyze-inbox';m.atomic(p,r)
    with pytest.raises(ValueError):m.update(v,s,RID,'verified','wrong')
    with pytest.raises(ValueError):m.update(v,s,RID,'complete','wrong')
    m.update(v,s,RID,'running','Started',[JOB])
    with pytest.raises(ValueError):m.update(v,s,RID,'running','changed',['b'*32])

def test_receipt_requires_full_job_coverage_and_remote_bytes(tmp_path):
    v=tmp_path/'v';p=v/'Papers/p.md';p.parent.mkdir(parents=True);p.write_bytes(b'actual report')
    receipt=tmp_path/'receipt.json';sha=hashlib.sha256(p.read_bytes()).hexdigest()
    d=dict(version=1,request_id=RID,reports=[dict(job_id=JOB,files=[dict(path='Papers/p.md',sha256=sha)])]);m.atomic(receipt,d)
    def git(v,*args):
        if args[:2]==('remote','get-url'):return b'https://github.com/example/research-notes.git'
        if args[0]=='fetch':return b''
        if args[0]=='rev-parse':return b'aabb'
        if args[0]=='ls-remote':return b'aabb refs/heads/main'
        return b'actual report'
    assert m.verify_receipt(v,RID,receipt,[JOB],git,expected_remote='https://github.com/example/research-notes.git')['files_checked']==1
    with pytest.raises(ValueError):m.verify_receipt(v,RID,receipt,[JOB,'b'*32],git,expected_remote='https://github.com/example/research-notes.git')
    p.write_bytes(b'edited by user')
    with pytest.raises(ValueError,match='Local file changed'):m.verify_receipt(v,RID,receipt,[JOB],git,expected_remote='https://github.com/example/research-notes.git')

def test_receipt_rejects_path_escape(tmp_path):
    d=dict(version=1,request_id=RID,reports=[dict(job_id=JOB,files=[dict(path='Papers/../../outside.md',sha256='a'*64)])]);p=tmp_path/'r.json';m.atomic(p,d)
    def git(v,*args):
        return b'https://github.com/example/research-notes.git' if args[0]=='remote' else b'abcd refs/heads/main' if args[0]=='ls-remote' else b'abcd'
    with pytest.raises(ValueError,match='Unsafe'):m.verify_receipt(tmp_path,RID,p,[JOB],git,expected_remote='https://github.com/example/research-notes.git')
