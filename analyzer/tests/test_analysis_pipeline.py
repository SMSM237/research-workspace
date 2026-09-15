import copy
import pytest
from figure_reports.analysis_pipeline import validate_inventory,validate_unit

PAGES={('D001',1):'The control samples were measured separately.'}
UNIT=dict(id='F1',document_id='D001',page=1,extra_pages=[],panels=['a','b'])
ANCHOR=dict(document_id='D001',page=1,kind='text',excerpt='control samples were measured')

def value():return dict(figure_id='F1',image_readable=True,additional_panels=[],panels=[dict(label=p,observation='test',anchors=[copy.deepcopy(ANCHOR)]) for p in ['a','b']])

def test_each_panel_and_literal_source_anchor_required():
    v=value();validate_unit(v,UNIT,PAGES)
    v['panels'].pop()
    with pytest.raises(ValueError):validate_unit(v,UNIT,PAGES)

def test_hallucinated_quotes_and_unseen_images_fail():
    v=value();v['panels'][0]['anchors'][0]['excerpt']='invented statistical significance'
    with pytest.raises(ValueError):validate_unit(v,UNIT,PAGES)
    v=value();v['panels'][0]['anchors'][0].update(kind='image',page=2)
    with pytest.raises(ValueError):validate_unit(v,UNIT,{**PAGES,('D001',2):'other page'})

def test_empty_anchors_and_extra_panels_fail():
    v=value();v['panels'][0]['anchors']=[]
    with pytest.raises(ValueError):validate_unit(v,UNIT,PAGES)
    v=value();v['additional_panels']=['c']
    with pytest.raises(ValueError):validate_unit(v,UNIT,PAGES)

def test_inventory_source_pages_cannot_be_omitted_or_invented():
    inventory=dict(reviewed_pages=[dict(document_id='D001',page=1)],figures=[UNIT],other_evidence=[])
    validate_inventory(inventory,PAGES)
    with pytest.raises(ValueError):validate_inventory(inventory,{**PAGES,('D001',2):'missing'})
    inventory['figures'][0]=dict(UNIT,id='../escape')
    with pytest.raises(ValueError):validate_inventory(inventory,PAGES)


def test_completed_stage_keeps_its_recorded_model_when_default_changes(tmp_path):
    import json
    from figure_reports.analysis_pipeline import FigurePipeline
    from figure_reports.model_adapter import CodexSubscription
    (tmp_path/'request-record.json').write_text(json.dumps(dict(status='validated',model='gpt-6-astra',effort='high')))
    pipe=FigurePipeline(None,CodexSubscription('codex',model='gpt-5.6-sol'))
    assert pipe.backend_for(tmp_path).model=='gpt-6-astra'
    assert pipe.backend_for(tmp_path/'new').model=='gpt-5.6-sol'


def test_astra_escalation_is_limited_to_explicit_conflicts():
    from figure_reports.critical_review import select_difficult
    simple={'figure_id':'F1','limitations':[{'text':'독립 donor 수가 보고되지 않았습니다.'}]}
    conflict={'figure_id':'F2','limitations':[{'text':'축과 Methods의 단위가 불일치합니다.'}]}
    assert select_difficult([simple,conflict])==[conflict]


def test_column_layout_matches_contiguous_block_but_not_invented_join():
    from figure_reports.analysis_pipeline import EvidencePage,quote_matches
    page=EvidencePage('The control Other column samples were measured.',
                      ['The control samples were measured.','Other column'])
    assert quote_matches(page,'control samples were measured')
    assert not quote_matches(page,'measured. Other column')
    assert not quote_matches(page,'The control samples were not measured')
    assert not quote_matches(EvidencePage('Another page',[]),'control samples were measured')


def test_quote_validation_reports_all_invalid_anchors():
    v=value()
    v['panels'][0]['anchors'][0]['excerpt']='invented one'
    v['panels'][1]['anchors'][0]['excerpt']='invented two'
    with pytest.raises(ValueError) as error:validate_unit(v,UNIT,PAGES)
    assert 'invented one' in str(error.value) and 'invented two' in str(error.value)

def test_cross_page_quote_splits_only_literal_adjacent_block_boundaries():
    from figure_reports.analysis_pipeline import EvidencePage,split_boundary_anchors
    pages={('D001',1):EvidencePage('', ['A broader role affecting multiple']),('D001',2):EvidencePage('', ['pathways. Other findings follow.'])}
    v=value();v['panels'][0]['anchors'][0]['excerpt']='broader role affecting multiple pathways'
    v['panels'][1]['anchors'][0]['excerpt']='broader role affecting multiple'
    fixed,log=split_boundary_anchors(v,pages)
    assert len(log)==1 and len(fixed['panels'][0]['anchors'])==2
    assert fixed['panels'][0]['anchors'][1]['page']==2
    assert fixed['panels'][0]['anchors'][1]['excerpt']=='pathways'
    assert len(v['panels'][0]['anchors'])==1  # original model output stays immutable
    validate_unit(fixed,UNIT,pages)

