"""Build a clean distributable from an explicit source root; never packages a user's Vault."""
from pathlib import Path
import argparse,hashlib,json,re,zipfile
EXCLUDE={'.git','node_modules','__pycache__','.pytest_cache','.gradle','build','.venv','.idea'}
def files(root):
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if not p.is_file() or any(x in EXCLUDE for x in rel.parts):continue
        if p.name in {'local.properties','.DS_Store'} or p.name.endswith('.test-build.cjs') or p.suffix in {'.pyc','.jks','.keystore'}:continue
        yield p
def package(root,out):
    root=Path(root).resolve();out=Path(out).resolve()
    if out.is_relative_to(root):raise ValueError('Write archives outside the source tree')
    out.mkdir(parents=True,exist_ok=True);items=list(files(root));records=[]
    forbidden=[r'(?:ghp_|github_pat_)[A-Za-z0-9_]{15,}',r'-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY',r'[\w.+-]+@(?:gmail|naver|outlook)\.com']
    for p in items:
        data=p.read_bytes();rel=p.relative_to(root).as_posix()
        if p.suffix not in {'.png','.webp','.apk','.jar'}:
            text=data.decode('utf-8',errors='replace')
            # Patterns in this scanner are data, not credentials.
            if rel!='tools/package_release.py' and any(re.search(pattern,text) for pattern in forbidden):raise ValueError('Review private data in '+rel)
        if p.stat().st_size>=90_000_000:raise ValueError('Unexpected large file: '+rel)
        records.append(dict(path=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
    for name in ['main.js','styles.css','manifest.json']:
        assert (root/'dashboard/plugin'/name).read_bytes()==(root/'starter-vault/.obsidian/plugins/figure-first-reader'/name).read_bytes()
    assert not list((root/'starter-vault/Papers').glob('*.md'))
    assert (root/'starter-vault/Tasks/할 일.md').read_text('utf-8')=='# 할 일\n\n'
    for link in re.findall(r'!\[\[([^\]]+)\]\]',(root/'starter-vault/Dashboard/모바일 홈.md').read_text('utf-8')):
        assert (root/'starter-vault'/(link+'.md')).is_file(),link
    archive=out/'Research-Workspace-2026.09.16.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in items:z.write(p,Path('research-workspace')/p.relative_to(root))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(records)
        for r in records:assert hashlib.sha256(z.read('research-workspace/'+r['path'])).hexdigest()==r['sha256']
    result=dict(archive=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),files=records)
    (out/'SHA256.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(archive=archive.name,bytes=archive.stat().st_size,sha256=result['sha256'],files=len(records))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--out',required=True);a=p.parse_args();package(a.root,a.out)
