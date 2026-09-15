import {ItemView,WorkspaceLeaf,TFile,Notice} from 'obsidian';
import {NotesData,Annotation,parseNotes,serializeNotes,updateNote} from './annotation-data';
export const ANNOTATIONS='figure-first-annotations';
export interface NoteContext {reportId:string;path:string;anchor:string;quote:string;}
export class AnnotationView extends ItemView {
  context:NoteContext|null=null;
  private data:NotesData|null=null;
  private raw:string|null=null;
  private draft='';
  private editing:Annotation|null=null;
  private busy=false;
  private draftKey(){const a=this.app.vault.adapter as any;return 'figure-first-draft:'+String(a.getBasePath?.()||this.app.vault.getName())+':'+this.context?.reportId;}
  private keepDraft(){if(!this.context)return;try{if(this.draft.trim())localStorage.setItem(this.draftKey(),JSON.stringify({context:this.context,draft:this.draft,editing:this.editing}));else localStorage.removeItem(this.draftKey());}catch{new Notice('초안 보관에 실패했습니다. 메모 저장을 눌러 파일로 저장해 주세요.');}}
  async onClose(){this.keepDraft();}
  getViewType(){return ANNOTATIONS;}
  getDisplayText(){return '본문 메모';}
  getIcon(){return 'message-square-text';}
  async onOpen(){this.contentEl.classList.add('rr-annotations');this.render();}
  async setContext(context:NoteContext){
    if(this.draft.trim()&&this.context&&(this.context.reportId!==context.reportId||this.context.anchor!==context.anchor||this.context.quote!==context.quote)){new Notice('작성 중인 메모를 저장하거나 취소한 뒤 다른 위치를 선택해 주세요.');return;}
    this.context=context;
    if(!this.draft){try{const raw=localStorage.getItem(this.draftKey());if(raw){const saved=JSON.parse(raw);if(saved.context?.reportId===context.reportId&&typeof saved.draft==='string'&&saved.draft.length<=20000){this.context=saved.context;this.draft=saved.draft;this.editing=saved.editing||null;new Notice('작성 중이던 메모 초안을 복원했습니다.');}}}catch{new Notice('이전 초안을 읽을 수 없습니다. 저장된 메모 파일은 유지됩니다.');}}
    await this.loadNotes();
  }
  private get path(){return `Notes/${this.context!.reportId}.annotations.md`;}
  private async loadNotes(){try{const file=this.app.vault.getAbstractFileByPath(this.path);if(file&&!(file instanceof TFile))throw Error('메모 경로가 파일이 아닙니다.');this.raw=file?await this.app.vault.read(file as TFile):null;this.data=this.raw===null?{version:1,report_id:this.context!.reportId,comments:[]}:parseNotes(this.raw,this.context!.reportId);this.render();}catch(err){this.data=null;this.render(String(err));}}
  private render(error=''){
    const e=this.contentEl;e.empty();e.createEl('h2',{text:'본문 메모'});
    if(!this.context){e.createEl('p',{text:'그림의 메모 버튼을 누르거나 본문 문장을 선택해 주세요.'});return;}
    const context=this.context;e.createEl('p',{text:context.anchor?context.anchor.replace('fig-','').toUpperCase():'선택 문장',cls:'rr-note-location'});
    if(context.quote)e.createEl('blockquote',{text:context.quote});
    if(error){e.createEl('p',{text:error,cls:'rr-note-error',attr:{role:'alert'}});const retry=e.createEl('button',{text:'다시 읽기'});retry.onclick=()=>{void this.loadNotes();};return;}
    const field=e.createEl('textarea',{placeholder:'이 부분에 대한 메모를 남겨 주세요.'});field.setAttribute('aria-label','메모 내용');field.value=this.draft;field.rows=5;field.maxLength=20000;field.oninput=()=>{this.draft=field.value;this.keepDraft();};
    const actions=e.createDiv({cls:'rr-note-actions'});const save=actions.createEl('button',{text:this.editing?'수정 저장':'메모 저장',cls:'mod-cta'});save.disabled=this.busy;save.onclick=()=>{void this.save();};const cancel=actions.createEl('button',{text:'취소'});cancel.onclick=()=>{this.draft='';this.editing=null;this.keepDraft();this.render();};
    const status=e.createEl('p',{cls:'rr-note-save-status',attr:{role:'status'}});status.textContent=this.busy?'저장 중…':'메모는 분석 본문과 별도로 보관됩니다.';
    const all=e.createEl('details',{cls:'rr-note-all'});all.open=true;all.createEl('summary',{text:`이 논문의 메모 · ${this.data?.comments.length||0}`});
    for(const c of this.data?.comments||[]){const row=all.createDiv({cls:'rr-note'+(c.resolved?' is-resolved':'')});row.createEl('p',{text:(c.anchor||'선택 문장')+(c.resolved?' · 해결됨':''),cls:'rr-note-location'});if(c.quote)row.createEl('blockquote',{text:c.quote});row.createEl('p',{text:c.text,cls:'rr-note-text'});const controls=row.createDiv({cls:'rr-note-actions'});const edit=controls.createEl('button',{text:'수정'});edit.onclick=()=>{if(this.draft.trim()){new Notice('작성 중인 메모를 먼저 저장하거나 취소해 주세요.');return;}this.editing=c;this.draft=c.text;this.render();};const resolve=controls.createEl('button',{text:c.resolved?'다시 열기':'해결됨'});resolve.onclick=()=>{void this.save(c);};}
  }
  private async save(toggle?:Annotation){
    if(this.busy||!this.data||!this.context)return;
    if(!toggle&&!this.draft.trim()){new Notice('메모 내용을 입력해 주세요.');return;}
    this.busy=true;const now=new Date().toISOString();
    try{
      let next:NotesData;
      if(toggle)next=updateNote(this.data,toggle.id,toggle.text,!toggle.resolved,toggle.updated,now);
      else if(this.editing)next=updateNote(this.data,this.editing.id,this.draft.trim(),this.editing.resolved,this.editing.updated,now);
      else next={...this.data,comments:[...this.data.comments,{id:crypto.randomUUID(),anchor:this.context.anchor,quote:this.context.quote,text:this.draft.trim(),created:now,updated:now,resolved:false}]};
      const text=serializeNotes(next),file=this.app.vault.getAbstractFileByPath(this.path),expected=this.raw;
      if(file instanceof TFile){await this.app.vault.process(file,current=>{if(expected===null||current!==expected)throw Error('다른 곳에서 메모가 변경되었습니다. 초안은 유지됩니다. 다시 읽은 후 저장해 주세요.');return text;});}
      else{if(expected!==null)throw Error('메모 파일이 이동되었습니다. 초안은 유지됩니다.');if(!this.app.vault.getAbstractFileByPath('Notes'))await this.app.vault.createFolder('Notes');await this.app.vault.create(this.path,text);}
      this.raw=text;this.data=next;if(!toggle){this.draft='';this.editing=null;this.keepDraft();}this.busy=false;this.render();this.contentEl.querySelector('.rr-note-save-status')!.textContent='저장됨';
    }catch(err){this.busy=false;this.render();const s=this.contentEl.querySelector('.rr-note-save-status')!;s.textContent=String(err);s.classList.add('rr-note-error');s.setAttribute('role','alert');const retry=this.contentEl.createEl('button',{text:'다시 읽기 · 초안 유지'});retry.onclick=()=>{void this.loadNotes();};}
  }
}

