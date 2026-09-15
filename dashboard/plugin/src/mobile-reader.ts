import {App,Modal,Plugin,TFile,MarkdownView,WorkspaceLeaf,Platform} from 'obsidian';

type Entry={heading:string;level:number};
function entries(app:App,file:TFile):Entry[]{return (app.metadataCache.getFileCache(file)?.headings||[]).filter(h=>h.level===2||(h.level===3&&/^Figure\s+\d+\b/i.test(h.heading))).map(h=>({heading:h.heading,level:h.level}));}

class Contents extends Modal{
  constructor(app:App,private rows:Entry[],private current:number,private jump:(index:number)=>Promise<void>){super(app);}
  onOpen(){this.titleEl.setText('리포트 목차');this.modalEl.classList.add('rr-contents-modal');this.contentEl.createEl('p',{text:'본문을 생략하지 않고 원하는 구간으로 이동합니다.',cls:'rr-contents-hint'});
    this.rows.forEach((row,i)=>{const b=this.contentEl.createEl('button',{text:row.heading,cls:'rr-contents-entry',attr:{'data-level':String(row.level),'aria-current':i===this.current?'location':'false'}});b.onclick=()=>{this.close();void this.jump(i);};});}
}

/** Navigation lives outside Obsidian's virtualized Markdown blocks. */
export function installMobileReader(plugin:Plugin){
  const mounted=new Map<WorkspaceLeaf,{path:string;dispose:()=>void}>();
  const refresh=()=>{
    const leaves=plugin.app.workspace.getLeavesOfType('markdown').filter(leaf=>leaf===plugin.app.workspace.getMostRecentLeaf());
    for(const [leaf,m] of mounted)if(!leaves.includes(leaf)||!(leaf.view instanceof MarkdownView)||leaf.view.file?.path!==m.path||leaf.view.getMode()!=='preview'){m.dispose();mounted.delete(leaf);}
    if(!Platform.isMobile&&!document.body.classList.contains('is-mobile'))return;
    for(const leaf of leaves){
      if(mounted.has(leaf)||!(leaf.view instanceof MarkdownView)||!leaf.view.file||leaf.view.getMode()!=='preview')continue;
      const view=leaf.view,file=view.file!,fm=plugin.app.metadataCache.getFileCache(file)?.frontmatter;
      const classes=fm?.cssclasses; if(!(Array.isArray(classes)?classes.includes('figure-first-report'):String(classes||'').split(/[,\s]+/).includes('figure-first-report')))continue;
      const rows=entries(plugin.app,file);if(!rows.length)continue;
      const parent=view.containerEl.querySelector<HTMLElement>('.view-content'),preview=view.containerEl.querySelector<HTMLElement>('.markdown-preview-view');if(!parent||!preview)continue;
      let current=0,pending=false,holdUntil=0;const nav=parent.createEl('nav',{cls:'rr-mobile-navigation',attr:{'aria-label':'리포트 구간 이동'}});
      const prev=nav.createEl('button',{text:'이전',attr:{'aria-label':'이전 구간'}}),toc=nav.createEl('button',{text:'목차',cls:'rr-mobile-contents'}),next=nav.createEl('button',{text:'다음',attr:{'aria-label':'다음 구간'}});
      const update=()=>{prev.disabled=pending||current===0;next.disabled=pending||current===rows.length-1;toc.textContent=`목차 · ${current+1}/${rows.length}`;toc.setAttribute('aria-label','목차 열기. 현재 '+rows[current].heading);};
      const jump=async(index:number)=>{if(pending||index<0||index>=rows.length)return;pending=true;holdUntil=performance.now()+1000;update();try{plugin.app.workspace.setActiveLeaf(leaf,{focus:false});await plugin.app.workspace.openLinkText(file.path+'#'+rows[index].heading,file.path,false);current=index;}finally{pending=false;update();}};
      prev.onclick=()=>void jump(current-1);next.onclick=()=>void jump(current+1);toc.onclick=()=>new Contents(plugin.app,rows,current,jump).open();
      let frame=0;const scroll=()=>{if(frame)return;frame=requestAnimationFrame(()=>{frame=0;if(pending||performance.now()<holdUntil)return;const top=preview.getBoundingClientRect().top+70;let found=-1;for(const h of Array.from(preview.querySelectorAll<HTMLElement>('h2,h3'))){const i=rows.findIndex(r=>r.heading===h.textContent?.trim());if(i>=0&&h.getBoundingClientRect().top<=top)found=i;}if(found>=0){current=found;update();}});};
      preview.addEventListener('scroll',scroll,{passive:true});parent.classList.add('rr-has-mobile-navigation');update();
      mounted.set(leaf,{path:file.path,dispose:()=>{nav.remove();parent.classList.remove('rr-has-mobile-navigation');preview.removeEventListener('scroll',scroll);if(frame)cancelAnimationFrame(frame);}});
    }
  };
  let frame=0;const schedule=()=>{if(frame)return;frame=requestAnimationFrame(()=>{frame=0;refresh();});};
  plugin.registerEvent(plugin.app.workspace.on('layout-change',schedule));plugin.registerEvent(plugin.app.workspace.on('active-leaf-change',schedule));plugin.registerEvent(plugin.app.workspace.on('file-open',schedule));plugin.registerEvent(plugin.app.metadataCache.on('resolved',schedule));plugin.registerDomEvent(window,'resize',schedule);
  plugin.app.workspace.onLayoutReady(schedule);
  plugin.register(()=>{if(frame)cancelAnimationFrame(frame);for(const m of mounted.values())m.dispose();mounted.clear();});
}
