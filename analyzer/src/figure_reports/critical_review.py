"""Escalate explicitly detected evidence conflicts, never all routine Figures."""
import json
from pathlib import Path
import re
from .analysis_pipeline import obj,arr,TEXT,ANCHOR,quote_matches,quote_error,repair_source_anchors,indexed_corpus,BLOCK_GUIDE
from .model_adapter import CodexSubscription
from .worker_runtime import atomic_json

SCHEMA=obj({'reviewed_figures':arr(TEXT),'findings':arr(obj({'figure_id':TEXT,
    'kind':{'enum':['source_conflict','overclaim','uncertainty','no_change']},'finding':TEXT,
    'anchors':arr(ANCHOR),'recommended_wording':TEXT})),
    'summary':TEXT,'status':{'enum':['needs_revision','reviewed_with_limits']}})


def select_difficult(findings):
    return [f for f in findings if any(re.search(r'상충|모순|불일치|충돌|일치하지|서로 다른 기준',x['text']) for x in f['limitations'])]


def review_difficult_findings(worker,backend,job,consent,mapped,findings,pages,corpus,analysis):
    scope=select_difficult(findings)
    decision={'policy':'Sol High default; Astra High only for detected source conflicts',
              'selected_figures':[f['figure_id'] for f in scope],
              'selection_reason':'Explicit conflict language in source-anchored limitations; not general missing metadata'}
    atomic_json(analysis/'review-routing.json',decision)
    if not scope:
        return {'status':'not_requested','reason':'No explicit conflict was detected by this rule; not proof that none exists.'}
    worker.queue.update(job['id'],stage='critical_review',message='Astra High · 확인된 쟁점 검토 중')
    worker.set_status(stage='critical_review',message='Astra High · '+', '.join(decision['selected_figures'])+'의 근거 충돌 검토',
                      figures_done=sum(f['kind']=='main' for f in mapped['figures']),figures_total=sum(f['kind']=='main' for f in mapped['figures']),
                      supplements_done=sum(f['kind']=='supplementary' for f in mapped['figures']),supplements_total=sum(f['kind']=='supplementary' for f in mapped['figures']))
    visual=set()
    for unit in mapped['figures']:
        if unit['id'] in decision['selected_figures']:
            visual.update((unit['document_id'],p) for p in [unit['page'],*unit['extra_pages']])
    images=[analysis/'pages'/f'{doc}-{page}.png' for doc,page in sorted(visual)]
    def validate(value):
        errors=[]
        if set(value['reviewed_figures'])!=set(decision['selected_figures']) or len(value['reviewed_figures'])!=len(scope):
            raise ValueError('쟁점 검토 범위가 요청과 다릅니다.')
        for finding in value['findings']:
            if finding['figure_id'] not in decision['selected_figures'] or not finding['anchors']:
                raise ValueError('쟁점 검토의 Figure 또는 근거가 없습니다.')
            for a in finding['anchors']:
                key=a['document_id'],a['page']
                if key not in pages:raise ValueError('쟁점 검토에 존재하지 않는 페이지가 인용되었습니다.')
                if a['kind']=='image' and key not in visual:raise ValueError('첨부하지 않은 이미지가 인용되었습니다.')
                if a['kind']=='text' and not quote_matches(pages[key],a['excerpt']):
                    errors.append(f"{finding['figure_id']} {key}: {quote_error(pages[key],a['excerpt'])}")
        if errors:raise ValueError('쟁점 검토 인용 오류:\n'+'\n'.join(dict.fromkeys(errors)))
    prompt=('한국어 존댓말로 답하십시오. 앞 단계가 표시한 쟁점을 원문·첨부 이미지에서 다시 검토하십시오. '
            '다른 모델의 주장을 정답으로 받아들이지 마십시오. 실제 상충, 단순 미보고, 과잉 해석을 구분하고 '
            '수정할 문장을 제안하십시오. 원문이 밝히지 않은 단위/표본수/기전은 채우지 마십시오. '
            'text anchors excerpt는 해당 FILE PAGE에서 짧은 구절을 그대로 복사하고 image 근거는 첨부된 페이지에만 연결하십시오. '
            '이는 모델 검토이며 독립 실험이나 통계 재분석이 아닙니다. JSON만 반환합니다.\nSELECTED FINDINGS:\n'+json.dumps(scope,ensure_ascii=False)+
            '\nIMAGE ORDER:\n'+json.dumps(sorted(visual))+'\nFULL SOURCES:\n'+corpus)
    format_file=analysis/'critical-review/source-format.json'
    if format_file.exists() or not (analysis/'critical-review/request-record.json').exists():
        if not format_file.exists():atomic_json(format_file,{'version':2})
        prompt=prompt.replace('\nFULL SOURCES:\n'+corpus,BLOCK_GUIDE+'\nFULL SOURCES:\n'+indexed_corpus(pages))
    reviewer=CodexSubscription(backend.command[0],model='gpt-6-astra',effort='high',timeout=backend.timeout)
    reviewer.command=list(backend.command)
    from .analysis_pipeline import FigurePipeline
    pipe=FigurePipeline(worker,reviewer);pipe.source_pages=pages
    value=pipe.reviewed_call(job,consent,prompt,images,SCHEMA,analysis/'critical-review',validate,lambda v:repair_source_anchors(v,pages))
    worker.queue.checkpoint(job['id'],'critical_review',analysis/'critical-review/source-checked.json')
    return value
