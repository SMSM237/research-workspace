"""Compiled plugin component tests with an explicit fake Obsidian host.

These test behavior, not native Obsidian rendering or PDF viewer integration.
"""
import json
import os
from pathlib import Path
import shutil
import pytest
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def reader_page():
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium'))
        page=browser.new_page(viewport={'width':1000,'height':800})
        page.set_content('<main class="markdown-preview-view figure-first-report"><h1>테스트 논문</h1><img id="figure" alt="테스트 Figure"><div class="callout is-collapsible is-collapsed" data-callout="rr-supplement"><div class="callout-title">서플</div><div class="callout-content">서플 내용</div></div></main>')
        page.add_style_tag(content=(ROOT.parent/'dashboard/plugin/styles.css').read_text(encoding='utf-8')+'.modal-container{position:fixed;inset:0;background:white}.is-collapsed>.callout-content{display:none}')
        page.evaluate('''() => {
          HTMLElement.prototype.empty=function(){this.replaceChildren();};
          class Component{constructor(){this.cleanups=[];}register(fn){this.cleanups.push(fn);}registerDomEvent(el,event,fn){el.addEventListener(event,fn);this.register(()=>el.removeEventListener(event,fn));}unload(){this.onunload?.();this.cleanups.forEach(f=>f());}}
          class TFile{constructor(path){this.path=path;this.basename=path.split('/').at(-1).split('.')[0];}}
          const canvas=document.createElement('canvas');canvas.width=800;canvas.height=400;const ctx=canvas.getContext('2d');ctx.fillStyle='#ddd';ctx.fillRect(0,0,800,400);window.imageURL=canvas.toDataURL();document.querySelector('#figure').src=imageURL;
          window.events={saved:[],links:[],notices:[]};window.children=[];
          const files={'Resources/P1/F1.png':new TFile('Resources/P1/F1.png'),'Sources/P1/D001.pdf':new TFile('Sources/P1/D001.pdf')};
          window.packet={report_id:'P1',figures:[{image:{path:'Resources/P1/F1.png',source_ref:'s1'}}],sources:[{id:'s1',document_id:'D001',page:2}]};
          window.host={metadataCache:{getCache:()=>null,on:()=>({})},vault:{on:()=>({}),getAbstractFileByPath:p=>files[p]||null,getResourcePath:f=>imageURL,adapter:{stat:async()=>({mtime:1,size:300}),read:async()=>JSON.stringify(packet)}},workspace:{on:()=>({}),onLayoutReady:()=>{},getLeavesOfType:()=>[{view:{containerEl:document.body}}],openLinkText:async(...args)=>events.links.push(args)}};
          class Plugin extends Component{constructor(){super();this.app=host;}async loadData(){return {};}async saveData(data){if(window.failSave)throw new Error('readonly');events.saved.push({...data});}registerMarkdownPostProcessor(fn){this.processor=fn;}addCommand(){}addSettingTab(){}registerView(){}addRibbonIcon(){}registerEvent(){}registerInterval(id){this.register(()=>clearInterval(id));}registerMarkdownCodeBlockProcessor(){}registerObsidianProtocolHandler(){}}
          class Child extends Component{constructor(el){super();this.containerEl=el;}}
          class Modal{constructor(app){this.containerEl=document.createElement('div');this.containerEl.className='modal-container';this.modalEl=document.createElement('div');this.titleEl=document.createElement('h2');this.contentEl=document.createElement('div');this.modalEl.append(this.titleEl,this.contentEl);this.containerEl.append(this.modalEl);}open(){document.body.append(this.containerEl);window.activeModal=this;this.onOpen();}close(){this.onClose();this.containerEl.remove();}}
          document.addEventListener('keydown',e=>{if(e.key==='Escape')window.activeModal?.close();});
          class Notice{constructor(text){events.notices.push(text);}}
          window.exports={};window.require=()=>({Plugin,MarkdownRenderChild:Child,Modal,TFile,Notice,ItemView:class extends Component{},FileView:class extends Component{},MarkdownView:class extends Component{},Platform:{isMobile:false,isDesktopApp:false,isWin:false},PluginSettingTab:class{},Setting:class{}});
          document.querySelector('.callout-title').onclick=e=>e.currentTarget.parentElement.classList.toggle('is-collapsed');
        }''')
        page.add_script_tag(content=(ROOT.parent/'dashboard/plugin/main.js').read_text(encoding='utf-8'))
        page.evaluate('''async()=>{window.reader=new exports.default();await reader.onload();reader.processor(document.querySelector('main'),{sourcePath:'Papers/P1.md',frontmatter:{cssclasses:['figure-first-report'],report_id:'P1'},addChild:c=>{children.push(c);c.onload();}});}''')
        page.get_by_role('button',name='원문 PDF · p.2',exact=True).wait_for()
        yield page
        browser.close()

