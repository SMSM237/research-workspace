import json,shutil
import pytest
from test_chat_exchange import fixture
from figure_reports.concept_visuals import apply_visuals
from figure_reports.worker_queue import digest

def prepared(tmp_path):
    w,j,v=fixture(tmp_path);bundle=__import__('pathlib').Path(j['bundle']);inv=json.loads((bundle/'inventory.json').read_text('utf-8'))
    folder=tmp_path/'visuals';folder.mkdir();shutil.copyfile(bundle/inv['documents'][0]['pages'][0]['image_path'],folder/'test.png')
    data=dict(report_id=j['report_id'],concepts=[dict(id='concept-f1-0'),dict(id='concept-f1-1')])
    manifest=dict(format='concept-images/1',source_fingerprint=j['fingerprint'],images=[dict(concept_ids=['concept-f1-0','concept-f1-1'],file='test.png',alt='synthetic fixture',caption='test only',status='generated')],pending=[])
    (folder/'concept-images.json').write_text(json.dumps(manifest),'utf-8');(folder/'reviewed-images.json').write_text(json.dumps({'test.png':dict(sha256=digest(folder/'test.png'),visual_scientific_review='pass')}),'utf-8')
    return j,data,folder,manifest

def test_reviewed_image_reused_without_pixel_change(tmp_path):
    j,data,folder,m=prepared(tmp_path);result=apply_visuals(data,j['fingerprint'],folder,tmp_path/'out')
    assert result['complete'] and data['concepts'][0]['visual']['path']==data['concepts'][1]['visual']['path']
    assert digest(tmp_path/'out'/data['concepts'][0]['visual']['path'])==digest(folder/'test.png')

@pytest.mark.parametrize('bad',['fingerprint','modified','traversal','missing','duplicate'])
def test_visual_failures_do_not_publish(tmp_path,bad):
    j,data,folder,m=prepared(tmp_path)
    if bad=='fingerprint':m['source_fingerprint']='other'
    if bad=='modified':(folder/'test.png').write_bytes((folder/'test.png').read_bytes()+b'changed')
    if bad=='traversal':m['images'][0]['file']='../test.png'
    if bad=='missing':m['images'][0]['concept_ids']=['concept-f1-0'];m['pending']=['concept-f1-1']
    if bad=='duplicate':m['images'][0]['concept_ids']=['concept-f1-0','concept-f1-0']
    (folder/'concept-images.json').write_text(json.dumps(m),'utf-8')
    with pytest.raises(ValueError):apply_visuals(data,j['fingerprint'],folder,tmp_path/'out')
    assert not (tmp_path/'out').exists()