def test_cross_page_repair_rejects_invention_nonadjacent_or_ambiguous_sources():
    from figure_reports.analysis_pipeline import EvidencePage,split_boundary_anchors
    v=value();v['panels'][0]['anchors'][0]['excerpt']='broader role affecting multiple pathways'
    p=EvidencePage('', ['A broader role affecting multiple'])
    for pages in [{('D001',1):p,('D001',3):EvidencePage('', ['pathways.'])},
                  {('D001',1):p,('D002',2):EvidencePage('', ['pathways.'])},
                  {('D001',1):p,('D001',2):EvidencePage('', ['not pathways.'])},
                  {('D001',1):p,('D001',2):EvidencePage('', ['pathways.','pathways again.'])}]:
        fixed,log=split_boundary_anchors(v,pages)
        assert fixed==v and not log


def test_same_page_two_columns_split_into_independent_literal_anchors():
    from figure_reports.analysis_pipeline import EvidencePage,split_boundary_anchors
    pages={('D001',1):EvidencePage('interleaved column text', ['pathways, including VEGFR.', 'A broader role affecting multiple'])}
    v=value();v['panels'][0]['anchors'][0]['excerpt']='broader role affecting multiple pathways'
    v['panels'][1]['anchors'][0]['excerpt']='broader role affecting multiple'
    fixed,log=split_boundary_anchors(v,pages)
    validate_unit(fixed,UNIT,pages)
    assert len(log)==1 and [a['page'] for a in fixed['panels'][0]['anchors']]==[1,1]


def test_short_literal_anchor_expands_only_unique_complete_token_on_same_page():
    from figure_reports.analysis_pipeline import repair_source_anchors,quote_matches,EvidencePage
    pages={('D001',1):EvidencePage('WIPI11 formation of autophagosomes',[])}
    original={'anchors':[dict(document_id='D001',page=1,kind='text',excerpt='WIPI11')]}
    fixed,audit=repair_source_anchors(original,pages)
    assert len(audit)==1 and quote_matches(pages['D001',1],fixed['anchors'][0]['excerpt'])
    assert fixed['anchors'][0]['excerpt'].startswith('WIPI11 ')
    assert original['anchors'][0]['excerpt']=='WIPI11'
    for text in ['WIPI111 formation of autophagosomes','WIPI11 and WIPI11','WIPI1 formation of autophagosomes']:
        p={('D001',1):EvidencePage(text,[])}
        assert repair_source_anchors(original,p)==(original,[])
    assert repair_source_anchors(original,{('D001',2):pages['D001',1]})==(original,[])


def test_short_literal_expansion_does_not_jump_blocks_or_invent_context():
    from figure_reports.analysis_pipeline import repair_source_anchors,EvidencePage,quote_matches
    original={'anchors':[dict(document_id='D001',page=1,kind='text',excerpt='64 μL')]}
    pages={('D001',1):EvidencePage('mixture composed of 64 μL fibrinogen',[])}
    fixed,audit=repair_source_anchors(original,pages)
    assert len(audit)==1 and quote_matches(pages['D001',1],fixed['anchors'][0]['excerpt'])
    assert repair_source_anchors(original,{('D001',1):EvidencePage('64 μL',[])})==(original,[])


def test_source_repair_precedes_model_correction_and_records_audit(tmp_path):
    from figure_reports.analysis_pipeline import FigurePipeline,repair_source_anchors,EvidencePage,quote_matches
    class Backend:
        def run(self,*args):return {'anchors':[dict(document_id='D001',page=1,kind='text',excerpt='WIPI11')]}
    class Worker:stop=None
    pages={('D001',1):EvidencePage('WIPI11 formation of autophagosomes',[])}
    def validate(value):
        if not quote_matches(pages['D001',1],value['anchors'][0]['excerpt']):raise ValueError('short quote')
    result=FigurePipeline(Worker(),Backend()).reviewed_call({}, {}, 'prompt', [], {},tmp_path,validate,lambda v:repair_source_anchors(v,pages))
    validate(result)
    assert (tmp_path/'source-anchor-repairs.json').exists()
    assert not (tmp_path/'correction-layout-v2').exists()


