"""CPU-only tests: policy invariants and scheduler-subclass delegation.

These are NOT tests against a real installed vLLM engine or GPU.
"""
import importlib
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from budget_lab.budget_policy import BudgetController


class PolicyTests(unittest.TestCase):
    def test_initial_idle(self):
        p=BudgetController(2048)
        self.assertEqual(p.decide(0,0,0).budget,2048)
    def test_moderate_when_backlogged_with_decode(self):
        p=BudgetController(2048,min_hold_steps=0)
        d=p.decide(2,4,2)
        self.assertEqual((d.regime,d.budget),('moderate',1024))
    def test_heavy_under_pressure(self):
        p=BudgetController(2048,min_hold_steps=0)
        d=p.decide(10,5,3)
        self.assertEqual((d.regime,d.budget),('heavy',512))
    def test_bounded_small_ceiling(self):
        p=BudgetController(128,min_tokens=256,min_hold_steps=0)
        self.assertEqual(p.decide(8,8,4).budget,128)
    def test_floor_guards_active(self):
        p=BudgetController(1024,min_tokens=16,min_hold_steps=0)
        self.assertGreaterEqual(p.decide(10,300,200).budget,300)
    def test_never_exceeds_ceiling(self):
        p=BudgetController(256,min_tokens=16,min_hold_steps=0)
        for active in [0,1,200,400]:
            d=p.decide(10,active,active)
            self.assertTrue(1 <= d.budget <= 256)
    def test_invalid_negative(self):
        with self.assertRaises(ValueError):BudgetController(2048).decide(-1,0,0)
    def test_invalid_decoding_excess(self):
        with self.assertRaises(ValueError):BudgetController(2048).decide(1,3,4)
    def test_invalid_constructor(self):
        with self.assertRaises(ValueError):BudgetController(0)
    def test_hysteresis(self):
        p=BudgetController(2048,min_hold_steps=2)
        self.assertEqual(p.decide(10,5,3).regime,'idle')
        self.assertEqual(p.decide(10,5,3).regime,'idle')
        self.assertEqual(p.decide(10,5,3).regime,'heavy')
    def test_idle_immediate_release(self):
        p=BudgetController(2048,min_hold_steps=0)
        p.decide(10,5,3)
        self.assertEqual(p.decide(0,0,0).regime,'idle')
    def test_heavy_recovery(self):
        p=BudgetController(2048,min_hold_steps=0)
        p.decide(10,5,3)
        self.assertEqual(p.decide(1,4,2).regime,'moderate')
    def test_zero_decoding_idle(self):
        p=BudgetController(2048,min_hold_steps=0)
        self.assertEqual(p.decide(10,5,0).regime,'idle')
    def test_medium_ratio_floor(self):
        p=BudgetController(512,min_tokens=300,min_hold_steps=0)
        self.assertEqual(p.decide(2,2,1).budget,300)


class FakeParent:
    def __init__(self,*args,**kwargs):
        self.max_num_scheduled_tokens=2048
        self.running=[]
        self.waiting=[]
        self.called=[]
        self.fail=False
    def schedule(self,throttle_prefills=False):
        self.called.append((self.max_num_scheduled_tokens,throttle_prefills))
        if self.fail:raise RuntimeError('parent failed')
        return {'budget_seen_by_parent':self.max_num_scheduled_tokens}

class FakeReq:
    def __init__(self,computed,prompt):
        self.num_computed_tokens=computed
        self.num_prompt_tokens=prompt


class IntegrationAgainstMockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        mod=types.ModuleType('vllm')
        mod1=types.ModuleType('vllm.v1')
        mod2=types.ModuleType('vllm.v1.core')
        mod3=types.ModuleType('vllm.v1.core.sched')
        mod4=types.ModuleType('vllm.v1.core.sched.scheduler')
        mod4.Scheduler=FakeParent
        cls.mock_modules={'vllm':mod,'vllm.v1':mod1,'vllm.v1.core':mod2,'vllm.v1.core.sched':mod3,'vllm.v1.core.sched.scheduler':mod4}
        cls.patcher=patch.dict(sys.modules,cls.mock_modules)
        cls.patcher.start()
        sys.modules.pop('budget_lab.vllm_scheduler',None)
        cls.mod=importlib.import_module('budget_lab.vllm_scheduler')
    @classmethod
    def tearDownClass(cls):
        sys.modules.pop('budget_lab.vllm_scheduler',None)
        cls.patcher.stop()
    def scheduler(self):
        with patch.dict('os.environ',{'BUDGET_LAB_MIN_HOLD':'0'}):
            return self.mod.PressureAwareScheduler()
    def test_custom_class_subclasses_in_engine_parent(self):
        self.assertTrue(issubclass(self.mod.PressureAwareScheduler,FakeParent))
    def test_delegates_dynamic_budget_to_parent(self):
        s=self.scheduler()
        s.waiting=list(range(10))
        s.running=[FakeReq(20,10),FakeReq(20,10),FakeReq(20,10)]
        result=s.schedule()
        self.assertEqual(result['budget_seen_by_parent'],512)
    def test_restores_original_budget(self):
        s=self.scheduler()
        s.waiting=list(range(9))
        s.running=[FakeReq(10,9),FakeReq(10,9)]
        s.schedule()
        self.assertEqual(s.max_num_scheduled_tokens,2048)
    def test_restores_budget_on_exception(self):
        s=self.scheduler()
        s.fail=True
        with self.assertRaises(RuntimeError):s.schedule()
        self.assertEqual(s.max_num_scheduled_tokens,2048)
    def test_forwards_throttle_prefills(self):
        s=self.scheduler()
        s.schedule(throttle_prefills=True)
        self.assertEqual(s.called[-1][1],True)
    def test_counts_prefill_as_non_decoding(self):
        s=self.scheduler()
        s.waiting=list(range(10))
        s.running=[FakeReq(3,20),FakeReq(20,10),FakeReq(20,10)]
        s.schedule()
        self.assertEqual(s.research_last_decision.decoding,2)
    def test_optional_log_sampling(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'decisions.jsonl'
            with patch.dict('os.environ',{'BUDGET_LAB_MIN_HOLD':'0','BUDGET_LAB_SAMPLE_LOG':str(path),'BUDGET_LAB_LOG_EVERY':'1'}):
                s=self.mod.PressureAwareScheduler()
            s.schedule()
            self.assertTrue(path.exists())
            self.assertIn('"budget": 2048',path.read_text())

if __name__=='__main__':unittest.main()
