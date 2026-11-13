# Repository publication and verification

This project is already published publicly at:
https://github.com/Afreen-Shaik446/vllm-workload-adaptive-scheduling

It is independent, exploratory, AI-assisted ML systems research. Public repository
availability is not a peer-reviewed paper, university endorsement, or evidence
of a statistically established scheduler performance improvement.

## Verify an existing public checkout

On a machine with Git, Python 3.10+, and enough disk space:

```bash
git clone https://github.com/Afreen-Shaik446/vllm-workload-adaptive-scheduling.git
cd vllm-workload-adaptive-scheduling
python tools/verify_pilot.py --out recompute-output
python -m pip install -r requirements-test.txt
python -m pytest -q tests
```

The evidence auditor is CPU-only and uses the unchanged archival GPU record.
The tests are deterministic software checks and are not a fresh GPU experiment.

The file manifest `SHA256SUMS.txt` lists the hashes of the checked-in files,
excluding the manifest itself. From the repository root, verify it with
`sha256sum -c SHA256SUMS.txt` (Linux) or `shasum -a 256 -c SHA256SUMS.txt`
(macOS). Recompute the manifest whenever tracked files change.

## Updating this public repository

Make changes using GitHub's file editor or by pushing a Git commit. Keep
`README.md` and all documentation at their existing paths. Record new
experiments separately from the archival 2026-11-06 UTC pilot. Do not
rewrite, relabel, or overwrite the raw experimental archive silently.

## Public review limitations

The raw RunPod archive includes a GPU UUID, rented-environment paths, and a
captured excerpt of upstream vLLM scheduler source. See
[PUBLIC_RELEASE_NOTES.md](../PUBLIC_RELEASE_NOTES.md) and
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Before wide distribution,
confirm that these identifiers and the captured code are appropriate to share.
The upstream Apache-2.0 license copy applies to the referenced upstream code,
not automatically to this project's original research scripts.

For PhD materials, describe the existing result as one independently
recomputed, single-seed exploratory GPU pilot with a negative adaptive-versus-
fixed-2048 result; not as a journal publication or verified improvement.
