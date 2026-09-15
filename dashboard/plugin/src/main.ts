import { App, MarkdownRenderChild, Modal, Notice, Plugin, PluginSettingTab, Setting, TFile,Platform } from 'obsidian';
import { desiredOpen, Depth } from './policy';
import { FigureSource, sourceMap, localPath } from './reader-data';
import {PaperLibrary,LIBRARY} from './library';
import {AnnotationView,ANNOTATIONS,NoteContext} from './annotations';
import {ResearchDashboard} from './dashboard';
import {installMeetingView} from './meeting-view';
import {installMobileReader} from './mobile-reader';
import {PaperRemoteControl} from './remote-control';

interface Preferences { depth: Depth; conceptsExpanded: boolean; }
const DEFAULTS: Preferences = { depth: 'standard', conceptsExpanded: true };
const LABELS: Record<Depth,string> = { summary:'요약',standard:'표준',detail:'상세' };

/** Use the host's native toggle instead of rewriting Markdown or callout content. */
function setOpen(callout: HTMLElement, open: boolean): void {
  if (!callout.classList.contains('is-collapsible')) return;
  const currentlyOpen=!callout.classList.contains('is-collapsed');
  if (open !== currentlyOpen) {
    const title=callout.querySelector<HTMLElement>(':scope > .callout-title');
    title?.click();
  }
}

