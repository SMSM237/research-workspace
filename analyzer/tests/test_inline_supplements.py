import copy
import json
import re
from pathlib import Path
import pytest
from figure_reports.render import render_markdown, render_html

ROOT = Path(__file__).resolve().parents[1]
@pytest.fixture
def report():
    return json.loads((ROOT / 'examples/demo.analysis.json').read_text(encoding='utf-8'))

def test_supplement_is_local_collapsed_before_next_main(report):
    md=render_markdown(report)
    assert '> [!rr-supplement]- Figure S1' in md
    assert md.index('[!rr-supplement]- Figure S1') < md.index('### Figure 2')
    assert '연결해서 읽기 · Figure S1' not in md
    assert md.count('![Figure S1') == 1

def test_critical_supplement_limits_are_outside_fold(report):
    md=render_markdown(report)
    sup=next(f for f in report['figures'] if f['kind']=='supplementary')
    for limitation in sup['limitations']:
        line=next(line for line in md.splitlines() if limitation['text'] in line)
        assert not line.startswith('>'), 'A collapsed supplement may not hide its critical scope'

def test_no_supplement_is_left_as_top_level_figure(report):
    md=render_markdown(report)
    assert not re.search(r'^### Figure S\d', md, re.M)

def test_shared_supplement_is_local_in_both_contexts_with_unique_anchors(report):
    report['figures'][1]['related_figures']=['fig-s1']
    html=render_html(report, ROOT/'assets')
    assert html.count('data-kind="rr-supplement"')==2
    ids=re.findall(r'\bid="([^"]+)"',html)
    assert len(ids)==len(set(ids))
    assert 'id="fig-s1"' in html and 'id="fig-s1-at-fig-2"' in html

def test_supplements_use_numeric_not_lexical_order(report):
    base=report['figures'][2]
    for number in [10,2]:
        sup=copy.deepcopy(base);sup['id']=f'fig-s{number}';sup['label']=f'Figure S{number}'
        report['figures'].append(sup)
    report['figures'][0]['related_figures']=['fig-s10','fig-s2','fig-s1']
    md=render_markdown(report)
    assert md.index('[!rr-supplement]- Figure S1 ') < md.index('[!rr-supplement]- Figure S2 ') < md.index('[!rr-supplement]- Figure S10 ')

def test_unlinked_supplement_kept_collapsed(report):
    report['figures'][0]['related_figures']=[]
    report['figures'][2]['related_figures']=[]
    md=render_markdown(report)
    assert '독립 Supplementary' in md
    assert md.count('[!rr-supplement]- Figure S1')==1

def test_preview_reveal_opens_supplement_target_itself(report):
    from playwright.sync_api import sync_playwright
    import os, shutil
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or shutil.which('chromium'))
        page=browser.new_page()
        page.set_content(render_html(report,ROOT/'assets'))
        page.locator('.fig-nav a[href="#fig-s1"]').click()
        assert page.locator('#fig-s1').evaluate('(el)=>el.open')
        browser.close()

def test_numbered_figure_order_ignores_numbers_inside_captions():
    from figure_reports.layout import figure_number
    assert figure_number({'label':'Figure S2 | 14 day response'})[0]==2
    assert figure_number({'label':'Extended Data Fig. 3 | 2024 experiment'})[0]==3
    assert figure_number({'label':'Fig. 1 | 3D imaging'})[0]==1
