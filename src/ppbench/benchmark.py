import gc,hashlib,json,os,platform,secrets,statistics,sys,time,tracemalloc
from datetime import datetime,timezone
from importlib import metadata
from pathlib import Path
from .crypto import keygen
from .integrity import canonical
from .model import Keys
from .pipeline import protect,verify,query,finalize
from .reference import reference
from .resources import ProcessTreeMonitor,DEFINITION

def measured(fn,interval=.05):
    gc.collect(); monitor=ProcessTreeMonitor(interval).start(); tracemalloc.start(); t=time.perf_counter_ns()
    try:
        result=fn(); elapsed=(time.perf_counter_ns()-t)/1e9
        peak=tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop(); resources=monitor.stop()
    return result,elapsed,peak,resources

def environment():
    packages={}
    for p in ('cryptography','pandas','pyarrow','pyspark','matplotlib','psutil'):
        try: packages[p]=metadata.version(p)
        except metadata.PackageNotFoundError: packages[p]=None
    return {'python':sys.version,'platform':platform.platform(),'machine':platform.machine(),'processor':platform.processor(),'cpu_count':os.cpu_count(),'packages':packages,'memory_metric':'tracemalloc Python peak bytes; excludes native allocations and Spark workers/JVM','clock':'perf_counter_ns','process_tree_metric_definition':DEFINITION,'spark_master':os.environ.get('PPBENCH_SPARK_MASTER','local[*]'),'spark_driver_memory':os.environ.get('PPBENCH_SPARK_DRIVER_MEMORY','4g')}

def atomic_json(path,obj):
    path=Path(path); temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8') as f:
        json.dump(obj,f,indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)

