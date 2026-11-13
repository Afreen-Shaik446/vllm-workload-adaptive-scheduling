#!/usr/bin/env bash
set -euo pipefail
python scripts/runtime_probe.py --out "${1:-results/environment}"
