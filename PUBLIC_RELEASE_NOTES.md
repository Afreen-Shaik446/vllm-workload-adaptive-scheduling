# Public-release review and scope

This repository is a reproducibility-focused record of an independent **exploratory** LLM inference scheduling experiment. It is **not** a peer-reviewed paper, a university-sponsored research project, or a claim of scheduler improvement.

## Verification checks performed before publication

- `python -m pytest -q tests`: 36 tests passed in the local packaging environment.
- `python tools/verify_pilot.py --out recompute-output`: passed integrity and metric recomputation against the unchanged archived evidence ZIP; 640 recorded successful requests.
- Pattern-based inspection found no apparent API-key/token signatures or email addresses inside the supplied raw evidence. **This is not a guarantee that every sensitive string has been detected.**

## Identifiers present in the raw evidence

The unchanged `evidence/pilot/Raw_RunPod_GPU_Evidence.zip` includes a GPU hardware UUID, absolute cloud-workspace paths (`/workspace/` and `/root/`), detailed runtime logs, and synthetic prompts/streamed responses. These are **not needed for an employer project**. **The original archive is already public in this repository.** If these identifiers should not remain public, remove or replace the archive and review repository history and copies; a deletion commit alone does not erase an older Git object. Redacting it requires an updated hash/audit path and a clearly labeled derivative of the evidence; do not silently change the archived original.

## Scientific interpretation

One seed, one workload family, one model and one GPU: the adaptive controller changed scheduled-token caps but performed worse than fixed-2048 on client-observed P99 time-to-first-nonempty-text and output-token throughput. Do not infer general superiority or infer server-side queue waiting from client-observed TTFT. The code and report acknowledge AI-assisted implementation.

## Third-party and license considerations

- This repository does **not** vendor model weights. Its model is Qwen2.5-1.5B-Instruct, referenced by model name and revision.
- The recorded archive contains `environment/installed_schedule.py`, a copy of the installed upstream vLLM scheduler source captured during execution. The upstream attribution and a copy of its Apache-2.0 license are included in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and `third_party/`; the repository owner should still check whether all upstream copyright and any NOTICE requirements are met.
- The applicant has not chosen a license for the original experiment scripts. GitHub does not require a license to make code publicly visible, but absence of a license restricts others' reuse rights; see `LICENSE_DECISION_REQUIRED.md`.

## Publication status

Published publicly at https://github.com/Afreen-Shaik446/vllm-workload-adaptive-scheduling. The README, source code, benchmark configurations, CPU tests, original GPU pilot evidence, and audit reports are publicly accessible. This is a **software research repository**, not a peer-reviewed paper or proof of a superior scheduler. The public evidence contains hardware and environment metadata, and the licensing review remains outstanding.