def test_compiled_plugin_zoom_source_depth_and_cleanup(reader_page):
    page=reader_page
    page.get_by_role('button',name='테스트 Figure 확대',exact=True).click()
    assert page.locator('.rr-image-modal').is_visible()
    page.get_by_role('button',name='200%',exact=True).click()
    assert page.locator('.rr-image-viewport img').evaluate('(i)=>i.clientWidth')==1600
    page.get_by_role('button',name='화면에 맞춤',exact=True).click()
    assert page.locator('.rr-image-viewport img').evaluate('(i)=>i.clientWidth')<=1000
    if os.environ.get('RR_COMPONENT_CAPTURE'):
        folder=Path(os.environ['RR_COMPONENT_CAPTURE']);folder.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(folder/'zoom-component.png'))
    page.keyboard.press('Escape')
    assert page.locator('.rr-image-modal').count()==0
    if os.environ.get('RR_COMPONENT_CAPTURE'):
        page.screenshot(path=str(Path(os.environ['RR_COMPONENT_CAPTURE'])/'reader-component.png'))
    page.get_by_role('button',name='원문 PDF · p.2',exact=True).click()
    assert page.evaluate('events.links')==[['Sources/P1/D001.pdf#page=2','Papers/P1.md','tab']]
    page.get_by_role('button',name='상세',exact=True).click()
    assert 'is-collapsed' not in page.locator('.callout').get_attribute('class')
    page.get_by_role('button',name='요약',exact=True).click()
    assert 'is-collapsed' in page.locator('.callout').get_attribute('class')
    assert page.evaluate('events.saved.at(-1).depth')=='summary'
    page.evaluate('children.forEach(c=>c.unload());reader.unload()')
    assert page.locator('.rr-reader-toolbar,.rr-figure-tools').count()==0
    assert page.locator('#figure').count()==1

def test_preference_failure_is_visible_and_later_save_recovers(reader_page):
    page=reader_page
    page.evaluate('window.failSave=true')
    page.get_by_role('button',name='상세',exact=True).click()
    assert page.evaluate('events.notices.length')==1
    assert 'is-collapsed' not in page.locator('.callout').get_attribute('class')
    page.evaluate('window.failSave=false')
    page.get_by_role('button',name='표준',exact=True).click()
    assert page.evaluate('events.saved.at(-1).depth')=='standard'


def test_missing_pdf_disables_source_without_losing_zoom(reader_page):
    page=reader_page
    page.evaluate('''()=>{children.forEach(c=>c.unload());const original=host.vault.getAbstractFileByPath;host.vault.getAbstractFileByPath=p=>p.endsWith('.pdf')?null:original(p);reader.processor(document.querySelector('main'),{sourcePath:'Papers/P1.md',frontmatter:{cssclasses:['figure-first-report'],report_id:'P1'},addChild:c=>{children.push(c);c.onload();}});}''')
    assert page.get_by_role('button',name='원문 PDF 미등록',exact=True).is_disabled()
    page.get_by_role('button',name='테스트 Figure 확대',exact=True).click()
    assert page.locator('.rr-image-modal').is_visible()


def test_invalid_index_reports_problem_without_injecting_controls(reader_page):
    page=reader_page
    page.evaluate('''()=>{children.forEach(c=>c.unload());host.vault.adapter.stat=async()=>({mtime:2,size:300});host.vault.adapter.read=async()=>'{broken';reader.processor(document.querySelector('main'),{sourcePath:'Papers/P1.md',frontmatter:{cssclasses:['figure-first-report'],report_id:'P1'},addChild:c=>{children.push(c);c.onload();}});}''')
    page.get_by_role('status').wait_for()
    assert page.locator('.rr-figure-tools').count()==0
    assert page.locator('#figure').count()==1
