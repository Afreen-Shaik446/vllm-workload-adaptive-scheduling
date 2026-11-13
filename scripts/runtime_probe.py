"""Records local runtime evidence; refuses to pass without real CUDA/vLLM."""
import argparse,datetime,hashlib,importlib.metadata as md,json,platform,shutil,subprocess,sys
from pathlib import Path

def capture(cmd):
    try:
        r=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
        return {'command':cmd,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    except Exception as e:return {'command':cmd,'error':str(e)}
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    data={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':sys.version,'platform':platform.platform(),'gpu_verified':False,'packages':{}}
    for name in ('vllm','torch','transformers','aiohttp','numpy'):
        try:data['packages'][name]=md.version(name)
        except md.PackageNotFoundError:data['packages'][name]=None
    for name,cmd in [('nvidia',['nvidia-smi','--query-gpu=name,uuid,driver_version,memory.total,compute_cap','--format=csv']),('pip_check',[sys.executable,'-m','pip','check']),('pip_freeze',[sys.executable,'-m','pip','freeze'])]:
        data[name]=capture(cmd)
    try:
        import torch,vllm,inspect
        from vllm.v1.core.sched.scheduler import Scheduler
        source=inspect.getsource(Scheduler.schedule)
        data.update(cuda=torch.version.cuda,cuda_available=torch.cuda.is_available(),vllm=vllm.__version__,scheduler_signature=str(inspect.signature(Scheduler.schedule)),scheduler_source_sha256=hashlib.sha256(source.encode()).hexdigest())
        (out/'installed_schedule.py').write_text(source)
        data['gpu_verified']=torch.cuda.is_available() and vllm.__version__=='0.32.0' and data['pip_check'].get('returncode')==0 and data['nvidia'].get('returncode')==0
        if torch.cuda.is_available():data['device_name']=torch.cuda.get_device_name(0)
    except Exception as e:data['import_error']=str(e)
    code_root=Path(__file__).resolve().parents[1]
    data['code_sha256']={str(p.relative_to(code_root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(code_root.rglob('*.py')) if 'results' not in p.parts}
    (out/'environment.json').write_text(json.dumps(data,indent=2));print(json.dumps(data,indent=2))
    if not data['gpu_verified']:raise SystemExit(2)
if __name__=='__main__':main()
