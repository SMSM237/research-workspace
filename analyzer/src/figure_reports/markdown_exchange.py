"""Versioned Markdown exchange; parsing, source checks and rendering use no model.

Only structural metadata and reading aids use small JSON fences. All main analysis
is Markdown. Unknown/duplicate/missing blocks fail closed instead of losing prose.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy, hashlib, json, re
from .chat_exchange import load_sources, validate_response
from .analysis_pipeline import indexed_corpus
from .build import atomic_write
from .worker_runtime import atomic_json
from .worker_queue import digest

FORMAT = 'paper-markdown/1'
PROMPT_VERSION = '2026-09-11.3'
HEADER = re.compile(r'^## [^\n]+ \{#([A-Za-z0-9_.()-]+)\}\s*$', re.M)
REF = re.compile(r'\[@(D[0-9]+):([0-9]+):(image|B[0-9]{4}|text\|[^\]\n]+)\]')
FIGREF = re.compile(r'\[@([A-Za-z][A-Za-z0-9_-]*)\]')
SEPARATOR = '\n\n---\n\n'


def merge_fragments(fragments, *, replace_keys=()):
    """Join saved response parts; replacing an existing block is always explicit.

    Caller keeps original parts; this function never truncates/rewrites a block.
    A partial final block remains invalid until replaced by a complete block.
    """
    blocks={};allowed=set(replace_keys);used=set()
    for fragment in fragments:
        text=fragment.removeprefix('\ufeff').replace('\r\n','\n');matches=list(HEADER.finditer(text))
        if not matches or text[:matches[0].start()].strip():raise ValueError('블록 경계에서 이어쓰십시오.')
        for i,m in enumerate(matches):
            key=m[1];raw=text[m.start():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
            if key in blocks and raw!=blocks[key]:
                if key not in allowed:raise ValueError('교체 승인 목록에 없는 중복 블록: '+key)
                used.add(key)
            blocks[key]=raw
    if used!=allowed:raise ValueError('교체할 기존 블록이 없거나 수정되지 않았습니다: '+', '.join(allowed-used))
    end=blocks.pop('end',None)
    return '\n\n'.join([*blocks.values(),*([end] if end else [])])+'\n'


def strict_json(text):
    def unique(pairs):
        value={}
        for key,item in pairs:
            if key in value:raise ValueError('중복 JSON 키: '+key)
            value[key]=item
        return value
    match=re.fullmatch(r'```json\s*\n(.*?)\n```',text.strip(),re.S)
    if not match:raise ValueError('구조 정보는 하나의 json 코드 블록이어야 합니다.')
    try:return json.loads(match[1],object_pairs_hook=unique)
    except (json.JSONDecodeError,TypeError) as exc:raise ValueError('구조 정보 JSON 오류: '+str(exc)) from exc


def parse_markdown(text):
    if not isinstance(text,str) or '\x00' in text or '\ufffd' in text:raise ValueError('손상된 Markdown 문자')
    text=text.removeprefix('\ufeff').replace('\r\n','\n')
    matches=list(HEADER.finditer(text))
    if not matches or text[:matches[0].start()].strip():raise ValueError('형식 밖의 본문이 있습니다. 삭제하지 말고 해당 블록에 넣으십시오.')
    blocks={}
    for i,m in enumerate(matches):
        key=m[1]
        if key in blocks:raise ValueError('중복 Markdown 블록: '+key)
        blocks[key]=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].strip()
    if matches[-1][1]!='end':raise ValueError('완료 블록이 없거나 뒤에 추가 내용이 있습니다.')
    def take(key):
        if key not in blocks:raise ValueError('누락된 Markdown 블록: '+key)
        value=blocks.pop(key)
        if not value:raise ValueError('빈 Markdown 블록: '+key)
        return value
    meta_raw=take('metadata')
    meta_match=re.fullmatch(r'(```json\s*\n.*?\n```)([\s\S]*)',meta_raw,re.S)
    if not meta_match:raise ValueError('서지 구조 정보 오류')
    meta=strict_json(meta_match[1]);notes_raw=meta_match[2].strip()
    expected={'format','source_fingerprint','source_map','metadata','supplement_links'}
    if not isinstance(meta,dict) or set(meta)!=expected or meta['format']!=FORMAT:raise ValueError('지원하지 않거나 잘못된 Markdown 메타데이터')
    def statement(raw):
        anchors=[]
        def replace(m):
            kind=m[3];anchors.append(dict(document_id=m[1],page=int(m[2]),kind='image' if kind=='image' else 'text',
                excerpt='' if kind=='image' else '@'+kind if kind.startswith('B') else kind[5:]))
            return ''
        body=REF.sub(replace,raw).strip()
        if '[@' in body or not body or not anchors:raise ValueError('문장에 올바른 원문 근거가 필요합니다: '+body[:100])
        return dict(text=body,anchors=anchors)
    def narrative(raw):
        ids=[]
        def replace(m):
            if m[1] not in ids:ids.append(m[1])
            return ''
        body=FIGREF.sub(replace,raw).strip();direct=None
        if REF.search(body):direct=statement(body);body=direct['text']
        if '[@' in body or not body or not ids:raise ValueError('통합 문장에 Figure 근거가 필요합니다.')
        result=dict(text=body,figure_ids=ids)
        if direct:result['anchors']=direct['anchors']
        return result
    def rows(key,fn):return [fn(x) for x in take(key).split(SEPARATOR)]
    revision=dict(takeaway=narrative(take('takeaway')),question=narrative(take('question')),
        design=rows('design',narrative),integration=rows('integration',narrative),applications=rows('applications',narrative),review_actions=[])
    findings=[];diagrams=[]
    try:units=meta['source_map']['figures'];extras=meta['source_map']['other_evidence']
    except (KeyError,TypeError) as exc:raise ValueError('Figure/독립 근거 목록 누락') from exc
    for unit in units:
        fid=unit['id'];data=strict_json(take(fid+'.data'))
        if set(data)!={'title','image_readable','replicates','terms','concepts','diagrams'}:raise ValueError('Figure 구조 정보 항목 오류: '+fid)
        f={k:data[k] for k in ['title','image_readable','replicates','terms','concepts']}
        question=take(fid+'.question')
        if '[@' in question:raise ValueError('Figure 질문의 근거는 핵심 결론에서 연결합니다.')
        f.update(figure_id=fid,question=question,takeaway=statement(take(fid+'.takeaway')),panels=[],additional_panels=[])
        for label in unit['panels']:
            p=statement(take(fid+'.panel.'+label));f['panels'].append(dict(label=label,observation=p['text'],anchors=p['anchors']))
        for key in ['author_interpretation','analyst_inference','methods','limitations']:f[key]=rows(fid+'.'+key,statement)
        for i,d in enumerate(data['diagrams']):
            if set(d)!={'steps','links','caption','essential'}:raise ValueError('도식 구조 정보 항목 오류')
            diagrams.append(dict(figure_id=fid,concept_index=i,**d))
        findings.append(f)
    standalone=[dict(evidence_index=i,title=e['title'],blocks=rows(f'E{i}.body',statement)) for i,e in enumerate(extras)]
    end=strict_json(take('end'))
    if not isinstance(end,dict) or set(end)!={'complete','unresolved'} or end['complete'] is not True or end['unresolved']!=[]:
        raise ValueError('미완료 분석입니다. 저장 후 누락 항목만 이어서 처리하십시오.')
    if blocks:raise ValueError('처리하지 못한 본문 블록: '+', '.join(blocks))
    result=dict(source_fingerprint=meta['source_fingerprint'],source_map=meta['source_map'],findings=findings,revision=revision,
        presentation=dict(metadata=meta['metadata'],supplement_links=meta['supplement_links'],standalone=standalone,concept_diagrams=diagrams))
    if notes_raw:result['editorial_notes']=[statement(x) for x in notes_raw.split(SEPARATOR)]
    return result


def compose_example(value):
    """Lossless serialization for contract examples and migration, not AI analysis."""
    chunks=[]
    def put(key,title,text):chunks.append(f'## {title} {{#{key}}}\n\n{text}\n')
    def code(data):return '```json\n'+json.dumps(data,ensure_ascii=False,indent=2)+'\n```'
    def stmt(b):
        refs=[]
        for a in b['anchors']:
            source='image' if a['kind']=='image' else a['excerpt'].lstrip('@') if re.fullmatch(r'@?B[0-9]{4}',a['excerpt']) else 'text|'+a['excerpt']
            if ']' in source or '\n' in source:raise ValueError('문단 식별자로 인용하십시오.')
            refs.append(f'[@{a["document_id"]}:{a["page"]}:{source}]')
        return b['text']+' '+''.join(refs)
    def narrative(b):return (stmt(b) if b.get('anchors') else b['text'])+' '+''.join('[@'+fid+']' for fid in b['figure_ids'])
    p=value['presentation'];revision=value['revision']
    put('metadata','서지·자료 범위',code(dict(format=FORMAT,source_fingerprint=value['source_fingerprint'],source_map=value['source_map'],metadata=p['metadata'],supplement_links=p['supplement_links'])))
    if value.get('editorial_notes'):chunks[-1]+='\n'+SEPARATOR.join(stmt(x) for x in value['editorial_notes'])+'\n'
    for key,title in [('question','01 · 연구 질문'),('takeaway','01 · 핵심 결론')]:put(key,title,narrative(revision[key]))
    for key,title in [('design','02 · 연구 설계'),('integration','04 · 통합 해석'),('applications','05 · 연구 활용')]:put(key,title,SEPARATOR.join(narrative(b) for b in revision[key]))
    for f in value['findings']:
        fid=f['figure_id'];data={k:f[k] for k in ['title','image_readable','replicates','terms','concepts']}
        data['diagrams']=[{k:d[k] for k in ['steps','links','caption','essential']} for d in p['concept_diagrams'] if d['figure_id']==fid]
        put(fid+'.data',fid+' · 읽기 정보',code(data));put(fid+'.question',fid+' · 질문',f['question']);put(fid+'.takeaway',fid+' · 핵심 결론',stmt(f['takeaway']))
        for panel in f['panels']:put(fid+'.panel.'+panel['label'],fid+' · 패널 '+panel['label'],stmt(dict(text=panel['observation'],anchors=panel['anchors'])))
        for key,title in [('author_interpretation','저자 해석'),('analyst_inference','분석자 해석'),('methods','Methods'),('limitations','한계')]:
            put(fid+'.'+key,fid+' · '+title,SEPARATOR.join(stmt(b) for b in f[key]))
    for e in p['standalone']:put(f'E{e["evidence_index"]}.body',e['title'],SEPARATOR.join(stmt(b) for b in e['blocks']))
    put('end','완료',code(dict(complete=True,unresolved=[])))
    return '\n'.join(chunks)


def publish_markdown(worker,job,path,chat_url,model_label,*,history=None,visual_bundle=None):
    from .publication import publish_checked
    if not re.fullmatch(r'https://chatgpt\.com/c/[a-zA-Z0-9-]+',chat_url):raise ValueError('실제 Chat 대화 주소가 필요합니다.')
    if not model_label.strip():raise ValueError('실제 화면의 모델 표시를 기록하십시오.')
    path=Path(path)
    request_path=path.parent/'request.json'
    request=json.loads(request_path.read_text('utf-8')) if request_path.exists() else {}
    if request and request.get('source_fingerprint')!=job['fingerprint']:raise ValueError('Chat request belongs to another paper')
    if request.get('require_concept_images') and visual_bundle is None:raise ValueError('Chat concept images must be generated and reviewed before publication')
    if path.stat().st_size>10*1024*1024:raise ValueError('분석 파일 크기 초과')
    raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
    folder=Path(job['folder'])/'chat-markdown'/sha[:20];folder.mkdir(parents=True,exist_ok=True)
    # Keep invalid/truncated originals too, so recovery never starts from scratch.
    atomic_write(folder/'analysis.md',raw)
    value=parse_markdown(raw.decode('utf-8-sig'));packet,presentation,repairs=validate_response(job,value,model_label)
    atomic_json(folder/'derived.json',value)
    provenance=dict(format=FORMAT,prompt_version=PROMPT_VERSION,chat_url=chat_url,model_label=model_label,
        received_at=datetime.now(timezone.utc).isoformat(),source_fingerprint=job['fingerprint'],markdown_sha256=sha,
        conversion='deterministic_python_no_model_call',source_anchor_repairs=repairs,
        validation='structure, source identity, literal anchors, declared coverage; semantic and visual claims still require source review')
    artifacts={'chat-analysis.md':raw}
    if history is not None:
        if set(history)!={'initial','patches'} or not isinstance(history['initial'],str) or not isinstance(history['patches'],list):
            raise ValueError('Invalid Chat correction history')
        reconstructed=history['initial']
        for patch in history['patches']:
            if set(patch)!={'text','replace_keys'}:raise ValueError('Invalid Chat correction entry')
            reconstructed=merge_fragments([reconstructed,patch['text']],replace_keys=patch['replace_keys'])
        if reconstructed!=raw.decode('utf-8-sig').replace('\r\n','\n'):raise ValueError('Chat history does not reproduce the accepted result')
        atomic_write(folder/'history.json',json.dumps(history,ensure_ascii=False,indent=2).encode('utf-8'))
        artifacts['chat-history.json']=(folder/'history.json').read_bytes()
        provenance['history_sha256']=digest(folder/'history.json')
        provenance['initial_text_sha256']=hashlib.sha256(history['initial'].encode()).hexdigest()
        provenance['corrected_blocks']=[key for patch in history['patches'] for key in patch['replace_keys']]
    atomic_write(folder/'provenance.json',json.dumps(provenance,ensure_ascii=False,indent=2).encode('utf-8'))
    artifacts['chat-provenance.json']=(folder/'provenance.json').read_bytes()
    if visual_bundle:
        artifacts['chat-visuals.json']=json.dumps({name:json.loads((Path(visual_bundle)/name).read_text('utf-8')) for name in ['concept-images.json','reviewed-images.json']},ensure_ascii=False,indent=2).encode()
    return publish_checked(worker,job,packet,presentation,folder,artifacts=artifacts,visual_bundle=visual_bundle)


def export_markdown_packet(job,destination):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    inv,pages=load_sources(job);documents=[]
    for doc in inv['documents']:
        if not re.fullmatch(r'D[0-9]+',doc['id']):raise ValueError('원문 식별자 오류')
        rel=doc['id']+'.pdf';atomic_write(destination/rel,(Path(job['bundle'])/doc['original_path']).read_bytes())
        documents.append(dict(document_id=doc['id'],file=rel,sha256=doc['sha256'],pages=len(doc['pages'])))
    atomic_write(destination/'source-blocks.txt',indexed_corpus(pages).encode('utf-8'))
    prompt=(Path(__file__).parent/'resources/chat-analysis-prompt.md').read_bytes()
    atomic_write(destination/'analysis-instructions.md',prompt)
    previous=Path(job['folder'])/'model-analysis/source-map.json'
    request=dict(format=FORMAT,prompt_version=PROMPT_VERSION,require_concept_images=True,prompt_sha256=hashlib.sha256(prompt).hexdigest(),source_fingerprint=job['fingerprint'],documents=documents,
        known_inventory=json.loads(previous.read_text('utf-8')) if previous.exists() else None,
        source_blocks_sha256=digest(destination/'source-blocks.txt'))
    atomic_json(destination/'request.json',request)
    return request


def main():
    import argparse, sys
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    from .worker_queue import JobQueue
    from .worker_runtime import LocalWorker
    p=argparse.ArgumentParser(description='Chat Markdown export/check/publish; no AI/API calls')
    p.add_argument('action',choices=['export','check','publish']);p.add_argument('--state',required=True);p.add_argument('--job',required=True)
    p.add_argument('--path',required=True);p.add_argument('--vault');p.add_argument('--chat-url');p.add_argument('--model-label',default='UI model not recorded');p.add_argument('--visual-bundle')
    a=p.parse_args();job=JobQueue(a.state).get(a.job)
    if not job:p.error('job not found')
    if a.action=='export':result=export_markdown_packet(job,a.path)
    elif a.action=='check':
        validate_response(job,parse_markdown(Path(a.path).read_text('utf-8-sig')),a.model_label);result={'structural_source_checks':'pass','scientific_validation':'not_asserted'}
    else:
        if not a.vault or not a.chat_url:p.error('--vault and --chat-url required')
        result=publish_markdown(LocalWorker(a.vault,a.state),job,a.path,a.chat_url,a.model_label,visual_bundle=a.visual_bundle)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
