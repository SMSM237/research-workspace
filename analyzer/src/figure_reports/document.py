"""One document AST powers both exports; no scientific content is generated here."""
from __future__ import annotations
from typing import Any
import re,json
from .validate import validate_report
from .layout import figure_layout

ORIGIN_LABELS = {
 'paper':'원문에서 설명한 개념',
 'external':'외부 자료를 이용한 배경 설명 · 이 논문의 직접 결과 아님',
 'general_reasoning':'일반적인 정의·논리 설명 · 이 논문의 직접 결과 아님',
 'demo':'가상 예시 설명 · 연구 근거 아님',
}

def heading(level: int, text: str, id: str='') -> dict:
    return {'type':'heading','level':level,'text':text,'id':id}

def p(text: str, refs: list[str] | None=None, role: str='') -> dict:
    return {'type':'paragraph','text':text,'refs':refs or [],'role':role}

def blocks(items: list[dict]) -> list[dict]:
    entries=[p(x['text'],x['refs']) for x in items]
    return [{'type':'list','items':entries}] if len(entries)>1 else entries

def callout(kind: str, title: str, children: list[dict], id: str='') -> dict:
    return {'type':'callout','kind':kind,'title':title,'children':children,'id':id}

def link(text: str, target: str) -> dict:
    return {'type':'link','text':text,'target':target}

