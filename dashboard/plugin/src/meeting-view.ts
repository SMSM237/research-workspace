import {App,FileView,Plugin,TFile,WorkspaceLeaf,setIcon,parseYaml} from 'obsidian';
import {MEETING_SECTIONS,meetingSlots,writeMeeting} from './meeting-data';
export const MEETING_VIEW='research-meeting-editor';
class MeetingView extends FileView {
 private base='';private fields=new Map<string,HTMLTextAreaElement>();private timer:number|undefined;private queue=Promise.resolve();private status!:HTMLElement;private dirty=false;private activeFile:TFile|null=null;
 constructor(leaf:WorkspaceLeaf){super(leaf);}
 getViewType(){return MEETING_VIEW;}getDisplayText(){return this.file?.basename||'회의록';}getIcon(){return 'messages-square';}
 private draftKey(file:TFile){return 'research-meeting-draft:'+file.path;}
 async onLoadFile(file:TFile){this.activeFile=file;this.base=await this.app.vault.read(file);this.dirty=false;this.render(file);}
 private render(file:TFile){
  const root=this.contentEl;root.empty();root.classList.add('rm-editor');this.fields.clear();
  let fm=this.app.metadataCache.getFileCache(file)?.frontmatter;try{fm=parseYaml(this.base.match(/^---\r?\n([\s\S]*?)\r?\n---/)?.[1]||'')||fm;}catch{/* The existing source remains available through the raw editor. */}
  const bar=root.createDiv({cls:'rm-toolbar'});const raw=bar.createEl('button',{text:'원문 열기',attr:{type:'button'}});raw.onclick=()=>void this.save().then(async()=>{await this.leaf.setViewState({type:'markdown',state:{file:file.path,mode:'source'},active:true});});
  this.status=bar.createSpan({cls:'rm-save-status',text:'저장됨',attr:{role:'status','aria-live':'polite'}});const save=bar.createEl('button',{text:'저장',cls:'mod-cta',attr:{type:'button'}});save.onclick=()=>void this.save();
  const scroll=root.createDiv({cls:'rm-scroll'});scroll.createEl('h1',{text:String(fm?.title||file.basename)});const meta=[fm?.date,fm?.time].filter(Boolean).join(' · ');if(meta)scroll.createEl('p',{cls:'rm-meta',text:meta});
  scroll.createEl('p',{cls:'rm-guide',text:'각 박스 안을 눌러 작성하세요. 입력 내용은 자동으로 저장됩니다.'});
  let slots;try{slots=meetingSlots(this.base);}catch(e){this.status.textContent=String(e);this.status.classList.add('is-error');return;}
  const draft=this.app.loadLocalStorage(this.draftKey(file));const restored=draft&&typeof draft.base==='string'&&(draft.values||typeof draft.text==='string');let values=Object.fromEntries(slots.map(s=>[s.key,s.value]));
  if(restored){try{values=draft.values&&MEETING_SECTIONS.every(s=>typeof draft.values[s.key]==='string')?draft.values:Object.fromEntries(meetingSlots(draft.text).map(s=>[s.key,s.value]));this.dirty=true;this.status.textContent=draft.base===this.base?'저장하지 못한 입력 복원됨':'원본 변경 · 입력 복원됨. 원문과 비교해 주세요.';if(draft.base!==this.base){this.base=draft.base;this.status.classList.add('is-error');}}catch{this.status.textContent='보관한 입력을 읽지 못했습니다. 원문을 확인해 주세요.';}}
  for(const section of MEETING_SECTIONS){const card=scroll.createDiv({cls:'rm-card',attr:{'data-tone':section.tone}});const heading=card.createDiv({cls:'rm-card-heading'});const icon=heading.createSpan({cls:'rm-card-icon',attr:{'aria-hidden':'true'}});setIcon(icon,section.icon);const id='rm-'+section.key+'-'+Math.random().toString(36).slice(2);heading.createEl('label',{text:section.title,attr:{for:id}});
   const input=card.createEl('textarea',{cls:'rm-input',attr:{id,'aria-label':section.title,placeholder:section.hint,rows:section.key==='discussion'?'5':'3',spellcheck:'false'}});input.value=values[section.key]||'';this.fields.set(section.key,input);
   const changed=()=>{this.dirty=true;this.status.textContent='저장 대기…';this.status.classList.remove('is-error');this.persistDraft();if(this.timer!==undefined)window.clearTimeout(this.timer);this.timer=window.setTimeout(()=>void this.save(),500);};input.oninput=changed;input.onblur=()=>{if(this.dirty)void this.save();};input.onkeydown=e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();void this.save();}};
   if(section.key==='actions'){const add=card.createEl('button',{text:'＋ 할 일 추가',cls:'rm-add-action',attr:{type:'button'}});add.onclick=()=>{input.value=input.value.replace(/\s*$/,'')+(input.value.trim()?'\n':'')+'- [ ] ';input.focus();input.setSelectionRange(input.value.length,input.value.length);changed();};}
  }
 }
 private text(){return writeMeeting(this.base,Object.fromEntries([...this.fields].map(([key,input])=>[key,input.value])));}
 private persistDraft(){if(this.activeFile){try{this.app.saveLocalStorage(this.draftKey(this.activeFile),{base:this.base,values:Object.fromEntries([...this.fields].map(([key,input])=>[key,input.value]))});}catch(e){this.status.textContent=String(e);this.status.classList.add('is-error');}}}
 async save(){if(this.timer!==undefined)window.clearTimeout(this.timer);this.queue=this.queue.then(async()=>{const file=this.activeFile;if(!file||!this.dirty)return;let next:string;try{next=this.text();}catch(e){this.status.textContent=String(e);this.status.classList.add('is-error');return;}const before=this.base;this.status.textContent='저장 중…';
   try{await this.app.vault.process(file,current=>{if(current!==before)throw Error('원본이 변경되어 저장을 멈췄습니다. 입력은 이 기기에 보관했습니다. 원문과 비교해 주세요.');return next;});const current=this.text();this.base=next;this.dirty=current!==next;if(!this.dirty){this.app.saveLocalStorage(this.draftKey(file),null);this.status.textContent='저장됨';this.status.classList.remove('is-error');}else this.persistDraft();}
   catch(e){this.persistDraft();this.status.textContent=e instanceof Error?e.message:'저장 실패 · 입력 내용은 이 기기에 보관됩니다.';this.status.classList.add('is-error');}
  });return this.queue;}
 async onUnloadFile(){await this.save();this.activeFile=null;this.fields.clear();}
 async onClose(){await this.save();if(this.timer!==undefined)window.clearTimeout(this.timer);this.contentEl.empty();}
}
export function installMeetingView(plugin:Plugin){plugin.registerView(MEETING_VIEW,leaf=>new MeetingView(leaf));}
