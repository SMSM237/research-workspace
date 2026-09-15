"""Local render/validate and source-evidence intake. Does not launch an AI."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
from .build import atomic_write, build_report
from .render import render_html
from .validate import validate_report

def main(argv: list[str] | None=None) -> int:
    parser=argparse.ArgumentParser(description='Validate and render an existing figure-linked analysis JSON.')
    sub=parser.add_subparsers(dest='command',required=True)
    v=sub.add_parser('validate'); v.add_argument('analysis',type=Path); v.add_argument('--assets',type=Path)
    b=sub.add_parser('build'); b.add_argument('analysis',type=Path); b.add_argument('--assets',type=Path,required=True); b.add_argument('--out',type=Path,required=True); b.add_argument('--html',type=Path)
    ingest=sub.add_parser('ingest',help='Extract source evidence; no AI or scientific analysis.')
    ingest.add_argument('--main',type=Path,required=True)
    ingest.add_argument('--supplement',type=Path,action='append',default=[])
    ingest.add_argument('--out',type=Path,required=True)
    ingest.add_argument('--report-id',required=True)
    ingest.add_argument('--dpi',type=int,default=110)
    crop=sub.add_parser('crop',help='Create a provenance-tracked crop from explicit PDF coordinates.')
    crop.add_argument('--bundle',type=Path,required=True)
    crop.add_argument('--document',required=True)
    crop.add_argument('--page',type=int,required=True)
    crop.add_argument('--rect',type=float,nargs=4,required=True)
    crop.add_argument('--name',required=True)
    crop.add_argument('--label',required=True)
    terms=sub.add_parser('review-terms',help='Check paper-derived candidate dispositions and generated report links; no identity inference.')
    terms.add_argument('--candidates',type=Path,required=True)
    terms.add_argument('--resolutions',type=Path,required=True)
    terms.add_argument('--analysis',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='review-terms':
            from .term_discovery import check_term_resolution
            inventory=json.loads(args.candidates.read_text(encoding='utf-8'))
            resolutions=json.loads(args.resolutions.read_text(encoding='utf-8'))
            report=json.loads(args.analysis.read_text(encoding='utf-8'));validate_report(report)
            result=check_term_resolution(inventory,resolutions,{t['symbol'] for t in report.get('reading_aids',{}).get('terms',[])})
            print(json.dumps(result,ensure_ascii=False));return 0
        if args.command=='ingest':
            from .intake import ingest_bundle
            result=ingest_bundle(args.main,args.supplement,args.out,args.report_id,args.dpi)
            print(json.dumps({'status':result['status'],'report_id':result['report_id'],'documents':len(result['documents']),'analysis_status':result['analysis_status']},ensure_ascii=False));return 0
        if args.command=='crop':
            from .intake import crop_evidence
            result=crop_evidence(args.bundle,args.document,args.page,args.rect,args.name,args.label)
            print(json.dumps(result,ensure_ascii=False));return 0
        data=json.loads(args.analysis.read_text(encoding='utf-8'))
        if args.command=='validate':
            validate_report(data,args.assets); print('Contract and reference validation passed. Scientific validity is not asserted.'); return 0
        # Prepare preview before publishing anything, so a preview error cannot create a partial build.
        preview=render_html(data,args.assets) if args.html else None
        result=build_report(data,args.assets,args.out)
        if args.html: atomic_write(args.html,preview.encode('utf-8'))
        print(json.dumps({'status':'local_rendered','kind':data['kind'],**result},ensure_ascii=False)); return 0
    except (OSError,ValueError,KeyError) as exc:
        print(f'ERROR: {exc}',file=sys.stderr); return 2

if __name__=='__main__': raise SystemExit(main())
