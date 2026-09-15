"""Chat UI exchange: explicit local validation/publication; never hidden web/API calls."""
from pathlib import Path
from datetime import datetime,timezone
import copy,json,re
from jsonschema import Draft202012Validator,ValidationError
from .analysis_pipeline import (obj,arr,TEXT,ANCHOR,STATEMENT,quote_matches,INVENTORY_SCHEMA,unit_schema,EvidencePage,
    indexed_corpus,repair_source_anchors,validate_inventory,validate_unit)
from .integration import SCHEMA as REVISION_SCHEMA,apply_revision
from .publication import SCHEMA as PRESENTATION_SCHEMA,validate_presentation,publish_checked
from .worker_queue import digest
from .worker_runtime import atomic_json
from .build import atomic_write

UNIT=unit_schema({'id':'placeholder'});UNIT['properties']['figure_id']=TEXT
CHAT_REVISION=copy.deepcopy(REVISION_SCHEMA)
for key in ['takeaway','question','design','integration','applications']:
    shape=CHAT_REVISION['properties'][key]
    if shape.get('type')=='array':shape=shape['items']
    shape['properties']['anchors']=arr(ANCHOR)
SCHEMA=obj({'source_fingerprint':TEXT,'source_map':INVENTORY_SCHEMA,'findings':arr(UNIT),
    'revision':CHAT_REVISION,'presentation':PRESENTATION_SCHEMA})
SCHEMA['properties']['editorial_notes']=arr(STATEMENT)


def load_sources(job):
    bundle=Path(job['bundle']).resolve();inv=json.loads((bundle/'inventory.json').read_text('utf-8'));pages={}
    def file(rel):
        path=(bundle/rel).resolve()
        if not path.is_relative_to(bundle):raise ValueError('원문 경로가 묶음 밖을 가리킵니다.')
        return path
    hashes=[]
    for doc in inv['documents']:
        if digest(file(doc['original_path']))!=doc['sha256']:raise ValueError('원본 PDF 식별값이 다릅니다.')
        hashes.append(doc['sha256'])
        for page in doc['pages']:
            blocks=json.loads(file(page['blocks_path']).read_text('utf-8'))
            pages[doc['id'],page['file_page']]=EvidencePage(file(page['text_path']).read_text('utf-8'),[b['text'] for b in blocks])
    if sorted(hashes)!=sorted(job['source_hashes']):raise ValueError('다른 자료 묶음입니다.')
    return inv,pages


