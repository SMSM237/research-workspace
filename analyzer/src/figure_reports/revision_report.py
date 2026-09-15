"""Map reviewed findings into an existing reader contract without changing assets."""
import copy
import hashlib
import json
from .validate import _refs, validate_report


def revised_report(packet, base):
    data=copy.deepcopy(base)
    figures={f['id']:f for f in data['figures']}
    expected={'fig-'+f['figure_id'].lower() for f in packet['findings']}
    if expected != set(figures):
        raise ValueError('Revision must preserve the complete source figure inventory')
    sources={s['id']:s for s in data['sources']}

    def anchor_refs(anchors):
        result=[]
        for a in anchors:
            key='anchor-'+hashlib.sha256(json.dumps(a,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
            sources[key]={'id':key,'kind':'main_text' if a['document_id']=='D001' else 'supplementary_figure',
                'document_id':a['document_id'],'page':a['page'],'section':'그림 판독' if a['kind']=='image' else '본문·캡션·Methods',
                'locator':f"{a['document_id']} · 파일 p.{a['page']} · "+('그림 판독' if a['kind']=='image' else '원문 구절'),
                'note':a['excerpt'] if a['kind']=='text' else '해당 원문 페이지 이미지와 패널을 판독한 근거입니다. 텍스트 인용이 아닙니다.'}
            if key not in result:result.append(key)
        return result

    def block(value):return {'text':value['text'],'refs':anchor_refs(value['anchors'])}
    for finding in packet['findings']:
        f=figures['fig-'+finding['figure_id'].lower()]
        f['question']={'text':finding['question'],'refs':[f['image']['source_ref']]}
        f['takeaway']=block(finding['takeaway'])
        f['panels']=[p['label'] for p in finding['panels']]
        f['panel_groups']=[{'panels':[p['label']],'reading':p['observation'],'refs':anchor_refs(p['anchors'])} for p in finding['panels']]
        f['observations']=[{'text':p['label']+' · '+p['observation'],'refs':anchor_refs(p['anchors'])} for p in finding['panels']]
        for target,origin in [('author_interpretation','author_interpretation'),('scientific_interpretation','analyst_inference'),('limitations','limitations'),('methods','methods')]:
            f[target]=[block(v) for v in finding[origin]]
        refs=list(dict.fromkeys(r for m in f['methods'] for r in m['refs']))
        labels={'reported_n':'보고된 반복 수','independent_unit':'독립 실험 단위','technical_nesting':'기술 반복과 중첩','pairing':'대응 구조','uncertainty':'불확실성'}
        f['methods'] += [{'text':labels[k]+' · '+v,'refs':refs} for k,v in finding['replicates'].items()]

    def narrative(v):
        refs=anchor_refs(v.get('anchors',[]))
        for fid in v['figure_ids']:
            f=figures['fig-'+fid.lower()]
            refs.extend(f['takeaway']['refs']);refs.append(f['image']['source_ref'])
        refs=list(dict.fromkeys(refs))
        key='synthesis-'+hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:16]
        sources[key]={'id':key,'kind':'main_text','locator':'종합 근거 · '+', '.join(v['figure_ids']),
            'note':'여러 Figure를 연결한 종합 해석입니다. 각 Figure의 관찰·Methods·해석 범위에서 개별 근거를 확인할 수 있습니다. '+
                ' / '.join(sources[r]['locator']+': '+sources[r]['note'] for r in refs)}
        return {'text':v['text'],'refs':[key]}
    revision=packet['revision']
    for key in ['takeaway','question']:data['summary'][key]=narrative(revision[key])
    data['design']['blocks']=[narrative(v) for v in revision['design']]
    for key in ['integration','applications']:data[key]=[narrative(v) for v in revision[key]]
    if packet.get('editorial_notes'):
        data['standalone'].append(dict(id='chat-scope',title='자료 범위에 대한 모델 설명 · 별도 검증 완료를 뜻하지 않습니다',blocks=[block(v) for v in packet['editorial_notes']]))
    data['sources']=list(sources.values())
    return data


def rebuild_coverage(data):
    targets={k:data[k] for k in ['summary','design','integration','applications']}
    for k in ['figures','concepts','standalone']:targets.update({v['id']:v for v in data[k]})
    used={k:set(_refs(v)) for k,v in targets.items()}
    previous={c['source_id']:c for c in data['coverage']}
    data['coverage']=[]
    for source in data['sources']:
        sid=source['id'];links=[k for k,refs in used.items() if sid in refs]
        old=previous.get(sid,{})
        status=('context_only' if source['kind']=='background' else 'analyzed') if links else old.get('status','not_analyzed')
        if not links and status in ['analyzed','context_only']:status='not_analyzed'
        data['coverage'].append({'source_id':sid,'status':status,'linked_to':links,
            'reason':'본문 연결 범위의 기록이며 과학적 정확성 인증을 뜻하지 않습니다.' if links else old.get('reason','이번 통합 본문에서 직접 인용하지 않은 이전 배경 자료입니다.')})
    validate_report(data)
    return data
