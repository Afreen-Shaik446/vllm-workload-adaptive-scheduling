"""Second calculation path using stdlib only. Does not import the analyzer."""
import argparse,csv,math
from pathlib import Path

def quant(values,p):
    v=sorted(values);x=(len(v)-1)*p;lo=math.floor(x);hi=math.ceil(x)
    return v[lo]+(v[hi]-v[lo])*(x-lo)
def main():
    p=argparse.ArgumentParser();p.add_argument('runs');p.add_argument('summary');a=p.parse_args()
    summary=list(csv.DictReader(Path(a.summary).open()));checked=0
    for s in summary:
        candidates=[]
        for f in Path(a.runs).glob('*/requests.csv'):
            rows=list(csv.DictReader(f.open()))
            if rows and all(str(rows[0][k])==str(s[k]) for k in ('policy','workload','seed')) and float(rows[0]['rate'])==float(s['rate']):candidates.append(rows)
        if len(candidates)!=1:raise ValueError('Ambiguous/missing run')
        rr=candidates[0];good=[r for r in rr if r['status']=='ok'];duration=max(float(r['finish_s']) for r in rr)-min(float(r['arrival_s']) for r in rr)
        if not good:raise ValueError('No valid requests; independent latency estimate unavailable')
        estimates={'valid_output_tokens_s':sum(int(r['output_tokens']) for r in good)/duration}
        for q in (.5,.95,.99):estimates[f'all_p{int(q*100)}_ttft_ms']=quant([1000*(float(r['first_text_s'])-float(r['arrival_s'])) for r in good],q)
        for key,value in estimates.items():
            if not math.isclose(value,float(s[key]),rel_tol=1e-9,abs_tol=1e-6):raise ValueError('Independent calculation mismatch: '+key)
        checked+=1
    if not checked:raise SystemExit('No summaries to verify')
    print(f'Independent stdlib TTFT/throughput calculation agrees for {checked} runs. Hardware/provenance not authenticated by this check.')
if __name__=='__main__':main()
