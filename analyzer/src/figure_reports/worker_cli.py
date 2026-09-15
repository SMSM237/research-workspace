"""Local worker control with explicitly approved subscription inference."""
import argparse
import json
from pathlib import Path
import sys
from .worker_queue import JobQueue
from .worker_runtime import LocalWorker, atomic_json


def main():
    parser = argparse.ArgumentParser(description='Windows 논문 자료 준비 분석기')
    parser.add_argument('--vault', required=True, type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--codex', type=Path, help='공식 Codex 실행 파일 · ChatGPT 구독 로그인만 허용')
    parser.add_argument('--model',default='gpt-5.6-sol',choices=['gpt-5.6-sol','gpt-6-astra'])
    parser.add_argument('--auto-publish',action='store_true',help='사용자가 승인한 Inbox 자동 구독 분석·게시 정책')
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('run'); sub.add_parser('stop'); sub.add_parser('status')
    submit = sub.add_parser('enqueue')
    submit.add_argument('--main', required=True, type=Path)
    submit.add_argument('--supplement', action='append', default=[], type=Path)
    submit.add_argument('--report-id')
    retry = sub.add_parser('retry'); retry.add_argument('job_id')
    args = parser.parse_args()
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if args.action == 'run':
        LocalWorker(args.vault, args.state,model_executable=args.codex,analysis_model=args.model,auto_publish=args.auto_publish).run(); return
    if args.action == 'stop':
        atomic_json(args.vault / '.figure-reports/stop-request.json', {'action':'stop'})
        print('분석기 중지 요청을 보냈습니다.'); return
    queue = JobQueue(args.state)
    if args.action == 'enqueue':
        data = queue.enqueue(args.main, args.supplement, args.report_id)
    elif args.action == 'retry':
        data = queue.retry(args.job_id)
    else:
        data = queue.list()
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
