"""Managed local output with preflight protection and atomic per-file replacements.
This is not a cross-file transaction and must not be used as a sync publisher.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import re
from typing import Any
from .render import render_markdown
from .validate import validate_report, resolved_asset

class ModifiedOutputError(ValueError):
    """A managed file was changed locally; never overwrite it silently."""

def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()

def _under(root: Path, relative: str) -> Path:
    target=root/relative
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Output path escapes the selected directory: {relative}')
    return target

def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.tmp-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(content); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def build_report(data: dict[str,Any], asset_root: Path, output_dir: Path, *, artifacts=None) -> dict[str,str]:
    validate_report(data,asset_root)
    root=output_dir.resolve(); rid=data['report_id']
    title=data['paper'].get('library_title',rid)
    if not title or len(title)>160 or re.search(r'[\\/:*?"<>|#%\x00-\x1f]',title) or title.endswith(('.', ' ')) or title in {'.','..'}:
        raise ValueError('Unsafe library filename')
    markdown_path=f'Paper reports/{title}.md'; state_path=f'.figure-reports/{rid}/manifest.json'
    state=_under(root,state_path)
    old=json.loads(state.read_text(encoding='utf-8')) if state.exists() else {'files':{}}
    if not isinstance(old,dict) or not isinstance(old.get('files'),dict):
        raise ValueError('Invalid managed output manifest; refusing to overwrite')
    if old.get('markdown_path'):
        previous_path=old['markdown_path']
        if not isinstance(previous_path,str) or not re.fullmatch(r'(?:Papers|Paper reports)/[^/\\]+\.md',previous_path) or any(c in previous_path for c in ':?#%'):
            raise ValueError('Invalid managed Markdown path')
        markdown_path=previous_path.replace('Papers/','Paper reports/',1)
    payload={markdown_path:render_markdown(data).encode('utf-8'),
             f'.figure-reports/{rid}/analysis.json':json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8')}
    # Raw model output/provenance travel with the report under the same edit guard.
    for name,raw in (artifacts or {}).items():
        if name not in {'chat-analysis.md','chat-provenance.json','chat-history.json','chat-visuals.json'} or not isinstance(raw,bytes):
            raise ValueError('Unsupported report artifact')
        payload[f'.figure-reports/{rid}/{name}']=raw
    # A later theme-only rebuild preserves the canonical Chat source and receipt.
    for name in ['chat-analysis.md','chat-provenance.json','chat-history.json','chat-visuals.json']:
        rel=f'.figure-reports/{rid}/{name}'
        if rel not in payload and rel in old['files']:
            target=_under(root,rel)
            if not target.exists() or _digest(target.read_bytes())!=old['files'][rel]:
                raise ModifiedOutputError('Chat original was modified or removed: '+rel)
            payload[rel]=target.read_bytes()
    for fig in data['figures']:
        path=fig['image']['path']; payload[path]=resolved_asset(asset_root,path,rid).read_bytes()
    for entry in data['standalone']:
        if entry.get('image'):
            path=entry['image']['path'];payload[path]=resolved_asset(asset_root,path,rid).read_bytes()
    for concept in data['concepts']:
        if concept.get('visual'):
            path=concept['visual']['path'];payload[path]=resolved_asset(asset_root,path,rid).read_bytes()
    # All paths and existing content are inspected before any output is written.
    _under(root,'Resources/.nomedia')
    for rel,raw in payload.items():
        target=_under(root,rel)
        if target.exists():
            current=_digest(target.read_bytes()); previous=old['files'].get(rel)
            if current!=_digest(raw) and current!=previous:
                raise ModifiedOutputError(f'Local edits detected; output left unchanged: {rel}')
    nomedia=_under(root,'Resources/.nomedia')
    if not nomedia.exists(): atomic_write(nomedia,b'')
    # Images precede the Markdown; the manifest is the last completion record.
    order=sorted(payload,key=lambda rel:rel==markdown_path)
    for rel in order: atomic_write(_under(root,rel),payload[rel])
    manifest={'report_id':rid,'schema_version':data['schema_version'],'template_version':'0.4.0','markdown_path':markdown_path,
              'kind':data['kind'],'files':{rel:_digest(raw) for rel,raw in payload.items()},
              'publication':'local_only','scientific_validation':'not_performed' if data['kind']=='demo' else 'not_asserted_by_renderer'}
    atomic_write(state,json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
    return {'markdown':markdown_path,'manifest':state_path}
