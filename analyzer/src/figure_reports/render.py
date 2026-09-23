"""Escaped text-only exports. HTML preview is offline and uses local asset bytes."""
from __future__ import annotations
import base64
from html import escape
from importlib.resources import files
import json
import mimetypes
from pathlib import Path
import posixpath
import re
from typing import Any
from .document import build_document
from .validate import validate_report, resolved_asset

def _md(text: str) -> str:
    return re.sub(r'([\\`*\[\]<>])',r'\\\1',text).replace('\n',' ')

def _rich_md(text: str) -> str:
    """Preserve prose formatting while refusing generated embeds/active links."""
    from markdown_it import MarkdownIt
    from urllib.parse import urlsplit
    # Chat's LaTeX delimiters map losslessly to Obsidian's MathJax syntax.
    text=re.sub(r'\\\[([\s\S]*?)\\\]',lambda m:'\n\n$$\n'+m[1]+'\n$$\n\n',text)
    text=re.sub(r'\\\(([^\n]*?)\\\)',lambda m:'$'+m[1]+'$',text)
    # CommonMark otherwise leaves **math/punctuation**조사 as literal stars.
    # A narrow layout space preserves the words and makes emphasis portable.
    text=re.sub(r'\*\*([^\n*]+)\*\*',lambda m:m[0]+(' ' if m.end()<len(text) and text[m.end()].isalpha() else ''),text)
    parser=MarkdownIt('commonmark',{'html':False}).enable('table')
    for token in parser.parse(text):
        for child in token.children or []:
            if child.type=='image':raise ValueError('Model prose cannot embed images; use verified local figure assets')
            if child.type=='link_open':
                href=child.attrGet('href') or ''
                if not href.startswith('#') and urlsplit(href).scheme.lower() not in {'http','https'}:
                    raise ValueError('Unsupported link in model prose')
    # Keep mathematical comparisons, but make raw HTML visibly inert in Obsidian.
    return re.sub(r'<(?:/?[A-Za-z][^>]*|!--[\s\S]*?--)>',lambda m:m[0].replace('<','&lt;').replace('>','&gt;'),text)

def render_markdown(data: dict[str,Any]) -> str:
    doc=build_document(data); indexes={s['id']:i for i,s in enumerate(data['sources'],1)}
    rich=data.get('text_format')=='markdown'
    def refs(items: list[str]) -> str:
        return ('  '+ ' '.join(f'[{indexes[r]}](#source-{r})' for r in items)) if items else ''
    def node(n: dict) -> str:
        t=n['type']
        if t=='heading':
            anchor=f'<a id="{n["id"]}"></a>\n\n' if n['id'] else ''
            return anchor+'#'*n['level']+' '+_md(n['text'])+'\n\n'
        if t=='paragraph':
            if rich:return _rich_md(n['text'])+('\n\n'+refs(n['refs']).strip() if n['refs'] else '')+'\n\n'
            return _md(n['text'])+refs(n['refs'])+'\n\n'
        if t=='list': return '\n'.join('- '+(node(item).strip().replace('\n','\n  ') if rich else node(item).strip()) for item in n['items'])+'\n\n'
        if t=='link': return f'[{_md(n["text"])}](#{n["target"]})\n\n'
        if t in {'image','concept-image'}: return f'![{_md(n["alt"])}]({posixpath.relpath(n["path"],"Paper reports")})\n\n'
        if t=='callout':
            fold='' if n['kind']=='rr-critical' else ('-' if n['kind'] in {'rr-detail','rr-supplement'} else '+')
            anchor=f'<a id="{n["id"]}"></a>\n\n' if n['id'] else ''
            content=f'[!{n["kind"]}]{fold} {_md(n["title"])}\n\n'+''.join(node(c) for c in n['children']).rstrip()
            return anchor+'\n'.join('> '+line if line else '>' for line in content.splitlines())+'\n\n'
        raise ValueError(f'Unsupported AST node: {t}')
    fm={'report_id':data['report_id'],'report_kind':data['kind'],'schema_version':data['schema_version'],
        'template_version':'0.4.0','cssclasses':['figure-first-report'],'generated':True}
    paper=data['paper']; b=paper.get('bibliography')
    if paper.get('library_title'): fm['library_title']=paper['library_title']
    if b:
        fm.update(journal=b['journal'],publication_year=paper['year'],authors=paper['authors'],doi=paper['doi'],
                  impact_factor=b['impact_factor'],impact_factor_year=b['impact_factor_year'],journal_quartiles=b['quartiles'],
                  author_affiliations=b['author_affiliations'],metric_source=b['metric_source'],metric_checked=b['metric_checked'])
    header='---\n'+'\n'.join(f'{k}: {json.dumps(v,ensure_ascii=False)}' for k,v in fm.items())+'\n---\n\n'
    return header+''.join(node(n) for n in doc)

