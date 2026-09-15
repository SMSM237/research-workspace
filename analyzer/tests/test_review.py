from hashlib import sha256
import copy
import pytest
import fitz
from figure_reports.review import validate_review


@pytest.fixture
def packet(tmp_path):
    pdf=fitz.open();pdf.new_page();pdf.new_page();pdf.save(tmp_path/'main.pdf');pdf.close()
    (tmp_path/'figure.png').write_bytes(b'reviewed image bytes')
    report={'report_id':'P1','sources':[{'id':'s1','document_id':'D1','page':2}], 'figures':[{'id':'f1','panels':['a','b'],'image':{'path':'figure.png','source_ref':'s1'},'limitations':[{'text':'pending biological unit'}]}]}
    ledger={'version':'1','report_id':'P1','documents':[{'document_id':'D1','filename':'main.pdf','pages':2,'sha256':sha256((tmp_path/'main.pdf').read_bytes()).hexdigest()}],
            'inventory':[{'figure_id':'f1','panels':['a','b'],'document_id':'D1','page':2,'visual_review':'model_self_review','image_path':'figure.png','image_sha256':sha256(b'reviewed image bytes').hexdigest()}]}
    return report,ledger,tmp_path


def test_reviewed_source_and_image_integrity(packet):
    r,l,p=packet; validate_review(r,l,p,p)


@pytest.mark.parametrize('change',['missing_figure','missing_panel','pending','source_changed','image_changed','page','path_escape'])
def test_review_rejects_stale_or_incomplete_evidence(packet,change):
    r,l,p=packet
    if change=='missing_figure': r['figures']=[]
    if change=='missing_panel': r['figures'][0]['panels']=['a']
    if change=='pending': l['inventory'][0]['visual_review']='pending'
    if change=='source_changed': (p/'main.pdf').write_bytes(b'new source')
    if change=='image_changed': (p/'figure.png').write_bytes(b'new crop')
    if change=='page': l['inventory'][0]['page']=3
    if change=='path_escape': l['documents'][0]['filename']='../outside.pdf'
    with pytest.raises(ValueError): validate_review(r,l,p,p)


@pytest.mark.parametrize('change',['duplicate_report_id','source_page_mismatch','source_document_mismatch','invented_page_count','boolean_page'])
def test_review_binds_report_to_real_source(packet,change):
    r,l,p=packet
    if change=='duplicate_report_id':r['figures'].append(copy.deepcopy(r['figures'][0]))
    if change=='source_page_mismatch':r['sources'][0]['page']=1
    if change=='source_document_mismatch':r['sources'][0]['document_id']='D2'
    if change=='invented_page_count':l['documents'][0]['pages']=100
    if change=='boolean_page':l['inventory'][0]['page']=True
    with pytest.raises(ValueError):validate_review(r,l,p,p)
