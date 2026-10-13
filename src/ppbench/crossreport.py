"""Cross-size numerical reporting. Publication gates are metadata checks, not certification."""
import csv,html,json,re
from pathlib import Path
from .report import summary
from .model import CONFIGS
STAGES=('protection','integrity_verification','query','final_decryption','serialization','hashing')

def expand_paths(paths):
    result=[]
    for item in paths:
        p=Path(item)
        found=sorted(p.rglob('run.json')) if p.is_dir() else [p]
        result.extend(found)
    result=list(dict.fromkeys(p.resolve() for p in result))
    if not result:raise ValueError('no run.json inputs found')
    return result

def sample_metrics(s):
    total=sum(s[k+'_sec'] for k in STAGES)
    values={k+'_sec':s[k+'_sec'] for k in STAGES}
    values.update(end_to_end_sec=total,throughput_records_per_sec=s['rows']/total,protected_bytes=s['protected_bytes'],size_expansion=s['protected_bytes']/s['plaintext_bytes'])
    for stage,m in s.get('process_metrics',{}).items():
        if m.get('available'):
            for key in ('peak_tree_rss_bytes','tree_cpu_seconds'):values[stage+'_'+key]=m[key]
    return values

def numerical_rows(paths):
    rows=[];reports=[];seen=set()
    for p in expand_paths(paths):
        r=json.loads(p.read_text(encoding='utf-8'));reports.append((p,r))
        dataset=(r.get('provenance') or {}).get('kind','unknown');size=r['parameters']['rows']
        for config in sorted({s['config'] for s in r['samples']}):
            identity=(dataset,size,config)
            if identity in seen:raise ValueError('duplicate dataset/size/configuration inputs; separate protocols or sessions explicitly')
            seen.add(identity);samples=[s for s in r['samples'] if s['config']==config];metrics=[sample_metrics(s) for s in samples]
            for key in sorted(set.intersection(*(set(m) for m in metrics))):
                rows.append({'dataset':dataset,'rows':size,'config':config,'metric':key,'backend':r['parameters']['backend'],'key_bits':r['parameters']['key_bits'],'evidence_status':r['status'],'source_run':str(p),**summary([m[key] for m in metrics])})
    return rows,reports

def cross_summary(paths,output,png=False):
    rows,reports=numerical_rows(paths);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    with (out/'cross-size-summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    (out/'cross-size-summary.json').write_text(json.dumps({'sources':[str(p) for p,_ in reports],'rows':rows},indent=2),encoding='utf-8')
    colors=['#215c98','#c56116','#23765a','#94337b'];statuses=sorted({r['status'] for _,r in reports})
    for metric in ('end_to_end_sec','throughput_records_per_sec'):
        selected=[r for r in rows if r['metric']==metric];xmin=min(r['rows'] for r in selected);xmax=max(r['rows'] for r in selected);ymax=max(r['median'] for r in selected) or 1
        x=lambda v:90+650*(v-xmin)/(xmax-xmin or 1);y=lambda v:340-240*v/ymax
        pieces=['<svg xmlns="http://www.w3.org/2000/svg" width="1050" height="450" viewBox="0 0 1050 450">','<rect width="1050" height="450" fill="white"/>',f'<text x="30" y="28" font-family="sans-serif" font-size="18">Measured {html.escape(metric)} by sample size</text>','<path d="M90 90V340H760" fill="none" stroke="black"/>','<text x="340" y="420" font-family="sans-serif">Number of records (linear scale)</text>']
        series=sorted({(r['dataset'],r['config']) for r in selected})
        for i,identity in enumerate(series):
            points=sorted((r['rows'],r['median']) for r in selected if (r['dataset'],r['config'])==identity);color=colors[i%len(colors)]
            pieces.append(f'<polyline points="'+ ' '.join(f'{x(n):.2f},{y(v):.2f}' for n,v in points)+f'" fill="none" stroke="{color}" stroke-width="2"/>')
            for n,v in points:pieces.append(f'<circle cx="{x(n):.2f}" cy="{y(v):.2f}" r="4" fill="{color}"><title>{n} records: {v:.6g}</title></circle>')
            pieces.append(f'<text x="780" y="{100+22*i}" font-family="sans-serif" font-size="12" fill="{color}">{html.escape(identity[0]+" / "+identity[1])}</text>')
        for n in sorted({r['rows'] for r in selected}):pieces.append(f'<text x="{x(n):.2f}" y="360" font-family="sans-serif" font-size="11">{n}</text>')
        for fraction in (0,.25,.5,.75,1):pieces.append(f'<text x="8" y="{y(fraction*ymax):.2f}" font-family="sans-serif" font-size="11">{fraction*ymax:.4g}</text>')
        pieces.append(f'<text x="30" y="55" font-family="sans-serif" font-size="10">{html.escape("; ".join(statuses))}</text>');pieces.append('</svg>')
        (out/(metric+'-cross-size.svg')).write_text('\n'.join(pieces),encoding='utf-8')
        if png:
            import matplotlib;matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig,ax=plt.subplots(figsize=(9,5))
            for dataset,config in series:
                data=sorted((r['rows'],r['median']) for r in selected if r['dataset']==dataset and r['config']==config)
                ax.plot([d[0] for d in data],[d[1] for d in data],marker='o',label=dataset+'/'+config)
            ax.set_xlabel('Records');ax.set_ylabel(metric);ax.set_title('Measured samples: inspect CSV evidence labels');ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/(metric+'-cross-size.png'));plt.close(fig)
    return rows

