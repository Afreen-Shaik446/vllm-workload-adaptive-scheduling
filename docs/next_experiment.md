# Next experiments and criteria for a stronger research claim

## Evidence tiers

1. **Archived pilot**: prior GPU execution + independently recomputed arithmetic; single seed `42`, 128 requests × 5 policies. This is already in the repository.
2. **Fresh reproduction**: same model revision, code, and recorded protocol on a GPU you already have permission to use. Preserve machine version, new timestamps, raw logs, trace hashes, and all failures. Expect noise; do not require identical numbers.
3. **Three-seed exploratory extension**: seeds `7`, `17`, `29` with *matched traces per policy*, using `configs/three_seed_exploration.json`. An offered rate of 16 requests/s was used in the previous pilot, but **not calibrated** for the new runs. This is not a confirmatory result.
4. **Research-grade confirmation**: calibrate offered load on disjoint pilot seeds and workload families, select a fixed comparator using an announced rule, freeze parameters/hypotheses, run at least five independent seeds and enough long requests for robust tail/fairness assessment, publish per-seed values and appropriate block-wise uncertainty. Consider stable, bursty, and decode-heavy request mixes, and evaluate scheduler overhead/instrumentation effects.

## Guardrails to decide before final comparison

- Client P99 TTFT lower than the *calibrated* strongest fixed baseline under the target regime.
- Valid output token throughput at least 95% of the baseline.
- Long-request P95 TTFT no more than 110% of the baseline.
- Completion rate no more than one percentage point lower.

These thresholds are **research design choices**, not existing measured outcomes. Guardrails must be frozen before confirming results, and both favorable and unfavorable results must be reported. A three-seed demonstration cannot establish robust generalization.

## Basic data-integrity requirements

- Compare same trace SHA256 within each seed/rate/workload across policies; verify matching request IDs, groups, token lengths and decode controls.
- Preserve the full execution order and verify the policy server restarted and warmed before each condition.
- Save raw `requests.csv`, `events.jsonl`, `trace.jsonl`, server logs, `allocations.jsonl`, version probe, command arguments, errors, and analysis artifacts.
- Check workload dispatch lag (`enqueued_s-arrival_s`), unexpected model usage lengths, failures/timeouts, and GPU contention before interpreting performance.
- Retain not just aggregate percentile scores, but the complete per-request distribution and per-run paired comparisons.
- For P99, the number of requests in the relevant *cohort* matters. A single small experiment is highly sensitive to a few outliers.
- Avoid treating client TTFT or stream-chunk gaps as server queue wait or token-level ITL.
