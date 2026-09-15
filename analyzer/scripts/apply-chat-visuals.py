from pathlib import Path
import sys,json,argparse
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'app'));sys.stdout.reconfigure(encoding='utf-8')
from figure_reports.build import atomic_write,build_report
from figure_reports.concept_visuals import apply_visuals
from figure_reports.worker_queue import JobQueue
p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--visual-dir',required=True);a=p.parse_args()
config=json.loads((root/'config.json').read_text('utf-8'));vault=Path(config['vault']);j=JobQueue(root/'state').get(a.job)
if not j or j['state']!='complete':raise ValueError('This command updates images in an existing published report')
folder=Path(a.visual_dir);data=json.loads((vault/'.figure-reports'/j['report_id']/'analysis.json').read_text('utf-8'))
result=apply_visuals(data,j['fingerprint'],folder,vault,require_complete=True)
artifact=json.dumps({name:json.loads((folder/name).read_text('utf-8')) for name in ['concept-images.json','reviewed-images.json']},ensure_ascii=False,indent=2).encode()
built=build_report(data,vault,vault,artifacts={'chat-visuals.json':artifact})
result['markdown']=built['markdown'];atomic_write(folder/'application-receipt.json',json.dumps(result,ensure_ascii=False,indent=2).encode())
print(json.dumps(result,ensure_ascii=False))
