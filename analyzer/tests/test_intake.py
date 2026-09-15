"""Synthetic input PDFs verify file handling, never paper interpretation."""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
import pytest
import pymupdf as fitz

@pytest.fixture
def source_pdfs(tmp_path):
    main=tmp_path/'main.pdf'
    with fitz.open() as doc:
        page=doc.new_page(width=400,height=520)
        page.insert_text((30,40),'Example paper - SYNTHETIC TEST FIXTURE')
        page.insert_text((30,80),'Results: Figure 1 is cited here; this is not a caption.')
        page=doc.new_page(width=400,height=520)
        page.draw_rect(fitz.Rect(40,50,220,180))
        page.insert_text((30,230),'Figure 1. Synthetic diagram used to test extraction.')
        page.insert_text((30,255),'Methods: This file has no scientific results.')
        doc.new_page(width=400,height=520) # visually unreviewed blank/scanned-like page
        doc.save(main)
    sup=tmp_path/'supplement.pdf'
    with fitz.open() as doc:
        page=doc.new_page(width=400,height=520)
        page.insert_text((30,40),'Supplementary Figure 1. Synthetic supplementary fixture.')
        doc.save(sup)
    return main,sup

def intake_module():
    from figure_reports import intake
    return intake

def test_intake_module_is_available():
    assert importlib.util.find_spec('figure_reports.intake') is not None

def test_intake_preserves_sources_and_explicit_roles(source_pdfs,tmp_path):
    main,sup=source_pdfs; before=main.read_bytes()
    result=intake_module().ingest_bundle(main,[sup],tmp_path/'bundles','P001')
    assert main.read_bytes()==before
    assert result['analysis_status']=='not_started'
    assert [d['role'] for d in result['documents']]==['main','supplementary']
    assert [d['page_count'] for d in result['documents']]==[3,1]
    assert result['documents'][0]['sha256']==hashlib.sha256(before).hexdigest()
    assert not (tmp_path/'bundles/P001/analysis.json').exists()
    terms=json.loads((tmp_path/'bundles/P001/term-candidates.json').read_text(encoding='utf-8'))
    candidate=next(c for c in terms['candidates'] if c['term']=='SYNTHETIC')
    assert candidate['occurrences'][0]['document_id']=='D001' and candidate['occurrences'][0]['page']==1
    assert candidate['status']=='pending_context_review'

def test_page_images_blocks_and_no_false_analysis(source_pdfs,tmp_path):
    result=intake_module().ingest_bundle(*[source_pdfs[0],[source_pdfs[1]]],tmp_path/'bundles','P001')
    root=tmp_path/'bundles/P001'
    assert (root/'.nomedia').exists()
    page=result['documents'][0]['pages'][1]
    assert page['file_page']==2 and page['visual_review']=='pending'
    assert (root/page['image_path']).exists()
    blocks=json.loads((root/page['blocks_path']).read_text(encoding='utf-8'))
    assert any('Figure 1.' in b['text'] and len(b['bbox'])==4 for b in blocks)
    assert result['documents'][0]['pages'][2]['text_status']=='low_text_requires_review'
    assert not any(p['visual_review']=='completed' for d in result['documents'] for p in d['pages'])

def test_figures_and_mentions_remain_candidates(source_pdfs,tmp_path):
    result=intake_module().ingest_bundle(source_pdfs[0],[source_pdfs[1]],tmp_path/'bundles','P001')
    candidates=[c for d in result['documents'] for c in d['figure_candidates']]
    assert any(c['label']=='Figure 1' and c['file_page']==2 for c in candidates)
    assert any(c['label']=='Figure S1' for c in candidates)
    assert all(c['review_status']=='unverified_candidate' for c in candidates)
    assert any(c['detection']=='reference_mention' and c['file_page']==1 for c in candidates)

