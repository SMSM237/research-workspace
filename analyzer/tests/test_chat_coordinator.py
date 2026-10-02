import json
import shutil
import pytest
from figure_reports.chat_coordinator import ChatCoordinator
from test_chat_exchange import fixture


def button_fixture(tmp_path):
    w,j,v=fixture(tmp_path)
    rid='11111111-2222-4333-8444-555555555555'
    paper=w.vault/'Paper'/'test.pdf';paper.parent.mkdir();shutil.copyfile(j['main'],paper)
    requests=w.vault/'.paper-control'/'requests';requests.mkdir(parents=True)
    (requests/f'{rid}.json').write_text(json.dumps({'version':2,'id':rid,'action':'analyze-pdf','createdAt':'2026-09-23T00:00:00Z','path':'Paper/test.pdf','sha256':j['source_hashes'][0]}),encoding='utf-8')
    (w.state.parent/'config.json').write_text(json.dumps({'vault':str(w.vault)}),encoding='utf-8')
    (w.state.parent/'mobile-control-ledger.json').write_text(json.dumps({rid:{'state':'queued','queueMessageId':'received'}}),encoding='utf-8')
    return w,j,v

def test_one_owner_and_resume_survive_reopen(tmp_path):
    w,j,v=button_fixture(tmp_path);c=ChatCoordinator(w.state)
    assert c.peek()['status']=='ready'
    first=c.claim('one');assert first['job']['id']==j['id']
    assert c.claim('two')['status']=='busy'
    c.update('one',dict(phase='chat_analysis',chat_url='https://chatgpt.com/c/test'))
    other=ChatCoordinator(w.state);assert other.claim('one')['record']['chat_url'].endswith('/test')
    with pytest.raises(ValueError):other.update('two',dict(phase='complete'))
    with pytest.raises(ValueError):other.update('one',dict(phase='complete'))
    w.queue.update(j['id'],state='complete');other.update('one',dict(phase='complete'),release=True)
    assert other.peek()['status']=='idle'

def test_stale_lease_resumes_same_job_and_pause_preserves_queue(tmp_path):
    w,j,v=button_fixture(tmp_path);c=ChatCoordinator(w.state)
    c.claim('one',now=0);c.read()
    resumed=c.claim('two',now=2800);assert resumed['job']['id']==j['id']
    import time
    c.update('two',dict(phase='waiting',retry_at=time.time()+3600,last_error='login'),release=True)
    assert c.peek()['status']=='idle' and w.queue.get(j['id'])['state']=='prepared'


def test_unrequested_paper_is_not_dispatched(tmp_path):
    w,j,v=fixture(tmp_path);c=ChatCoordinator(w.state)
    assert c.peek()['status']=='idle'
    assert c.claim('one')['status']=='idle'
