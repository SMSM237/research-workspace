import {ItemView,WorkspaceLeaf,Plugin,Modal,App,Platform} from 'obsidian';
import {statusModel,sharedStatusModel} from './status-data';
export async function workerRecord(app:App,queue=false):Promise<{value:any;shared:boolean}>{
  const local=queue?'.figure-reports/queue-status.json':'.figure-reports/worker-status.json';
  const shared=Platform.isMobile||!await app.vault.adapter.exists(local);
  const path=shared?'.figure-reports/shared-status.json':local;
  const stat=await app.vault.adapter.stat(path);if(!stat)return {value:null,shared};
  if(stat.size>1000000)throw Error('상태 기록이 너무 큽니다.');
  const value=JSON.parse(await app.vault.adapter.read(path));
  return {value,shared};
}
export async function workerModel(app:App){
  try{const r=await workerRecord(app);return r.shared?sharedStatusModel(r.value):statusModel(r.value);}
  catch{return Platform.isMobile?sharedStatusModel({invalid:true}):statusModel({invalid:true});}
}
export const LIBRARY='figure-first-library';
export class PaperLibrary extends ItemView {
  private query='';
  private statusSignature='';
  constructor(leaf:WorkspaceLeaf,private plugin:Plugin){super(leaf);}
  getViewType(){return LIBRARY;}
  getDisplayText(){return '논문';}
  getIcon(){return 'library';}
  async onOpen(){this.render();this.registerEvent(this.app.metadataCache.on('changed',()=>this.renderList()));this.registerEvent(this.app.vault.on('rename',()=>this.renderList()));this.registerEvent(this.app.vault.on('delete',()=>this.renderList()));this.registerInterval(window.setInterval(()=>{void this.renderStatus();},5000));}
  render(){const e=this.contentEl;e.empty();e.classList.add('rr-library');e.createEl('h2',{text:'논문'});const s=e.createEl('input',{type:'search',placeholder:'논문 찾기'});s.setAttribute('aria-label','논문 검색');s.value=this.query;this.registerDomEvent(s,'input',()=>{this.query=s.value;this.renderList();});e.createDiv({cls:'rr-library-list'});e.createDiv({cls:'rr-analyzer-status',attr:{role:'status'}});this.renderList();void this.renderStatus();}
  private async renderStatus(){
    const e=this.contentEl.querySelector<HTMLElement>('.rr-analyzer-status');if(!e)return;
    const status=await workerModel(this.app),signature=JSON.stringify(status);
    if(signature===this.statusSignature&&e.childElementCount)return;this.statusSignature=signature;
    e.replaceChildren();e.dataset.connection=status.connection;e.setAttribute('aria-live','polite');e.setAttribute('aria-atomic','true');
    const connection=e.createDiv({cls:'rr-connection-line'});connection.createSpan({cls:'rr-connection-dot',attr:{'aria-hidden':'true'}});connection.createSpan({text:status.label});
    if(status.stage){const line=e.createDiv({cls:'rr-analysis-stage'});if(status.running){const dots=line.createSpan({cls:'rr-working-dots',attr:{'aria-hidden':'true'}});for(let i=0;i<3;i++)dots.createSpan();}line.createSpan({text:status.stage});}
    if(status.counts)e.createEl('p',{text:status.counts,cls:'rr-progress-counts'});
    if(status.detail)e.createEl('p',{text:status.detail,cls:'rr-connection-detail'});
    const jobs=e.createEl('button',{text:'작업 내역',cls:'rr-jobs-button'});jobs.onclick=()=>new WorkerJobs(this.app).open();
  }
  renderList(){const list=this.contentEl.querySelector<HTMLElement>('.rr-library-list');if(!list)return;list.empty();const papers=this.app.vault.getMarkdownFiles().filter(f=>f.path.startsWith('Papers/')&&this.app.metadataCache.getFileCache(f)?.frontmatter?.report_id).sort((a,b)=>a.basename.localeCompare(b.basename,'ko'));
    let count=0;for(const file of papers){const fm=this.app.metadataCache.getFileCache(file)?.frontmatter;const title=String(fm?.library_title||file.basename);if(!title.toLocaleLowerCase().includes(this.query.toLocaleLowerCase()))continue;count++;const b=list.createEl('button',{cls:'rr-library-paper',text:title});b.title=title;b.onclick=async()=>{await this.app.workspace.getLeaf(false).openFile(file,{state:{mode:'preview'}});if(Platform.isMobile)this.app.workspace.leftSplit.collapse();};}
    if(!count)list.createEl('p',{text:this.query?'검색 결과가 없습니다.':'등록된 논문이 없습니다.',cls:'rr-empty'});
  }
}

