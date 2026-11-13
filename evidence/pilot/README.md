# Previously executed pilot (November 6, 2026)

- `Raw_RunPod_GPU_Evidence.zip` is the original user-supplied RunPod archive.
- Raw evidence SHA256: `b74d55753bbd9bf37c20ac2fcb8361e139d22779775ee59a8a47b2c10b165d8c`
- `GPU_Pilot_Independent_Research_Report.md` is the prior independent audit narrative.
- `independent_results/` contains independently calculated metrics and structural checks.
- `independent_recompute.py` is the **historical** NumPy rechecker; it expects the raw ZIP to be extracted at its own directory into `results/`. It is preserved, not silently rewritten.
- Run `python tools/verify_pilot.py` at repository root to recompute key metrics *without NumPy and without a GPU* into `recompute-output/`.
- These hashes and on-disk logs provide file integrity and provenance evidence, **not cryptographic proof of a GPU run**. The independent calculation is not a second GPU execution.
- The synthetic benchmark trace contains no enterprise data; review server logs and archive contents before publishing.
