"""Strict structural checks and source-link checks; not a scientific truth checker."""
from __future__ import annotations
from collections import Counter
from importlib.resources import files
from pathlib import Path, PurePosixPath
import json
from typing import Any
from jsonschema import Draft202012Validator

class ReportValidationError(ValueError):
    """The report cannot be rendered safely or its links are inconsistent."""

def safe_asset_path(path: str, report_id: str) -> PurePosixPath:
    p = PurePosixPath(path)
    if (not path.startswith(f'Resources/{report_id}/') or p.is_absolute()
        or any(v in path for v in ('\\', ':', '%', '\x00', '?', '#'))
        or '..' in p.parts or '.' in path.split('/') or '' in path.split('/')
        or p.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}):
        raise ReportValidationError(f'Unsafe local image path: {path!r}')
    return p

def resolved_asset(root: Path, path: str, report_id: str) -> Path:
    safe_asset_path(path, report_id)
    base = root.resolve(); candidate = (base/path).resolve()
    if not candidate.is_relative_to(base) or not candidate.is_file():
        raise ReportValidationError(f'Missing image or path escapes asset root: {path}')
    return candidate

def _refs(value: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(value,dict):
        for key,item in value.items():
            if key == 'refs': refs.extend(item)
            elif key == 'source_ref': refs.append(item)
            else: refs.extend(_refs(item))
    elif isinstance(value,list):
        for item in value: refs.extend(_refs(item))
    return refs

def _unique(items: list[str], label: str) -> None:
    duplicates=[key for key,n in Counter(items).items() if n>1]
    if duplicates: raise ReportValidationError(f'Duplicate {label}: {duplicates}')

def validate_report(data: dict[str,Any], asset_root: Path | None = None) -> None:
    schema=json.loads(files('figure_reports').joinpath('resources/report.schema.json').read_text(encoding='utf-8'))
    errors=sorted(Draft202012Validator(schema).iter_errors(data),key=lambda e:str(list(e.path)))
    if errors:
        err=errors[0]
        raise ReportValidationError(f'{"/".join(map(str,err.path)) or "report"}: {err.message}')
    figure_ids=[f['id'] for f in data['figures']]
    concept_ids=[c['id'] for c in data['concepts']]
    source_ids=[s['id'] for s in data['sources']]
    standalone_ids=[s['id'] for s in data['standalone']]
    _unique(figure_ids+concept_ids+source_ids+standalone_ids+['summary','design','integration','applications'],'IDs')
    known_sources=set(source_ids); used=set(_refs(data))
    if used-known_sources: raise ReportValidationError(f'Unknown source references: {sorted(used-known_sources)}')
    targets={'summary':data['summary'],'design':data['design'],'integration':data['integration'],'applications':data['applications']}
    targets.update({f['id']:f for f in data['figures']}); targets.update({s['id']:s for s in data['standalone']})
    targets.update({c['id']:c for c in data['concepts']})
    linked_concepts=set()
    for fig in data['figures']:
        _unique(fig['panels'],f'panels in {fig["id"]}')
        covered=[p for g in fig['panel_groups'] for p in g['panels']]
        if Counter(covered)!=Counter(fig['panels']):
            raise ReportValidationError(f'Every panel must be covered exactly once: {fig["id"]}')
        if set(fig['related_figures'])-set(figure_ids): raise ReportValidationError('Unknown related figure')
        for link in fig['concept_links']:
            if link['concept_id'] not in concept_ids: raise ReportValidationError('Unknown concept')
            linked_concepts.add(link['concept_id'])
        _unique([link['concept_id'] for link in fig['concept_links']],f'concept placements in {fig["id"]}')
        safe_asset_path(fig['image']['path'],data['report_id'])
        if asset_root is not None: resolved_asset(asset_root,fig['image']['path'],data['report_id'])
        if data['kind']=='paper' and fig['image']['origin']=='synthetic_demo':
            raise ReportValidationError('A real-paper report must not contain synthetic demo assets')
    for entry in data['standalone']:
        if entry.get('image'):
            image=entry['image'];safe_asset_path(image['path'],data['report_id'])
            if asset_root is not None:resolved_asset(asset_root,image['path'],data['report_id'])
            if data['kind']=='paper' and image['origin']=='synthetic_demo':
                raise ReportValidationError('A real-paper table must not contain synthetic demo assets')
    if set(concept_ids)-linked_concepts: raise ReportValidationError('Concept defined but not attached to a figure')
    for concept in data['concepts']:
        if concept.get('visual'):
            safe_asset_path(concept['visual']['path'],data['report_id'])
            if asset_root is not None:resolved_asset(asset_root,concept['visual']['path'],data['report_id'])
        if concept['origin'] in {'external','paper'} and not concept['refs']:
            raise ReportValidationError('Paper/external concepts need explicit source references')
        if data['kind']=='paper' and concept['origin']=='demo': raise ReportValidationError('Demo concept in real report')
    if data['kind']=='paper' and any(s['kind']=='demo' for s in data['sources']):
        raise ReportValidationError('Demo source in real report')
    for item in data['summary']['findings']+data['design']['flow']:
        if item['figure_id'] not in figure_ids: raise ReportValidationError('Unknown figure in outline')
    _unique([c['source_id'] for c in data['coverage']], 'coverage source')
    if {c['source_id'] for c in data['coverage']} != known_sources:
        raise ReportValidationError('Coverage inventory must include every source exactly once')
    for row in data['coverage']:
        if set(row['linked_to'])-set(targets): raise ReportValidationError('Unknown coverage target')
        if row['status'] in {'analyzed','context_only'}:
            if not row['linked_to'] or row['source_id'] not in used:
                raise ReportValidationError('Reviewed source needs a rendered reference and target')
            for target in row['linked_to']:
                if row['source_id'] not in _refs(targets[target]):
                    raise ReportValidationError(f'Coverage target {target} does not cite {row["source_id"]}')
        elif not row['reason'].strip():
            raise ReportValidationError('Missing/unreadable/unprocessed material needs a reason')
