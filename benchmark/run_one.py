"""Execute one genuine streaming benchmark against an already-running server.
No GPU resource allocation or fake results. Generates per-request CSV and logs.
"""
import argparse,subprocess,sys,json,hashlib
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--policy',required=True,choices=('fixed_256','fixed_512','fixed_1024','fixed_2048','adaptive_internal'))
    p.add_argument('--trace',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--workload',required=True)
    p.add_argument('--seed',type=int,required=True)
    p.add_argument('--rate',type=float,required=True)
    a=p.parse_args()
    base=Path(__file__).resolve().parent
    trace=Path(a.trace).resolve()
    root=Path(a.out).resolve()
    if not trace.exists():raise FileNotFoundError(trace)
    if root.exists():raise FileExistsError('Refuse to overwrite completed/partial results: '+str(root))
    meta={'policy':a.policy,'workload':a.workload,'seed':a.seed,'rate':a.rate,'trace':str(trace),'trace_sha256':hashlib.sha256(trace.read_bytes()).hexdigest(), 'bench_client':'client_observed_first_text'}
    cmd=[sys.executable,str(base/'benchmark.py'),'--trace',str(trace),'--output',str(root),'--model','Qwen/Qwen2.5-1.5B-Instruct', '--policy',a.policy,'--workload',a.workload,'--seed',str(a.seed),'--rate',str(a.rate),'--admission','open','--timeout','180']
    try:
        subprocess.run(cmd,check=True)
    finally:
        root.mkdir(parents=True,exist_ok=True)
        if root.exists() and (root/'COMPLETE').exists():
            import shutil
            shutil.copyfile(trace,root/'trace.jsonl')
            meta['trace']='trace.jsonl'
        (root/'evidence_metadata.json').write_text(json.dumps(meta,indent=2))
if __name__=='__main__':main()
