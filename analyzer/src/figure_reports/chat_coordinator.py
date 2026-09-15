"""Durable handoff between the Inbox worker and scheduled Codex browser turns.

No browser automation, model calls, or credential access occur in this module.
"""
from pathlib import Path
import argparse,json,time
from .worker_queue import JobQueue,WorkerLock
from .build import atomic_write

class ChatCoordinator:
    def __init__(self,state):
        self.root=Path(state);self.queue=JobQueue(state);self.path=self.root/'chat-coordinator.json'
    def read(self):
        return json.loads(self.path.read_text('utf-8')) if self.path.exists() else {'active':None,'jobs':{}}
    def save(self,data):atomic_write(self.path,json.dumps(data,ensure_ascii=False,indent=2).encode())
    def peek(self):
        data=self.read();jobs=self.queue.list();active=data.get('active')
        if active:
            record=data['jobs'][active['job_id']]
            return dict(status='waiting' if record.get('retry_at',0)>time.time() else 'resume',active=active,record=record)
        candidates=[j for j in jobs if j['state'] in {'queued','prepared','review','interrupted'} and data['jobs'].get(j['id'],{}).get('retry_at',0)<=time.time()]
        return dict(status='ready' if candidates else 'idle',count=len(candidates),next_job={k:candidates[0].get(k) for k in ['id','report_id','state','folder','bundle','source_names']} if candidates else None)
    def claim(self,owner,now=None):
        now=time.time() if now is None else now;lock=WorkerLock(self.root/'chat-coordinator.lock');lock.acquire()
        try:
            data=self.read();active=data.get('active')
            if active:
                if data['jobs'][active['job_id']].get('retry_at',0)>now:return dict(status='waiting')
                if active['owner']!=owner and active['lease_until']>now:return dict(status='busy')
                jid=active['job_id'];record=data['jobs'][jid]
            else:
                candidates=[j for j in self.queue.list() if j['state'] in {'queued','prepared','review','interrupted'} and data['jobs'].get(j['id'],{}).get('retry_at',0)<=now]
                if not candidates:return dict(status='idle')
                jid=candidates[0]['id'];record=data['jobs'].setdefault(jid,dict(phase='prepare',chat_url=None))
            data['active']=dict(job_id=jid,owner=owner,lease_until=now+2700);self.save(data)
            return dict(status='claimed',job=self.queue.get(jid),record=record,resume_required=record['phase']!='prepare')
        finally:lock.close()
    def update(self,owner,fields,release=False):
        allowed={'phase','chat_url','packet_dir','analysis_path','visual_dir','retry_at','last_error','publication_receipt'}
        if not set(fields)<=allowed:raise ValueError('Unknown coordinator field')
        lock=WorkerLock(self.root/'chat-coordinator.lock');lock.acquire()
        try:
            data=self.read();active=data.get('active')
            if not active or active['owner']!=owner:raise ValueError('This run does not own the Chat job')
            if fields.get('phase')=='complete' and self.queue.get(active['job_id'])['state']!='complete':raise ValueError('No published report exists')
            data['jobs'][active['job_id']].update(fields,updated_at=time.time());active['lease_until']=time.time()+2700
            if release:data['active']=None
            self.save(data);return dict(status='saved',record=data['jobs'][active['job_id']])
        finally:lock.close()

def main():
    import sys
    sys.stdout.reconfigure(encoding='utf-8');p=argparse.ArgumentParser()
    p.add_argument('action',choices=['peek','claim','update','release']);p.add_argument('--state',required=True);p.add_argument('--owner',default='paper-vault-codex');p.add_argument('--fields',default='{}');a=p.parse_args();c=ChatCoordinator(a.state)
    result=c.peek() if a.action=='peek' else c.claim(a.owner) if a.action=='claim' else c.update(a.owner,json.loads(a.fields),a.action=='release')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
