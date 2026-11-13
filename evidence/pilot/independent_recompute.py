#!/usr/bin/env python3
"""Independently recompute major pilot metrics from request records + audit serving logs.
No code from the supplied benchmark analysis is imported. Inputs are user-supplied evidence.
"""
from pathlib import Path
from collections import Counter, defaultdict
import json, csv, hashlib, numpy as np, datetime

ROOT=Path(__file__).resolve().parent / 'results/pilot_fixed_20261106_041612'
ANALYSIS=ROOT.parent/(ROOT.name+'_analysis')
RECOMP=Path(__file__).resolve().parent/'independent_results'
RECOMP.mkdir(parents=True, exist_ok=True)
reported={r['policy']:r for r in csv.DictReader((ANALYSIS/'summary.csv').open())}
policies=['fixed_256','fixed_512','fixed_1024','fixed_2048','adaptive_internal']
results=[]; all_diffs=[]; evidence=[]; policy_rows={}
for p in policies:
    slug='bursty_mixed_r16_s42_'+p
    rundir=ROOT/'runs'/slug
    serverdir=ROOT/'server_logs'/slug
    rows=list(csv.DictReader((rundir/'requests.csv').open()))
    policy_rows[p]=rows
    assert len(rows)==128 and (rundir/'COMPLETE').exists(), (p,'incomplete')
    statuses=Counter(r['status'] for r in rows)
    assert statuses == {'ok':128},(p,statuses)
    ids=[r['request_id'] for r in rows]
    assert len(set(ids))==128, (p,'duplicate IDs')
    tracehash=hashlib.sha256((rundir/'trace.jsonl').read_bytes()).hexdigest()
    assert len(set(r['trace_sha256'] for r in rows))==1 and rows[0]['trace_sha256']==tracehash
    assert all(r['policy']==p and r['workload']=='bursty_mixed' for r in rows)
    def diffms(r,end,start):return 1000*(float(r[end])-float(r[start]))
    ttft=np.array([diffms(r,'first_text_s','arrival_s') for r in rows])
    e2e=np.array([diffms(r,'finish_s','arrival_s') for r in rows])
    adm=np.array([diffms(r,'dispatch_s','arrival_s') for r in rows])
    total_output=sum(int(r['output_tokens']) for r in rows)
    span=max(float(r['finish_s']) for r in rows)-min(float(r['arrival_s']) for r in rows)
    tpot=np.array([float(r['client_tpot_ms']) for r in rows])
    s=reported[p]
    values={'all_p50_ttft_ms':float(np.percentile(ttft,50)),
            'all_p95_ttft_ms':float(np.percentile(ttft,95)),
            'all_p99_ttft_ms':float(np.percentile(ttft,99)),
            'all_p99_e2e_ms':float(np.percentile(e2e,99)),
            'valid_output_tokens_s':total_output/span,
            'all_p99_client_tpot_ms':float(np.percentile(tpot,99)),
            'all_p99_client_admission_delay_ms':float(np.percentile(adm,99))}
    for field,v in values.items():
        if field in s and s[field]:
            delta=float(s[field])-v
            all_diffs.append(abs(delta))
            if abs(delta)>max(1e-5,abs(v)*1e-6):
                print('DISAGREEMENT',p,field,'recomputed=',v,'reported=',s[field],'diff=',delta)
    sr=[r for r in rows if r['group']=='short']
    lr=[r for r in rows if r['group']=='long']
    assert len(sr)+len(lr)==128
    for grp, rr in [('short',sr),('long',lr)]:
        arr=np.array([diffms(r,'first_text_s','arrival_s') for r in rr]);
        for q in [50,95,99]:
            field=grp+f'_p{q}_ttft_ms'
            if field in s:
                delta=abs(float(s[field])-np.percentile(arr,q))
                all_diffs.append(delta)
                if delta>1e-5:print('GROUP DISAGREEMENT',p,field,delta)
    allocations=[json.loads(l) for l in (serverdir/'allocations.jsonl').read_text().splitlines()]
    bcount=Counter(a['budget'] for a in allocations)
    nonempty=[a for a in allocations if a['actual_tokens']>0]
    violations=[(a['step'],a['actual_tokens'],a['budget']) for a in allocations if a['actual_tokens']>a['budget'] or a['budget']>a['ceiling']]
    assert not violations,(p,violations[:3])
    assert all(sum(a['num_scheduled_tokens'].values())==a['actual_tokens'] for a in allocations)
    ae={'policy':p,'steps':len(allocations),'nonempty_steps':len(nonempty),'budgets_all':sorted(bcount),
        'budgets_nonempty':sorted({a['budget'] for a in nonempty}),
        'budget_counts':dict(bcount),'actual_tokens_total':sum(a['actual_tokens'] for a in allocations),
        'max_actual_per_step':max(a['actual_tokens'] for a in allocations),'scheduler_class':list(set(a['scheduler_class'] for a in allocations))}
    evidence.append(ae)
    out={'policy':p,'n_requests':len(rows),'completed':statuses['ok'],'trace_sha256':tracehash,
         'short_n':len(sr),'long_n':len(lr),'output_tokens_total':total_output,
         'elapsed_s':span,'p50_ttft_ms':values['all_p50_ttft_ms'],
         'p95_ttft_ms':values['all_p95_ttft_ms'],'p99_ttft_ms':values['all_p99_ttft_ms'],
         'p99_e2e_ms':values['all_p99_e2e_ms'],'tokens_per_s':values['valid_output_tokens_s'],
         'p99_client_tpot_ms':values['all_p99_client_tpot_ms'],
         'short_p95_ttft_ms':float(np.percentile([diffms(r,'first_text_s','arrival_s') for r in sr],95)),
         'long_p95_ttft_ms':float(np.percentile([diffms(r,'first_text_s','arrival_s') for r in lr],95)),
         'long_p99_ttft_ms':float(np.percentile([diffms(r,'first_text_s','arrival_s') for r in lr],99)),
         'allocation_steps':ae['steps'],'allocation_budgets':ae['budgets_nonempty']}
    results.append(out)
