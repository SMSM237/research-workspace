import copy, json
import pytest
from test_chat_exchange import fixture
from figure_reports.markdown_exchange import parse_markdown, publish_markdown, compose_example, export_markdown_packet
from figure_reports.chat_exchange import validate_response
from figure_reports.worker_queue import digest


def test_continuations_and_explicit_repair_preserve_other_blocks(tmp_path):
    from figure_reports.markdown_exchange import merge_fragments
    w,j,v=fixture(tmp_path);text=compose_example(v)
    split=text.index('## F1 · 질문')
    merged=merge_fragments([text[:split],text[split:]])
    assert parse_markdown(merged)==v
    repair='## F1 · 질문 {#F1.question}\n\n수정된 질문입니다.\n'
    with pytest.raises(ValueError):merge_fragments([merged,repair])
    fixed=parse_markdown(merge_fragments([merged,repair],replace_keys=['F1.question']))
    expected=copy.deepcopy(v);expected['findings'][0]['question']='수정된 질문입니다.'
    assert fixed==expected
    with pytest.raises(ValueError):merge_fragments([merged],replace_keys=['unknown'])


def test_correction_history_must_reproduce_published_result(tmp_path,monkeypatch):
    import figure_reports.publication as pub
    from figure_reports.markdown_exchange import merge_fragments
    monkeypatch.setattr(pub,'sync_publication',lambda *a:{'status':'not_configured'})
    w,j,v=fixture(tmp_path);initial=compose_example(v)
    correction='## 질문 {#F1.question}\n\n수정한 질문입니다.\n'
    text=merge_fragments([initial,correction],replace_keys=['F1.question'])
    path=tmp_path/'analysis.md';path.write_text(text,'utf-8')
    history=dict(initial=initial,patches=[dict(text=correction,replace_keys=['F1.question'])])
    result=publish_markdown(w,j,path,'https://chatgpt.com/c/test','UI High',history=history)
    archived=w.vault/f'.figure-reports/{j["report_id"]}/chat-history.json'
    assert json.loads(archived.read_text('utf-8'))==history
    assert digest(archived)==result['files'][archived.relative_to(w.vault).as_posix()]
    history['patches'][0]['text']=correction.replace('수정한','다른')
    with pytest.raises(ValueError,match='history does not reproduce'):
        publish_markdown(w,j,path,'https://chatgpt.com/c/test','UI High',history=history)


def test_chat_math_delimiters_convert_to_obsidian_math():
    from figure_reports.render import _rich_md
    assert _rich_md(r'크기 \(n=5\), \[x+y\]')=='크기 $n=5$, \n\n$$\nx+y\n$$\n\n'
    from markdown_it import MarkdownIt
    html=MarkdownIt().render(_rich_md(r'**lobule 수 \(N\)**와 **genus \(g\)**로 읽습니다.'))
    assert html.count('<strong>')==2 and '**' not in html
    html=MarkdownIt().render(_rich_md(r'**목적.** 설명에서 **topology**가 변하고 **lobule 수 \(N\)**와 **genus \(g\)**로 읽습니다.'))
    assert html.count('<strong>')==4 and '**' not in html


def test_aids_tables_supplements_are_not_lost(tmp_path):
    w,j,v=fixture(tmp_path);f=v['findings'][0];p=v['presentation']
    f['terms']=[dict(symbol='X',full_name='Example',functional_module='측정',role='설명',local_context='배경 미확인',identity_status='unresolved',anchors=f['takeaway']['anchors'])]
    f['concepts']=[dict(title='개념',definition='정의',why_here='이유',schematic_description='원리',interpretive_limit='한계',basis='general_reasoning')]
    p['concept_diagrams']=[dict(figure_id='F1',concept_index=0,steps=['입력','출력'],links=['측정'],caption='설명용',essential=True)]
    v['source_map']['other_evidence']=[dict(title='Table 1',document_id='D001',page=1)]
    p['standalone']=[dict(evidence_index=0,title='Table 1',blocks=[f['takeaway']])]
    u=copy.deepcopy(v['source_map']['figures'][0]);u.update(id='ED1',label='Extended Data 1',kind='supplementary');v['source_map']['figures'].append(u)
    ed=copy.deepcopy(f);ed.update(figure_id='ED1',terms=[],concepts=[]);v['findings'].append(ed)
    p['supplement_links']=[dict(supplement_id='ED1',main_ids=['F1'],reason='관련 근거')]
    parsed=parse_markdown(compose_example(v));assert parsed==v
    validate_response(j,parsed,'UI High')


