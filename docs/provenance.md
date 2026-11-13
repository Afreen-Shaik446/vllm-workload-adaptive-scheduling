# Reproducibility provenance and limits

## Source lineage

The core code in `benchmark/`, `budget_lab/`, `scripts/`, `tests/`, and the original files under `configs/` came from the exact `Research_Source_Code.zip` independently audited with the 2026-11-06 RunPod evidence. Original source archive SHA256:
`d4d778b42f51c9998b7fea511692cf3160211f35d18b3a89fd4acc1cd17c60a1`.

The runner `scripts/run_matrix.py` is the original launcher with the documented `SO_REUSEADDR` port-bind fix. Its SHA256 is `c98c7a0d9d4f8b7f3af9d1cf0a1e4e55e02fb6b6e73ac851f7360e32bb83e4da`, matching the code hash saved in `evidence/pilot/Raw_RunPod_GPU_Evidence.zip`'s `environment/environment.json`.

The original source ZIP also contained unrelated applicant notes; it is deliberately **not** bundled for public release. Any future changes in this repository must be recorded as separate commits. `configs/pilot_recorded_20261106.json` is copied from the *executed* evidence; the historical `configs/pilot.json` candidate uses rate 8 and should not be mislabeled as the recorded November 6 run (rate 16).

## What existing evidence can and cannot verify

- Five conditions, 128 successful requests per policy, same intended trace and request controls.
- Model pinned to Qwen/Qwen2.5-1.5B-Instruct revision `989aa7980e4cf806f80c7fef2b1adb7bc71aa306`; vLLM `0.32.0`, torch `2.13.0`, transformers `5.19.0`, NVIDIA RTX A6000 (driver `595.91.07`) according to archived environment logs.
- Scheduler allocation logs demonstrate in-engine token-cap switching for the adaptive candidate. They also include warmups and smoke tests; not every logged step belongs exclusively to measured requests.
- Client P99 first nonempty text is measured from intended arrival, including local dispatch/network effects. Client text-event gaps are NOT token-level inter-token latency.
- The first pilot is single-seed, single workload, single GPU, with sequential policy runs and no uncertainty estimate from independent repeated blocks.
- Neither local hash checks nor a captured `nvidia-smi` log establish independent GPU attestation.
- The scheduler implementation was AI-assisted. Do not claim peer-reviewed publication or an improvement that the evidence does not show.

## Reuse and research integrity

Review AI-assisted code and verify personally. Cite prior adaptive scheduling work; study *when* adaptation works rather than claiming the general concept is new. Preserve negative results. Do not publish university or employer confidential material, API keys, pod tokens, personally identifiable data, or unapproved datasets. Make the GitHub repository private until you have inspected all files and chosen an appropriate license.

The bundled historical audit Markdown has one editorial correction: an unexpanded `longp95diff` formatting placeholder was replaced with `116.6%`, derived from the independently recomputed long-cohort P95 values (5260.856 vs. 2428.340 ms). The raw archive and prior independent result files remain unchanged.
