from pathlib import Path
import json,sys,traceback
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'app'))
config=json.loads((root/'config.json').read_text(encoding='utf-8'))
args=sys.argv[1:] or ['run']
sys.argv=['paper-analyzer','--vault',config['vault'],'--state',config['state'],*(['--codex',config['model_executable']] if config.get('model_executable') else []),'--model',config.get('analysis_model','gpt-5.6-sol'),*(['--auto-publish'] if config.get('auto_publish') else []),*args]
from figure_reports.worker_cli import main
try:
    if args[0]=='run':
        from figure_reports.model_adapter import require_runner_user
        require_runner_user(config.get('run_as_user'))
    main()
except Exception:
    with (root/'worker-errors.log').open('a',encoding='utf-8') as log:
        traceback.print_exc(file=log)
    raise
