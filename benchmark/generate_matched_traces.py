"""Create byte-identical workload traces shared across all scheduling policies.
Runs locally after model tokenizer download; does not generate benchmark results.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from workload import generate

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    p.add_argument('--count',type=int,default=300);p.add_argument('--rate',type=float,default=8)
    p.add_argument('--seeds',type=int,nargs='+',default=[42,43,44])
    a=p.parse_args()
    if a.count<1 or a.rate<=0:raise ValueError('count and rate must be positive')
    from transformers import AutoTokenizer
    model='Qwen/Qwen2.5-1.5B-Instruct'
    sha='989aa7980e4cf806f80c7fef2b1adb7bc71aa306'
    tok=AutoTokenizer.from_pretrained(model,revision=sha,trust_remote_code=False)
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=False)
    rows=[]
    for seed in a.seeds:
        for workload in ('stable_short','stable_mixed','bursty_short','bursty_mixed','decode_heavy','bursty_decode_heavy'):
            trace=dest/f'{workload}_s{seed}_r{a.rate:g}.jsonl'
            trace.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in generate(tok,workload,seed,a.rate,a.count)))
            rows.append({'trace':trace.name,'workload':workload,'seed':seed,'rate':a.rate,'requests':a.count,'sha256':hashlib.sha256(trace.read_bytes()).hexdigest()})
    (dest/'index.json').write_text(json.dumps(rows,indent=2))
    print('Created',len(rows),'trace files (not inference measurements).')
if __name__=='__main__':main()
