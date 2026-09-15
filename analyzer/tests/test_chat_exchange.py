import copy,json
from pathlib import Path
import pytest
from test_publication import setup
from figure_reports.chat_exchange import export_packet,validate_response,publish_response
from figure_reports.worker_queue import digest

def fixture(tmp):
 w,j,packet,p=setup(tmp)
 source=copy.deepcopy(packet['source_map']);source.update(paper_title='Test paper',journal='Test journal',reviewed_pages=[{'document_id':'D001','page':1}])
 findings=copy.deepcopy(packet['findings']);findings[0].update(image_readable=True,additional_panels=[])
 value=dict(source_fingerprint=j['fingerprint'],source_map=source,findings=findings,revision=packet['revision'],presentation=p)
 return w,j,value

def test_chat_export_contains_exact_source_blocks_and_output_contract(tmp_path):
 w,j,value=fixture(tmp_path);out=tmp_path/'export';result=export_packet(j,out)
 assert result['source_fingerprint']==j['fingerprint']
 assert 'Control and treatment' in (out/'source-blocks.txt').read_text('utf-8')
 assert (out/'response.schema.json').exists()
 assert digest(out/'D001.pdf')==j['source_hashes'][0]

def test_chat_response_validates_all_source_pages_panels_and_identity(tmp_path):
 w,j,value=fixture(tmp_path)
 packet,p,repairs=validate_response(j,value,'Chat UI High (model not shown)')
 assert packet['models_used']==['Chat UI High (model not shown)']
 for field in ['fingerprint','page','panel','quote','readable','duplicate']:
  bad=copy.deepcopy(value)
  if field=='fingerprint':bad['source_fingerprint']='other'
  if field=='page':bad['source_map']['reviewed_pages']=[]
  if field=='panel':bad['findings'][0]['panels']=[]
  if field=='quote':bad['findings'][0]['takeaway']['anchors'][0]['excerpt']='not present in the source'
  if field=='readable':bad['findings'][0]['image_readable']=False
  if field=='duplicate':bad['findings'].append(copy.deepcopy(bad['findings'][0]))
  with pytest.raises(ValueError):validate_response(j,bad,'test')

def test_chat_full_local_publication_preserves_originals_notes_and_edit_guard(tmp_path,monkeypatch):
 import figure_reports.publication as publication
 w,j,value=fixture(tmp_path);response=tmp_path/'response.json';response.write_text(json.dumps(value,ensure_ascii=False),'utf-8')
 (w.vault/'Notes').mkdir();(w.vault/'Notes/keep.md').write_text('my notes')
 monkeypatch.setattr(publication,'sync_publication',lambda *a:{'status':'not_configured'})
 receipt=publish_response(w,j,response,'https://chatgpt.com/c/00000000-0000-0000-0000-000000000001','UI High')
 assert w.queue.get(j['id'])['state']=='complete'
 assert all(digest(w.vault/k)==v for k,v in receipt['files'].items())
 assert (w.vault/'Notes/keep.md').read_text()=='my notes'
 md=w.vault/receipt['markdown'];md.write_text(md.read_text('utf-8')+' USER EDIT','utf-8')
 from figure_reports.build import ModifiedOutputError
 with pytest.raises(ModifiedOutputError):publish_response(w,j,response,'https://chatgpt.com/c/00000000-0000-0000-0000-000000000001','UI High')
 assert md.read_text('utf-8').endswith('USER EDIT')
