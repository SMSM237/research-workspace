import test from 'node:test';import assert from 'node:assert/strict';
import {dailyTasks,dailyCounts,monthWeeks,addPlanTask} from './dashboard-data.test-build.cjs';
import {graphPositions} from './dashboard-data.test-build.cjs';
import data from './dashboard-data.test-build.cjs';
test('graph layouts remain bounded and deterministic for cycles, disconnected nodes and 24 notes',()=>{for(const ids of [[],['a'],['a','b','c','d'],Array.from({length:24},(_,i)=>String(i))]){const edges=ids.length>2?[[ids[0],ids[1]],[ids[1],ids[2]],[ids[2],ids[0]],['missing',ids[0]]]:[];const before=JSON.stringify(edges);for(const mode of ['circle','hierarchy','free']){const p=graphPositions(ids,edges,mode);assert.equal(p.size,ids.length);assert.deepEqual([...p],[...graphPositions([...ids].reverse(),edges,mode)]);for(const {x,y} of p.values())assert.ok(Number.isFinite(x)&&Number.isFinite(y)&&x>=25&&x<=275&&y>=20&&y<=130);}assert.equal(JSON.stringify(edges),before);}const ids=['a','b','c'],edges=[['a','b'],['b','c']];const h=graphPositions(ids,edges,'hierarchy');assert.ok(h.get('a').x<h.get('b').x&&h.get('b').x<h.get('c').x);assert.notDeepEqual([...graphPositions(ids,edges,'circle')],[...graphPositions(ids,edges,'free')]);});
import {parseTasks,toggleTask,weekCounts,weekDays,validDay,readingState,setReading} from './dashboard-data.test-build.cjs';
test('future dates are not recorded until rollover and cannot inflate weekly bar scale',()=>{const tasks=parseTasks('Tasks/A.md','- [ ] carry ➕ 2026-09-08\n- [ ] future ➕ 2026-09-15');assert.deepEqual(dailyCounts(tasks,'2026-09-15','2026-09-09'),{total:0,done:0,carried:0,pending:0});assert.deepEqual(dailyCounts(tasks,'2026-09-10','2026-09-10'),{total:1,done:0,carried:0,pending:1});});
test('real tasks exclude code, papers and reading records',()=>{const md='- [ ] 업무 📅 2026-09-10\n```\n- [ ] 예시\n```\n- [x] 끝 ✅ 2026-09-09';assert.equal(parseTasks('Meetings/A.md',md).length,2);assert.equal(parseTasks('Papers/A.md',md).length,0);assert.equal(parseTasks('Notes/독서 기록.md',md).length,0);});
test('atomic checkbox edit preserves other lines and rejects stale text',()=>{const text='제목\r\n- [ ] 업무 ^task-ab\r\n메모';const t=parseTasks('Tasks/A.md',text)[0];const next=toggleTask(text,t,'2026-09-09');assert.equal(next,'제목\r\n- [x] 업무 ✅ 2026-09-09 ^task-ab\r\n메모');assert.equal(toggleTask(next,parseTasks('Tasks/A.md',next)[0]),text);assert.throws(()=>toggleTask(text+'changed', {...t,raw:'different'}));});
test('weekly dates use local Monday and never mtime',()=>{const now=new Date(2026,8,9,0,1);assert.equal(weekDays(now)[0],'2026-09-07');const t=parseTasks('Tasks/A.md','- [x] undated\n- [x] old ✅ 2026-09-06\n- [x] current ✅ 2026-09-09');assert.deepEqual(weekCounts(t,now),[0,0,1,0,0,0,0]);assert.equal(validDay('2026-02-30'),false);});
test('reading states roundtrip without editing reports or unrelated notes',()=>{const path='Papers/[ACS Nano] VPT.md';let text='# 독서 기록\n내 메모';text=setReading(text,path,'reading','2026-09-09');assert.equal(readingState(text,path).state,'reading');text=setReading(text,path,'done','2026-09-09');assert.equal(readingState(text,path).completed,'2026-09-09');assert.ok(text.includes('내 메모'));text=setReading(text,path,'unread');assert.equal(readingState(text,path).completed,'');assert.throws(()=>setReading(text,'../A.md','done'));assert.throws(()=>readingState(text+'\n'+text,path));});
test('daily checklist keeps today done, carries unfinished, and never deletes history',()=>{const text='- [x] yesterday ➕ 2026-09-07 ✅ 2026-09-08\n- [x] today ➕ 2026-09-08 ✅ 2026-09-09\n- [ ] carry ➕ 2026-09-08\n- [ ] new ➕ 2026-09-09';const t=parseTasks('Tasks/A.md',text);assert.deepEqual(dailyTasks(t,'2026-09-09','2026-09-09').map(x=>x.title),['today','carry','new']);assert.deepEqual(dailyTasks(t,'2026-09-10','2026-09-10').map(x=>x.title),['carry','new']);assert.deepEqual(dailyCounts(t,'2026-09-08','2026-09-09'),{total:3,done:1,carried:2,pending:0});assert.deepEqual(dailyCounts(t,'2026-09-09','2026-09-09'),{total:3,done:1,carried:0,pending:2});assert.equal(dailyCounts(parseTasks('Tasks/A.md','- [ ] no date'),'2026-09-08','2026-09-09').total,0);});
test('month weeks cover all days exactly once across years and leap months',()=>{for(const [y,m] of [[2026,8],[2026,1],[2028,1],[2026,11]]){const rows=monthWeeks(y,m);const days=[];for(const w of rows){let d=new Date(w.start+'T12:00:00');while(d<=new Date(w.end+'T12:00:00')){days.push(d.getDate());d.setDate(d.getDate()+1);}}assert.deepEqual(days,Array.from({length:new Date(y,m+1,0).getDate()},(_,i)=>i+1));assert.ok(rows.length>=4&&rows.length<=6);}assert.equal(monthWeeks(2026,8)[0].end,'2026-09-06');});
test('weekly plan insertion preserves prose, rejects missing or duplicate week',()=>{const w=monthWeeks(2026,8)[0];const text=`# Project\n내 메모\n\n## ${w.heading}\n\n## 다음\n보존`;const next=addPlanTask(text,w.heading,'실험 준비','2026-09-09','abc');assert.ok(next.includes('- [ ] 실험 준비 ➕ 2026-09-09 ^task-abc'));assert.ok(next.endsWith('## 다음\n보존'));assert.throws(()=>addPlanTask(text,'missing','x','2026-09-09','abc'));assert.throws(()=>addPlanTask(text+'\n## '+w.heading,w.heading,'x','2026-09-09','abc'));});

