#!/usr/bin/env python3
"""Independent, stdlib-only audit of the actual November 6 vLLM GPU pilot.

Independent of benchmark/analyze_verified.py and the prior NumPy audit.
No network access, GPU usage, synthetic benchmark outputs, or inferred data.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path
from zipfile import ZipFile

EXPECTED_ZIP_SHA = "b74d55753bbd9bf37c20ac2fcb8361e139d22779775ee59a8a47b2c10b165d8c"
EXPECTED_SOURCE_ARCHIVE_SHA = "d4d778b42f51c9998b7fea511692cf3160211f35d18b3a89fd4acc1cd17c60a1"
POLICIES = ("fixed_256", "fixed_512", "fixed_1024", "fixed_2048", "adaptive_internal")
PILOT_ROOT = "results/pilot_fixed_20261106_041612"
ANALYSIS_ROOT = PILOT_ROOT + "_analysis"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def percentile(values, q):
    """NumPy's default linear interpolated sample percentile, without NumPy."""
    v = sorted(float(x) for x in values)
    if not v:
        raise ValueError("Cannot compute percentile from zero observations")
    where = (len(v) - 1) * float(q)
    low, high = math.floor(where), math.ceil(where)
    return v[low] * (high - where) + v[high] * (where - low) if high != low else v[low]


def read_csv(zf, path):
    return list(csv.DictReader(io.StringIO(zf.read(path).decode("utf8"))))


def read_json(zf, path):
    return json.loads(zf.read(path))


def guard(test, message):
    if not test:
        raise AssertionError(message)


def nearly(x, y):
    return math.isclose(float(x), float(y), rel_tol=1e-9, abs_tol=1e-5)