def test_checked_checkpoint_is_preserved_instead_of_rebuilt_from_an_older_response(tmp_path):
    import json
    from figure_reports.analysis_pipeline import FigurePipeline
    folder=tmp_path/'F1';folder.mkdir();path=folder/'source-checked.json'
    path.write_text(json.dumps({'wording':'retained later correction'}));before=path.read_bytes()
    class Backend:
        def run(self,*args):return {'wording':'older raw response'}
    class Queue:
        def completed(self,job,stage):assert stage=='figure_F1';return path
    class Worker:queue=Queue();stop=None
    result=FigurePipeline(Worker(),Backend()).reviewed_call({'id':'job'}, {}, 'prompt',[],{},folder,lambda v:None)
    assert result['wording']=='retained later correction' and path.read_bytes()==before


def test_changed_validation_diagnostic_uses_new_correction_cache(tmp_path):
    from figure_reports.analysis_pipeline import FigurePipeline
    calls=[]
    class Backend:
        def run(self,job,consent,prompt,images,schema,folder,stop):calls.append(folder);return {'ok':len(calls)>1}
    class Worker:stop=None
    (tmp_path/'correction-layout-v2').mkdir()
    marker=tmp_path/'correction-layout-v2/validated.json';marker.write_text('historical response')
    def validate(value):
        if not value['ok']:raise ValueError('clear updated diagnostic')
    assert FigurePipeline(Worker(),Backend()).reviewed_call({}, {}, 'prompt',[],{},tmp_path,validate)['ok']
    assert calls[1].parent.name=='correction-source-v4' and marker.read_text()=='historical response'

def test_block_ids_resolve_to_exact_source_and_preserve_claim():
    from figure_reports.analysis_pipeline import EvidencePage,repair_source_anchors,indexed_corpus
    pages={('D001',1):EvidencePage('Raw text',['The control samples were measured separately.','Axis'])}
    v=value();v['panels'][0]['anchors'][0]['excerpt']='@B0000'
    fixed,audit=repair_source_anchors(v,pages)
    assert fixed['panels'][0]['anchors'][0]['excerpt']=='The control samples were measured separately.'
    assert fixed['panels'][0]['observation']==v['panels'][0]['observation']
    assert v['panels'][0]['anchors'][0]['excerpt']=='@B0000' and len(audit)==1
    assert '@B0000' in indexed_corpus(pages)
    validate_unit(fixed,UNIT,pages)
    v['panels'][0]['anchors'][0]['excerpt']='@B9999'
    with pytest.raises(ValueError):validate_unit(repair_source_anchors(v,pages)[0],UNIT,pages)
    v['panels'][0]['anchors'][0]['excerpt']='@B0001'
    with pytest.raises(ValueError):validate_unit(repair_source_anchors(v,pages)[0],UNIT,pages)


def test_anchor_recovery_selects_only_literal_blocks_and_rejects_unsupported_claim(tmp_path):
    from types import SimpleNamespace
    from figure_reports.analysis_pipeline import FigurePipeline,EvidencePage,repair_source_anchors
    class Backend:
        supported=True
        def run(self,*args):return {'corrections':[dict(index=0,supported=self.supported,document_id='D001',page=1,block_id='@B0000')]}
    backend=Backend();pipe=FigurePipeline(SimpleNamespace(stop=None),backend)
    pages={('D001',1):EvidencePage('The control samples were measured separately.',['The control samples were measured separately.'])}
    v=value();v['panels'][0]['anchors'][0]['excerpt']='a paraphrase that is not a quote'
    fixed,audit=pipe.recover_anchors({}, {}, v,pages,tmp_path)
    validate_unit(repair_source_anchors(fixed,pages)[0],UNIT,pages)
    assert fixed['panels'][0]['observation']==v['panels'][0]['observation'] and audit
    backend.supported=False
    with pytest.raises(ValueError):pipe.recover_anchors({}, {},v,pages,tmp_path)


def test_source_block_prefix_alias_is_canonicalized_without_inventing_text():
    from figure_reports.analysis_pipeline import EvidencePage,repair_source_anchors
    pages={('D001',1):EvidencePage('Original text',['Original text'])}
    value={'text':'unchanged claim','anchors':[{'document_id':'D001','page':1,'kind':'text','excerpt':'B0000'}]}
    fixed,audit=repair_source_anchors(value,pages)
    assert fixed['anchors'][0]['excerpt']=='Original text' and fixed['text']=='unchanged claim'
    assert value['anchors'][0]['excerpt']=='B0000' and len(audit)==1