def build_document(data: dict[str,Any]) -> list[dict]:
    validate_report(data)
    paper=data['paper']; out=[heading(1,paper['title'],'report-title'),p(paper['subtitle'],role='subtitle')]
    out.append(p(f'{paper["venue"]} · {paper["year"] or "연도 미확인"}'+('' if paper.get('bibliography') else f' · {", ".join(paper["authors"])}'),role='metadata'))
    out.extend([heading(2,'01 · 논문 한눈에 보기','overview'),heading(3,'핵심 결론'),p(**data['summary']['takeaway']),
                heading(3,'연구 질문과 중요성'),p(**data['summary']['question'])])
    out.append({'type':'list','items':[link(finding['text'],finding['figure_id']) for finding in data['summary']['findings']]})
    out.append(callout('rr-critical','반드시 함께 읽어야 할 범위',blocks(data['summary']['critical_limitations'])))
    out.append(heading(2,'02 · 연구 설계와 논리 흐름','design'))
    out.append({'type':'list','items':[p(x['text'],x['refs']) for x in data['design']['blocks']]})
    for n,flow in enumerate(data['design']['flow'],1): out.append(link(f'{n:02d}  {flow["question"]}',flow['figure_id']))
    out.append(heading(2,'03 · Figure 중심 결과와 해석','figures'))
    concepts={c['id']:c for c in data['concepts']}; seen:set[str]=set()
    figures={f['id']:f for f in data['figures']}
    terms=data.get('reading_aids',{}).get('terms',[])
    def term_box(value:Any,title:str='용어와 기능 모듈 · 이 부분에서 읽기') -> dict | None:
        text=json.dumps(value,ensure_ascii=False); selected=[t for t in terms if any(re.search(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?![A-Za-z0-9])',text,re.I) for name in t.get('matches',[t['symbol']]))]
        if not selected:return None
        nodes=[p('기능 모듈은 이해를 돕기 위한 분류입니다. 한 단백질이 여러 역할을 할 수 있으며, 단백질량 변화만으로 모듈 활성·억제나 인과관계를 확정하지 않습니다.')]
        for module in dict.fromkeys(t['module'] for t in selected):
            nodes.append(heading(4,module))
            for t in selected:
                if t['module']!=module:continue
                nodes.append(p(f'{t["symbol"]} · {t["name"]} — {t["role"]}'+(f' {t["note"]}' if t.get('note') else '')))
                nodes.append(p(f'명칭·기능 출처: {t["source"]}',role='provenance'))
        return callout('rr-detail',title,nodes)

    def concept_box(item: dict) -> dict:
        c=concepts[item['concept_id']]; first=c['id'] not in seen; seen.add(c['id'])
        body=[p(c['definition'],c['refs']),p(item['context'],role='context')]
        if first:
            details=blocks([{'text':x,'refs':c['refs']} for x in c['details']])
            if c.get('visual'):details=[{'type':'concept-image',**c['visual']},p(c['visual']['caption'],role='provenance')]+details
            details.append(p(c['caution'],role='caution'))
            details.append(p(ORIGIN_LABELS[c['origin']],role='provenance'))
            body.append(callout('rr-detail','조금 더 이해하기',details))
        else:
            body.append(link('앞에서 설명한 개념의 상세 보기',f'concept-{c["id"]}'))
        return callout('rr-critical' if item['critical'] else 'rr-concept',
                       f'개념 · {c["term"]} / {c["english"]}',body,f'concept-{c["id"]}' if first else '')

    # A single source object can appear beside multiple main figures. Anchor IDs
    # are unique, while the canonical source/coverage link uses its first occurrence.
    rendered_supplements: set[str] = set()

    def figure_content(fig: dict, supplementary: bool = False) -> list[dict]:
        nodes = [p(fig['takeaway']['text'], fig['takeaway']['refs'], role='takeaway'),
                 p(fig['question']['text'], fig['question']['refs'], role='question')]
        glossary=term_box(fig)
        if glossary:nodes.append(glossary)
        for item in fig['concept_links']:
            if item['critical']:
                nodes.append(concept_box(item))
        body = [{'type':'image', **fig['image'], 'label':fig['label']}]
        for item in fig['concept_links']:
            if not item['critical'] and item['placement']=='before_results':
                body.append(concept_box(item))
        body.append(heading(4,'무엇이 관찰되었는가')); body.extend(blocks(fig['observations']))
        body.append(heading(4,'저자는 어떻게 설명하는가')); body.extend(blocks(fig['author_interpretation']))
        for item in fig['concept_links']:
            if not item['critical'] and item['placement']=='before_interpretation':
                body.append(concept_box(item))
        body.append(heading(4,'과학적으로 어떻게 해석되는가')); body.extend(blocks(fig['scientific_interpretation']))
        # The outer supplement is the only extra disclosure level. Do not require
        # a second click merely to reveal its figure and essential narrative.
        nodes.extend(body if supplementary else [callout('rr-body','그림과 주요 결과',body)])
        if not supplementary:
            nodes.append(callout('rr-critical','해석의 범위',blocks(fig['limitations'])))
        detail = []
        for group in fig['panel_groups']:
            detail.extend([heading(4,f'패널 {", ".join(group["panels"])}'),p(group['reading'],group['refs'])])
        detail.append(heading(4,'실험 조건과 정량 방법')); detail.extend(blocks(fig['methods']))
        nodes.append(callout('rr-detail','패널별 근거와 방법',detail))
        return nodes

    def inline_supplement(fig: dict, owner: str) -> list[dict]:
        canonical = fig['id'] not in rendered_supplements
        anchor = fig['id'] if canonical else f'{fig["id"]}-at-{owner}'
        rendered_supplements.add(fig['id'])
        # Scope/essential concepts cannot disappear behind a collapsed wrapper.
        visible = [p(f'{fig["label"]} · 해석 범위: {row["text"]}', row['refs'],
                     role='supplement-scope') for row in fig['limitations']]
        for item in fig['concept_links']:
            if item['critical']:
                visible.append(concept_box(item))
        # Avoid rendering critical concepts twice; keep the source data unchanged.
        inline = dict(fig)
        inline['concept_links'] = [item for item in fig['concept_links'] if not item['critical']]
        visible.append(callout('rr-supplement',f'{fig["label"]} — {fig["title"]}',
                               figure_content(inline, supplementary=True),anchor))
        return visible

    slots, unlinked = figure_layout(data['figures'])
    for slot in slots:
        fig = slot['main']
        out.append(heading(3,f'{fig["label"]} — {fig["title"]}',fig['id']))
        out.extend(figure_content(fig))
        if slot['supplements']:
            out.append(heading(4,'이 Figure와 함께 읽는 Supplementary'))
            for supplement in slot['supplements']:
                out.extend(inline_supplement(supplement,fig['id']))
        # Main-to-main references remain optional navigation, not the way to read S figures.
        for related in fig['related_figures']:
            if figures[related]['kind']=='main':
                out.append(link(f'다른 메인 결과 · {figures[related]["label"]}',related))
    if unlinked:
        out.append(heading(3,'독립 Supplementary — 번호순 펼쳐보기','independent-supplements'))
        for supplement in unlinked:
            out.extend(inline_supplement(supplement,'independent'))
    for entry in data['standalone']:
        if entry['id']=='chat-scope':continue
        if data.get('standalone_policy')=='tables_only' and not re.search(r'^(?:Table\b|표\s*\d)',entry['title'],re.I):continue
        out.append(heading(3,entry['title'] if data.get('standalone_policy')=='tables_only' else f'독립 근거 · {entry["title"]}',entry['id']))
        if entry.get('image'):
            out.append({'type':'image',**entry['image'],'label':entry['title']})
        out.extend(blocks(entry['blocks']))
    out.append(heading(2,'04 · 논문 전체의 통합 해석','integration')); out.extend(blocks(data['integration']))
    out.append(heading(2,'05 · 내 연구에 가져올 점','applications')); out.extend(blocks(data['applications']))
    out.append(heading(2,'06 · 상세 근거와 분석 범위','evidence'))
    for entry in data['standalone']:
        if entry['id']=='chat-scope':
            out.append(heading(3,entry['title'],entry['id']));out.extend(blocks(entry['blocks']))
    glossary=term_box({k:v for k,v in data.items() if k!='reading_aids'},'용어와 기능 모듈 · 리포트 전체 사전')
    if glossary:out.append(glossary)
    out.append(p('처리 범위의 기록과 과학적 해석의 정확성 검증은 서로 다릅니다. 아래 연결은 제공된 자료의 추적 가능성을 확인하기 위한 것입니다.'))
    source_map={s['id']:s for s in data['sources']}
    status_names={'analyzed':'분석 연결','context_only':'배경 연결','not_provided':'자료 미제공','unreadable':'판독 불가','not_analyzed':'미분석'}
    coverage=[]
    for row in data['coverage']:
        coverage.append(p(f'{source_map[row["source_id"]]["locator"]} — {status_names[row["status"]]}'+(f' · {row["reason"]}' if row['reason'] else '')))
        for target in row['linked_to']:
            anchor='overview' if target=='summary' else (f'concept-{target}' if target in concepts else target)
            coverage.append(link(f'분석 위치 · {target}',anchor))
    if data.get('standalone_policy')!='tables_only':out.append(callout('rr-detail','자료별 처리 범위와 연결 위치',coverage))
    source_nodes=[]
    for i,s in enumerate(data['sources'],1):
        source_nodes.append(heading(3,f'[{i}] {s["locator"]}',f'source-{s["id"]}'))
        if data.get('standalone_policy')!='tables_only':
            source_nodes.append(p(s['note'] or '추가 설명 없음'))
            if s.get('document_id'): source_nodes.append(p(f'문서 {s["document_id"]}'+(f' · 파일 페이지 {s["page"]}' if s.get('page') else '')))
    out.append(callout('rr-detail','원문·배경 설명의 출처',source_nodes))
    return out