export class WorkerJobs extends Modal {
  private timer:number|undefined;
  private signature='';
  onOpen(){this.modalEl.classList.add('rr-jobs-modal');this.titleEl.setText('분석 작업');this.contentEl.createEl('p',{text:'작업별 진행 상태와 저장 결과를 확인합니다. 자료 준비, Figure 분석, 최종 리포트 완료를 구분하여 표시합니다.',cls:'rr-jobs-intro'});this.contentEl.createDiv({cls:'rr-jobs-list'});void this.refresh();this.timer=window.setInterval(()=>void this.refresh(),3000);}
  onClose(){if(this.timer!==undefined)window.clearInterval(this.timer);this.contentEl.empty();}
  private async refresh(){
    const list=this.contentEl.querySelector<HTMLElement>('.rr-jobs-list');if(!list)return;
    try{
      const record=await workerRecord(this.app,true),data=record.value;
      if(!data){list.setText(record.shared?'분석 상태가 아직 동기화되지 않았습니다.':'접수된 작업이 없습니다.');return;}
      const raw=JSON.stringify(data);if(raw===this.signature)return;
      if(data.version!==1||!Array.isArray(data.jobs)||data.jobs.length>2000)throw Error();
      for(const job of data.jobs)if(typeof job.id!=='string'||! /^[a-f0-9]{32}$/.test(job.id)||typeof job.report_id!=='string'||typeof job.state!=='string')throw Error();
      this.signature=raw;list.empty();
      if(record.shared)list.createEl('p',{text:'마지막 동기화 기록 · '+new Date(data.updated_at).toLocaleString('ko-KR')+' · 실시간 상태가 아닙니다.',cls:'rr-connection-detail'});
      if(!data.jobs.length)list.setText('접수된 작업이 없습니다.');
      const labels:Record<string,string>={queued:'대기 중',running:'진행 중',prepared:'자료 준비 완료',failed:'오류',interrupted:'중단됨',waiting:'대기',review:'분석 결과 검토 대기',complete:'분석 완료'};
      for(const job of data.jobs.slice().reverse()){
        const paper=this.app.vault.getMarkdownFiles().find(f=>f.path.startsWith('Papers/')&&this.app.metadataCache.getFileCache(f)?.frontmatter?.report_id===job.report_id);
        const title=paper?String(this.app.metadataCache.getFileCache(paper)?.frontmatter?.library_title||paper.basename):(typeof job.source_name==='string'&&job.source_name?job.source_name:job.report_id);
        const row=list.createDiv({cls:'rr-job'});row.createEl('h3',{text:title});row.createSpan({text:labels[job.state]||'상태 확인 필요',cls:'rr-job-state'});
        row.createEl('p',{text:typeof job.message==='string'?job.message.slice(0,300):''});
        if(!record.shared&&['failed','interrupted'].includes(job.state)){
          const button=row.createEl('button',{text:'다시 시도'});button.onclick=async()=>{
            button.disabled=true;
            try{const folder='.figure-reports/commands';if(!await this.app.vault.adapter.exists(folder))await this.app.vault.adapter.mkdir(folder);
              await this.app.vault.adapter.write(`${folder}/${crypto.randomUUID()}.json`,JSON.stringify({action:'retry',job_id:job.id}));button.setText('재시도 요청됨');}
            catch{button.disabled=false;button.setText('요청 실패 · 다시 시도');}
          };
        }
      }
    }catch{this.signature='';list.setText('작업 기록을 읽지 못했습니다. 분석기 상태를 확인해 주세요.');}
  }
}
