#!/bin/bash
set -uo pipefail
expected_stage="D_DECODE"
expected_step="d_decode"
reward=0
python3 - "$expected_stage" "$expected_step" <<'PY'
import json
import sys
import zipfile
from pathlib import Path

stage, step = sys.argv[1:]
out = Path("/workspace/output/stages") / step
required = [out / "results.jsonl", out / "evidence_bundle.zip", out / "final_report.md"]
if not all(path.is_file() and path.stat().st_size > 0 for path in required):
    raise SystemExit("required stage outputs are missing or empty")
if not (out / "code").is_dir() or not any(path.is_file() for path in (out / "code").rglob("*")):
    raise SystemExit("reproducible code directory is missing or empty")
found = False
with (out / "results.jsonl").open("r", encoding="utf-8") as handle:
    for line_number, line in enumerate(handle, 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("stage") == stage:
            found = True
if not found:
    raise SystemExit(f"no structured result record for completed stage {stage}")
with zipfile.ZipFile(out / "evidence_bundle.zip") as archive:
    if "manifest.json" not in archive.namelist() or archive.testzip() is not None:
        raise SystemExit("evidence bundle is corrupt or lacks manifest.json")
PY
if [ "$?" -eq 0 ]; then
  reward=1
fi
mkdir -p /logs/verifier
printf '%s\n' "$reward" > /logs/verifier/reward.txt
printf '%s\n' "$reward"
exit 0