class ReportSection extends MarkdownRenderChild {
  private bar: HTMLElement | null = null;
  private alive=false;
  constructor(container: HTMLElement, private plugin: FigureFirstReader, private sourcePath: string, private reportId: string) { super(container); }
  onload(): void {
    this.alive=true;
    const firstHeading=this.containerEl.querySelector('h1');
    if (firstHeading && !this.containerEl.querySelector('.rr-reader-toolbar')) {
      this.bar=this.containerEl.ownerDocument.createElement('div');
      this.bar.className='rr-reader-toolbar';
      this.bar.setAttribute('role','group'); this.bar.setAttribute('aria-label','리포트 읽기 설정');
      for (const depth of ['summary','standard','detail'] as Depth[]) {
        const button=this.bar.ownerDocument.createElement('button'); button.type='button';
        button.textContent=LABELS[depth]; button.dataset.rrDepth=depth;
        this.registerDomEvent(button,'click',()=>{void this.plugin.changeDepth(depth);});
        this.bar.appendChild(button);
      }
      const concepts=this.bar.ownerDocument.createElement('button'); concepts.type='button';
      concepts.className='rr-concepts-toggle';
      this.registerDomEvent(concepts,'click',()=>{void this.plugin.toggleConcepts();});
      this.bar.appendChild(concepts); firstHeading.insertAdjacentElement('afterend',this.bar);
      const memo=this.bar.ownerDocument.createElement('button');memo.type='button';memo.textContent='메모';
      this.registerDomEvent(memo,'click',()=>{void this.plugin.openNotes({reportId:this.reportId,path:this.sourcePath,anchor:'',quote:''});});this.bar.appendChild(memo);
      const fm=this.plugin.app.metadataCache?.getCache(this.sourcePath)?.frontmatter;
      if(fm?.journal){
        const details=firstHeading.ownerDocument.createElement('details');details.className='rr-paper-properties';
        const summary=details.createEl('summary',{text:'논문 정보 · 저널 / 저자 / 소속'});
        const dl=details.createEl('dl');
        const row=(label:string,value:unknown)=>{dl.createEl('dt',{text:label});dl.createEl('dd',{text:Array.isArray(value)?value.join('\n'):String(value??'확인되지 않음')});};
        row('저널',fm.journal);row('출판 연도',fm.publication_year);row('Impact Factor',fm.impact_factor==null?'확인되지 않음':`${fm.impact_factor} (${fm.impact_factor_year})`);
        row('카테고리 · 쿼터',fm.journal_quartiles?.length?fm.journal_quartiles:'공식 JCR 카테고리별 쿼터 확인 전');row('저자',fm.authors);row('소속',fm.author_affiliations);row('DOI',fm.doi);row('지표 출처',fm.metric_source);row('지표 확인일',fm.metric_checked);
        this.bar.insertAdjacentElement('afterend',details);this.register(()=>details.remove());
      }
      const preview=this.containerEl.closest<HTMLElement>('.markdown-preview-view');
      if (preview) {
        this.registerDomEvent(preview,'click',(event: MouseEvent)=>{
          const target=event.target as Element | null;
          const anchor=target?.closest<HTMLAnchorElement>('a[href^="#"]');
          const id=anchor?.getAttribute('href')?.slice(1);
          if(!id || !/^[A-Za-z0-9_-]+$/.test(id)) return;
          const destination=preview.querySelector<HTMLElement>(`[id="${id}"]`);
          if(!destination) return;
          event.preventDefault();
          let parent: HTMLElement | null=destination.parentElement;
          while(parent && parent!==preview){ if(parent.classList.contains('callout'))setOpen(parent,true); parent=parent.parentElement; }
          const next=(destination.closest('p') || destination).nextElementSibling;
          if(next && next.matches('.callout[data-callout="rr-supplement"]'))setOpen(next as HTMLElement,true);
          destination.scrollIntoView({block:'start'});
        });
      }
    }
    this.plugin.apply(this.containerEl);
    void this.enhanceImages();
    void this.enhanceEvidence();
    const win=this.containerEl.ownerDocument.defaultView;
    if(win){const id=win.requestAnimationFrame(()=>this.plugin.apply(this.containerEl));this.register(()=>win.cancelAnimationFrame(id));}
  }
  private async enhanceEvidence():Promise<void>{
    const data=await this.plugin.reportData(this.reportId);if(!this.alive||!data)return;
    for(const anchor of Array.from(this.containerEl.querySelectorAll<HTMLAnchorElement>('a[href^="#source-"]'))){
      const id=anchor.getAttribute('href')!.slice('#source-'.length);const source=Array.isArray(data.sources)?data.sources.find((s:any)=>s.id===id):null;if(!source)continue;
      anchor.classList.add('rr-evidence-ref');anchor.setAttribute('aria-label',`근거 ${anchor.textContent} 펼치기`);anchor.setAttribute('aria-expanded','false');
      let box:HTMLElement|null=null;
      this.registerDomEvent(anchor,'click',(event:MouseEvent)=>{if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;event.preventDefault();event.stopPropagation();if(box){box.remove();box=null;anchor.setAttribute('aria-expanded','false');return;}
        box=anchor.ownerDocument.createElement('aside');box.className='rr-inline-evidence';box.setAttribute('role','note');
        box.createEl('strong',{text:`근거 ${anchor.textContent} · ${source.locator||source.label||source.id}`});
        box.createEl('p',{text:source.note||source.detail||source.description||source.quote||source.location||''});
        if(source.document_id&&Number.isInteger(source.page)){const open=box.createEl('button',{text:`원문 PDF · p.${source.page}`});open.onclick=()=>{void this.plugin.openSource({imagePath:'',pdfPath:`Sources/${this.reportId}/${source.document_id}.pdf`,page:source.page},this.sourcePath);};}
        const close=box.createEl('button',{text:'근거 접기'});close.onclick=()=>{box?.remove();box=null;anchor.setAttribute('aria-expanded','false');anchor.focus();};
        (anchor.closest('p')||anchor).insertAdjacentElement('afterend',box);anchor.setAttribute('aria-expanded','true');
      });this.register(()=>box?.remove());
    }
  }
  private async enhanceImages(): Promise<void> {
    const sources=await this.plugin.imageSources(this.reportId);
    if(!this.alive)return;
    if(!sources.length && this.bar){
      const status=this.bar.ownerDocument.createElement('span');status.className='rr-reader-status';status.setAttribute('role','status');
      status.textContent='그림 연결 정보를 확인할 수 없습니다. 리포트의 분석 파일을 확인해 주세요.';
      this.bar.appendChild(status);
    }
    for(const img of Array.from(this.containerEl.querySelectorAll<HTMLImageElement>('img'))){
      const item=sources.find(row=>{
        const file=this.plugin.app.vault.getAbstractFileByPath(row.imagePath);
        return file instanceof TFile && img.src===this.plugin.app.vault.getResourcePath(file);
      });
      // Only indexed local report images are enhanced. Remote/unknown embeds keep host behavior.
      if(!item)continue;
      const file=this.plugin.app.vault.getAbstractFileByPath(item.imagePath);
      if(!(file instanceof TFile))continue;
      const tools=img.ownerDocument.createElement('div');tools.className='rr-figure-tools';
      const zoom=tools.ownerDocument.createElement('button');zoom.type='button';zoom.textContent=item.kind==='table'?'표 확대':'그림 확대';
      zoom.setAttribute('aria-label',`${img.alt || 'Figure'} 확대`);tools.appendChild(zoom);
      const open=()=>new FigureModal(this.plugin.app,this.plugin.app.vault.getResourcePath(file),img.alt,item,this.sourcePath).open();
      this.registerDomEvent(zoom,'click',open);
      this.registerDomEvent(img,'click',(event:MouseEvent)=>{
        if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
        event.preventDefault();event.stopPropagation();open();
      });
      const original=tools.ownerDocument.createElement('button');original.type='button';
      const conceptImage=item.imagePath.includes('/Concepts/');
      const pdf=item.pdfPath?this.plugin.app.vault.getAbstractFileByPath(item.pdfPath):null;
      original.textContent=pdf instanceof TFile?`원문 PDF · p.${item.page}`:'원문 PDF 미등록';
      original.disabled=!(pdf instanceof TFile);
      if(pdf instanceof TFile)this.registerDomEvent(original,'click',()=>{void this.plugin.openSource(item,this.sourcePath);});
      if(conceptImage){const label=tools.ownerDocument.createElement('span');label.className='rr-diagram-label';label.textContent='이해를 돕는 설명 도식';tools.appendChild(label);}else tools.appendChild(original);
      const memo=tools.ownerDocument.createElement('button');memo.type='button';memo.textContent='메모';memo.setAttribute('aria-label',`${img.alt||'Figure'} 메모`);
      this.registerDomEvent(memo,'click',()=>{void this.plugin.openNotes({reportId:this.reportId,path:this.sourcePath,anchor:item.anchor||'fig-'+file.basename.toLowerCase(),quote:img.alt});});if(!conceptImage)tools.appendChild(memo);
      const embed=img.closest('.internal-embed') || img;embed.insertAdjacentElement('afterend',tools);
      this.register(()=>tools.remove());
    }
  }
  onunload(): void { this.alive=false; this.bar?.remove(); }
}