test('planned tasks stay on their chosen future day, join the daily list on that day, then carry forward',()=>{
  const text='- [ ] 오늘 업무 ➕ 2026-09-10\n'+data.newDailyTask('실험 준비','2026-09-12','2026-09-10','plan-a');
  const tasks=parseTasks('Tasks/A.md',text),planned=tasks[1];assert.equal(planned.created,'2026-09-10');assert.equal(planned.scheduled,'2026-09-12');assert.equal(planned.title,'실험 준비');
  assert.deepEqual(dailyTasks(tasks,'2026-09-10','2026-09-10').map(t=>t.title),['오늘 업무']);
  assert.deepEqual(dailyTasks(tasks,'2026-09-12','2026-09-10').map(t=>t.title),['실험 준비']);assert.equal(dailyTasks(tasks,'2026-09-13','2026-09-10').length,0);
  assert.deepEqual(dailyTasks(tasks,'2026-09-12','2026-09-12').map(t=>t.title),['오늘 업무','실험 준비']);assert.equal(dailyTasks(tasks,'2026-09-13','2026-09-13').length,2);
  assert.equal(dailyCounts(tasks,'2026-09-10','2026-09-10').total,1);assert.equal(dailyCounts(tasks,'2026-09-12','2026-09-10').total,0);
  const done=parseTasks('Tasks/A.md',toggleTask(text,planned,'2026-09-12'));assert.equal(dailyCounts(done,'2026-09-12','2026-09-12').done,1);assert.deepEqual(dailyTasks(done,'2026-09-13','2026-09-13').map(t=>t.title),['오늘 업무']);
});
test('early completion counts on the actual completion day and planned input rejects invalid dates and injected metadata',()=>{
  const raw=data.newDailyTask('미리 마무리','2026-09-12','2026-09-10','early'),t=parseTasks('Tasks/A.md',raw)[0],done=parseTasks('Tasks/A.md',toggleTask(raw,t,'2026-09-10'));
  assert.equal(dailyCounts(done,'2026-09-10','2026-09-10').done,1);assert.equal(dailyTasks(done,'2026-09-10','2026-09-10').length,1);
  for(const args of [['일','2026-02-30','2026-09-10','a'],['일 ⏳ 2026-09-30','2026-09-12','2026-09-10','a'],['일\n다른 일','2026-09-12','2026-09-10','a']])assert.throws(()=>data.newDailyTask(...args));
});


