"""Trusted local acknowledgements for mobile requests; never a model runner.

Complete requires per-file SHA-256 equality with the fetched, verified remote
commit. A diagnostic acknowledgement is a different state from publication.
"""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, os, re, sqlite3, subprocess
from datetime import datetime, timezone

UUID = re.compile(r'^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$')
PDF_PATH = re.compile(r'^PDF/(?:[^/\\:\r\n<>"|?*#]+/)*[^/\\:\r\n<>"|?*#]+\.pdf$',re.I)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def atomic(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    os.replace(tmp,path)

def request(vault, rid):
    if not UUID.fullmatch(rid):raise ValueError('Invalid request ID')
    p=Path(vault)/'.paper-control/requests'/f'{rid}.json'
    if p.stat().st_size>2048:raise ValueError('Request too large')
    r=read(p)
    if r.get('id')!=rid or not isinstance(r.get('createdAt'),str):raise ValueError('Invalid request')
    if r.get('version')==1:
        if set(r)!={'version','id','action','createdAt','maxPapers'} or r['action'] not in {'analyze-inbox','diagnostic'} or type(r['maxPapers']) is not int or not 1<=r['maxPapers']<=10:raise ValueError('Invalid request')
    elif r.get('version')==2:
        rel=r.get('path');sha=r.get('sha256')
        if set(r)!={'version','id','action','createdAt','path','sha256'} or r['action']!='analyze-pdf' or not isinstance(rel,str) or not PDF_PATH.fullmatch(rel) or any(x in {'.','..',''} for x in rel.split('/')) or not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('Invalid PDF request')
        root=Path(vault).resolve();p=(root/rel).resolve()
        if not p.is_relative_to(root) or not p.is_relative_to((root/'PDF').resolve()) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError('Selected PDF is missing or changed')
    else:raise ValueError('Invalid request version')
    return r

def selected_job(state,jid,sha):
    db=Path(state)/'state/jobs.sqlite3'
    with sqlite3.connect(f'file:{db.as_posix()}?mode=ro',uri=True) as con:
        row=con.execute('SELECT data FROM jobs WHERE id=?',(jid,)).fetchone()
    if not row or json.loads(row[0]).get('source_hashes',[None])[0]!=sha:raise ValueError('Selected job does not match PDF hash')

def git(vault,*args):
    result=subprocess.run(['git','-c','credential.interactive=never',*args],cwd=vault,capture_output=True,timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode:raise ValueError('Git verification failed: '+result.stderr.decode('utf-8','replace')[:250])
    return result.stdout

def verify_receipt(vault,rid,receipt,selected,run_git=git,expected_remote=None):
    d=read(receipt)
    if d.get('version')!=1 or d.get('request_id')!=rid or not isinstance(d.get('reports'),list) or not d['reports']:raise ValueError('Invalid publication receipt')
    reports=d['reports'];ids=[r.get('job_id') for r in reports]
    if len(ids)!=len(set(ids)) or set(ids)!=set(selected):raise ValueError('Publication does not cover selected jobs')
    remote=run_git(vault,'remote','get-url','origin').decode().strip()
    if not expected_remote or remote.removesuffix('.git')!=expected_remote.removesuffix('.git'):raise ValueError('Unexpected Git destination')
    run_git(vault,'fetch','origin','main')
    head=run_git(vault,'rev-parse','origin/main').decode().strip()
    remote_head=run_git(vault,'ls-remote','origin','refs/heads/main').decode().split()[0]
    if head!=remote_head:raise ValueError('Remote changed during verification')
    checked=0
    for report in reports:
        files=report.get('files',[])
        if not files or not any(str(f.get('path','')).startswith('Papers/') and str(f.get('path','')).endswith('.md') for f in files):raise ValueError('Missing paper report')
        for f in files:
            rel=f.get('path','');sha=f.get('sha256','');pp=PurePosixPath(rel)
            if not rel or '\\' in rel or ':' in rel or pp.is_absolute() or '..' in pp.parts or not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('Unsafe receipt path or hash')
            path=(Path(vault)/rel).resolve()
            if not path.is_relative_to(Path(vault).resolve()):raise ValueError('Receipt path escapes Vault')
            if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:raise ValueError('Local file changed')
            if hashlib.sha256(run_git(vault,'show',f'{head}:{rel}')).hexdigest()!=sha:raise ValueError('Remote file differs')
            checked+=1
    return {'commit':head,'files_checked':checked,'completed':len(reports)}

def update(vault,state,rid,phase,message,selected=None,receipt=None):
    r=request(vault,rid);lp=Path(state)/'mobile-control-ledger.json';ledger=read(lp) if lp.exists() else {}
    existing=ledger.get(rid)
    if not existing:raise ValueError('Request has not been dispatched by this PC')
    if existing['state'] in {'complete','verified','empty','cancelled'}:raise ValueError('Terminal request cannot be rewritten')
    if len(message)>1000:raise ValueError('Message too long')
    record={**existing,'state':phase,'message':message,'updatedAt':datetime.now(timezone.utc).isoformat()}
    if phase=='verified':
        if r['action']!='diagnostic':raise ValueError('Only diagnostics can be verified without reports')
    elif phase=='running':
        if r['action'] not in {'analyze-inbox','analyze-pdf'} or not selected or len(selected)>(r['maxPapers'] if r['version']==1 else 1) or len(set(selected))!=len(selected):raise ValueError('Select only requested jobs before analysis')
        if any(not re.fullmatch('[a-f0-9]{32}',s) for s in selected):raise ValueError('Invalid job IDs')
        if r['version']==2:selected_job(state,selected[0],r['sha256'])
        if existing.get('selected_jobs') and existing['selected_jobs']!=selected:raise ValueError('Cannot change a running batch')
        record['selected_jobs']=selected;record['total']=len(selected);record.setdefault('completed',0)
    elif phase=='complete':
        if r['action'] not in {'analyze-inbox','analyze-pdf'} or not receipt or not existing.get('selected_jobs'):raise ValueError('Missing selected jobs or receipt')
        config=read(Path(state)/'config.json')
        verified=verify_receipt(vault,rid,receipt,existing['selected_jobs'],expected_remote=config.get('expected_remote'))
        if r['version']==2 and hashlib.sha256(git(vault,'show',f'{verified["commit"]}:{r["path"]}')).hexdigest()!=r['sha256']:raise ValueError('Selected PDF differs in remote Git')
        record.update(verified)
    elif phase in {'review','publishing'}:
        if r['action'] not in {'analyze-inbox','analyze-pdf'} or not existing.get('selected_jobs'):raise ValueError('Selected job is required')
    elif phase not in {'waiting','blocked','empty','cancelled'}:raise ValueError('Unsupported status transition')
    ledger[rid]=record;atomic(lp,ledger)
    atomic(Path(vault)/'.paper-control/status'/f'{rid}.json',record)
    return record

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['running','review','publishing','waiting','blocked','verified','empty','cancelled','complete'])
    p.add_argument('--request',required=True);p.add_argument('--message',required=True);p.add_argument('--jobs',nargs='*');p.add_argument('--receipt')
    p.add_argument('--vault',default=str(Path.home()/'Documents/Codex/Paper Research Vault'));p.add_argument('--state',default=str(Path.home()/'Documents/Codex/Paper Analyzer'))
    a=p.parse_args();print(json.dumps(update(a.vault,a.state,a.request,a.phase,a.message,a.jobs,a.receipt),ensure_ascii=False))
if __name__=='__main__':main()
