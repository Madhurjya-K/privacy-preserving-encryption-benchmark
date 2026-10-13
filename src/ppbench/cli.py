import argparse,json
from pathlib import Path
from .model import CONFIGS,NYC_NUMERIC,NYC_VISIBLE,NSL_NUMERIC,NSL_VISIBLE
from .datasets import synthetic,load_dataset
from .benchmark import run

def main():
    parser=argparse.ArgumentParser(description='Experimental encryption benchmark; never silently substitutes Python for Spark')
    sub=parser.add_subparsers(dest='command',required=True)
    smoke=sub.add_parser('smoke'); smoke.add_argument('--output',default='results/smoke'); smoke.add_argument('--rows',type=int,default=12); smoke.add_argument('--bits',type=int,default=128); smoke.add_argument('--repeats',type=int,default=2); smoke.add_argument('--configs',nargs='+',choices=CONFIGS,default=list(CONFIGS))
    bench=sub.add_parser('benchmark'); bench.add_argument('--dataset',choices=['nyc','nslkdd'],required=True); bench.add_argument('--path',required=True); bench.add_argument('--size',type=int,choices=[10000,50000,100000,500000],required=True); bench.add_argument('--seed',type=int,default=2024); bench.add_argument('--output',required=True); bench.add_argument('--backend',choices=['spark','python-smoke'],default='spark'); bench.add_argument('--repeats',type=int,default=10); bench.add_argument('--warmups',type=int,default=1); bench.add_argument('--bits',type=int,default=2048); bench.add_argument('--configs',nargs='+',choices=CONFIGS,default=list(CONFIGS))
    bench.add_argument('--protocol');bench.add_argument('--expected-sha256');bench.add_argument('--source-label')
    smoke.add_argument('--resume',action='store_true'); bench.add_argument('--resume',action='store_true')
    report=sub.add_parser('report'); report.add_argument('run'); report.add_argument('--output',required=True); report.add_argument('--charts',action='store_true')
    security=sub.add_parser('security');security.add_argument('--output',default='results/security.json')
    args=parser.parse_args()
    if args.command=='report':
        from .report import summarize_run
        summarize_run(args.run,args.output,args.charts); return
    if args.command=='security':
        from .security import security_report
        Path(args.output).parent.mkdir(parents=True,exist_ok=True); security_report(args.output); return
    if args.command=='smoke':
        if args.rows<1 or args.rows>100: parser.error('smoke rows must be between 1 and 100')
        if args.repeats<1: parser.error('smoke needs at least one measured repeat')
        rows=synthetic(args.rows); numeric,visible=NYC_NUMERIC,NYC_VISIBLE
        result=run(rows,numeric,visible,'payment_type',args.configs,args.output,repeats=args.repeats,bits=args.bits,test_only=True,provenance={'kind':'synthetic','seed':2024,'publishable':False},resume=args.resume)
    else:
        if args.repeats<10 or args.warmups<1: parser.error('public-data protocol requires >=10 repeats and >=1 warmup')
        protocol_info=None
        if args.protocol:
            from .protocol import load_protocol,validate_selection
            protocol,protocol_info=load_protocol(args.protocol);validate_selection(protocol,args.dataset,args.size)
            actual={'backend':args.backend,'paillier_bits':args.bits,'repeats':args.repeats,'warmups':args.warmups,'seed':args.seed,'configurations':args.configs}
            for key,value in actual.items():
                if value!=protocol[key]:parser.error(f'{key} does not match frozen protocol')
            expected_release=protocol['nyc_release' if args.dataset=='nyc' else 'nsl_release']
            if Path(args.path).name!=expected_release:parser.error('input filename does not match frozen release')
        rows,provenance=load_dataset(args.dataset,args.path,args.size,args.seed)
        if args.expected_sha256 and provenance['sha256']!=args.expected_sha256:parser.error('input SHA-256 differs from supplied expected checksum')
        if args.source_label:provenance['source_description']=args.source_label
        numeric,visible=(NYC_NUMERIC,NYC_VISIBLE) if args.dataset=='nyc' else (NSL_NUMERIC,NSL_VISIBLE)
        result=run(rows,numeric,visible,visible[0],args.configs,args.output,backend=args.backend,repeats=args.repeats,warmups=args.warmups,bits=args.bits,provenance=provenance,resume=args.resume,protocol_info=protocol_info)
    print(json.dumps({'status':result['status'],'samples':len(result['samples']),'output':args.output}))

if __name__=='__main__': main()
