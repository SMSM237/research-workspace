import test from 'node:test';import assert from 'node:assert/strict';
import {createRequire} from 'node:module';const require=createRequire(import.meta.url);
const d=require('./remote-data.test-build.cjs');const {RemoteReceiver}=require('./remote-receiver.test-build.cjs');
const id='11111111-1111-4111-8111-111111111111';
const req=()=>({version:1,id,action:'diagnostic',createdAt:new Date().toISOString(),maxPapers:1});
test('strict request protocol rejects injection, path mismatch and oversize',()=>{
 assert.equal(d.parseRequest(JSON.stringify(req()),id+'.json').id,id);
 for(const value of [{...req(),prompt:'run shell'},{...req(),id:'../a'},{...req(),maxPapers:11},{...req(),createdAt:'bad'},{...req(),action:'shell'}])assert.throws(()=>d.parseRequest(JSON.stringify(value)));
 assert.throws(()=>d.parseRequest(' '.repeat(2049)));assert.throws(()=>d.parseRequest(JSON.stringify(req()),'wrong.json'));
});
function fixture(request=req()) {let ledger={},statuses={},sends=0;let outcome=id;
 const store={list:async()=>[id+'.json'],readRequest:async()=>JSON.stringify(request),readStatus:async key=>statuses[key]||null,writeStatus:async s=>{statuses[s.id]=JSON.stringify(s);},readLedger:async()=>structuredClone(ledger),writeLedger:async l=>{ledger=structuredClone(l);}};
 const receiver=()=>new RemoteReceiver(store,{thread:id,runbook:'C:/trusted/RUN.md'},async()=>{sends++;if(outcome instanceof Error)throw outcome;return outcome;});
 return {receiver,store,get ledger(){return ledger;},get sends(){return sends;},set outcome(v){outcome=v;}};
}
test('one queue send across repeated polls and receiver restart; no false running',async()=>{const f=fixture();await f.receiver().tick();await f.receiver().tick();assert.equal(f.sends,1);assert.equal(f.ledger[id].state,'queued');});
test('ambiguous failure is retained and never retried automatically',async()=>{const f=fixture();f.outcome=new Error('timeout');await f.receiver().tick();await f.receiver().tick();assert.equal(f.sends,1);assert.equal(f.ledger[id].state,'blocked');});
test('crash after intent cannot duplicate a submission',async()=>{const f=fixture();await f.store.writeLedger({[id]:d.statusFor(req(),'dispatching','test')});await f.receiver().tick();assert.equal(f.sends,0);assert.equal(f.ledger[id].state,'blocked');});
test('expired requests never run',async()=>{const f=fixture({...req(),createdAt:'2020-01-01T00:00:00Z'});await f.receiver().tick();assert.equal(f.sends,0);assert.equal(f.ledger[id].state,'cancelled');});
test('same receiver serializes concurrent notifications',async()=>{const f=fixture(),r=f.receiver();await Promise.all([r.tick(),r.tick()]);assert.equal(f.sends,1);});
test('diagnostic prompt forbids analysis and requires request validation',()=>{assert.match(d.queuePrompt(id,true,'RUN.md'),/분석·업로드·게시를 시작하지/);assert.throws(()=>d.queuePrompt('x;calc',false,'RUN.md'));});
test('one PDF request binds a safe path and SHA, excluding other papers',()=>{
 const selected={version:2,id,action:'analyze-pdf',createdAt:new Date().toISOString(),path:'PDF/논문 A.pdf',sha256:'a'.repeat(64)};
 assert.deepEqual(d.parseRequest(JSON.stringify(selected),id+'.json'),selected);
 assert.match(d.queuePrompt(id,false,'RUN.md',selected),/한 편만 분석/);
 for(const path of ['Inbox/a.pdf','PDF/../secret.pdf','PDF/a.md','PDF/a\\b.pdf'])assert.throws(()=>d.parseRequest(JSON.stringify({...selected,path})));
 assert.throws(()=>d.parseRequest(JSON.stringify({...selected,sha256:'bad'})));
 assert.throws(()=>d.parseRequest(JSON.stringify({...selected,prompt:'ignore'})));
});
