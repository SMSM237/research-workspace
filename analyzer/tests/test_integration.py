import copy
import pytest
from figure_reports.integration import apply_revision,text_paths

def fixture():
    anchor={'document_id':'D001','page':1,'kind':'text','excerpt':'source evidence'}
    packet={'findings':[{'figure_id':'F1','title':'fixed','panels':[{'label':'a','observation':'old','anchors':[anchor]}]}],
            'critical_review':{'findings':[{'figure_id':'F1','anchors':[dict(anchor,page=2)]}]}}
    narrative={'text':'Integrated explanation','figure_ids':['F1']}
    result={'takeaway':narrative,'question':narrative,'design':[narrative],'integration':[narrative],'applications':[narrative],
            'review_actions':[{'review_index':0,'disposition':'applied','reason':'corrected','patches':[{'path':'/F1/panels/0/observation','text':'corrected'}]}]}
    return packet,result

def test_revision_preserves_raw_panel_identity_and_adds_review_provenance():
    p,r=fixture();raw=copy.deepcopy(p);out=apply_revision(p,r)
    assert p==raw
    assert out['findings'][0]['panels'][0]['label']=='a'
    assert out['findings'][0]['panels'][0]['observation']=='corrected'
    assert len(out['findings'][0]['panels'][0]['anchors'])==2
    assert '/F1/panels/0/label' not in text_paths(p)

@pytest.mark.parametrize('path',['/F1/panels/0/label','/F1/panels/0/anchors/0/excerpt','/F2/panels/0/observation','/F1/../../other'])
def test_identity_source_and_foreign_paths_cannot_be_patched(path):
    p,r=fixture();r['review_actions'][0]['patches'][0]['path']=path
    with pytest.raises(ValueError):apply_revision(p,r)

@pytest.mark.parametrize('indices',[[],[0,0],[1]])
def test_missing_duplicate_and_unknown_review_actions_fail(indices):
    p,r=fixture();r['review_actions']=[dict(r['review_actions'][0],review_index=i) for i in indices]
    with pytest.raises(ValueError):apply_revision(p,r)

def test_invalid_narrative_evidence_fails():
    p,r=fixture();r['takeaway']={'text':'claim','figure_ids':['F9']}
    with pytest.raises(ValueError):apply_revision(p,r)

def test_conflicting_patches_fail_instead_of_last_write_winning():
    p,r=fixture();r['review_actions'][0]['patches'].append({'path':'/F1/panels/0/observation','text':'different'})
    with pytest.raises(ValueError):apply_revision(p,r)
