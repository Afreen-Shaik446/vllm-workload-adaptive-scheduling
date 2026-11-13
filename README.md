[README (1).md](https://github.com/user-attachments/files/34827064/README.1.md)
# Workload-Adaptive Scheduling for LLM Inference

**Independent ML systems research — status as of November 13, 2026:** An NVIDIA RTX A6000 single-seed pilot was run on November 6 and its original recorded data were independently recalculated. No new GPU runs were performed while preparing this repository. The adaptive scheduler **did not** outperform the fixed-2048 baseline on the measured workload. This is independent research preparation, not a publication or a proven scheduling advance.

## Research question

When do observable queue/decode-pressure signals make per-iteration scheduling-token-budget adaptation worthwhile under heterogeneous and bursty LLM requests, compared with a well-calibrated fixed cap?

## Existing measured result (one bursty, matched seed)

| Server policy | Client P99 first-text latency | Valid output token throughput |
|---|---:|---:|
| Fixed 256 | 7.991 s | 1,286 tokens/s |
| Fixed 512 | 6.142 s | 1,409 tokens/s |
| Fixed 1024 | 4.227 s | 1,585 tokens/s |
| Fixed 2048 | **3.101 s** | **1,776 tokens/s** |
| Adaptive internal | 5.684 s | 1,435 tokens/s |

All 640 requests succeeded (128 × 5); the same generated trace SHA was used for all policies. The adaptive scheduler logged actual nonempty engine allocations at caps 512, 1024, and 2048. Values are single-seed descriptive observations, **not confidence intervals or general results**.

## 1. Audit the existing pilot now (NO GPU and NO downloads)

With Python 3.10+ from this directory:

```bash
python tools/verify_pilot.py --out recompute-output
```

This checks ZIP integrity, five matched traces, request identities and controls, completions, client-observed TTFT quantiles, output-token throughput, streamed events, allocation caps, and agreement with the archived summary. It writes an independently calculated CSV/JSON summary. The older independent NumPy audit and its output are preserved under `evidence/pilot/`.

CPU-only project tests:

```bash
python -m pip install -r requirements-test.txt
python -m pytest -q tests
```

The CPU tests validate logic/fixtures only. They do not replay LLM inference.

## 2. Reproduce the pilot on an *existing, authorized* GPU

The scripts do **not** launch cloud GPU instances or buy compute. Run on Linux with a compatible NVIDIA GPU and driver, after confirming you have permission and available budget. Exact CUDA and dependency compatibility depends on hardware. Review the recorded environment in the archived evidence. Upstream versioned CLI: https://docs.vllm.ai/en/v0.32.0/cli/serve/.

```bash
python -m venv .gpu_env
source .gpu_env/bin/activate
python -m pip install 'vllm==0.32.0' -r requirements-client.txt -r requirements-test.txt
python -m pip check
python -m pytest -q tests
nvidia-smi
# Build 128-request trace for seed 42, offered rate 16 requests/s.
python benchmark/generate_matched_traces.py --out work/pilot_traces --count 128 --rate 16 --seeds 42
# Restarts server separately for 5 policies; makes new evidence in results/.
python scripts/run_matrix.py --protocol configs/pilot_recorded_20261106.json --traces work/pilot_traces --out results/pilot_fresh
python benchmark/analyze_verified.py results/pilot_fresh/runs --protocol results/pilot_fresh/protocol.json --out results/pilot_fresh_analysis
python scripts/independent_check.py results/pilot_fresh/runs results/pilot_fresh_analysis/summary.csv
```

This uses the historical controller and the documented port-fix runner. If anything errors, save the partial `results/` and logs. Do **not** silently switch model version, GPU, batch budget, caching mode, or seed. The archived evidence already demonstrates one real run; a new replay is not guaranteed to reproduce exact latency numbers due to hardware and runtime noise.

## 3. Run the three-seed exploratory extension on the same GPU

Use a **separate** result location and new matched workload traces. A rate of 16 is carried over from the original pilot solely as a starting point, not a calibrated rate:

```bash
python benchmark/generate_matched_traces.py --out work/three_seed_traces --count 1200 --rate 16 --seeds 7 17 29
python scripts/run_matrix.py --protocol configs/three_seed_exploration.json --traces work/three_seed_traces --out results/three_seed
python benchmark/analyze_verified.py results/three_seed/runs --protocol results/three_seed/protocol.json --out results/three_seed_analysis
python scripts/independent_check.py results/three_seed/runs results/three_seed_analysis/summary.csv
```

The generator creates six predefined workload families, but the starter matrix selects only `bursty_mixed`. For a real research claim, calibrate load on disjoint seeds and extend to stable/bursty/decode-heavy conditions *before* locking the confirmatory matrix; read `docs/next_experiment.md`. Avoid declaring a successful outcome based on the exploratory extension alone.

## Source transparency

This is **independent, AI-assisted experimental research**. The measured GPU result is the negative result documented above; the code was not independently replicated on a second GPU, and a general performance improvement is not claimed. The associated archived raw logs contain an NVIDIA GPU UUID and paths from a rented Linux environment. No employer code, private application materials, or model weights are included.

## Structure

- `benchmark/` — matched workload generation, open-loop streaming benchmark, audited analysis
- `budget_lab/` — fixed and experimental in-engine scheduler classes
- `scripts/` — runtime probe, independent cross-check, server launch and experiment matrix
- `configs/` — historical, recorded and clearly labeled exploratory protocols
- `tests/` — deterministic CPU verification; not GPU results
- `tools/verify_pilot.py` — second, stdlib-only arithmetic/structural audit from archived raw evidence
- `evidence/pilot/Raw_RunPod_GPU_Evidence.zip` — **original** raw request, event, server and allocation records
- `evidence/pilot/independent_results/` — first independent audit and figures
- `docs/` — provenance, limitations, and next experiments

## Scope and provenance

The completed single-seed result was generated **before** this repository was packaged. Its original code SHA256 fingerprints, patch, server/runtime manifest, log hashes, and audit outputs are documented in `docs/provenance.md`. The Python experiment scripts were built with AI assistance, and this package has not been independently rerun on a second GPU. All new experiments must be labelled separately from the November 6 pilot. No other professional data or university application documents are included.

For privacy, attribution, and permission considerations before sharing raw experiment evidence, read [PUBLIC_RELEASE_NOTES.md](PUBLIC_RELEASE_NOTES.md). This repository is not affiliated with UC Berkeley or any other institution. No open-source license has been chosen (see `LICENSE_DECISION_REQUIRED.md`).