def audit(archive: Path, code_root: Path):
    guard(archive.exists(), f"Archive not found: {archive}")
    guard(sha256(archive.read_bytes()) == EXPECTED_ZIP_SHA,
          "Raw evidence ZIP fingerprint differs from the recorded original")
    with ZipFile(archive) as z:
        guard(z.testzip() is None, "Corrupted evidence ZIP member")
        names = set(z.namelist())
        env = read_json(z, f"{PILOT_ROOT}/environment/environment.json")
        protocol = read_json(z, f"{PILOT_ROOT}/protocol.json")
        guard(protocol["seeds"] == [42], "Pilot must be seed 42 only")
        guard(protocol["rates"] == [16], "Pilot offered rate is 16 (not pre-run candidate 8)")
        guard(protocol["requests"] == 128, "Pilot request count unexpected")
        guard(set(protocol["policies"]) == set(POLICIES), "Policy list mismatch")
        guard(protocol["workloads"] == ["bursty_mixed"], "Workload mismatch")
        guard(env.get("vllm") == "0.32.0", "vLLM version mismatch")
        guard(env.get("device_name") == "NVIDIA RTX A6000", "Recorded GPU model mismatch")
        guard(env.get("code_sha256") and isinstance(env["code_sha256"], dict), "Code hashes missing")
        for rel, expected in env["code_sha256"].items():
            path = code_root / rel
            guard(path.exists(), f"Original benchmark code missing: {rel}")
            guard(sha256(path.read_bytes()) == expected, f"Source file differs from executed version: {rel}")
        reported = {row["policy"]: row for row in read_csv(z, f"{ANALYSIS_ROOT}/summary.csv")}
        guard(set(reported) == set(POLICIES), "Recorded summary incomplete")
        all_rows, results, allocation_results = {}, [], []
        seen_trace_hashes = set()
        all_success, all_requests = 0, 0
        for policy in POLICIES:
            slug = f"bursty_mixed_r16_s42_{policy}"
            prefix = f"{PILOT_ROOT}/runs/{slug}"
            logprefix = f"{PILOT_ROOT}/server_logs/{slug}"
            rows = read_csv(z, prefix + "/requests.csv")
            guard((prefix + "/COMPLETE") in names, f"COMPLETE missing: {policy}")
            guard(int(z.read(prefix + "/COMPLETE")) == len(rows) == 128, f"Request count mismatch: {policy}")
            guard(all(r["status"] == "ok" for r in rows), f"Invalid request status: {policy}")
            guard(len({r["request_id"] for r in rows}) == len(rows), f"Duplicated IDs: {policy}")
            guard(all(r["policy"] == policy for r in rows), f"Policy row mismatch: {policy}")
            trace_bytes = z.read(prefix + "/trace.jsonl")
            tracehash = sha256(trace_bytes)
            seen_trace_hashes.add(tracehash)
            guard(all(r["trace_sha256"] == tracehash for r in rows), f"Trace SHA mismatch: {policy}")
            meta = read_json(z, prefix + "/evidence_metadata.json")
            guard(meta["trace_sha256"] == tracehash, f"Trace metadata mismatch: {policy}")
            source_jobs = [json.loads(line) for line in trace_bytes.decode().splitlines()]
            jobs = {r["request_id"]: r for r in source_jobs}
            guard(len(jobs) == 128, f"Duplicate source-trace IDs: {policy}")
            for r in rows:
                j = jobs[r["request_id"]]
                guard(r["group"] == j["group"], f"Request group mismatch: {policy}")
                guard(int(r["input_tokens_estimate"]) == j["input_tokens_estimate"], "Prompt token mismatch")
                guard(int(r["requested_output_tokens"]) == j["max_tokens"], "Requested output token mismatch")
                guard(int(r["output_tokens"]) == j["max_tokens"], "Actual output tokens mismatch")
                guard(int(r["input_tokens"]) == j["input_tokens_estimate"], "Usage prompt tokens mismatch")
                ts = [float(r[k]) for k in ("arrival_s", "dispatch_s", "first_text_s", "finish_s")]
                guard(all(math.isfinite(t) for t in ts) and ts == sorted(ts), f"Time ordering invalid: {policy}")
            all_rows[policy] = rows
            ttfts = [1000 * (float(r["first_text_s"]) - float(r["arrival_s"])) for r in rows]
            long_rows = [r for r in rows if r["group"] == "long"]
            output_tokens = sum(int(r["output_tokens"]) for r in rows)
            duration = max(float(r["finish_s"]) for r in rows) - min(float(r["arrival_s"]) for r in rows)
            metrics = {
                "policy": policy,
                "n_requests": len(rows), "completed": len(rows),
                "short_n": sum(r["group"] == "short" for r in rows), "long_n": len(long_rows),
                "trace_sha256": tracehash,
                "output_tokens_total": output_tokens,
                "duration_s": duration,
                "p50_ttft_ms": percentile(ttfts, .5),
                "p95_ttft_ms": percentile(ttfts, .95),
                "p99_ttft_ms": percentile(ttfts, .99),
                "long_p95_ttft_ms": percentile([1000 * (float(r["first_text_s"]) - float(r["arrival_s"])) for r in long_rows], .95),
                "valid_output_tokens_s": output_tokens / duration,
            }
            values = {
                "all_p50_ttft_ms": metrics["p50_ttft_ms"],
                "all_p95_ttft_ms": metrics["p95_ttft_ms"],
                "all_p99_ttft_ms": metrics["p99_ttft_ms"],
                "long_p95_ttft_ms": metrics["long_p95_ttft_ms"],
                "valid_output_tokens_s": metrics["valid_output_tokens_s"],
            }
            for key, recalculated in values.items():
                guard(nearly(recalculated, reported[policy][key]), f"Reported metric mismatch: {policy}:{key}")
            results.append(metrics)
            all_requests += len(rows)
            all_success += sum(r["status"] == "ok" for r in rows)
            # Parse the original streaming events without importing the first analyzer.
            streamed_ids, nonempty_ids = set(), set()
            with z.open(prefix + "/events.jsonl") as events:
                for raw in events:
                    event = json.loads(raw)
                    rid = str(event["request_id"])
                    streamed_ids.add(rid)
                    line = event.get("line", "")
                    if line.startswith("data:") and line[5:].strip() != "[DONE]":
                        payload = json.loads(line[5:].strip())
                        if any(c.get("text") for c in payload.get("choices", [])):
                            nonempty_ids.add(rid)
            guard(streamed_ids == jobs.keys(), f"SSE stream ID mismatch: {policy}")
            guard(nonempty_ids == jobs.keys(), f"First-text evidence missing: {policy}")
            budget_counts, active_budget_set, steps = {}, set(), 0
            with z.open(logprefix + "/allocations.jsonl") as allocations:
                for raw in allocations:
                    entry = json.loads(raw)
                    budget = int(entry["budget"])
                    allocated = int(entry["actual_tokens"])
                    steps += 1
                    guard(allocated <= budget <= int(entry["ceiling"]), f"Scheduler cap violated: {policy}")
                    guard(allocated == sum(int(v) for v in entry["num_scheduled_tokens"].values()),
                          f"Allocation accounting mismatch: {policy}")
                    expected_class = "PressureAwareScheduler" if policy == "adaptive_internal" else "InstrumentedFixedScheduler"
                    guard(entry["scheduler_class"] == expected_class, f"Scheduler class mismatch: {policy}")
                    budget_counts[budget] = budget_counts.get(budget, 0) + 1
                    if allocated > 0:
                        active_budget_set.add(budget)
            if policy.startswith("fixed_"):
                guard(active_budget_set == {int(policy.removeprefix("fixed_"))}, f"Fixed policy cap mismatch: {policy}")
            else:
                guard(active_budget_set == {512, 1024, 2048}, "Adaptive budget variation not observed")
            allocation_results.append({"policy": policy, "steps_including_warmup": steps,
                                       "selected_budget_counts": budget_counts,
                                       "nonempty_budgets": sorted(active_budget_set)})
        guard(all_requests == all_success == 640, "Total request/completion mismatch")
        guard(len(seen_trace_hashes) == 1, "Policies did not share a byte-identical trace")
        control_fields = ("group", "input_tokens_estimate", "requested_output_tokens")
        base = {r["request_id"]: r for r in all_rows["fixed_2048"]}
        for policy in POLICIES:
            guard(set(r["request_id"] for r in all_rows[policy]) == set(base), f"Request set mismatch: {policy}")
            for row in all_rows[policy]:
                for field in control_fields:
                    guard(row[field] == base[row["request_id"]][field], f"Cross-policy input mismatch: {policy}")
        return {
            "status": "PASS - original pilot arithmetic and structural checks",
            "audit_scope": "Archival integrity, per-request arithmetic, source/config hash, streaming and allocation logs; no new GPU replay",
            "evidence_sha256": EXPECTED_ZIP_SHA,
            "original_source_archive_sha256": EXPECTED_SOURCE_ARCHIVE_SHA,
            "trace_sha256": next(iter(seen_trace_hashes)),
            "vllm_version": env.get("vllm"),
            "reported_device": env.get("device_name"),
            "total_requests": all_requests,
            "total_completed": all_success,
            "runs": results,
            "allocation_audit": allocation_results,
            "limitations": ["single seed 42", "one workload", "one GPU", "not a fresh GPU replication", "client-observed first-nonempty-text TTFT", "in-engine allocations include warmups"],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path(__file__).resolve().parents[1]/"evidence/pilot/Raw_RunPod_GPU_Evidence.zip")
    parser.add_argument("--out", type=Path, default=Path("recompute-output"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        report = audit(args.archive, root)
    except Exception as exc:
        print(f"AUDIT FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/"audit.json").write_text(json.dumps(report, indent=2)+"\n")
    rows = report["runs"]
    with (args.out/"recomputed_summary.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    print("PASS: Archived evidence hash, source hashes, 640 request records, stream events, allocation caps, and independent metrics match.")
    for r in rows:
        print(f"{r['policy']:18s}  P99 first text {r['p99_ttft_ms']/1000:.3f} s  output {r['valid_output_tokens_s']:.0f} tokens/s")
    print(f"Wrote {args.out/'audit.json'} and {args.out/'recomputed_summary.csv'}")
    print("CAUTION: No fresh GPU execution or multi-seed statistical confidence is implied.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
