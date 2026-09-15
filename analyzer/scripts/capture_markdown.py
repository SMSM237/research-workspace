"""Capture the emitted Markdown + actual plugin CSS, NOT the Obsidian app.

The small host shim only supplies generic Markdown/callout DOM and theme variables.
It is a reproducible visual harness, not a plugin-host integration certification.
"""
from __future__ import annotations
import argparse
import base64
from html import escape
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
from bs4 import BeautifulSoup
from markdown_it import MarkdownIt

HOST_CSS = '''
*{box-sizing:border-box}body{margin:0;color:#272b31;background:#f5f6f8;font-family:"Noto Sans CJK KR",-apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",sans-serif;--background-primary:#fff;--background-secondary:#f6f7f9;--background-modifier-border:#e2e6eb;--text-normal:#272b31}
.capture-label{max-width:1020px;margin:0 auto;padding:18px 30px;font-size:11px;letter-spacing:.025em;line-height:1.7;color:#7e8692}
.markdown-preview-view{max-width:1020px;margin:0 auto 40px;background:white;border:1px solid #e5e8ed;border-radius:8px;padding:44px 74px 80px}
.callout-title{display:flex;align-items:baseline;gap:9px}.is-collapsible>.callout-title{cursor:pointer}.callout-fold{font-size:17px;display:inline-block;width:12px;color:#8692a0;transform:rotate(90deg)}.is-collapsed>.callout-title .callout-fold{transform:none}.is-collapsed>.callout-content{display:none}.callout-title-content{flex:1}.callout-content>:last-child{margin-bottom:0}button{font:inherit;font-size:12px;padding:6px 12px;border:1px solid #dce2e9;background:#fff;color:#687486;cursor:pointer}button:focus-visible,.callout-title:focus-visible{outline:2px solid #8a9bb0;outline-offset:4px}h1,h2,h3,h4{scroll-margin-top:24px}a{text-decoration:none}.markdown-preview-view>p:nth-of-type(1){font-size:13px;color:#7a8491}.markdown-preview-view>p:nth-of-type(2){font-size:11px;color:#8590a0}
@media(max-width:650px){.capture-label{padding:12px 18px;font-size:10px}.markdown-preview-view{border:0;border-radius:0;padding:28px 21px 55px;margin:0;background:#fff}.capture-label span{display:block}}
'''


def render_markdown_preview(markdown: Path, plugin: Path) -> str:
    content = markdown.read_text(encoding='utf-8')
    if content.startswith('---\n'):
        content = content.split('\n---\n', 1)[1]
    parser = MarkdownIt('commonmark', {'html': True})
    parser.enable('table')
    soup = BeautifulSoup(parser.render(content), 'html.parser')
    for quote in list(soup.find_all('blockquote'))[::-1]:
        first = quote.find('p', recursive=False)
        if first is None:
            continue
        match = re.fullmatch(r'\[!([\w-]+)\]([+-]?)\s*(.*)', first.get_text(), re.S)
        if not match:
            continue
        kind, fold, title = match.groups()
        first.decompose()
        box = soup.new_tag('div')
        box['data-callout'] = kind
        box['class'] = ['callout'] + (['is-collapsible'] if fold else []) + (['is-collapsed'] if fold == '-' else [])
        label = soup.new_tag('div', attrs={'class': 'callout-title'})
        if fold:
            label['tabindex']='0'; label['role']='button';label['aria-expanded']=str(fold=='+').lower()
            icon = soup.new_tag('span', attrs={'class':'callout-fold', 'aria-hidden':'true'});icon.string='›';label.append(icon)
        text = soup.new_tag('span', attrs={'class':'callout-title-content'});text.string=title;label.append(text)
        box.append(label)
        body=soup.new_tag('div',attrs={'class':'callout-content'})
        for child in list(quote.contents):
            body.append(child.extract())
        box.append(body); quote.replace_with(box)
    vault = markdown.parent.parent.resolve()
    for image in soup.find_all('img'):
        image_path=(markdown.parent / image['src']).resolve()
        if not image_path.is_relative_to(vault):
            raise ValueError('Capture assets must remain inside the provided Vault')
        mime=mimetypes.guess_type(image_path.name)[0] or 'image/png'
        image['src']='data:'+mime+';base64,'+base64.b64encode(image_path.read_bytes()).decode('ascii')
    for paragraph in soup.find_all('p'):
        if '· 해석 범위:' in paragraph.get_text():
            paragraph['class']=['supplement-scope']
    toolbar=BeautifulSoup('''<div class="rr-reader-toolbar" role="group" aria-label="리포트 읽기 설정"><button data-rr-depth="summary" aria-pressed="false">요약</button><button data-rr-depth="standard" aria-pressed="true">표준</button><button data-rr-depth="detail" aria-pressed="false">상세</button><button class="rr-concepts-toggle" aria-pressed="true">개념 설명 펼침</button></div>''','html.parser')
    soup.find('h1').insert_after(toolbar)
    policy=(plugin/'policy.test-build.cjs').read_text(encoding='utf-8')
    script='''(() => {const exports={};\n'''+policy+'''\nlet depth='standard', concepts=true;
    const root=document.querySelector('.markdown-preview-view');
    function setOpen(el,open){if(!el.classList.contains('is-collapsible'))return;el.classList.toggle('is-collapsed',!open);el.querySelector(':scope > .callout-title').setAttribute('aria-expanded',String(open));}
    function apply(){root.dataset.depth=depth;root.querySelectorAll('[data-callout]').forEach(el=>{const val=exports.desiredOpen(el.dataset.callout,depth,concepts);if(val!==null)setOpen(el,val);});document.querySelectorAll('[data-rr-depth]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.rrDepth===depth)));}
    root.querySelectorAll('.is-collapsible>.callout-title').forEach(label=>{const toggle=()=>setOpen(label.parentElement,label.parentElement.classList.contains('is-collapsed'));label.addEventListener('click',toggle);label.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();toggle();}});});
    document.querySelectorAll('[data-rr-depth]').forEach(btn=>btn.addEventListener('click',()=>{depth=btn.dataset.rrDepth;apply();}));
    document.querySelector('.rr-concepts-toggle').addEventListener('click',e=>{concepts=!concepts;if(depth==='detail')depth='standard';e.target.textContent=concepts?'개념 설명 펼침':'개념 설명 접힘';e.target.setAttribute('aria-pressed',String(concepts));apply();});
    root.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',e=>{const target=document.getElementById(a.getAttribute('href').slice(1));if(!target)return;e.preventDefault();let el=target.parentElement;while(el){if(el.classList.contains('callout'))setOpen(el,true);el=el.parentElement;}target.scrollIntoView({block:'start'});}));apply();})();'''
    return '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Markdown reading capture</title><style>'+HOST_CSS+(plugin/'styles.css').read_text(encoding='utf-8')+'</style></head><body class="theme-light"><div class="capture-label">'+escape(markdown.name)+' · 실제 Markdown 렌더링 + 플러그인 CSS <span>／ Obsidian 앱 실행 화면이 아닌 읽기 화면 검증용입니다.</span></div><main class="markdown-preview-view figure-first-report">'+str(soup)+'</main><script>'+script+'</script></body></html>'


