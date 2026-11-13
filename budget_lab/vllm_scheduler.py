"""EXPERIMENTAL vLLM V1 internal-scheduler subclass (target v0.32.0).

Requires an installed, compatible vLLM runtime; mocked unit tests alone do
not demonstrate successful engine integration or inference speedups.

Underlying vLLM Scheduler.schedule() reads self.max_num_scheduled_tokens
once at the beginning of each step. This class temporarily selects that
budget before dispatching to the parent scheduler. The scheduler config's
max_num_batched_tokens remains the fixed GPU execution capacity.

The custom scheduler API is explicitly marked non-public by vLLM.
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from vllm.v1.core.sched.scheduler import Scheduler
from .budget_policy import BudgetController


class PressureAwareScheduler(Scheduler):
    """Heuristic in-engine per-iteration token-budget adaptation.

    Not an external request-admission controller. No claim of improvement.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._research_ceiling = int(self.max_num_scheduled_tokens)
        self._research_policy = BudgetController(
            self._research_ceiling,
            min_tokens=int(os.getenv('BUDGET_LAB_MIN_TOKENS', '256')),
            queue_high=int(os.getenv('BUDGET_LAB_QUEUE_HIGH', '8')),
            decode_guard=int(os.getenv('BUDGET_LAB_DECODE_GUARD', '2')),
            min_hold_steps=int(os.getenv('BUDGET_LAB_MIN_HOLD', '3')),
        )
        # Optional sampling: instrumentation can distort performance; off by default.
        self._research_log_path = os.getenv('BUDGET_LAB_SAMPLE_LOG', '')
        self._research_log_every = max(1, int(os.getenv('BUDGET_LAB_LOG_EVERY', '100')))
        self._research_step_count = 0
        self.research_last_decision = None

    def schedule(self, throttle_prefills: bool = False):
        active = len(self.running)
        # Prompt completion is a proxy for decode-active; does not assume
        # final generation length is known at decision time.
        decode_active = sum(
            1 for r in self.running
            if r.num_computed_tokens >= r.num_prompt_tokens
        )
        decision = self._research_policy.decide(
            waiting=len(self.waiting), active=active, decoding=decode_active
        )
        self.research_last_decision = decision
        self._research_step_count += 1
        # Only change the budget while parent schedule() executes, restoring
        # it even if vLLM raises. This avoids cross-step configuration drift.
        previous = self.max_num_scheduled_tokens
        self.max_num_scheduled_tokens = decision.budget
        try:
            output = super().schedule(throttle_prefills=throttle_prefills)
            # Record returned engine allocations, not just the requested ceiling.
            allocations = getattr(output, 'num_scheduled_tokens', None)
            if allocations is not None and sum(allocations.values()) > decision.budget:
                raise RuntimeError('Engine exceeded experimental token ceiling')
            if self._research_log_path and self._research_step_count % self._research_log_every == 0:
                with Path(self._research_log_path).open('a', encoding='utf-8') as out:
                    out.write(json.dumps({
                        'pid': os.getpid(), 'monotonic_s': time.monotonic(),
                        'step': self._research_step_count,
                        'scheduler_class': type(self).__name__,
                        'budget': decision.budget, 'ceiling': self._research_ceiling,
                        'regime': decision.regime, 'waiting': decision.waiting,
                        'active': decision.active, 'decoding': decision.decoding,
                        'num_scheduled_tokens': allocations,
                        'actual_tokens': sum(allocations.values()) if allocations is not None else None,
                    }) + '\n')
            return output
        finally:
            self.max_num_scheduled_tokens = previous


class InstrumentedFixedScheduler(PressureAwareScheduler):
    """Same audit overhead; the selected static ceiling stays unchanged."""
    def schedule(self, throttle_prefills=False):
        from .budget_policy import BudgetDecision
        class Fixed:
            def decide(_, waiting, active, decoding):
                return BudgetDecision(self._research_ceiling, 'fixed', waiting, active, decoding)
        self._research_policy = Fixed()
        return super().schedule(throttle_prefills=throttle_prefills)
