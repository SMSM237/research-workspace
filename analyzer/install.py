"""Install a private, watch-only workspace. Never starts AI or Git publication."""
from pathlib import Path
import argparse, getpass, json, shutil, subprocess, sys, venv

def install(vault, destination, expected_remote='', skip_dependencies=False):
    vault=Path(vault).resolve(); destination=Path(destination).resolve()
    if not vault.is_dir() or not (vault/'.obsidian').is_dir():
        raise ValueError('Choose the Vault root containing .obsidian')
    if destination.exists():
        raise FileExistsError('Choose a new installation folder; existing installations are preserved')
    if destination.is_relative_to(vault):
        raise ValueError('Analyzer settings must stay outside the synchronized Vault')
    if expected_remote and not (expected_remote.startswith('https://github.com/') or expected_remote.startswith('git@github.com:')):
        raise ValueError('Use your own GitHub repository URL without credentials')
    if expected_remote.startswith('https://') and '@' in expected_remote:
        raise ValueError('Credentials must not be included in a repository URL')
    source=Path(__file__).resolve().parent
    destination.mkdir(parents=True)
    shutil.copytree(source/'src',destination/'app',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    for name in ['chat-dispatch.py','prepare-chat-job.py','apply-chat-visuals.py','remote_control_state.py']:
        shutil.copy2(source/'scripts'/name,destination/name)
    shutil.copy2(source/'scripts/local_analyzer_launch.py',destination/'launch.py')
    shutil.copy2(source/'REMOTE_ANALYSIS_RUN.md',destination/'REMOTE_ANALYSIS_RUN.md')
    state=destination/'state';state.mkdir()
    config=dict(vault=str(vault),state=str(state),run_as_user=getpass.getuser(),auto_publish=False,expected_remote=expected_remote)
    (destination/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    # Receipt validation reads local config from the ledger directory, outside Git.
    (state/'config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
    (state/'analysis-hold.json').write_text(json.dumps({'message':'Chat 결과 대기 · Inbox 감지는 계속됩니다.'},ensure_ascii=False),encoding='utf-8')
    (destination/'mobile-control.json').write_text(json.dumps(dict(version=1,enabled=False,thread='',codex='',runbook=str(destination/'REMOTE_ANALYSIS_RUN.md'),workspace=str(destination)),indent=2),encoding='utf-8')
    if not skip_dependencies:
        venv.create(destination/'.venv',with_pip=True)
        python=destination/'.venv'/('Scripts/python.exe' if sys.platform=='win32' else 'bin/python')
        subprocess.run([str(python),'-m','pip','install','jsonschema>=4.23,<5','markdown-it-py>=3,<5','PyMuPDF>=1.26,<2'],check=True)
    (destination/'Start-Watcher.ps1').write_text('''$ErrorActionPreference='Stop'
$pythonw=Join-Path $PSScriptRoot '.venv/Scripts/pythonw.exe'
$script=Join-Path $PSScriptRoot 'launch.py'
if (!(Test-Path -LiteralPath $pythonw)) { throw 'Run the installer with dependencies first.' }
Start-Process -FilePath $pythonw -ArgumentList @(('"'+$script+'"'),'run') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
''',encoding='utf-8')
    return config

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vault',required=True)
    parser.add_argument('--install-dir',default=str(Path.home()/'Documents/Codex/Paper Analyzer'))
    parser.add_argument('--expected-remote',default='')
    parser.add_argument('--skip-dependencies',action='store_true',help='For isolated tests only; creates no usable Python environment')
    args=parser.parse_args()
    result=install(args.vault,args.install_dir,args.expected_remote,args.skip_dependencies)
    print('Installed. The watcher, AI analysis and Git publishing have NOT been started.')