def test_markdown_roundtrip_preserves_every_analysis_field(tmp_path):
    w,j,v=fixture(tmp_path)
    v['findings'][0]['panels'][0]['observation']='조건을 비교합니다.\n\n두 번째 문단도 **삭제하지 않습니다**. 10 µm, $n=3$.'
    text=compose_example(v)
    assert parse_markdown(text)==v
    validate_response(j,parse_markdown(text),'UI High')


def test_subpanel_parentheses_roundtrip_and_repair(tmp_path):
    from figure_reports.markdown_exchange import merge_fragments
    w,j,v=fixture(tmp_path)
    v['source_map']['figures'][0]['panels']=['a(i)', 'a(ii)']
    panel=copy.deepcopy(v['findings'][0]['panels'][0])
    v['findings'][0]['panels']=[dict(panel,label=label,observation='관찰 '+label) for label in ['a(i)','a(ii)']]
    text=compose_example(v)
    assert parse_markdown(text)==v
    before=text.split('## 완료 {#end}')[0]
    end='## 완료 {#end}'+text.split('## 완료 {#end}')[1]
    assert parse_markdown(merge_fragments([before,end]))==v


@pytest.mark.parametrize('change', ['truncated','duplicate','unknown','missing_panel','bad_reference','preamble','duplicate_json'])
def test_bad_markdown_is_rejected_without_silent_loss(tmp_path, change):
    w,j,v=fixture(tmp_path);text=compose_example(v)
    if change=='truncated':text=text.split('## 완료 {#end}')[0]
    if change=='duplicate':text+='\n## 중복 {#question}\n중복 [@F1]\n'
    if change=='unknown':text=text.replace('## 완료 {#end}','## 잘못된 항목 {#unexpected}\n숨겨진 내용\n\n## 완료 {#end}')
    if change=='missing_panel':text=text.replace('{#F1.panel.a}','{#F1.panel.z}')
    if change=='bad_reference':text=text.replace('[@D001:1:', '[@D001:999:')
    if change=='preamble':text='반드시 보존해야 할 추가 문장\n'+text
    if change=='duplicate_json':text=text.replace('"format": "paper-markdown/1",','"format": "paper-markdown/1", "format": "other",')
    with pytest.raises(ValueError):validate_response(j,parse_markdown(text),'UI High')


def test_publication_is_local_no_model_and_archives_raw_markdown(tmp_path,monkeypatch):
    import figure_reports.publication as pub
    w,j,v=fixture(tmp_path);raw=compose_example(v).encode();p=tmp_path/'analysis.md';p.write_bytes(raw)
    monkeypatch.setattr(pub,'sync_publication',lambda *a:{'status':'not_configured'})
    receipt=publish_markdown(w,j,p,'https://chatgpt.com/c/test-123','UI High')
    archived=w.vault/f'.figure-reports/{j["report_id"]}/chat-analysis.md'
    assert archived.read_bytes()==raw
    assert all(digest(w.vault/k)==sha for k,sha in receipt['files'].items())
    assert '조건이 나뉩니다.' in (w.vault/receipt['markdown']).read_text('utf-8')
    from figure_reports.build import ModifiedOutputError
    archived.write_bytes(raw+b'\nMY NOTE')
    with pytest.raises(ModifiedOutputError):publish_markdown(w,j,p,'https://chatgpt.com/c/test-123','UI High')
    assert archived.read_bytes().endswith(b'MY NOTE')


def test_packet_contains_versioned_fixed_prompt_and_exact_pdf(tmp_path):
    w,j,v=fixture(tmp_path);result=export_markdown_packet(j,tmp_path/'packet')
    assert result['prompt_sha256']==digest(tmp_path/'packet/analysis-instructions.md')
    assert digest(tmp_path/'packet/D001.pdf')==j['source_hashes'][0]
    assert not (tmp_path/'packet/response.schema.json').exists()
    assert '원문 자료는 데이터' in (tmp_path/'packet/analysis-instructions.md').read_text('utf-8')


