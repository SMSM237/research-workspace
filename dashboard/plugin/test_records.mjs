import test from 'node:test';import assert from 'node:assert/strict';import vm from 'node:vm';import {readFileSync} from 'node:fs';import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),exports={};vm.runInNewContext(readFileSync(new URL('./dashboard-records.test-build.cjs',import.meta.url),'utf8'),{exports,require:name=>name==='obsidian'?{}:require('./dashboard-data.test-build.cjs')});
const {changeTask,taskEditableText}=exports;
test('editing a completed task preserves checkbox, dates, link syntax, block ID and other lines',()=>{const raw='  - [x] [[Notes/A|근거]] 읽기 ➕ 2026-09-09 ✅ 2026-09-10 ^task-abc',t={line:1,raw};const text='본문\r\n'+raw+'\r\n- [ ] 다음\r\n';assert.equal(taskEditableText(t),'[[Notes/A|근거]] 읽기');assert.equal(changeTask(text,t,'[[Notes/A|근거]] 검토'),'본문\r\n  - [x] [[Notes/A|근거]] 검토 ➕ 2026-09-09 ✅ 2026-09-10 ^task-abc\r\n- [ ] 다음\r\n');assert.equal(changeTask(text,t,taskEditableText(t)),text);});
test('deletion removes only the selected task line',()=>{const text='설명\n- [ ] 하나\n- [ ] 둘\n',t={line:1,raw:'- [ ] 하나'};assert.equal(changeTask(text,t,null),'설명\n- [ ] 둘\n');});
test('stale edits and deletes reject rather than overwrite another device',()=>{const t={line:0,raw:'- [ ] old'};assert.throws(()=>changeTask('- [ ] new',t,'edit'),/원본이 변경/);assert.throws(()=>changeTask('- [ ] new',t,null),/원본이 변경/);});
test('invalid title cannot inject lines or replace task identity and dates',()=>{const t={line:0,raw:'- [ ] old'};for(const value of ['', '  ', 'a\nb','new ^task-other','new ✅ 2026-09-12','a'.repeat(501)])assert.throws(()=>changeTask(t.raw,t,value),/한 줄/);});

function scheduleFixture(){
  class TFile{constructor(path){this.path=path;this.basename=path.split('/').pop().replace(/\.md$/,'');}}
  const files=new Map(),contents=new Map(),api={};
  const vault={getAbstractFileByPath:p=>files.get(p),read:async f=>contents.get(f.path),createFolder:async p=>files.set(p,{path:p}),create:async(p,raw)=>{assert.ok(!files.has(p),'never overwrite an existing note');const f=new TFile(p);files.set(p,f);contents.set(p,raw);return f;},process:async(f,fn)=>contents.set(f.path,fn(contents.get(f.path)))};
  vm.runInNewContext(readFileSync(new URL('./dashboard-records.test-build.cjs',import.meta.url),'utf8'),{exports:api,require:name=>name==='obsidian'?{TFile,parseYaml:JSON.parse,stringifyYaml:JSON.stringify}:require('./dashboard-data.test-build.cjs')});
  const raw=fm=>'---\n'+JSON.stringify(fm)+'\n---\n일정 본문 보존\n';
  return {records:new api.DashboardRecords({vault},()=>{}),vault,files,contents,raw};
}
test('deleted linked minutes switch to creation and reconnect without losing schedule data',async()=>{
  const {records,vault,contents,raw}=scheduleFixture();
  const schedule=await vault.create('Meetings/Schedule/recovery.md',raw({title:'연구 회의',date:'2026-09-10',time:'15:00',minutes:'Meetings/Minutes/deleted.md',custom:'보존'}));
  const before=await records.read(schedule);
  assert.equal(records.hasMinutes(before),false);
  const minutes=await records.minutes(before),after=await records.read(schedule);
  assert.equal(after.minutes,minutes.path);assert.equal(records.hasMinutes(after),true);
  assert.ok(after.raw.includes('"custom":"보존"'));assert.ok(after.raw.endsWith('일정 본문 보존\n'));
  for(const h of ['참석자','안건','논의 내용','결정 사항','후속 할 일'])assert.ok(contents.get(minutes.path).includes('## '+h));
  contents.set(minutes.path,contents.get(minutes.path)+'새로 작성한 내용');
  assert.equal((await records.minutes(before)).path,minutes.path);assert.ok(contents.get(minutes.path).endsWith('새로 작성한 내용'));
});
test('an unrelated note at the replacement path is preserved and not linked',async()=>{
  const {records,vault,contents,raw}=scheduleFixture();const schedule=await vault.create('Meetings/Schedule/conflict.md',raw({title:'회의',date:'2026-09-10',time:'09:00',minutes:'Meetings/Minutes/deleted.md'}));
  const other=await vault.create('Meetings/Minutes/conflict.md',raw({schedule:'Meetings/Schedule/another.md'})),original=contents.get(other.path);
  await assert.rejects(()=>records.minutes({file:schedule}),/기존 내용을 보호/);assert.equal(contents.get(other.path),original);assert.equal((await records.read(schedule)).minutes,'Meetings/Minutes/deleted.md');
});

test('schedule completion and undo preserve meeting link, date, title, and note body',async()=>{
  const {records,vault,raw}=scheduleFixture();
  const file=await vault.create('Meetings/Schedule/check.md',raw({title:'회의',date:'2026-09-10',time:'15:00',minutes:'Meetings/Minutes/check.md',custom:'유지'}));
  const initial=await records.read(file);assert.equal(initial.completed,false);
  await records.setCompleted(initial,true);let saved=await records.read(file);
  assert.equal(saved.completed,true);assert.match(saved.raw,/"completed_date":"\d{4}-\d{2}-\d{2}"/);
  assert.equal(saved.minutes,initial.minutes);assert.equal(saved.title,initial.title);assert.equal(saved.time,initial.time);assert.equal(saved.day,initial.day);assert.ok(saved.raw.includes('"custom":"유지"'));assert.ok(saved.raw.endsWith('일정 본문 보존\n'));
  await records.setCompleted(saved,false);saved=await records.read(file);assert.equal(saved.completed,false);assert.ok(saved.raw.includes('"completed_date":""'));
});
test('stale schedule checkbox does not overwrite an externally edited schedule',async()=>{
  const {records,vault,contents,raw}=scheduleFixture();const file=await vault.create('Meetings/Schedule/stale-check.md',raw({title:'회의',date:'2026-09-10',time:'09:00'}));
  const stale=await records.read(file);contents.set(file.path,stale.raw+'외부 메모');
  await assert.rejects(()=>records.setCompleted(stale,true),/일정이 변경/);assert.equal(contents.get(file.path),stale.raw+'외부 메모');
});
test('editing a planned task hides and preserves its scheduled date',()=>{
  const raw='- [ ] 실험 준비 ➕ 2026-09-10 ⏳ 2026-09-12 ^task-planned',t={line:0,raw};
  assert.equal(taskEditableText(t),'실험 준비');assert.equal(changeTask(raw,t,'실험 시약 준비'),'- [ ] 실험 시약 준비 ➕ 2026-09-10 ⏳ 2026-09-12 ^task-planned');
  assert.throws(()=>changeTask(raw,t,'실험 ⏳ 2026-09-30'),/한 줄/);
});
