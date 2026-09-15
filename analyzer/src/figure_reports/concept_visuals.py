"""Import reviewed Chat-generated educational images without changing pixels."""
from pathlib import Path
import json,hashlib
from PIL import Image
from .build import atomic_write

def apply_visuals(data,fingerprint,directory,destination,*,require_complete=True):
    directory=Path(directory).resolve();destination=Path(destination)
    manifest=json.loads((directory/'concept-images.json').read_text('utf-8'))
    reviews=json.loads((directory/'reviewed-images.json').read_text('utf-8'))
    if manifest.get('format')!='concept-images/1' or manifest.get('source_fingerprint')!=fingerprint:raise ValueError('Concept images belong to another paper')
    concepts={c['id']:c for c in data['concepts']};seen=set();prepared=[]
    for item in manifest['images']:
        name=item['file'];path=(directory/name).resolve()
        if Path(name).name!=name or not path.is_relative_to(directory) or path.suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:raise ValueError('Unsafe concept image path')
        if item['status']!='generated' or not item['alt'].strip() or not item['caption'].strip():raise ValueError('Incomplete concept image record')
        if not 0<path.stat().st_size<=25*1024*1024:raise ValueError('Concept image size invalid')
        raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if reviews.get(name,{}).get('sha256')!=sha or reviews[name].get('visual_scientific_review')!='pass':raise ValueError('Concept image has not passed visual/source review')
        with Image.open(path) as image:
            if min(image.size)<256 or max(image.size)>12000:raise ValueError('Concept image resolution invalid')
            image.verify()
        if not item['concept_ids'] or len(set(item['concept_ids']))!=len(item['concept_ids']):raise ValueError('Invalid concept image mapping')
        for cid in item['concept_ids']:
            if cid not in concepts or cid in seen:raise ValueError('Missing or duplicate concept ID')
            seen.add(cid)
        # Existing reader registers concept zoom tools from this dedicated folder.
        rel=f'Resources/{data["report_id"]}/Concepts/concept-art-{sha[:16]}{path.suffix.lower()}'
        prepared.append((item,rel,raw))
    pending=set(concepts)-seen
    if set(manifest['pending'])!=pending:raise ValueError('Pending concept image list is inaccurate')
    if require_complete and pending:raise ValueError('Concept images still pending: '+', '.join(sorted(pending)))
    for item,rel,raw in prepared:
        target=destination/rel
        if target.exists() and target.read_bytes()!=raw:raise ValueError('Generated image was modified')
        atomic_write(target,raw)
        for cid in item['concept_ids']:
            concepts[cid]['visual']=dict(path=rel,alt=item['alt'],caption=item['caption']+' · Chat 생성 개념 그림이며 논문 원본 실험 결과가 아닙니다.')
    return dict(generated_concepts=sorted(seen),pending_concepts=sorted(pending),complete=not pending)
