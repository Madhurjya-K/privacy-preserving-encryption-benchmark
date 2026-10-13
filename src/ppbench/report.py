import csv,json,random,statistics,html
from pathlib import Path

def quantile(values,p):
    values=sorted(values); pos=(len(values)-1)*p; lo=int(pos); hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(pos-lo)

def summary(values,seed=2024,bootstrap=2000):
    rng=random.Random(seed); n=len(values)
    medians=[statistics.median(rng.choices(values,k=n)) for _ in range(bootstrap)]
    return {'n':n,'median':statistics.median(values),'q1':quantile(values,.25),'q3':quantile(values,.75),
            'iqr':quantile(values,.75)-quantile(values,.25),'median_bootstrap_ci95_low':quantile(medians,.025),'median_bootstrap_ci95_high':quantile(medians,.975)}

def summarize_run(run_path,output,charts=False):
    run=json.loads(Path(run_path).read_text(encoding='utf-8')); rows=[]; samples=run['samples']
    stages=('protection_sec','integrity_verification_sec','query_sec','final_decryption_sec','serialization_sec','hashing_sec','protected_bytes','protection_peak_python_bytes','query_peak_python_bytes')
    for sample in samples:
        sample['end_to_end_sec']=sum(sample[k] for k in ('protection_sec','integrity_verification_sec','query_sec','final_decryption_sec','serialization_sec','hashing_sec'))
        sample['throughput_records_per_sec']=sample['rows']/sample['end_to_end_sec']
        sample['size_expansion']=sample['protected_bytes']/sample['plaintext_bytes']
    process_stages=('protection','integrity_verification','query','final_decryption','serialization','hashing')
    process_metrics=[]
    for stage in process_stages:
        for key in ('peak_tree_rss_bytes','tree_cpu_seconds'):
            if all(s.get('process_metrics',{}).get(stage,{}).get('available') for s in samples):
                name=stage+'_'+key;process_metrics.append(name)
                for s in samples:s[name]=s['process_metrics'][stage][key]
    for config in sorted({s['config'] for s in samples}):
        data=[s for s in samples if s['config']==config]
        for metric in stages+tuple(process_metrics)+('end_to_end_sec','throughput_records_per_sec','size_expansion'):
            rows.append({'config':config,'metric':metric,**summary([s[metric] for s in data])})
    # Paired repeat ratios: useful descriptive CI, not independent execution-order randomization.
    for config in sorted({s['config'] for s in samples}):
        for reference in ('PLAIN','AES-DEC'):
            ref={s['repeat']:s for s in samples if s['config']==reference}
            ratios=[100*(s['end_to_end_sec']/ref[s['repeat']]['end_to_end_sec']-1) for s in samples if s['config']==config and s['repeat'] in ref]
            if ratios: rows.append({'config':config,'metric':f'end_to_end_overhead_percent_vs_{reference}',**summary(ratios)})
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    (output/'summary.json').write_text(json.dumps({'status':run['status'],'source':str(run_path),'bootstrap_resamples':2000,'seed':2024,'rows':rows},indent=2),encoding='utf-8')
    with (output/'summary.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader();writer.writerows(rows)
    table=['# Measured samples: '+run['status'],'','| Configuration | Metric | Median | IQR | Bootstrap 95% CI | n |','|---|---|---:|---:|---|---:|']
    for r in rows: table.append(f"|{r['config']}|{r['metric']}|{r['median']:.6g}|{r['iqr']:.6g}|[{r['median_bootstrap_ci95_low']:.6g}, {r['median_bootstrap_ci95_high']:.6g}]|{r['n']}|")
    (output/'table.md').write_text('\n'.join(table),encoding='utf-8')
    # Dependency-free vector charts are always generated from actual samples.
    for metric in ('end_to_end_sec','protected_bytes'):
        selected=[r for r in rows if r['metric']==metric]; maximum=max((r['median'] for r in selected),default=1) or 1
        elements=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="400" viewBox="0 0 900 400">','<rect width="900" height="400" fill="white"/>',f'<text x="30" y="30" font-family="sans-serif" font-size="16">{html.escape(metric)}: actual sample medians</text>',f'<text x="30" y="55" font-family="sans-serif" font-size="11">{html.escape(run["status"])}</text>']
        for i,r in enumerate(selected):
            y=90+i*65; width=600*r['median']/maximum
            elements.extend([f'<text x="25" y="{y+20}" font-family="sans-serif">{html.escape(r["config"])}</text>',f'<rect x="140" y="{y}" width="{width:.2f}" height="30" fill="#315b8a"/>',f'<text x="{150+width:.2f}" y="{y+20}" font-family="sans-serif" font-size="12">{r["median"]:.6g}</text>'])
        elements.extend(['<text x="30" y="380" font-family="sans-serif" font-size="11">Smoke is not publication evidence; numerical uncertainty is in summary.csv.</text>','</svg>'])
        (output/(metric+'.svg')).write_text('\n'.join(elements),encoding='utf-8')
    if charts:
        import matplotlib.pyplot as plt
        for metric in ('end_to_end_sec','protected_bytes'):
            selected=[r for r in rows if r['metric']==metric]
            fig,ax=plt.subplots(); ax.bar([r['config'] for r in selected],[r['median'] for r in selected]); ax.set_ylabel(metric); ax.set_title(run['status']); fig.tight_layout(); fig.savefig(output/(metric+'.png'));plt.close(fig)
    return rows
