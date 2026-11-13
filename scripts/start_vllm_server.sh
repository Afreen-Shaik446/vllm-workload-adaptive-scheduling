#!/usr/bin/env bash
set -euo pipefail
# RUN IN ALREADY-APPROVED GPU ENVIRONMENT. THIS SCRIPT NEVER ALLOCATES A GPU.
POLICY=${1:-fixed_2048}
MODEL=Qwen/Qwen2.5-1.5B-Instruct
REVISION=989aa7980e4cf806f80c7fef2b1adb7bc71aa306
# No auto-install or cost-incurring operations. Set up vLLM v0.32.0 yourself.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$HERE:${PYTHONPATH:-}"
python - <<'PY'
import vllm
assert vllm.__version__ == '0.32.0', f'Expected 0.32.0, got {vllm.__version__}'
PY
ARGS=("$MODEL" --revision "$REVISION" --tokenizer-revision "$REVISION" --dtype half --host 127.0.0.1 --port 8000 --max-model-len 4096 --max-num-batched-tokens 2048 --max-num-seqs 64 --enable-chunked-prefill --no-enable-prefix-caching --no-async-scheduling --gpu-memory-utilization 0.85 --seed 0)
case "$POLICY" in
  stock_2048) ;;
  fixed_2048) ARGS+=(--scheduler-cls budget_lab.vllm_scheduler.InstrumentedFixedScheduler) ;;
  fixed_256|fixed_512|fixed_1024|fixed_2048_audit)
    BUDGET=${POLICY#fixed_}; BUDGET=${BUDGET%_audit}
    ARGS+=(--max-num-scheduled-tokens "$BUDGET" --scheduler-cls budget_lab.vllm_scheduler.InstrumentedFixedScheduler) ;;
  adaptive_internal) ARGS+=(--scheduler-cls budget_lab.vllm_scheduler.PressureAwareScheduler) ;;
  *) echo 'Allowed: fixed_256 | fixed_512 | fixed_1024 | fixed_2048 | adaptive_internal' >&2; exit 2;;
esac
printf 'Executing vllm serve with policy %s\n' "$POLICY"
exec vllm serve "${ARGS[@]}"
