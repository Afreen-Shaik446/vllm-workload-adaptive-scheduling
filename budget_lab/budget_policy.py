"""Pure, CPU-testable per-step token-budget controller.

This module does not claim optimality or any measured inference improvement.
The policy is deliberately simple and pre-registered for controlled evaluation.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetDecision:
    budget: int
    regime: str
    waiting: int
    active: int
    decoding: int


class BudgetController:
    """Selects a bounded token ceiling without predicting output lengths.

    Regimes:
      idle: no mixed prefill/decode pressure, use full budget;
      moderate: new queue exists while decodes are active, use half;
      heavy: >= queue_high waiting and >= decode_guard running decode,
             use one quarter of the ceiling.
    Hysteresis holds a regime for `min_hold_steps` decisions to avoid jitter.
    This is a heuristic candidate, not a validated research contribution.
    """

    def __init__(self, ceiling: int, *, min_tokens: int = 256,
                 queue_high: int = 8, decode_guard: int = 2,
                 min_hold_steps: int = 3):
        if ceiling < 1 or min_tokens < 1 or queue_high < 1 or decode_guard < 1 or min_hold_steps < 0:
            raise ValueError('All bounds must be positive; hold may be zero.')
        self.ceiling = int(ceiling)
        self.min_tokens = min(int(min_tokens), self.ceiling)
        self.queue_high = int(queue_high)
        self.decode_guard = int(decode_guard)
        self.min_hold_steps = int(min_hold_steps)
        self._regime = 'idle'
        self._steps_in_regime = 0

    def decide(self, waiting: int, active: int, decoding: int) -> BudgetDecision:
        if not (0 <= decoding <= active and waiting >= 0):
            raise ValueError('Invalid queue or decoding counts')
        if waiting >= self.queue_high and decoding >= self.decode_guard:
            proposed = 'heavy'
        elif waiting > 0 and decoding > 0:
            proposed = 'moderate'
        else:
            proposed = 'idle'
        # Avoid leaving a congested regime too quickly, unless now truly idle.
        if proposed != self._regime:
            if proposed != 'idle' and self._steps_in_regime < self.min_hold_steps:
                proposed = self._regime
            else:
                self._regime = proposed
                self._steps_in_regime = 0
        self._steps_in_regime += 1
        ratio = {'idle': 1.0, 'moderate': 0.5, 'heavy': 0.25}[self._regime]
        # Guarantee >= one token per running request where possible.
        floor = min(self.ceiling, max(self.min_tokens, active))
        budget = min(self.ceiling, max(floor, int(self.ceiling * ratio)))
        return BudgetDecision(budget, self._regime, waiting, active, decoding)
