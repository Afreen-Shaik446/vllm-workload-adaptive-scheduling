"""Actual HTTP model inference, no fixtures or simulated responses."""
import argparse,datetime,json,urllib.request
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args()
payload=dict(model='Qwen/Qwen2.5-1.5B-Instruct',prompt='Explain a GPU scheduling queue in one sentence.',temperature=0,max_tokens=32,seed=42)
request=urllib.request.Request('http://127.0.0.1:8000/v1/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
with urllib.request.urlopen(request,timeout=180) as response:answer=json.load(response)
Path(a.out).write_text(json.dumps({'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'request':payload,'response':answer},indent=2))
assert answer['choices'][0]['text'] and answer['usage']['completion_tokens']>0
print('Actual model response saved. This alone does not verify adaptive scheduling.')
