"""Test the archive audit itself; uses no GPU, vLLM, or network."""
from pathlib import Path
from tools.verify_pilot import audit, percentile


def test_linear_percentile():
    assert percentile([1, 2, 3, 4], .5) == 2.5
    assert abs(percentile([1, 2, 3, 4], .95) - 3.85) < 1e-12


def test_original_pilot_archive_matches_independent_math():
    root = Path(__file__).resolve().parents[1]
    result = audit(root/"evidence/pilot/Raw_RunPod_GPU_Evidence.zip", root)
    assert result["total_completed"] == 640
    assert len(result["runs"]) == 5
    entries = {r["policy"]: r for r in result["runs"]}
    assert entries["fixed_2048"]["p99_ttft_ms"] < entries["adaptive_internal"]["p99_ttft_ms"]