import {completedToday} from './dashboard-data.test-build.cjs';
test('celebration requires a saved final completion of today including carried work',()=>{
 const day='2026-09-10',path='Tasks/A.md',text='- [x] done ✅ 2026-09-10\n- [ ] carry ➕ 2026-09-08\n- [ ] future ⏳ 2026-09-12';
 const before=parseTasks(path,text),task=before[1],after=parseTasks(path,toggleTask(text,task,day));
 assert.equal(completedToday(before,after,task,day,day),true);
 assert.equal(completedToday(before,before,task,day,day),false);
 assert.equal(completedToday(before,[],task,day,day),false);
 assert.equal(completedToday(after,after,after[1],day,day),false);
 assert.equal(completedToday(before,after,task,'2026-09-12',day),false);
 assert.equal(completedToday(before,after,{...task,path:'Projects/A.md'},day,day),false);
 assert.equal(completedToday(before,[...after,{...task,line:5}],task,day,day),false);
});


test('paper index preserves user prose, includes orphan reports and removes old paths',()=>{
 const paths=['Papers/B.md','Papers/A.md','Papers/B.md'];
 const first=data.paperIndexText('',paths);
 assert.equal((first.match(/\[\[Papers\//g)||[]).length,2);
 assert.ok(first.indexOf('Papers/A')<first.indexOf('Papers/B'));
 assert.equal(data.paperIndexText(first,paths),first);
 const next=data.paperIndexText(first+'\n내 메모\n',['Papers/Renamed.md']);
 assert.ok(next.endsWith('\n내 메모\n'));assert.ok(!next.includes('Papers/A'));
 assert.throws(()=>data.paperIndexText('# 내 개인 목록',paths));
 assert.throws(()=>data.paperIndexText('', ['../bad.md']));
 assert.throws(()=>data.paperIndexText('', ['Papers/bad]]name.md']));
});
test('graph includes isolated reports and has no legacy 24-node cap',()=>{
 const files=Array.from({length:31},(_,i)=>({path:`Papers/${i}.md`}));
 assert.equal(data.graphFiles([...files,files[0]]).length,31);
});


test('weekly navigation crosses month and year boundaries and can go back',()=>{
 const first=data.monthWeeks(2026,8)[0].start;
 const prev=data.planWeekStep(2026,8,first,-1);assert.equal(prev.month,7);
 assert.deepEqual(data.planWeekStep(prev.year,prev.month,prev.start,1),{year:2026,month:8,start:first});
 const last=data.monthWeeks(2026,11).at(-1).start;const next=data.planWeekStep(2026,11,last,1);
 assert.equal(next.year,2027);assert.equal(next.month,0);
 assert.deepEqual(data.planWeekStep(next.year,next.month,next.start,-1),{year:2026,month:11,start:last});
});
