import pytest
from figure_reports.term_discovery import discover_terms,check_term_resolution
def test_new_paper_unknown_symbol_is_not_filtered_by_a_dictionary():
    x=discover_terms([{'document_id':'D001','page':1,'text':'NEWGENE42 and IFI16 were measured. NEWGENE42 differs from NEWGENE43.'}])
    assert {'NEWGENE42','NEWGENE43','IFI16'} <= {v['term'] for v in x['candidates']}
    t=next(t for t in x['candidates'] if t['term']=='NEWGENE42');assert len(t['occurrences'])==2
def test_missing_disposition_blocks_accounting():
    x=discover_terms([{'document_id':'D001','page':2,'text':'NEWGENE42'}])
    with pytest.raises(ValueError):check_term_resolution(x,[])
def test_unresolved_symbol_is_preserved_without_inventing_a_full_name():
    x=discover_terms([{'document_id':'D001','page':2,'text':'NEWGENE42'}]);c=x['candidates'][0]
    out=check_term_resolution(x,[{'id':c['id'],'status':'unresolved','reason':'Official identifier not confirmed'}]);assert out['unresolved']==1 and out['all_accounted']

def test_explanation_cannot_point_to_a_nonexistent_generated_term():
    x=discover_terms([{'document_id':'D001','page':2,'text':'NEWGENE42'}]);c=x['candidates'][0]
    with pytest.raises(ValueError):
        check_term_resolution(x,[{'id':c['id'],'status':'explained','reason':'Reviewed','term_ids':['absent']}],{'NEWGENE42'})

def test_new_paper_explanations_reach_the_report_without_vpt_dictionary():
    import json
    from pathlib import Path
    from figure_reports.render import render_markdown
    d=json.loads((Path(__file__).resolve().parents[1]/'examples/demo.analysis.json').read_text(encoding='utf-8'))
    d['figures'][0]['observations'][0]['text']='NEWGENE42: synthetic discovery regression example.'
    d['reading_aids']={'terms':[{'symbol':'NEWGENE42','name':'Synthetic test identifier, not a real gene','module':'A new paper-specific module','role':'Regression fixture only','source':'synthetic test fixture','matches':['NEWGENE42'],'note':''}]}
    md=render_markdown(d)
    assert 'Synthetic test identifier, not a real gene' in md and 'A new paper-specific module' in md
