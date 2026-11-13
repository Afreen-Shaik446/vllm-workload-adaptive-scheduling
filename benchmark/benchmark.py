"""Streaming HTTP benchmark. TTFT is first nonempty client-observed text.
Arrival-based TTFT includes local admission delay; dispatch-based TTFT also saved.
No model execution or measurements are simulated by this program.
"""
import argparse, asyncio, csv, hashlib, json, time
from pathlib import Path
import aiohttp
from policy import decision,pick
FIELDS=['run_id','policy','workload','seed','rate','trace_sha256','request_id','group',
'arrival_s','enqueued_s','dispatch_s','first_text_s','finish_s','input_tokens_estimate',
'input_tokens','output_tokens','requested_output_tokens','status','finish_reason','error','text_event_count','text_event_gaps_ms','client_tpot_ms']

async def stream(session,url,model,r,meta,raw,timeout):
    row={**meta,**{k:r[k] for k in ['request_id','group','input_tokens_estimate','enqueued_s']},
         'arrival_s':r['scheduled_s'],'dispatch_s':time.monotonic(),'first_text_s':'',
         'input_tokens':'','output_tokens':'','requested_output_tokens':r['max_tokens'],
         'status':'error','finish_reason':'','error':''}
    done=False; reason=None; text_times=[]
    payload=dict(model=model,prompt=r['prompt'],max_tokens=r['max_tokens'],temperature=0,
        seed=meta['seed'],ignore_eos=True,stream=True,stream_options={'include_usage':True})
    try:
      async with asyncio.timeout(timeout):
       async with session.post(url+'/v1/completions',json=payload) as resp:
        if resp.status!=200: raise RuntimeError(f'HTTP {resp.status}: '+(await resp.text())[:400])
        async for rawline in resp.content:
            line=rawline.decode('utf8').strip()
            raw.write(json.dumps(dict(request_id=r['request_id'],at_s=time.monotonic(),line=line))+'\n');raw.flush()
            if not line.startswith('data:'):continue
            event=line[5:].strip()
            if event=='[DONE]':done=True;break
            chunk=json.loads(event)
            if chunk.get('error'):raise RuntimeError(str(chunk['error']))
            for choice in chunk.get('choices',[]):
                if choice.get('text'):
                    at=time.monotonic(); text_times.append(at)
                    if row['first_text_s']=='':row['first_text_s']=at
                if choice.get('finish_reason') is not None:reason=choice['finish_reason']
            u=chunk.get('usage') or {}
            for key,out in [('prompt_tokens','input_tokens'),('completion_tokens','output_tokens')]:
                if u.get(key) is not None:row[out]=u[key]
        row['finish_reason']=reason or ''
        if not done:raise RuntimeError('Stream ended without DONE')
        if row['first_text_s']=='':raise RuntimeError('No nonempty generated text')
        if reason not in ('length','stop'):raise RuntimeError('Missing or unexpected finish_reason')
        if row['input_tokens']=='' or row['output_tokens']=='':
            row['status']='missing_usage';row['error']='Stream completed; usage absent'
        elif row['input_tokens']!=r['input_tokens_estimate'] or row['output_tokens']!=r['max_tokens']:
            row['status']='token_mismatch';row['error']='Usage differs from exact requested token controls'
        else:row['status']='ok'
    except Exception as exc:row['error']=str(exc) or type(exc).__name__
    row['finish_s']=time.monotonic()
    row['text_event_count']=len(text_times)
    row['text_event_gaps_ms']=json.dumps([1000*(b-a) for a,b in zip(text_times,text_times[1:])])
    # Completion-normalized client TPOT; text chunks are NOT individual tokens.
    row['client_tpot_ms']=1000*(text_times[-1]-text_times[0])/(int(row['output_tokens'])-1) if len(text_times)>1 and row['output_tokens']!='' and int(row['output_tokens'])>1 else ''
    return row

async def run(a):
    trace=Path(a.trace); jobs=[json.loads(x) for x in trace.read_text().splitlines()]
    if not jobs:raise ValueError('Empty trace')
    assert all(jobs[i]['arrival_offset_s']<=jobs[i+1]['arrival_offset_s'] for i in range(len(jobs)-1))
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    meta=dict(run_id=root.name,policy=a.policy,workload=a.workload,seed=a.seed,rate=a.rate,
              trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest())
    pending=[];active=set();start=time.monotonic()+.1;idx=0;finished=0
    (root/'manifest.json').write_text(json.dumps(dict(**vars(a),**{'trace_hash':meta['trace_sha256'],'start_monotonic_s':start,'metric_source':'client_first_nonempty_text'}),indent=2))
    with (root/'requests.csv').open('w',newline='') as f,(root/'events.jsonl').open('w') as raw,(root/'decisions.jsonl').open('w') as dec:
     writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();f.flush()
     async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=0),timeout=aiohttp.ClientTimeout(total=None)) as session:
      while idx<len(jobs) or pending or active:
        now=time.monotonic()
        # Workload clock is independent of HTTP admission/completion (open loop).
        while idx<len(jobs) and start+jobs[idx]['arrival_offset_s']<=now:
            pending.append(dict(jobs[idx],scheduled_s=start+jobs[idx]['arrival_offset_s'],enqueued_s=now));idx+=1
        done={t for t in active if t.done()}
        for task in done:
            writer.writerow(task.result());finished+=1;f.flush()
        active-=done
        limit,quantum,order=(len(active)+len(pending),len(pending),'fifo') if a.admission=='open' else decision(pending,len(active),now,a.admission)
        dispatches=[]
        for _ in range(min(quantum,max(0,limit-len(active)),len(pending))):
            r=pending.pop(pick(pending,now,order));dispatches.append(r['request_id'])
            active.add(asyncio.create_task(stream(session,a.url,a.model,r,meta,raw,a.timeout)))
        if dispatches:
            dec.write(json.dumps(dict(at_s=now,queue_depth=len(pending)+len(dispatches),active=len(active),limit=limit,quantum=quantum,order=order,request_ids=dispatches))+'\n');dec.flush()
        await asyncio.sleep(.002)
    assert finished==len(jobs)
    (root/'COMPLETE').write_text(str(finished)+'\n')

def main():
    p=argparse.ArgumentParser()
    for name in ['trace','output','model','policy','workload']:p.add_argument('--'+name,required=True)
    p.add_argument('--url',default='http://127.0.0.1:8000');p.add_argument('--seed',type=int,required=True)
    p.add_argument('--rate',type=float,required=True);p.add_argument('--admission',choices=['open','16','64','adaptive'],required=True)
    p.add_argument('--timeout',type=float,default=180)
    asyncio.run(run(p.parse_args()))
if __name__=='__main__':main()
