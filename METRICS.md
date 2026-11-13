# Measurement definitions and missing observability

| Quantity | Source and definition | Limitation |
|---|---|---|
| Arrival TTFT | Client first nonempty text minus scheduled arrival | Includes generator lag, socket/network, API and engine time; not server TTFT |
| Dispatch TTFT | Client first nonempty text minus HTTP coroutine dispatch | Dispatch precedes actual socket transmission |
| Text event gap | Time between nonempty streamed text events | A text event may contain zero/multiple token boundaries; MUST NOT call this inter-token latency |
| Client TPOT approximation | Last minus first nonempty text time / (usage output tokens - 1) | Excludes final protocol/usage delay; text coalescing and suppressed text affect it; undefined with <2 text events |
| End-to-end latency | Client finish minus scheduled arrival | Finish includes DONE/protocol processing |
| Client admission delay | Dispatch minus scheduled arrival | Includes event-loop/network-client initiation delay; NOT engine queue waiting |
| Long-request TTFT | Arrival TTFT for long-input or long-output group | Fairness proxy; does not isolate server waiting |
| Valid output token throughput | Sum output tokens for status=ok / makespan through last failed/completed request | Invalid/missing usage remains visible and is excluded from numerator |
| Completion | Valid or protocol-completed missing-usage/token-mismatch responses | Separate valid percentage and failed statuses must be reported |
| Server metrics | Raw /metrics snapshots before/after each run | Cumulative histogram deltas; inspect exact version-specific names, buckets, counters; no per-request mapping |
| Engine allocations | Actual SchedulerOutput.num_scheduled_tokens and chosen budget | Sampled logs can miss transitions; log every step only for integration proof |

True **request-level token ITL and server queue wait are not implemented or measured** here. Before reporting them, add a verified server token-ID/timestamp path and request-ID-correlated enqueue/first-schedule events. Do not substitute chunk gaps, average TPOT, or long TTFT for those quantities. Server histogram buckets yield bucket-bounded approximate quantiles, not exact percentiles; do not subtract histogram quantiles. Existing raw snapshots are retained for a later validated parser.

Quantiles use linear interpolation, separately within runs/groups. Latency summaries condition on valid completions; failure rates and timeout drain time must accompany every comparison. Paired 95% bootstrap intervals resample entire seed/run blocks (10,000 draws, seed 9321), reporting geometric mean ratios. Small block counts, repeated workloads within seeds, and multiple comparisons limit interpretation. These intervals do not make P99 statistically reliable with few tail observations. No bootstrap was applied to GPU data in this execution because none exists.
