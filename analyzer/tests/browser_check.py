"""Offline Chromium UI validation, NOT an actual Obsidian/device test."""
from pathlib import Path
import json
import os
import shutil
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
HTML=Path(os.environ.get('REPORT_PREVIEW', str(ROOT/'Preview.html')))
VERIFY=ROOT/'verification/phase2'
VERIFY.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium") or None)
    for width,height,label in [(1440,1080,'desktop'),(390,844,'mobile')]:
        context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1)
        context.set_offline(True)
        page=context.new_page(); errors=[]; requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:requests.append(r.url) if r.url.startswith(('http:','https:')) else None)
        # This environment blocks file:// navigation by managed Chromium policy.
        # Render the exact standalone file contents in an offline blank page instead.
        page.set_content(HTML.read_text(encoding='utf-8'));page.wait_for_load_state('load')
        page.screenshot(path=str(VERIFY/f'html-{label}-overview.png'),full_page=False)
        def check(name,condition):
            results.append({'viewport':label,'check':name,'passed':bool(condition)})
            assert condition,f'{label}: {name}'
        check('no horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'))
        broken=page.evaluate('''() => [...document.querySelectorAll('a[href^="#"]')].map(a=>a.getAttribute('href').slice(1)).filter(id=>!document.getElementById(id))''')
        check('every internal link has a destination',not broken)
        check('default standard mode',page.locator('#content').get_attribute('data-mode')=='standard')
        page.get_by_role('button',name='상세',exact=True).click()
        # Lazy images are loaded when their section enters the viewport.
        for image in page.locator('figure img').all():
            image.scroll_into_view_if_needed()
            image.evaluate('(el) => el.decode()')
        check('local figure bytes loaded',page.evaluate('''() => [...document.querySelectorAll('figure img')].every(i=>i.complete && i.naturalWidth>0)'''))
        page.get_by_role('button',name='요약',exact=True).click()
        check('summary collapses narrative',page.locator('details[data-kind="rr-body"][open]').count()==0)
        check('critical caveats stay visible',page.locator('[data-critical="true"]').evaluate_all('(els)=>els.every(el=>el.offsetHeight>0)'))
        check('critical concept stays visible',page.locator('#concept-denominator').is_visible())
        page.get_by_role('button',name='상세',exact=True).click()
        check('detail opens every optional section',page.evaluate('''() => [...document.querySelectorAll('details[data-kind]')].every(el=>el.open)'''))
        page.get_by_role('button',name='표준',exact=True).click()
        page.locator('#concept-toggle').click()
        check('concept button collapses optional concepts',page.locator('details[data-kind="rr-concept"][open]').count()==0)
        page.locator('#concept-toggle').click()
        check('supplements default to collapsed',page.locator('details[data-kind="rr-supplement"][open]').count()==0)
        supplement=page.locator('details[data-kind="rr-supplement"]').first
        supplement.scroll_into_view_if_needed()
        scroll_before=page.evaluate('window.scrollY')
        supplement.locator(':scope > summary').click()
        check('inline supplement opens without navigation',supplement.evaluate('(el)=>el.open') and abs(page.evaluate('window.scrollY')-scroll_before)<5)
        supplement.locator(':scope > summary').click()
        page.locator('#fig-1').scroll_into_view_if_needed()
        page.screenshot(path=str(VERIFY/f'html-{label}-figure-concept.png'),full_page=False)
        page.locator('.figure-zoom').first.click()
        check('image zoom opens dialog',page.locator('#image-dialog').evaluate('(el)=>el.open'))
        page.keyboard.press('Escape')
        check('Escape closes image zoom',not page.locator('#image-dialog').evaluate('(el)=>el.open'))
        page.get_by_role('button',name='요약',exact=True).click()
        page.locator('a[href="#source-demo-fig1"]').first.click()
        check('source navigation opens hidden source section',page.locator('#source-demo-fig1').is_visible())
        check('no external network requests',not requests)
        check('no JavaScript errors',not errors)
        context.close()
    browser.close()
(VERIFY/'html-browser-tests.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'{len(results)} offline browser checks passed. Desktop + mobile viewports; not real-device validation.')
