import {dailyVerse,millisUntilNextDay} from './daily-verse';
import {planWeekStep,graphFiles,paperIndexText} from './dashboard-data';
import {TaskCelebration} from './task-celebration';
import {completedToday} from './dashboard-data';
import {App,ItemView,WorkspaceLeaf,MarkdownRenderChild,Notice,Platform,Plugin,TFile,setIcon} from 'obsidian';
import {GraphLayout,graphPositions,Task,READING,ReadingState,localDay,parseTasks,readingState,setReading,toggleTask,weekCounts,weekDays,taskSource,validDay,dailyTasks,dailyCounts,newDailyTask,taskStart,monthWeeks,addPlanTask} from './dashboard-data';
import {statusModel} from './status-data';
import {DashboardRecords} from './dashboard-records';
import {MEETING_VIEW} from './meeting-view';
import {ScheduleEditor,TaskEditor,MeetingCreateModal} from './record-dialogs';
import {DashboardExtras} from './dashboard-extras';
import {WorkerJobs,workerRecord,workerModel} from './library';

const DESKTOP='research-dashboard';
const PC='Dashboard/연구 홈.canvas',MOBILE='Dashboard/모바일 홈.md';
const MODULES:Record<string,[string,string,string]>={tasks:['할 일','완료는 오늘까지 · 미완료는 내일로','check-square'],weekly:['이번 주 기록','완료한 날짜를 기준으로','chart-no-axes-column'],projects:['프로젝트','프로젝트별 월간·주간 계획','folder-kanban'],connections:['연결된 노트','프로젝트·회의·논문 사이','network'],meetings:['회의록','결정과 후속 업무를 이어서','messages-square'],papers:['논문','분석과 읽기를 구분해서','book-open']};
interface Snapshot {tasks:Task[];projects:TFile[];meetings:TFile[];schedules:TFile[];papers:TFile[];paperIndex:TFile|null;reading:string;}
MODULES.calendar=['달력','날짜별 회의와 할 일 기록','calendar-days'];
MODULES.schedules=['회의 일정','예정된 만남과 준비','calendar-clock'];
MODULES.graph=['그래프뷰','실제 노트의 연결','network'];
export class ResearchDashboard {
  private celebration=new TaskCelebration();
  extras:DashboardExtras;
  records:DashboardRecords;
  refresh(){this.cache=null;this.listeners.forEach(fn=>fn());}
  selectedDay='';
  selectDay(day:string){this.selectedDay=day;this.listeners.forEach(fn=>fn());}
  private cache:Promise<Snapshot>|null=null;private listeners=new Set<()=>void>();private timer:number|undefined;
  constructor(private plugin:Plugin){
    this.records=new DashboardRecords(plugin.app,()=>this.refresh());
    plugin.registerView(DESKTOP,leaf=>new DesktopDashboard(leaf,this));
    this.extras=new DashboardExtras(plugin,()=>this.listeners.forEach(fn=>fn()));
    let lastDay=localDay();plugin.registerInterval(window.setInterval(()=>{if(localDay()!==lastDay){lastDay=localDay();this.cache=null;this.listeners.forEach(fn=>fn());}},30000));
    plugin.registerMarkdownCodeBlockProcessor('research-module',(source,el,ctx)=>{ctx.addChild(new ModuleView(el,this,source.trim()));});
    const refresh=()=>{this.cache=null;if(this.timer!==undefined)window.clearTimeout(this.timer);this.timer=window.setTimeout(()=>{this.listeners.forEach(fn=>fn());},180);};
    for(const event of ['create','modify','delete','rename'] as const)plugin.registerEvent((plugin.app.vault.on as any)(event,refresh));
    plugin.registerEvent(plugin.app.metadataCache.on('resolved',refresh));
    plugin.register(()=>{if(this.timer!==undefined)window.clearTimeout(this.timer);this.listeners.clear();this.celebration.destroy();});
    plugin.addRibbonIcon('house','연구 홈',()=>void this.openHome());
    plugin.addCommand({id:'research-home',name:'연구 홈 열기',callback:()=>void this.openHome()});
    plugin.addCommand({id:'research-mobile-home',name:'모바일 홈 열기',callback:()=>void this.openHome(true)});
    plugin.app.workspace.onLayoutReady(()=>{void (async()=>{if(!Platform.isMobile||plugin.app.vault.getAbstractFileByPath(MOBILE))await this.openHome();if(Platform.isMobile)await (plugin as any).openLibrary(false);})();});
  }
  get app(){return this.plugin.app;}
  async openLibrary(){await (this.plugin as Plugin&{openLibrary:()=>Promise<void>}).openLibrary();}
  async newSchedule(title:string,day:string,time:string){if(!validDay(day)||!/^([01]\d|2[0-3]):[0-5]\d$/.test(time))throw Error('회의 날짜와 시간을 입력해 주세요.');const safe=title.trim().replace(/[<>:"/\\|?*\x00-\x1f]/g,' ').replace(/[. ]+$/,'').slice(0,90);if(!safe)throw Error('회의 제목을 입력해 주세요.');await this.ensureFolder('Meetings/Schedule');const path=`Meetings/Schedule/${day} ${time.replace(':','')} ${safe}.md`;if(this.app.vault.getAbstractFileByPath(path))throw Error('같은 회의 일정이 있습니다.');await this.app.vault.create(path,`---\ntype: meeting_schedule\ndate: ${day}\ntime: "${time}"\ntitle: ${JSON.stringify(safe)}\n---\n# ${safe}\n\n## 관련 프로젝트·논문\n\n## 준비할 내용\n\n## 회의록\n\n`);this.cache=null;}
  async jobs(){try{const {value}=await workerRecord(this.app,true);if(!value)return [];if(value.version!==1||!Array.isArray(value.jobs))throw Error();return value.jobs;}catch{throw Error('분석 작업 기록을 읽지 못했습니다.');}}
  subscribe(fn:()=>void){this.listeners.add(fn);return ()=>this.listeners.delete(fn);}
  async openHome(mobile=Platform.isMobile){if(mobile){await this.open(MOBILE,false);return;}const leaf=this.app.workspace.getLeavesOfType(DESKTOP)[0]||this.app.workspace.getLeaf('tab');await leaf.setViewState({type:DESKTOP,active:true});this.app.workspace.setActiveLeaf(leaf,{focus:true});}
  async open(path:string,newTab=true){const file=this.app.vault.getAbstractFileByPath(path);if(!(file instanceof TFile)){new Notice('연결된 노트를 찾을 수 없습니다.');return;}
    if(newTab&&!Platform.isMobile&&file.extension==='md'&&path!==MOBILE){const leaf=[...this.app.workspace.getLeavesOfType(MEETING_VIEW),...this.app.workspace.getLeavesOfType('markdown')].find(l=>l.getRoot()===this.app.workspace.rightSplit)||this.app.workspace.getRightLeaf(false);if(!leaf)return;await leaf.openFile(file,{state:{mode:'preview'}});await this.app.workspace.revealLeaf(leaf);(this.app.workspace.rightSplit as any).setSize(Math.min(580,window.innerWidth*.44));return;}
    const existing=this.app.workspace.getLeavesOfType(file.extension==='canvas'?'canvas':'markdown').find(l=>l.getRoot()===this.app.workspace.rootSplit&&(l.view as any).file?.path===path);const leaf=existing||this.app.workspace.getLeaf('tab');await leaf.openFile(file,{state:{mode:'preview'}});this.app.workspace.setActiveLeaf(leaf,{focus:true});}
  async openMeeting(path:string){
    const file=this.app.vault.getAbstractFileByPath(path);if(!(file instanceof TFile))throw Error('회의록을 찾을 수 없습니다.');
    const leaf=Platform.isMobile?this.app.workspace.getLeaf(false):([...this.app.workspace.getLeavesOfType(MEETING_VIEW),...this.app.workspace.getLeavesOfType('markdown')].find(l=>l.getRoot()===this.app.workspace.rightSplit)||this.app.workspace.getRightLeaf(false));
    if(!leaf)throw Error('회의록을 열 공간을 찾지 못했습니다.');await leaf.setViewState({type:MEETING_VIEW,state:{file:file.path},active:true});await this.app.workspace.revealLeaf(leaf);
    if(!Platform.isMobile)(this.app.workspace.rightSplit as any).setSize(Math.min(580,window.innerWidth*.44));
  }
  private indexQueue:Promise<unknown>=Promise.resolve();
  private indexError="";
  private syncPaperIndex(papers:TFile[]):Promise<TFile|null>{
    const run=this.indexQueue.catch(()=>{}).then(async()=>{
      const path='Dashboard/논문 목록.md',file=this.app.vault.getAbstractFileByPath(path);
      if(file instanceof TFile){const current=await this.app.vault.read(file);if(paperIndexText(current,papers.map(f=>f.path))!==current)await this.app.vault.process(file,old=>paperIndexText(old,papers.map(f=>f.path)));return file;}
      if(file)throw Error('논문 목록 경로가 파일이 아닙니다.');
      await this.ensureFolder('Dashboard');return this.app.vault.create(path,paperIndexText('',papers.map(f=>f.path)));
    });this.indexQueue=run;return run.then(file=>{this.indexError="";return file;}).catch(error=>{const message=String(error);if(this.indexError!==message){this.indexError=message;new Notice("논문 목록 갱신 확인 필요: "+message);}return null;});
  }
  snapshot():Promise<Snapshot>{
    if(!this.cache)this.cache=(async()=>{const files=this.app.vault.getMarkdownFiles();const papers=files.filter(f=>f.path.startsWith('Papers/')&&this.app.metadataCache.getFileCache(f)?.frontmatter?.report_id);const paperIndex=await this.syncPaperIndex(papers);const sources=files.filter(f=>taskSource(f.path));const contents=await Promise.all(sources.map(async f=>[f.path,await this.app.vault.cachedRead(f)] as const));const reading=this.app.vault.getAbstractFileByPath(READING);return {tasks:contents.flatMap(([p,t])=>parseTasks(p,t)),projects:files.filter(f=>f.path.startsWith('Projects/')&&!f.path.startsWith('Projects/Plans/')&&this.app.metadataCache.getFileCache(f)?.frontmatter?.dashboard_example!==true).sort((a,b)=>a.basename.localeCompare(b.basename,'ko')),schedules:files.filter(f=>f.path.startsWith('Meetings/Schedule/')),meetings:files.filter(f=>f.path.startsWith('Meetings/')&&!f.path.startsWith('Meetings/Schedule/')).sort((a,b)=>b.basename.localeCompare(a.basename,'ko')),papers,paperIndex,reading:reading instanceof TFile?await this.app.vault.cachedRead(reading):''};})();
    return this.cache;
  }
  async ensureFolder(path:string){let parent='';for(const part of path.split('/')){parent=parent?parent+'/'+part:part;if(!this.app.vault.getAbstractFileByPath(parent))await this.app.vault.createFolder(parent);}}
  async append(path:string,text:string){await this.ensureFolder(path.slice(0,path.lastIndexOf('/')));const file=this.app.vault.getAbstractFileByPath(path);if(file instanceof TFile)await this.app.vault.process(file,old=>old.replace(/\s*$/,'')+'\n'+text+'\n');else await this.app.vault.create(path,text+'\n');this.cache=null;}
  async toggle(task:Task,anchor?:HTMLElement){
    const day=localDay(),selected=this.selectedDay||day;
    const file=this.app.vault.getAbstractFileByPath(task.path);if(!(file instanceof TFile))throw Error('원본 업무 노트가 없습니다.');
    const before=(await this.snapshot()).tasks;
    await this.app.vault.process(file,text=>toggleTask(text,task,day));this.cache=null;
    try { if(anchor&&localDay()===day&&this.app.loadLocalStorage('research-task-celebration-day')!==day){
      // Read the saved file directly; cachedRead can lag behind the modify event.
      const saved=await this.app.vault.read(file),all=(await this.snapshot()).tasks;
      const after=[...all.filter(t=>t.path!==task.path),...parseTasks(task.path,saved)];
      if(localDay()===day&&this.app.loadLocalStorage('research-task-celebration-day')!==day&&completedToday(before,after,task,selected,day)){
        this.app.saveLocalStorage('research-task-celebration-day',day);
        this.celebration.show(anchor);
      }
    }} catch(error){console.warn('Task saved; celebration unavailable',error);}
  }
  async reading(path:string,state:ReadingState){await this.ensureFolder('Notes');let file=this.app.vault.getAbstractFileByPath(READING);if(!file)file=await this.app.vault.create(READING,'# 독서 기록\n\n');if(!(file instanceof TFile))throw Error('독서 기록 경로가 파일이 아닙니다.');await this.app.vault.process(file,text=>setReading(text,path,state));this.cache=null;}
  async newNote(kind:'Projects'|'Meetings',title:string){const safe=title.trim().replace(/[<>:"/\\|?*\x00-\x1f]/g,' ').replace(/[. ]+$/,'').slice(0,90);if(!safe)throw Error('이름을 입력해 주세요.');await this.ensureFolder(kind);const path=`${kind}/${kind==='Meetings'?localDay()+' ':''}${safe}.md`;if(this.app.vault.getAbstractFileByPath(path))throw Error('같은 이름의 노트가 있습니다. 다른 이름을 입력해 주세요.');const text=kind==='Meetings'?`---\ntype: meeting\ntitle: ${JSON.stringify(safe)}\ndate: ${localDay()}\ncssclasses:\n  - research-meeting\n---\n# ${safe}\n\n## 참석자\n\n\n## 안건\n\n\n## 논의 내용\n\n\n## 결정 사항\n\n\n## 후속 할 일\n\n<!-- - [ ] 할 일 내용 -->\n\n`:`---\ntype: project\nstatus: active\n---\n# ${safe}\n\n## 목표\n\n## 관련 논문·회의\n\n## 업무\n\n`;await this.app.vault.create(path,text);this.cache=null;if(kind==='Meetings')await this.openMeeting(path);return path;}
  async planFile(project:TFile,month:Date){
    const key=`${month.getFullYear()}-${String(month.getMonth()+1).padStart(2,'0')}`,folder='Projects/Plans/'+project.path.slice('Projects/'.length,-3);await this.ensureFolder(folder);const path=folder+'/'+key+'.md';let file=this.app.vault.getAbstractFileByPath(path);
    if(!file)file=await this.app.vault.create(path,`---\ntype: project_weekly_plan\nproject: ${JSON.stringify(project.path)}\nmonth: ${key}\n---\n# ${project.basename} · ${key}\n\n[[${project.path}]]\n\n`+monthWeeks(month.getFullYear(),month.getMonth()).map(w=>`## ${w.heading}\n\n`).join(''));
    if(!(file instanceof TFile))throw Error('계획 경로를 확인해 주세요.');return file;
  }
  async addPlan(file:TFile,heading:string,title:string){await this.app.vault.process(file,text=>addPlanTask(text,heading,title,localDay(),crypto.randomUUID().slice(0,8)));this.cache=null;}
  async worker(){return workerModel(this.app);}
}

class ModuleView extends MarkdownRenderChild {
  private month=new Date(new Date().getFullYear(),new Date().getMonth(),1);
  private graphLayout:GraphLayout='circle';private lastSelectedDay='';private projectPath='';private selectedWeek='';private openWeeks=new Set<string>();
  private alive=false;private body!:HTMLElement;private error!:HTMLElement;private filter='all';private ticket=0;
  constructor(el:HTMLElement,private dashboard:ResearchDashboard,private kind:string){super(el);}
  onload(){this.alive=true;const saved=this.dashboard.app.loadLocalStorage('research-dashboard-view')||{};if(typeof saved.project==='string')this.projectPath=saved.project;if(['circle','hierarchy','free'].includes(saved.graph))this.graphLayout=saved.graph;const root=this.containerEl;root.empty();root.classList.add('rd-module');root.dataset.module=this.kind;
    if(this.kind==='home'){root.classList.add('rd-home');this.error=root.createEl('p',{cls:'rd-error',attr:{role:'alert'}});this.error.hidden=true;this.body=root.createDiv({cls:'rd-home-content'});this.register(this.dashboard.subscribe(()=>void this.renderHome()));void this.renderHome();this.registerInterval(window.setInterval(()=>void this.renderHome(),1800000));let midnight=0;const nextDay=()=>{window.clearTimeout(midnight);midnight=window.setTimeout(()=>{if(!this.alive)return;void this.renderHome();nextDay();},millisUntilNextDay());};nextDay();this.register(()=>window.clearTimeout(midnight));this.registerDomEvent(document,'visibilitychange',()=>{if(!document.hidden){void this.renderHome();nextDay();}});this.registerDomEvent(window,'focus',()=>{void this.renderHome();nextDay();});return;}
    const meta=MODULES[this.kind];if(!meta){root.createEl('p',{text:'알 수 없는 모듈입니다. 원본 노트의 모듈 이름을 확인해 주세요.'});return;}
    const h=root.createDiv({cls:'rd-module-heading'});const icon=h.createSpan({cls:'rd-icon',attr:{'aria-hidden':'true'}});setIcon(icon,meta[2]);const heading=h.createEl('h2');if(this.kind==='papers'){const open=heading.createEl('button',{cls:'rd-library-open',text:meta[0],attr:{type:'button','aria-label':'분석된 논문 목록 열기',title:'왼쪽 사이드바에서 논문 목록 열기'}});open.onclick=()=>void this.act(()=>this.dashboard.openLibrary());}else heading.textContent=meta[0];if(this.kind!=='papers')root.createEl('p',{text:meta[1],cls:'rd-subtitle'});else h.createDiv({cls:'rd-paper-connection'});
    if(this.kind==='graph'){const pick=h.createEl('select',{cls:'rd-graph-picker',attr:{'aria-label':'그래프 배치 형태'}});for(const [value,text] of [['circle','원형'],['hierarchy','계층형'],['free','자유 배치']])pick.createEl('option',{value,text});pick.value=this.graphLayout;pick.onchange=()=>{this.graphLayout=pick.value as GraphLayout;this.saveView();void this.render();};}
    this.error=root.createEl('p',{cls:'rd-error',attr:{role:'alert'}});this.error.hidden=true;
    this.body=root.createDiv({cls:'rd-body'});this.body.createEl('p',{text:'기록을 불러오고 있습니다.',cls:'rd-empty'});
    if(this.kind==='tasks'){h.createSpan({cls:'rd-task-day'});const today=this.button(h,'↩',async()=>this.dashboard.selectDay(''));today.classList.add('rd-task-today');today.setAttribute('aria-label','오늘 할 일로 돌아가기');today.title='오늘 할 일로 돌아가기';this.taskForm(root);}if(this.kind==='schedules')this.scheduleForm(h);
    if(this.kind==='projects'){const add=h.createEl('button',{text:'+',cls:'rd-new-project-button',attr:{type:'button','aria-label':'연구 프로젝트 추가',title:'연구 프로젝트 추가','aria-haspopup':'dialog'}});add.onclick=()=>new MeetingCreateModal(this.dashboard.app,async title=>{this.projectPath=await this.dashboard.newNote('Projects',title);this.saveView();this.dashboard.refresh();},'project').open();}if(this.kind==='meetings'){const add=h.createEl('button',{text:'새 회의록',cls:'rd-new-meeting',attr:{type:'button','aria-haspopup':'dialog'}});add.onclick=()=>new MeetingCreateModal(this.dashboard.app,async title=>{await this.dashboard.newNote('Meetings',title);this.dashboard.refresh();}).open();}
    this.register(this.dashboard.subscribe(()=>void this.render()));void this.render();
    if(this.kind==='papers')this.registerInterval(window.setInterval(()=>void this.renderWorker(),5000));
  }
  onunload(){this.alive=false;this.ticket++;this.projectResize?.disconnect();}
  private saveView(){const previous=this.dashboard.app.loadLocalStorage('research-dashboard-view')||{};this.dashboard.app.saveLocalStorage('research-dashboard-view',{...previous,...(this.kind==='projects'?{project:this.projectPath}:{graph:this.graphLayout})});}
  private async act(fn:()=>Promise<unknown>){try{this.error.hidden=true;await fn();if(this.kind==='home')await this.renderHome();else await this.render();}catch(error){this.error.textContent=error instanceof Error?error.message:'저장하지 못했습니다. 다시 시도해 주세요.';this.error.hidden=false;}}
  private button(parent:HTMLElement,label:string,fn:()=>Promise<unknown>,icon?:string){const b=parent.createEl('button',{text:label,attr:{type:'button'}});if(icon){const i=b.createSpan({cls:'rd-button-icon',attr:{'aria-hidden':'true'}});setIcon(i,icon);b.prepend(i);}b.onclick=()=>void this.act(fn);return b;}
  private link(parent:HTMLElement,file:TFile,label=file.basename){const b=parent.createEl('button',{cls:'rd-note-link',text:label,attr:{type:'button'}});b.title=label;b.onclick=()=>void this.act(()=>this.dashboard.open(file.path));return b;}
  private taskForm(root:HTMLElement){const f=root.createEl('form',{cls:'rd-add-task rd-simple-task'});const title=f.createEl('input',{type:'text',placeholder:'할 일을 적고 Enter',attr:{'aria-label':'새 할 일',maxlength:'500',required:'true'}});const submit=f.createEl('button',{text:'추가',type:'submit'});f.onsubmit=e=>{e.preventDefault();if(!title.value.trim())return;submit.disabled=true;void this.act(async()=>{await this.dashboard.append('Tasks/할 일.md',newDailyTask(title.value,this.dashboard.selectedDay||localDay(),localDay(),crypto.randomUUID().slice(0,8)));title.value='';title.focus();}).finally(()=>submit.disabled=false);};}
  private taskRow(parent:HTMLElement,t:Task){const row=parent.createDiv({cls:'rd-task-row'+(t.done?' is-done':'')});const wrap=row.createEl('label',{cls:'rd-task-check'});const check=wrap.createEl('input',{type:'checkbox',attr:{'aria-label':`${t.title} ${t.done?'완료 취소':'완료'}`}});check.checked=t.done;check.onchange=()=>{check.disabled=true;void this.act(()=>this.dashboard.toggle(t,row)).finally(()=>check.disabled=false);};const label=row.createDiv({cls:'rd-task-text'});const edit=label.createEl('button',{text:t.title,cls:'rd-task-label rd-task-edit',attr:{type:'button','aria-label':t.title+' 수정','aria-haspopup':'dialog'}});edit.onclick=()=>new TaskEditor(this.dashboard.app,this.dashboard.records,t,()=>this.dashboard.refresh()).open();if(!t.done&&taskStart(t)&&taskStart(t)<(this.dashboard.selectedDay||localDay())&&(this.dashboard.selectedDay||localDay())<=localDay()&&t.path.startsWith('Tasks/'))label.createSpan({text:'이월',cls:'rd-carry-tag'});}
  private noteForm(root:HTMLElement,kind:'Projects'|'Meetings'){{const details=root.createEl('details',{cls:'rd-new-project'});details.createEl('summary',{text:kind==='Projects'?'새 프로젝트':'새 회의록'});root=details;}const form=root.createEl('form',{cls:'rd-new-note'});const name=form.createEl('input',{type:'text',placeholder:kind==='Projects'?'새 프로젝트 이름':'새 회의 제목',attr:{'aria-label':kind==='Projects'?'새 프로젝트 이름':'새 회의 제목',required:'true',maxlength:'90'}});const b=form.createEl('button',{text:'만들기',type:'submit'});form.onsubmit=e=>{e.preventDefault();b.disabled=true;void this.act(async()=>{await this.dashboard.newNote(kind,name.value);name.value='';}).finally(()=>b.disabled=false);};}
  private empty(text:string){this.body.createEl('p',{cls:'rd-empty',text});}
  private scheduleForm(heading:HTMLElement){
    const add=heading.createEl('button',{cls:'rd-schedule-add',text:'일정 추가',attr:{type:'button','aria-label':'회의 일정 추가','aria-haspopup':'dialog'}});
    add.onclick=()=>new ScheduleEditor(this.dashboard.app,this.dashboard.records,undefined,this.dashboard.selectedDay||localDay(),async(title,day,time)=>{await this.dashboard.newSchedule(title,day,time);this.dashboard.refresh();},async record=>this.dashboard.openMeeting((await this.dashboard.records.minutes(record)).path),()=>this.dashboard.refresh()).open();
  }
  private async render(){const ticket=++this.ticket;try{const s=await this.dashboard.snapshot();if(!this.alive||ticket!==this.ticket)return;const previousScroll=this.body.scrollTop;this.body.empty();
    if(this.kind==='tasks'){
      const day=this.dashboard.selectedDay||localDay(),today=localDay(),future=day>today,label=day===today?'오늘':`${Number(day.slice(5,7))}월 ${Number(day.slice(8))}일`;
      this.containerEl.querySelector('.rd-task-day')!.textContent=`${label} (${'일월화수목금토'[new Date(day+'T12:00:00').getDay()]})`;
      (this.containerEl.querySelector('.rd-task-today') as HTMLElement).hidden=day===today;
      this.containerEl.querySelector('.rd-subtitle')!.textContent=future?`${day} · 이 날짜의 할 일을 미리 적어 두세요.`:`${day} · 완료는 해당 날짜에 보관 · 미완료는 다음날로`;
      const input=this.containerEl.querySelector('.rd-add-task input') as HTMLInputElement;input.placeholder=`${label} 할 일을 적고 Enter`;input.setAttribute('aria-label',`${day} 새 할 일`);
      const rows=dailyTasks(s.tasks,day,today);if(!rows.length)this.empty(`${label} 할 일을 한 줄씩 적어 보세요.`);for(const t of rows)this.taskRow(this.body,t);
      const info=this.body.createDiv({cls:'rd-task-summary'});info.createSpan({text:`${future?'예정':label} ${rows.length}개 · 완료 ${rows.filter(t=>t.done).length}개`});
    }else if(this.kind==='calendar'){
      const nav=this.body.createDiv({cls:'rd-calendar-nav'});this.button(nav,'이전 달',async()=>{this.month=new Date(this.month.getFullYear(),this.month.getMonth()-1,1);});nav.createEl('strong',{text:`${this.month.getFullYear()}년 ${this.month.getMonth()+1}월`});this.button(nav,'다음 달',async()=>{this.month=new Date(this.month.getFullYear(),this.month.getMonth()+1,1);});
      const grid=this.body.createDiv({cls:'rd-calendar-grid',attr:{role:'group','aria-label':'월간 할 일·회의 달력'}});for(const day of ['월','화','수','목','금','토','일'])grid.createSpan({text:day,cls:'rd-calendar-weekday'});
      const start=(this.month.getDay()+6)%7,days=new Date(this.month.getFullYear(),this.month.getMonth()+1,0).getDate();for(let i=0;i<start;i++)grid.createSpan();for(let n=1;n<=days;n++){const day=localDay(new Date(this.month.getFullYear(),this.month.getMonth(),n));const count=dailyCounts(s.tasks,day);const taskCount=day>localDay()?dailyTasks(s.tasks,day).length:count.total;const meetings=s.schedules.filter(f=>String(this.dashboard.app.metadataCache.getFileCache(f)?.frontmatter?.date)===day).length;const b=grid.createEl('button',{attr:{type:'button','aria-label':`${day} 할 일 ${taskCount}개 · 회의 ${meetings}개`,'aria-pressed':String(this.dashboard.selectedDay===day)}});b.createSpan({text:String(n),cls:'rd-day-number'});if(day===localDay())b.classList.add('rd-today');if(taskCount||meetings)b.createSpan({text:String(taskCount+meetings)+'건',cls:'rd-day-count',attr:{'aria-hidden':'true'}});b.onclick=()=>this.dashboard.selectDay(day);}
      const heading=this.containerEl.querySelector('.rd-module-heading') as HTMLElement;heading.querySelector('.rd-calendar-today')?.remove();const today=this.button(heading,'오늘',async()=>{this.month=new Date(new Date().getFullYear(),new Date().getMonth(),1);this.dashboard.selectDay('');});today.classList.add('rd-calendar-today');
    }else if(this.kind==='schedules'){
      const rows=s.schedules.map(file=>({file,fm:this.dashboard.app.metadataCache.getFileCache(file)?.frontmatter})).filter(({fm})=>this.dashboard.selectedDay?String(fm?.date)===this.dashboard.selectedDay:!validDay(String(fm?.date))||String(fm?.date)>=localDay()).sort((a,b)=>(String(a.fm?.date)+String(a.fm?.time)).localeCompare(String(b.fm?.date)+String(b.fm?.time)));
      if(!rows.length)this.empty(this.dashboard.selectedDay?'선택한 날짜에 회의가 없습니다.':'예정된 회의가 없습니다.');
      for(const {file,fm} of rows){
        const done=fm?.completed===true,title=String(fm?.title||file.basename);
        const row=this.body.createDiv({cls:'rd-schedule-row'+(done?' is-done':'')}),main=row.createDiv({cls:'rd-schedule-main'});
        const edit=main.createEl('button',{text:title,cls:'rd-note-link',attr:{type:'button','aria-haspopup':'dialog','aria-label':title+' 일정 수정'}});
        edit.onclick=()=>void this.act(async()=>{const record=await this.dashboard.records.read(file);new ScheduleEditor(this.dashboard.app,this.dashboard.records,record,record.day,async()=>{},async r=>this.dashboard.openMeeting((await this.dashboard.records.minutes(r)).path),()=>this.dashboard.refresh()).open();});
        const action=done?'완료 취소':'완료로 표시';
        const complete=main.createEl('button',{cls:'rd-schedule-complete',attr:{type:'button','aria-pressed':String(done),'aria-label':title+' '+action,title:action}});
        complete.createSpan({text:done?'✅':'○',attr:{'aria-hidden':'true'}});
        complete.onclick=()=>{complete.disabled=true;void this.act(async()=>{const record=await this.dashboard.records.read(file);await this.dashboard.records.setCompleted(record,!done);}).finally(()=>complete.disabled=false);};
        row.createEl('p',{text:validDay(String(fm?.date))?`${fm?.date} · ${fm?.time||'시간 미정'}`:'일정 노트의 날짜를 확인해 주세요.',cls:'rd-small'});
      }
    }else if(this.kind==='weekly'){
      const days=weekDays(),counts=days.map(day=>dailyCounts(s.tasks,day)),max=Math.max(1,...counts.map(c=>c.total));const chart=this.body.createDiv({cls:'rd-daily-chart',attr:{'aria-label':'요일별 완료·이월·남은 할 일'}});
      for(let i=0;i<7;i++){const c=counts[i],col=chart.createDiv({cls:'rd-daily-column'});col.dataset.day=days[i];col.title=`${days[i]} · 완료 ${c.done} · 이월 ${c.carried} · 남음 ${c.pending}`;col.setAttribute('aria-label',col.title);col.createSpan({text:String(c.done),cls:'rd-complete-number'});const track=col.createDiv({cls:'rd-daily-track',attr:{'aria-hidden':'true'}});for(const [key,value] of [['done',c.done],['carried',c.carried],['pending',c.pending]] as const)track.createDiv({cls:'rd-daily-fill '+key,attr:{style:`height:${value/max*100}%`,'data-count':String(value)}});col.createSpan({text:['월','화','수','목','금','토','일'][i]});}
      const total=counts.reduce((n,c)=>n+c.done,0),carried=counts.reduce((n,c)=>n+c.carried,0),legend=this.body.createDiv({cls:'rd-week-legend'});for(const [key,label,value] of [['done','완료',total],['carried','이월',carried],['pending','남음',dailyCounts(s.tasks,localDay()).pending]])legend.createSpan({cls:'rd-legend-item '+key,text:`${label} ${value}`});legend.title='요일 위 숫자는 완료 수 · 막대는 이번 주 가장 많은 업무 수 기준 · 이월은 각 날짜의 미완료 수';
    }else if(this.kind==='projects'){
      await this.renderProjects(s,ticket);
    }else if(this.kind==='graph'){
      this.renderGraph(s);
    }else if(this.kind==='meetings'){
      if(!s.meetings.length)this.empty('회의록이 아직 없습니다.');
      for(const m of s.meetings){const row=this.body.createDiv({cls:'rd-meeting-row'});const link=row.createEl('button',{cls:'rd-note-link',text:String(this.dashboard.app.metadataCache.getFileCache(m)?.frontmatter?.title||m.basename),attr:{type:'button'}});link.onclick=()=>void this.act(()=>this.dashboard.openMeeting(m.path));const tasks=s.tasks.filter(t=>t.path===m.path);row.createEl('p',{text:tasks.length?`후속 업무 ${tasks.filter(t=>!t.done).length}개 남음`:'후속 업무가 아직 없습니다.',cls:'rd-small'});}
    }else if(this.kind==='connections'){
      const nodes=new Set([...s.projects,...s.meetings,...s.papers].map(f=>f.path));const edges:Array<[string,string]>=[];for(const [from,to] of Object.entries(this.dashboard.app.metadataCache.resolvedLinks)){if(!nodes.has(from))continue;for(const target of Object.keys(to))if(nodes.has(target)&&from!==target)edges.push([from,target]);}
      if(!edges.length)this.empty('프로젝트·회의록에 [[논문 이름]]을 연결하면 여기에 모입니다.');
      for(const [from,to] of edges.slice(0,6)){const row=this.body.createDiv({cls:'rd-connection-row'});for(const path of [from,to]){const f=this.dashboard.app.vault.getAbstractFileByPath(path);if(f instanceof TFile)this.link(row,f);}row.setAttribute('aria-label',`${from}에서 ${to}로 연결`);}
      this.button(this.body,'그래프 펼치기',async()=>{await this.dashboard.app.workspace.getLeaf('split').setViewState({type:'graph',active:true});},'network');
    }else if(this.kind==='papers'){
      if(!s.papers.length)this.empty('완성된 리포트가 등록되면 이곳에서 읽을 수 있습니다.');
      for(const p of s.papers){const row=this.body.createDiv({cls:'rd-paper-row'});const fm=this.dashboard.app.metadataCache.getFileCache(p)?.frontmatter;row.dataset.reportId=String(fm?.report_id||'');this.link(row,p,String(fm?.library_title||p.basename));const analysis=row.createEl('button',{cls:'rd-paper-analysis',text:'상태 확인',type:'button'});analysis.onclick=()=>new WorkerJobs(this.dashboard.app).open();}
      await this.renderWorker();
    }
    this.body.scrollTop=previousScroll;
  }catch(error){if(this.alive){this.error.textContent=error instanceof Error?error.message:'기록을 불러오지 못했습니다.';this.error.hidden=false;}}}
  private projectResize?:ResizeObserver;
  private async renderProjects(s:Snapshot,ticket:number){
    if(!s.projects.some(p=>p.path===this.projectPath))this.projectPath=s.projects[0]?.path||'';
    const heading=this.containerEl.querySelector('.rd-module-heading')!;this.projectResize?.disconnect();heading.querySelector('.rd-project-choice')?.remove();heading.querySelector('.rd-project-picker')?.remove();
    const choice=heading.createDiv({cls:'rd-project-choice'});heading.insertBefore(choice,heading.querySelector('.rd-new-project-button'));
    const label=choice.createDiv({cls:'rd-project-name',attr:{'aria-hidden':'true'}}),text=label.createSpan({text:s.projects.find(p=>p.path===this.projectPath)?.basename||'연구 선택'}),chevron=choice.createSpan({cls:'rd-project-chevron',attr:{'aria-hidden':'true'}});setIcon(chevron,'chevron-down');
    const pick=choice.createEl('select',{cls:'rd-project-picker',attr:{'aria-label':'연구 프로젝트 선택'}});for(const project of s.projects)pick.createEl('option',{value:project.path,text:project.basename});if(!s.projects.length){pick.createEl('option',{value:'',text:'연구 프로젝트를 추가해 주세요'});pick.disabled=true;}pick.value=this.projectPath;pick.onchange=()=>{this.projectPath=pick.value;this.saveView();this.body.scrollTop=0;void this.render();};choice.title=text.textContent||'';
    const fit=()=>{const distance=Math.max(0,text.scrollWidth-label.clientWidth);choice.classList.toggle('is-long',distance>3);choice.style.setProperty('--rd-name-travel',`-${distance}px`);choice.style.setProperty('--rd-name-duration',`${Math.max(7,distance/18+4)}s`);};this.projectResize=new ResizeObserver(fit);this.projectResize.observe(choice);requestAnimationFrame(fit);
    const weeks=monthWeeks(this.month.getFullYear(),this.month.getMonth());if(!weeks.some(w=>w.start===this.selectedWeek))this.selectedWeek=(weeks.find(w=>w.start<=localDay()&&localDay()<=w.end)||weeks[0]).start;
    const nav=this.body.createDiv({cls:'rd-plan-period'}),step=async(delta:-1|1)=>{const next=planWeekStep(this.month.getFullYear(),this.month.getMonth(),this.selectedWeek,delta);this.month=new Date(next.year,next.month,1);this.selectedWeek=next.start;};
    this.button(nav,'‹',()=>step(-1)).setAttribute('aria-label','이전 주');const select=nav.createEl('select',{attr:{'aria-label':'월별 주차'}});for(const w of weeks)select.createEl('option',{value:w.start,text:`${this.month.getMonth()+1}월 ${w.heading.split(' · ')[0]} · ${w.start.slice(5)}–${w.end.slice(5)}`});select.value=this.selectedWeek;select.onchange=()=>{this.selectedWeek=select.value;void this.render();};this.button(nav,'›',()=>step(1)).setAttribute('aria-label','다음 주');
    if(!s.projects.length){this.empty('오른쪽 +로 진행 중인 연구를 등록하면, 선택한 주에 계획을 적을 수 있습니다.');return;}
    const project=s.projects.find(p=>p.path===this.projectPath)!,file=await this.dashboard.planFile(project,this.month),content=await this.dashboard.app.vault.read(file);if(!this.alive||ticket!==this.ticket)return;
    const w=weeks.find(w=>w.start===this.selectedWeek)!,lines=content.split(/\r?\n/),start=lines.indexOf('## '+w.heading);if(start<0||lines.filter(l=>l==='## '+w.heading).length!==1){this.empty('주차 제목이 변경되었습니다. 월간 계획 원본을 확인해 주세요.');return;}const end=lines.findIndex((l,i)=>i>start&&l.startsWith('## ')),rows=parseTasks(file.path,content).filter(t=>t.line>start&&(end<0||t.line<end));
    const list=this.body.createDiv({cls:'rd-plan-items'});if(!rows.length){list.classList.add('is-empty');list.createEl('p',{cls:'rd-plan-empty',text:'이번 주 계획을 추가해 보세요.'});}for(const task of rows)this.taskRow(list,task);
    const form=this.body.createEl('form',{cls:'rd-simple-task rd-plan-input'}),input=form.createEl('input',{type:'text',placeholder:'이번 주 할 일',attr:{'aria-label':w.heading+' 할 일',maxlength:'500',required:'true'}}),add=form.createEl('button',{type:'submit',text:'추가'});form.onsubmit=e=>{e.preventDefault();add.disabled=true;void this.act(()=>this.dashboard.addPlan(file,w.heading,input.value)).finally(()=>add.disabled=false);};
  }
  private graphSelected='';
  private renderGraph(s:Snapshot){
    const nodes=graphFiles([...(s.paperIndex?[s.paperIndex]:[]),...s.projects,...s.meetings,...s.papers]),paths=new Set(nodes.map(f=>f.path));
    if(!nodes.length){this.empty('논문·프로젝트·회의록을 등록하면 연결이 표시됩니다.');return;}
    const edges:Array<[string,string]>=[];for(const [from,targets] of Object.entries(this.dashboard.app.metadataCache.resolvedLinks))if(paths.has(from))for(const to of Object.keys(targets))if(paths.has(to)&&from!==to)edges.push([from,to]);
    const head=this.containerEl.querySelector('.rd-module-heading')!;
    if(!head.querySelector('.rd-network-expand')){const expand=head.createEl('button',{cls:'rd-network-expand',attr:{type:'button','aria-label':'전체 그래프 크게 열기',title:'전체 그래프 크게 열기'}});setIcon(expand,'expand');expand.onclick=()=>void this.act(async()=>{const leaf=this.dashboard.app.workspace.getRightLeaf(false);if(leaf){await leaf.setViewState({type:'graph',active:true});await this.dashboard.app.workspace.revealLeaf(leaf);(this.dashboard.app.workspace.rightSplit as any).setSize(Math.min(680,window.innerWidth*.5));}});}
    const map=this.body.createDiv({cls:'rd-network-map',attr:{role:'group','aria-label':`논문 ${s.papers.length}편을 포함한 ${nodes.length}개 문서 연결`}});map.dataset.nodes=String(nodes.length);map.dataset.layout=this.graphLayout;
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 300 150');svg.setAttribute('preserveAspectRatio','none');svg.setAttribute('aria-hidden','true');map.append(svg);
    const hub=s.paperIndex?.path;const pos=graphPositions(nodes.map(f=>f.path),edges,this.graphLayout);
    if(this.graphLayout==='circle'&&hub){const ring=graphPositions(nodes.filter(f=>f.path!==hub).map(f=>f.path),edges,'circle');for(const [key,value] of ring)pos.set(key,value);pos.set(hub,{x:150,y:75});}
    for(const [from,to] of edges){const a=pos.get(from)!,b=pos.get(to)!;const line=document.createElementNS(svg.namespaceURI,'path');line.setAttribute('d',`M ${a.x} ${a.y} Q ${(a.x+b.x)/2} ${(a.y+b.y)/2-7} ${b.x} ${b.y}`);line.setAttribute('data-from',from);line.setAttribute('data-to',to);svg.append(line);}
    const caption=this.body.createEl('button',{cls:'rd-network-caption',attr:{type:'button'}}),kind=caption.createSpan({cls:'rd-network-kind'}),title=caption.createSpan({cls:'rd-network-title'}),arrow=caption.createSpan({cls:'rd-network-arrow',attr:{'aria-hidden':'true'}});setIcon(arrow,'arrow-up-right');
    const select=(file:TFile)=>{this.graphSelected=file.path;const isHub=file.path===hub;kind.textContent=isHub?`논문 ${s.papers.length}편 · 연결된 문서 ${nodes.length}개`:file.path.startsWith('Papers/')?'논문':file.path.startsWith('Projects/')?'프로젝트':'회의록';title.textContent=isHub?'분석한 논문 모두 보기':String(this.dashboard.app.metadataCache.getFileCache(file)?.frontmatter?.library_title||file.basename);caption.title=title.textContent;caption.setAttribute('aria-label',title.textContent+' 열기');caption.onclick=()=>void this.act(()=>this.dashboard.open(file.path));for(const node of Array.from(map.querySelectorAll<HTMLElement>('.rd-network-node')))node.setAttribute('aria-pressed',String(node.dataset.path===file.path));for(const line of Array.from(svg.querySelectorAll('path')))line.classList.toggle('is-active',line.dataset.from===file.path||line.dataset.to===file.path);};
    for(const file of nodes){const point=pos.get(file.path)!,isHub=file.path===hub,type=isHub?'hub':file.path.startsWith('Papers/')?'paper':file.path.startsWith('Projects/')?'project':'meeting';const node=map.createEl('button',{cls:'rd-network-node is-'+type,attr:{type:'button','aria-label':file.basename,title:file.basename,'aria-pressed':'false'}});node.dataset.path=file.path;node.style.left=point.x/3+'%';node.style.top=point.y/1.5+'%';const dot=node.createSpan({cls:'rd-network-dot',attr:{'aria-hidden':'true'}});if(isHub)setIcon(dot,'book-open');node.onclick=()=>select(file);node.onfocus=()=>select(file);node.onmouseenter=()=>select(file);}
    select(nodes.find(f=>f.path===this.graphSelected)||s.paperIndex||nodes[0]);
  }
  private async renderHome(){const ticket=++this.ticket;try{const counts=await this.dashboard.extras.activity();if(!this.alive||ticket!==this.ticket)return;this.body.empty();const left=this.body.createDiv({cls:'rd-greeting'});const today=new Date();left.createEl('h1',{text:today.toLocaleDateString('ko-KR',{month:'long',day:'numeric',weekday:'long'})});const weather=left.createDiv({cls:'rd-weather',text:'서울 · 날씨 확인 중'});void this.dashboard.extras.weather().then(text=>{if(weather.isConnected)weather.textContent=text;});const controls=left.createDiv({cls:'rd-weather-actions'});this.button(controls,'현재 위치',async()=>{weather.textContent=await this.dashboard.extras.useLocation();});this.button(controls,'서울',async()=>{weather.textContent=await this.dashboard.extras.seoul();});const source=controls.createEl('a',{text:'Open-Meteo',href:'https://open-meteo.com/',attr:{target:'_blank',rel:'noopener'}});
    const verse=dailyVerse();left.createEl('p',{cls:'rd-verse',text:verse.text});left.createEl('a',{cls:'rd-verse-source',text:verse.ref+' · 개역개정',href:verse.url,attr:{target:'_blank',rel:'noopener',title:'성경전서 개역개정판 © 대한성서공회 1998'}});
    const right=this.body.createDiv({cls:'rd-activity'}),keys=Object.keys(counts).filter(d=>counts[d]>0).sort(),day=localDay();let streak=0,cursor=new Date(day+'T12:00:00');if(!counts[day])cursor.setDate(cursor.getDate()-1);while(counts[localDay(cursor)]){streak++;cursor.setDate(cursor.getDate()-1);}
    const stats=right.createDiv({cls:'rd-activity-stats'});for(const [value,label] of [[counts[day]||0,'오늘 변경한 노트'],[keys.length,'기록한 날'],[streak,'연속 기록일']]){const stat=stats.createDiv();stat.createEl('strong',{text:String(value)});stat.createSpan({text:String(label)});}
    const grid=right.createDiv({cls:'rd-activity-grid',attr:{role:'img','aria-label':`최근 1년 노트 변경 기록. 기록한 날 ${keys.length}일, 연속 ${streak}일.`}});const start=new Date(today.getFullYear(),today.getMonth(),today.getDate()-364,12);start.setDate(start.getDate()-start.getDay());for(let i=0;i<371;i++){const d=new Date(start);d.setDate(d.getDate()+i);const key=localDay(d),n=counts[key]||0,cell=grid.createSpan({cls:'rd-activity-cell'});cell.dataset.level=String(Math.min(4,n));cell.title=`${key} · ${n}개 노트 변경`;if(key>day)cell.style.visibility='hidden';}
    right.createEl('p',{cls:'rd-small',text:keys.length?`${keys[0]}부터 관찰 · 같은 날 같은 노트는 한 번만 셉니다.`:'측정을 시작했습니다. 할 일·계획·회의록·메모의 실제 변경부터 기록합니다.'});
  }catch(error){if(this.alive){this.error.hidden=false;this.error.textContent=String(error);}}}
  private async renderWorker(){const e=this.containerEl.querySelector<HTMLElement>('.rd-paper-connection');if(!e)return;const status=await this.dashboard.worker();if(!this.alive||!e.isConnected)return;const signature=JSON.stringify(status);if(e.dataset.signature!==signature){e.dataset.signature=signature;e.empty();e.dataset.connection=status.connection;const b=e.createEl('button',{cls:'rr-connection-line',type:'button'});b.createSpan({cls:'rr-connection-dot',attr:{'aria-hidden':'true'}});b.createSpan({text:status.connection==='snapshot'?'분석 기록':status.label});b.title=status.detail;b.setAttribute('aria-label',status.label+'. '+status.detail);b.onclick=()=>new WorkerJobs(this.dashboard.app).open();}
    let jobs:any[];try{jobs=await this.dashboard.jobs();}catch{jobs=[];for(const b of Array.from(this.body.querySelectorAll<HTMLElement>('.rd-paper-analysis')))b.textContent='상태 확인 필요';return;}
    const active=jobs.filter(j=>j.state==='queued').length;
    let stage=e.querySelector<HTMLElement>('.rd-paper-stage');if(!stage)stage=e.createDiv({cls:'rd-paper-stage'});stage.replaceChildren();
    if(status.running){const dots=stage.createSpan({cls:'rr-working-dots',attr:{'aria-hidden':'true'}});for(let i=0;i<3;i++)dots.createSpan();}
    stage.createSpan({text:[status.stage,active?`대기 ${active}건`:''].filter(Boolean).join(' · ')});stage.title=status.detail;
    for(const row of Array.from(this.body.querySelectorAll<HTMLElement>('.rd-paper-row'))){const job=jobs.filter(j=>j.report_id===row.dataset.reportId).pop();const b=row.querySelector<HTMLElement>('.rd-paper-analysis');if(!b)continue;const labels:Record<string,string>={running:'분석 중',failed:'분석 오류',interrupted:'분석 중단',review:'검토 대기',prepared:'자료 준비',complete:'분석 완료',queued:'분석 대기'};b.classList.toggle('is-running',job?.state==='running'&&status.connection==='connected');b.textContent=job?(labels[job.state]||'상태 확인 필요'):'리포트 있음';b.title=job?.message||'분석 작업 내역 열기';}
  }
}

class DesktopDashboard extends ItemView {
  constructor(leaf:WorkspaceLeaf,private dashboard:ResearchDashboard){super(leaf);}
  getViewType(){return DESKTOP;}
  getDisplayText(){return '대시보드';}
  getIcon(){return 'house';}
  async onOpen(){this.contentEl.empty();this.contentEl.classList.add('rd-desktop');const grid=this.contentEl.createDiv({cls:'rd-desktop-grid'});for(const kind of ['home','tasks','weekly','projects','graph','schedules','meetings','calendar','papers']){let parent:HTMLElement=grid;if(['schedules','meetings','papers'].includes(kind))parent=grid.querySelector<HTMLElement>('.rd-desktop-right')||grid.createDiv({cls:'rd-desktop-right'});const card=parent.createDiv({cls:'rd-desktop-card',attr:{'data-card':kind}});this.addChild(new ModuleView(card,this.dashboard,kind));}}
  async onClose(){this.contentEl.empty();}
}

