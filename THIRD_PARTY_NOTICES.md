# Third-party source attribution and review

## vLLM engine scheduler excerpt (historical GPU evidence)

The unmodified archival evidence file `evidence/pilot/Raw_RunPod_GPU_Evidence.zip`
contains `results/pilot_fixed_20261106_041612/environment/installed_schedule.py`,
a 966-line source excerpt captured from the installed vLLM scheduler at
experiment time. It is third-party source evidence, **not original code by the
researcher**. The source excerpt is retained in the original raw archive to
allow audit of the executed environment. No additional vLLM source is copied
into the ordinary project folders by this notice.

- Upstream project: https://github.com/vllm-project/vllm
- Recorded runtime: `vllm==0.32.0` (per archived environment data)
- Upstream license: Apache License, Version 2.0
- Full upstream license: https://github.com/vllm-project/vllm/blob/main/LICENSE
- License copy retained here: `third_party/vllm-Apache-2.0-LICENSE.txt`

The archival excerpt does not contain the upstream file's header, so it is
particularly important to preserve this attribution outside the ZIP. This
notice is not a legal determination that all source-level attribution,
modification notices, or upstream NOTICE requirements have been satisfied.
The repository owner should compare the captured excerpt with the precise
upstream version before wider redistribution. Neither vLLM nor the model
publisher endorses this independent research.

## Researcher-owned code and model references

The license copy under `third_party/` applies to the upstream excerpt, not to
the original `benchmark/`, `budget_lab/`, `scripts/`, `tools/` and `tests/`
code by default. Original project licensing remains undecided; see
`LICENSE_DECISION_REQUIRED.md`.

The project references Qwen/Qwen2.5-1.5B-Instruct by model and revision; model
weights are not redistributed in this repository. Any future redistribution
of model weights or extra third-party code requires separate license review.