def export_packet(job,destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    inv,pages=load_sources(job);documents=[]
    for doc in inv['documents']:
        if not re.fullmatch(r'D[0-9]+',doc['id']):raise ValueError('잘못된 원문 식별자')
        rel=doc['id']+'.pdf';raw=(Path(job['bundle'])/doc['original_path']).read_bytes();atomic_write(destination/rel,raw)
        documents.append({'document_id':doc['id'],'file':rel,'sha256':doc['sha256'],'pages':len(doc['pages'])})
    atomic_write(destination/'source-blocks.txt',indexed_corpus(pages).encode('utf-8'))
    atomic_json(destination/'response.schema.json',SCHEMA)
    previous=Path(job['folder'])/'model-analysis/source-map.json'
    record=dict(version=1,source_fingerprint=job['fingerprint'],documents=documents,
        source_blocks_sha256=digest(destination/'source-blocks.txt'),known_inventory=json.loads(previous.read_text('utf-8')) if previous.exists() else None)
    atomic_json(destination/'request.json',record)
    return record


def validate_response(job,value,model_label):
    try:Draft202012Validator(SCHEMA).validate(value)
    except ValidationError as exc:raise ValueError('Chat 결과 형식 오류: '+exc.message) from exc
    if value['source_fingerprint']!=job['fingerprint']:raise ValueError('다른 논문의 Chat 결과입니다.')
    inv,pages=load_sources(job)
    checked,repairs=repair_source_anchors(value,pages)
    def check_direct(item):
        if isinstance(item,dict):
            for a in item.get('anchors',[]):
                key=(a['document_id'],a['page'])
                if key not in pages or (a['kind']=='text' and not quote_matches(pages[key],a['excerpt'])):
                    raise ValueError('통합/범위 설명의 원문 근거가 일치하지 않습니다.')
            for child in item.values():check_direct(child)
        elif isinstance(item,list):
            for child in item:check_direct(child)
    check_direct(checked['revision']);check_direct(checked.get('editorial_notes',[]))
    source_map=checked['source_map'];validate_inventory(source_map,pages)
    units={u['id']:u for u in source_map['figures']};findings=checked['findings']
    ids=[f['figure_id'] for f in findings]
    if len(ids)!=len(set(ids)) or set(ids)!=set(units):raise ValueError('Figure 결과가 누락되었거나 중복됩니다.')
    previous=Path(job['folder'])/'model-analysis/source-map.json'
    if previous.exists():
        known=json.loads(previous.read_text('utf-8'))
        for unit in known['figures']:
            incoming=units.get(unit['id'],{}).get('panels',[])
            alias=len(unit['panels'])==len(incoming)==1 and set(unit['panels']+incoming).issubset({'whole','unlettered'})
            if alias and unit['panels']!=incoming:repairs.append(dict(figure_id=unit['id'],original=unit['panels'],replacement=incoming,policy='single unlettered panel alias'))
            if unit['id'] not in units or (not alias and not set(unit['panels']).issubset(incoming)):
                raise ValueError('기존에 발견된 Figure·패널이 누락되었습니다: '+unit['id'])
    for finding in findings:
        validate_unit(finding,units[finding['figure_id']],pages)
        if not finding['question'].strip() or not finding['takeaway']['text'].strip() or any(not p['observation'].strip() for p in finding['panels']):
            raise ValueError('질문·핵심 결과·패널 설명은 비워둘 수 없습니다.')
    packet=dict(version=1,report_id=job['report_id'],source_fingerprint=job['fingerprint'],source_map=source_map,
        findings=findings,models_used=[model_label],auth_method='chatgpt_browser',
        critical_review={'findings':[],'status':'no_independent_model_review'})
    packet=apply_revision(packet,checked['revision'])
    if checked.get('editorial_notes'):packet['editorial_notes']=checked['editorial_notes']
    validate_presentation(checked['presentation'],packet,pages)
    return packet,checked['presentation'],repairs


def publish_response(worker,job,response_path,chat_url,model_label):
    if not re.fullmatch(r'https://chatgpt\.com/c/[a-zA-Z0-9-]+',chat_url):raise ValueError('실제 Chat 대화 주소가 필요합니다.')
    if not model_label.strip():raise ValueError('화면에서 확인한 모델 표시 또는 미확인 표시가 필요합니다.')
    path=Path(response_path)
    if path.stat().st_size>10*1024*1024:raise ValueError('Chat 결과 파일이 너무 큽니다.')
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('중복 JSON 키: '+key)
            value[key]=item
        return value
    raw=path.read_bytes();value=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=unique)
    packet,presentation,repairs=validate_response(job,value,model_label)
    # Separate immutable Chat responses from earlier CLI results.
    import hashlib
    folder=Path(job['folder'])/'chat-analysis'/hashlib.sha256(raw).hexdigest()[:20]
    folder.mkdir(parents=True,exist_ok=True);atomic_write(folder/'response.json',raw)
    atomic_json(folder/'provenance.json',dict(chat_url=chat_url,model_label=model_label,
        received_at=datetime.now(timezone.utc).isoformat(),source_fingerprint=job['fingerprint'],
        response_sha256=hashlib.sha256(raw).hexdigest(),source_anchor_repairs=repairs,
        review_scope='schema, source identity, page/panel coverage and literal anchor checks; no claim of expert scientific validation'))
    atomic_json(folder/'checked-findings.json',packet)
    return publish_checked(worker,job,packet,presentation,folder)
