from pathlib import Path
import sys,json,argparse
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'app'));sys.stdout.reconfigure(encoding='utf-8')
from figure_reports.worker_runtime import LocalWorker
from figure_reports.chat_coordinator import ChatCoordinator
from figure_reports.markdown_exchange import export_markdown_packet
p=argparse.ArgumentParser();p.add_argument('--job',required=True);a=p.parse_args()
config=json.loads((root/'config.json').read_text('utf-8'));c=ChatCoordinator(root/'state')
active=c.read().get('active')
if not active or active['job_id']!=a.job:raise ValueError('Claim this job before preparation')
w=LocalWorker(config['vault'],root/'state');j=w.queue.get(a.job)
if j['state']=='complete':raise ValueError('Published jobs must not be reanalysed')
w.prepare(j);j=w.queue.get(a.job);packet=Path(j['folder'])/'chat-packet'
if (packet/'request.json').exists():
    request=json.loads((packet/'request.json').read_text('utf-8'))
    if request['source_fingerprint']!=j['fingerprint']:raise ValueError('Packet belongs to another input')
else:request=export_markdown_packet(j,packet)
c.update(active['owner'],dict(phase='upload',packet_dir=str(packet)))
print(json.dumps(dict(job=a.job,packet_dir=str(packet),request=request),ensure_ascii=False))
