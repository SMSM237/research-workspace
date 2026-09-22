import copy,json
from pathlib import Path
import pytest
from figure_reports.worker_runtime import LocalWorker
from figure_reports.worker_queue import digest
from figure_reports.publication import make_report,validate_presentation,publish
from figure_reports.build import build_report,ModifiedOutputError


def setup(tmp):
    import pymupdf
    vault=tmp/'vault';vault.mkdir();p=tmp/'main.pdf'
    with pymupdf.open() as d:
        page=d.new_page();page.insert_text((40,50),'Test paper 2024. Author Example. Control and treatment are independent.');d.save(p)
    w=LocalWorker(vault,tmp/'state');job=w.queue.enqueue(p,[]);w.tick();job=w.queue.get(job['id'])
    a=dict(document_id='D001',page=1,kind='text',excerpt='Control and treatment are independent.')
    b=dict(text='대조군과 처치군을 구분합니다.',anchors=[a]);u=dict(id='F1',label='Figure 1',kind='main',document_id='D001',page=1,extra_pages=[],panels=['a'])
    f=dict(figure_id='F1',title='시험 그림',question='조건을 비교합니다.',takeaway=b,panels=[dict(label='a',observation='조건이 나뉩니다.',anchors=[a])],author_interpretation=[b],analyst_inference=[b],methods=[b],replicates=dict(reported_n='미보고',independent_unit='미보고',technical_nesting='미보고',pairing='미보고',uncertainty='미보고'),limitations=[b],terms=[],concepts=[])
    n=dict(text='해석 범위를 구분합니다.',figure_ids=['F1'])
    packet=dict(report_id=job['report_id'],source_fingerprint=job['fingerprint'],source_map=dict(figures=[u],other_evidence=[],missing_material=['별도 서플 미제공']),findings=[f],critical_review=dict(findings=[]),models_used=['test-only'],revision=dict(takeaway=n,question=n,design=[n],integration=[n],applications=[n],review_actions=[]))
    presentation=dict(metadata=dict(title='Test paper',journal='Test journal',year=None,authors=['Author Example'],affiliations=['미확인'],doi=None,keywords='시험 논문',anchors=[a]),standalone=[],supplement_links=[],concept_diagrams=[])
    return w,job,packet,presentation


def test_generic_report_roundtrip_and_modified_output_protection(tmp_path):
    w,j,packet,p=setup(tmp_path);stage=tmp_path/'stage'
    report=make_report(packet,p,j['bundle'],stage);assert report['paper']['year'] is None
    built=build_report(report,stage,w.vault);md=w.vault/built['markdown'];assert '연도 미확인' in md.read_text('utf-8')
    assert len(report['figures'])==1 and report['summary']['critical_limitations']
    md.write_text(md.read_text('utf-8')+'\nUSER NOTE','utf-8')
    changed=copy.deepcopy(report);changed['paper']['subtitle']='changed'
    with pytest.raises(ModifiedOutputError):build_report(changed,stage,w.vault)
    assert md.read_text('utf-8').endswith('USER NOTE')


def test_long_paper_title_preserved_with_compact_windows_filename(tmp_path):
    w,j,packet,p=setup(tmp_path)
    p['metadata'].update(title='A complete scientific title '*12,keywords='topological morphogenesis; neuroepithelial organoid; epithelial fusion; retinoic acid; reduced Gaussian rigidity; lysophosphatidic acid')
    stage=tmp_path/('s'*30)/('t'*20)
    data=make_report(packet,p,j['bundle'],stage)
    assert data['paper']['title']==p['metadata']['title']
    assert len(data['paper']['library_title'])<=72
    result=build_report(data,stage,stage)
    assert (stage/result['markdown']).read_text('utf-8')


def test_compact_report_omits_evidence_dump_but_preserves_table(tmp_path):
    from figure_reports.render import render_markdown
    w,j,packet,p=setup(tmp_path);data=make_report(packet,p,j['bundle'],tmp_path/'stage')
    data['standalone']=[dict(id='abstract-extra',title='Abstract',blocks=[dict(text='DUPLICATE_ABSTRACT_DUMP',refs=[])]),dict(id='table-extra',title='Table 1 · 조건 비교',blocks=[dict(text='KEEP_TABLE_EXPLANATION',refs=[])],image=data['figures'][0]['image'])]
    text=render_markdown(data)
    assert 'DUPLICATE_ABSTRACT_DUMP' not in text and '독립 근거 ·' not in text
    assert 'KEEP_TABLE_EXPLANATION' in text and '### Table 1' in text
    assert len(data['standalone'])==2


