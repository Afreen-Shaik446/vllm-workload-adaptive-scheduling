"""Runs only on an existing GPU. No provisioning/payment functionality.
Restarts server per measured run. Never invokes this automatically on import.
"""
import argparse,csv,json,os,random,signal,socket,subprocess,sys,time,urllib.request
from pathlib import Path

def ready(proc):
    for _ in range(600):
        if proc.poll() is not None:raise RuntimeError('Server exited; inspect server.log')
        try:
            with urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2):return
        except Exception:time.sleep(1)
    raise TimeoutError('Server did not become healthy')
def metrics(path):
    with urllib.request.urlopen('http://127.0.0.1:8000/metrics',timeout=10) as r:path.write_bytes(r.read())
def main():
    p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--traces',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    root=Path(a.out).resolve();root.mkdir(parents=True,exist_ok=False)
    c=json.loads(Path(a.protocol).read_text());(root/'protocol.json').write_text(json.dumps(c,indent=2))
    subprocess.run([sys.executable,'scripts/runtime_probe.py','--out',str(root/'environment')],check=True,stdout=(root/'probe.log').open('w'))
    index=json.loads((Path(a.traces)/'index.json').read_text());rng=random.Random(c['order_seed']);plan=[]
    for w in c['workloads']:
      for rate in c['rates']:
       for seed in c['seeds']:
        order=c['policies'].copy();rng.shuffle(order)
        for pol in order:plan.append(dict(workload=w,rate=rate,seed=seed,policy=pol))
    (root/'execution_order.json').write_text(json.dumps(plan,indent=2))
    for condition in plan:
        w,rate,seed,pol=[condition[k] for k in ('workload','rate','seed','policy')]
        matches=[x for x in index if x['workload']==w and x['seed']==seed and float(x['rate'])==rate]
        if len(matches)!=1 or matches[0]['requests']!=c['requests']:raise ValueError('Trace index mismatch')
        trace=(Path(a.traces)/matches[0]['trace']).resolve();runid=f'{w}_r{rate}_s{seed}_{pol}'
        logs=root/'server_logs'/runid;logs.mkdir(parents=True)
        env=os.environ.copy();env.update(BUDGET_LAB_SAMPLE_LOG=str(logs/'allocations.jsonl'),BUDGET_LAB_LOG_EVERY=str(c['audit_every']),PYTHONUNBUFFERED='1')
        (logs/'launch.json').write_text(json.dumps(dict(condition=condition,command=['bash','scripts/start_vllm_server.sh',pol],audit_every=c['audit_every'],policy_controls={k:v for k,v in env.items() if k.startswith('BUDGET_LAB_')}),indent=2))
        with socket.socket() as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('127.0.0.1',8000))
        with (logs/'server.log').open('w') as log:
            proc=subprocess.Popen(['bash','scripts/start_vllm_server.sh',pol],stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
            try:
                ready(proc)
                # Warm all compared conditions with identical short+long prompts.
                for n in (128,2048):
                    payload=dict(model='Qwen/Qwen2.5-1.5B-Instruct',prompt=[1]*n,max_tokens=64,ignore_eos=True,temperature=0,seed=0)
                    req=urllib.request.Request('http://127.0.0.1:8000/v1/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(req,timeout=180) as resp:
                        result=json.load(resp)
                    if result['usage']['completion_tokens']!=64:raise RuntimeError('Warmup failed')
                subprocess.run([sys.executable,'scripts/smoke.py','--out',str(logs/'smoke.json')],check=True)
                metrics(logs/'metrics_before.prom')
                subprocess.run([sys.executable,'benchmark/run_one.py','--policy',pol,'--trace',str(trace),'--out',str(root/'runs'/runid),'--workload',w,'--seed',str(seed),'--rate',str(rate)],check=True)
                metrics(logs/'metrics_after.prom')
            finally:
                os.killpg(proc.pid,signal.SIGTERM)
                try:proc.wait(timeout=30)
                except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        subprocess.run([sys.executable,'scripts/verify_allocations.py',str(logs/'allocations.jsonl')]+([] if pol=='adaptive_internal' else ['--fixed']),stdout=(logs/'allocation_audit.log').open('w'),stderr=subprocess.STDOUT,check=False)
        # An unchanged adaptive policy is a valid negative/inconclusive workload result;
        # its failed allocation audit is retained, never silently excluded.
    (root/'MATRIX_COMPLETE').write_text(str(len(plan)))
if __name__=='__main__':main()