def test_repeated_identical_supplement_is_deduplicated(source_pdfs,tmp_path):
    main,sup=source_pdfs
    result=intake_module().ingest_bundle(main,[sup,sup],tmp_path/'bundles','P001')
    assert len(result['documents'])==2

def test_conflicting_roles_are_rejected(source_pdfs,tmp_path):
    with pytest.raises(ValueError,match='role|역할'):
        intake_module().ingest_bundle(source_pdfs[0],[source_pdfs[0]],tmp_path/'bundles','P001')

def test_existing_bundle_is_not_overwritten(source_pdfs,tmp_path):
    args=(source_pdfs[0],[],tmp_path/'bundles','P001')
    intake_module().ingest_bundle(*args)
    inventory=tmp_path/'bundles/P001/inventory.json'; before=inventory.read_bytes()
    with pytest.raises(FileExistsError): intake_module().ingest_bundle(*args)
    assert inventory.read_bytes()==before

def test_invalid_ids_and_pdf_fail_without_partial_publish(source_pdfs,tmp_path):
    with pytest.raises(ValueError): intake_module().ingest_bundle(source_pdfs[0],[],tmp_path/'out','../escape')
    bad=tmp_path/'bad.pdf';bad.write_text('NOT A PDF')
    with pytest.raises(ValueError): intake_module().ingest_bundle(bad,[],tmp_path/'out','P002')
    assert not (tmp_path/'out/P002').exists()

def test_encrypted_input_is_not_silently_skipped(tmp_path):
    src=tmp_path/'locked.pdf'
    with fitz.open() as doc:
        doc.new_page();doc.save(src,encryption=fitz.PDF_ENCRYPT_AES_256,owner_pw='owner',user_pw='secret')
    with pytest.raises(ValueError,match='암호|encrypt'):
        intake_module().ingest_bundle(src,[],tmp_path/'out','P003')
    assert not (tmp_path/'out/P003').exists()

def test_events_and_ai_packet_do_not_claim_analysis_complete(source_pdfs,tmp_path):
    intake_module().ingest_bundle(source_pdfs[0],[],tmp_path/'out','P001')
    root=tmp_path/'out/P001'
    events=[json.loads(x) for x in (root/'events.jsonl').read_text(encoding='utf-8').splitlines()]
    assert events[-1]['stage']=='awaiting_analysis'
    assert all('percent' not in x for x in events)
    prompt=(root/'ANALYSIS_TASK.md').read_text(encoding='utf-8')
    assert 'untrusted' in prompt and 'visual_review' in prompt
    assert 'schema' in prompt and (root/'report.schema.json').exists()

def test_explicit_crop_preserves_bbox_and_original(source_pdfs,tmp_path):
    intake=intake_module();intake.ingest_bundle(source_pdfs[0],[],tmp_path/'out','P001')
    root=tmp_path/'out/P001'
    result=intake.crop_evidence(root,'D001',2,[30,35,260,200],'Fig01', 'Figure 1')
    assert result['bbox_points']==[30.0,35.0,260.0,200.0]
    assert result['file_page']==2 and result['document_id']=='D001'
    assert (root/result['image_path']).exists()
    assert result['visual_review']=='pending'
    with pytest.raises(FileExistsError): intake.crop_evidence(root,'D001',2,[30,35,260,200],'Fig01','Figure 1')

def test_invalid_crop_rejected(source_pdfs,tmp_path):
    intake=intake_module();intake.ingest_bundle(source_pdfs[0],[],tmp_path/'out','P001')
    root=tmp_path/'out/P001'
    with pytest.raises(ValueError): intake.crop_evidence(root,'D001',2,[-10,0,800,800],'Fig01','Figure 1')
    with pytest.raises(ValueError): intake.crop_evidence(root,'D001',99,[0,0,50,50],'Fig01','Figure 1')
    with pytest.raises(ValueError): intake.crop_evidence(root,'D001',2,[0,0,50,50],'../bad','Figure 1')