class FigureModal extends Modal {
  constructor(app:App,private imageUrl:string,private label:string,private source:FigureSource,private sourcePath:string){super(app);}
  onOpen():void {
    this.modalEl.classList.add('rr-image-modal');this.titleEl.textContent=this.source.kind==='table'?'Table 확대':'Figure 확대';
    const document=this.contentEl.ownerDocument;
    const bar=document.createElement('div');bar.className='rr-figure-tools';
    const viewport=document.createElement('div');viewport.className='rr-image-viewport';viewport.tabIndex=0;viewport.setAttribute('aria-label','확대 그림 · 방향키로 스크롤');
    const image=document.createElement('img');image.src=this.imageUrl;image.alt=this.label;viewport.appendChild(image);
    for(const [label,scale] of [['화면에 맞춤',0],['100%',1],['200%',2]] as [string,number][]){
      const button=document.createElement('button');button.type='button';button.textContent=label;button.setAttribute('aria-pressed',String(scale===0));
      button.onclick=()=>{
        image.style.width=scale?`${image.naturalWidth*scale}px`:'100%';image.style.maxWidth=scale?'none':'100%';
        bar.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
      };bar.appendChild(button);
    }
    const caption=document.createElement('p');caption.textContent=this.label;caption.className='rr-image-caption';
    this.contentEl.append(bar,viewport,caption);
    const close=document.createElement('button');close.type='button';close.textContent='닫기';close.onclick=()=>this.close();this.contentEl.appendChild(close);
  }
  onClose():void {this.contentEl.empty();}
}

