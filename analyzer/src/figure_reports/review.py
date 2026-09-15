"""Validate source-review records separately from report formatting.

This verifies inventory and file integrity, not the truth of a model's review.
"""
from hashlib import sha256
from pathlib import Path


def _local(root: Path, name: str) -> Path:
    path=(root/name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Missing file or review path escapes root')
    return path


def validate_review(report: dict, ledger: dict, originals: Path, assets: Path) -> None:
    if ledger.get('version') != '1' or ledger.get('report_id') != report['report_id']:
        raise ValueError('Review/report identity mismatch')
    inventory=ledger['inventory']
    ids=[row['figure_id'] for row in inventory]
    figures={f['id']:f for f in report['figures']}
    if len(figures)!=len(report['figures']):
        raise ValueError('Duplicate report figures')
    sources={s['id']:s for s in report['sources']}
    if len(sources)!=len(report['sources']):
        raise ValueError('Duplicate report sources')
    if len(ids)!=len(set(ids)) or set(ids)!=set(figures):
        raise ValueError('Source-derived figure inventory differs from report')
    docs={d['document_id']:d for d in ledger['documents']}
    if len(docs)!=len(ledger['documents']):
        raise ValueError('Duplicate source documents')
    for doc in docs.values():
        original=_local(originals,doc['filename'])
        if sha256(original.read_bytes()).hexdigest()!=doc['sha256']:
            raise ValueError('Original source changed after review')
        import fitz
        with fitz.open(original) as pdf:
            if type(doc['pages']) is not int or doc['pages']!=len(pdf):
                raise ValueError('Declared source page count differs from actual PDF')
    for row in inventory:
        figure=figures[row['figure_id']]
        if row.get('visual_review') != 'model_self_review':
            raise ValueError('Figure visual review is incomplete')
        if len(row['panels'])!=len(set(row['panels'])) or set(row['panels'])!=set(figure['panels']):
            raise ValueError('Source-derived panel inventory differs from report')
        if type(row['page']) is not int or row['document_id'] not in docs or not 1<=row['page']<=docs[row['document_id']]['pages']:
            raise ValueError('Invalid source page')
        source=sources.get(figure['image']['source_ref'])
        if not source or source.get('document_id')!=row['document_id'] or source.get('page')!=row['page']:
            raise ValueError('Report source does not match reviewed document/page')
        if row['image_path']!=figure['image']['path']:
            raise ValueError('Reviewed image differs from report')
        if sha256(_local(assets,row['image_path']).read_bytes()).hexdigest()!=row['image_sha256']:
            raise ValueError('Image changed after visual review')
    for issue in ledger.get('unresolved',[]):
        if not issue.get('reason') or not issue.get('figure_ids'):
            raise ValueError('Unresolved issue lacks scope or explanation')
        for fid in issue['figure_ids']:
            if fid not in figures or not figures[fid]['limitations']:
                raise ValueError('Unresolved issue has no visible limitation')