def run(rows,numeric,visible,group,configs,output,backend='python-smoke',repeats=10,warmups=1,bits=2048,test_only=False,provenance=None,partition_size=1000,resume=False,resource_interval=.05,protocol_info=None):
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    if repeats<1 or warmups<0 or not configs or len(set(configs))!=len(configs): raise ValueError('positive repeats and unique nonempty configurations required')
    parameters={'rows':len(rows),'configs':list(configs),'repeats':repeats,'warmups':warmups,'key_bits':bits,'backend':backend,'partition_size':partition_size,'scale':100,'group':group,'numeric':list(numeric),'visible':list(visible),'test_only':test_only,'resource_interval_sec':resource_interval,'protocol':protocol_info,'workloads':['grouped SUM/COUNT(*)/AVG','global SUM/COUNT(*)/AVG']}
    checkpoint_path=output/'checkpoint.json'; prior=None
    if resume:
        if not checkpoint_path.exists(): raise ValueError('resume requested but checkpoint.json is absent')
        prior=json.loads(checkpoint_path.read_text(encoding='utf-8'))
        if prior['parameters']!=parameters or prior['provenance']!=provenance: raise ValueError('checkpoint parameters or dataset provenance mismatch')
        if prior.get('state')=='complete':
            atomic_json(output/'run.json',prior)
            return prior
    elif checkpoint_path.exists():
        raise ValueError('checkpoint already exists: use --resume or a new output directory; refusing to overwrite samples')
    private,keygen_sec,keygen_peak,keygen_resources=measured(lambda:keygen(bits,test_only=test_only),resource_interval)
    keys=Keys(private,secrets.token_bytes(32),secrets.token_bytes(32),secrets.token_bytes(32))
    spark=None
    if backend=='spark':
        from pyspark.sql import SparkSession
        spark=SparkSession.builder.master(os.environ.get('PPBENCH_SPARK_MASTER','local[*]')).appName('privacy-preserving-encryption-benchmark').config('spark.driver.memory',os.environ.get('PPBENCH_SPARK_DRIVER_MEMORY','4g')).getOrCreate()
    samples=list(prior['samples']) if prior else []
    baseline={'grouped':reference(rows,numeric,group),'global':reference(rows,numeric,None)}
    if prior and prior['query_result']!=baseline: raise ValueError('checkpoint plaintext oracle mismatch')
    audits=dict(prior.get('bounded_exposure_audit',{})) if prior else {}
    sessions=list(prior.get('execution_sessions',[])) if prior else []
    sessions.append({'session_index':len(sessions),'started_utc':datetime.now(timezone.utc).isoformat(),'environment':environment(),'key_generation':{'seconds':keygen_sec,'peak_python_bytes':keygen_peak,'process_tree':keygen_resources,'excluded_from_stage_timings':True}})
    completed={(s['config'],s['repeat']) for s in samples}
    status='synthetic/Python smoke only; NOT Spark or publishable public-data evidence' if test_only or backend!='spark' or (provenance or {}).get('kind')=='synthetic' else 'public-data Spark experimental samples; requires review'
    def snapshot(state,active_sample=None):
        return {'schema_version':3,'created_utc':prior['created_utc'] if prior else sessions[0]['started_utc'],'updated_utc':datetime.now(timezone.utc).isoformat(),'state':state,'status':status,'parameters':parameters,'key_generation':sessions[0]['key_generation'],'execution_sessions':sessions,'provenance':provenance,'environment':sessions[0]['environment'],'query_result':baseline,'bounded_exposure_audit':audits,'samples':samples,'active_sample':active_sample,'resume_policy':'Completed samples retained verbatim; fresh independent keys per resumed execution session; rerun warmup for unfinished configurations; interrupted sample rerun from protection.'}
    atomic_json(checkpoint_path,snapshot('in_progress'))
    try:
        for config in configs:
            if all((config,r) in completed for r in range(repeats)): continue
            for repeat in range(-warmups,repeats):
                if repeat>=0 and (config,repeat) in completed: continue
                atomic_json(checkpoint_path,snapshot('in_progress',{'config':config,'repeat':repeat,'phase':'sample_started'}))
                print(json.dumps({'event':'sample_started','config':config,'repeat':repeat,'rows':len(rows),'backend':backend}),flush=True)
                bundle,pt,pm,pr=measured(lambda:protect(rows,config,keys,numeric,visible,partition_size=partition_size),resource_interval)
                _,it,im,ir=measured(lambda:verify(bundle,keys),resource_interval)
                if repeat==0:
                    from .security import exposure_audit
                    audits[config]=exposure_audit(bundle,[r['research_canary'] for r in rows if 'research_canary' in r])
                raw,qt,qm,qr=measured(lambda:{'grouped':query(bundle,keys,group,backend,spark),'global':query(bundle,keys,None,backend,spark)},resource_interval)
                answer,dt,dm,dr=measured(lambda:{k:finalize(v,bundle,keys) for k,v in raw.items()},resource_interval)
                serialized,st,sm,sr=measured(lambda:canonical(bundle),resource_interval)
                digest,ht,hm,hr=measured(lambda:hashlib.sha256(serialized).hexdigest(),resource_interval)
                # Control times have no encryption and are not subtracted from main timings.
                plainbytes,ct,cm,cr=measured(lambda:canonical(rows),resource_interval)
                _,cht,chm,chr=measured(lambda:hashlib.sha256(plainbytes).hexdigest(),resource_interval)
                if answer!=baseline: raise AssertionError('configuration disagrees with independent Decimal plaintext oracle')
                if repeat>=0:
                    samples.append({'config':config,'repeat':repeat,'execution_session_index':sessions[-1]['session_index'],'rows':len(rows),'backend':backend,'protection_sec':pt,'integrity_verification_sec':it,'query_sec':qt,'final_decryption_sec':dt,'serialization_sec':st,'hashing_sec':ht,'plain_serialization_control_sec':ct,'plain_hash_control_sec':cht,'protected_bytes':len(serialized),'plaintext_bytes':len(plainbytes),'protection_peak_python_bytes':pm,'query_peak_python_bytes':qm,'final_decryption_peak_python_bytes':dm,'integrity_peak_python_bytes':im,'serialization_peak_python_bytes':sm,'hashing_peak_python_bytes':hm,'control_peak_python_bytes':cm,'hash_control_peak_python_bytes':chm,'protected_sha256':digest,'process_metrics':{'protection':pr,'integrity_verification':ir,'query':qr,'final_decryption':dr,'serialization':sr,'hashing':hr,'plain_serialization_control':cr,'plain_hash_control':chr}})
                    completed.add((config,repeat))
                    atomic_json(checkpoint_path,snapshot('in_progress'))
                    print(json.dumps({'event':'sample_completed','config':config,'repeat':repeat,'completed':len(samples),'target':len(configs)*repeats}),flush=True)
                del bundle,raw,answer,serialized,plainbytes
    finally:
        if spark is not None: spark.stop()
    report=snapshot('complete')
    atomic_json(checkpoint_path,report)
    atomic_json(output/'run.json',report)
    return report
