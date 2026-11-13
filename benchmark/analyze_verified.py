"""Audit complete paired experiments. Never manufactures missing measurements.
Client text-event gaps are explicitly not token-level ITL. See METRICS.md.
"""
import argparse,csv,hashlib,json,math
from pathlib import Path
from collections import defaultdict
import numpy as np
POLICIES={'fixed_256','fixed_512','fixed_1024','fixed_2048','adaptive_internal'}
def quant(xs,p): return float(np.quantile(xs,p)) if len(xs) else None
def summarize(rows):
    if not rows: raise ValueError('Empty CSV')
    for r in rows:
        a,e,d,f=[float(r[x]) for x in ('arrival_s','enqueued_s','dispatch_s','finish_s')]
        if not all(math.isfinite(x) for x in (a,e,d,f)) or not a<=e<=d<=f:raise ValueError('Invalid timing')
        if r['first_text_s'] and not d<=float(r['first_text_s'])<=f:raise ValueError('Invalid first text timing')
    good=[r for r in rows if r['status']=='ok']
    completed=[r for r in rows if r['status'] in ('ok','missing_usage','token_mismatch')]
    duration=max(float(r['finish_s']) for r in rows)-min(float(r['arrival_s']) for r in rows)
    if duration<=0:raise ValueError('Invalid makespan')
    out={'requests':len(rows),'valid':len(good),'completed':len(completed),'completion_pct':100*len(completed)/len(rows),'valid_pct':100*len(good)/len(rows),'duration_s':duration,'completed_requests_s':len(completed)/duration,'valid_output_tokens_s':sum(int(r['output_tokens']) for r in good)/duration if good else None,'max_generator_lag_ms':max(1000*(float(r['enqueued_s'])-float(r['arrival_s'])) for r in rows)}
    for group,rr in [('all',good),('short',[r for r in good if r['group']=='short']),('long',[r for r in good if r['group']=='long'])]:
        out[group+'_n']=len(rr);out[group+'_tail_exploratory']=len(rr)<1000
        metrics={name:[1000*(float(r[end])-float(r[start])) for r in rr] for name,start,end in [('ttft','arrival_s','first_text_s'),('dispatch_ttft','dispatch_s','first_text_s'),('e2e','arrival_s','finish_s'),('client_admission_delay','arrival_s','dispatch_s')]}
        metrics['client_tpot']=[float(r['client_tpot_ms']) for r in rr if r.get('client_tpot_ms') not in ('',None)]
        metrics['text_event_gap']=[v for r in rr for v in json.loads(r.get('text_event_gaps_ms') or '[]')]
        for name,values in metrics.items():
            for q in (.5,.95,.99):out[f'{group}_p{int(q*100)}_{name}_ms']=quant(values,q)
    return out

def audit_run(f):
    root=f.parent
    if not (root/'COMPLETE').exists():raise ValueError('Incomplete run: '+str(root))
    rows=list(csv.DictReader(f.open()));meta=json.loads((root/'evidence_metadata.json').read_text());manifest=json.loads((root/'manifest.json').read_text())
    trace=root/meta['trace'] if not Path(meta['trace']).is_absolute() else Path(meta['trace'])
    raw=trace.read_bytes();jobs=[json.loads(x) for x in raw.decode().splitlines()];sha=hashlib.sha256(raw).hexdigest()
    ids=[r['request_id'] for r in rows];expected={r['request_id']:r for r in jobs}
    if len(expected)!=len(jobs) or len(ids)!=len(set(ids)) or set(ids)!=set(expected):raise ValueError('Request identity mismatch')
    if int((root/'COMPLETE').read_text())!=len(rows):raise ValueError('Completion count mismatch')
    if meta['trace_sha256']!=sha or manifest['admission']!='open':raise ValueError('Trace/admission mismatch')
    for r in rows:
        if r['trace_sha256']!=sha or any(str(r[k])!=str(meta[k]) for k in ('policy','workload','seed')) or float(r['rate'])!=float(meta['rate']):raise ValueError('Row metadata mismatch')
        job=expected[r['request_id']]
        if r['group']!=job['group'] or int(r['requested_output_tokens'])!=job['max_tokens'] or int(r['input_tokens_estimate'])!=job['input_tokens_estimate']:raise ValueError('Request controls mismatch')
        if r['status']=='ok' and (int(r['output_tokens'])!=job['max_tokens'] or int(r['input_tokens'])!=len(job['prompt'])):raise ValueError('Usage mismatch')
        planned=float(manifest['start_monotonic_s'])+job['arrival_offset_s']
        if abs(float(r['arrival_s'])-planned)>1e-6:raise ValueError('Arrival trace mismatch')
    return meta,rows,summarize(rows)

