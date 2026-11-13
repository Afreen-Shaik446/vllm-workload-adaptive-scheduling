"""Generate deterministic open-loop traces; exact token IDs avoid word estimates."""
import argparse, hashlib, json, random
from pathlib import Path

def generate(tokenizer, workload, seed, rate, count):
    if workload not in ('stable_short','stable_mixed','bursty_short','bursty_mixed','decode_heavy','bursty_decode_heavy') or count<1 or rate<=0: raise ValueError('Invalid workload/count/rate')
    rng=random.Random(seed); t=0.; rows=[]
    # Natural-language corpus; shuffled topics and nonce vary prompts. No chat template.
    topics=['distributed systems','GPU memory','network queues','database indexing',
            'operating systems','request scheduling','parallel computing']
    for i in range(count):
        mixed=workload.endswith('mixed') or 'decode_heavy' in workload
        group='long' if mixed and rng.random()<.5 else 'short'
        n=128 if 'decode_heavy' in workload else (2048 if group=='long' else 128)
        topic=rng.choice(topics)
        text=f'Request {seed} {i} {rng.getrandbits(32)}. Explain {topic}. '
        text+=(f'Describe {topic}, bottlenecks, latency, fairness, and practical examples. '*600)
        ids=tokenizer.encode(text,add_special_tokens=False)[:n]
        if len(ids)!=n: raise ValueError('Corpus too short')
        # Stable spacing with seeded jitter. Bursts: 32 arrivals over 31 ms,
        # then idle, retaining identical average target rate.
        at=(i//32)*32/rate+(i%32)*.001 if workload.startswith('bursty') else i/rate+rng.random()*.1/rate
        rows.append(dict(request_id=str(i),arrival_offset_s=at,group=group,prompt=ids,
                         input_tokens_estimate=n,max_tokens=(1024 if group=='long' else 256) if 'decode_heavy' in workload else (256 if group=='long' else 64)))
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',default='workloads');a=p.parse_args()
    c=json.load(open('configs/protocol.json')); lock=json.load(open('configs/model_lock.json'))
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(c['model'],revision=lock['sha'],trust_remote_code=False)
    root=Path(a.root);root.mkdir(parents=True,exist_ok=False)
    index=[]
    for seed in c['seeds']:
      for rate in c['rates']:
       for work in c['workloads']:
        path=root/f'{work}_s{seed}_r{rate}.jsonl'
        path.write_text(''.join(json.dumps(x,separators=(',',':'))+'\n' for x in generate(tok,work,seed,rate,c['requests'])))
        index.append(dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),seed=seed,rate=rate,workload=work))
    (root/'index.json').write_text(json.dumps(index,indent=2))
if __name__=='__main__':main()
