# Public-release review and scope

This repository is a reproducibility-focused record of an independent **exploratory** LLM inference scheduling experiment. It is **not** a peer-reviewed paper, a university-sponsored research project, or a claim of scheduler improvement.

## Verified checks for this release candidate

- `python -m pytest -q tests`: 36 tests passed in the local packaging environment.
- `python tools/verify_pilot.py --out recompute-output`: passed integrity and metric recomputation against the unchanged archived evidence ZIP; 640 recorded successful requests.
- Pattern-based inspection found no apparent API-key/token signatures or email addresses inside the supplied raw evidence. **This is not a guarantee that every sensitive string has been detected.**

## Identifiers present in the raw evidence

The unchanged `evidence/pilot/Raw_RunPod_GPU_Evidence.zip` includes a GPU hardware UUID, absolute cloud-workspace paths (`/workspace/` and `/root/`), detailed runtime logs, and synthetic prompts/streamed responses. These are **not needed for an employer project**. If you do not want the hardware/runtime metadata made public, do not upload that ZIP unchanged. Redacting it requires an updated hash/audit path and a clearly labeled derivative of the evidence; do not silently change the archived original.

## Scientific interpretation

One seed, one workload family, one model and one GPU: the adaptive controller changed scheduled-token caps but performed worse than fixed-2048 on client-observed P99 time-to-first-nonempty-text and output-token throughput. Do not infer general superiority or infer server-side queue waiting from client-observed TTFT. The code and report acknowledge AI-assisted implementation.

## Third-party and license considerations

- This repository does **not** vendor model weights. Its model is Qwen2.5-1.5B-Instruct, referenced by model name and revision.
- The recorded archive contains `environment/installed_schedule.py`, a copy of the installed upstream vLLM scheduler source captured during execution. Check upstream notices and the project's applicable license before distributing derived or copied code.
- The applicant has not chosen a license for the original experiment scripts. GitHub does not require a license to make code publicly visible, but absence of a license restricts others' reuse rights; see `LICENSE_DECISION_REQUIRED.md`.

## Publication status

This local package is **not** live on GitHub until the owner creates the repository, commits the files, and verifies its visibility. The ChatGPT GitHub integration returned a 403 for repository writes; publication was not completed through that connection.
