import {App,TFile,parseYaml,stringifyYaml} from 'obsidian';
import {Task,validDay,localDay} from './dashboard-data';

const dates=/(?:📅|✅|➕|⏳)\s*\d{4}-\d{2}-\d{2}/g;
export function taskEditableText(task:Task){return task.raw.replace(/^\s*[-*+] \[[ xX]\]\s+/,'').replace(dates,'').replace(/\s*\^[\w-]+\s*$/,'').trim();}
export function changeTask(text:string,task:Task,value:string|null):string{
  const sep=text.includes('\r\n')?'\r\n':'\n',lines=text.split(/\r?\n/);
  if(lines[task.line]!==task.raw)throw Error('원본이 변경되었습니다. 창을 닫고 다시 선택해 주세요.');
  if(value===null){lines.splice(task.line,1);return lines.join(sep);}
  const title=value.trim();if(!title||title.length>500||/[\r\n]/.test(title)||/(?:📅|✅|➕|⏳)\s*\d{4}-\d{2}-\d{2}|\^[\w-]+\s*$/.test(title))throw Error('할 일 내용을 한 줄로 입력해 주세요. 날짜와 식별자는 자동으로 유지됩니다.');
  if(title===taskEditableText(task))return text;
  const prefix=task.raw.match(/^\s*[-*+] \[[ xX]\]\s+/)?.[0];if(!prefix)throw Error('할 일 형식을 확인해 주세요.');
  const metadata=task.raw.match(dates)||[],anchor=task.raw.match(/\s+(\^[\w-]+)\s*$/)?.[1];
  lines[task.line]=prefix+[title,...metadata,...(anchor?[anchor]:[])].join(' ');return lines.join(sep);
}
export interface ScheduleRecord {file:TFile;raw:string;title:string;day:string;time:string;minutes:string;completed:boolean;}
function parts(raw:string){const match=raw.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/);if(!match)throw Error('일정 속성을 읽지 못했습니다. 원본 노트를 확인해 주세요.');const fm=parseYaml(match[1]);if(!fm||typeof fm!=='object'||Array.isArray(fm))throw Error('일정 속성 형식이 잘못되었습니다.');return {fm,body:raw.slice(match[0].length),sep:raw.includes('\r\n')?'\r\n':'\n'};}
function rewritten(raw:string,patch:Record<string,unknown>){const {fm,body,sep}=parts(raw);return '---'+sep+stringifyYaml({...fm,...patch}).trimEnd().replace(/\r?\n/g,sep)+sep+'---'+sep+body;}
function cleanTitle(value:string){const title=value.trim().replace(/[<>:"/\\|?*\x00-\x1f]/g,' ').replace(/[. ]+$/,'').slice(0,90);if(!title)throw Error('회의 제목을 입력해 주세요.');return title;}
export class DashboardRecords {
  constructor(private app:App,private changed:()=>void){}
  hasMinutes(record:ScheduleRecord):boolean{return !!record.minutes&&this.app.vault.getAbstractFileByPath(record.minutes) instanceof TFile;}
  async read(file:TFile):Promise<ScheduleRecord>{const raw=await this.app.vault.read(file),{fm}=parts(raw);return {file,raw,title:String(fm.title||file.basename),day:String(fm.date||''),time:String(fm.time||''),minutes:typeof fm.minutes==='string'?fm.minutes:'',completed:fm.completed===true};}
  async setCompleted(record:ScheduleRecord,completed:boolean){
    await this.app.vault.process(record.file,raw=>{if(raw!==record.raw)throw Error('일정이 변경되었습니다. 다시 선택해 주세요.');return rewritten(raw,{completed,completed_date:completed?localDay():''});});
    this.changed();return this.read(record.file);
  }
  async edit(record:ScheduleRecord,title:string,day:string,time:string){
    title=cleanTitle(title);if(!validDay(day)||!/^([01]\d|2[0-3]):[0-5]\d$/.test(time))throw Error('회의 날짜와 시간을 확인해 주세요.');
    await this.app.vault.process(record.file,raw=>{if(raw!==record.raw)throw Error('다른 곳에서 일정이 변경되었습니다. 창을 닫고 다시 열어 주세요.');return rewritten(raw,{title,date:day,time});});this.changed();return this.read(record.file);
  }
  async removeSchedule(record:ScheduleRecord){if(await this.app.vault.read(record.file)!==record.raw)throw Error('일정이 변경되었습니다. 창을 닫고 다시 열어 주세요.');await this.app.fileManager.trashFile(record.file);this.changed();}
  async editTask(task:Task,value:string|null){const file=this.app.vault.getAbstractFileByPath(task.path);if(!(file instanceof TFile))throw Error('할 일 원본이 없습니다.');await this.app.vault.process(file,text=>changeTask(text,task,value));this.changed();}
  async minutes(record:ScheduleRecord):Promise<TFile>{
    // Re-read the schedule so existing minutes are reused across devices and reopens.
    record=await this.read(record.file);
    if(record.minutes){const existing=this.app.vault.getAbstractFileByPath(record.minutes);if(existing instanceof TFile)return existing;}
    // A deleted note leaves its path in the schedule. Recreate through the same
    // guarded creation flow and replace that stale link only after success.
    const folder='Meetings/Minutes';if(!this.app.vault.getAbstractFileByPath(folder))await this.app.vault.createFolder(folder);
    const path=`${folder}/${record.file.basename}.md`;
    // A concurrent attempt may already have created the note but not linked it yet.
    let file=this.app.vault.getAbstractFileByPath(path);
    if(file){if(!(file instanceof TFile))throw Error('회의록 경로를 확인해 주세요.');const {fm}=parts(await this.app.vault.read(file));if(fm.schedule!==record.file.path)throw Error('같은 이름의 회의록이 있습니다. 기존 내용을 보호하기 위해 연결을 중단했습니다.');}
    else file=await this.app.vault.create(path,`---\ntype: meeting\ntitle: ${JSON.stringify(record.title)}\ndate: ${record.day}\ntime: ${JSON.stringify(record.time)}\nschedule: ${JSON.stringify(record.file.path)}\ncssclasses:\n  - research-meeting\n---\n# ${record.title}\n\n${record.day} · ${record.time}\n\n## 참석자\n\n\n## 안건\n\n\n## 논의 내용\n\n\n## 결정 사항\n\n\n## 후속 할 일\n\n<!-- - [ ] 할 일 내용 -->\n\n`);
    const minutes=file as TFile;
    await this.app.vault.process(record.file,raw=>{if(raw!==record.raw)throw Error('일정이 변경되었습니다. 생성된 회의록은 회의록 목록에 보관했습니다. 다시 열어 연결해 주세요.');return rewritten(raw,{minutes:minutes.path});});
    this.changed();return minutes;
  }
}