def publication_guard(report):
    p=report['parameters'];prov=report.get('provenance') or {}
    if report.get('state')!='complete' or p['backend']!='spark' or p['key_bits']<2048 or p.get('test_only',False):raise ValueError('publication requires complete actual Spark and >=2048-bit non-test execution')
    if prov.get('kind') not in ('nyc','nslkdd') or not re.fullmatch('[0-9a-f]{64}',prov.get('sha256','')):raise ValueError('public-dataset identity/checksum required')
    if prov.get('sample_rows')!=p['rows'] or prov.get('source_rows',0)<p['rows'] or prov.get('replacement') is not False:raise ValueError('sampling provenance invalid')
    if prov['kind']=='nslkdd' and p['rows']>125973:raise ValueError('NSL-KDD oversized sample rejected')
    if p.get('repeats',0)<10 or p.get('warmups',0)<1 or set(p['configs'])!=set(CONFIGS):raise ValueError('publication requires all four configurations and research repeat/warmup counts')
    if not p.get('protocol',{}).get('protocol_sha256'):raise ValueError('consumed frozen protocol identity is required')
    for config in CONFIGS:
        samples=[s for s in report['samples'] if s['config']==config]
        if len(samples)!=p['repeats'] or {s['repeat'] for s in samples}!=set(range(p['repeats'])):raise ValueError('missing/duplicate measured repeats')
        if any(s.get('backend')!='spark' or s['rows']!=p['rows'] for s in samples):raise ValueError('sample backend/size mismatch')
    return True

def latex_results(paths,output):
    # Validate EVERY input before writing any publication result file.
    expanded=expand_paths(paths)
    for p in expanded:publication_guard(json.loads(p.read_text(encoding='utf-8')))
    rows,reports=numerical_rows(expanded);lookup={(r['dataset'],r['rows'],r['config'],r['metric']):r['median'] for r in rows}
    lines=['% Generated only from complete public-data Spark >=2048-bit runs; metadata gate is not independent certification.','\\begin{table*}[t]','\\centering','\\caption{Measured public-data local-Spark medians. Latency sums the defined stages; throughput refers to the combined grouped/global workload. RSS is sampled process-tree resident memory, not PSS.}','\\label{tab:measured-results}','\\begin{tabular}{lrlrrr}','\\toprule','Dataset & Records & Configuration & Latency (s) & Records/s & Query RSS (MiB) \\\\','\\midrule']
    for dataset,n,config in sorted({(r['dataset'],r['rows'],r['config']) for r in rows}):
        latency=lookup[(dataset,n,config,'end_to_end_sec')];throughput=lookup[(dataset,n,config,'throughput_records_per_sec')];rss=lookup.get((dataset,n,config,'query_peak_tree_rss_bytes'));rss_text='n/m' if rss is None else f'{rss/(1<<20):.4g}'
        lines.append(f'{dataset} & {n} & {config} & {latency:.4g} & {throughput:.4g} & {rss_text} '+r'\\')
    lines+=['\\bottomrule','\\end{tabular}','\\end{table*}']
    for path,r in reports:lines.append('% Source SHA-256: '+r['provenance']['sha256'])
    out=Path(output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n',encoding='utf-8');return out