def render_html(data: dict[str,Any], asset_root: Path) -> str:
    validate_report(data,asset_root); doc=build_document(data)
    indexes={s['id']:i for i,s in enumerate(data['sources'],1)}
    rich=data.get('text_format')=='markdown'
    if rich:
        from markdown_it import MarkdownIt
        prose_parser=MarkdownIt('commonmark',{'html':False}).enable('table')
    def refs(items: list[str]) -> str:
        return '<span class="refs">'+''.join(f'<a href="#source-{r}" aria-label="근거 {indexes[r]} 보기">[{indexes[r]}]</a>' for r in items)+'</span>' if items else ''
    def node(n: dict) -> str:
        t=n['type']; ident=f' id="{escape(n.get("id",""),quote=True)}"' if n.get('id') else ''
        if t=='heading': return f'<h{n["level"]}{ident}>{escape(n["text"])}</h{n["level"]}>'
        if t=='paragraph':
            if rich:return f'<div class="{escape(n["role"],quote=True)}">{prose_parser.render(_rich_md(n["text"]))}{refs(n["refs"])}</div>'
            return f'<p class="{escape(n["role"],quote=True)}">{escape(n["text"])}{refs(n["refs"])}</p>'
        if t=='list': return '<ul>'+''.join('<li>'+node(item)+'</li>' for item in n['items'])+'</ul>'
        if t=='link': return f'<p class="jump"><a href="#{n["target"]}">{escape(n["text"])}<span aria-hidden="true">↗</span></a></p>'
        if t in {'image','concept-image'}:
            image=resolved_asset(asset_root,n['path'],data['report_id'])
            mime=mimetypes.guess_type(image.name)[0] or 'image/png'
            src='data:'+mime+';base64,'+base64.b64encode(image.read_bytes()).decode('ascii')
            if t=='concept-image':return f'<figure class="concept-diagram"><img src="{src}" alt="{escape(n["alt"],quote=True)}" loading="lazy"></figure>'
            return f'<figure><button type="button" class="figure-zoom" aria-label="{escape(n["label"],quote=True)} 확대"><img src="{src}" alt="{escape(n["alt"],quote=True)}" loading="lazy"></button><figcaption>{escape(n["label"])} · 원본 확대 {refs([n["source_ref"]])}</figcaption></figure>'
        if t=='callout':
            children=''.join(node(c) for c in n['children'])
            if n['kind']=='rr-critical':
                return f'<aside{ident} class="callout critical" data-kind="rr-critical" data-critical="true"><div class="callout-label">{escape(n["title"])}</div>{children}</aside>'
            opened=' open' if n['kind'] in {'rr-body','rr-concept'} else ''
            return f'<details{ident} class="callout {n["kind"]}" data-kind="{n["kind"]}"{opened}><summary>{escape(n["title"])}</summary><div class="disclosure-body">{children}</div></details>'
        raise ValueError(f'Unsupported AST node: {t}')
    resource=files('figure_reports').joinpath('resources')
    css=resource.joinpath('preview.css').read_text(encoding='utf-8'); js=resource.joinpath('preview.js').read_text(encoding='utf-8')
    title=escape(data['paper']['title']); content=''.join(node(n) for n in doc)
    nav=[('overview','01','한눈에 보기'),('design','02','연구의 흐름'),('figures','03','Figure 읽기'),('integration','04','통합 해석'),('applications','05','연구 적용'),('evidence','06','근거와 범위')]
    links=''.join(f'<a href="#{id}"><span>{num}</span>{label}</a>' for id,num,label in nav)
    figure_links=''.join(f'<a href="#{f["id"]}">{escape(f["label"])}</a>' for f in data['figures'])
    badge='가상 데이터 · 실제 논문 분석 아님' if data['kind']=='demo' else '로컬 리포트 · 원문 근거 연결'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{title} — Figure Notes</title><style>{css}</style></head>
<body><a class="skip-link" href="#report-title">본문으로 이동</a><aside class="rail"><div class="brand">FIGURE<span>NOTES</span></div><div class="rail-caption">논문의 흐름을 따라 읽기</div><nav aria-label="리포트 목차">{links}</nav><div class="rail-rule"></div><div class="rail-caption">FIGURE INDEX</div><nav class="fig-nav" aria-label="Figure 바로가기">{figure_links}</nav><div class="rail-foot">LOCAL-FIRST READER<br>Report template 0.2</div></aside>
<div class="page"><header class="toolbar"><span class="crumb">리포트 / 읽기 형식 예시</span><div class="controls"><div class="mode-group" aria-label="읽기 깊이"><button type="button" data-mode="summary" aria-pressed="false">요약</button><button type="button" data-mode="standard" aria-pressed="true">표준</button><button type="button" data-mode="detail" aria-pressed="false">상세</button></div><button type="button" id="concept-toggle" aria-pressed="true">개념 설명 펼침</button></div></header>
<main class="figure-first-report" id="content" data-mode="standard"><div class="eyebrow">FIGURE-FIRST RESEARCH REPORT</div><div class="demo-badge">{badge}</div>{content}<footer>이 파일은 Markdown과 동일한 분석 데이터로 만든 오프라인 미리보기입니다. 실제 Obsidian 실행 화면과는 구분됩니다.</footer></main></div>
<dialog id="image-dialog" aria-label="Figure 확대 보기"><button type="button" id="close-dialog" aria-label="확대 보기 닫기">닫기 ×</button><img alt=""><p></p></dialog><div id="mode-status" class="sr-only" aria-live="polite"></div><script>{js}</script></body></html>'''
