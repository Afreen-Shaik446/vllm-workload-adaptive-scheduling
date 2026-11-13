"""Mathematical/protocol fixtures ONLY. Never inference observations."""
import argparse,asyncio,csv,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'benchmark'));sys.path.insert(0,str(ROOT/'scripts'))
from workload import generate
from analyze_verified import summarize,bootstrap_ratios,audit_run
from verify_allocations import verify
from benchmark import run
from aiohttp import web
class Tokenizer:
    def encode(self,text,add_special_tokens=False):return [1]*10000
class VerificationTests(unittest.TestCase):
    def test_decode_heavy_has_long_generations(self):
        rr=generate(Tokenizer(),'decode_heavy',42,8,100)
        self.assertEqual({len(x['prompt']) for x in rr},{128});self.assertEqual({x['max_tokens'] for x in rr},{256,1024})
    def test_invalid_workload_rejected(self):
        with self.assertRaises(ValueError):generate(Tokenizer(),'typo',42,8,10)
    def test_bursty_decode_reproducible(self):
        a=generate(Tokenizer(),'bursty_decode_heavy',42,8,100)
        self.assertEqual(a,generate(Tokenizer(),'bursty_decode_heavy',42,8,100));self.assertEqual(a[32]['arrival_offset_s'],4)
    def test_bootstrap_constant_ratio(self):self.assertEqual(bootstrap_ratios([1]*5),(1,1,1))
    def test_bootstrap_reproducible(self):self.assertEqual(bootstrap_ratios([.8,1,1.2]),bootstrap_ratios([.8,1,1.2]))
    def test_fake_parent_no_allocation_rejected(self):
        with self.assertRaises(ValueError):verify([dict(num_scheduled_tokens=None)])
    def test_no_adaptation_rejected(self):
        with self.assertRaises(ValueError):verify([dict(num_scheduled_tokens={'x':1},actual_tokens=1,budget=2048,ceiling=2048)])
    def test_overbudget_rejected(self):
        with self.assertRaises(ValueError):verify([dict(num_scheduled_tokens={'x':513},actual_tokens=513,budget=512,ceiling=2048)])
    def test_allocation_consistency_fixture(self):
        rows=[dict(num_scheduled_tokens={'x':n},actual_tokens=n,budget=b,ceiling=2048) for n,b in [(128,2048),(512,512)]]
        self.assertEqual(verify(rows)['budgets'],[512,2048])
    def test_first_text_outside_interval_rejected(self):
        with self.assertRaises(ValueError):summarize([dict(arrival_s=0,enqueued_s=0,dispatch_s=1,finish_s=2,first_text_s=3)])
    def test_failure_in_throughput_denominator(self):
        b=dict(arrival_s=0,enqueued_s=0,dispatch_s=0,first_text_s=1,finish_s=2,status='ok',group='long',output_tokens=4,client_tpot_ms=5,text_event_gaps_ms='[5, 10]')
        fail=b|dict(status='error',first_text_s='',finish_s=10)
        s=summarize([b,fail]);self.assertEqual(s['valid_output_tokens_s'],.4);self.assertEqual(s['completion_pct'],50);self.assertEqual(s['long_p99_ttft_ms'],1000)
