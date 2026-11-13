# Exact quantities to report

- **Client first-nonempty-text TTFT** = (`first_text_s` - `arrival_s`) × 1000, where `arrival_s` is the client-generated scheduled arrival time. It includes generation/dispatch lag and HTTP overhead. It is **not** pure server queuing time and not necessarily the instant of first token on GPU.
- **P99 TTFT** = default linear interpolation of the 99th percentile of valid-completion TTFTs. Always show the number of valid requests and failures; do not treat correlated requests in a single burst as independent sampling units for confidence intervals.
- **Output tokens per second** = sum of confirmed `output_tokens` for valid requests ÷ (`max(finish_s)` - `min(arrival_s)`) across scheduled requests. This includes local ingress and tail-drain time and is not a direct hardware tokens/s microbenchmark.
- **Long-cohort P95 TTFT** = same latency computed only for requests labelled `long` in the fixed synthetic trace. It is a responsiveness proxy, **not** direct observation of scheduler starvation or a formal fairness metric.
- **Client text-event gaps** correspond to nonempty streamed *text chunks*, not guaranteed token-level inter-token latencies. Do not label these GPU decode-time ITL.
- **Scheduler allocation caps** = returned `num_scheduled_tokens` totals per scheduler step, not direct proof of issued GPU cycles. The allocation event logs include warmup and smoke-test steps.

For formal conclusions, report error rate, actual offered load and generator lag, hardware and model revision, per-seed data, comparable warmed startup procedure, and the uncertainties of the paired independent-seed design.