def test_complete_requires_actual_published_files_and_hash_readback(tmp_path,monkeypatch):
    import figure_reports.publication as module
    w,j,packet,p=setup(tmp_path);notes=w.vault/'Notes';notes.mkdir();(notes/'mine.md').write_text('KEEP')
    monkeypatch.setattr(module,'integrate_findings',lambda *a:packet)
    monkeypatch.setattr(module.FigurePipeline,'reviewed_call',lambda *a,**k:p)
    receipt=publish(w,None,j,{},packet,{},'',Path(j['folder'])/'model-analysis')
    assert w.queue.get(j['id'])['state']=='complete'
    assert all(digest(w.vault/rel)==sha for rel,sha in receipt['files'].items())
    assert digest(w.vault/f'Sources/{j["report_id"]}/D001.pdf')==j['source_hashes'][0]
    assert (notes/'mine.md').read_text()=='KEEP'


def test_selected_pdf_links_to_published_report(tmp_path,monkeypatch):
    import shutil
    import figure_reports.publication as module
    w,j,packet,p=setup(tmp_path)
    library=w.vault/'PDF';library.mkdir()
    original=library/'selected.pdf';shutil.copyfile(j['main'],original)
    monkeypatch.setattr(module,'sync_publication',lambda *args:{'status':'pending_git'})
    receipt=module.publish_checked(w,j,packet,p,Path(j['folder'])/'model-analysis')
    links=json.loads((w.vault/'Dashboard/pdf-links.json').read_text('utf-8'))
    assert links['links']['PDF/selected.pdf']==receipt['markdown']
    assert (w.vault/receipt['markdown']).is_file()


def test_explicit_auto_policy_resumes_prepared_without_new_permission(tmp_path,monkeypatch):
    from figure_reports.analysis_pipeline import FigurePipeline
    from figure_reports.model_adapter import require_consent
    w,j,packet,p=setup(tmp_path);w.auto_publish=True;w.model_executable='test-only';called=[]
    def run(self,job):
        require_consent(job,json.loads((Path(job['folder'])/'consent.json').read_text('utf-8')))
        called.append(job['id']);w.queue.update(job['id'],state='complete',stage='complete')
    monkeypatch.setattr(FigurePipeline,'run',run);w.tick();w.tick()
    assert called==[j['id']]


def test_missing_evidence_or_diagram_is_rejected(tmp_path):
    w,j,packet,p=setup(tmp_path);pages={('D001',1):'Control and treatment are independent.'}
    validate_presentation(p,packet,pages)
    packet['source_map']['other_evidence']=[dict(title='Table 1',document_id='D001',page=1)]
    with pytest.raises(ValueError):validate_presentation(p,packet,pages)


def test_korean_concept_schematic_is_real_image(tmp_path):
    from figure_reports.publication import schematic
    from PIL import Image
    path=tmp_path/'concept.png';schematic(path,'독립 반복',dict(steps=['독립된 개체를 관찰합니다.','같은 개체의 반복 측정과 구분합니다.'],links=['실험 단위를 구분'],caption='설명용'))
    with Image.open(path) as im:assert im.width==1050 and im.height>400


def with_concept(packet,presentation):
    packet['findings'][0]['concepts']=[dict(title='독립 반복',definition='실험 단위를 구분합니다.',why_here='반복 수의 의미를 읽습니다.',schematic_description='개체와 같은 개체의 여러 측정을 구분합니다.',interpretive_limit='시야를 독립 개체로 세지 않습니다.',basis='general_reasoning')]
    presentation['concept_diagrams']=[dict(figure_id='F1',concept_index=0,steps=['개체','반복 측정'],links=['구분'],caption='제작 내용 설계',essential=True)]


def test_report_preparation_never_draws_python_concept_fallback(tmp_path,monkeypatch):
    import figure_reports.publication as module
    w,j,packet,p=setup(tmp_path);with_concept(packet,p)
    def prohibited(*args):raise AssertionError('Python fallback must not run')
    monkeypatch.setattr(module,'schematic',prohibited)
    stage=tmp_path/'stage';data=make_report(packet,p,j['bundle'],stage)
    assert len(data['concepts'])==1 and 'visual' not in data['concepts'][0]
    assert not list(stage.rglob('concept-*.png'))


def test_publication_requires_complete_generated_images_even_without_request_sidecar(tmp_path):
    from figure_reports.publication import publish_checked
    w,j,packet,p=setup(tmp_path);with_concept(packet,p)
    with pytest.raises(ValueError,match='complete.*concept image'):
        publish_checked(w,j,packet,p,Path(j['folder'])/'candidate')
    assert not list((w.vault/'Papers').glob('*.md'))