def capture(markdown: Path, plugin: Path, output: Path) -> list[dict]:
    from playwright.sync_api import sync_playwright
    output.mkdir(parents=True,exist_ok=True)
    html=render_markdown_preview(markdown,plugin)
    (output/'Markdown_Reading_Preview.html').write_text(html,encoding='utf-8')
    records=[]
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium'))
        for width,height,label in [(1220,1020,'desktop'),(430,932,'mobile')]:
            context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1.5)
            context.set_offline(True);page=context.new_page();errors=[];requests=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
            page.set_content(html);page.wait_for_load_state('load');page.evaluate('document.fonts.ready')
            def check(name,success):
                records.append({'viewport':label,'check':name,'passed':bool(success)})
                assert success,f'{label}: {name}'
            check('Markdown image loaded',page.locator('img').first.evaluate('(el)=>el.complete&&el.naturalWidth>0'))
            check('No horizontal overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
            sup=page.locator('[data-callout="rr-supplement"]').first
            check('Supplement is collapsed in standard', 'is-collapsed' in sup.get_attribute('class'))
            page.screenshot(path=str(output/f'Markdown_{label}_Overview.png'))
            sup.evaluate('(el)=>window.scrollTo(0,scrollY+el.getBoundingClientRect().top-innerHeight*0.66)')
            page.screenshot(path=str(output/f'Markdown_{label}_Supplement_Closed.png'))
            before=page.evaluate('window.scrollY')
            sup.locator(':scope > .callout-title').click()
            check('Supplement expands locally', 'is-collapsed' not in sup.get_attribute('class'))
            check('Click does not navigate to a distant anchor',abs(page.evaluate('window.scrollY')-before)<5)
            check('Supplement image and interpretation visible',sup.locator('img').is_visible() and sup.get_by_role('heading',name='과학적으로 어떻게 해석되는가').is_visible())
            sup.evaluate('(el)=>window.scrollTo(0,scrollY+el.getBoundingClientRect().top-28)')
            page.screenshot(path=str(output/f'Markdown_{label}_Supplement_Open.png'))
            page.locator('[data-rr-depth="summary"]').click()
            check('Summary preserves critical notes',page.locator('[data-callout="rr-critical"]').evaluate_all('(els)=>els.every(el=>el.offsetHeight>0)'))
            check('Supplement scopes visible in summary',page.locator('p.supplement-scope').evaluate_all('(els)=>els.every(el=>el.offsetHeight>0)'))
            page.locator('[data-rr-depth="detail"]').click()
            check('Detail opens supplement',not ('is-collapsed' in sup.get_attribute('class')))
            page.locator('[data-rr-depth="standard"]').click()
            sup.locator(':scope > .callout-title').focus();page.keyboard.press('Enter')
            check('Keyboard opens supplement',not ('is-collapsed' in sup.get_attribute('class')))
            check('No external requests',not requests);check('No JavaScript errors',not errors)
            context.close()
        browser.close()
    (output/'markdown-browser-checks.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    return records

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=root/'verification/phase2')
    args=parser.parse_args()
    results=capture(root/'DemoVault/Papers/DEMO.md',root/'plugin',args.out)
    print(f'{len(results)} Markdown-derived browser checks passed. This is not native Obsidian integration.')
