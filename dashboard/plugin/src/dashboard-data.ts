export interface Task {path:string;line:number;raw:string;title:string;done:boolean;due:string;created:string;scheduled:string;completed:string;links:string[];}
export const READING='Notes/독서 기록.md';
export function localDay(date=new Date()):string{return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;}
export function validDay(value:string):boolean{if(!/^\d{4}-\d{2}-\d{2}$/.test(value))return false;return localDay(new Date(value+'T12:00:00'))===value;}
export function taskSource(path:string):boolean{return /^(Tasks|Meetings|Projects|Notes)\/.+\.md$/.test(path)&&path!==READING;}
export function parseTasks(path:string,text:string):Task[]{
  if(!taskSource(path))return [];const tasks:Task[]=[];let fence='';
  text.split(/\r?\n/).forEach((raw,line)=>{const mark=raw.match(/^\s*(`{3,}|~{3,})/);if(mark){if(!fence)fence=mark[1][0];else if(mark[1][0]===fence)fence='';return;}if(fence)return;
    const m=raw.match(/^\s*[-*+] \[([ xX])\]\s+(.+)$/);if(!m)return;
    const date=(symbol:string)=>{const d=m[2].match(new RegExp(symbol+'\\s*(\\d{4}-\\d{2}-\\d{2})'))?.[1]||'';return validDay(d)?d:'';};
    tasks.push({path,line,raw,done:m[1].toLowerCase()==='x',due:date('📅'),created:date('➕'),scheduled:date('⏳'),completed:date('✅'),links:[...m[2].matchAll(/\[\[([^\]|#]+)(?:[^\]]*)\]\]/g)].map(x=>x[1]),title:m[2].replace(/(?:📅|✅|➕|⏳)\s*\d{4}-\d{2}-\d{2}/g,'').replace(/\s*\^[\w-]+\s*$/,'').replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g,'$2').replace(/\[\[([^\]]+)\]\]/g,(_,p)=>p.split('/').pop()).trim()});
  });return tasks;
}
export function toggleTask(text:string,task:Task,day=localDay()):string{
  if(!validDay(day))throw Error('완료 날짜를 확인해 주세요.');const sep=text.includes('\r\n')?'\r\n':'\n',lines=text.split(/\r?\n/);
  if(lines[task.line]!==task.raw)throw Error('원본이 변경되었습니다. 새로고침 후 다시 선택해 주세요.');
  let next=task.raw.replace(/\[([ xX])\]/,task.done?'[ ]':'[x]').replace(/\s*✅\s*\d{4}-\d{2}-\d{2}/g,'');
  if(!task.done){const id=next.match(/\s+(\^[\w-]+)\s*$/);next=id?next.slice(0,id.index)+` ✅ ${day} ${id[1]}`:next+` ✅ ${day}`;}
  lines[task.line]=next;return lines.join(sep);
}
export function weekDays(now=new Date()):string[]{const d=new Date(now.getFullYear(),now.getMonth(),now.getDate(),12);d.setDate(d.getDate()-((d.getDay()+6)%7));return Array.from({length:7},(_,i)=>{const x=new Date(d);x.setDate(x.getDate()+i);return localDay(x);});}
export function weekCounts(tasks:Task[],now=new Date()):number[]{return weekDays(now).map(day=>tasks.filter(t=>t.done&&t.completed===day).length);}
export function taskStart(task:Task):string{return task.scheduled||task.created;}
export function newDailyTask(title:string,day:string,created:string,id:string):string{
  title=title.trim();if(!title||title.length>500||/[\r\n]/.test(title)||/(?:📅|✅|➕|⏳)\s*\d{4}-\d{2}-\d{2}|\^[\w-]+\s*$/.test(title)||!validDay(day)||!validDay(created)||!/^[\w-]+$/.test(id))throw Error('할 일 내용과 선택 날짜를 확인해 주세요.');
  return `- [ ] ${title} ➕ ${created} ⏳ ${day} ^task-${id}`;
}
export function dailyTasks(tasks:Task[],day=localDay(),today=localDay()):Task[]{
  return tasks.filter(t=>t.path.startsWith('Tasks/')&&(day>today?taskStart(t)===day:((t.done&&t.completed===day)||((!taskStart(t)||taskStart(t)<=day)&&!t.done))));
}
export function dailyCounts(tasks:Task[],day:string,today=localDay()){
  if(day>today)return {total:0,done:0,carried:0,pending:0};
  const eligible=tasks.filter(t=>t.path.startsWith('Tasks/')&&((t.done&&t.completed===day)||(taskStart(t)?taskStart(t)<=day:(t.completed?t.completed===day:day===today)))&&(!t.done||(t.completed&&t.completed>=day)));
  const done=eligible.filter(t=>t.done&&t.completed===day).length,remaining=eligible.length-done;
  return {total:eligible.length,done,carried:day<today?remaining:0,pending:day===today?remaining:0};
}
export function monthWeeks(year:number,month:number){
  const last=new Date(year,month+1,0).getDate();const result:Array<{start:string;end:string;heading:string}>=[];let day=1;
  while(day<=last){const d=new Date(year,month,day,12),end=Math.min(last,day+(7-d.getDay())%7);const start=localDay(d),finish=localDay(new Date(year,month,end,12));result.push({start,end:finish,heading:`${result.length+1}주차 · ${start} — ${finish}`});day=end+1;}return result;
}
export function addPlanTask(text:string,heading:string,title:string,day:string,id:string){
  if(!title.trim()||/[\r\n]/.test(title)||!validDay(day)||!/^[\w-]+$/.test(id))throw Error('계획 내용을 확인해 주세요.');
  const sep=text.includes('\r\n')?'\r\n':'\n',lines=text.split(/\r?\n/),matches=lines.map((l,i)=>l===`## ${heading}`?i:-1).filter(i=>i>=0);if(matches.length!==1)throw Error('주차 제목이 변경되거나 중복되었습니다. 원본 노트를 확인해 주세요.');
  let end=matches[0]+1;while(end<lines.length&&!/^## /.test(lines[end]))end++;lines.splice(end,0,`- [ ] ${title.trim()} ➕ ${day} ^task-${id}`,'');return lines.join(sep);
}
export type GraphLayout='circle'|'hierarchy'|'free';
/** Stable coordinates only: layout never adds, removes, or infers note links. */
export function graphPositions(ids:string[],edges:ReadonlyArray<readonly [string,string]>,mode:GraphLayout){
  const keys=[...new Set(ids)].sort(),n=keys.length,result=new Map<string,{x:number;y:number}>();
  if(!n)return result;
  const valid=edges.filter(([a,b])=>a!==b&&keys.includes(a)&&keys.includes(b));
  const points=keys.map((_,i)=>({x:150+110*Math.cos(i/n*Math.PI*2),y:75+55*Math.sin(i/n*Math.PI*2)}));
  if(n===1)points[0]={x:150,y:75};
  if(mode==='hierarchy'){
    const levels=new Map<string,number>(),incoming=new Set(valid.map(e=>e[1]));
    // Directed shortest distance from roots. Cycles without roots start a new component.
    const visit=(seed:string)=>{if(levels.has(seed))return;levels.set(seed,0);const queue=[seed];for(let i=0;i<queue.length;i++)for(const [a,b] of valid)if(a===queue[i]&&!levels.has(b)){levels.set(b,levels.get(a)!+1);queue.push(b);}};
    keys.filter(k=>!incoming.has(k)).forEach(visit);keys.forEach(visit);
    const depth=Math.max(...levels.values());
    for(let level=0;level<=depth;level++){const row=keys.filter(k=>levels.get(k)===level);row.forEach((k,i)=>{const cols=Math.ceil(row.length/5),col=Math.floor(i/5),count=Math.min(5,row.length-col*5),base=depth===0?150:60+180*level/depth;points[keys.indexOf(k)]={x:Math.max(25,Math.min(275,base+(col-(cols-1)/2)*28)),y:count===1?75:25+100*(i%5)/(count-1)};});}
  }else if(mode==='free'&&n>1){
    // Bounded deterministic force settling; no background animation or random drift.
    for(let step=0;step<100;step++){
      const force=points.map(p=>({x:(150-p.x)*.012,y:(75-p.y)*.018}));
      for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){const dx=points[i].x-points[j].x,dy=points[i].y-points[j].y,d2=Math.max(16,dx*dx+dy*dy),f=420/d2;force[i].x+=dx*f;force[i].y+=dy*f;force[j].x-=dx*f;force[j].y-=dy*f;}
      for(const [a,b] of valid){const i=keys.indexOf(a),j=keys.indexOf(b),dx=points[j].x-points[i].x,dy=points[j].y-points[i].y,d=Math.max(1,Math.hypot(dx,dy)),f=(d-72)*.018/d;force[i].x+=dx*f;force[i].y+=dy*f;force[j].x-=dx*f;force[j].y-=dy*f;}
      const cooling=1-step/120;points.forEach((p,i)=>{p.x=Math.max(48,Math.min(252,p.x+Math.max(-5,Math.min(5,force[i].x))*cooling));p.y=Math.max(25,Math.min(125,p.y+Math.max(-5,Math.min(5,force[i].y))*cooling));});
    }
  }
  keys.forEach((k,i)=>result.set(k,points[i]));return result;
}
export type ReadingState='unread'|'reading'|'done';
export function readingState(text:string,path:string):{state:ReadingState;completed:string}{
  const rows=text.split(/\r?\n/).filter(line=>line.includes(`[[${path}]]`));if(rows.length>1)throw Error('독서 기록에 같은 논문이 중복되어 있습니다.');
  const m=rows[0]?.match(/^- \[([ x-])\]/);return {state:m?.[1]==='x'?'done':m?.[1]==='-'?'reading':'unread',completed:rows[0]?.match(/✅ (\d{4}-\d{2}-\d{2})/)?.[1]||''};
}
export function setReading(text:string,path:string,state:ReadingState,day=localDay()):string{
 if(!/^Paper reports\/[^\r\n|#]+\.md$/.test(path)||path.includes('[[')||path.includes(']]')||path.split('/').some(p=>p==='..'||p==='.')||!['unread','reading','done'].includes(state)||!validDay(day))throw Error('논문 기록을 확인해 주세요.');
  readingState(text,path);const lines=text.split(/\r?\n/);const i=lines.findIndex(x=>x.includes(`[[${path}]]`));
  const next=`- [${state==='done'?'x':state==='reading'?'-':' '}] [[${path}]]${state==='done'?` ✅ ${day}`:''}`;
  if(i<0)lines.push(next);else lines[i]=next;return lines.join(text.includes('\r\n')?'\r\n':'\n');
}

/** A saved, direct completion transition; never a render or sync notification. */
export function completedToday(before:Task[],after:Task[],task:Task,selected:string,today:string):boolean {
  if(task.done||selected!==today||!task.path.startsWith('Tasks/'))return false;
  const previous=dailyTasks(before,today,today),next=dailyTasks(after,today,today);
  return previous.some(t=>t.path===task.path&&t.line===task.line&&!t.done)&&next.length>0&&next.every(t=>t.done);
}


export function graphFiles<T extends {path:string}>(files:T[]):T[]{return [...new Map(files.map(f=>[f.path,f])).values()].sort((a,b)=>a.path.localeCompare(b.path,'ko'));}
export function paperIndexText(existing:string,paths:string[]):string{
 const start='<!-- research-paper-index:start -->',end='<!-- research-paper-index:end -->';
 const sorted=[...new Set(paths)].sort((a,b)=>a.localeCompare(b,'ko'));
 for(const path of sorted)if(!path.startsWith('Paper reports/')||!path.endsWith('.md')||path.split('/').includes('..')||/[\\\r\n|#]/.test(path)||path.includes(']]'))throw Error('논문 경로를 확인해 주세요.');
 const block=start+'\n'+sorted.map(p=>'- [['+p.slice(0,-3)+']]').join('\n')+'\n'+end;
 if(!existing)return '# 논문 목록\n\n분석된 논문을 모은 탐색용 목록입니다. 선은 문서 링크를 나타냅니다.\n\n'+block+'\n';
 const a=existing.indexOf(start),b=existing.indexOf(end);
 if(a<0||b<a||existing.indexOf(start,a+1)>=0||existing.indexOf(end,b+1)>=0)throw Error('기존 논문 목록의 자동 갱신 영역을 확인해 주세요.');
 return existing.slice(0,a)+block+existing.slice(b+end.length);
}

const INTERNAL_ROOTS=new Set(['Dashboard','Inbox','Meetings','Notes','Papers','PDF','Projects','Resources','Sources','Tasks','Templates','Daily']);
export function personalFileCount(paths:string[]):number{
 return paths.filter(path=>{const parts=path.split('/');return parts.length>1&&!parts[0].startsWith('.')&&!INTERNAL_ROOTS.has(parts[0]);}).length;
}

export function planWeekStep(year:number,month:number,start:string,delta:-1|1){
 const weeks=monthWeeks(year,month),i=weeks.findIndex(w=>w.start===start),next=i+delta;
 if(i<0)throw Error('선택한 주차를 확인해 주세요.');
 if(next>=0&&next<weeks.length)return {year,month,start:weeks[next].start};
 const date=new Date(year,month+delta,1),rows=monthWeeks(date.getFullYear(),date.getMonth());
 return {year:date.getFullYear(),month:date.getMonth(),start:(delta<0?rows[rows.length-1]:rows[0]).start};
}