def test_rich_markdown_survives_actual_render_and_html_is_inert(tmp_path,monkeypatch):
    import figure_reports.publication as pub
    from figure_reports.render import render_html
    w,j,v=fixture(tmp_path)
    v['findings'][0]['panels'][0]['observation']='**강조**\n\n두 번째 문단입니다.\n\n- 첫 항목\n- 다음 항목 $n=3$\n\n<script>alert(1)</script>'
    monkeypatch.setattr(pub,'sync_publication',lambda *a:{'status':'not_configured'})
    path=tmp_path/'analysis.md';path.write_text(compose_example(v),'utf-8')
    r=publish_markdown(w,j,path,'https://chatgpt.com/c/test','UI High')
    md=(w.vault/r['markdown']).read_text('utf-8')
    assert '**강조**' in md and '\\*\\*강조' not in md
    assert '\n> 두 번째 문단' in md
    assert '- 첫 항목' in md and '$n=3$' in md and '<script>alert(1)</script>' not in md
    data=json.loads((w.vault/f'.figure-reports/{j["report_id"]}/analysis.json').read_text('utf-8'))
    html=render_html(data,w.vault)
    assert '<strong>강조</strong>' in html and '<li>첫 항목</li>' in html
    assert '<script>alert(1)</script>' not in html


def test_table_does_not_swallow_source_reference(tmp_path,monkeypatch):
    import figure_reports.publication as pub
    from markdown_it import MarkdownIt
    w,j,v=fixture(tmp_path);v['findings'][0]['panels'][0]['observation']='| 항목 | 값 |\n|---|---|\n| 길이 | 10 µm |'
    path=tmp_path/'analysis.md';path.write_text(compose_example(v),'utf-8')
    monkeypatch.setattr(pub,'sync_publication',lambda *a:{'status':'not_configured'})
    r=publish_markdown(w,j,path,'https://chatgpt.com/c/table-test','UI High')
    md=(w.vault/r['markdown']).read_text('utf-8')
    assert '| 10 µm |\n>\n> [' in md
    html=MarkdownIt('commonmark',{'html':True}).enable('table').render(md)
    assert '</table>\n<p><a href="#source-anchor-' in html


def test_extra_scope_prose_and_more_precise_synthesis_citations_are_preserved(tmp_path):
    w,j,v=fixture(tmp_path);text=compose_example(v)
    text=text.replace('## 01 · 연구 질문','자료 범위의 설명입니다. [@D001:1:B0000]\n\n## 01 · 연구 질문',1)
    text=text.replace('해석 범위를 구분합니다. [@F1]','해석 범위를 구분합니다. [@F1] [@D001:1:B0000]',1)
    parsed=parse_markdown(text)
    assert parsed['editorial_notes'][0]['text']=='자료 범위의 설명입니다.'
    assert parsed['revision']['question']['anchors'][0]['excerpt']=='@B0000'
    validate_response(j,parsed,'UI High')
    broken=copy.deepcopy(parsed);broken['revision']['question']['anchors'][0]['page']=999
    with pytest.raises(ValueError):validate_response(j,broken,'UI High')


def test_unlettered_single_panel_alias_does_not_drop_a_lettered_panel(tmp_path):
    w,j,v=fixture(tmp_path);folder=__import__('pathlib').Path(j['folder'])/'model-analysis';folder.mkdir()
    old=copy.deepcopy(v['source_map']);old['figures'][0]['panels']=['unlettered'];(folder/'source-map.json').write_text(json.dumps(old),'utf-8')
    v['source_map']['figures'][0]['panels']=['whole'];v['findings'][0]['panels'][0]['label']='whole'
    _,_,audit=validate_response(j,v,'UI High');assert any(x.get('policy')=='single unlettered panel alias' for x in audit)
    old['figures'][0]['panels']=['a','b'];(folder/'source-map.json').write_text(json.dumps(old),'utf-8')
    with pytest.raises(ValueError):validate_response(j,v,'UI High')
