import {ItemView,Notice,Platform,Plugin,TFile,WorkspaceLeaf} from 'obsidian';
declare const require:(name:string)=>any;
import {CONTROL,PDF_PATH,UUID,RunRequest,RunStatus,parseRequest,parseStatus,statusFor,STATES,TERMINAL} from './remote-data';
import {RemoteReceiver,RemoteStore} from './remote-receiver';
const VIEW='paper-analysis-control';
interface LocalConfig {version:1;enabled:boolean;thread:string;codex:string;runbook:string;workspace:string;}
export class PaperRemoteControl {
  private receiver:RemoteReceiver|null=null;private submitBusy=false;private stopped=false;private lastPull=0;
  private lastError='';
  constructor(private plugin:Plugin) {
    plugin.registerView(VIEW,leaf=>new ControlView(leaf,this));
    plugin.addCommand({id:'paper-analysis-control',name:'논문 분석 시작 · 상태 보기',callback:()=>{void this.open();}});
    plugin.addRibbonIcon('circle-play','논문 분석 시작 · 상태 보기',()=>{void this.open();});
    plugin.registerObsidianProtocolHandler('paper-analysis',params=>{
      void this.open().then(()=>params.action==='sync'?this.sync():undefined).catch(e=>this.error(e));
    });
    plugin.register(()=>{this.stopped=true;});
    plugin.app.workspace.onLayoutReady(()=>{void this.setupDesktop();});
    plugin.registerInterval(window.setInterval(()=>{void this.tick();},15000));
  }
  private error(e:unknown):void {this.lastError=e instanceof Error?e.message:'요청 처리 중 문제가 발생했습니다.';new Notice(this.lastError);void this.refresh();}
  async ensure():Promise<void> {const a=this.plugin.app.vault.adapter;for(const p of [CONTROL,`${CONTROL}/requests`,`${CONTROL}/status`])if(!await a.exists(p))await a.mkdir(p);}
  async requests():Promise<Array<{request:RunRequest;status:RunStatus}>> {
    const a=this.plugin.app.vault.adapter;if(!await a.exists(`${CONTROL}/requests`))return [];
    const files=(await a.list(`${CONTROL}/requests`)).files;
    if(files.length>1000)throw Error('요청 기록이 너무 많습니다. PC에서 확인해 주세요.');
    const items:Array<{request:RunRequest;status:RunStatus}>=[];
    for(const f of files){try{
      const stat=await a.stat(f);if(!stat||stat.size>2048)continue;
      const request=parseRequest(await a.read(f),f.split('/').pop());
      const sp=`${CONTROL}/status/${request.id}.json`;
      const ss=await a.stat(sp);
      let status=statusFor(request,'pending','요청이 이 기기에 저장되었습니다. Git 동기화 후 PC에서 접수합니다.');
      if(ss){try{if(ss.size>8192)throw Error();status=parseStatus(await a.read(sp),request.id);}catch{status=statusFor(request,'blocked','동기화된 상태 파일을 읽지 못했습니다. 중복 요청을 막기 위해 PC 확인을 기다립니다.');}}
      if(!ss)status.updatedAt=request.createdAt;
      items.push({request,status});
    }catch{/* Foreign or partially synchronized JSON is not executable input. */}}
    return items.sort((a,b)=>b.request.createdAt.localeCompare(a.request.createdAt));
  }
  async submit(action:'analyze-inbox'|'diagnostic'='analyze-inbox'):Promise<void> {
    if(this.submitBusy)return;this.submitBusy=true;
    try {
      await this.ensure();const pending=(await this.requests()).find(x=>!TERMINAL.has(x.status.state));
      if(pending){new Notice('기존 실행 요청이 남아 있습니다. 상태를 확인해 주세요.');await this.sync();return;}
      const r:RunRequest={version:1,id:crypto.randomUUID(),createdAt:new Date().toISOString(),action,maxPapers:action==='diagnostic'?1:10};
      const path=`${CONTROL}/requests/${r.id}.json`,a=this.plugin.app.vault.adapter;
      await a.write(path,JSON.stringify(r,null,2));parseRequest(await a.read(path),r.id+'.json');
      new Notice('요청을 저장했습니다. Git 동기화가 완료될 때까지 Obsidian을 열어 두세요.');
      await this.sync();await this.tick();
    }catch(e){this.error(e);}finally{this.submitBusy=false;await this.refresh();}
  }
  async submitPdf(file:TFile):Promise<void> {
    if(this.submitBusy)return;
    if(!PDF_PATH.test(file.path)||file.path.split('/').some(p=>p==='.'||p==='..'))throw Error('PDF 폴더의 파일만 분석 요청할 수 있습니다.');
    if(file.stat.size>95*1024*1024)throw Error('95MB를 넘는 PDF는 Git 동기화 전에 크기를 확인해 주세요.');
    this.submitBusy=true;
    try{
      const digest=await crypto.subtle.digest('SHA-256',await this.plugin.app.vault.readBinary(file));
      const sha256=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join('');
      const current=this.plugin.app.vault.getAbstractFileByPath(file.path);
      if(!(current instanceof TFile)||current.stat.mtime!==file.stat.mtime||current.stat.size!==file.stat.size)throw Error('PDF가 변경되었습니다. 다시 눌러 주세요.');
      await this.ensure();
      const prior=(await this.requests()).find(x=>x.request.version===2&&x.request.path===file.path&&x.request.sha256===sha256&&!['cancelled','empty'].includes(x.status.state));
      if(prior){new Notice(`이미 요청한 PDF입니다 · ${STATES[prior.status.state]}`);return;}
      const r:RunRequest={version:2,id:crypto.randomUUID(),createdAt:new Date().toISOString(),action:'analyze-pdf',path:file.path,sha256};
      const path=`${CONTROL}/requests/${r.id}.json`,a=this.plugin.app.vault.adapter;
      await a.write(path,JSON.stringify(r,null,2));parseRequest(await a.read(path),r.id+'.json');
      new Notice('이 PDF의 분석 요청을 저장했습니다. Git 전송과 PC 접수 상태를 확인해 주세요.');
      await this.sync();await this.tick();
    }catch(e){this.error(e);throw e;}finally{this.submitBusy=false;await this.refresh();}
  }
  async sync():Promise<void> {
    const commands=(this.plugin.app as any).commands;
    if(!commands?.commands?.['obsidian-git:push']){new Notice('요청은 저장됐습니다. GitSync에서 동기화하면 PC에 전달됩니다.');return;}
    // Command dispatch is not proof that push succeeded; remote receipt is authoritative.
    commands.executeCommandById('obsidian-git:push');
    this.lastError='';await this.refresh();
  }
  async open():Promise<void> {
    const app=this.plugin.app;let leaf=app.workspace.getLeavesOfType(VIEW)[0];
    if(!leaf){leaf=app.workspace.getLeaf('tab');await leaf.setViewState({type:VIEW,active:true});}
    await app.workspace.revealLeaf(leaf);await this.refresh();
  }
  async refresh():Promise<void> {for(const leaf of this.plugin.app.workspace.getLeavesOfType(VIEW))if(leaf.view instanceof ControlView)await leaf.view.render();}
  get errorText():string{return this.lastError;}
  private async setupDesktop():Promise<void> {
    if(!Platform.isDesktopApp||!Platform.isWin)return;
    try {
      const fs=require('fs'),path=require('path'),os=require('os');
      const root=path.join(os.homedir(),'Documents','Codex','Paper Analyzer');
      const configPath=path.join(root,'mobile-control.json');if(!fs.existsSync(configPath))return;
      const c:LocalConfig=JSON.parse(fs.readFileSync(configPath,'utf8'));
      if(!c.enabled)return;
      if(c.version!==1||!UUID.test(c.thread)||![c.codex,c.runbook,c.workspace].every(p=>typeof p==='string'&&path.isAbsolute(p))||![c.runbook,c.workspace].every(p=>fs.existsSync(p)))throw Error('PC 분석 연결 설정을 확인해 주세요.');
      let codexExecutable=c.codex;
      if(!fs.existsSync(codexExecutable)){
        const bin=path.join(os.homedir(),'AppData','Local','OpenAI','Codex','bin');
        const configured=path.resolve(c.codex).toLowerCase();
        if(path.basename(configured)!=='codex.exe'||!configured.startsWith(bin.toLowerCase()+path.sep))throw Error('PC 분석 실행 파일을 찾지 못했습니다.');
        const candidates=fs.existsSync(bin)?fs.readdirSync(bin,{withFileTypes:true}).filter((d:any)=>d.isDirectory()).map((d:any)=>path.join(bin,d.name,'codex.exe')).filter((p:string)=>fs.existsSync(p)).sort((a:string,b:string)=>fs.statSync(b).mtimeMs-fs.statSync(a).mtimeMs):[];
        if(!candidates.length)throw Error('Codex 앱 실행 파일을 찾지 못했습니다.');
        codexExecutable=candidates[0];
      }
      const ledgerPath=path.join(root,'mobile-control-ledger.json');
      const a=this.plugin.app.vault.adapter;await this.ensure();
      const atomic=(filename:string,value:unknown)=>{const tmp=filename+'.tmp';fs.writeFileSync(tmp,JSON.stringify(value,null,2),'utf8');fs.renameSync(tmp,filename);};
      const store:RemoteStore={
        list:async()=> (await a.list(`${CONTROL}/requests`)).files.map((p:string)=>p.split('/').pop()!),
        readRequest:async name=>{const p=`${CONTROL}/requests/${name}`,s=await a.stat(p);if(!s||s.size>2048)throw Error('oversized');return a.read(p);},
        readStatus:async id=>{const p=`${CONTROL}/status/${id}.json`;return await a.exists(p)?a.read(p):null;},
        writeStatus:async s=>{await a.write(`${CONTROL}/status/${s.id}.json`,JSON.stringify(s,null,2));},
        readLedger:async()=>fs.existsSync(ledgerPath)?JSON.parse(fs.readFileSync(ledgerPath,'utf8')):{},
        writeLedger:async l=>atomic(ledgerPath,l)
      };
      this.receiver=new RemoteReceiver(store,c,(thread,message)=>new Promise((resolve,reject)=>{
        require('child_process').execFile(codexExecutable,['queue','--thread',thread,'--message',message],{cwd:c.workspace,windowsHide:true,timeout:45000,maxBuffer:65536,encoding:'utf8'},(err:unknown,stdout:string)=>{
          if(err){reject(Error('Codex 연결을 확인해 주세요.'));return;}
          const match=stdout.match(/Queued message ([0-9a-f-]{36}) for thread ([0-9a-f-]{36})/);
          match&&match[2]===thread&&UUID.test(match[1])?resolve(match[1]):reject(Error('Codex 접수 확인을 받지 못했습니다.'));
        });
      }));
      await this.tick();
    }catch(e){this.error(e);}
  }
  async tick():Promise<void> {
    if(this.stopped)return;
    try {
      if(this.receiver){
        await this.receiver.tick();
        // Git polling is ordinary local code; no LLM wakes while the queue is empty.
        if(Date.now()-this.lastPull>60000){this.lastPull=Date.now();(this.plugin.app as any).commands?.executeCommandById('obsidian-git:pull');}
      }
      await this.refresh();
    }catch(e){const message=e instanceof Error?e.message:String(e);if(message!==this.lastError)this.error(e);}
  }
}
class ControlView extends ItemView {
  private signature='';
  constructor(leaf:WorkspaceLeaf,private control:PaperRemoteControl){super(leaf);}
  getViewType():string{return VIEW;}getDisplayText():string{return '논문 분석';}getIcon():string{return 'circle-play';}
  async onOpen():Promise<void>{await this.render();}
  async render():Promise<void>{
    const items=await this.control.requests();const signature=JSON.stringify([items,this.control.errorText]);
    if(signature===this.signature)return;this.signature=signature;
    const el=this.contentEl;el.empty();el.addClass('paper-remote');
    const body=el.createDiv('paper-remote-body');body.createEl('h1',{text:'논문 분석'});
    body.createEl('p',{text:'PDF 보관함에서 분석할 논문 한 편을 선택합니다. 요청·검토·Git 게시 상태를 여기서 확인할 수 있습니다.',cls:'paper-remote-intro'});
    const start=body.createEl('button',{text:'PDF 보관함 열기',cls:'paper-remote-start'});start.onclick=()=>{void (this.app as any).commands.executeCommandById('figure-first-reader:open-library');};
    if(this.control.errorText){const alert=body.createEl('p',{text:this.control.errorText,cls:'paper-remote-error'});alert.setAttribute('role','alert');}
    const sync=body.createEl('button',{text:'다시 동기화',cls:'paper-remote-sync'});sync.onclick=()=>{void this.control.sync().catch(e=>new Notice(e.message));};
    body.createEl('h2',{text:'최근 요청'});
    if(!items.length)body.createEl('p',{text:'아직 요청이 없습니다. 파일 준비가 끝나면 분석을 시작하세요.'});
    for(const {request,status} of items.slice(0,8)){
      const row=body.createDiv('paper-remote-record');const heading=row.createDiv('paper-remote-record-head');
      heading.createEl('strong',{text:request.action==='diagnostic'?'연결 진단':STATES[status.state]});
      heading.createEl('time',{text:new Date(request.createdAt).toLocaleString('ko-KR',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'})});
      if(request.version===2)row.createEl('p',{text:request.path.split('/').pop(),cls:'paper-remote-source'});
      row.createEl('p',{text:status.message});
      if(status.completed!==undefined&&status.total!==undefined)row.createEl('p',{text:`${status.total}편 중 ${status.completed}편 완료`});
    }
    const info=body.createEl('details');info.createEl('summary',{text:'실행 조건과 파일 위치'});
    info.createEl('p',{text:'Windows PC와 Obsidian·Codex가 실행 중이어야 합니다. PDF 폴더는 Git 동기화 대상이며, PC에 원본 PDF와 요청이 모두 도착해야 분석이 시작됩니다.'});
    info.createEl('p',{text:'요청 저장은 분석 시작과 다릅니다. PC 접수와 Codex 실행 상태가 도착하면 표시가 바뀝니다. 다운로드·로그인 문제는 조치 필요 상태로 남습니다.'});
  }
}