class StreamTests(unittest.IsolatedAsyncioTestCase):
    async def test_open_loop_text_gaps_and_portable_audit(self):
        async def handle(req):
            payload=await req.json();resp=web.StreamResponse(headers={'Content-Type':'text/event-stream'});await resp.prepare(req)
            for text in ['fixtureA','fixtureB']:
                await asyncio.sleep(.01);await resp.write(('data: '+json.dumps({'choices':[{'text':text}]})+'\n\n').encode())
            await resp.write(('data: '+json.dumps({'choices':[{'text':'','finish_reason':'length'}],'usage':{'prompt_tokens':1,'completion_tokens':2}})+'\n\ndata: [DONE]\n\n').encode());return resp
        app=web.Application();app.router.add_post('/v1/completions',handle);runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);trace=root/'trace.jsonl';trace.write_text(json.dumps(dict(request_id='0',arrival_offset_s=0,group='short',prompt=[1],input_tokens_estimate=1,max_tokens=2))+'\n')
                dest=root/'run';args=argparse.Namespace(trace=str(trace),output=str(dest),model='SOFTWARE_FIXTURE',policy='fixed_256',workload='stable_short',seed=42,rate=8,admission='open',timeout=2,url=f'http://127.0.0.1:{port}')
                await run(args);row=list(csv.DictReader((dest/'requests.csv').open()))[0]
                self.assertEqual(row['status'],'ok');self.assertEqual(int(row['text_event_count']),2);self.assertEqual(len(json.loads(row['text_event_gaps_ms'])),1)
                import hashlib
                (dest/'trace.jsonl').write_bytes(trace.read_bytes());m=dict(trace='trace.jsonl',trace_sha256=hashlib.sha256(trace.read_bytes()).hexdigest(),policy='fixed_256',workload='stable_short',seed=42,rate=8)
                (dest/'evidence_metadata.json').write_text(json.dumps(m));self.assertEqual(audit_run(dest/'requests.csv')[2]['valid'],1)
                (dest/'COMPLETE').write_text('2')
                with self.assertRaises(ValueError):audit_run(dest/'requests.csv')
        finally:await runner.cleanup()

class AnalysisPipelineTests(unittest.TestCase):
    def test_complete_fixture_matrix_and_independent_calculation(self):
        # Mathematical fixture, temp-only; no model/GPU execution represented.
        import hashlib,subprocess
        from benchmark import FIELDS
        policies=['fixed_256','fixed_512','fixed_1024','fixed_2048','adaptive_internal']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);runs=root/'runs';runs.mkdir();trace=json.dumps(dict(request_id='0',arrival_offset_s=0,group='long',prompt=[1],input_tokens_estimate=1,max_tokens=2))+'\n';sha=hashlib.sha256(trace.encode()).hexdigest()
            protocol=root/'protocol.json';protocol.write_text(json.dumps(dict(workloads=['stable_mixed'],seeds=[42],rates=[8])))
            for pol in policies:
                d=runs/pol;d.mkdir();(d/'COMPLETE').write_text('1');(d/'trace.jsonl').write_text(trace)
                (d/'manifest.json').write_text(json.dumps(dict(admission='open',start_monotonic_s=0)))
                (d/'evidence_metadata.json').write_text(json.dumps(dict(policy=pol,workload='stable_mixed',seed=42,rate=8,trace='trace.jsonl',trace_sha256=sha)))
                row=dict.fromkeys(FIELDS,'');row.update(run_id=pol,policy=pol,workload='stable_mixed',seed=42,rate=8,trace_sha256=sha,request_id='0',group='long',arrival_s=0,enqueued_s=0,dispatch_s=0,first_text_s=1,finish_s=2,input_tokens_estimate=1,input_tokens=1,output_tokens=2,requested_output_tokens=2,status='ok',finish_reason='length',client_tpot_ms=500,text_event_count=2,text_event_gaps_ms='[500]')
                with (d/'requests.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerow(row)
            r=subprocess.run([sys.executable,str(ROOT/'benchmark/analyze_verified.py'),str(runs),'--protocol',str(protocol),'--out',str(root/'out')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(len(list((root/'out').glob('*.png'))),1)
            r=subprocess.run([sys.executable,str(ROOT/'scripts/independent_check.py'),str(runs),str(root/'out/summary.csv')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            (runs/'fixed_512/COMPLETE').unlink()
            r=subprocess.run([sys.executable,str(ROOT/'benchmark/analyze_verified.py'),str(runs),'--protocol',str(protocol),'--out',str(root/'invalid')],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0);self.assertFalse((root/'invalid').exists())
