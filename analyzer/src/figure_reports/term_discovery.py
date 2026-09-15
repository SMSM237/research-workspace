"""Paper-derived candidate discovery, never a fixed glossary lookup or identity resolver.

Regex candidates require contextual scientific review. Mixed-case/non-abbreviated
concepts and labels visible only in images must be added by the analysis pass.
"""
import hashlib,re
from typing import Iterable

def discover_terms(pages:Iterable[dict])->dict:
    candidates={}
    pattern=re.compile(r'(?<![A-Za-z0-9])(?:[A-Z][A-Z0-9]{1,19}(?:-[A-Z0-9]{1,10})?|p53)(?![A-Za-z0-9])')
    for p in pages:
        for match in pattern.finditer(p['text']):
            term=match.group();key=term.upper();entry=candidates.setdefault(key,{'id':'term-'+hashlib.sha256(key.encode()).hexdigest()[:12],'term':term,'status':'pending_context_review','occurrences':[]})
            entry['occurrences'].append({'document_id':p['document_id'],'page':p['page'],'offset':match.start(),'context':p['text'][max(0,match.start()-100):match.end()+140]})
    return {'version':1,'discovery':'source_text_candidates_not_confirmed_identities','requires_visual_and_semantic_review':True,'candidates':sorted(candidates.values(),key=lambda c:c['term'])}

def check_term_resolution(inventory:dict,resolutions:list[dict],generated_terms:set[str]|None=None)->dict:
    expected={c['id'] for c in inventory['candidates']};seen=set();unresolved=0
    for r in resolutions:
        if r.get('id') not in expected or r['id'] in seen or r.get('status') not in {'explained','unresolved','not_needed'} or not str(r.get('reason','')).strip():raise ValueError('Invalid term disposition')
        links=r.get('term_ids',[])
        if not isinstance(links,list) or any(not isinstance(t,str) or not t for t in links):raise ValueError('Invalid explanation IDs')
        if r['status']=='explained' and not links:raise ValueError('Explained candidate needs generated explanation IDs')
        if generated_terms is not None and r['status']!='not_needed':
            if not links or not set(links)<=generated_terms:raise ValueError('Explanation or unresolved notice is missing from the report')
        seen.add(r['id']);unresolved+=r['status']=='unresolved'
    if seen!=expected:raise ValueError('Unaccounted source-derived term candidates')
    return {'all_accounted':True,'candidates':len(expected),'unresolved':unresolved,'report_links_checked':generated_terms is not None,'scientific_identity_verified_by_checker':False}