export default class FigureFirstReader extends Plugin {
  remoteControl:PaperRemoteControl|null=null;
  prefs: Preferences={...DEFAULTS};
  private sourceCache=new Map<string,{stamp:string;value:FigureSource[]}>();
  private saveQueue:Promise<void>=Promise.resolve();
  async onload(): Promise<void> {
    installMobileReader(this);
    installMeetingView(this);
    const saved=await this.loadData();
    this.prefs={ depth: ['summary','standard','detail'].includes(saved?.depth)?saved.depth:'standard',
                 conceptsExpanded:typeof saved?.conceptsExpanded==='boolean'?saved.conceptsExpanded:true };
    this.registerMarkdownPostProcessor((element,context)=>{
      const classes=context.frontmatter?.cssclasses;
      const enabled=Array.isArray(classes)?classes.includes('figure-first-report'):
        typeof classes==='string' && classes.split(/[,\s]+/).includes('figure-first-report');
      if(!enabled) return;
      const id=context.frontmatter?.report_id;
      context.addChild(new ReportSection(element,this,context.sourcePath,typeof id==='string'?id:''));
    },200);
    for(const depth of ['summary','standard','detail'] as Depth[]){
      this.addCommand({id:`depth-${depth}`,name:`리포트: ${LABELS[depth]} 보기`,callback:()=>{void this.changeDepth(depth);}});
    }
    this.addSettingTab(new ReaderSettings(this.app,this));
    this.registerView(LIBRARY,leaf=>new PaperLibrary(leaf,this));
    this.registerView(ANNOTATIONS,leaf=>new AnnotationView(leaf));
    new ResearchDashboard(this);
    this.remoteControl=new PaperRemoteControl(this);
    this.addRibbonIcon('library','논문 목록',()=>{void this.openLibrary();});
    this.addCommand({id:'open-library',name:'논문 목록 열기',callback:()=>{void this.openLibrary();}});
    this.registerDomEvent(document,'mouseup',()=>{this.selectionMemo();});
    this.register(()=>document.querySelectorAll('.rr-selection-note').forEach(e=>e.remove()));
  }
  async reportData(reportId:string):Promise<any>{
    if(!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(reportId))return null;
    try{const path=`.figure-reports/${reportId}/analysis.json`;const stat=await this.app.vault.adapter.stat(path);if(!stat||stat.size>2_000_000)return null;const data=JSON.parse(await this.app.vault.adapter.read(path));return data.report_id===reportId?data:null;}catch{return null;}
  }
  async openLibrary(reveal=true):Promise<void>{
    let leaf=this.app.workspace.getLeavesOfType(LIBRARY).find(l=>l.getRoot()===this.app.workspace.leftSplit);if(!leaf){const next=this.app.workspace.getLeftLeaf(false);if(!next)return;leaf=next;}await leaf.setViewState({type:LIBRARY,active:true});await this.app.workspace.revealLeaf(leaf);if(reveal)this.app.workspace.leftSplit.expand();else this.app.workspace.leftSplit.collapse();
  }
  async openNotes(context:NoteContext):Promise<void>{
    if(!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(context.reportId))return;
    let leaf=this.app.workspace.getLeavesOfType(ANNOTATIONS)[0];if(!leaf){const next=this.app.workspace.getRightLeaf(false);if(!next)return;leaf=next;await leaf.setViewState({type:ANNOTATIONS,active:true});}
    if(window.innerWidth<1250)this.app.workspace.leftSplit.collapse();
    await this.app.workspace.revealLeaf(leaf);await (leaf.view as AnnotationView).setContext(context);
  }
  private selectionMemo():void{
    const existing=document.querySelector('.rr-selection-note');
    const selection=window.getSelection();if(!selection||selection.isCollapsed||!selection.rangeCount){if(!existing?.matches(':hover'))existing?.remove();return;}
    const range=selection.getRangeAt(0);const el=range.startContainer instanceof Element?range.startContainer:range.startContainer.parentElement;
    const root=el?.closest<HTMLElement>('.markdown-preview-view.figure-first-report');if(!root||!root.contains(range.endContainer))return;
    const leaf=this.app.workspace.getLeavesOfType('markdown').find(l=>l.view.containerEl.contains(root));const file=(leaf?.view as any)?.file as TFile|undefined;if(!file)return;
    const rid=this.app.metadataCache.getFileCache(file)?.frontmatter?.report_id;if(!rid)return;
    const quote=selection.toString().trim().slice(0,5000);if(!quote)return;existing?.remove();
    const ids=Array.from(root.querySelectorAll<HTMLElement>('[id]')).filter(a=>/^fig-/.test(a.id)&&(a.compareDocumentPosition(el!)&Node.DOCUMENT_POSITION_FOLLOWING));
    const context={reportId:rid,path:file.path,anchor:ids[ids.length-1]?.id||'',quote};
    const b=document.createElement('button');b.type='button';b.className='rr-selection-note';b.textContent='선택 문장에 메모';const rect=range.getBoundingClientRect();b.style.left=`${Math.max(8,Math.min(innerWidth-180,rect.right-130))}px`;b.style.top=`${Math.min(innerHeight-55,rect.bottom+8)}px`;b.onmousedown=e=>e.preventDefault();b.onclick=()=>{b.remove();void this.openNotes(context);};document.body.appendChild(b);
  }
  async imageSources(reportId:string):Promise<FigureSource[]> {
    if(!/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(reportId))return [];
    const path=`.figure-reports/${reportId}/analysis.json`;
    try {
      const stat=await this.app.vault.adapter.stat(path);
      if(!stat || stat.size>2_000_000)return [];
      const stamp=`${stat.mtime}:${stat.size}`;const cached=this.sourceCache.get(reportId);
      if(cached?.stamp===stamp)return cached.value;
      const value=sourceMap(JSON.parse(await this.app.vault.adapter.read(path)),reportId);
      const packet=await this.reportData(reportId);
      for(const c of packet?.concepts||[]){const image=c.visual?.path;if(typeof image==='string'&&localPath(image)&&image.startsWith(`Resources/${reportId}/Concepts/`)&&/\.(png|jpe?g|webp)$/i.test(image))value.push({imagePath:image,pdfPath:null,page:null});}
      this.sourceCache.set(reportId,{stamp,value});return value;
    }catch{return [];}
  }
  async openSource(source:FigureSource,sourcePath:string):Promise<void>{
    if(!source.pdfPath||!localPath(source.pdfPath)||!source.page)return;
    try{await this.app.workspace.openLinkText(`${source.pdfPath}#page=${source.page}`,sourcePath,'tab');}
    catch{new Notice('원문 PDF를 열지 못했습니다. Vault의 Sources 폴더를 확인해 주세요.');}
  }
  async persist():Promise<void>{
    const snapshot={...this.prefs};this.refresh();
    this.saveQueue=this.saveQueue.catch(()=>{}).then(()=>this.saveData(snapshot));
    try{await this.saveQueue;}catch{new Notice('읽기 설정을 저장하지 못했습니다. 현재 화면에만 적용합니다.');}
  }
  async changeDepth(depth: Depth): Promise<void> { this.prefs.depth=depth; await this.persist(); }
  async toggleConcepts(): Promise<void> {
    this.prefs.conceptsExpanded=!this.prefs.conceptsExpanded;
    if(this.prefs.depth==='detail')this.prefs.depth='standard';
    await this.persist();
  }
  apply(element: HTMLElement): void {
    element.querySelectorAll<HTMLParagraphElement>('p').forEach(paragraph=>{
      if (/^Figure S\d+ · 해석 범위:/.test(paragraph.textContent || '')) paragraph.classList.add('supplement-scope');
    });
    const callouts=Array.from(element.querySelectorAll<HTMLElement>('.callout[data-callout]'));
    if(element.matches('.callout[data-callout]')) callouts.unshift(element);
    for(const callout of callouts){
      const open=desiredOpen(callout.dataset.callout || '',this.prefs.depth,this.prefs.conceptsExpanded);
      if(open!==null)setOpen(callout,open);
    }
    element.querySelectorAll<HTMLButtonElement>('button[data-rr-depth]').forEach(button=>{
      button.setAttribute('aria-pressed',String(button.dataset.rrDepth===this.prefs.depth));
    });
    element.querySelectorAll<HTMLButtonElement>('.rr-concepts-toggle').forEach(button=>{
      button.textContent=this.prefs.conceptsExpanded?'개념 설명 펼침':'개념 설명 접힘';
      button.setAttribute('aria-pressed',String(this.prefs.conceptsExpanded));
    });
  }
  refresh(): void {
    for(const leaf of this.app.workspace.getLeavesOfType('markdown')){
      const root=leaf.view.containerEl.querySelector<HTMLElement>('.markdown-preview-view.figure-first-report');
      if(root) this.apply(root);
    }
  }
  onunload(): void {
    for(const leaf of this.app.workspace.getLeavesOfType('markdown')){
      leaf.view.containerEl.querySelectorAll('.rr-reader-toolbar').forEach(node=>node.remove());
    }
  }
}

class ReaderSettings extends PluginSettingTab {
  constructor(app: App, private plugin: FigureFirstReader){super(app,plugin);}
  display(): void {
    this.containerEl.empty();
    this.containerEl.createEl('h2',{text:'Figure-first Reader'});
    this.containerEl.createEl('p',{text:'읽기 모드에만 적용됩니다. Markdown 본문을 수정하거나 외부로 전송하지 않습니다. 중요한 개념과 해석 범위는 항상 유지합니다.'});
    new Setting(this.containerEl).setName('기본 읽기 깊이').addDropdown(drop=>drop
      .addOptions(LABELS).setValue(this.plugin.prefs.depth)
      .onChange(value=>this.plugin.changeDepth(value as Depth)));
    new Setting(this.containerEl).setName('개념 설명 기본 펼침').addToggle(toggle=>toggle
      .setValue(this.plugin.prefs.conceptsExpanded).onChange(async value=>{
        this.plugin.prefs.conceptsExpanded=value; await this.plugin.persist();
      }));
  }
}