# Cross-run identity checks
trace_hashes=set(r['trace_sha256'] for r in results)
assert len(trace_hashes)==1
id_sets={p:set(r['request_id'] for r in policy_rows[p]) for p in policies}
assert all(ids==id_sets[policies[0]] for ids in id_sets.values())
# check same per-request workload properties (input_tokens, expected output lengths, group)
fields=['group','input_tokens_estimate','requested_output_tokens']
base={r['request_id']:r for r in policy_rows['fixed_2048']}
for p in policies:
    for r in policy_rows[p]:
        for fld in fields:
            assert r[fld]==base[r['request_id']][fld],(p,r['request_id'],fld)
# Real response stream evidence, counts for first-nonempty events
stream_checks=[]
for p in policies:
    slug='bursty_mixed_r16_s42_'+p
    path=ROOT/'runs'/slug/'events.jsonl'
    events=0; parsed=0; content=0; request_ids=set(); parse_error=0
    for line in path.open():
        e=json.loads(line);events+=1;request_ids.add(e['request_id'])
        raw=e.get('line','')
        if raw.startswith('data: ') and raw[6:]!='[DONE]':
            try:
                d=json.loads(raw[6:]);parsed+=1
                for choice in d.get('choices',[]):
                    if choice.get('text'):content+=1
            except Exception:parse_error+=1
    stream_checks.append({'policy':p,'total_event_rows':events,'parsed_response_sse_json':parsed,'text_events':content,'request_ids':len(request_ids),'json_parse_error':parse_error})
# Write artifacts
with (RECOMP/'recomputed_summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=results[0].keys());w.writeheader();w.writerows(results)
(RECOMP/'scheduler_budget_audit.json').write_text(json.dumps(evidence,indent=2))
(RECOMP/'stream_integrity.json').write_text(json.dumps(stream_checks,indent=2))
stat={'five_policies':policies,'n_total_requests':sum(r['n_requests'] for r in results),'n_total_completed':sum(r['completed'] for r in results),
 'all_traces_same_sha256':list(trace_hashes)[0],'max_abs_diff_recomputed_vs_reported':max(all_diffs),
 'benchmarks_in_run_files':len(results),'request_matched_by_id_and_parameters':True,'allocations_within_budget':True,
 'stream_checks':stream_checks}
(RECOMP/'independent_audit_summary.json').write_text(json.dumps(stat,indent=2))
print('INDEPENDENT AUDIT SUMMARY',json.dumps(stat,indent=2))
for r in results: print('RECOMPUTED',r)
for e in evidence: print('SCHEDULER',e)
