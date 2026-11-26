#!/usr/bin/env bash
set -euo pipefail
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
canonical_reward="/logs/verifier/reward.json"
log_root="${VERIFIER_LOG_DIR:-$(dirname "$canonical_reward")}"
output_root="${VERIFIER_OUTPUT_DIR:-/workspace/outputs}"
resource_root="${VERIFIER_RESOURCE_DIR:-/workspace/resources}"
checker="${VERIFIER_CHECKER_DRIVER:-$here/checker.py}"
mkdir -p "$log_root"
rm -f "$log_root/reward.json" "$log_root/reward.txt" "$log_root/.reward.pending.json"
trap 'rm -f "$log_root/.reward.pending.json"' EXIT
if ! timeout "${VERIFIER_TIMEOUT_SECONDS:-60}" python -I -B "$checker" --resources "$resource_root" --outputs "$output_root" --report "$log_root/.reward.pending.json"; then
    echo "VERIFIER_INFRASTRUCTURE_FAILURE: checker failed or timed out" >&2
    exit 1
fi
python -I -B - "$log_root/.reward.pending.json" "$log_root/reward.json" <<'PY'
import json
import math
import os
import sys
from pathlib import Path

pending, destination = map(Path, sys.argv[1:])
try:
    result = json.loads(pending.read_text())
    reward = result["reward"]
    if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward) or not 0.0 <= reward <= 1.0:
        raise ValueError("reward must be a finite normalized number")
    result["reward_contract"] = "harbor-reward-contract/1.0"
    destination.with_name("grading_details.json").write_text(json.dumps(result, allow_nan=False) + "\n")
    pending.write_text(json.dumps({"reward": reward}, allow_nan=False) + "\n")
    os.replace(pending, destination)
except Exception as error:
    print(f"VERIFIER_INFRASTRUCTURE_FAILURE: {error}", file=sys.stderr)
    sys.exit(1)
PY
