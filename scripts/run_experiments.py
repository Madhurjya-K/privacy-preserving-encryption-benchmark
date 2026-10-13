"""Run selected cells of the frozen matrix; never download or fabricate datasets."""
import argparse,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from ppbench.protocol import load_protocol
from ppbench.benchmark import atomic_json
from ppbench.report import summarize_run

def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',default=str(ROOT/'configs/protocol.json'));p.add_argument('--data-dir',default=str(ROOT/'data/external'));p.add_argument('--output',default=str(ROOT/'results/public-matrix'));p.add_argument('--datasets',nargs='+',choices=['nyc','nslkdd'],default=['nyc','nslkdd']);p.add_argument('--sizes',nargs='+',type=int);p.add_argument('--resume',action='store_true');p.add_argument('--plan-only',action='store_true');p.add_argument('--keep-going',action='store_true');a=p.parse_args()
    protocol,identity=load_protocol(a.protocol);sizes=a.sizes or protocol['sizes']
    if len(set(sizes))!=len(sizes) or any(x not in protocol['sizes'] for x in sizes):p.error('sizes must be unique frozen-protocol sizes')
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True);statefile=out/'matrix-status.json'
    state={'schema_version':1,'protocol':identity,'selected_datasets':a.datasets,'selected_sizes':sizes,'cells':{},'updated_utc':None}
    if a.resume and statefile.exists():
        previous=json.loads(statefile.read_text())
        if any(previous[k]!=state[k] for k in ('protocol','selected_datasets','selected_sizes')):raise ValueError('matrix selection/protocol mismatch')
        state=previous
    elif statefile.exists():raise ValueError('matrix state exists; use --resume or a fresh output')
    def save():state['updated_utc']=datetime.now(timezone.utc).isoformat();atomic_json(statefile,state)
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'src')+os.pathsep+env.get('PYTHONPATH','');env.setdefault('PYSPARK_PYTHON',sys.executable)
    failures=0
    for dataset in a.datasets:
        release=protocol['nyc_release' if dataset=='nyc' else 'nsl_release'];source=Path(a.data_dir).resolve()/release
        for size in sizes:
            cell=f'{dataset}-{size}';folder=out/cell;folder.mkdir(exist_ok=True)
            if dataset=='nslkdd' and size==500000:
                state['cells'][cell]={'state':'unavailable','reason':'125973 original training rows; no replacement or replication permitted'};save();continue
            if not source.exists():
                state['cells'][cell]={'state':'blocked','reason':'source file absent; no automatic download','source':str(source)};save();failures+=1;continue
            cmd=[sys.executable,'-m','ppbench.cli','benchmark','--dataset',dataset,'--path',str(source),'--size',str(size),'--output',str(folder),'--protocol',str(Path(a.protocol).resolve())]
            if a.resume and (folder/'checkpoint.json').exists():cmd.append('--resume')
            if dataset=='nslkdd':cmd+=['--expected-sha256','1b86d2f957b33082081bba410fe129b475efebcc13c9014c3f447c8271aadf95','--source-label','jmnwong mirror, checksum supplied by parent; exact download URL recorded externally']
            state['cells'][cell]={'state':'planned' if a.plan_only else 'running','command':cmd,'log':str(folder/'execution.log')};save();print(json.dumps({'cell':cell,'state':state['cells'][cell]['state']}),flush=True)
            if a.plan_only:continue
            with (folder/'execution.log').open('a',encoding='utf-8') as log:
                result=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            if result.returncode:
                state['cells'][cell]['state']='failed';state['cells'][cell]['returncode']=result.returncode;save();failures+=1
                if not a.keep_going:return 1
                continue
            state['cells'][cell]['state']='reporting';save()
            summarize_run(folder/'run.json',folder/'summary')
            state['cells'][cell]['state']='complete';save()
    save();return 1 if failures and not a.plan_only else 0
if __name__=='__main__':raise SystemExit(main())
