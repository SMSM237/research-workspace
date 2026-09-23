import json
from pathlib import Path
import pytest
from figure_reports.build import build_report
from figure_reports.render import render_markdown
ROOT=Path(__file__).resolve().parents[1]
def data():return json.loads((ROOT/'examples/demo.analysis.json').read_text(encoding='utf-8'))
def test_library_filename_and_metadata_readback(tmp_path):
    d=data();d['paper']['library_title']='[Journal] 논문 핵심 키워드';d['paper']['bibliography']={'journal':'Journal','impact_factor':None,'impact_factor_year':None,'quartiles':[],'author_affiliations':['A — University'],'metric_source':'unverified','metric_checked':'2026-09-09'}
    p=build_report(d,ROOT/'assets',tmp_path)
    assert p['markdown']=='Paper reports/[Journal] 논문 핵심 키워드.md'
    md=(tmp_path/p['markdown']).read_text(encoding='utf-8');assert 'journal: "Journal"' in md and 'impact_factor: null' in md
    assert json.loads((tmp_path/p['manifest']).read_text(encoding='utf-8'))['markdown_path']==p['markdown']
    assert build_report(d,ROOT/'assets',tmp_path)==p
@pytest.mark.parametrize('title',['../bad','a/b','a\\b','a:bad','a#bad','a?bad','a.'])
def test_unsafe_library_title_rejected(title,tmp_path):
    d=data();d['paper']['library_title']=title
    with pytest.raises(ValueError):build_report(d,ROOT/'assets',tmp_path)
    assert not list(tmp_path.rglob('*.md'))
def test_design_items_are_bullets_without_losing_words():
    d=data();md=render_markdown(d)
    for block in d['design']['blocks']:assert '- '+block['text'] in md