def bootstrap_ratios(values,seed=9321):
    # Resample whole paired run blocks; requests in a burst are correlated.
    a=np.array(values,float);rng=np.random.default_rng(seed)
    draws=np.exp(np.mean(np.log(a[rng.integers(0,len(a),(10000,len(a)))]),axis=1))
    return float(np.exp(np.mean(np.log(a)))),float(np.quantile(draws,.025)),float(np.quantile(draws,.975))

def write(path,rows):
    if rows:
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('runs');p.add_argument('--protocol',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    fs=sorted(Path(a.runs).glob('*/requests.csv'))
    if not fs:raise SystemExit('NO MEASURED DATA: no request CSVs. No graphs or estimates generated.')
    protocol=json.loads(Path(a.protocol).read_text());expected={(w,str(s),float(r)) for w in protocol['workloads'] for s in protocol['seeds'] for r in protocol['rates']}
    paired=defaultdict(dict);summaries=[];failures=[]
    for f in fs:
        m,rr,s=audit_run(f);key=(m['workload'],str(m['seed']),float(m['rate']));pol=m['policy']
        if pol in paired[key]:raise ValueError('Duplicate run condition')
        s={k:m[k] for k in ('policy','workload','seed','rate','trace_sha256')}|s
        paired[key][pol]=s;summaries.append(s);failures.extend(r for r in rr if r['status']!='ok')
    if set(paired)!=expected:raise ValueError('Preregistered matrix incomplete/unexpected')
    comparisons=[];groups=defaultdict(list)
    for key,v in paired.items():
        if set(v)!=POLICIES or len({r['trace_sha256'] for r in v.values()})!=1:raise ValueError('Unmatched policies/traces')
        ad=v['adaptive_internal']
        for base in sorted(POLICIES-{'adaptive_internal'}):
            b=v[base];r={'workload':key[0],'seed':key[1],'rate':key[2],'baseline':base,'completion_delta_pp':ad['completion_pct']-b['completion_pct']}
            for metric in ('all_p99_ttft_ms','valid_output_tokens_s','long_p95_ttft_ms','long_p99_ttft_ms','all_p99_client_tpot_ms'):
                r[metric+'_ratio']=ad[metric]/b[metric] if ad[metric] is not None and b[metric] else None
                val=r[metric+'_ratio']
                if val is not None and val>0:groups[(key[0],key[2],base,metric)].append(val)
            r['valid_for_interpretation']=ad['valid_pct']==b['valid_pct']==100 and max(ad['max_generator_lag_ms'],b['max_generator_lag_ms'])<=50
            comparisons.append(r)
    cis=[]
    for (work,rate,base,metric),values in groups.items():
        mean,lo,hi=bootstrap_ratios(values)
        cis.append(dict(workload=work,rate=rate,baseline=base,metric=metric,paired_blocks=len(values),geometric_mean_ratio=mean,ci_low=lo,ci_high=hi,warning='Exploratory: fewer than 5 paired blocks' if len(values)<5 else 'Finite-run bootstrap; no multiple-comparison correction'))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    write(out/'summary.csv',summaries);write(out/'paired_comparisons.csv',comparisons);write(out/'paired_bootstrap.csv',cis);write(out/'failed_or_invalid_requests.csv',failures)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for work,rate in sorted({(r['workload'],r['rate']) for r in summaries}):
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        for ax,metric,label in zip(axes,['all_p99_ttft_ms','valid_output_tokens_s'],['Client P99 first-text latency (ms)','Valid output tokens / s']):
            for i,pol in enumerate(sorted(POLICIES)):
                vals=[r[metric] for r in summaries if r['workload']==work and r['rate']==rate and r['policy']==pol and r[metric] is not None]
                ax.scatter([i]*len(vals),vals)
            ax.set_xticks(range(5),sorted(POLICIES),rotation=35,ha='right');ax.set_ylabel(label)
        fig.suptitle(f'{work}, offered {rate} requests/s; individual runs');fig.tight_layout();fig.savefig(out/f'{work}_r{rate}.png',dpi=180);plt.close(fig)
    (out/'AUDIT.md').write_text('Structural consistency checks passed. This does not authenticate hardware or prove live integration. Independently inspect environment, server, smoke, and scheduler-allocation logs. Latencies condition on valid completions: interpret alongside failures. Chunk gaps are not true ITL; TTFT is first nonempty text. Long TTFT is not server queue waiting. Ratios above 1 mean larger metric. Bootstrap units are paired run blocks, not independent requests. No automatic success/novelty claim.\n')
if __name__=='__main__':main()
